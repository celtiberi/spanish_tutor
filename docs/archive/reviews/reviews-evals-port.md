

---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-26 20:05 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the inlined subject files so the port design is grounded in the real ConvSession API, not the legacy smoke driver alone.Next I'll pull the real ConvSession API, existing evals, and the rest of the inlined subject so the draft isn't based on truncated stubs.Checking hard-break arithmetic and how blank-learner detection interacts with seeded sheets:# Conv behavioral-gate port — independent design + complete draft

**Date:** 2026-07-26  
**Role:** independent second author (do not treat as rubber-stamp of a “just mirror run_smoke” plan)  
**Subject:** port evals gate from legacy `tutor.cli` / `tutor.planner` onto shipping `ConversationalSession` planned pipeline

---

## 1. Verdict on the brief (contrarian)

A faithful port of `evals/run_smoke.py` + `TRAJECTORIES` + `run_checks` UNIVERSAL list would be **wrong**. Those artifacts encode a different product:

| Legacy smoke | Shipping conv (planned) |
|---|---|
| `student` session_state + policy markers | character sheet + hard observer |
| planner directive ghostwrite checks | `select_mode` → AI realize → `output_gate` |
| open harness: `"Please open the session…"` | `open_session()` / placement vs known-open |
| `parse_ok` / review_schedule | `parts.mode`, `parts.output_gate`, `error_patterns` |

**Do not reuse** `UNIVERSAL = [state_parses, schedule_valid, directive_no_ghostwrite, …]` on ConvSession results. They will false-fail or no-op.

**Do not** put all six modes in one multi-turn script. Mode selection is mostly deterministic in *code*, but the **hard-break budget** makes sequential hard modes impossible immediately after placement.

### Hard-break arithmetic (load-bearing)

From `modes._can_hard_break` + `ModeSessionState.tick` + open path:

1. Blank open → `Mode.PLACEMENT`, `hard_break=True` → `note_hard_break` sets `turns_since_hard_break = 0`, `hard_breaks_this_session = 1`.
2. Each subsequent `user_turn` starts with `tick()` → `turns_since_hard_break += 1`.
3. `can_hard` is **False** while `hard_breaks_this_session > 0` and `turns_since_hard_break < 3`.

| Event | `turns_since` after tick | `can_hard` | Hard modes that need budget |
|---|---|---|---|
| open (placement) | 0 (post-break) | n/a | placement already used budget |
| learner turn 1 | 1 | False | form_focus / association(hard) blocked |
| learner turn 2 | 2 | False | still blocked |
| learner turn 3 | 3 | True | hard breaks allowed again |

**Implication:** after diagnostic open, first-turn `form_focus` and hard `association` **cannot** fire. Soft `cf_recast` and `comprehension_repair` (repair path does not consult `can_hard`) can.

**Design rule:** one **primary** mode target per trajectory; use **known (non-blank) seed sheets** when the target hard-break must fire on the first learner turn; allow mode **sets** where budget/guards legitimately fork (`association` | `conversation` with `image_concept`).

---

## 2. Public API used (and gaps)

### Usable without refactor

```text
ConversationalSession(
    model=..., pack_dir=..., sheet_path=...,   # MUST be per-run temp path
    use_tools=False,                           # hard observer only; faster
    label=..., log=False,                      # avoid polluting logs/sessions
)
session.open_session() -> TurnResult
session.user_turn(text) -> TurnResult
session.sheet                       # live dict after each turn
session.mode_state                  # public attr; seed after construct (shim)
session.last_mode_decision
session.close(persist_sheet=False)  # or True if writing only temp sheet
TurnResult.reply / .parts / .notes / .usage / .error
  parts["mode"], parts["mode_decision"], parts["output_gate"],
  parts["model"|"try"|"recast"|...], parts["plan"], parts["teach_images"]
```

### API gaps (flag explicitly)

| Gap | Force | Recommendation |
|---|---|---|
| No in-memory sheet; `__init__` always `load_sheet` + **`save_sheet`** | Must supply unique `sheet_path` under results stamp | Driver writes seed JSON then constructs session |
| No `teacher_mode=` ctor arg | Env / `config.TEACHER_MODE` only | Set `config.TEACHER_MODE = "planned"` in driver |
| `log=True` always writes under `config.LOG_DIR` | New files (not sheet clobber), still noise | **`log=False`** for smoke |
| Default `CHARACTER_SHEET_PATH` = `logs/character_sheet.json` | **Will clobber** live sheet if omitted | Never omit `sheet_path` |
| No public seed for `ModeSessionState` / `SessionMemory` | Need post-init mutation for transfer / budget edge cases | Documented shim: assign `session.mode_state` fields after init; optional later ctor kwargs |
| Mode/gate only on `parts`, not `TurnResult` fields | Checks must dig into `parts` | Accept; optional small `TurnResult` fields later |
| `ensure_asset(..., generate=True)` on association/repair | Cost/latency/nondeterminism | Force `TEACH_IMAGE_GENERATE=0` + patch `teach_assets.GENERATE_ON_MISS` |
| Focus async thread | Side effects / races on teardown | `FOCUS_MODEL=off`, `FOCUS_ASYNC=False` |
| `open_session` always required for real history shape | Cannot inject mid-dialogue without private history | Every traj calls open first |

