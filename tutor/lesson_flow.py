"""Harness-owned lesson flow for the controller path.

Goals:
  - Feel like a conversation, not a worksheet.
  - Advance when the learner *knows the material* — don't grind spelling.
  - Keep a light arc (input → meaning → use it) without robotic phase locks.
"""

from __future__ import annotations

import datetime
import json
import re
import unicodedata
from typing import Any

PHASES = (
    "review",
    "input",
    "comprehension",
    "structured_input",
    "production",
    "task",
)

# Slightly looser than before — conversation can move when learner is ready.
ALLOWED_MOVES: dict[str, frozenset[str]] = {
    "review": frozenset({
        "elicit_production", "probe", "hint", "remediate", "model_form",
        "teach_answer", "passthrough", "comprehension_check", "recap_and_space",
        "present_input",
    }),
    "input": frozenset({
        "present_input", "comprehension_check", "passthrough",
    }),
    "comprehension": frozenset({
        "comprehension_check", "present_input", "structured_input",
        "elicit_production",  # if they already show understanding, use it
        "passthrough", "recap_and_space",
    }),
    "structured_input": frozenset({
        "structured_input", "comprehension_check", "model_form",
        "elicit_production", "present_input", "passthrough",
    }),
    "production": frozenset({
        "elicit_production", "remediate", "hint", "probe", "model_form",
        "teach_answer", "nudge_then_offer", "recap_and_space", "close",
        "passthrough", "answer_key_item", "present_input",
    }),
    "task": frozenset({
        "elicit_production", "remediate", "hint", "probe", "model_form",
        "recap_and_space", "close", "passthrough", "teach_answer",
        "present_input", "nudge_then_offer",
    }),
}

ADVANCE_ON_MOVE: dict[str, str] = {
    "present_input": "comprehension",
    "comprehension_check": "structured_input",
    "structured_input": "production",
}

_ID_IN_TEXT = re.compile(r"\b([MCPST]-\d+(?:\.\d+)?|SI-\d+(?:\.\d+)?)\b")

# Accents / punctuation that shouldn't block progress when the form is clear.
_SURFACE_NOISE = re.compile(r"[\u0300-\u036f]|[¿¡\?\.!,;:\"']+")


def ensure_flow_fields(state: dict) -> dict:
    s = dict(state or {})
    if "lesson_phase" not in s or s["lesson_phase"] not in PHASES:
        s["lesson_phase"] = "input"
    if "lesson_goal" not in s:
        s["lesson_goal"] = s.get("goal")
    s.setdefault("consecutive_successes", 0)
    s.setdefault("same_target_retries", 0)
    s.setdefault("last_focus_ref", None)
    s.setdefault("last_move", None)
    return s


def due_items(state: dict, today: str | None = None) -> list[dict]:
    today = today or datetime.date.today().isoformat()
    out = []
    for item in state.get("review_schedule") or []:
        if isinstance(item, dict) and item.get("due", "9999") <= today:
            out.append(item)
    return out


def _pack_id_from_review_item(item: dict) -> str:
    blob = " ".join(str(item.get(k, "")) for k in ("item", "misconception", "id"))
    m = _ID_IN_TEXT.search(blob)
    return m.group(1) if m else ""


def fold_spanish(s: str) -> str:
    """Lowercase + strip accents/punct for 'good enough' matching."""
    s = (s or "").lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = _SURFACE_NOISE.sub("", s)
    s = re.sub(r"\s+", " ", s)
    return s


