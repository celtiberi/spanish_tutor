"""Pedagogy contract — durable teaching invariants for conversational mode.

Why this module exists
----------------------
Teaching rules used to live only in ``prompts/conversational_tutor.md`` and
per-turn harness strings. Those are soft: any “tone” or “language mix” edit
could erase the teach cycle without a failing test. That is how we drifted
into chat-buddy mode.

This file is the **source of truth for what counts as teaching**. The prompt
implements the contract; the harness restates it; **code checks every turn**.
Experiments change the contract deliberately (PR + tests), not by accident.

Contract (v1)
-------------
1. Every learner-facing turn must include a **teach move**:
   ``model`` and/or ``try`` and/or ``recast``.
2. **Open** turns should include ``model`` *and* ``try`` (not a bare greeting).
3. If there is a **recast**, there should also be a **try** (same-form retry),
   unless the learner only asked a meta question with no production attempt
   (still prefer try after meta).
4. ``continue`` alone (chatty next question with no model/try/recast) is a
   **contract violation**.

Enforcement is non-blocking for the learner (we still show the reply) but
always logged as sheet notes / turn flags so sims and UI can surface misses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Bump when invariants change (experiments document the new version).
CONTRACT_VERSION = "1.1"  # + diagnostic open when sheet is blank

# Machine ids for notes / checks.
# Phase 3 batch 2 (typed turn events, docs/reviews-architecture-refactor.md):
# the bare KEYS are first-class — a note string is "pedagogy:" + key, the
# rendered projection of a typed PEDAGOGY TurnEvent (tutor/turn_events.py).
# conv_session emits from PedagogyCheck.note_keys / these KEY_ constants;
# the full-string constants remain the comparison vocabulary for callers.
PEDAGOGY_NOTE_PREFIX = "pedagogy:"
KEY_NO_TEACH_MOVE = "no_teach_move"
KEY_OPEN_NEEDS_MODEL_TRY = "open_needs_model_try"
KEY_RECAST_WITHOUT_TRY = "recast_without_try"
KEY_OK = "ok"
KEY_UNSTRUCTURED = "unstructured"
KEY_DIAGNOSTIC_OPEN = "diagnostic_open"
KEY_KNOWN_LEARNER_OPEN = "known_learner_open"

VIOLATION_NO_TEACH_MOVE = PEDAGOGY_NOTE_PREFIX + KEY_NO_TEACH_MOVE
VIOLATION_OPEN_NEEDS_MODEL_TRY = PEDAGOGY_NOTE_PREFIX + KEY_OPEN_NEEDS_MODEL_TRY
VIOLATION_RECAST_WITHOUT_TRY = PEDAGOGY_NOTE_PREFIX + KEY_RECAST_WITHOUT_TRY
OK_TEACH_MOVE = PEDAGOGY_NOTE_PREFIX + KEY_OK
NOTE_DIAGNOSTIC_OPEN = PEDAGOGY_NOTE_PREFIX + KEY_DIAGNOSTIC_OPEN
NOTE_KNOWN_LEARNER_OPEN = PEDAGOGY_NOTE_PREFIX + KEY_KNOWN_LEARNER_OPEN

# Teaching channels the system owns. v1 only *enforces* text moves;
# planned channels are listed so they expand via contract, not as UI toys.
# See docs/pedagogy-contract.md § Teaching modalities.
TEACH_MODALITIES: dict[str, dict[str, Any]] = {
    "text_model": {
        "status": "active",
        "role": "Present target form(s) for comprehension/production.",
        "contract_part": "model",
    },
    "text_try": {
        "status": "active",
        "role": "Elicit learner production of the target.",
        "contract_part": "try",
    },
    "recast": {
        "status": "active",
        "role": "Focus on form: clean model of what they meant.",
        "contract_part": "recast",
    },
    "audio_tts": {
        "status": "active_support",
        "role": "Voice input for memory and pronunciation (playback).",
        "contract_part": None,
    },
    "audio_stt": {
        "status": "active_support",
        "role": "Spoken production under real conditions.",
        "contract_part": None,
    },
    "visual_image": {
        "status": "planned",
        "role": (
            "Associate nouns/scenes/concepts with form (dual coding / CI). "
            "Image must match the teach target in the same turn — not decoration."
        ),
        "contract_part": "image",  # future structured part or teach_assets
        "rules": [
            "target_linked",       # same concept as model/try
            "same_turn_as_form",   # co-present with linguistic model
            "no_english_sticker",  # don't replace inference with labels
            "logged_as_teach_move",
        ],
    },
    "task_roleplay": {
        "status": "sheet_guided",
        "role": "TBLT use of form in a micro-task (next_best activity).",
        "contract_part": None,
    },
}


@dataclass
class PedagogyCheck:
    """Result of checking one tutor turn against the contract."""

    ok: bool
    violations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    version: str = CONTRACT_VERSION
    # Typed event keys (Phase 3 batch 2 leaf push-down): the bare keys the
    # notes render from — notes[i] == PEDAGOGY_NOTE_PREFIX + note_keys[i].
    # conv_session._finish emits PEDAGOGY TurnEvents from these; when a
    # (test-built) check carries notes without keys, the absorb safety net
    # classifies the strings instead.  NOT in as_dict() (shape pinned).
    note_keys: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "violations": list(self.violations),
            "notes": list(self.notes),
            "version": self.version,
        }


def is_blank_learner(sheet: dict | None) -> bool:
    """True when we have essentially no ability evidence — feel-out required.

    A wiped / default sheet is not an intermediate speaker. Opening pure
    Spanish monologue at them is a contract failure of judgment.
    """
    if not isinstance(sheet, dict):
        return True
    ident = sheet.get("identity") or {}
    name = (ident.get("preferred_name") or ident.get("name") or "").strip()
    skills = sheet.get("skills") or {}
    any_evidence = False
    for _k, v in skills.items() if isinstance(skills, dict) else []:
        if not isinstance(v, dict):
            continue
        conf = float(v.get("confidence") or 0)
        status = (v.get("status") or "unknown").lower()
        ev = v.get("evidence") or []
        if conf > 0.05 or status not in ("unknown", "", "none") or ev:
            any_evidence = True
            break
    eps = sheet.get("error_patterns") or {}
    if isinstance(eps, dict):
        for k, v in eps.items():
            if k in ("active", "history", "resolved"):
                continue
            if isinstance(v, dict) and int(v.get("count") or 0) > 0:
                any_evidence = True
                break
    # Named but no skills still ≈ blank for placement
    if any_evidence:
        return False
    return True


def open_phase(sheet: dict | None) -> str:
    """Which open script to use: diagnostic | known."""
    return "diagnostic" if is_blank_learner(sheet) else "known"


def _truthy_part(parts: dict | Any, key: str) -> bool:
    if parts is None:
        return False
    if isinstance(parts, dict):
        val = parts.get(key) or ""
    else:
        # TutorParts
        if key == "try":
            val = getattr(parts, "try_", None) or getattr(parts, "try", None) or ""
        elif key == "continue":
            val = getattr(parts, "continue_", None) or getattr(parts, "continue", None) or ""
        else:
            val = getattr(parts, key, None) or ""
    return bool(str(val).strip())


def has_teach_move(parts: dict | Any) -> bool:
    """True if model, try, or recast is non-empty."""
    return (
        _truthy_part(parts, "model")
        or _truthy_part(parts, "try")
        or _truthy_part(parts, "recast")
    )


def check_tutor_parts(
    parts: dict | Any,
    *,
    is_open: bool = False,
) -> PedagogyCheck:
    """Validate structured (or unstructured) tutor parts against contract v1."""
    violations: list[str] = []
    note_keys: list[str] = []

    has_model = _truthy_part(parts, "model")
    has_try = _truthy_part(parts, "try")
    has_recast = _truthy_part(parts, "recast")
    teach = has_model or has_try or has_recast

    if not teach:
        violations.append(VIOLATION_NO_TEACH_MOVE)
        note_keys.append(KEY_NO_TEACH_MOVE)

    if is_open and not (has_model and has_try):
        violations.append(VIOLATION_OPEN_NEEDS_MODEL_TRY)
        note_keys.append(KEY_OPEN_NEEDS_MODEL_TRY)

    if has_recast and not has_try:
        # Soft-hard: recast without re-try is incomplete focus-on-form
        violations.append(VIOLATION_RECAST_WITHOUT_TRY)
        note_keys.append(KEY_RECAST_WITHOUT_TRY)

    if not violations:
        note_keys.append(KEY_OK)

    return PedagogyCheck(
        ok=not violations,
        violations=violations,
        notes=[PEDAGOGY_NOTE_PREFIX + k for k in note_keys],
        note_keys=note_keys,
    )


def check_visible_fallback(visible: str, *, is_open: bool = False) -> PedagogyCheck:
    """When structure is missing, still flag empty / greeting-only opens.

    Heuristic only — structured parts are preferred. Used if the model dumps
    plain text without tags.
    """
    text = (visible or "").strip()
    if not text:
        return PedagogyCheck(
            ok=False,
            violations=[VIOLATION_NO_TEACH_MOVE],
            notes=[VIOLATION_NO_TEACH_MOVE],
            note_keys=[KEY_NO_TEACH_MOVE],
        )
    # Unstructured always fails "has teach move tags" for open; for mid-turn
    # we still want a soft signal that structure was missing.
    violations = [VIOLATION_NO_TEACH_MOVE]
    note_keys = [KEY_NO_TEACH_MOVE, KEY_UNSTRUCTURED]
    if is_open:
        violations.append(VIOLATION_OPEN_NEEDS_MODEL_TRY)
        note_keys.append(KEY_OPEN_NEEDS_MODEL_TRY)
    return PedagogyCheck(
        ok=False,
        violations=violations,
        notes=[PEDAGOGY_NOTE_PREFIX + k for k in note_keys],
        note_keys=note_keys,
    )


def evaluate_turn(
    parts: dict | Any,
    *,
    is_open: bool = False,
    structured: bool | None = None,
    visible: str = "",
) -> PedagogyCheck:
    """Main entry: prefer structured check; fallback if no structure."""
    if structured is None:
        if isinstance(parts, dict):
            structured = bool(parts.get("structured"))
        else:
            structured = bool(getattr(parts, "raw_had_structure", False))

    if structured:
        return check_tutor_parts(parts, is_open=is_open)
    # Structured false but maybe still has fields
    if has_teach_move(parts):
        return check_tutor_parts(parts, is_open=is_open)
    return check_visible_fallback(visible, is_open=is_open)