No hard **refactor** is required to land a useful gate if the driver isolates paths and accepts the mode_state shim.

---

## 3. Trajectory set (six primary modes)

Naming: `cNN_*` so they never collide with legacy `tNN_*`.

| ID | Seed | Script | Expected mode sets (turn order: open + learners) |
|---|---|---|---|
| `c01_placement_open` | blank default | open only | open ∈ `{placement}` |
| `c02_cf_recast_weather` | blank | open → weather error | open ∈ `{placement}`; t1 ∈ `{cf_recast}` |
| `c03_form_focus_streak` | non-blank + `error_patterns.estar… count≥2` | open → neutral line | open ∈ `{conversation}`; t1 ∈ `{form_focus}` (budget free: open not hard) |
| `c04_association_bote` | non-blank, no hot errors | open → “estoy en mi bote” | open ∈ `{conversation}`; t1 ∈ `{association, conversation}` (budget / image) |
| `c05_comprehension_repair` | blank or light | open → “I don't understand what that means” | open ∈ `{placement, conversation}`; t1 ∈ `{comprehension_repair}` (needs last try/model from open) |
| `c06_transfer_after_resolve` | non-blank + pattern on sheet | open → correct resolve → free line | t1 may be conversation; after resolve, next ∈ `{transfer, conversation}` with allow; assert `last_resolved` path via sheet or mode |
| `c07_name_and_sheet` | blank | open → “Me llamo Sam. Estoy bien.” | sheet name + error/confidence direction; modes soft |

Requirement (1) coverage: placement, cf_recast, form_focus, association, comprehension_repair, transfer each have a home trajectory. c07 is sheet evolution insurance.

---

## 4. Complete draft code (no placeholders)

### 4a. `evals/conv_trajectories.py`

```python
"""Conversational (ConvSession / planned) smoke trajectories.

Committed before runs. Mechanical expectations only — no LLM judge criteria.
Legacy TRAJECTORIES in trajectories.py target tutor.cli / planner; do not mix.
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
    """Pattern known so a correct use can resolve and set transfer."""
    s = _known_sheet(IP_04=0.35)
    # skill key fix — use proper id
    s = _known_sheet()
    note_error_pattern(s, "estar_yo_estoy_vs_esta", "yo está", resolved=False)
    note_error_pattern(s, "estar_yo_estoy_vs_esta", "está bien", resolved=False)
    return s


# Each trajectory:
#   id, description, seed_sheet (dict|None → blank),
#   seed_mode_state (dict applied to session.mode_state after construct),
#   turns (learner strings; open is always separate),
#   expect: structured mechanical expectations consumed by conv_checks
#
# expect.mode_sets: list aligned to [open] + turns
#   each entry is a list/tuple of allowed mode strings
# expect.gate: per-turn optional {forbid_faults, require_any_fault} after final gate
# expect.teach: per-turn optional required part keys
# expect.sheet_final: predicates on final sheet

CONV_TRAJECTORIES: list[dict[str, Any]] = [
    {
        "id": "c01_placement_open",
        "description": "Blank sheet open → placement mode + teach move.",
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
            "sheet_final": {},
            "notes_any": [["mode=placement", "pedagogy:diagnostic_open"]],
        },
        "mechanical": [
            "mode_sequence",
            "teach_moves",
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
                {
                    "forbid_faults": ["gate:sheet_leak"],
                    # After repair path, missing_recast should be gone if repaired;
                    # still forbid sheet leak hard.
                },
            ],
            "sheet_final": {
                "error_pattern_min": {"weather_hace": 1},
            },
            "notes_any": [
                ["mode=placement"],
                ["mode=cf_recast"],
            ],
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
        "description": "Active error count>=2 on known learner → form_focus hard break.",
        "seed_sheet": _form_focus_seed(),
        "seed_mode_state": {
            # Defensive: ensure budget open even if future open paths harden
            "turns_since_hard_break": 999,
            "hard_breaks_this_session": 0,
        },
        "turns": [
            # No new hit required; top active error drives form_focus
            "Todo bien, gracias.",
        ],
        "expect": {
            "mode_sets": [
                ["conversation"],  # known open
                ["form_focus"],
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
            # Optional: image concept recorded when association path taken
            "image_concept_any_of": [None, "bote"],  # checked softly in sheet_evolution
            "mode_reason_substrings": [
                None,
                ["new_noun:bote", "association", "bote"],
            ],
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
            # After first learner resolve, runtime sets last_resolved_form;
            # second learner line should prefer transfer when no higher guard.
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
        "id": "c07_name_capture_sheet",
        "description": "Name + correct estoy → identity + skill confidence direction.",
        "seed_sheet": None,
        "turns": [
            "Me llamo Sam. Estoy bien.",
        ],
        "expect": {
            "mode_sets": [
                ["placement"],
                # soft: not the point of this traj
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
                "preferred_name": "Sam",
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
]


def get_seed_sheet(traj: dict) -> dict:
    raw = traj.get("seed_sheet")
    if raw is None:
        return _blank_sheet()
    return deepcopy(raw)
```

