"""Server-side text-to-speech for the web tutor.

Primary: Gemini TTS models (good Spanish + bilingual).
Fallback: callers use browser speechSynthesis if this fails
(on macOS that is the system voice — not ideal).

Env:
  TTS_MODEL   default gemini-2.5-flash-preview-tts
              (also try: gemini-3.1-flash-tts-preview)
  TTS_VOICE   default Sulafat (warm)
  TTS_ENABLED default true; set off/false to force browser only
  TTS_RATE    default 1.0 (0.7–1.2); slow-style prefix only at <= 0.8
              (no numeric Gemini rate field; client playbackRate is exact)
"""

from __future__ import annotations

import base64
import io
import os
import re
import time
import wave
from typing import Any

import httpx

from . import config

GEMINI_TTS_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

# Working AI Studio / API model ids (as of 2026-07)
DEFAULT_TTS_MODEL = "gemini-2.5-flash-preview-tts"
FALLBACK_TTS_MODELS = (
    "gemini-2.5-flash-preview-tts",
    "gemini-3.1-flash-tts-preview",
    "gemini-2.5-pro-preview-tts",
)
DEFAULT_TTS_VOICE = "Sulafat"  # Warm
# Friendly alternatives: Achird, Aoede, Kore, Charon


def tts_enabled() -> bool:
    v = (os.environ.get("TTS_ENABLED") or "true").strip().lower()
    return v not in ("0", "false", "off", "no", "browser")


def tts_model() -> str:
    return os.environ.get("TTS_MODEL") or DEFAULT_TTS_MODEL


def tts_voice() -> str:
    return os.environ.get("TTS_VOICE") or DEFAULT_TTS_VOICE


def clean_for_speech(text: str) -> str:
    """Strip markdown / structure noise so TTS reads cleanly."""
    t = text or ""
    t = re.sub(
        r"</?(?:tutor|acknowledge|recast|explain|continue)[^>]*>",
        " ",
        t,
        flags=re.I,
    )
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"^#+\s*", "", t, flags=re.M)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _parse_pcm_rate(mime: str) -> int:
    # audio/L16;codec=pcm;rate=24000  OR  audio/l16; rate=24000; channels=1
    m = re.search(r"rate\s*=\s*(\d+)", mime or "", flags=re.I)
    return int(m.group(1)) if m else 24000


def pcm_to_wav(
    pcm: bytes, *, rate: int = 24000, channels: int = 1, width: int = 2
) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(width)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()


# Style prefix ONLY when rate <= 0.8 — the deliberately-slow regime. Gemini
# API has no numeric speakingRate on speechConfig; exact speed at 0.85–1.2
# comes from client playbackRate alone (styling "slowly" at 0.9 stacked with
# 0.9× playback = double slowdown, user complaint 2026-07-28).
# Keep SHORT: long director preambles often HTTP 500, and the TTS model
# sometimes reads the preamble ALOUD — every extra word is leak risk
# (learner heard invisible director text, 2026-07-27 report).
SLOW_STYLE_PREFIX = "Speak slowly and clearly. "


def _tts_prompt_variants(spoken: str, *, rate: float = 1.0) -> list[str]:
    """Gemini TTS is picky: long 'director' preambles often 500; bare text can 400.

    Short speak-directives are the sweet spot for bilingual tutor lines.
    Keep every directive to ONE short line: the model occasionally reads the
    directive aloud, and the learner hears text that is not on screen.
    Only at rate <= 0.8 (deliberately slow) prepend a one-line slow-style
    instruction; at 0.85–1.2 the prompt is unstyled and the exact speed is
    applied client-side via playbackRate.
    """
    head = SLOW_STYLE_PREFIX if rate <= 0.8 else ""
    return [
        # Preferred — short, clear speak instruction
        f"{head}Say warmly, exactly as written:\n\n{spoken}",
        f"{head}Say warmly and clearly:\n{spoken}",
        f"{head}{spoken}" if head else spoken,
    ]


def _models_to_try(preferred: str) -> list[str]:
    out: list[str] = []
    for m in (preferred, *FALLBACK_TTS_MODELS):
        if m and m not in out:
            out.append(m)
    return out


