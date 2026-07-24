"""Web UI for conversational Spanish tutor.

  python -m tutor.web_app
  # → http://127.0.0.1:8765

Shared engine: tutor.conv_session.ConversationalSession
Audio: browser Web Speech (mic + TTS) for now; server STT/TTS later.
"""

from __future__ import annotations

import asyncio
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, HTMLResponse, Response as PlainResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config
from .conv_session import ConversationalSession
from . import stt as stt_mod
from . import stt_chirp as stt_chirp_mod
from . import stt_stream as stt_stream_mod
from . import tts as tts_mod

STATIC_DIR = Path(__file__).resolve().parent / "web_static"
COOKIE = "ml_teacher_sid"
SESSION_TTL_SEC = 60 * 60 * 8  # 8h

_lock = threading.Lock()
_sessions: dict[str, dict[str, Any]] = {}


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    input_mode: str = Field(default="text", pattern="^(text|speech)$")


class ResetIn(BaseModel):
    reset_sheet: bool = False


class SpeakIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)


def _purge_stale() -> None:
    now = time.time()
    dead = [
        sid for sid, meta in _sessions.items()
        if now - meta.get("touched", 0) > SESSION_TTL_SEC
    ]
    for sid in dead:
        sess: ConversationalSession | None = _sessions[sid].get("session")
        if sess:
            try:
                sess.close()
            except Exception:
                pass
        del _sessions[sid]


def _get_or_create(sid: str | None, *, model: str | None = None) -> tuple[str, ConversationalSession]:
    with _lock:
        _purge_stale()
        if sid and sid in _sessions:
            _sessions[sid]["touched"] = time.time()
            return sid, _sessions[sid]["session"]
        new_id = secrets.token_urlsafe(16)
        session = ConversationalSession(
            model=model or config.MODEL,
            label="web",
        )
        _sessions[new_id] = {
            "session": session,
            "touched": time.time(),
            "opened": False,
        }
        return new_id, session


def _require(sid: str | None) -> tuple[str, ConversationalSession, dict]:
    with _lock:
        _purge_stale()
        if not sid or sid not in _sessions:
            raise HTTPException(status_code=404, detail="No active session — refresh the page.")
        meta = _sessions[sid]
        meta["touched"] = time.time()
        return sid, meta["session"], meta


