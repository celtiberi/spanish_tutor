"""Server-side speech-to-text for the web mic.

Architecture note (Google docs):
  - Gemini audio = multimodal *understanding* (transcribe via prompt).
  - For dedicated real-time ASR, Google recommends Cloud Speech-to-Text (Chirp).
  - Gemini will invent phrases on silence/noise unless gated hard.

Best practices we apply:
  - LINEAR16/WAV @ 16 kHz mono
  - temperature 0
  - neutral prompt (no "Spanish tutor" priming)
  - VAD: peak RMS + speech-ratio; trim leading/trailing silence
  - structured JSON {has_speech, transcript} so EMPTY is explicit
  - reject short filler / non-Latin hallucinations

Env:
  STT_MODEL   default gemini-3.6-flash
  STT_ENABLED default true
"""

from __future__ import annotations

import base64
import io
import json
import math
import os
import re
import struct
import wave
from typing import Any

import httpx

from . import config

GEMINI_GEN_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

DEFAULT_STT_MODEL = "gemini-3.6-flash"

SYSTEM_INSTRUCTION = (
    "You are a speech-to-text engine only. "
    "Never translate, correct, or invent words. "
    "If the audio has no clear human speech, set has_speech to false "
    "and transcript to an empty string."
)

TRANSCRIBE_PROMPT = """Transcribe any clear human speech in this audio exactly as spoken.

Rules:
- Keep the speaker's language mix as heard (English and/or Spanish).
- Do not translate. Do not fix grammar or pronunciation.
- Do not invent, guess, or complete unfinished words.
- If there is only silence, noise, hum, or unintelligible sound:
  has_speech=false and transcript="".
- Output JSON only matching the schema.
"""

# Full-clip average RMS below this → skip API (near digital silence)
MIN_WAV_RMS = 0.012
# Fraction of short frames that must look "voiced" before we trust STT
MIN_SPEECH_RATIO = 0.10
# Frame for speech-ratio (20 ms @ 16 kHz mono s16)
FRAME_SAMPLES = 320
FRAME_RMS_THRESH = 0.018


def stt_enabled() -> bool:
    v = (os.environ.get("STT_ENABLED") or "true").strip().lower()
    return v not in ("0", "false", "off", "no")


def stt_model() -> str:
    return os.environ.get("STT_MODEL") or DEFAULT_STT_MODEL


def _normalize_mime(mime: str | None) -> str:
    m = (mime or "audio/webm").split(";")[0].strip().lower()
    allowed = {
        "audio/webm",
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/m4a",
        "audio/ogg",
        "audio/flac",
        "audio/aac",
    }
    if m in allowed:
        return m if m != "audio/x-wav" else "audio/wav"
    if m.startswith("audio/"):
        return m
    return "audio/webm"


def _read_wav_pcm(audio_bytes: bytes) -> tuple[bytes, int, int] | None:
    """Return (pcm_bytes, sample_rate, channels) or None."""
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            if wf.getsampwidth() != 2:
                return None
            rate = wf.getframerate()
            nchan = wf.getnchannels()
            raw = wf.readframes(wf.getnframes())
            return raw, rate, nchan
    except Exception:
        return None


def pcm_frame_stats(
    pcm: bytes,
    *,
    frame_samples: int = FRAME_SAMPLES,
    thresh: float = FRAME_RMS_THRESH,
) -> dict[str, float]:
    """RMS / peak / speech_ratio over s16le mono (or first channel of stereo)."""
    if len(pcm) < 4:
        return {"rms": 0.0, "peak": 0.0, "speech_ratio": 0.0, "voiced_frames": 0.0}
    n = len(pcm) // 2
    # Downmix stereo: take every other sample if needed — callers pass mono.
    step = max(1, frame_samples)
    voiced = 0
    total = 0
    acc_all = 0.0
    peak = 0.0
    count_all = 0
    for start in range(0, n - step + 1, step):
        acc = 0.0
        for i in range(start, start + step):
            s = struct.unpack_from("<h", pcm, i * 2)[0] / 32768.0
            acc += s * s
            acc_all += s * s
            count_all += 1
            a = abs(s)
            if a > peak:
                peak = a
        frame_rms = math.sqrt(acc / step)
        total += 1
        if frame_rms >= thresh:
            voiced += 1
    # leftover samples
    if count_all == 0:
        for i in range(n):
            s = struct.unpack_from("<h", pcm, i * 2)[0] / 32768.0
            acc_all += s * s
            count_all += 1
            a = abs(s)
            if a > peak:
                peak = a
    rms = math.sqrt(acc_all / count_all) if count_all else 0.0
    ratio = (voiced / total) if total else 0.0
    return {
        "rms": rms,
        "peak": peak,
        "speech_ratio": ratio,
        "voiced_frames": float(voiced),
    }


