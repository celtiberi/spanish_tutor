"""Mechanical checks for ConvSession smoke trajectories (no LLM judging).

Findings prefixed WARN are advisory; any non-WARN finding fails the trajectory.

Typed-event migration (Phase 3 batch 2, docs/reviews-architecture-refactor.md)
------------------------------------------------------------------------------
run_conv_smoke records each turn's serialized TurnEvent timeline under
``turn["events"]`` (kind/key/payload/seq/stage — tutor/turn_events.py).  Every
checker that historically parsed note-string prefixes now PREFERS the typed
events and falls back to the note strings ONLY when a turn record carries no
``events`` key — eval results are historical artifacts and old recorded runs
must stay replayable.

DECLARED TIGHTENING on the event path (accidental-substring false positives
the string scans could produce are impossible against typed kinds):
  - ``recast_or_gate_attempt``: the joined-notes substring scans
    ("output_gate" / "missing_recast") become precise checks — any of the six
    ``output_gate*`` event KINDS, and the ``gate:missing_recast`` fault id
    inside gate-fail event payloads.  A payload that merely CONTAINED either
    substring (e.g. a ``why=``/reason text mentioning "output_gate") no
    longer counts as gate evidence.
  - ``due_elicit_fired`` / ``introduce_scaffolded`` / ``task_goal_offered``:
    substring scans over whole notes become event-kind checks — a payload
    accidentally containing "due_elicit_offered" / "introduce_planned:" /
    "task_goal_offered:" no longer satisfies the expectation.
  - ``_mode`` / ``phase_adherence`` / ``uptake_flag_honored`` /
    ``progress_milestones_fired``: same answers by construction (their
    string parses were prefix-anchored); the event path simply reads
    kind/key/payload instead of splitting strings.
"""

from __future__ import annotations

import re


def _turns(result: dict) -> list[dict]:
    return list(result.get("turns") or [])


def _events(turn: dict) -> list[dict] | None:
    """The turn's serialized TurnEvent timeline, or None for records made
    before Phase 3 batch 2 (replay fallback → note strings)."""
    ev = turn.get("events")
    if not isinstance(ev, list):
        return None
    return [e for e in ev if isinstance(e, dict)]


def _events_of(turn: dict, *kinds: str) -> list[dict] | None:
    evs = _events(turn)
    if evs is None:
        return None
    want = set(kinds)
    return [e for e in evs if str(e.get("kind")) in want]


# The six gate event kinds (tutor/turn_events.py OUTPUT_GATE_*).
_GATE_EVENT_KINDS = (
    "output_gate_ok",
    "output_gate_soft_fail",
    "output_gate_fail",
    "output_gate_repaired",
    "output_gate_still_fail",
    "output_gate_error",
)
_GATE_FAIL_EVENT_KINDS = (
    "output_gate_soft_fail",
    "output_gate_fail",
    "output_gate_still_fail",
)


def _mode(turn: dict) -> str | None:
    parts = turn.get("parts") or {}
    m = parts.get("mode")
    if m:
        return str(m)
    md = parts.get("mode_decision") or {}
    if isinstance(md, dict) and md.get("mode"):
        return str(md["mode"])
    # typed events (preferred), then legacy notes fallback: mode=foo
    for e in _events_of(turn, "mode") or []:
        if e.get("key"):
            return str(e["key"])
    for n in turn.get("notes") or []:
        s = str(n)
        if s.startswith("mode="):
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
        for k in spec.get("require") or []:
            if not _truthy(parts, k):
                findings.append(f"turn {i}: missing required teach part <{k}>")
        any_of = list(spec.get("any_of") or [])
        if any_of and not any(_truthy(parts, k) for k in any_of):
            findings.append(f"turn {i}: no teach move in any_of={any_of}")
        if spec.get("open_prefer_model_and_try") and i == 0:
            if not (_truthy(parts, "model") and _truthy(parts, "try")):
                # Soft: pedagogy contract also flags; WARN not hard fail
                findings.append(
                    "WARN turn 0: open without both <model> and <try>"
                )
    return findings


