"""Phase 0 batch 2 — AI-path arc goldens (gate fail surface / comprehension repair /
budget arcs / close phase) + CHAR-BUG-005.

Extends the batch-1 harness (tests/conftest.py + tests/
test_characterization_ai_path.py — fixtures and golden format REUSED, not
forked) per the adjudicated Phase 0 spec and the batch-2 runbook in
docs/reviews-architecture-refactor.md:

  - gate-fault → NO repair (2026-08-01): critical fault ships raw + gate_fail;
    second model call deleted (hiding path removed).
  - comprehension repair: meta "what does X mean" turn → phase clock FROZEN,
    repair-target image relevance (no irrelevant image — the incident
    class), await/TTL hold armed then cleared by the learner's own Spanish.
  - budget arcs (multi-turn): introduce budget 2→1→0 with the third plan
    refused (R-G) and the §2.1a self-flag uptake budget (fires once, the
    consecutive flag blocked, recovers after the ≥3-turn window).
  - close phase: summary block content sources + the SESSION PHASE: CLOSE
    prefix; phase clock walks off the plan end afterwards.
  - CHAR-BUG-005: RESOLVED-BY-DELETION (Proposal A micro-batch, 2026-07-29)
    — the pin now asserts the scene_modeled machine is GONE.

Taxonomy: CHAR_PIN / CHAR_BUG / CHAR_DIVERGE (Grok round-1 (c) replacement
text, BINDING). Goldens regenerate ONLY via CHAR_GOLDEN_UPDATE=1 (never CI);
CHAR_BUG pins flip only with the paired bugfix PR + registry update
(tests/characterizations/known_bugs.json).
"""

from __future__ import annotations

from conftest import check_golden, note_families

from test_characterization_ai_path import (
    OPEN_KNOWN_REPLY,
    TURN_INTRO_REPLY,
    _known_seed,
    _observe,
)

# ---------------------------------------------------------------------------
# Canned replies
# ---------------------------------------------------------------------------

# Reply 1 for the repair golden: bare unintroduced table key «mucho gusto»
# (never seen, no gloss/anchor, not the planned introduce key) → CRITICAL
# gate:unscaffolded_new_item. «hola» is this turn's IntroducePlan key and is
# exempt from the bare scan (the introduce path owns its lapse).
GATE_BAD_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Hola!</acknowledge>\n"
    "  <model>**Mucho gusto**.</model>\n"
    "  <try>Di: **mucho gusto**.</try>\n"
    "</tutor>"
)

# Comprehension repair turn: explain + simpler model of the SAME idea; only
# structural keys («estoy») — no table-key faults, no new-topic jump.
REPAIR_TURN_REPLY = (
    "<tutor>\n"
    "  <explain>Contento means happy.</explain>\n"
    "  <model>**Estoy contento** (I'm happy).</model>\n"
    "  <try>Di: **Estoy contento**.</try>\n"
    "</tutor>"
)

# The turn after the repair: learner produced their own Spanish → hold clears.
REPAIR_CLEAR_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Perfecto!</acknowledge>\n"
    "  <model>**Estoy en el bote.**</model>\n"
    "  <try>¿Dónde estás tú?</try>\n"
    "</tutor>"
)

# Budget arc turn 2: realizes the SECOND introduce plan («buenos días», R-D
# single ≤6-word micro-gloss) — consumes the last budget slot.
# t2 introduces the router's second plan. Key changed buenos días→soy
# 2026-07-29 (encounter-variety round: _known_seed is mid-stream, openers
# sort last — the second content candidate after «me llamo» is «soy»).
ARC_INTRO2_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Perfecto!</acknowledge>\n"
    "  <model>Para presentarte también dices **soy** (I am): Soy "
    "Marisol.</model>\n"
    "  <try>Di: **Soy** y tu nombre.</try>\n"
    "</tutor>"
)