def classify_learner_issue(learner: str, expected_hints: list[str] | None = None) -> str:
    """Return: ok | surface | conceptual | unclear.

    surface = accents, missing ¿, minor spelling (uested/usted), spacing
    conceptual = wrong form/register that changes meaning (estas vs esta usted)
    """
    raw = (learner or "").strip()
    if not raw:
        return "unclear"
    folded = fold_spanish(raw)

    # Pure meta / English
    if re.search(r"[a-z]{4,}", raw) and not re.search(
            r"\b(hola|buenos|buenas|como|estoy|esta|estas|usted|llamo|gracias|senor|senora)\b",
            folded):
        if re.search(r"\b(what|why|how|should|we|doing|better|way)\b", raw.lower()):
            return "meta"

    # Register mismatch is conceptual even if the rest is close
    if re.search(r"\b(senora|senor|usted|profesor|maestr|boss|teacher)\b", folded):
        if re.search(r"\b(como estas|te llamas|y tu)\b", folded) and not re.search(
                r"\b(como esta|se llama|usted)\b", folded):
            return "conceptual"

    # If expected phrases provided, compare folded
    if expected_hints:
        for exp in expected_hints:
            ef = fold_spanish(exp)
            if not ef:
                continue
            # formal expected, informal produced
            if "usted" in ef and "estas" in folded and "usted" not in folded:
                return "conceptual"
            if ef == folded:
                if fold_spanish(raw) == fold_spanish(exp) and raw.lower() != exp.lower():
                    return "surface"  # accents/punct only
                return "ok"
            if ef in folded or folded in ef:
                # substring match after fold
                if "uested" in folded or "usteed" in folded:
                    return "surface"
                return "ok"
            # tiny edit distance after fold → surface
            if abs(len(folded) - len(ef)) <= 2:
                mismatches = sum(1 for a, b in zip(folded, ef) if a != b)
                mismatches += abs(len(folded) - len(ef))
                if mismatches <= 2:
                    return "surface"
            if "uested" in folded or "usteed" in folded:
                return "surface"

    # Heuristics without gold
    if re.search(r"\buested\b|\busteed\b|\bsenor\b|\bsenora\b", folded):
        # spelling of common words with otherwise right structure
        if re.search(r"\b(buenos dias|buenas|como esta)\b", folded):
            return "surface"
    if re.search(r"\bcomo estas\b", folded) and re.search(
            r"\b(senora|senor|usted|profesor|maestr)", folded):
        return "conceptual"  # informal to formal addressee
    if re.search(r"\besta bien\b", folded) and not re.search(r"\bestoy\b", folded):
        return "conceptual"  # wrong person of estar

    return "unclear"


def build_session_open_decision(state: dict) -> dict:
    """Conversational open: due review or input+meaning — never worksheet mode."""
    state = ensure_flow_fields(state)
    due = due_items(state)
    unit = state.get("current_unit") or 1

    if due:
        item = due[0]
        ref = _pack_id_from_review_item(item) or "P-1.1"
        focus_kind = "pack_id" if re.match(r"^[A-Z]", ref) else "grammatical_name"
        state = dict(state)
        state["lesson_phase"] = "review"
        state["lesson_goal"] = f"Quick warm-up, then new material"
        state["goal"] = state["lesson_goal"]
        state["consecutive_successes"] = 0
        state["same_target_retries"] = 0
        decision = {
            "situation": "session_open",
            "move": "elicit_production",
            "focus": {"kind": focus_kind, "ref": ref},
            "reveal_policy": "prefer_scaffold",
            "error_policy": {"mode": "none", "priority": "none"},
            "sequence_slot": "review",
            "frame": {
                "lang": "en", "register": "tu",
                "character": "none", "max_lines": 6,
            },
            "elicit": {"type": "attempt_current_item", "of": "focus"},
            "constraints": ["no_second_move"],
            "session_state": json.dumps(state, ensure_ascii=False),
            "_open_note": (
                "Warm, human session open with a DUE warm-up. "
                f"One quick check on: {item.get('item', ref)}. "
                "If they get it roughly right (ignore accents/typos), celebrate "
                "and move on — do not grind. Then continue into new input."
            ),
        }
        return decision

    state = dict(state)
    state["lesson_phase"] = "input"
    state["current_unit"] = unit
    state["lesson_goal"] = (
        f"Unit {unit}: greetings in real conversation — understand, then try"
    )
    state["goal"] = state["lesson_goal"]
    state["consecutive_successes"] = 0
    state["same_target_retries"] = 0
    state["same_target_retries"] = 0
    return {
        "situation": "session_open",
        "move": "present_input",
        "focus": {"kind": "none", "ref": ""},
        "reveal_policy": "prefer_scaffold",
        "error_policy": {"mode": "none", "priority": "none"},
        "sequence_slot": "input",
        "frame": {
            "lang": "es", "register": "tu",
            "character": "none", "max_lines": 12,
        },
        "elicit": {"type": "comprehension_answer", "of": "none"},
        "constraints": ["input_before_rules", "no_second_move"],
        "session_state": json.dumps(state, ensure_ascii=False),
        "_open_note": (
            "CONVERSATIONAL SESSION OPEN (input first).\n"
            "1) One warm English line stating what you'll do together today "
            "(not a syllabus lecture).\n"
            "2) Share a short natural Spanish dialogue (use seed if helpful).\n"
            "3) Ask ONE easy meaning question like a curious partner "
            "(not a test voice).\n"
            "Do NOT open with production drills, spelling quizzes, or "
            "'repeat after me' for its own sake."
        ),
    }