### 4b. `evals/conv_checks.py`

```python
"""Mechanical checks for ConvSession smoke trajectories (no LLM judging)."""

from __future__ import annotations

from typing import Any


def _turns(result: dict) -> list[dict]:
    return list(result.get("turns") or [])


def _mode(turn: dict) -> str | None:
    parts = turn.get("parts") or {}
    m = parts.get("mode")
    if m:
        return str(m)
    md = parts.get("mode_decision") or {}
    if isinstance(md, dict) and md.get("mode"):
        return str(md["mode"])
    # notes fallback: mode=foo
    for n in turn.get("notes") or []:
        s = str(n)
        if s.startswith("mode=") and "=" in s:
            return s.split("=", 1)[1].strip()
    return None


def _parts(turn: dict) -> dict:
    return turn.get("parts") or {}


def _gate(turn: dict) -> dict:
    g = _parts(turn).get("output_gate") or {}
    return g if isinstance(g, dict) else {}


def _truthy(parts: dict, key: str) -> bool:
    return bool(str(parts.get(key) or "").strip())


def no_empty_reply(traj: dict, result: dict) -> list[str]:
    out = []
    for i, t in enumerate(_turns(result)):
        if t.get("error"):
            continue  # no_turn_error owns this
        if not str(t.get("visible") or t.get("reply") or "").strip():
            out.append(f"turn {i}: empty visible reply")
    return out


def no_turn_error(traj: dict, result: dict) -> list[str]:
    return [
        f"turn {i}: session error {t.get('error')!r}"
        for i, t in enumerate(_turns(result))
        if t.get("error")
    ]


def mode_sequence(traj: dict, result: dict) -> list[str]:
    expect = (traj.get("expect") or {}).get("mode_sets") or []
    turns = _turns(result)
    findings = []
    if len(turns) != len(expect):
        findings.append(
            f"turn count {len(turns)} != expect.mode_sets length {len(expect)}"
        )
    n = min(len(turns), len(expect))
    for i in range(n):
        allowed = set(expect[i] or [])
        got = _mode(turns[i])
        if not allowed:
            continue
        if got not in allowed:
            findings.append(
                f"turn {i}: mode {got!r} not in allowed {sorted(allowed)}"
            )
    return findings


def teach_moves(traj: dict, result: dict) -> list[str]:
    specs = (traj.get("expect") or {}).get("teach") or []
    turns = _turns(result)
    findings = []
    n = min(len(turns), len(specs))
    for i in range(n):
        spec = specs[i] or {}
        parts = _parts(turns[i])
        req = list(spec.get("require") or [])
        for k in req:
            if not _truthy(parts, k):
                findings.append(f"turn {i}: missing required teach part <{k}>")
        any_of = list(spec.get("any_of") or [])
        if any_of and not any(_truthy(parts, k) for k in any_of):
            findings.append(
                f"turn {i}: no teach move in any_of={any_of}"
            )
        if spec.get("open_prefer_model_and_try") and i == 0:
            if not (_truthy(parts, "model") and _truthy(parts, "try")):
                # Soft: pedagogy contract also flags; WARN not hard fail
                findings.append(
                    "WARN turn 0: open without both <model> and <try>"
                )
    return findings


def gate_contract(traj: dict, result: dict) -> list[str]:
    specs = (traj.get("expect") or {}).get("gate") or []
    turns = _turns(result)
    findings = []
    n = min(len(turns), len(specs))
    for i in range(n):
        spec = specs[i] or {}
        faults = list((_gate(turns[i]).get("faults") or []))
        for f in spec.get("forbid_faults") or []:
            if f in faults:
                findings.append(f"turn {i}: forbidden gate fault {f}")
        req_any = list(spec.get("require_any_fault") or [])
        if req_any and not any(f in faults for f in req_any):
            findings.append(
                f"turn {i}: expected one of gate faults {req_any}, got {faults}"
            )
        # Always treat sheet leak in visible text as hard even if gate missed it
        blob = str(turns[i].get("visible") or turns[i].get("reply") or "")
        for marker in (
            "update_character_sheet",
            "error_patterns",
            "active_error_focus",
            '"confidence":',
        ):
            if marker in blob:
                findings.append(f"turn {i}: sheet/tool leak marker {marker!r}")
    return findings


def recast_or_gate_attempt(traj: dict, result: dict) -> list[str]:
    """For cf_recast turns: either recast text present or gate required it."""
    findings = []
    for i, t in enumerate(_turns(result)):
        if _mode(t) != "cf_recast":
            continue
        parts = _parts(t)
        if _truthy(parts, "recast"):
            continue
        notes = " ".join(str(n) for n in (t.get("notes") or []))
        gate_faults = _gate(t).get("faults") or []
        if "gate:missing_recast" in gate_faults:
            findings.append(
                f"WARN turn {i}: cf_recast still missing <recast> after gate"
            )
            continue
        if "output_gate" in notes or "missing_recast" in notes:
            findings.append(
                f"WARN turn {i}: cf_recast without recast part (gate notes only)"
            )
            continue
        findings.append(f"turn {i}: cf_recast without <recast> and no gate signal")
    return findings


def sheet_evolution(traj: dict, result: dict) -> list[str]:
    spec = (traj.get("expect") or {}).get("sheet_final") or {}
    if not spec:
        return []
    sheet = result.get("final_sheet") or {}
    findings = []

    want_name = spec.get("preferred_name")
    if want_name:
        got = ((sheet.get("identity") or {}).get("preferred_name") or "").strip()
        if got.lower() != str(want_name).lower():
            findings.append(
                f"preferred_name expected {want_name!r}, got {got!r}"
            )

    for pid, vmin in (spec.get("error_pattern_min") or {}).items():
        ent = (sheet.get("error_patterns") or {}).get(pid) or {}
        c = int(ent.get("count") or 0)
        if c < int(vmin):
            findings.append(
                f"error_patterns[{pid}].count={c} < min {vmin}"
            )

    direction = spec.get("error_pattern_resolved_direction") or {}
    if direction:
        pid = direction.get("pattern")
        ent = (sheet.get("error_patterns") or {}).get(pid) or {}
        streak = int(ent.get("resolved_streak") or 0)
        min_s = int(direction.get("min_resolved_streak") or 1)
        if streak < min_s:
            # Also accept count drop vs seed if seed provided
            seed_eps = ((traj.get("seed_sheet") or {}).get("error_patterns") or {})
            seed_c = int((seed_eps.get(pid) or {}).get("count") or 0)
            final_c = int(ent.get("count") or 0)
            if not (seed_c and final_c < seed_c):
                findings.append(
                    f"pattern {pid}: resolved_streak={streak} < {min_s} "
                    f"and count did not drop ({seed_c}→{final_c})"
                )

    for cid, vmin in (spec.get("skill_confidence_min") or {}).items():
        conf = float(
            ((sheet.get("skills") or {}).get(cid) or {}).get("confidence") or 0
        )
        if conf < float(vmin):
            findings.append(
                f"skills[{cid}].confidence={conf:.3f} < min {vmin}"
            )

    # Optional: confidence direction vs first post-open snapshot
    for cid, direction in (spec.get("skill_confidence_direction") or {}).items():
        series = result.get("skill_confidence_series") or {}
        vals = series.get(cid) or []
        if len(vals) < 2:
            findings.append(f"WARN no confidence series for {cid}")
            continue
        delta = float(vals[-1]) - float(vals[0])
        if direction == "up" and delta <= 0:
            findings.append(
                f"skills[{cid}] expected up, delta={delta:.3f} "
                f"({vals[0]:.3f}→{vals[-1]:.3f})"
            )
        if direction == "down" and delta >= 0:
            findings.append(
                f"skills[{cid}] expected down, delta={delta:.3f}"
            )

    return findings


def association_signal(traj: dict, result: dict) -> list[str]:
    """Pass if any non-open turn is association OR teaches with bote image."""
    findings = []
    turns = _turns(result)
    if len(turns) < 2:
        return ["association traj needs open + >=1 learner turn"]
    t = turns[1]
    mode = _mode(t)
    parts = _parts(t)
    md = parts.get("mode_decision") or {}
    img = md.get("image_concept") if isinstance(md, dict) else None
    teach_imgs = parts.get("teach_images") or []
    concepts = [
        (x.get("concept") if isinstance(x, dict) else None) for x in teach_imgs
    ]
    if mode == "association":
        return []
    if mode == "conversation" and (img == "bote" or "bote" in concepts):
        return []
    if mode in ("association", "conversation") and (
        "bote" in str(parts.get("model") or "").lower()
        or "bote" in str(parts.get("try") or "").lower()
    ):
        return [
            "WARN association: mode conversation without image_concept=bote "
            "but bote present in model/try"
        ]
    findings.append(
        f"turn 1: expected association signal (mode/image bote), "
        f"got mode={mode!r} image_concept={img!r} teach={concepts!r}"
    )
    return findings


def comprehension_repair_targets(traj: dict, result: dict) -> list[str]:
    findings = []
    for i, t in enumerate(_turns(result)):
        if _mode(t) != "comprehension_repair":
            continue
        md = (_parts(t).get("mode_decision") or {})
        targets = (md.get("targets") or {}) if isinstance(md, dict) else {}
        if not targets.get("require_same_topic") and not targets.get(
            "forbid_new_topic"
        ):
            findings.append(
                f"turn {i}: comprehension_repair missing same-topic targets"
            )
        # Soft: try should exist after realize
        if not _truthy(_parts(t), "try") and not _truthy(_parts(t), "model"):
            findings.append(
                f"turn {i}: comprehension_repair without model/try"
            )
    return findings


def transfer_seen_or_warn(traj: dict, result: dict) -> list[str]:
    want = (traj.get("expect") or {}).get("require_mode_somewhere") or []
    if not want:
        return []
    seen = {_mode(t) for t in _turns(result)}
    findings = []
    for m in want:
        if m not in seen:
            findings.append(
                f"WARN required mode {m!r} never observed (seen={sorted(x for x in seen if x)})"
            )
    return findings


CHECKS = {
    f.__name__: f
    for f in (
        no_empty_reply,
        no_turn_error,
        mode_sequence,
        teach_moves,
        gate_contract,
        recast_or_gate_attempt,
        sheet_evolution,
        association_signal,
        comprehension_repair_targets,
        transfer_seen_or_warn,
    )
}


def run_conv_checks(traj: dict, result: dict) -> tuple[dict, bool]:
    names = list(traj.get("mechanical") or [])
    # Always run core safety checks
    for core in ("no_empty_reply", "no_turn_error"):
        if core not in names:
            names.insert(0, core)
    findings: dict[str, list[str]] = {}
    for name in names:
        fn = CHECKS.get(name)
        if fn is None:
            findings[name] = [f"unknown check {name!r}"]
            continue
        out = fn(traj, result)
        if out:
            findings[name] = out
    hard = {
        k: v
        for k, v in findings.items()
        if any(not str(f).startswith("WARN") for f in v)
    }
    return findings, not hard
```