def open_english_orientation(traj: dict, result: dict) -> list[str]:
    """True-zero open must carry English support (incident 2026-07-28).

    Mechanical, applies only when expect.open_english is set (blank-sheet
    trajectories): the open reply must show at least one English hit from
    the gate's closed lexicon OR a parenthetical gloss containing letters
    (the app's gloss convention). The failing shape it catches is exactly
    the incident: a 100%-Spanish opening at a learner with a wiped sheet.
    """
    if not (traj.get("expect") or {}).get("open_english"):
        return []
    turns = _turns(result)
    if not turns:
        return ["no open turn recorded"]
    visible = str(turns[0].get("visible") or turns[0].get("reply") or "")
    from tutor.output_gate import spanish_token_ratio

    has_en_lexicon = spanish_token_ratio(visible) < 1.0
    has_gloss_paren = bool(re.search(r"\([^)]*[A-Za-z]{2,}[^)]*\)", visible))
    if not (has_en_lexicon or has_gloss_paren):
        return [
            "turn 0: true-zero open shows no English orientation "
            "(no English lexicon hit, no gloss parenthetical): "
            + visible[:120].replace("\n", " ")
        ]
    return []


def gate_contract(traj: dict, result: dict) -> list[str]:
    specs = (traj.get("expect") or {}).get("gate") or []
    turns = _turns(result)
    findings = []
    n = min(len(turns), len(specs))
    for i in range(n):
        spec = specs[i] or {}
        faults = list(_gate(turns[i]).get("faults") or [])
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
    """For cf_recast turns: either recast text present or gate flagged it.

    Event path (preferred): a gate signal is any of the six ``output_gate*``
    event KINDS or a ``missing_recast`` fault id inside a gate-fail event's
    payload — TIGHTENED vs the legacy joined-notes substring scan, which an
    unrelated payload containing "output_gate"/"missing_recast" could
    satisfy accidentally (declared improvement, module docstring)."""
    findings = []
    for i, t in enumerate(_turns(result)):
        if _mode(t) != "cf_recast":
            continue
        parts = _parts(t)
        if _truthy(parts, "recast"):
            continue
        gate_faults = _gate(t).get("faults") or []
        if "gate:missing_recast" in gate_faults:
            findings.append(
                f"WARN turn {i}: cf_recast still missing <recast> after gate"
            )
            continue
        gate_evs = _events_of(t, *_GATE_EVENT_KINDS)
        if gate_evs is not None:
            gate_signal = bool(gate_evs) or any(
                "missing_recast" in str(f)
                for e in _events_of(t, *_GATE_FAIL_EVENT_KINDS) or []
                for f in (e.get("payload") or {}).get("faults") or []
            )
        else:  # replay fallback: old records without events
            notes = " ".join(str(n) for n in (t.get("notes") or []))
            gate_signal = "output_gate" in notes or "missing_recast" in notes
        if gate_signal:
            findings.append(
                f"WARN turn {i}: cf_recast without recast part (gate notes only)"
            )
            continue
        findings.append(f"turn {i}: cf_recast without <recast> and no gate signal")
    return findings


# Confirming praise («¡Sí!», «¡Exacto!», «¡Perfecto!») — exclamation-shaped
# only, so plain content «sí» never warns (WARN-level: wording variety makes
# a hard fail brittle; PEDAGOGY §2.5 amended, blind-grade defect #3).
_PRAISE_ON_RECAST_RE = re.compile(
    r"¡\s*(?:s[ií]|exacto|perfecto)\b|\b(?:exacto|perfecto)\s*!", re.I
)


def recast_no_confirm_praise(traj: dict, result: dict) -> list[str]:
    """WARN: confirming praise in the acknowledge of a turn carrying <recast>.

    §2.5 amended (2026-07-28): never confirm/praise an incorrect form on a
    turn you are recasting — acknowledge the meaning, recast the form.
    Advisory only (never a hard fail)."""
    findings = []
    for i, t in enumerate(_turns(result)):
        parts = _parts(t)
        if not _truthy(parts, "recast"):
            continue
        ack = str(parts.get("acknowledge") or "")
        m = _PRAISE_ON_RECAST_RE.search(ack)
        if m:
            findings.append(
                f"WARN turn {i}: confirming praise {m.group(0)!r} in "
                "acknowledge on a recast turn (§2.5: never praise the form "
                "you are fixing)"
            )
    return findings


