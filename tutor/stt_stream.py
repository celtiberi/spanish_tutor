"""Streaming speech-to-text for the web mic.

Protocol (browser ↔ FastAPI WebSocket /ws/stt):
  client → {"type":"start"}
  client → binary frames: raw s16le mono PCM @ 16 kHz
  client → {"type":"stop"}
  server → {"type":"ready"|"status"|"interim"|"final"|"error"|"closed", ...}

Backends (env STT_BACKEND or STT_STREAM_BACKEND):
  chirp   — Google Cloud Speech-to-Text V2 Chirp (dedicated ASR)  [preferred]
  gemini  — Gemini generative STT with VAD (fallback)
  auto    — chirp if credentials ready, else gemini

While recording we periodically re-recognize the buffer → interim captions.
On stop we run one final recognize.

Silence / VAD: peak RMS + speech-ratio; Chirp still gets trimmed WAV-quality PCM.
See docs/asr-chirp-setup.md.
"""

from __future__ import annotations

import asyncio
import io
import math
import os
import re
import struct
import wave
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Optional

from . import config
from . import stt as stt_mod
from . import stt_chirp as chirp_mod

SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2
MIN_PEAK_RMS = 0.015
# First partial only after enough real speech
PARTIAL_MIN_AUDIO_S = 1.0
PARTIAL_INTERVAL_S = 1.2  # Chirp is fast enough for slightly snappier captions


def resolve_backend() -> str:
    """Return 'chirp' or 'gemini'."""
    config.load_env()
    v = (
        os.environ.get("STT_BACKEND")
        or os.environ.get("STT_STREAM_BACKEND")
        or "auto"
    ).strip().lower()
    if v in ("chirp", "cloud", "speech"):
        return "chirp"
    if v in ("gemini", "partial", "batch", "live", "file"):
        return "gemini"
    # auto
    if chirp_mod.chirp_available():
        return "chirp"
    return "gemini"


def stream_backend() -> str:
    """Caption path label for UI/health."""
    return resolve_backend()


def live_model() -> str:
    """Kept for /api/health compatibility."""
    if resolve_backend() == "chirp":
        return chirp_mod.chirp_model()
    return os.environ.get("STT_MODEL") or stt_mod.stt_model()


def stream_enabled() -> bool:
    v = (os.environ.get("STT_STREAM_ENABLED") or "true").strip().lower()
    return v not in ("0", "false", "off", "no")