# Budget arc turns 3/4: table-key-free conversation replies (no gate faults,
# nothing introduced — the R-G refusal and uptake-budget behavior are the
# pins, not the reply content).
ARC_PLAIN_REPLY_3 = (
    "<tutor>\n"
    "  <acknowledge>¡Perfecto!</acknowledge>\n"
    "  <model>Yo hablo mucho también.</model>\n"
    "  <try>¿Hablas conmigo un poco más?</try>\n"
    "</tutor>"
)
ARC_PLAIN_REPLY_4 = (
    "<tutor>\n"
    "  <acknowledge>¡Claro!</acknowledge>\n"
    "  <model>**Quiero leche** — I want milk.</model>\n"
    "  <try>¿Quieres leche en el desayuno?</try>\n"
    "</tutor>"
)

# Close-phase reply: the one-English-line summary + a glossed farewell (bare
# «adiós» would be a critical first exposure; the gloss saves it → first_seen).
CLOSE_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Muy bien!</acknowledge>\n"
    "  <model>Hoy practicaste saludos — today you practiced greetings. "
    "**Adiós** (goodbye).</model>\n"
    "  <try>Di: **adiós** (goodbye).</try>\n"
    "</tutor>"
)


# ---------------------------------------------------------------------------
# Golden (iv): gate-fault surfaces — NO repair rewrite (2026-08-01)
# ---------------------------------------------------------------------------


def test_golden_gate_fault_surfaces_no_repair(tutor_session_factory):
    ctx = tutor_session_factory(
        seed_sheet=_known_seed(),
        replies=[OPEN_KNOWN_REPLY, GATE_BAD_REPLY],
    )
    s = ctx.session
    assert s.open_session().error is None
    n_open = len(ctx.save_calls)

    turn = s.user_turn("Muy bien, gracias.")
    assert turn.error is None

    # CHAR_PIN: critical fault logged; never rewritten or blanked.
    assert "output_gate_fail:gate:unscaffolded_new_item" in turn.notes
    assert "output_gate_repaired" not in turn.notes
    assert "output_gate_recovered" not in turn.notes
    assert "output_gate_ok" not in turn.notes
    assert len(ctx.fake.requests) == 2  # open + turn only (no repair call)

    # CHAR_PIN: single model call usage for the user turn (no second bill).
    assert turn.usage == {
        "input_tokens": 120, "output_tokens": 60,
        "thinking_tokens": 0, "cached_input_tokens": 0,
    }

    # CHAR_PIN: raw failing attempt ships; gate_fail banner for the client.
    assert "Mucho gusto" in turn.reply
    assert turn.parts.get("gate_fail") is True
    gate = turn.parts["output_gate"]
    assert gate["ok"] is False
    assert "gate:unscaffolded_new_item" in (gate.get("faults") or [])
    assert ctx.save_calls[n_open:] == ["_commit_sheet"]

    # CHAR_PIN: planned key lapsed (absent from reply) — no introduced: write.
    assert "introduce_planned:me llamo:R-D" in turn.notes
    assert not any(n.startswith("introduced:") for n in turn.notes)
    assert s.pedagogy_memory.intro_budget_remaining() == 2

    obs = _observe(
        ctx, turn, save_slice=slice(n_open, None),
        sheet_keys=(("lexicon", "mucho gusto"), ("lexicon", "me llamo")),
    )
    obs["learner"] = "Muy bien, gracias."
    obs["gate_surface"] = {
        "requests_this_turn": 1,
        "gate_fail": True,
        "faults": list(gate.get("faults") or []),
        "no_repair": True,
    }
    check_golden("golden_gate_repair_turn", obs)


# ---------------------------------------------------------------------------
# Golden (v): comprehension repair — frozen clock, image relevance, hold TTL
# ---------------------------------------------------------------------------