def uptake_flag_honored(traj: dict, result: dict) -> list[str]:
    """WARN: a turn noted uptake_flagged:<token> → the reply should carry a
    target for the flagged form (the token itself, or a recast/model/explain
    part, or a gloss parenthetical).

    §2.1a instruction path, measurement-first per the closed content-uptake
    review (no gate until detection precision is measured)."""
    findings = []
    for i, t in enumerate(_turns(result)):
        evs = _events_of(t, "uptake_flagged")
        if evs is not None:  # typed events (preferred)
            toks = [str(e.get("key") or "") for e in evs if e.get("key")]
        else:  # replay fallback
            toks = [
                str(n).split(":", 1)[1]
                for n in (t.get("notes") or [])
                if str(n).startswith("uptake_flagged:")
            ]
        if not toks:
            continue
        parts = _parts(t)
        reply = str(t.get("visible") or t.get("reply") or "").lower()
        gave_form = (
            _truthy(parts, "recast")
            or _truthy(parts, "model")
            or _truthy(parts, "explain")
            or "(" in reply
        )
        for tok in toks:
            if tok.lower() in reply or gave_form:
                continue
            findings.append(
                f"WARN turn {i}: uptake_flagged:{tok} but no target form "
                "visible in the reply (no recast/model/explain/gloss)"
            )
    return findings


def sheet_evolution(traj: dict, result: dict) -> list[str]:
    spec = (traj.get("expect") or {}).get("sheet_final") or {}
    sheet = result.get("final_sheet") or {}
    findings = []

    # Personal-data capture is disabled (2026-07-28): a stored name is a
    # leak in EVERY trajectory — absence is the only legal state. This check
    # is UNCONDITIONAL: the legacy `preferred_name` equality expectation is
    # gone, and the `preferred_name_absent` spec key is still accepted for
    # compat but no flag can turn this check off.
    profile = result.get("final_profile") or {}
    stored = (
        profile.get("preferred_name")
        or (sheet.get("identity") or {}).get("preferred_name")
        or ""
    ).strip()
    if stored:
        findings.append(
            f"personal-data leak: preferred_name stored as {stored!r} "
            "(capture is disabled)"
        )

    if not spec:
        return findings

    for pid, vmin in (spec.get("error_pattern_min") or {}).items():
        ent = (sheet.get("error_patterns") or {}).get(pid) or {}
        c = int(ent.get("count") or 0)
        if c < int(vmin):
            findings.append(f"error_patterns[{pid}].count={c} < min {vmin}")

    direction = spec.get("error_pattern_resolved_direction") or {}
    if direction:
        pid = direction.get("pattern")
        ent = (sheet.get("error_patterns") or {}).get(pid) or {}
        streak = int(ent.get("resolved_streak") or 0)
        min_s = int(direction.get("min_resolved_streak") or 1)
        if streak < min_s:
            # Also accept count drop vs seed if seed provided
            seed_eps = (result.get("seed_sheet") or {}).get("error_patterns") or {}
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
            findings.append(f"skills[{cid}].confidence={conf:.3f} < min {vmin}")

    for cid, want_dir in (spec.get("skill_confidence_direction") or {}).items():
        series = result.get("skill_confidence_series") or {}
        vals = series.get(cid) or []
        if len(vals) < 2:
            findings.append(f"WARN no confidence series for {cid}")
            continue
        delta = float(vals[-1]) - float(vals[0])
        if want_dir == "up" and delta <= 0:
            findings.append(
                f"skills[{cid}] expected up, delta={delta:.3f} "
                f"({vals[0]:.3f}→{vals[-1]:.3f})"
            )
        if want_dir == "down" and delta >= 0:
            findings.append(f"skills[{cid}] expected down, delta={delta:.3f}")

    return findings


def association_signal(traj: dict, result: dict) -> list[str]:
    """Pass if the learner turn is association OR conversation carrying bote."""
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
    return [
        f"turn 1: expected association signal (mode/image bote), "
        f"got mode={mode!r} image_concept={img!r} teach={concepts!r}"
    ]


