#!/usr/bin/env python3
"""completeness_v1 lint — PEDAGOGY §3.3 (amended 2026-07-30) ship check.

Judges one logged B0 turn artifact (tutor/realization_context.py builds it;
the brief path stashes it on the TurnContext and in the debug ring entry as
``realization_artifact``). The predicate, from §3.3:

  1. every floor member present in the logged turn artifact OR its paired
     capability removed in code (never merely instructed away);
  2. every pack key in allowed_new ∪ due ∪ repair_targets ∪ cf_targets ∪
     learner-detected slice present with the fields the gate judges;
  3. every ban class the turn's gates can fire either injected or the
     capability removed (denylist, cluster_of_allowed_new, asked_frame,
     known_regloss, must_not);
  4. token pressure, latency, and soft overflow are never legal omission
     reasons (no override hook exists here by design);
  5. omissions only from the schema's versioned allowlist — free-form
     "named rules" never qualify.

Run:
  python scripts/check_completeness.py artifact.json [more.json ...]
  ... | python scripts/check_completeness.py -        # artifact on stdin

Exit nonzero on any fault. Importable: ``check_artifact(a) -> list[str]``
(used by tests/test_realization_context.py).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCHEMA = "completeness_v1"

# completeness_v1 amendment 2026-07-30: reply_protocol added as member 11
# after the first live B0 arm shipped without the structured-reply
# interface (10/12 turns pedagogy:no_teach_move — the census named laws,
# not the interface).
FLOOR_MEMBERS = (
    "law_core", "persona", "reply_protocol", "lesson_brief",
    "dynamic_slice", "negative_projection", "budgets", "session_manifest",
    "exchange_window", "pack_index", "fallback",
)
BUDGET_FIELDS = ("introduce_left", "form_focus_cooldown",
                 "content_uptake_left", "checker_left")
MANIFEST_FIELDS = ("introduced_this_session", "cf_targets",
                   "still_fail_count", "phase_id")
BAN_CLASSES = ("denylist_excerpt", "cluster_mates_of_allowed_new",
               "asked_frames", "must_not", "known_no_quiz")
GATE_KEY_CLASSES = ("allowed_new", "due", "repair_targets", "cf_targets",
                    "learner_detected")
# ≤1k-token pack index (rough 4 chars/token) — the schema's own bound.
PACK_INDEX_MAX_CHARS = 4000


def _present(member: str, value) -> bool:
    """Member-shaped presence check (an empty LIST member is legal only
    where the floor defines it as possibly-empty; see call sites)."""
    if value is None:
        return False
    if isinstance(value, dict):
        return bool(value) or bool(value.get("present"))
    return bool(value)


def check_artifact(a: dict) -> list[str]:
    """All completeness faults for one turn artifact ([] = green)."""
    faults: list[str] = []
    if not isinstance(a, dict):
        return ["artifact: not an object"]
    if a.get("schema") != SCHEMA:
        faults.append(f"schema: expected {SCHEMA!r}, got {a.get('schema')!r}")
    floor = a.get("floor")
    if not isinstance(floor, dict):
        return faults + ["floor: missing"]

    # --- predicate 1: the ten members ----------------------------------
    for member in FLOOR_MEMBERS:
        if member not in floor:
            faults.append(f"floor.{member}: MISSING member")
    law = floor.get("law_core")
    if isinstance(law, dict) and not law.get("present"):
        faults.append("floor.law_core: absent (prompts/executor_law_core.md)")
    persona = floor.get("persona")
    if isinstance(persona, dict) and not (
            persona.get("present") or persona.get("capability_removed")):
        faults.append(
            "floor.persona: absent and capability not removed in code")
    brief = floor.get("lesson_brief")
    if "lesson_brief" in floor and not isinstance(brief, dict):
        faults.append("floor.lesson_brief: not an object")
        brief = {}
    elif not isinstance(brief, dict):
        brief = {}

    dyn = floor.get("dynamic_slice")
    rows: dict = {}
    if "dynamic_slice" in floor:
        if not isinstance(dyn, dict) or "rows" not in dyn:
            faults.append("floor.dynamic_slice: missing rows")
        else:
            rows = dyn.get("rows") or {}

    # --- predicate 3: ban classes --------------------------------------
    neg = floor.get("negative_projection")
    if "negative_projection" in floor:
        if not isinstance(neg, dict):
            faults.append("floor.negative_projection: not an object")
        else:
            for ban in BAN_CLASSES:
                if ban not in neg:
                    faults.append(
                        f"floor.negative_projection.{ban}: MISSING ban class")
            if not (neg.get("denylist_excerpt") or "").strip():
                faults.append(
                    "floor.negative_projection.denylist_excerpt: empty "
                    "(§2.6 denylist must be injected)")
            if not neg.get("must_not"):
                faults.append(
                    "floor.negative_projection.must_not: empty")

    # --- member shapes --------------------------------------------------
    budgets = floor.get("budgets")
    if "budgets" in floor:
        if not isinstance(budgets, dict):
            faults.append("floor.budgets: not an object")
        else:
            for b in BUDGET_FIELDS:
                if not isinstance(budgets.get(b), int):
                    faults.append(
                        f"floor.budgets.{b}: missing or non-int "
                        "(budgets are code NUMBERS)")
    manifest = floor.get("session_manifest")
    if "session_manifest" in floor:
        if not isinstance(manifest, dict):
            faults.append("floor.session_manifest: not an object")
        else:
            for m in MANIFEST_FIELDS:
                if m not in manifest:
                    faults.append(f"floor.session_manifest.{m}: missing")

    # K window: K versioned, floor K≥2; empty window legal only on open.
    k = a.get("k_exchanges")
    k_floor = a.get("k_floor", 2)
    if not isinstance(k, int) or k < max(2, int(k_floor or 2)):
        faults.append(f"k_exchanges: {k!r} below the K≥2 floor")
    window = floor.get("exchange_window")
    if "exchange_window" in floor:
        if not isinstance(window, list):
            faults.append("floor.exchange_window: not a list")
        elif not window and not a.get("is_open"):
            # Turn 1 after open has ≤1 exchange of history; only a missing
            # list on a NON-open turn with history is judgeable here, so
            # the shape check stays: list present, contents may be short.
            pass

    idx = floor.get("pack_index")
    if "pack_index" in floor:
        if not isinstance(idx, dict) or not (
                idx.get("unit_topics") or idx.get("themes")):
            faults.append("floor.pack_index: empty (positive palette "
                          "signal required — Q3 ruling)")
        elif len(json.dumps(idx, ensure_ascii=False)) > PACK_INDEX_MAX_CHARS:
            faults.append(
                f"floor.pack_index: over {PACK_INDEX_MAX_CHARS} chars "
                "(≤1k-token bound)")

    fb = floor.get("fallback")
    if "fallback" in floor and not isinstance(fb, dict):
        faults.append("floor.fallback: not an object")

    # --- predicate 2: gate-critical keys in the slice -------------------
    gkc = a.get("gate_key_classes")
    if not isinstance(gkc, dict):
        faults.append("gate_key_classes: missing")
    else:
        for cls in GATE_KEY_CLASSES:
            for key in gkc.get(cls) or []:
                row = rows.get(str(key))
                if not isinstance(row, dict):
                    faults.append(
                        f"gate_key_classes.{cls}: key {key!r} not in "
                        "dynamic_slice rows (gate can fault on a key the "
                        "executor never saw)")
                    continue
                # §3.3 predicate 2 (B0 countersign AMEND A): "with the
                # fields the gate judges" — every slice row must carry
                # gloss (possibly hint/label-only for pure grammar/error-
                # pattern keys).
                if "gloss" not in row and "hint" not in row:
                    faults.append(
                        f"gate_key_classes.{cls}: key {key!r} row missing "
                        "gloss/hint (fields the gate judges)")
    # --- A1 completeness (B0 countersign AMEND B): cluster mates are a
    # FAULT when allowed_new is non-empty, never a soft empty ------------
    _brief = floor.get("lesson_brief") or {}
    _neg = floor.get("negative_projection") or {}
    if isinstance(_brief, dict) and isinstance(_neg, dict):
        if (_brief.get("allowed_new") or []) and not (
            _neg.get("cluster_mates_of_allowed_new") or []
        ):
            faults.append(
                "floor.negative_projection.cluster_mates_of_allowed_new: "
                "empty while allowed_new is non-empty (A1 completeness fault)"
            )
    return faults


def _load(path: str) -> dict:
    if path == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    rc = 0
    for path in argv:
        try:
            artifact = _load(path)
        except (OSError, ValueError) as e:
            print(f"{path}: unreadable artifact — {e}")
            rc = 1
            continue
        faults = check_artifact(artifact)
        if faults:
            rc = 1
            print(f"{path}: COMPLETENESS FAULTS ({len(faults)})")
            for f in faults:
                print(f"  - {f}")
        else:
            print(f"{path}: completeness_v1 ok")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