def test_golden_comprehension_repair(tutor_session_factory):
    ctx = tutor_session_factory(
        seed_sheet=_known_seed(),
        replies=[OPEN_KNOWN_REPLY, REPAIR_TURN_REPLY, REPAIR_CLEAR_REPLY],
    )
    s = ctx.session
    assert s.open_session().error is None
    n_open = len(ctx.save_calls)
    # The open's model/try are the repair targets remembered by the session.
    assert s.pedagogy_memory.last_tutor_try == "¿Estás contento hoy también?"

    turn = s.user_turn("What does contento mean?")
    assert turn.error is None

    # CHAR_PIN: meta turn → comprehension_repair hard break, same-topic
    # targets carry the remembered try/model, phase clock FROZEN.
    assert turn.parts["mode"] == "comprehension_repair"
    assert "mode_reason=meta_comprehension_stay_on_topic" in turn.notes
    assert "hard_break=True" in turn.notes
    assert "phase_consumed=False" in turn.notes
    assert s.phase_state.index == 0
    assert s.phase_state.turns_in_phase == 1  # only the open consumed
    assert s.phase_state.frozen_turns == 1
    targets = turn.parts["mode_decision"]["targets"]
    assert targets["last_try"] == "¿Estás contento hoy también?"
    assert targets["require_same_topic"] is True
    assert targets["forbid_new_topic"] is True

    # CHAR_PIN (incident class): the learner's meta question contains no
    # repair-target concept — NO image is served (an absent image beats a
    # wrong one); the decision is visible, not silent.
    assert turn.parts["mode_decision"]["image_concept"] is None
    assert not turn.parts.get("teach_images")
    assert not any(n.startswith("teach_image:") for n in turn.notes)

    # CHAR_PIN: await/TTL hold armed for exactly ONE following learner turn.
    assert s.pedagogy_memory.await_comprehension is True
    assert s.pedagogy_memory.await_comprehension_ttl == 1

    obs1 = _observe(
        ctx, turn, save_slice=slice(n_open, None),
        sheet_keys=(("lexicon", "contento"),),
    )
    obs1["learner"] = "What does contento mean?"
    obs1["await"] = {
        "await_comprehension": s.pedagogy_memory.await_comprehension,
        "ttl": s.pedagogy_memory.await_comprehension_ttl,
    }
    n_t1 = len(ctx.save_calls)

    turn2 = s.user_turn("Estoy contento.")
    assert turn2.error is None

    # CHAR_PIN: their own Spanish clears the hold eagerly (no sticky repair)
    # and the phase clock resumes consuming.
    assert s.pedagogy_memory.await_comprehension is False
    assert s.pedagogy_memory.await_comprehension_ttl == 0
    assert turn2.parts["mode"] == "conversation"
    # CHAR_PIN — re-routed by PHASE HOST rule 6 (Proposal A micro-batch,
    # 2026-07-29; golden regenerated with justification): this turn rides
    # the NEW_INPUT activity, where the topic scene pick is now SUPPRESSED
    # (introduce owns new_input per PEDAGOGY §6.4) — «Estoy contento» used
    # to topic-match scene_goal:boat_meet_captain; it now falls through to
    # default_conversation and the INTRODUCE block fires (lawfulness check:
    # the batch-4 unlawful class was introduce STARVATION on new_input —
    # this is its exact inverse; budget still consumable).
    assert "mode_reason=default_conversation" in turn2.notes
    assert "introduce_planned:me llamo:R-D" in turn2.notes
    assert "phase_consumed=True" in turn2.notes
    assert s.phase_state.turns_in_phase == 2
    assert s.phase_state.frozen_turns == 1

    # CHAR_PIN CHAR-BUG-006 RESOLVED (known_bugs.json): the dual miss-note
    # pin (mode attach «bote» + fallback «hola» from the scene's SUGGESTED
    # lines) was HOSTED by the old scene_goal routing of this turn; the
    # Proposal A rule-6 re-route displaced it from this trajectory, and
    # the Proposal B pin-first batch (2026-07-29) then RESOLVED the bug
    # itself — stage_fallback_image no longer reads scene scripts at all.
    # The direct pins live in test_characterization_ai_path.py
    # (test_char_bug_006_resolved_*); these asserts stay as the
    # trajectory-level guard.
    assert "image_gen_disabled:bote" not in turn2.notes
    assert "image_gen_disabled:hola" not in turn2.notes
    assert "hola" not in turn2.reply.lower()

    # CHAR_PIN CHAR-BUG-007 RESOLVED (Phase 5 batch 2, known_bugs.json;
    # golden regenerated with justification): the topic palette is now
    # table-derived through session_memory.topic_palette, which excludes
    # STRUCTURAL themes/keys — the PRONOUN «tú» no longer binds as the
    # topic concept of "¿Dónde estás tú?"; the registry records the bare
    # location frame and semantically identical asks dedupe onto one key.
    assert "asked_topic:location" in turn2.notes
    assert "asked_topic:location:tu" not in turn2.notes
    assert s.pedagogy_memory.asked_topics == {"location"}

    obs2 = _observe(
        ctx, turn2, save_slice=slice(n_t1, None), sheet_keys=(),
    )
    obs2["learner"] = "Estoy contento."
    obs2["await"] = {
        "await_comprehension": s.pedagogy_memory.await_comprehension,
        "ttl": s.pedagogy_memory.await_comprehension_ttl,
    }
    check_golden(
        "golden_comprehension_repair",
        {"repair_turn": obs1, "clear_turn": obs2},
    )