### 4c. `evals/run_conv_smoke.py`

```python
"""Conversational smoke driver: real ConvSession planned pipeline + mechanical checks.

Usage:
    python -m evals.run_conv_smoke
    python -m evals.run_conv_smoke c02 c03
    python -m evals.run_conv_smoke --model gemini-3.6-flash --cell conv-smoke

Results: evals/results/<stamp>/ with per-traj JSON + summary.json
Isolation: per-traj character sheets under that stamp; never writes
logs/character_sheet.json. Session logging off by default.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import traceback
from copy import deepcopy
from pathlib import Path

# --- env clamps BEFORE config-dependent work (still re-patched after import) ---
os.environ.setdefault("TEACHER_MODE", "planned")
os.environ.setdefault("TEACH_IMAGE_GENERATE", "0")
os.environ.setdefault("FOCUS_MODEL", "off")
os.environ.setdefault("FOCUS_ASYNC", "false")
os.environ.setdefault("FOCUS_BLOCKING", "false")
os.environ.setdefault("SHEET_TOOLS", "false")
# Full teacher context while testing (project gate)
os.environ.setdefault("TEACHER_CONTEXT_TRUNCATE", "false")

from evals.conv_checks import run_conv_checks
from evals.conv_trajectories import CONV_TRAJECTORIES, get_seed_sheet
from tutor import config
from tutor.character_sheet import save_sheet
from tutor.conv_session import ConversationalSession

RESULTS_ROOT = Path(__file__).resolve().parent / "results"


def _patch_runtime_for_smoke() -> None:
    """Module-level flags may already be bound; force smoke-safe values."""
    config.load_env()
    config.TEACHER_MODE = "planned"
    config.TEACH_IMAGE_GENERATE = False
    config.FOCUS_ASYNC = False
    config.FOCUS_BLOCKING = False
    config.SHEET_TOOLS = False
    # focus model off
    try:
        config.FOCUS_MODEL = "off"
    except Exception:
        pass
    try:
        import tutor.teach_assets as teach_assets

        teach_assets.GENERATE_ON_MISS = False
    except Exception:
        pass


def _apply_mode_state(session: ConversationalSession, seed: dict | None) -> None:
    if not seed:
        return
    ms = session.mode_state
    for k, v in seed.items():
        if k == "form_focus_cooldown" and isinstance(v, dict):
            ms.form_focus_cooldown = dict(v)
        elif k == "scene_modeled" and isinstance(v, (list, set, tuple)):
            ms.scene_modeled = set(v)
        elif hasattr(ms, k):
            setattr(ms, k, v)


def _skill_conf(sheet: dict, cid: str) -> float:
    try:
        return float(((sheet.get("skills") or {}).get(cid) or {}).get("confidence") or 0)
    except (TypeError, ValueError):
        return 0.0


def _snapshot_skills(sheet: dict, ids: tuple[str, ...] = (
    "IP-01", "IP-03", "IP-04", "IP-07",
)) -> dict[str, float]:
    return {cid: _skill_conf(sheet, cid) for cid in ids}


def _turn_record(
    *,
    learner: str,
    result,
    sheet: dict,
    is_open: bool,
) -> dict:
    parts = dict(result.parts or {})
    return {
        "learner": learner,
        "is_open": is_open,
        "visible": result.reply,
        "reply": result.reply,
        "error": result.error,
        "notes": list(result.notes or []),
        "usage": dict(result.usage or {}),
        "stop_reason": result.stop_reason,
        "parts": parts,
        "mode": parts.get("mode"),
        "mode_decision": parts.get("mode_decision"),
        "output_gate": parts.get("output_gate"),
        "next_best": dict(result.next_best or {}),
        "sheet_identity": deepcopy(sheet.get("identity") or {}),
        "sheet_error_patterns": deepcopy(sheet.get("error_patterns") or {}),
        "skill_confidence": _snapshot_skills(sheet),
        "mode_state": session_mode_snapshot(sheet, result),
    }


def session_mode_snapshot(sheet: dict, result) -> dict:
    # Placeholder filled by caller with real mode_state; kept for schema stability
    return {}


def run_conv_trajectory(
    traj: dict,
    *,
    model: str,
    pack_dir: Path,
    sheet_path: Path,
    cell: dict,
) -> dict:
    seed = get_seed_sheet(traj)
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    if sheet_path.exists():
        sheet_path.unlink()
    save_sheet(sheet_path, seed)

    session = ConversationalSession(
        model=model,
        pack_dir=pack_dir,
        sheet_path=sheet_path,
        use_tools=False,
        label=f"conv-smoke-{traj['id']}",
        log=False,  # do not write logs/sessions/*
        focus_model="off",
    )
    # Re-assert planned path
    session.teacher_mode = "planned"
    _apply_mode_state(session, traj.get("seed_mode_state"))

    turns_out: list[dict] = []
    conf_series: dict[str, list[float]] = {
        "IP-01": [], "IP-03": [], "IP-04": [], "IP-07": [],
    }

    def _push(learner: str, tr, *, is_open: bool) -> None:
        if tr.error:
            rec = {
                "learner": learner,
                "is_open": is_open,
                "visible": tr.reply or "",
                "reply": tr.reply or "",
                "error": tr.error,
                "notes": list(tr.notes or []),
                "usage": dict(tr.usage or {}),
                "stop_reason": tr.stop_reason,
                "parts": dict(tr.parts or {}),
                "mode": (tr.parts or {}).get("mode"),
                "mode_decision": (tr.parts or {}).get("mode_decision"),
                "output_gate": (tr.parts or {}).get("output_gate"),
                "next_best": dict(tr.next_best or {}),
                "sheet_identity": deepcopy(session.sheet.get("identity") or {}),
                "sheet_error_patterns": deepcopy(
                    session.sheet.get("error_patterns") or {}
                ),
                "skill_confidence": _snapshot_skills(session.sheet),
                "mode_state": session.mode_state.snapshot(),
            }
            turns_out.append(rec)
            return
        snap = _snapshot_skills(session.sheet)
        for cid, val in snap.items():
            conf_series.setdefault(cid, []).append(val)
        turns_out.append({
            "learner": learner,
            "is_open": is_open,
            "visible": tr.reply,
            "reply": tr.reply,
            "error": tr.error,
            "notes": list(tr.notes or []),
            "usage": dict(tr.usage or {}),
            "stop_reason": tr.stop_reason,
            "parts": dict(tr.parts or {}),
            "mode": (tr.parts or {}).get("mode"),
            "mode_decision": (tr.parts or {}).get("mode_decision"),
            "output_gate": (tr.parts or {}).get("output_gate"),
            "next_best": dict(tr.next_best or {}),
            "sheet_identity": deepcopy(session.sheet.get("identity") or {}),
            "sheet_error_patterns": deepcopy(
                session.sheet.get("error_patterns") or {}
            ),
            "skill_confidence": snap,
            "mode_state": session.mode_state.snapshot(),
        })

    # Open
    print(f"\n--- {traj['id']} open ---")
    open_res = session.open_session()
    _push("(session open)", open_res, is_open=True)
    if open_res.error:
        session.close(persist_sheet=True)
        return {
            "id": traj["id"],
            **cell,
            "status": "ERROR",
            "error": open_res.error,
            "turns": turns_out,
            "final_sheet": deepcopy(session.sheet),
            "skill_confidence_series": conf_series,
        }

    # Re-apply mode_state after open if traj asks (placement consumes budget)
    if traj.get("reseed_mode_state_after_open"):
        _apply_mode_state(session, traj["reseed_mode_state_after_open"])

    for i, learner_turn in enumerate(traj.get("turns") or []):
        print(f"\n--- {traj['id']} turn {i + 1} ---")
        tr = session.user_turn(learner_turn)
        _push(learner_turn, tr, is_open=False)
        if tr.error:
            break

    final_sheet = deepcopy(session.sheet)
    session.close(persist_sheet=True)  # only the isolated sheet_path

    return {
        "id": traj["id"],
        **cell,
        "turns": turns_out,
        "final_sheet": final_sheet,
        "skill_confidence_series": conf_series,
        "seed_sheet": seed,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="ConvSession behavioral smoke gate")
    ap.add_argument("prefixes", nargs="*", help="trajectory id prefixes")
    ap.add_argument(
        "--model",
        default=None,
        help=f"tutor model (default: config.MODEL={config.MODEL})",
    )
    ap.add_argument("--pack", type=Path, default=config.DEFAULT_PACK_DIR)
    ap.add_argument("--cell", default=None, help="cell label in results")
    args = ap.parse_args()

    _patch_runtime_for_smoke()
    model = args.model or config.MODEL

    selected = [
        t
        for t in CONV_TRAJECTORIES
        if not args.prefixes
        or any(t["id"].startswith(p) for p in args.prefixes)
    ]
    if not selected:
        raise SystemExit(f"no trajectories matched {args.prefixes!r}")

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = RESULTS_ROOT / stamp
    sheets_dir = outdir / "sheets"
    sheets_dir.mkdir(parents=True, exist_ok=True)

    cell = {
        "arch": "conversational_planned",
        "model": model,
        "teacher_mode": "planned",
        "cell": args.cell or f"conv-{model}",
        "pack": str(args.pack),
    }
    print(
        f"[conv-smoke] model={model} teacher_mode=planned "
        f"n={len(selected)} out={outdir}"
    )
    print(
        f"[conv-smoke] isolation sheets_dir={sheets_dir} "
        f"(not {config.CHARACTER_SHEET_PATH})"
    )

    summary = []
    for traj in selected:
        sheet_path = sheets_dir / f"{traj['id']}.json"
        try:
            result = run_conv_trajectory(
                traj,
                model=model,
                pack_dir=Path(args.pack),
                sheet_path=sheet_path,
                cell=cell,
            )
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            print(f"\n[{traj['id']}] ERROR {err}")
            traceback.print_exc()
            summary.append({
                "id": traj["id"],
                "status": "ERROR",
                "error": err[:500],
            })
            (outdir / f"{traj['id']}.json").write_text(
                json.dumps(
                    {"id": traj["id"], **cell, "status": "ERROR", "error": err},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            continue

        if result.get("error") and not result.get("turns"):
            summary.append({
                "id": traj["id"],
                "status": "ERROR",
                "error": result.get("error"),
            })
        else:
            findings, passed = run_conv_checks(traj, result)
            result["findings"] = findings
            result["mechanical_pass"] = passed
            summary.append({
                "id": traj["id"],
                "status": "PASS" if passed else "FAIL",
                "warns": sum(
                    1
                    for v in findings.values()
                    for f in v
                    if str(f).startswith("WARN")
                ),
                "findings": findings,
                "modes": [t.get("mode") for t in result.get("turns") or []],
            })

        (outdir / f"{traj['id']}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    summary_doc = {
        "cell": cell,
        "stamp": stamp,
        "n": len(selected),
        "results": summary,
        "isolation": {
            "sheets_dir": str(sheets_dir),
            "default_character_sheet_untouched": str(config.CHARACTER_SHEET_PATH),
            "session_log": False,
            "teach_image_generate": False,
        },
    }
    (outdir / "summary.json").write_text(
        json.dumps(summary_doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n{'=' * 50}")
    print(f"Conv mechanical scoreboard [{cell['cell']}] ({outdir}):")
    for row in summary:
        warns = f" ({row['warns']} warns)" if row.get("warns") else ""
        modes = row.get("modes")
        mode_s = f" modes={modes}" if modes else ""
        extra = f" err={row.get('error')}" if row.get("status") == "ERROR" else ""
        print(f"  {row['status']:5} {row['id']}{warns}{mode_s}{extra}")


if __name__ == "__main__":
    main()
```