def comprehension_repair_targets(traj: dict, result: dict) -> list[str]:
    findings = []
    for i, t in enumerate(_turns(result)):
        if _mode(t) != "comprehension_repair":
            continue
        md = _parts(t).get("mode_decision") or {}
        targets = (md.get("targets") or {}) if isinstance(md, dict) else {}
        if not targets.get("require_same_topic") and not targets.get(
            "forbid_new_topic"
        ):
            findings.append(
                f"turn {i}: comprehension_repair missing same-topic targets"
            )
        if not _truthy(_parts(t), "try") and not _truthy(_parts(t), "model"):
            findings.append(f"turn {i}: comprehension_repair without model/try")
    return findings


def due_elicit_fired(traj: dict, result: dict) -> list[str]:
    """expect.due_elicit=true → some turn's notes must carry due_elicit_offered.

    Phase 1 retrieval scheduler (docs/build-plan-pedagogy-engine.md): a
    past-due sheet item must ride at least one conversation-flavored turn
    as a DUE RE-ENCOUNTERS instruction (soft; logged in notes).
    """
    if not (traj.get("expect") or {}).get("due_elicit"):
        return []
    for t in _turns(result):
        evs = _events_of(t, "due_elicit_offered")
        if evs is not None:  # typed events (preferred; kind-precise)
            if evs:
                return []
            continue
        for n in t.get("notes") or []:  # replay fallback (substring scan)
            if "due_elicit_offered" in str(n):
                return []
    return [
        "expect.due_elicit: no turn notes contained due_elicit_offered"
    ]


def progress_milestones_fired(traj: dict, result: dict) -> list[str]:
    """expect.progress_milestones: ["<kind>:<key>", ...] → each must appear
    EXACTLY ONCE across all turn notes as progress_milestone:<kind>:<key>.

    Journey rail honesty (docs/design-progression-view.md, as amended;
    PEDAGOGY §3): the milestone must fire when its code-owned evidence event
    lands, and an up-crossing never fires twice for one key (dedupe law).
    """
    want = list((traj.get("expect") or {}).get("progress_milestones") or [])
    if not want:
        return []
    # Per turn: typed events (preferred; identical answers — the string
    # match was already exact) with note-string replay fallback.
    notes: list[str] = []
    for t in _turns(result):
        evs = _events_of(t, "progress_milestone")
        if evs is not None:
            notes.extend(
                "progress_milestone:"
                f"{(e.get('payload') or {}).get('milestone')}:{e.get('key')}"
                for e in evs
            )
        else:
            notes.extend(str(n) for n in (t.get("notes") or []))
    out: list[str] = []
    for w in want:
        tag = f"progress_milestone:{w}"
        hits = sum(1 for n in notes if n == tag)
        if hits == 0:
            out.append(
                f"expect.progress_milestones: {tag!r} never appeared in notes"
            )
        elif hits > 1:
            out.append(
                f"expect.progress_milestones: {tag!r} fired {hits}x "
                "(up-crossings must dedupe to once per key)"
            )
    return out


def introduce_scaffolded(traj: dict, result: dict) -> list[str]:
    """expect.introduce_planned=true → some turn's notes must carry
    introduce_planned:<key>:<rule>.

    Phase 3 introduce router (docs/build-plan-pedagogy-engine.md): on a
    new_input-phase flavorable turn the code-owned IntroducePlan must ride
    the tutor instructions (logged in notes). Note presence only — whether
    the same turn later marks (introduced:<key>) or the plan lapses is the
    model's realization and is intentionally NOT asserted (non-flaky).
    """
    if not (traj.get("expect") or {}).get("introduce_planned"):
        return []
    for t in _turns(result):
        evs = _events_of(t, "introduce_planned")
        if evs is not None:  # typed events (preferred; kind-precise)
            if evs:
                return []
            continue
        for n in t.get("notes") or []:  # replay fallback (substring scan)
            if "introduce_planned:" in str(n):
                return []
    return [
        "expect.introduce_planned: no turn notes contained introduce_planned"
    ]