def trim_pcm_silence(
    pcm: bytes,
    *,
    frame_samples: int = FRAME_SAMPLES,
    thresh: float = FRAME_RMS_THRESH,
    pad_frames: int = 2,
) -> bytes:
    """Drop leading/trailing non-speech frames (keep small pad)."""
    if len(pcm) < frame_samples * 2 * 4:
        return pcm
    n = len(pcm) // 2
    step = frame_samples
    frames: list[tuple[int, int, float]] = []
    for start in range(0, n - step + 1, step):
        acc = 0.0
        for i in range(start, start + step):
            s = struct.unpack_from("<h", pcm, i * 2)[0] / 32768.0
            acc += s * s
        frames.append((start, start + step, math.sqrt(acc / step)))
    if not frames:
        return pcm
    first = next((i for i, f in enumerate(frames) if f[2] >= thresh), None)
    last = next((i for i in range(len(frames) - 1, -1, -1) if frames[i][2] >= thresh), None)
    if first is None or last is None:
        return b""  # all silence
    first = max(0, first - pad_frames)
    last = min(len(frames) - 1, last + pad_frames)
    s0 = frames[first][0] * 2
    s1 = frames[last][1] * 2
    return pcm[s0:s1]


def wav_from_pcm(pcm: bytes, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def prepare_wav_for_stt(audio_bytes: bytes) -> tuple[bytes | None, dict[str, Any]]:
    """VAD gate + silence trim. Returns (wav_or_None, stats)."""
    parsed = _read_wav_pcm(audio_bytes)
    if not parsed:
        return audio_bytes, {"format": "non_wav"}
    pcm, rate, nchan = parsed
    if nchan > 1:
        # downmix to mono
        samples = struct.unpack("<" + "h" * (len(pcm) // 2), pcm)
        mono = bytearray()
        for i in range(0, len(samples), nchan):
            v = int(sum(samples[i : i + nchan]) / nchan)
            mono += struct.pack("<h", max(-32768, min(32767, v)))
        pcm = bytes(mono)
    stats = pcm_frame_stats(pcm)
    stats["rate"] = float(rate)
    stats["bytes_in"] = float(len(audio_bytes))
    if stats["rms"] < MIN_WAV_RMS or stats["speech_ratio"] < MIN_SPEECH_RATIO:
        stats["skipped"] = "vad_gate"
        return None, stats
    trimmed = trim_pcm_silence(pcm)
    if len(trimmed) < rate * 2 * 0.2:  # <200ms
        stats["skipped"] = "too_short_after_trim"
        return None, stats
    stats["bytes_trimmed"] = float(len(trimmed))
    return wav_from_pcm(trimmed, rate), stats


def wav_rms(audio_bytes: bytes) -> float | None:
    parsed = _read_wav_pcm(audio_bytes)
    if not parsed:
        return None
    pcm, _, _ = parsed
    return pcm_frame_stats(pcm)["rms"]


def _clean_transcript(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^transcript\s*:\s*", "", text, flags=re.I).strip()
    text = text.strip('"').strip("'").strip()
    upper = text.upper().strip(" .!?:;")
    if not text or upper in {
        "EMPTY",
        "(EMPTY)",
        "[EMPTY]",
        "SILENCE",
        "NO SPEECH",
        "NO SPEECH DETECTED",
        "INAUDIBLE",
        "N/A",
        "NONE",
    }:
        return ""
    if re.fullmatch(r"(?i)\(?\s*empty\s*\)?", text):
        return ""
    # Common silence hallucinations
    if re.fullmatch(
        r"(?i)(who|what|huh|um+|uh+|hmm+|look|hi|hey|hello|thanks|thank you|"
        r"there are|there is|you know|i mean|okay|ok|yes|no|yeah)\.?",
        text,
    ):
        return ""
    if not re.search(r"[A-Za-zÀ-ÿÁÉÍÓÚÜÑáéíóúüñ]", text):
        return ""
    # Reject pure punctuation / very short junk
    letters = re.findall(r"[A-Za-zÀ-ÿÁÉÍÓÚÜÑáéíóúüñ]", text)
    if len(letters) < 2:
        return ""
    return text


def _parse_model_json(raw: str) -> tuple[bool, str]:
    """Parse structured {has_speech, transcript} or fall back to plain text."""
    t = (raw or "").strip()
    if not t:
        return False, ""
    # strip markdown fences
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.I)
    t = re.sub(r"\s*```$", "", t)
    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            has = obj.get("has_speech")
            transcript = obj.get("transcript") or obj.get("text") or ""
            if has is False:
                return False, ""
            return bool(has if has is not None else bool(str(transcript).strip())), str(
                transcript
            )
    except json.JSONDecodeError:
        pass
    # plain text fallback
    if t.upper() in {"EMPTY", "FALSE", "NULL"}:
        return False, ""
    return True, t


def transcribe_gemini(
    audio_bytes: bytes,
    *,
    mime_type: str = "audio/webm",
    model: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return (transcript, meta). Raises on failure."""
    config.load_env()
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set (needed for server STT)")
    if not audio_bytes or len(audio_bytes) < 64:
        raise ValueError("audio too short")

    model = model or stt_model()
    mime = _normalize_mime(mime_type)
    stats: dict[str, Any] = {}

    # VAD + trim for WAV (our streaming path always sends WAV)
    if mime == "audio/wav":
        prepared, stats = prepare_wav_for_stt(audio_bytes)
        if prepared is None:
            return "", {
                "provider": "gemini",
                "model": model,
                "mime": mime,
                "bytes": len(audio_bytes),
                "chars": 0,
                **{k: (round(v, 5) if isinstance(v, float) else v) for k, v in stats.items()},
            }
        audio_bytes = prepared
        mime = "audio/wav"

    b64 = base64.b64encode(audio_bytes).decode("ascii")
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{
            "parts": [
                {"text": TRANSCRIBE_PROMPT},
                {"inline_data": {"mime_type": mime, "data": b64}},
            ]
        }],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 512,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "object",
                "properties": {
                    "has_speech": {"type": "boolean"},
                    "transcript": {"type": "string"},
                },
                "required": ["has_speech", "transcript"],
            },
        },
    }
    url = GEMINI_GEN_URL.format(model=model)
    with httpx.Client(timeout=90.0) as client:
        r = client.post(url, params={"key": key}, json=body)
    if r.status_code != 200:
        # Fallback without schema if model rejects responseSchema
        if r.status_code in (400, 404):
            body.pop("generationConfig", None)
            body["generationConfig"] = {
                "temperature": 0.0,
                "maxOutputTokens": 512,
            }
            r = client.post(url, params={"key": key}, json=body)
        if r.status_code != 200:
            raise RuntimeError(f"gemini STT HTTP {r.status_code}: {r.text[:300]}")

    data = r.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
        texts = [
            p.get("text") or ""
            for p in parts
            if isinstance(p, dict) and p.get("text")
        ]
        raw = "\n".join(texts).strip()
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"gemini STT unexpected payload: {str(data)[:200]}") from e

    has_speech, text = _parse_model_json(raw)
    if not has_speech:
        text = ""
    else:
        text = _clean_transcript(text)

    umeta = data.get("usageMetadata") or {}
    meta: dict[str, Any] = {
        "provider": "gemini",
        "model": model,
        "mime": mime,
        "bytes": len(audio_bytes),
        "chars": len(text),
        "has_speech": bool(text),
        "usage": {
            "input_tokens": int(umeta.get("promptTokenCount") or 0),
            "output_tokens": int(umeta.get("candidatesTokenCount") or 0),
        },
    }
    for k, v in stats.items():
        if isinstance(v, float):
            meta[k] = round(v, 5)
        elif k not in meta:
            meta[k] = v
    return text, meta


def transcribe(audio_bytes: bytes, mime_type: str = "audio/webm") -> tuple[str, dict]:
    if not stt_enabled():
        raise RuntimeError("server STT disabled (STT_ENABLED=off)")
    return transcribe_gemini(audio_bytes, mime_type=mime_type)
