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
SESSION_TTL_SEC = 60 * 60 * 8  # 8h (cookie max_age)
# Orphan reaper (2026-07-28 reset-race forensics: session 20260728-120331
# leaked with no session_end): any session with no activity for 2h is
# close()d — writing its session_end — and dropped.
IDLE_REAP_SEC = 60 * 60 * 2  # 2h

# Stale-process detection: a long-lived `python -m tutor.web_app` keeps OLD
# code no matter what lands on disk (2026-07-28 incident: a July-26 process
# silently ignored two days of fixes). /api/health compares disk mtimes to
# process start so the UI can tell the operator to restart.
_PROC_STARTED = time.time()


def _newest_code_mtime() -> float:
    newest = 0.0
    root = Path(__file__).resolve().parent
    for p in list(root.glob("*.py")) + list((root / "web_static").glob("*")):
        try:
            newest = max(newest, p.stat().st_mtime)
        except OSError:
            continue
    return newest


def _stamp(mtime: float) -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.localtime(mtime)) if mtime else "?"


# Version of the code THIS process runs = newest file at import. Auto-derived
# (manual version bumps rot — see the ?v= incident). Shown in the web header.
CODE_VERSION = _stamp(_newest_code_mtime())

_lock = threading.Lock()
_sessions: dict[str, dict[str, Any]] = {}


# Single source of truth for learner-message length: API validation and the
# web composer's maxlength (served via /api/health). Abuse protection only,
# never a composition limit (~2000 words).
CHAT_MAX_CHARS = 12000


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=CHAT_MAX_CHARS)
    input_mode: str = Field(default="text", pattern="^(text|speech)$")


class StartIn(BaseModel):
    """Page load always wants a clean chat unless resume=true (rare)."""
    fresh: bool = True
    resume: bool = False


class ResetIn(BaseModel):
    # Spanish progress (ability sheet) and personal data (learner profile)
    # have separate lifecycles: reset one without losing the other.
    reset_sheet: bool = False
    clear_personal: bool = False


class SpeakIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    # Optional playback-rate hint (0.7–1.2). Defaults to config.TTS_RATE.
    # Gemini has no numeric rate API field; drives the slow-style prefix
    # (only at rate <= 0.8) + response header.
    rate: float | None = Field(default=None, ge=0.7, le=1.2)


def _close_meta(meta: dict, *, persist_sheet: bool = True) -> None:
    """Close one session meta record (session_end written; never raises —
    but a failed close is VISIBLE: no-hide, full-code-audit S5.4)."""
    sess: ConversationalSession | None = (meta or {}).get("session")
    if sess:
        try:
            sess.close(persist_sheet=persist_sheet)
        except Exception as e:
            import sys
            import traceback

            print(
                f"[no-hide] session close failed (sheet may be "
                f"unpersisted): {type(e).__name__}: {e}",
                file=sys.stderr, flush=True,
            )
            traceback.print_exc()


def _purge_stale() -> None:
    """Reap idle sessions: no activity for IDLE_REAP_SEC → close (writes
    session_end IF the session ever logged a learner turn — open-only
    probe sessions leave zero files, full-code-audit S8) and drop.
    Guard against orphan leaks (2026-07-28)."""
    now = time.time()
    dead = [
        sid for sid, meta in _sessions.items()
        if now - meta.get("touched", 0) > IDLE_REAP_SEC
    ]
    for sid in dead:
        _close_meta(_sessions.pop(sid))


def _reap_all_locked(*, persist_sheet: bool = True) -> int:
    """Close and drop EVERY live session (assumes _lock held). Used when a
    new session replaces all previous ones (reset / dead cookie): a local
    single-user app has one browser cookie jar, so sessions the cookie no
    longer points at are unreachable orphans that would otherwise leak
    without a session_end (2026-07-28: session 20260728-120331)."""
    n = 0
    for sid in list(_sessions):
        _close_meta(_sessions.pop(sid), persist_sheet=persist_sheet)
        n += 1
    return n


