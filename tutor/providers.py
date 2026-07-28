"""Non-Anthropic provider adapters exposing an anthropic-SDK-like surface.

GeminiClient speaks Google's OpenAI-compatible endpoint but presents
`client.messages.create(...)` with the subset of the Anthropic signature the
tutor uses (system blocks, string-content messages, max_tokens, tools),
returning an object shaped like an Anthropic Message (content blocks,
stop_reason, usage). Streaming is not supported — config.SUPPORTS_STREAMING
gates that path.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import httpx

from . import config as _cfg

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"

_STOP_MAP = {
    "stop": "end_turn",
    "length": "max_tokens",
    "tool_calls": "tool_use",
    "function_call": "tool_use",
}


class ProviderHTTPError(RuntimeError):
    pass


def anthropic_tools_to_openai(tools: list[dict] | None) -> list[dict] | None:
    """Convert Anthropic tool defs → OpenAI function tools."""
    if not tools:
        return None
    out = []
    for t in tools:
        out.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description") or "",
                "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
            },
        })
    return out


def _content_to_openai_parts(content: Any) -> Any:
    """Map Anthropic-style message content into OpenAI chat content / tool fields.

    Returns either a string content, or a dict with content + optional tool_calls
    for assistant messages that used tools.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content)

    texts: list[str] = []
    tool_calls: list[dict] = []
    tool_results: list[dict] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            texts.append(block.get("text") or "")
        elif btype == "tool_use":
            tool_calls.append({
                "id": block.get("id") or f"call_{len(tool_calls)}",
                "type": "function",
                "function": {
                    "name": block.get("name") or "",
                    "arguments": json.dumps(
                        block.get("input") or {}, ensure_ascii=False
                    ),
                },
            })
        elif btype == "tool_result":
            tool_results.append({
                "role": "tool",
                "tool_call_id": block.get("tool_use_id") or "",
                "content": (
                    block.get("content")
                    if isinstance(block.get("content"), str)
                    else json.dumps(block.get("content"), ensure_ascii=False)
                ),
            })
    # tool_result messages are expanded by the caller as separate messages
    if tool_results and not texts and not tool_calls:
        return {"_tool_results": tool_results}
    result: dict[str, Any] = {"content": "\n".join(texts) if texts else None}
    if tool_calls:
        result["tool_calls"] = tool_calls
    return result


def messages_to_openai(
    messages: list[dict], system=None
) -> list[dict]:
    """Build OpenAI chat messages from Anthropic-style system + messages."""
    oai: list[dict] = []
    if system:
        if isinstance(system, list):
            text = "\n\n".join(
                b.get("text", "") if isinstance(b, dict) else str(b)
                for b in system
            )
        else:
            text = str(system)
        oai.append({"role": "system", "content": text})

    for m in messages:
        role = m.get("role", "user")
        content = m.get("content")
        # Expand Anthropic user messages that mix tool_result + text blocks
        if role == "user" and isinstance(content, list):
            tool_results = []
            texts = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result":
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": block.get("tool_use_id") or "",
                        "content": (
                            block.get("content")
                            if isinstance(block.get("content"), str)
                            else json.dumps(
                                block.get("content"), ensure_ascii=False)
                        ),
                    })
                elif block.get("type") == "text":
                    texts.append(block.get("text") or "")
            if tool_results:
                oai.extend(tool_results)
                if texts:
                    oai.append({"role": "user", "content": "\n".join(texts)})
                continue

        mapped = _content_to_openai_parts(content)
        if isinstance(mapped, dict) and "_tool_results" in mapped:
            oai.extend(mapped["_tool_results"])
            continue
        if isinstance(mapped, dict):
            msg: dict[str, Any] = {"role": role}
            if mapped.get("content") is not None:
                msg["content"] = mapped["content"]
            elif mapped.get("tool_calls"):
                msg["content"] = None
            if mapped.get("tool_calls"):
                msg["tool_calls"] = mapped["tool_calls"]
            oai.append(msg)
        else:
            oai.append({"role": role, "content": mapped})
    return oai


def parse_openai_message_to_anthropic(choice_msg: dict, finish_reason: str | None):
    """Map an OpenAI chat completion message into Anthropic-like content blocks."""
    blocks: list[SimpleNamespace] = []
    text = choice_msg.get("content") or ""
    if text:
        blocks.append(SimpleNamespace(type="text", text=text))

    for i, tc in enumerate(choice_msg.get("tool_calls") or []):
        fn = tc.get("function") or {}
        raw_args = fn.get("arguments") or "{}"
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            args = {}
        if not isinstance(args, dict):
            args = {}
        blocks.append(SimpleNamespace(
            type="tool_use",
            id=tc.get("id") or f"call_{i}",
            name=fn.get("name") or "",
            input=args,
        ))

    # legacy single function_call
    fc = choice_msg.get("function_call")
    if fc and not choice_msg.get("tool_calls"):
        raw_args = fc.get("arguments") or "{}"
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            args = {}
        blocks.append(SimpleNamespace(
            type="tool_use",
            id="call_0",
            name=fc.get("name") or "",
            input=args if isinstance(args, dict) else {},
        ))

    if not blocks:
        blocks = [SimpleNamespace(type="text", text="")]

    stop = _STOP_MAP.get(finish_reason or "", finish_reason)
    if any(getattr(b, "type", None) == "tool_use" for b in blocks):
        # Anthropic uses tool_use when tools fire; may still have text
        if finish_reason in ("tool_calls", "function_call"):
            stop = "tool_use"
    return blocks, stop


class _GeminiMessages:
    def __init__(self, api_key: str):
        self._key = api_key

    def create(
        self,
        *,
        model,
        max_tokens,
        messages,
        system=None,
        tools=None,
        **_ignored,
    ):
        oai_messages = messages_to_openai(messages, system=system)
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": oai_messages,
        }
        # Thinking models share max_tokens between reasoning and visible text;
        # an effort hint keeps reasoning from starving the reply.
        effort = getattr(_cfg, "GEMINI_REASONING_EFFORT", None)
        if effort:
            body["reasoning_effort"] = effort
        oai_tools = anthropic_tools_to_openai(tools)
        if oai_tools:
            body["tools"] = oai_tools
            body["tool_choice"] = "auto"

        try:
            r = httpx.post(
                f"{GEMINI_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {self._key}"},
                json=body,
                timeout=300,
            )
        except httpx.HTTPError as e:
            raise ProviderHTTPError(f"gemini transport error: {e}") from e
        if r.status_code != 200:
            raise ProviderHTTPError(
                f"gemini HTTP {r.status_code}: {r.text[:400]}")
        data = r.json()
        choice = data["choices"][0]
        msg = choice.get("message") or {}
        blocks, stop = parse_openai_message_to_anthropic(
            msg, choice.get("finish_reason"))
        usage = data.get("usage", {})
        # Billing extras: reasoning tokens charge at the OUTPUT rate but are
        # not in completion_tokens; cached prompt tokens bill at the cache rate.
        _cdet = usage.get("completion_tokens_details") or {}
        _pdet = usage.get("prompt_tokens_details") or {}
        return SimpleNamespace(
            content=blocks,
            stop_reason=stop,
            usage=SimpleNamespace(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                thinking_tokens=_cdet.get("reasoning_tokens", 0) or 0,
                cache_read_input_tokens=_pdet.get("cached_tokens", 0) or 0,
                cache_creation_input_tokens=0,
            ),
        )


class GeminiClient:
    def __init__(self, api_key: str):
        self.messages = _GeminiMessages(api_key)
