"""EXP-003 harness gate: validate a structured directive before the executor is
called. Grok run-1 fork(a): refuse to ship a malformed/ghostwriting directive —
the compiler-refuses-a-parse-error discipline, not prompt-warfare on the gate.

`check_directive` returns (ok, findings). The caller (run_planned_turn, EXP-003
path) re-plans once on failure and hard-fails the turn on a second failure;
replan-rescued turns are logged and excluded from the primary discourse count
per Grok countersign item (3).
"""

from evals.checks import MOVES, directive_no_ghostwrite

REQUIRED = ("pedagogical_move_present", "move", "target", "withhold",
            "frame", "elicit", "intent")
FRAME_KEYS = ("lang", "register", "character", "max_lines")


def schema_errors(d: dict) -> list[str]:
    """Structural validity, independent of output_config (belt-and-suspenders)."""
    errs = []
    if not isinstance(d, dict):
        return [f"directive is {type(d).__name__}, not object"]
    for k in REQUIRED:
        if k not in d:
            errs.append(f"missing field {k!r}")
    if not isinstance(d.get("pedagogical_move_present"), bool):
        errs.append("pedagogical_move_present not a boolean")
    move = d.get("move")
    if move not in MOVES:
        errs.append(f"move {move!r} not in enum")
    frame = d.get("frame")
    if not isinstance(frame, dict) or any(k not in frame for k in FRAME_KEYS):
        errs.append("frame is not the required tag object")
    # Consistency: present is false iff move is passthrough.
    present = d.get("pedagogical_move_present")
    if isinstance(present, bool) and (present == (move == "passthrough")):
        errs.append(
            f"present={present} inconsistent with move={move!r} "
            "(passthrough iff not present)")
    return errs


def check_directive(directive: dict, visible: str = "") -> tuple[bool, list[str]]:
    """Gate a directive before the executor runs. `visible` is empty pre-exec
    (no tutor turn yet), so the run rule only catches directive-internal quotes
    and reveal-risk; the shared-run-vs-visible check runs post-hoc in scoring.

    Re-plan is triggered by (a) any schema error, (b) any hard ghostwrite
    finding, or (c) a reveal-risk WARN (over-specified target/elicit — cheap to
    fix in the loop). Reveal-risk is a re-plan trigger, NOT a scoring void:
    diagnostic 1 showed a hard rule over-fires on grammatical metalanguage."""
    errs = list(schema_errors(directive))
    gw = directive_no_ghostwrite(
        None, {"turns": [{"directive": directive, "visible": visible}]})
    errs += [f for f in gw
             if not f.startswith("WARN") or "reveal risk" in f]
    return (not errs), errs