def allowed_moves_for_state(state: dict) -> frozenset[str]:
    phase = ensure_flow_fields(state).get("lesson_phase", "input")
    return ALLOWED_MOVES.get(phase, ALLOWED_MOVES["production"])


def flow_gate_errors(decision: dict, state: dict) -> list[str]:
    phase = ensure_flow_fields(state).get("lesson_phase", "input")
    move = decision.get("move")
    allowed = allowed_moves_for_state(state)
    always = frozenset({
        "refuse_injection", "redirect_scope", "nudge_then_offer", "passthrough",
        "close", "recap_and_space",  # meta / reframe always ok
    })
    # If stuck retrying same focus, force advance-capable moves only
    if (state.get("same_target_retries") or 0) >= 2:
        advance_moves = frozenset({
            "elicit_production", "present_input", "recap_and_space",
            "passthrough", "nudge_then_offer", "teach_answer", "model_form",
        })
        if move == "remediate":
            return [
                "same target retried too many times — do NOT remediate again; "
                "accept good-enough, recast once in conversation, and MOVE ON "
                f"(try one of: {sorted(advance_moves)})"
            ]
    if move in always:
        return []
    if move not in allowed:
        return [
            f"lesson_phase={phase!r} forbids move {move!r}; "
            f"allowed={sorted(allowed | always)}"
        ]
    return []


def advance_phase(
    state: dict,
    move: str,
    *,
    success_signal: bool = False,
    issue_class: str = "unclear",
    focus_ref: str | None = None,
) -> dict:
    """Update phase + mastery counters after a turn."""
    s = ensure_flow_fields(state)
    phase = s.get("lesson_phase", "input")
    focus_ref = focus_ref or ""

    # Track grinding only for conceptual remediations — surface noise is success.
    if move == "remediate" and issue_class not in ("ok", "surface"):
        if focus_ref and focus_ref == s.get("last_focus_ref"):
            s["same_target_retries"] = int(s.get("same_target_retries") or 0) + 1
        else:
            s["same_target_retries"] = 1
        s["last_focus_ref"] = focus_ref
        s["consecutive_successes"] = 0
    elif success_signal or issue_class in ("ok", "surface"):
        s["consecutive_successes"] = int(s.get("consecutive_successes") or 0) + 1
        s["same_target_retries"] = 0
        s["last_focus_ref"] = focus_ref or s.get("last_focus_ref")
    else:
        s["consecutive_successes"] = 0

    # Structural advances
    if move in ADVANCE_ON_MOVE:
        s["lesson_phase"] = ADVANCE_ON_MOVE[move]
    elif success_signal or issue_class in ("ok", "surface"):
        # Good enough → push forward through the arc
        if phase == "review":
            s["lesson_phase"] = "input"
        elif phase == "comprehension":
            # Skip SI if they're clearly ready — jump to production/task sooner
            if s["consecutive_successes"] >= 1:
                s["lesson_phase"] = "production"
            else:
                s["lesson_phase"] = "structured_input"
        elif phase == "structured_input":
            s["lesson_phase"] = "production"
        elif phase == "production":
            # One solid success is enough to try a real conversational task
            if s["consecutive_successes"] >= 1 or issue_class == "ok":
                s["lesson_phase"] = "task"
        elif phase == "task" and s["consecutive_successes"] >= 2:
            # Ready for next micro-goal / recap
            s["lesson_phase"] = "task"
    elif move == "recap_and_space":
        s["lesson_phase"] = "input"
        s["consecutive_successes"] = 0

    # Force escape hatch from remediation hell
    if int(s.get("same_target_retries") or 0) >= 2:
        s["lesson_phase"] = "task" if phase in ("production", "task", "review") else "production"
        s["same_target_retries"] = 0

    s["last_move"] = move
    s["sequence_slot"] = s["lesson_phase"]
    return s


