"""Rolling round-history summary (P1, ENGINEERING §3.3 amendment
2026-08-06; design converged in docs/analysis-multi-model-context.md).

Live sessions run p50 19k / p90 24k input tokens because the
plan-cycle history suffix is unbounded. Once the suffix exceeds the
versioned threshold, the OLDER portion is replaced in round prompts by
a facts-only summary + the last K raw exchanges. Hard rules:

- Authored ASYNC by a cheap model AFTER the reply ships — zero added
  reply latency. This is the one sanctioned cheap-model role from the
  analysis: summarizing FACTS, never judgment.
- MUST carry verbatim learner-error spans (countersigned mandatory —
  repair continuity lives in exact wording).
- The sheet stays the sole ability authority; a summary never grades.
- Any failure ⇒ no summary ⇒ the full suffix ships exactly as before.
"""

from __future__ import annotations

import sys
import threading

from . import config

SUMMARY_MODEL = "gemini-3.5-flash-lite"

_PROMPT = """Summarize this Spanish-lesson conversation segment for the
tutor's own working memory. FACTS ONLY, max ~150 words:
- topics discussed and Spanish items the learner heard/used
- what the learner attempted and how it went (no grades, no bands)
- REQUIRED section "Learner said (verbatim):" quoting every learner
  utterance that contained an error or struggle, exactly as written
- open threads (questions asked, promises made, games played)
Do not invent, do not evaluate ability, do not address the learner.

SEGMENT:
{segment}
"""


def build_summary(messages: list[dict]) -> str | None:
    """Synchronous summary of a message list (called from the async
    worker). Returns None on any failure — callers degrade to full
    history, visibly."""
    seg = "\n".join(
        f"{'LEARNER' if m.get('role') == 'user' else 'TUTOR'}: "
        f"{(m.get('content') or '')[:600]}"
        for m in messages
    )
    if not seg.strip():
        return None
    try:
        client = config.make_client_for(SUMMARY_MODEL)
        caps = config.caps_for(SUMMARY_MODEL)
        r = client.messages.create(
            model=caps.model,
            max_tokens=400,
            system=[{"type": "text", "text": "You summarize lesson logs."}],
            messages=[{"role": "user",
                       "content": _PROMPT.format(segment=seg)}],
        )
        text = "\n".join(
            getattr(b, "text", "") for b in (r.content or [])
            if getattr(b, "type", "") == "text"
        ).strip()
        if text:
            try:
                from .costs import record_event

                u = getattr(r, "usage", None)
                record_event({
                    "category": "history_summary",
                    "model": caps.model,
                    "input_tokens": getattr(u, "input_tokens", 0),
                    "output_tokens": getattr(u, "output_tokens", 0),
                    "source": "summarizer",
                })
            except Exception:
                pass
        return text or None
    except Exception as e:
        print(f"[no-hide] history summary FAILED (full history ships): "
              f"{type(e).__name__}: {e}", file=sys.stderr, flush=True)
        return None


def maybe_update_async(session) -> None:
    """After a turn: if the plan-cycle suffix is long enough, refresh
    the session's rolling summary in a daemon thread. Single writer
    (the session's own turns are serialized), readers tolerate stale."""
    if not getattr(config, "HISTORY_SUMMARY_ENABLED", True):
        return
    from .session_plan import (
        ROUND_SUMMARY_KEEP_EXCHANGES,
        ROUND_SUMMARY_THRESHOLD_MSGS,
    )

    start = max(0, int(getattr(session, "plan_cycle_start", 0) or 0))
    suffix = session.history[start:]
    if len(suffix) <= ROUND_SUMMARY_THRESHOLD_MSGS:
        return
    keep_msgs = ROUND_SUMMARY_KEEP_EXCHANGES * 2
    covers_abs = start + len(suffix) - keep_msgs  # summarize up to here
    cur = getattr(session, "history_summary", None)
    if cur and cur.get("covers", -1) >= covers_abs:
        return  # already current

    to_summarize = session.history[start:covers_abs]

    def _work() -> None:
        text = build_summary(to_summarize)
        if text:
            session.history_summary = {"text": text, "covers": covers_abs}

    threading.Thread(target=_work, name="history-summary",
                     daemon=True).start()
