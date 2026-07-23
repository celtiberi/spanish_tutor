"""Session-scoped student state.

The model maintains the state itself: every reply ends with a <session_state>
JSON block (see prompts/teaching_policy.md). The harness parses and strips it,
persists it, and re-injects it next turn as a mid-conversation system message
(supported on Opus 4.8; keeps the cached prefix intact).
"""

import datetime
import json
import re
from pathlib import Path

STATE_RE = re.compile(r"<session_state>\s*(\{.*?\})\s*</session_state>", re.DOTALL)
STATE_MARKER = "<session_state>"


def default_state() -> dict:
    return {
        "current_unit": None,
        "goal": None,
        "observed_misconceptions": [],
        "mastered": [],
        "struggling": [],
        "current_item_attempts": 0,
        "revisit_queue": [],
        "review_schedule": [],
    }


def load_profile(path: Path) -> dict:
    """Cross-session learner profile: last session's final state.

    Session-local fields are reset; the durable fields (misconceptions,
    mastery, review_schedule) carry over so spaced review works.
    """
    if not path.exists():
        return default_state()
    try:
        stored = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return default_state()
    state = default_state()
    for key in ("current_unit", "observed_misconceptions", "mastered",
                "struggling", "review_schedule"):
        if key in stored:
            state[key] = stored[key]
    return state


def save_profile(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def extract_state(reply: str, previous: dict) -> tuple[str, dict]:
    """Split a model reply into (visible text, updated state).

    Falls back to the previous state if the block is missing or malformed —
    a dropped state update shouldn't kill the session. Always hide from
    STATE_MARKER onward when the open tag is present, even if the close
    tag / JSON is truncated.
    """
    match = STATE_RE.search(reply)
    if match:
        visible = reply[: match.start()].strip()
        try:
            state = json.loads(match.group(1))
        except json.JSONDecodeError:
            return visible, previous
        return visible, state
    marker_at = reply.find(STATE_MARKER)
    if marker_at != -1:
        return reply[:marker_at].strip(), previous
    return reply.strip(), previous


def state_message(state: dict) -> dict:
    today = datetime.date.today().isoformat()
    return {
        "role": "system",
        "content": (
            f"Today's date: {today}.\n"
            "Learner profile / session state so far (maintained by you across "
            "turns and sessions):\n"
            + json.dumps(state, ensure_ascii=False)
        ),
    }