# ---------------------------------------------------------------------------
# Golden (vi): budget arcs — introduce 2→1→0 + R-G refusal; §2.1a uptake
# fires / blocked / recovers
# ---------------------------------------------------------------------------


def _arc_view(ctx, s, result, req_index) -> dict:
    """Compact per-turn view for the multi-turn budget-arc golden."""
    payload = ctx.fake.task_payload(req_index)
    return {
        "mode": (result.parts or {}).get("mode"),
        "notes": note_families(result.notes),
        "intro_budget_remaining":
            s.pedagogy_memory.intro_budget_remaining(),
        "introduced_this_session": list(
            s.pedagogy_memory.introduced_this_session
        ),
        "uptake_last_turn": s.mode_state.content_uptake_last_turn,
        "learner_turn_index": s.mode_state.learner_turn_index,
        "phase": {
            "index": s.phase_state.index,
            "turns_in_phase": s.phase_state.turns_in_phase,
            "frozen_turns": s.phase_state.frozen_turns,
        },
        # §1.1 rewrite (2026-08-03): router scripts no longer ship — the
        # pin is their ABSENCE from the payload (shadow notes carry them).
        "instructions": {
            "scripts_shipped": "mode" in payload,
        },
        "requests_so_far": len(ctx.fake.requests),
    }