**Small fix to apply when pasting:** in `conv_trajectories._transfer_seed` I left a dead line with invalid `IP_04=` kw — use only:

```python
def _transfer_seed() -> dict:
    s = _known_sheet()
    note_error_pattern(s, "estar_yo_estoy_vs_esta", "yo está", resolved=False)
    note_error_pattern(s, "estar_yo_estoy_vs_esta", "está bien", resolved=False)
    return s
```

And delete the unused helpers `_turn_record` / incomplete `session_mode_snapshot` in the driver if you want a lean file — runtime path uses the inline `_push` only.

---

## 5. How this maps to requirements

| Req | How met |
|---|---|
| (1) modes exercised | c01…c06 primary; association allows conversation fork |
| (2) mode sets, gate, teach, sheet | `expect.*` + `conv_checks` |
| (3) public API + gaps | §2 table; only shim = `mode_state` attr seed |
| (4) isolate state | per-traj `outdir/sheets/<id>.json`; `log=False`; never default sheet path |
| (5) complete drafts | three modules above |

**Not** a drop-in to `run_checks` / `TRAJECTORIES` — intentional.

---

## 6. Risks

1. **Live model variance on content**, not mode: Spanish wording will drift; checks intentionally avoid string equality on tutor text (except leak markers).
2. **Transfer flakiness:** after `Estoy bien.`, higher-priority guards (`new_noun:cafe`, association) can beat `transfer`. That is why c06 allows `{transfer, conversation, association}` and only WARNs if transfer never appears. Fix later: learner line without association nouns (`Sí. Todo bien ahora.`) or seed `images_shown` / lexicon conf high for café.
3. **c05 depends on open producing a try/model** so session memory has `last_tutor_try`. If open fails pedagogy and leaves empty try, repair may not fire. Mitigate: assert open teach-move first; FAIL open empty.
4. **Hard-break vs seed mistakes:** if someone seeds blank sheet for form_focus, first learner turn cannot form_focus (budget). Arithmetic in §1.
5. **Cost:** real API calls × (1 open + N turns) × optional gate repair (2nd call). Budget ~1–2× turns of tokens vs legacy single path.
6. **Image path:** even with generate off, association still wants cache; pedagogy should proceed without image.
7. **Race:** if `log=True` ever enabled, session files land in shared `logs/sessions/` (unique names — no overwrite, still clutter).
8. **Config import order:** if another import bound `GENERATE_ON_MISS` before patch, images might still generate — keep `_patch_runtime_for_smoke` and early `os.environ`.
9. **False confidence on PASS:** mechanical pass ≠ good teaching; it gates *runtime contracts*. Keep blind transcript review separate (as legacy did with judge_criteria).

