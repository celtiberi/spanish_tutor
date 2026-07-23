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
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    lines = [
        f"Today's date: {today}. Tomorrow: {tomorrow}.",
        "Learner profile / session state so far (maintained by you across "
        "turns and sessions):",
        json.dumps(state, ensure_ascii=False),
    ]
    from . import config
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
    lines.append(
        "Reminder (harness contract): end this reply with the trailing "
        "<session_state> block — every turn, even short ones. "
        "Bookkeeping: a failed due-review item gets due = tomorrow's date "
        "(given above) and successes = 0; log the matching M-x.y ID in "
        "observed_misconceptions AND on its schedule entry whenever you "
        "diagnose an error. Credit production only after a Spanish echo of "
        "the target form. "
        "Style: at most ONE emoji. One production deliverable per prompt — "
        "never two asks in one ('greet AND ask how they are'). "
        "In roleplay tasks: stay in Spanish, in character; fix errors with "
        "in-character recasts — English feedback only after the closing, "
        "which you must elicit."
    )
    content = "\n".join(lines)
    if config.SUPPORTS_MID_SYSTEM:
        return {"role": "system", "content": content}
    # Fallback for models without mid-conversation system messages: a
    # clearly-framed harness message in a user turn (not learner text).
    return {
        "role": "user",
        "content": "<harness_context>\n(This is from the tutoring system, "
                   "not the learner.)\n" + content + "\n</harness_context>",
    }