def test_golden_budget_arc(tutor_session_factory):
    ctx = tutor_session_factory(
        seed_sheet=_known_seed(),
        replies=[
            OPEN_KNOWN_REPLY,      # open: plan «me llamo» emitted, not realized
            TURN_INTRO_REPLY,      # t1: «me llamo» + R-D gloss → introduced
            ARC_INTRO2_REPLY,      # t2: «soy» + R-D gloss → introduced
            ARC_PLAIN_REPLY_3,     # t3: nothing new (R-G refused the plan)
            ARC_PLAIN_REPLY_4,     # t4: task-phase turn, uptake recovered
        ],
    )
    s = ctx.session
    views: list[dict] = []

    open_res = s.open_session()
    assert open_res.error is None
    assert "introduce_planned:me llamo:R-D" in open_res.notes
    assert s.pedagogy_memory.intro_budget_remaining() == 2
    views.append(_arc_view(ctx, s, open_res, 0))

    # t1 — uptake FIRES (first §2.1a self-flag, budget fresh) and the
    # realized plan consumes introduce budget 2→1.
    t1 = s.user_turn("Muy bien, gracias. El pan (bread?) es muy rico.")
    assert t1.error is None
    assert "uptake_flagged:pan" in t1.notes
    assert "introduced:me llamo" in t1.notes
    assert s.pedagogy_memory.intro_budget_remaining() == 1
    assert s.mode_state.content_uptake_last_turn == 2
    views.append(_arc_view(ctx, s, t1, 1))

    # t2 — consecutive self-flag BLOCKED (≥3-turn gap not met: 3-2=1); the
    # second introduce plan lands and consumes the last slot 1→0.
    t2 = s.user_turn("La leche (milk?) es buena.")
    assert t2.error is None
    assert not any(n.startswith("uptake_flagged:") for n in t2.notes)
    assert s.mode_state.content_uptake_last_turn == 2  # unchanged
    assert "introduce_planned:soy:R-D" in t2.notes
    assert "introduced:soy" in t2.notes
    assert s.pedagogy_memory.intro_budget_remaining() == 0
    views.append(_arc_view(ctx, s, t2, 2))

    # t3 — R-G: budget exhausted → the router refuses to plan (no
    # introduce_planned note) and the phase prefix says EXHAUSTED.
    t3 = s.user_turn("Sí, hablo con mi familia cada día.")
    assert t3.error is None
    assert not any(n.startswith("introduce_planned:") for n in t3.notes)
    assert not any(n.startswith("introduced:") for n in t3.notes)
    # §1.1 rewrite: the budget refusal is shadow telemetry (notes above);
    # no script ships either way.
    assert "mode" not in ctx.fake.task_payload(3)
    views.append(_arc_view(ctx, s, t3, 3))

    # t4 — new_input exhausted → task phase binds the first task-capable
    # scene; the ≥3-turn uptake window has passed (5-2=3) → uptake fires
    # again on the fresh self-flag.
    t4 = s.user_turn("Quiero leche (milk?) en el desayuno.")
    assert t4.error is None
    assert "uptake_flagged:leche" in t4.notes
    assert s.mode_state.content_uptake_last_turn == 5
    assert "task_goal_offered:boat_likes" in t4.notes
    assert s.task_state is not None
    assert s.task_state.scene_id == "boat_likes"
    assert s.task_state.status == "open"
    assert s.task_state.slots_filled == {}
    views.append(_arc_view(ctx, s, t4, 4))

    # CHAR_PIN: both introductions honesty-lawful (schedule fields only).
    assert s.pedagogy_memory.introduced_this_session == [
        "me llamo", "soy",
    ]
    for key in ("me llamo", "soy"):
        entry = s.sheet["lexicon"][key]
        assert entry["status"] == "unknown"
        assert float(entry["confidence"] or 0.0) == 0.0
        assert entry["introduced_at"]

    check_golden("golden_budget_arc", {
        "turns": views,
        "learners": [
            "(session open)",
            "Muy bien, gracias. El pan (bread?) es muy rico.",
            "La leche (milk?) es buena.",
            "Sí, hablo con mi familia cada día.",
            "Quiero leche (milk?) en el desayuno.",
        ],
    })


# ---------------------------------------------------------------------------
# Golden (vii): close phase — summary sources + prefix
# ---------------------------------------------------------------------------