def _get_or_create(sid: str | None, *, model: str | None = None) -> tuple[str, ConversationalSession]:
    with _lock:
        _purge_stale()
        if sid and sid in _sessions:
            _sessions[sid]["touched"] = time.time()
            return sid, _sessions[sid]["session"]
        if sid:
            # Dead cookie (2026-07-28 reset race): the browser's sid points
            # nowhere, so every remaining session is an unreachable orphan —
            # close them (session_end) before creating the replacement.
            _reap_all_locked()
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
    # Teach images: generate-on-miss via Gemini when key is present
    try:
        from .image_gen import install_teach_image_generator

        install_teach_image_generator()
    except Exception as e:
        print(f"teach image generator not installed: {type(e).__name__}: {e}", flush=True)

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
        # Avoid sticky HTML so script/css ?v= busts always take effect
        return FileResponse(
            index_path,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
            },
        )

    @app.get("/api/health")
    def health():
        teach_cache = {}
        try:
            from .teach_assets import cache_stats, seed_index_from_disk

            seed_index_from_disk()
            teach_cache = cache_stats()
        except Exception as e:
            teach_cache = {"error": f"{type(e).__name__}: {e}"}
        try:
            from .image_gen import image_gen_enabled, image_model

            teach_cache["generate_enabled"] = image_gen_enabled()
            teach_cache["image_model"] = image_model()
        except Exception:
            pass
        newest = _newest_code_mtime()
        return {
            "ok": True,
            "model": config.MODEL,
            "teacher_mode": getattr(config, "TEACHER_MODE", "planned"),
            # plan = two-phase (model-authored session plan, §3.3 amendment)
            "teacher_context": getattr(config, "TEACHER_CONTEXT", "plan"),
            "teach_image_cache": teach_cache,
            "pack": config.DEFAULT_PACK_DIR.name,
            "chat_max_chars": CHAT_MAX_CHARS,
            "process_started": _PROC_STARTED,
            "code_newest_mtime": newest,
            # Running version vs what's on disk right now
            "version": CODE_VERSION,
            "disk_version": _stamp(newest),
            # True = files on disk are newer than this process: RESTART needed
            "stale_code": bool(newest > _PROC_STARTED + 1.0),
            "tts": {
                "enabled": tts_mod.tts_enabled(),
                "model": tts_mod.tts_model(),
                "voice": tts_mod.tts_voice(),
                # rate = server default (now 1.0); slower_rate kept for
                # compat readers — the client Voice slider owns the speed.
                "rate": float(getattr(config, "TTS_RATE", 1.0)),
                "slower_rate": float(getattr(config, "TTS_SLOWER_RATE", 0.8)),
                "model_try_gap_ms": int(getattr(config, "TTS_MODEL_TRY_GAP_MS", 400)),
                # Gemini TTS path has no numeric speakingRate (client playbackRate)
                "api_numeric_rate": False,
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

    def _session_costs(request: Request):
        """Cost tracker for the caller's session; ledger-only fallback if none."""
        sid = request.cookies.get(COOKIE)
        if sid and sid in _sessions:
            sess = _sessions[sid].get("session")
            if sess is not None and getattr(sess, "costs", None) is not None:
                return sess.costs
        from .costs import SessionCostTracker

        return SessionCostTracker(source="web-nosession")

    @app.post("/api/audio/speak")
    def audio_speak(body: SpeakIn, request: Request):
        """Neural TTS (Gemini). Returns audio/wav bytes.

        Optional body.rate (0.7–1.2) drives a short slow-style prefix only
        when rate <= 0.8. API gap: Gemini generateContent TTS has no numeric
        speakingRate; clients also set HTMLAudioElement.playbackRate.
        """
        rate = body.rate
        if rate is None:
            rate = float(getattr(config, "TTS_RATE", 1.0))
        rate = max(0.7, min(1.2, float(rate)))
        try:
            audio, mime, meta = tts_mod.synthesize(body.text, rate=rate)
        except Exception as e:
            print(f"TTS failed: {type(e).__name__}: {e}", flush=True)
            raise HTTPException(
                status_code=502,
                detail=f"TTS failed: {type(e).__name__}: {e}",
            ) from e
        print(
            f"TTS ok model={meta.get('model')} voice={meta.get('voice')} "
            f"rate={meta.get('rate')} style_slow={meta.get('style_slow')} "
            f"bytes={len(audio)} chars={meta.get('chars')}",
            flush=True,
        )
        u = meta.get("usage") or {}
        _session_costs(request).add_llm(
            "tts",
            str(meta.get("model") or ""),
            input_tokens=u.get("input_tokens", 0),
            output_tokens=u.get("output_tokens", 0),
        )
        return PlainResponse(
            content=audio,
            media_type=mime or "audio/wav",
            headers={
                "X-TTS-Provider": str(meta.get("provider") or ""),
                "X-TTS-Voice": str(meta.get("voice") or ""),
                "X-TTS-Model": str(meta.get("model") or ""),
                "X-TTS-Rate": str(meta.get("rate") if meta.get("rate") is not None else rate),
                "X-TTS-Api-Numeric-Rate": "0",
                "Cache-Control": "no-store",
            },
        )

    @app.post("/api/audio/transcribe")
    async def audio_transcribe(
        request: Request,
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
        u = meta.get("usage") or {}
        _session_costs(request).add_llm(
            "stt",
            str(meta.get("model") or ""),
            input_tokens=u.get("input_tokens", 0),
            output_tokens=u.get("output_tokens", 0),
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
    def session_start(
        request: Request,
        response: Response,
        body: StartIn | None = None,
    ):
        body = body or StartIn()
        # Default: every page load is a clean chat (Ctrl/Cmd+Shift+R expectation).
        # Only resume when client explicitly sends resume=true.
        want_fresh = body.fresh or not body.resume
        sid = request.cookies.get(COOKIE)

        if want_fresh:
            if sid and sid in _sessions:
                with _lock:
                    old = _sessions.pop(sid, None)
                if old and old.get("session"):
                    try:
                        # Keep character sheet; only drop chat memory
                        old["session"].close(persist_sheet=True)
                    except Exception as e:
                        import sys
                        import traceback

                        print(
                            f"[no-hide] session close failed (sheet may be "
                            f"unpersisted): {type(e).__name__}: {e}",
                            file=sys.stderr, flush=True,
                        )
                        traceback.print_exc()
            sid = None

        sid, session = _get_or_create(sid)

        # Always re-read sheet from disk so a manual file wipe shows up
        try:
            from .character_sheet import (
                clear_session_scoped_affect,
                load_sheet,
            )
            session.sheet = clear_session_scoped_affect(
                load_sheet(session.sheet_path)
            )
        except Exception:
            pass

        # Always open a new tutor turn on page load. Both branches route
        # through the unified new-chat reset inside open_session() (Phase 1
        # batch 2, SessionState.reset("new_chat")): transcript, focus
        # fields, session memory, mode state, debug ring and the
        # per-chat cost tracker all reset there — no inline partial clears
        # (the batch-1 census leak).
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
            "fresh": True,
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
        _t0 = time.perf_counter()
        turn = session.user_turn(body.message, input_mode=body.input_mode)
        _server_ms = int((time.perf_counter() - _t0) * 1000)
        if turn.error:
            raise HTTPException(status_code=502, detail=turn.error)
        response.set_cookie(
            COOKIE, sid, httponly=True, samesite="lax", max_age=SESSION_TTL_SEC,
        )
        return {
            **turn.to_dict(),
            "server_ms": _server_ms,
            "messages": session.messages_for_ui,
            "sheet": session.sheet_public(),
        }

    @app.get("/api/sheet")
    def get_sheet(request: Request):
        sid = request.cookies.get(COOKIE)
        _, session, _ = _require(sid)
        return session.sheet_public()

    @app.get("/api/progress")
    def get_progress(request: Request):
        """Grade feed (Phase 3, 2026-07-31): teacher tool ability grades with
        why + header counts from the sheet. Replaces Journey milestones as
        the learner-visible progress surface."""
        sid = request.cookies.get(COOKIE)
        _, session, _ = _require(sid)
        from .grade_log import build_grades_payload

        return build_grades_payload(
            session.sheet,
            session_id=getattr(session, "progress_session_id", ""),
        )

    @app.get("/api/debug/requests")
    def debug_requests(request: Request):
        """Debug box (local app, no auth): the current session's last
        outbound tutor requests + responses, NEWEST FIRST, from the
        in-memory ring buffer.  The same entries are mirrored to
        logs/sessions/<YYYY-MM-DD>/<session_id>.requests.jsonl (model
        traffic log; files appear once the session has a learner turn).
        No session → empty list (valid JSON always)."""
        sid = request.cookies.get(COOKIE)
        if not sid or sid not in _sessions:
            return {"entries": [], "count": 0, "session": False}
        with _lock:
            meta = _sessions.get(sid)
            if not meta:
                return {"entries": [], "count": 0, "session": False}
            meta["touched"] = time.time()
            session = meta["session"]
        entries = list(getattr(session, "debug_requests", None) or [])
        entries.reverse()  # newest first
        return {
            "entries": entries,
            "count": len(entries),
            "session": True,
            "ring_size": len(entries),
        }

    @app.post("/api/session/reset")
    def reset(body: ResetIn, request: Request, response: Response):
        sid = request.cookies.get(COOKIE)
        # FULL REPLACE (2026-07-28 reset-race forensics): reset closes the
        # cookie's session AND every other live session (all become
        # unreachable once the new sid cookie is set), so nothing can leak
        # without a session_end. Then one new session is created and opened.
        old_sid = sid
        old_sheet_path = None
        with _lock:
            old = _sessions.pop(old_sid, None) if old_sid else None
            orphans = [_sessions.pop(k) for k in list(_sessions)]
        if old and old.get("session"):
            try:
                old_sheet_path = getattr(old["session"], "sheet_path", None)
                # On reset_sheet: close WITHOUT persisting (no stale re-save
                # possible); the disk wipe rides the nuclear-wipe block
                # below and the NEW session's reset_sheet() below appends
                # the single learner-epoch mark (Phase 1 batch 2 — calling
                # the old session's reset_sheet here would double-mark).
                old["session"].close(persist_sheet=not body.reset_sheet)
            except Exception as e:
                import sys
                import traceback

                print(
                    f"[no-hide] session close failed (sheet may be "
                    f"unpersisted): {type(e).__name__}: {e}",
                    file=sys.stderr, flush=True,
                )
                traceback.print_exc()
        for meta in orphans:
            _close_meta(meta, persist_sheet=True)
        # Nuclear wipe even if no live session (stale cookie / cold start)
        if body.reset_sheet:
            from .conv_session import DEFAULT_SHEET_PATH
            from .character_sheet import default_sheet, save_sheet

            path = Path(old_sheet_path or DEFAULT_SHEET_PATH)
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass
            path.parent.mkdir(parents=True, exist_ok=True)
            save_sheet(path, default_sheet())

        sid, session = _get_or_create(None)
        if body.reset_sheet:
            session.reset_sheet()
        if body.clear_personal:
            session.reset_profile()
        turn = session.open_session()
        if turn.error:
            raise HTTPException(status_code=502, detail=turn.error)
        with _lock:
            _sessions[sid]["opened"] = True
        response.set_cookie(
            COOKIE, sid, httponly=True, samesite="lax", max_age=SESSION_TTL_SEC,
        )
        sheet_pub = session.sheet_public()
        return {
            **turn.to_dict(),
            "messages": session.messages_for_ui,
            "sheet": sheet_pub,
            "session_id": sid,
            "sheet_reset": body.reset_sheet,
            "personal_cleared": body.clear_personal,
            "fresh_learner": bool(body.reset_sheet),
        }

    return app


app = create_app()


def main() -> None:
    import uvicorn

    host = "127.0.0.1"
    port = int(__import__("os").environ.get("PORT", "8765"))
    print(f"ml_teacher web → http://{host}:{port}")
    print(
        f"  tutor={config.MODEL}  pack={config.DEFAULT_PACK_DIR.name}"
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
