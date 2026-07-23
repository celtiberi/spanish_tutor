"""Non-Anthropic provider adapters exposing an anthropic-SDK-like surface.

GeminiClient speaks Google's OpenAI-compatible endpoint but presents
`client.messages.create(...)` with the subset of the Anthropic signature the
tutor uses (system blocks, string-content messages, max_tokens), returning an
object shaped like an Anthropic Message (content blocks, stop_reason, usage).
Streaming is not supported — config.SUPPORTS_STREAMING gates that path.
"""

from types import SimpleNamespace

import httpx

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"

_STOP_MAP = {"stop": "end_turn", "length": "max_tokens"}


class ProviderHTTPError(RuntimeError):
    pass


class _GeminiMessages:
    def __init__(self, api_key: str):
        self._key = api_key

    def create(self, *, model, max_tokens, messages, system=None, **_ignored):
        oai_messages = []
        if system:
            text = "\n\n".join(b["text"] for b in system)
            oai_messages.append({"role": "system", "content": text})
        oai_messages += [
            {"role": m["role"], "content": m["content"]} for m in messages
        ]
        try:
            r = httpx.post(
                f"{GEMINI_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {self._key}"},
                json={"model": model, "max_tokens": max_tokens,
                      "messages": oai_messages},
                timeout=300,
            )
        except httpx.HTTPError as e:
            raise ProviderHTTPError(f"gemini transport error: {e}") from e
        if r.status_code != 200:
            raise ProviderHTTPError(
                f"gemini HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return SimpleNamespace(
            content=[SimpleNamespace(
                type="text", text=choice["message"].get("content") or "")],
            stop_reason=_STOP_MAP.get(choice.get("finish_reason"),
                                      choice.get("finish_reason")),
            usage=SimpleNamespace(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
            ),
        )


class GeminiClient:
    def __init__(self, api_key: str):
        self.messages = _GeminiMessages(api_key)