def test_golden_close_phase(tutor_session_factory):
    ctx = tutor_session_factory(
        seed_sheet=_known_seed(),
        replies=[OPEN_KNOWN_REPLY, CLOSE_REPLY],
    )
    s = ctx.session
    assert s.open_session().error is None
    n_open = len(ctx.save_calls)

    # Seed the session state the close summary is built FROM (code-owned
    # sources: introduce ledger, resolved forms; task_state stays unbound) —
    # then tick the phase state to the close phase per the batch-2 runbook.
    assert s.pedagogy_memory.note_introduced("hola")
    s.mode_state.note_resolved(["weather_hace"])
    while s.phase_state.current_activity() != "close":
        assert s.phase_state.force_advance()

    turn = s.user_turn("Muy bien, gracias.")
    assert turn.error is None

    # CHAR_PIN: flavorable close turn carries the CLOSE prefix + the compact
    # summary data block, built ONLY from tracked session state (§3 honesty:
    # introduced keys, resolved error patterns, skills shown — invents
    # nothing; no task line when no task was bound).
    assert "close_phase_offered" in turn.notes
    # §1.1 rewrite: the close offer is shadow telemetry (note above); the
    # model decides how to close from session_facts. No script, no
    # code-authored SESSION SUMMARY line, ships.
    assert "mode" not in ctx.fake.task_payload(-1)

    # CHAR_PIN: the close turn consumes the 1-turn close budget; the clock
    # walks off the plan end and the session continues in "free".
    assert s.phase_state.index == len(s.phase_state.plan.phases)
    assert s.phase_state.current_activity() == "free"

    # CHAR_PIN: the glossed farewell in the reply is a scaffolded first
    # exposure (first_seen bit), NOT an introduction — ledger untouched.
    assert "first_seen:adiós" in turn.notes
    assert not any(n == "introduced:adiós" for n in turn.notes)
    adios = s.sheet["lexicon"]["adiós"]
    assert adios.get("first_seen") and not adios.get("introduced_at")

    obs = _observe(
        ctx, turn, save_slice=slice(n_open, None),
        sheet_keys=(("lexicon", "adiós"),),
    )
    obs["learner"] = "Muy bien, gracias."
    check_golden("golden_close_phase", obs)


# ---------------------------------------------------------------------------
# CHAR-BUG-005 RESOLVED-BY-DELETION: the scene_modeled machine is GONE
# ---------------------------------------------------------------------------


def test_char_bug_open_marks_all_scenes_modeled(tutor_session_factory):
    # CHAR_PIN — CHAR-BUG-005 RESOLVED-BY-DELETION (Proposal A micro-batch,
    # 2026-07-29, known_bugs.json + docs/reviews-architecture-refactor.md
    # policy round): the prefer-unmodeled machine was deleted, not revived —
    # ModeSessionState.scene_modeled (field + snapshot keys), the
    # prefer-unmodeled +1 inside _scene_for_topic, _scene_needs_model and
    # its guard-7 fallback call, and the stage_mode_record mark loop are
    # all GONE.  Scene realization belongs to the task phase; topic-matched
    # scene_goal pursuit (KEEP-5) survives under the phase host rules.
    # This pin flipped WITH the deletion per the Phase 0 law.
    import inspect

    ctx = tutor_session_factory(
        seed_sheet=_known_seed(), replies=[OPEN_KNOWN_REPLY],
    )
    s = ctx.session
    assert s.open_session().error is None

    all_scenes = {"boat_likes", "boat_meet_captain", "boat_where_boat"}
    assert set(s.mode_state.open_scene_ids) == all_scenes

    import tutor.modes as modes_mod
    import tutor.turn_pipeline as tp_mod

    # The field is gone from the dataclass and from the snapshot surfaces.
    assert not hasattr(s.mode_state, "scene_modeled")
    assert "scene_modeled" not in s.mode_state.snapshot()
    assert "scene_modeled" not in (s.state.snapshot().get("mode_state") or {})
    # The needs-model fallback is gone entirely.
    assert not hasattr(modes_mod, "_scene_needs_model")
    # Deletion lint: no CODE reference to the deleted names remains in the
    # owning modules (comments/docstrings recording the deletion are fine).
    import ast

    dead = {"scene_modeled", "_scene_needs_model"}
    for mod in (modes_mod, tp_mod):
        tree = ast.parse(inspect.getsource(mod))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in dead, (mod.__name__, node.attr)
            elif isinstance(node, ast.Name):
                assert node.id not in dead, (mod.__name__, node.id)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.name not in dead, (mod.__name__, node.name)
            elif isinstance(node, ast.Constant):
                # exact-string uses (dict keys) only — prose may mention them
                assert node.value not in dead, (mod.__name__, node.value)