def pcm_rms(pcm: bytes) -> float:
    if len(pcm) < 4:
        return 0.0
    n = len(pcm) // 2
    step = max(1, n // 8000)
    acc = 0.0
    count = 0
    for i in range(0, n, step):
        s = struct.unpack_from("<h", pcm, i * 2)[0] / 32768.0
        acc += s * s
        count += 1
    return math.sqrt(acc / count) if count else 0.0


def pcm_to_wav(pcm: bytes, rate: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def clean_stream_text(text: str | None) -> str:
    return stt_mod._clean_transcript(text or "")


def prefer_interim(old: str, new: str) -> str:
    """Stable captions: only extend / refine — never jump to unrelated inventions.

    Gemini often invents a short phrase on early partials ("There are"); the real
    sentence arrives later. We only accept updates that share structure with the
    previous caption, or the first non-empty result.
    """
    new = clean_stream_text(new)
    if not new:
        return old
    old = (old or "").strip()
    if not old:
        return new
    ol, nl = old.lower().strip(), new.lower().strip()
    # Extension / containment (normal streaming ASR behavior)
    if nl.startswith(ol) or ol.startswith(nl) or ol in nl or nl in ol:
        return new if len(new) >= len(old) * 0.5 else old
    # Shared word set (bilingual re-segmentation)
    ow = set(re.findall(r"[a-záéíóúüñ']+", ol, flags=re.I))
    nw = set(re.findall(r"[a-záéíóúüñ']+", nl, flags=re.I))
    if ow and nw:
        overlap = len(ow & nw) / max(1, min(len(ow), len(nw)))
        if overlap >= 0.4:
            return new if len(new) >= len(old) * 0.7 else old
    # Shared character prefix
    n = 0
    for a, b in zip(ol, nl):
        if a != b:
            break
        n += 1
    if n >= 6 or (min(len(ol), len(nl)) and n / min(len(ol), len(nl)) >= 0.5):
        return new
    # Completely different → keep old (final STT will correct on stop)
    return old


@dataclass
class StreamSession:
    backend: str = "partial"
    pcm: bytearray = field(default_factory=bytearray)
    peak_rms: float = 0.0
    interim: str = ""
    final_text: str = ""
    error: str | None = None
    _emit: Optional[Callable[[dict], Any]] = None
    _closed: bool = False
    _final_sent: bool = False
    _stop_partials: bool = False
    _partial_task: asyncio.Task | None = None
    _partial_inflight: bool = False
    _last_partial_at: float = 0.0

    def note_pcm(self, chunk: bytes) -> None:
        if not chunk:
            return
        self.pcm.extend(chunk)
        max_bytes = SAMPLE_RATE * BYTES_PER_SAMPLE * 45
        if len(self.pcm) > max_bytes:
            del self.pcm[: len(self.pcm) - max_bytes]
        r = pcm_rms(chunk)
        if r > self.peak_rms:
            self.peak_rms = r

    def has_voice(self) -> bool:
        return self.peak_rms >= MIN_PEAK_RMS

    def audio_seconds(self) -> float:
        return len(self.pcm) / float(SAMPLE_RATE * BYTES_PER_SAMPLE)

    async def emit(self, msg: dict) -> None:
        if self._emit and not self._closed:
            try:
                await self._emit(msg)
            except Exception:
                pass


async def recognize_buffer(sess: StreamSession, *, kind: str) -> tuple[str, dict]:
    """Run configured backend on current PCM buffer."""
    pcm = bytes(sess.pcm)
    backend = sess.backend
    if backend == "chirp":
        text, meta = await asyncio.to_thread(chirp_mod.transcribe_pcm, pcm, sample_rate=SAMPLE_RATE)
        text = (text or "").strip()
        # light clean — Chirp doesn't invent EMPTY tokens, but strip noise
        text = clean_stream_text(text) or text
        print(f"STT-{kind} chirp empty={not bool(text)} text={text!r} meta={meta}", flush=True)
        return text, meta

    wav = pcm_to_wav(pcm, SAMPLE_RATE)
    text, meta = await asyncio.to_thread(stt_mod.transcribe, wav, "audio/wav")
    text = clean_stream_text(text)
    print(f"STT-{kind} gemini empty={not bool(text)} text={text!r} meta={meta}", flush=True)
    return text, meta


async def finish_batch(sess: StreamSession) -> str:
    if not sess.has_voice() or sess.audio_seconds() < 0.25:
        return ""
    text, _meta = await recognize_buffer(sess, kind="final")
    sess.final_text = text or ""
    return sess.final_text


async def run_one_partial(sess: StreamSession) -> None:
    """Transcribe current buffer → interim (for live text box)."""
    if sess._stop_partials or sess._closed or sess._partial_inflight:
        return
    if not sess.has_voice() or sess.audio_seconds() < PARTIAL_MIN_AUDIO_S:
        return
    # Require sustained speech in the buffer (not one click + silence)
    stats = stt_mod.pcm_frame_stats(bytes(sess.pcm))
    if stats["speech_ratio"] < 0.12:
        return
    sess._partial_inflight = True
    try:
        text, meta = await recognize_buffer(sess, kind="interim")
        if sess._stop_partials or sess._closed:
            return
        if text:
            # Chirp interims are trustworthy — still stabilize jumps for Gemini
            if sess.backend == "chirp":
                updated = text if (not sess.interim or len(text) >= len(sess.interim) * 0.6
                                   or text.lower().startswith(sess.interim.lower()[:8])) else prefer_interim(sess.interim, text)
            else:
                updated = prefer_interim(sess.interim, text)
            if updated and updated != sess.interim:
                sess.interim = updated
                print(f"STT-interim text={updated!r} meta={meta}", flush=True)
                await sess.emit({"type": "interim", "text": updated})
    except Exception as e:
        print(f"STT-interim error: {type(e).__name__}: {e}", flush=True)
    finally:
        sess._partial_inflight = False


async def partial_loop(sess: StreamSession) -> None:
    """Periodic captions while the mic is open."""
    # Quick first attempt once we have enough audio
    while not sess._stop_partials and not sess._closed:
        try:
            await asyncio.sleep(0.35)
            if sess.has_voice() and sess.audio_seconds() >= PARTIAL_MIN_AUDIO_S:
                await run_one_partial(sess)
                break
        except asyncio.CancelledError:
            return
    while not sess._stop_partials and not sess._closed:
        try:
            await asyncio.sleep(PARTIAL_INTERVAL_S)
            await run_one_partial(sess)
        except asyncio.CancelledError:
            return
        except Exception as e:
            print(f"partial_loop: {e}", flush=True)


async def stop_partials(sess: StreamSession) -> None:
    sess._stop_partials = True
    t = sess._partial_task
    sess._partial_task = None
    if t and not t.done():
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
    # Wait out any in-flight partial so final is clean
    for _ in range(50):
        if not sess._partial_inflight:
            break
        await asyncio.sleep(0.05)


async def emit_final(
    sess: StreamSession, text: str, *, reason: str | None = None
) -> None:
    if sess._final_sent:
        return
    sess._final_sent = True
    payload: dict[str, Any] = {
        "type": "final",
        "text": text or "",
        "empty": not bool(text),
        "peak_rms": round(sess.peak_rms, 5),
        "backend": sess.backend,
        "bytes": len(sess.pcm),
    }
    if reason:
        payload["reason"] = reason
    await sess.emit(payload)


async def run_stream_session(
    messages: AsyncIterator[dict | bytes],
    emit: Callable[[dict], Any],
) -> None:
    """One WebSocket mic session: live interims + final batch."""
    backend = resolve_backend()
    # If chirp requested but not ready, fall back with a status note
    if backend == "chirp" and not chirp_mod.chirp_available():
        await emit({
            "type": "status",
            "phase": "fallback_gemini",
            "reason": "chirp_not_configured",
        })
        backend = "gemini"
    sess = StreamSession(backend=backend)
    sess._emit = emit

    await emit({
        "type": "ready",
        "backend": backend,
        "sample_rate": SAMPLE_RATE,
        "min_peak_rms": MIN_PEAK_RMS,
        "partial_interval_s": PARTIAL_INTERVAL_S,
        "final_via": backend,
        "chirp": chirp_mod.chirp_status() if backend == "chirp" else None,
    })

    try:
        async for item in messages:
            if isinstance(item, (bytes, bytearray)):
                sess.note_pcm(bytes(item))
                # Start partial loop once we have any audio
                if sess._partial_task is None and not sess._stop_partials:
                    sess._partial_task = asyncio.create_task(partial_loop(sess))
                continue

            if not isinstance(item, dict):
                continue
            typ = item.get("type")
            if typ == "start":
                await emit({
                    "type": "status",
                    "phase": "recording",
                    "backend": backend,
                })
            elif typ == "stop":
                await emit({
                    "type": "status",
                    "phase": "transcribing",
                    "backend": backend,
                })
                await stop_partials(sess)
                sess._closed = False  # still need to emit

                if not sess.has_voice():
                    await emit_final(sess, "", reason="no_voice")
                    return

                try:
                    text = await finish_batch(sess)
                    # Prefer final; only use interim if final empty AND interim
                    # is a plausible multi-word utterance
                    if not text and sess.interim:
                        cand = clean_stream_text(sess.interim)
                        if cand and len(cand.split()) >= 2:
                            text = cand
                    text = clean_stream_text(text)
                    await emit_final(sess, text)
                except Exception as e:
                    text = clean_stream_text(sess.interim)
                    if text:
                        await emit_final(
                            sess, text, reason="batch_failed_used_interim"
                        )
                    else:
                        await emit({
                            "type": "error",
                            "message": f"STT failed: {type(e).__name__}: {e}",
                        })
                        sess._final_sent = True
                return
            elif typ == "cancel":
                await stop_partials(sess)
                await emit({"type": "closed", "reason": "cancel"})
                sess._final_sent = True
                return
    except Exception as e:
        if not sess._final_sent:
            try:
                await stop_partials(sess)
                if sess.has_voice() and len(sess.pcm) > 1000:
                    sess._closed = False
                    text = clean_stream_text(await finish_batch(sess))
                    if text:
                        await emit_final(sess, text, reason="recovered")
                        return
            except Exception:
                pass
            await emit({
                "type": "error",
                "message": f"STT session error: {type(e).__name__}: {e}",
            })
            sess._final_sent = True
    finally:
        await stop_partials(sess)
        if not sess._final_sent:
            sess._closed = False
            await emit_final(sess, clean_stream_text(sess.interim), reason="session_ended")
        sess._closed = False
        await emit({"type": "closed"})