def task_goal_offered(traj: dict, result: dict) -> list[str]:
    """expect.task_instructions_offered=true → some turn's notes must carry
    task-phase evidence: task_goal_offered:<scene_id> (the ConvergentTask
    block was attached to the tutor instructions) or task_slot_filled:<id>
    (the learner's own text filled an info-gap slot).

    Phase 5 task wiring (docs/build-plan-pedagogy-engine.md): on task-phase
    flavorable turns the code-owned TaskState must ride the tutor
    instructions. Note presence only — task completion is the learner's
    realization and is intentionally NOT asserted (non-flaky)."""
    if not (traj.get("expect") or {}).get("task_instructions_offered"):
        return []
    for t in _turns(result):
        evs = _events_of(t, "task_goal_offered", "task_slot_filled")
        if evs is not None:  # typed events (preferred; kind-precise)
            if evs:
                return []
            continue
        for n in t.get("notes") or []:  # replay fallback (substring scan)
            s = str(n)
            if "task_goal_offered:" in s or "task_slot_filled:" in s:
                return []
    return [
        "expect.task_instructions_offered: no turn notes contained "
        "task_goal_offered/task_slot_filled"
    ]


def phase_adherence(traj: dict, result: dict) -> list[str]:
    """expect.phase_sequence → each turn's notes must carry the expected
    activity= value (same [open]+turns alignment as mode_sets; entries may be
    a single activity string or a list of allowed activities; empty = skip).

    Phase 2 session-phase layer (docs/build-plan-pedagogy-engine.md): the
    activity_type is code-decided and logged per turn. Per-turn mismatches
    are WARN; adherence = matching/total hard-fails below
    expect.phase_adherence_min (default 0.8).
    """
    expect = traj.get("expect") or {}
    seq = expect.get("phase_sequence") or []
    if not seq:
        return []
    try:
        min_adherence = float(expect.get("phase_adherence_min") or 0.8)
    except (TypeError, ValueError):
        min_adherence = 0.8
    turns = _turns(result)
    findings: list[str] = []
    if len(turns) != len(seq):
        findings.append(
            f"turn count {len(turns)} != expect.phase_sequence length {len(seq)}"
        )
    matching = 0
    total = 0
    n = min(len(turns), len(seq))
    for i in range(n):
        allowed = seq[i]
        if not allowed:
            continue
        if isinstance(allowed, str):
            allowed = [allowed]
        total += 1
        got = None
        evs = _events_of(turns[i], "activity")
        if evs is not None:  # typed events (preferred)
            if evs:
                got = str(evs[0].get("key") or "").strip() or None
        else:  # replay fallback
            for note in turns[i].get("notes") or []:
                s = str(note)
                if s.startswith("activity="):
                    got = s.split("=", 1)[1].strip()
                    break
        if got in set(allowed):
            matching += 1
        else:
            findings.append(
                f"WARN turn {i}: activity {got!r} not in allowed "
                f"{sorted(allowed)}"
            )
    if total:
        ratio = matching / total
        if ratio < min_adherence:
            findings.append(
                f"phase adherence {matching}/{total}={ratio:.2f} "
                f"< min {min_adherence:.2f}"
            )
    return findings


def transfer_seen_or_warn(traj: dict, result: dict) -> list[str]:
    want = (traj.get("expect") or {}).get("require_mode_somewhere") or []
    if not want:
        return []
    seen = {_mode(t) for t in _turns(result)}
    return [
        f"WARN required mode {m!r} never observed "
        f"(seen={sorted(x for x in seen if x)})"
        for m in want
        if m not in seen
    ]


CHECKS = {
    f.__name__: f
    for f in (
        no_empty_reply,
        no_turn_error,
        mode_sequence,
        teach_moves,
        open_english_orientation,
        gate_contract,
        recast_or_gate_attempt,
        recast_no_confirm_praise,
        uptake_flag_honored,
        sheet_evolution,
        association_signal,
        comprehension_repair_targets,
        due_elicit_fired,
        progress_milestones_fired,
        introduce_scaffolded,
        task_goal_offered,
        phase_adherence,
        transfer_seen_or_warn,
    )
}


def run_conv_checks(traj: dict, result: dict) -> tuple[dict, bool]:
    names = list(traj.get("mechanical") or [])
    # Always run core safety checks. sheet_evolution is core since 2026-07-28:
    # its unconditional no-stored-name check must cover every trajectory.
    # recast_no_confirm_praise + uptake_flag_honored are WARN-only
    # measurement checks (2026-07-28, §2.5 amended / §2.1a) — advisory on
    # every trajectory, never a hard fail.
    for core in (
        "no_empty_reply",
        "no_turn_error",
        "sheet_evolution",
        "recast_no_confirm_praise",
        "uptake_flag_honored",
    ):
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
