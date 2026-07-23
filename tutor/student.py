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
    """Cross-session learner profile: last session's final durable state.

    Durable (carried): current_unit, observed_misconceptions, mastered,
    struggling, review_schedule. Session-local (reset): goal,
    current_item_attempts, revisit_queue.
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


def extract_state(reply: str, previous: dict) -> tuple[str, dict, bool]:
    """Split a model reply into (visible text, updated state, parse_ok).

    Falls back to the previous state (parse_ok=False) if the block is missing
    or malformed — a dropped state update shouldn't kill the session, but the
    harness tells the model next turn so it can re-emit. Always hide from
    STATE_MARKER onward when the open tag is present, even if the close
    tag / JSON is truncated.
    """
    match = STATE_RE.search(reply)
    if match:
        visible = reply[: match.start()].strip()
        try:
            state = json.loads(match.group(1))
        except json.JSONDecodeError:
            return visible, previous, False
        return visible, state, True
    marker_at = reply.find(STATE_MARKER)
    if marker_at != -1:
        return reply[:marker_at].strip(), previous, False
    return reply.strip(), previous, False


def state_message(state: dict, parse_failed: bool = False,
                  session_open: bool = False) -> dict:
    today = datetime.date.today().isoformat()
    lines = [
        f"Today's date: {today}.",
        "Learner profile / session state so far (maintained by you across "
        "turns and sessions):",
        json.dumps(state, ensure_ascii=False),
    ]
    if parse_failed:
        lines.append(
            "Previous turn state parse failed; re-emit full state from evidence."
        )
    if session_open and any(
        item.get("due", "9999") <= today
        for item in state.get("review_schedule", [])
        if isinstance(item, dict)
    ):
        lines.append("Open with due-item warm-up before new material.")
    return {"role": "system", "content": "\n".join(lines)}