def _request_tts(
    *,
    key: str,
    model: str,
    voice: str,
    prompt: str,
) -> tuple[bytes, str, dict]:
    url = GEMINI_TTS_URL.format(model=model)
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice},
                }
            },
        },
    }
    with httpx.Client(timeout=90.0) as client:
        r = client.post(url, params={"key": key}, json=body)
    if r.status_code != 200:
        raise RuntimeError(f"gemini TTS HTTP {r.status_code}: {r.text[:280]}")

    data = r.json()
    try:
        part = data["candidates"][0]["content"]["parts"][0]
        inline = part.get("inlineData") or part.get("inline_data") or {}
        b64 = inline.get("data")
        mime = inline.get("mimeType") or inline.get("mime_type") or ""
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(
            f"gemini TTS unexpected payload: {str(data)[:200]}"
        ) from e
    if not b64:
        raise RuntimeError("gemini TTS empty audio")
    umeta = data.get("usageMetadata") or {}
    usage = {
        "input_tokens": int(umeta.get("promptTokenCount") or 0),
        # candidatesTokenCount = audio output tokens (billed at the audio rate)
        "output_tokens": int(umeta.get("candidatesTokenCount") or 0),
    }
    return base64.b64decode(b64), mime, usage


def synthesize_gemini(
    text: str,
    *,
    model: str | None = None,
    voice: str | None = None,
    rate: float | None = None,
) -> tuple[bytes, str, dict[str, Any]]:
    """Return (wav_bytes, mime, meta). Raises on failure.

    `rate` is a product playback multiplier (0.7–1.2). Gemini has no numeric
    rate field; only when rate <= 0.8 does the prompt get SLOW_STYLE_PREFIX.
    At 0.85–1.2 the audio is generated at natural pace and the exact speed
    is applied client-side via HTMLAudioElement.playbackRate.
    """
    config.load_env()
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set (needed for server TTS)")

    preferred = model or tts_model()
    voice = voice or tts_voice()
    spoken = clean_for_speech(text)
    if not spoken:
        raise ValueError("empty text for TTS")

    if rate is None:
        rate = float(getattr(config, "TTS_RATE", 1.0))
    try:
        rate = float(rate)
    except (TypeError, ValueError):
        rate = 1.0
    rate = max(0.7, min(1.2, rate))

    errors: list[str] = []
    for mid in _models_to_try(preferred):
        for prompt in _tts_prompt_variants(spoken, rate=rate):
            for attempt in range(2):
                try:
                    pcm, mime, tts_usage = _request_tts(
                        key=key, model=mid, voice=voice, prompt=prompt
                    )
                    sample_rate = _parse_pcm_rate(mime)
                    meta = {
                        "provider": "gemini",
                        "model": mid,
                        "voice": voice,
                        "chars": len(spoken),
                        "sample_rate": sample_rate,
                        "rate": rate,
                        "style_slow": rate <= 0.8,
                        # No numeric Gemini speakingRate; client applies playbackRate
                        "api_numeric_rate": False,
                        "usage": tts_usage,
                    }
                    if mime.lower().startswith("audio/wav") or mime.lower().startswith(
                        "audio/mpeg"
                    ):
                        return pcm, mime.split(";")[0], meta
                    wav = pcm_to_wav(pcm, rate=sample_rate)
                    return wav, "audio/wav", meta
                except Exception as e:
                    errors.append(f"{mid}/{attempt}: {e}")
                    # brief pause on internal 500
                    if "HTTP 500" in str(e) and attempt == 0:
                        time.sleep(0.4)
                        continue
                    break  # next prompt / model

    raise RuntimeError(
        "gemini TTS failed after retries: " + " | ".join(errors[-4:])
    )


def synthesize(
    text: str,
    *,
    rate: float | None = None,
) -> tuple[bytes, str, dict[str, Any]]:
    """Public entry: currently Gemini only."""
    if not tts_enabled():
        raise RuntimeError("server TTS disabled (TTS_ENABLED=off)")
    return synthesize_gemini(text, rate=rate)
