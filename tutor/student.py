"""Session-scoped student state.

The model maintains the state itself: every reply ends with a <session_state>
JSON block (see prompts/teaching_policy.md). The harness parses and strips it,
persists it, and re-injects it next turn as a mid-conversation system message
(supported on Opus 4.8; keeps the cached prefix intact).
"""

import json
import re

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
    }


def extract_state(reply: str, previous: dict) -> tuple[str, dict]:
    """Split a model reply into (visible text, updated state).

    Falls back to the previous state if the block is missing or malformed —
    a dropped state update shouldn't kill the session.
    """
    match = STATE_RE.search(reply)
    if not match:
        return reply.strip(), previous
    visible = reply[: match.start()].strip()
    try:
        state = json.loads(match.group(1))
    except json.JSONDecodeError:
        return visible, previous
    return visible, state


def state_message(state: dict) -> dict:
    return {
        "role": "system",
        "content": (
            "Session state so far (maintained by you in earlier turns):\n"
            + json.dumps(state, ensure_ascii=False)
        ),
    }