---

## 7. Open questions

1. Should **transfer** be a hard FAIL when missing, or stay WARN until noun competition is controlled?
2. Do we want a **`--offline-modes`** arm that only runs `select_mode` on scripted (sheet, learner, memory) fixtures with zero API cost (complements live smoke)? Strongly recommended as CI default; live smoke as nightly.
3. Is **mutating `session.mode_state`** acceptable long-term, or should `ConversationalSession` gain `seed_mode_state: dict | None = None` and `sheet: dict | None = None` ctor args?
4. Should results record **raw model text pre-gate** for repair debugging? Today only post-repair visible is in `TurnResult`.
5. Gate **soft fails** (non-critical faults) currently do not fail the trajectory — intentional floor vs ceiling. Confirm product wants smoke FAIL only on forbidden faults + mode mismatch + empty/error.
6. **c04** with `TEACH_IMAGE_GENERATE=0`: is `image_concept` on `mode_decision` enough for pass, or must `teach_images` be non-empty (would force cache fixtures)?

---

## 8. Recommended apply order

1. Land three files; fix `_transfer_seed` dead code.
2. Run offline unit parity: existing `tests/test_modes.py` already locks guards — no change required for mode truth.
3. `python -m evals.run_conv_smoke c01` (cheapest) → then full suite.
4. Optional follow-up PR: ctor isolation API (`sheet=`, `seed_mode_state=`, `log_dir=`) to remove shims.
5. Do **not** delete legacy `run_smoke` until EXP-001/002 cells are formally retired; dual gates for one transition window.