def harness_flow_message(state: dict) -> str:
    s = ensure_flow_fields(state)
    phase = s.get("lesson_phase", "input")
    allowed = sorted(allowed_moves_for_state(s) | {
        "refuse_injection", "redirect_scope", "nudge_then_offer",
        "passthrough", "close", "recap_and_space",
    })
    due = due_items(s)
    lines = [
        "HARNESS LESSON FLOW + CONVERSATION RULES (authoritative):",
        f"  lesson_phase: {phase}",
        f"  lesson_goal: {s.get('lesson_goal') or s.get('goal') or '(none)'}",
        f"  current_unit: {s.get('current_unit')}",
        f"  consecutive_successes: {s.get('consecutive_successes', 0)}",
        f"  same_target_retries: {s.get('same_target_retries', 0)}",
        f"  allowed_moves_this_turn: {', '.join(allowed)}",
        "  PRIORITIES (in order):",
        "    1) Feel like a natural conversation with a good tutor.",
        "    2) If meaning is clear, MOVE ON — ignore accents/typos/spelling.",
        "    3) Only remediate conceptual errors (wrong form/register/meaning).",
        "    4) Never re-drill the same stem with only a costume change.",
        "    5) After they show they know it, go to a short roleplay/task.",
        "  If same_target_retries >= 2: accept, recast once, change activity.",
        "  Prefer in-conversation recasts over English red-pen lectures.",
    ]
    if due:
        lines.append(f"  due_review_items: {json.dumps(due, ensure_ascii=False)}")
    return "\n".join(lines)


def success_heuristic(
    learner: str,
    visible: str,
    decision: dict,
    *,
    issue_class: str = "unclear",
) -> bool:
    if issue_class in ("ok", "surface"):
        return True
    move = decision.get("move")
    if move == "remediate" and issue_class != "surface":
        return False
    if decision.get("situation") in (
            "multi_error_production", "single_error_production"
    ) and issue_class == "conceptual":
        return False
    v = (visible or "").lower()
    if any(w in v for w in (
            "¡muy bien", "excelente", "perfect", "correct", "great",
            "nice", "exactly", "you've got", "you got it", "listo")):
        return True
    if decision.get("situation") == "correct_production":
        return True
    return False


def infer_issue_for_turn(learner: str, decision: dict) -> str:
    """Classify this learner utterance for progression logic."""
    focus = (decision.get("focus") or {}).get("ref") or ""
    hints = []
    if focus == "P-1.1" or "P-1.1" in focus:
        hints = [
            "Buenos días, señora. ¿Cómo está usted?",
            "Buenos dias senora. Como esta usted?",
            "¿Cómo está usted?",
            "Como esta usted",
        ]
    if "estoy" in fold_spanish(learner) or "esta bien" in fold_spanish(learner):
        hints += ["Estoy bien ¿y tú?", "Estoy bien y tu", "Estoy bien"]
    # Meta questions
    if re.search(r"\b(what are we|why are we|better way|stuck|boring)\b",
                 (learner or "").lower()):
        return "meta"
    return classify_learner_issue(learner, hints or None)