def create_app() -> FastAPI:
    config.load_env()
    app = FastAPI(title="ml_teacher conversational", version="0.2.0")

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index():
        index_path = STATIC_DIR / "index.html"
        if not index_path.exists():
            return HTMLResponse(
                "<h1>ml_teacher</h1><p>Missing web_static/index.html</p>",
                status_code=500,
            )
        return FileResponse(index_path)

    @app.get("/api/health")
    def health():
        return {
            "ok": True,
            "model": config.MODEL,
            "pack": config.DEFAULT_PACK_DIR.name,
            "tts": {
                "enabled": tts_mod.tts_enabled(),
                "model": tts_mod.tts_model(),
                "voice": tts_mod.tts_voice(),
            },
            "stt": {
                "enabled": stt_mod.stt_enabled(),
                "model": stt_mod.stt_model(),
                "stream": stt_stream_mod.stream_enabled(),
                "stream_backend": stt_stream_mod.stream_backend(),
                "live_model": stt_stream_mod.live_model(),
                "sample_rate": stt_stream_mod.SAMPLE_RATE,
                "chirp": stt_chirp_mod.chirp_status(),
            },
        }

    @app.post("/api/audio/speak")
    def audio_speak(body: SpeakIn):
        """Neural TTS (Gemini). Returns audio/wav bytes."""
        try:
            audio, mime, meta = tts_mod.synthesize(body.text)
        except Exception as e:
            print(f"TTS failed: {type(e).__name__}: {e}", flush=True)
            raise HTTPException(
                status_code=502,
                detail=f"TTS failed: {type(e).__name__}: {e}",
            ) from e
        print(
            f"TTS ok model={meta.get('model')} voice={meta.get('voice')} "
            f"bytes={len(audio)} chars={meta.get('chars')}",
            flush=True,
        )
        return PlainResponse(
            content=audio,
            media_type=mime or "audio/wav",
            headers={
                "X-TTS-Provider": str(meta.get("provider") or ""),
                "X-TTS-Voice": str(meta.get("voice") or ""),
                "X-TTS-Model": str(meta.get("model") or ""),
                "Cache-Control": "no-store",
            },
        )

    @app.post("/api/audio/transcribe")
    async def audio_transcribe(
        file: UploadFile = File(...),
    ):
        """Server STT (Gemini audio understanding). Avoids Chrome Web Speech network errors."""
        raw = await file.read()
        mime = file.content_type or ""
        name = (file.filename or "").lower()
        if not mime or mime == "application/octet-stream":
            if name.endswith(".wav"):
                mime = "audio/wav"
            elif name.endswith(".mp4") or name.endswith(".m4a"):
                mime = "audio/mp4"
            elif name.endswith(".ogg"):
                mime = "audio/ogg"
            else:
                mime = "audio/webm"
        if len(raw) > 12_000_000:
            raise HTTPException(status_code=413, detail="Audio too large (max ~12MB)")
        try:
            text, meta = stt_mod.transcribe(raw, mime_type=mime)
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"STT failed: {type(e).__name__}: {e}",
            ) from e
        # Helpful console breadcrumb when debugging phantom Spanish
        print(
            f"STT bytes={len(raw)} mime={mime} empty={not bool(text)} "
            f"text={text!r} meta={meta}",
            flush=True,
        )
        return {
            "text": text,
            "meta": meta,
            "empty": not bool(text),
        }

    @app.websocket("/ws/stt")
    async def ws_stt(websocket: WebSocket):
        """Streaming mic STT: PCM s16le 16kHz in, interim/final JSON out.

        See tutor.stt_stream for protocol. Falls back to batch Gemini STT
        when Live is unavailable.
        """
        if not stt_stream_mod.stream_enabled() or not stt_mod.stt_enabled():
            await websocket.close(code=1008, reason="STT stream disabled")
            return
        await websocket.accept()

        async def emit(msg: dict) -> None:
            try:
                await websocket.send_json(msg)
            except Exception:
                pass

        async def client_messages():
            try:
                while True:
                    message = await websocket.receive()
                    if message.get("type") == "websocket.disconnect":
                        break
                    if "bytes" in message and message["bytes"] is not None:
                        yield message["bytes"]
                    elif "text" in message and message["text"] is not None:
                        import json

                        try:
                            yield json.loads(message["text"])
                        except json.JSONDecodeError:
                            yield {"type": "error_in", "raw": message["text"][:80]}
            except WebSocketDisconnect:
                return

        try:
            await stt_stream_mod.run_stream_session(client_messages(), emit)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"ws/stt error: {type(e).__name__}: {e}", flush=True)
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": f"{type(e).__name__}: {e}",
                })
            except Exception:
                pass
        finally:
            # Give the browser a beat to read the last frame before close
            try:
                await asyncio.sleep(0.05)
            except Exception:
                pass
            try:
                await websocket.close()
            except Exception:
                pass

    @app.post("/api/session/start")
    def session_start(request: Request, response: Response):
        sid = request.cookies.get(COOKIE)
        sid, session = _get_or_create(sid)
        with _lock:
            meta = _sessions[sid]
            already = meta.get("opened")
        if already and session.messages_for_ui:
            # Resume existing browser session
            result = {
                "reply": session.messages_for_ui[-1]["content"]
                if session.messages_for_ui else "",
                "notes": [],
                "next_best": session.sheet.get("next_best"),
                "skills": {
                    k: {"status": v.get("status"), "confidence": v.get("confidence")}
                    for k, v in (session.sheet.get("skills") or {}).items()
                },
                "messages": session.messages_for_ui,
                "sheet": session.sheet_public(),
                "resumed": True,
            }
        else:
            turn = session.open_session()
            if turn.error:
                raise HTTPException(status_code=502, detail=turn.error)
            with _lock:
                _sessions[sid]["opened"] = True
            result = {
                **turn.to_dict(),
                "messages": session.messages_for_ui,
                "sheet": session.sheet_public(),
                "resumed": False,
            }
        response.set_cookie(
            COOKIE, sid, httponly=True, samesite="lax", max_age=SESSION_TTL_SEC,
        )
        result["session_id"] = sid
        result["model"] = session.model
        return result

    @app.post("/api/chat")
    def chat(body: ChatIn, request: Request, response: Response):
        sid = request.cookies.get(COOKIE)
        sid, session, meta = _require(sid)
        if not meta.get("opened"):
            # Auto-open if needed
            open_turn = session.open_session()
            if open_turn.error:
                raise HTTPException(status_code=502, detail=open_turn.error)
            with _lock:
                meta["opened"] = True
        turn = session.user_turn(body.message, input_mode=body.input_mode)
        if turn.error:
            raise HTTPException(status_code=502, detail=turn.error)
        response.set_cookie(
            COOKIE, sid, httponly=True, samesite="lax", max_age=SESSION_TTL_SEC,
        )
        return {
            **turn.to_dict(),
            "messages": session.messages_for_ui,
            "sheet": session.sheet_public(),
        }

    @app.get("/api/sheet")
    def get_sheet(request: Request):
        sid = request.cookies.get(COOKIE)
        _, session, _ = _require(sid)
        return session.sheet_public()

    @app.post("/api/session/reset")
    def reset(body: ResetIn, request: Request, response: Response):
        sid = request.cookies.get(COOKIE)
        # New session id; optionally wipe character sheet
        old_sid = sid
        if old_sid and old_sid in _sessions:
            with _lock:
                old = _sessions.pop(old_sid, None)
            if old and old.get("session"):
                try:
                    if body.reset_sheet:
                        old["session"].reset_sheet()
                    old["session"].close()
                except Exception:
                    pass
        sid, session = _get_or_create(None)
        if body.reset_sheet:
            session.reset_sheet()
        turn = session.open_session()
        if turn.error:
            raise HTTPException(status_code=502, detail=turn.error)
        with _lock:
            _sessions[sid]["opened"] = True
        response.set_cookie(
            COOKIE, sid, httponly=True, samesite="lax", max_age=SESSION_TTL_SEC,
        )
        return {
            **turn.to_dict(),
            "messages": session.messages_for_ui,
            "sheet": session.sheet_public(),
            "session_id": sid,
            "sheet_reset": body.reset_sheet,
        }

    return app