---

**Bottom line:** Port the *intent* (real pipeline, mechanical contracts, stamped results), not the legacy trajectory schema. Mode-budget arithmetic forces **known-open seeds** for hard breaks and **allow-sets** for association/transfer. Isolation is mandatory via per-run `sheet_path`; default `logs/character_sheet.json` must never be the smoke target.

---

## CLAUDE (Fable 5) — Port adjudication + landing — 2026-07-26

Grok's design accepted with its own two self-flagged fixes applied (`_transfer_seed` dead code; unused driver helpers). Every claimed ConvSession API surface re-verified against `tutor/conv_session.py` / `modes.py` / `character_sheet.py` before landing — all held (ctor kwargs, `close(persist_sheet=)`, `mode_state.snapshot()`, parts keys, `note_error_pattern` signature, pattern ids). One small change vs draft: `sheet_evolution` reads `seed_sheet` from the result record (driver always stores it) rather than the trajectory.

Landed: `evals/conv_trajectories.py` (7 trajectories), `evals/conv_checks.py`, `evals/run_conv_smoke.py`.

**First full live run (`gemini-3.6-flash`): 6/7 PASS; the FAIL was a real product bug** (form_focus hard break on a just-resolved form — fixed in `tutor/modes.py`, see reviews-system-overview.md). After fix: 7/7.

Open questions adjudicated: transfer stays WARN until noun competition controlled (Q1 — agreed); offline `select_mode` CI arm recommended, deferred (Q2); `mode_state` shim acceptable short-term, ctor seeding args are the follow-up PR (Q3); soft gate faults stay non-failing (Q5 — matches product floor/ceiling intent). Legacy `run_smoke` retained for the transition window (apply-order item 5).
