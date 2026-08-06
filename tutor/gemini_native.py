"""Gemini NATIVE generateContent client with explicit prefix caching.

P0 of the multi-model analysis (docs/analysis-multi-model-context.md,
converged 2026-08-06): implicit caching is dead for this key (2.9%
ledger hit rate), but the explicit cachedContents API works — smoke
2026-08-06 cached the full 7,008-token static prefix with 100% hits.
Round turns re-bill ~1.2¢ of identical text without it.

Design:
- Same client surface as the rest of the codebase: ``client.messages
  .create(model=, max_tokens=, system=, messages=, tools=)`` returning
  an anthropic-shaped SimpleNamespace (content blocks, stop_reason,
  usage) — a drop-in for conv_session._call.
- ONE process-global cache per (model, fingerprint(system+tools)):
  created lazily, TTL ~30 min, recreated on expiry/fingerprint change.
  All sessions share it (the static prefix is identical for every
  learner). Storage ≈ 0.7¢/hour while alive vs ≈1¢/turn saved.
- When the exact (system, tools) pair matches the cache, the request
  sends ``cachedContent`` and omits system/tools (API contract). Any
  MISMATCH (plan turns' extra blocks, tool changes) falls back to
  uncached native — correctness first, never an error path.
- Failures of the cache layer degrade to uncached calls with a
  [no-hide] line — a broken cache must never break teaching.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from types import SimpleNamespace
from typing import Any

import httpx

from .providers import ProviderHTTPError

NATIVE_BASE = "https://generativelanguage.googleapis.com/v1beta"
CACHE_TTL_S = 1800


def _system_text(system) -> str:
    if not system:
        return ""
    if isinstance(system, list):
        return "\n\n".join(
            (b.get("text", "") if isinstance(b, dict) else str(b))
            for b in system
        )
    return str(system)


_NATIVE_SCHEMA_KEYS = {
    "type", "format", "description", "nullable", "enum", "items",
    "properties", "required", "maxItems", "minItems",
}


def _sanitize_schema(node):
    """The native FunctionDeclaration Schema is a SUBSET of JSON Schema —
    it 400s on keywords like additionalProperties (hit live 2026-08-06).
    Keep only supported keywords; inside "properties" the keys are
    property NAMES (never filtered — first sanitizer version deleted
    every property and broke "required")."""
    if isinstance(node, dict):
        # anyOf unsupported by the native subset (400 live 2026-08-06):
        # flatten to the first branch — server-side validation loosens,
        # tool behavior is carried by descriptions.
        if "anyOf" in node and isinstance(node["anyOf"], list) and node["anyOf"]:
            merged = dict(node["anyOf"][0])
            merged.update({k: v for k, v in node.items() if k != "anyOf"})
            return _sanitize_schema(merged)
        out = {}
        for k, v in node.items():
            if k not in _NATIVE_SCHEMA_KEYS:
                continue
            if k == "properties" and isinstance(v, dict):
                out[k] = {name: _sanitize_schema(sub) for name, sub in v.items()}
            elif k == "type" and isinstance(v, list):
                # JSON-Schema union ["string","null"] → single type +
                # nullable (native proto: "cannot start list", live 400).
                non_null = [t for t in v if t != "null"]
                out[k] = non_null[0] if non_null else "string"
                if "null" in v:
                    out["nullable"] = True
            else:
                out[k] = _sanitize_schema(v)
        return out
    if isinstance(node, list):
        return [_sanitize_schema(x) for x in node]
    return node


def _tools_to_native(tools) -> list[dict] | None:
    if not tools:
        return None
    decls = []
    for t in tools:
        decls.append({
            "name": t.get("name"),
            "description": t.get("description", ""),
            "parameters": _sanitize_schema(
                t.get("input_schema") or {"type": "object"}),
        })
    return [{"functionDeclarations": decls}]


def _messages_to_contents(messages) -> list[dict]:
    """Anthropic-style messages → native contents (incl. tool blocks)."""
    contents: list[dict] = []
    for m in messages:
        role = "model" if m.get("role") == "assistant" else "user"
        content = m.get("content")
        parts: list[dict] = []
        if isinstance(content, str):
            parts.append({"text": content})
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    parts.append({"text": block.get("text") or ""})
                elif btype == "tool_use":
                    p = {"functionCall": {
                        "name": block.get("name") or "",
                        "args": block.get("input") or {},
                    }}
                    if block.get("thought_signature"):
                        p["thoughtSignature"] = block["thought_signature"]
                    parts.append(p)
                elif btype == "tool_result":
                    raw = block.get("content")
                    try:
                        resp = json.loads(raw) if isinstance(raw, str) else (raw or {})
                    except ValueError:
                        resp = {"result": str(raw)}
                    if not isinstance(resp, dict):
                        resp = {"result": resp}
                    parts.append({"functionResponse": {
                        # tool_use_id carries "call_<name>"-style ids; the
                        # native API matches on function NAME.
                        "name": str(block.get("tool_use_id") or "tool").split(":")[0],
                        "response": resp,
                    }})
        if parts:
            contents.append({"role": role, "parts": parts})
    return contents


def _parse_response(d: dict):
    cand = (d.get("candidates") or [{}])[0]
    blocks: list[SimpleNamespace] = []
    n_calls = 0
    for part in ((cand.get("content") or {}).get("parts") or []):
        if "text" in part:
            blocks.append(SimpleNamespace(type="text", text=part["text"]))
        elif "functionCall" in part:
            fc = part["functionCall"]
            n_calls += 1
            blocks.append(SimpleNamespace(
                type="tool_use",
                id=f"{fc.get('name','tool')}:call_{n_calls}",
                name=fc.get("name") or "",
                input=fc.get("args") or {},
                # Native API requires this replayed when the call goes
                # back into history (400 live 2026-08-06).
                thought_signature=part.get("thoughtSignature"),
            ))
    finish = (cand.get("finishReason") or "STOP").lower()
    stop = "max_tokens" if finish == "max_tokens" else (
        "tool_use" if (n_calls and not any(
            b.type == "text" and b.text.strip() for b in blocks)) else "end_turn")
    um = d.get("usageMetadata") or {}
    return SimpleNamespace(
        content=blocks,
        stop_reason=stop,
        usage=SimpleNamespace(
            input_tokens=um.get("promptTokenCount", 0),
            output_tokens=(um.get("candidatesTokenCount", 0)
                           + um.get("thoughtsTokenCount", 0)),
            thinking_tokens=um.get("thoughtsTokenCount", 0) or 0,
            cache_read_input_tokens=um.get("cachedContentTokenCount", 0) or 0,
            cache_creation_input_tokens=0,
        ),
    )


class _PrefixCache:
    """Process-global explicit cache for one (model, system+tools) pair."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # fp -> (cache name, expiry). Open/round turns have different
        # system variants; each gets ONE cache, none get recreated
        # per call (first version was single-slot and thrashed).
        self._by_fp: dict[str, tuple[str, float]] = {}

    @staticmethod
    def _fingerprint(model: str, system_text: str, tools_native) -> str:
        blob = model + "\x00" + system_text + "\x00" + json.dumps(
            tools_native or [], sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def get_or_create(self, key: str, model: str, system_text: str,
                      tools_native) -> str | None:
        fp = self._fingerprint(model, system_text, tools_native)
        with self._lock:
            hit = self._by_fp.get(fp)
            if hit and time.time() < hit[1]:
                return hit[0]
            body: dict[str, Any] = {
                "model": f"models/{model}",
                "systemInstruction": {"parts": [{"text": system_text}]},
                "ttl": f"{CACHE_TTL_S}s",
                "displayName": f"ml-teacher-prefix-{fp}",
            }
            if tools_native:
                body["tools"] = tools_native
            try:
                r = httpx.post(
                    f"{NATIVE_BASE}/cachedContents",
                    headers={"x-goog-api-key": key},
                    json=body, timeout=120)
                if r.status_code != 200:
                    raise ProviderHTTPError(
                        f"cache create {r.status_code}: {r.text[:200]}")
                name = r.json().get("name")
                # Refresh margin: recreate 2 min before actual expiry.
                self._by_fp[fp] = (name, time.time() + CACHE_TTL_S - 120)
                print(f"[gemini-cache] prefix cache created "
                      f"({name}, ttl {CACHE_TTL_S}s)", flush=True)
                return name
            except Exception as e:
                import sys

                print(f"[no-hide] gemini prefix cache create FAILED "
                      f"(uncached calls continue): {type(e).__name__}: {e}",
                      file=sys.stderr, flush=True)
                return None


_CACHE = _PrefixCache()


class _NativeMessages:
    def __init__(self, api_key: str):
        self._key = api_key

    def create(self, *, model, max_tokens, messages, system=None,
               tools=None, **_ignored):
        sys_text = _system_text(system)
        tools_native = _tools_to_native(tools)
        contents = _messages_to_contents(messages)
        gen_config: dict[str, Any] = {"maxOutputTokens": max_tokens}
        # The native default lets 3.6-flash think ~1k tokens/turn (billed
        # as output at $7.50/M, +latency) — the compat path our gates
        # passed on did not. Probed live 2026-08-06: thinkingBudget:0 is
        # rejected; thinkingLevel:"minimal" → 0 thought tokens (the
        # known-good profile). Override via GEMINI_THINKING_LEVEL.
        import os as _os

        level = _os.environ.get("GEMINI_THINKING_LEVEL", "minimal").strip()
        if level and level != "default":
            gen_config["thinkingConfig"] = {"thinkingLevel": level}
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": gen_config,
        }
        cache_name = None
        # API minimum is 1024 cached tokens — small prompts (e.g. the
        # history summarizer) skip caching instead of 400ing every call.
        if sys_text and len(sys_text) // 4 >= 1200:
            cache_name = _CACHE.get_or_create(
                self._key, model, sys_text, tools_native)
        if cache_name:
            body["cachedContent"] = cache_name
        else:
            if sys_text:
                body["systemInstruction"] = {"parts": [{"text": sys_text}]}
            if tools_native:
                body["tools"] = tools_native
        try:
            r = httpx.post(
                f"{NATIVE_BASE}/models/{model}:generateContent",
                headers={"x-goog-api-key": self._key},
                json=body, timeout=300)
        except httpx.HTTPError as e:
            raise ProviderHTTPError(f"gemini transport error: {e}") from e
        if r.status_code == 400 and cache_name:
            # Cache invalidated server-side (expired/deleted): retry
            # uncached, visibly, and drop the stale handle.
            import sys

            print(f"[no-hide] gemini cache 400 — retrying uncached: "
                  f"{r.text[:150]}", file=sys.stderr, flush=True)
            _CACHE._by_fp.clear()
            body.pop("cachedContent", None)
            if sys_text:
                body["systemInstruction"] = {"parts": [{"text": sys_text}]}
            if tools_native:
                body["tools"] = tools_native
            r = httpx.post(
                f"{NATIVE_BASE}/models/{model}:generateContent",
                headers={"x-goog-api-key": self._key},
                json=body, timeout=300)
        if r.status_code != 200:
            raise ProviderHTTPError(
                f"gemini native {r.status_code}: {r.text[:300]}")
        return _parse_response(r.json())


class GeminiNativeClient:
    def __init__(self, api_key: str):
        self.messages = _NativeMessages(api_key)
