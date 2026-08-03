"""Conversational (ConvSession / planned) smoke trajectories.

Committed before runs. Mechanical expectations only — no LLM judge criteria.
Legacy TRAJECTORIES in trajectories.py target tutor.cli / planner; do not mix.

Seeding rules (hard-break budget arithmetic — see docs/reviews-evals-port.md):
blank open consumes the budget via placement, so a hard mode cannot fire on
the first learner turn after a blank open. Trajectories that need a hard break
on turn 1 (form_focus, association) seed a known (non-blank) sheet so the open
is conversation, leaving the budget free.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from tutor.character_sheet import default_sheet, note_error_pattern


def _blank_sheet() -> dict:
    return default_sheet()


def _known_sheet(**skill_conf: float) -> dict:
    """Non-blank learner so open is conversation (not placement hard-break)."""
    s = default_sheet()
    skills = s.setdefault("skills", {})
    # Any conf > 0.05 clears is_blank_learner
    base = {"IP-01": 0.4, "IP-04": 0.3}
    base.update(skill_conf)
    for cid, conf in base.items():
        prev = dict(skills.get(cid) or {})
        prev["status"] = "emerging"
        prev["confidence"] = float(conf)
        skills[cid] = prev
    s["identity"] = dict(s.get("identity") or {})
    s["identity"]["preferred_name"] = None
    return s


def _form_focus_seed() -> dict:
    s = _known_sheet()
    # count >= 2 → form_focus when can_hard (known open is not a hard break)
    note_error_pattern(s, "estar_yo_estoy_vs_esta", "yo está", resolved=False)
    note_error_pattern(s, "estar_yo_estoy_vs_esta", "yo está bien", resolved=False)
    return s


def _transfer_seed() -> dict:
    """Pattern hot on the sheet so a correct use can resolve → transfer."""
    s = _known_sheet()
    note_error_pattern(s, "estar_yo_estoy_vs_esta", "yo está", resolved=False)
    note_error_pattern(s, "estar_yo_estoy_vs_esta", "está bien", resolved=False)
    return s


def _due_reencounter_seed() -> dict:
    """Known sheet with a lexicon MWU whose next_due is in the past.

    Phase 1 retrieval scheduler: due items must ride conversation turns as
    DUE RE-ENCOUNTERS soft instructions (notes flag due_elicit_offered).
    """
    s = _known_sheet()
    lex = s.setdefault("lexicon", {})
    lex["hasta luego"] = {
        "status": "emerging",
        "confidence": 0.3,
        "introduced_at": "2026-07-20",
        "scaffold": "l1_micro_gloss",
        "next_due": "2026-07-21",  # firmly in the past → always due
        "interval_days": 1,
        "successive_successes": 0,
    }
    return s


def _taking_root_seed() -> dict:
    """Due-reencounter seed one success from the 3-day interval.

    Progress rail (docs/design-progression-view.md, as amended): a due
    re-encounter success here moves the ladder 1d → 3d, which must emit the
    taking_root milestone note exactly once (code-owned, not model-driven —
    the crossing fires in _record_due_outcomes before the tutor call, so the
    expectation is deterministic regardless of the model reply).
    """
    s = _due_reencounter_seed()
    s["lexicon"]["hasta luego"]["successive_successes"] = 1
    return s


# Each trajectory:
#   id, description, seed_sheet (dict|None → blank),
#   seed_mode_state (dict applied to session.mode_state after construct),
#   turns (learner strings; open is always separate),
#   expect: structured mechanical expectations consumed by conv_checks
#
# expect.mode_sets: list aligned to [open] + turns; each entry is the set of
#   allowed mode strings for that turn.
# expect.gate: per-turn {forbid_faults, require_any_fault} on the final gate.
# expect.teach: per-turn required / any-of part keys.
# expect.sheet_final: predicates on the final sheet.

CONV_TRAJECTORIES: list[dict[str, Any]] = [
    {
        "id": "c01_placement_open",
        "description": "Blank sheet open → placement mode + teach move + English orientation (true-zero, incident 2026-07-28).",
        "seed_sheet": None,  # blank
        "turns": [],
        "expect": {
            "mode_sets": [
                ["placement"],
            ],
            "teach": [
                {"any_of": ["model", "try", "recast"], "open_prefer_model_and_try": True},
            ],
            "gate": [
                {"forbid_faults": ["gate:sheet_leak"]},
            ],
            # True-zero open must carry English support: at least one English
            # lexicon hit or a gloss parenthetical in the visible open reply.
            "open_english": True,
            "sheet_final": {},
        },
        "mechanical": [
            "mode_sequence",
            "teach_moves",
            "open_english_orientation",
            "gate_contract",
            "no_empty_reply",
            "no_turn_error",
        ],
    },
    {
        "id": "c02_cf_recast_weather",
        "description": "Weather form error → soft cf_recast (not association).",
        "seed_sheet": None,
        "turns": [
            # Catalog: weather_hace detect (está calor / esta un poco calor)
            "Hola. Esta un poco calor hoy en Rio Dulce.",
        ],
        "expect": {
            "mode_sets": [
                ["placement"],
                ["cf_recast"],
            ],
            "teach": [
                {"any_of": ["model", "try", "recast"]},
                {"require": ["recast"], "any_of": ["try", "model", "recast"]},
            ],
            "gate": [
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
            ],
            "sheet_final": {
                "error_pattern_min": {"weather_hace": 1},
            },
        },
        "mechanical": [
            "mode_sequence",
            "teach_moves",
            "gate_contract",
            "sheet_evolution",
            "no_empty_reply",
            "no_turn_error",
            "recast_or_gate_attempt",
        ],
    },
    {
        "id": "c03_form_focus_streak",
        "description": "Live error → recast; recent-error streak hard-breaks after cooldown (2026-07-28 recency contract).",
        "seed_sheet": _form_focus_seed(),
        "seed_mode_state": {
            # Defensive: ensure budget open even if future open paths harden
            "turns_since_hard_break": 999,
            "hard_breaks_this_session": 0,
        },
        "turns": [
            # Live hit this session (recency gate requires it)
            "yo está bien, gracias.",
            # Clean turns; cf_recast cooldown (3 → 2 suppressed turns) holds
            "todo bien hoy.",
            "si, todo bien.",
            # Cooldown expired; error recent (within K=4) → hard break allowed
            "todo tranquilo.",
        ],
        "expect": {
            "mode_sets": [
                ["conversation"],  # known open
                ["cf_recast", "form_focus"],
                ["conversation", "transfer", "cf_recast"],
                ["conversation", "transfer"],
                ["form_focus", "conversation"],
            ],
            "teach": [
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
            ],
            "gate": [
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
            ],
            "sheet_final": {
                "error_pattern_min": {"estar_yo_estoy_vs_esta": 2},
            },
        },
        "mechanical": [
            "mode_sequence",
            "teach_moves",
            "gate_contract",
            "sheet_evolution",
            "no_empty_reply",
            "no_turn_error",
        ],
    },
    {
        "id": "c04_association_bote",
        "description": "Concrete noun bote → association (or conversation+image if budget).",
        "seed_sheet": _known_sheet(),
        "seed_mode_state": {
            "turns_since_hard_break": 999,
            "hard_breaks_this_session": 0,
        },
        "turns": [
            "Estoy en mi bote.",
        ],
        "expect": {
            "mode_sets": [
                ["conversation"],
                # hard association if can_hard; else conversation with image_concept
                ["association", "conversation"],
            ],
            "teach": [
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
            ],
            "gate": [
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
            ],
            "sheet_final": {},
        },
        "mechanical": [
            "mode_sequence",
            "teach_moves",
            "gate_contract",
            "association_signal",
            "no_empty_reply",
            "no_turn_error",
        ],
    },
    {
        "id": "c05_comprehension_repair",
        "description": "Meta 'don't understand' after open → stay on same try.",
        "seed_sheet": None,
        "turns": [
            "I don't understand what that means. No entiendo.",
        ],
        "expect": {
            "mode_sets": [
                ["placement"],
                ["comprehension_repair"],
            ],
            "teach": [
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "explain", "recast"]},
            ],
            "gate": [
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
            ],
            "sheet_final": {},
        },
        "mechanical": [
            "mode_sequence",
            "teach_moves",
            "gate_contract",
            "comprehension_repair_targets",
            "no_empty_reply",
            "no_turn_error",
        ],
    },
    {
        "id": "c06_transfer_after_resolve",
        "description": "Correct use of focused form → transfer (or conversation).",
        "seed_sheet": _transfer_seed(),
        "seed_mode_state": {
            "turns_since_hard_break": 999,
            "hard_breaks_this_session": 0,
        },
        "turns": [
            "Estoy bien.",  # resolve estar_yo_estoy_vs_esta
            "Me gusta el café.",  # free line; expect transfer or conversation
        ],
        "expect": {
            "mode_sets": [
                ["conversation"],
                # resolve turn: may still cf_recast if other hits; allow soft set
                ["transfer", "conversation", "cf_recast", "association"],
                ["transfer", "conversation", "association"],
            ],
            "teach": [
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
            ],
            "gate": [
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
            ],
            "sheet_final": {
                # After correct estoy, resolved_streak or count should ease
                "error_pattern_resolved_direction": {
                    "pattern": "estar_yo_estoy_vs_esta",
                    "min_resolved_streak": 1,
                },
            },
            "require_mode_somewhere": ["transfer"],  # WARN if never seen
        },
        "mechanical": [
            "mode_sequence",
            "teach_moves",
            "gate_contract",
            "sheet_evolution",
            "transfer_seen_or_warn",
            "no_empty_reply",
            "no_turn_error",
        ],
    },
    {
        "id": "c07_intro_no_capture",
        "description": (
            "Me-llamo intro → IP-03 ability credit; the name VALUE is never "
            "stored (personal-data capture disabled 2026-07-28)."
        ),
        "seed_sheet": None,
        "turns": [
            "Me llamo Sam. Estoy bien.",
        ],
        "expect": {
            "mode_sets": [
                ["placement"],
                # soft: mode is not the point of this trajectory
                [
                    "cf_recast",
                    "conversation",
                    "association",
                    "transfer",
                    "form_focus",
                    "comprehension_repair",
                    "placement",
                ],
            ],
            "teach": [
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
            ],
            "gate": [
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
            ],
            "sheet_final": {
                "preferred_name_absent": True,
                "skill_confidence_min": {"IP-03": 0.05},
            },
        },
        "mechanical": [
            "mode_sequence",
            "teach_moves",
            "gate_contract",
            "sheet_evolution",
            "no_empty_reply",
            "no_turn_error",
        ],
    },
    {
        "id": "c08_due_reencounter",
        "description": (
            "Past-due lexicon MWU on the sheet → DUE RE-ENCOUNTERS soft "
            "instruction on a conversation turn (notes: due_elicit_offered). "
            "The learner USES the due MWU with the ladder one success from "
            "3d → the progress ledger must emit taking_root exactly once "
            "(notes: progress_milestone:taking_root:hasta luego)."
        ),
        "seed_sheet": _taking_root_seed(),
        "seed_mode_state": {
            "turns_since_hard_break": 999,
            "hard_breaks_this_session": 0,
        },
        "turns": [
            "Hola. Estoy bien hoy. ¡Hasta luego!",
        ],
        "expect": {
            "mode_sets": [
                ["conversation"],  # known open (due block may ride here too)
                ["conversation", "transfer", "cf_recast", "association"],
            ],
            "teach": [
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
            ],
            "gate": [
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
            ],
            "sheet_final": {},
            "due_elicit": True,
            "progress_milestones": ["taking_root:hasta luego"],
        },
        "mechanical": [
            "mode_sequence",
            "teach_moves",
            "gate_contract",
            "due_elicit_fired",
            "progress_milestones_fired",
            "no_empty_reply",
            "no_turn_error",
        ],
    },
    {
        "id": "c09_phase_mix",
        "description": (
            "Multi-turn due re-encounter: a past-due item keeps riding "
            "teaching_data as due-for-review FACTS across several "
            "conversation turns (due_elicit_offered fires from the "
            "due-data path; the session-phase layer was DELETED "
            "2026-08-03, full-code-audit S9)."
        ),
        "seed_sheet": _due_reencounter_seed(),
        "seed_mode_state": {
            "turns_since_hard_break": 999,
            "hard_breaks_this_session": 0,
        },
        "turns": [
            "Hola. Estoy bien hoy.",
            "Me gusta el café.",
            "El río es muy bonito.",
        ],
        "expect": {
            "mode_sets": [
                ["conversation"],  # known open (retrieval phase, due rides)
                ["conversation", "transfer", "cf_recast", "association"],
                ["conversation", "transfer", "cf_recast", "association"],
                ["conversation", "transfer", "cf_recast", "association"],
            ],
            "teach": [
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
            ],
            "gate": [
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
            ],
            "sheet_final": {},
            "due_elicit": True,
        },
        "mechanical": [
            "mode_sequence",
            "teach_moves",
            "gate_contract",
            "due_elicit_fired",
            "no_empty_reply",
            "no_turn_error",
        ],
    },
    {
        "id": "c10_introduce_scaffolded",
        "description": (
            "Phase 3 introduce router: known sheet with nothing due → the "
            "flavorable open/turns must mint an INTRODUCE plan (notes: "
            "introduce_planned:<key>:<rule>). "
            "Mechanical note-presence only — whether the plan marks "
            "(introduced:<key>) or lapses is the model's realization."
        ),
        "seed_sheet": _known_sheet(),
        "seed_mode_state": {
            "turns_since_hard_break": 999,
            "hard_breaks_this_session": 0,
        },
        "turns": [
            "Hola. Estoy bien hoy.",
            "Muy bien, gracias.",
        ],
        "expect": {
            "mode_sets": [
                ["conversation"],  # known open (new_input phase, plan rides)
                ["conversation", "transfer", "cf_recast", "association"],
                ["conversation", "transfer", "cf_recast", "association"],
            ],
            "teach": [
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
                {"any_of": ["model", "try", "recast"]},
            ],
            "gate": [
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
                {"forbid_faults": ["gate:sheet_leak"]},
            ],
            "sheet_final": {},
            "introduce_planned": True,
        },
        "mechanical": [
            "mode_sequence",
            "teach_moves",
            "gate_contract",
            "introduce_scaffolded",
            "no_empty_reply",
            "no_turn_error",
        ],
    },
]


def get_seed_sheet(traj: dict) -> dict:
    raw = traj.get("seed_sheet")
    if raw is None:
        return _blank_sheet()
    return deepcopy(raw)