app = create_app()


def main() -> None:
    import uvicorn

    host = "127.0.0.1"
    port = int(__import__("os").environ.get("PORT", "8765"))
    print(f"ml_teacher web → http://{host}:{port}")
    print(
        f"  tutor={config.MODEL}  focus={config.FOCUS_MODEL}  "
        f"pack={config.DEFAULT_PACK_DIR.name}"
    )
    if tts_mod.tts_enabled():
        print(
            f"  tts={tts_mod.tts_model()} voice={tts_mod.tts_voice()} "
            f"(browser fallback if TTS fails)"
        )
    else:
        print("  tts=browser only (TTS_ENABLED=off)")
    if stt_mod.stt_enabled():
        be = stt_stream_mod.stream_backend()
        from . import stt_chirp as _chirp

        chirp_ok = _chirp.chirp_available()
        print(
            f"  stt_backend={be}  gemini_model={stt_mod.stt_model()}  "
            f"chirp_ready={chirp_ok}  (ws /ws/stt)"
        )
        if be == "gemini" and not chirp_ok:
            print(
                "  → for dedicated ASR: see docs/asr-chirp-setup.md "
                "(STT_BACKEND=chirp + GCP credentials)"
            )
    else:
        print("  stt=disabled")
    uvicorn.run(
        "tutor.web_app:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
