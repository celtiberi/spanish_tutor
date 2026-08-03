"""Phase 0 batch 2 — AI-path arc goldens (gate fail surface / comprehension repair /
budget arcs / close phase) + CHAR-BUG-005.

Extends the batch-1 harness (tests/conftest.py + tests/
test_characterization_ai_path.py — fixtures and golden format REUSED, not
forked) per the adjudicated Phase 0 spec and the batch-2 runbook in
docs/reviews-architecture-refactor.md:

  - gate-fault → NO repair (2026-08-01): critical fault ships raw + gate_fail;
    second model call deleted (hiding path removed).
  - comprehension repair: meta "what does X mean" turn → repair-target
    image relevance (no irrelevant image — the incident class), await/TTL
    hold armed then cleared by the learner's own Spanish.
  - budget arcs (multi-turn): introduce budget 2→1→0 with the third plan
    refused (R-G) and the §2.1a self-flag uptake budget (fires once, the
    consecutive flag blocked, recovers after the ≥3-turn window).
  - scenes / phases / task runtime: DELETED 2026-08-03 (full-code-audit
    S9) — the close-phase golden died with the close phase; the
    CHAR-BUG-005 pin is now the wider scenes-stay-deleted lint.

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

    # CHAR_PIN (gate retune 2026-08-03): a bare unintroduced key is a
    # SOFT advisory now — logged + soft-fail event, never rewritten,
    # never a still_fail banner.
    assert "output_gate_fail:gate:unscaffolded_new_item" in turn.notes
    assert "output_gate_soft_fail:gate:unscaffolded_new_item" in turn.notes
    assert not any("output_gate_still_fail" in n for n in turn.notes)
    assert "output_gate_recovered" not in turn.notes
    assert "output_gate_ok" not in turn.notes
    assert len(ctx.fake.requests) == 2  # open + turn only (no repair call)

    # CHAR_PIN: single model call usage for the user turn (no second bill).
    assert turn.usage == {
        "input_tokens": 120, "output_tokens": 60,
        "thinking_tokens": 0, "cached_input_tokens": 0,
    }

    # CHAR_PIN: raw attempt ships with visible fault labels.
    assert "Mucho gusto" in turn.reply
    gate = turn.parts["output_gate"]
    assert gate["ok"] is False
    assert "gate:unscaffolded_new_item" in (gate.get("faults") or [])
    # AMEND 2a: the bare exposure is recorded — «mucho gusto» stops
    # re-faulting forever.
    assert gate.get("scaffold_saved", {}).get("mucho gusto") == "bare"
    assert "first_seen:mucho gusto" in turn.notes
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

    # CHAR_PIN: the mode router is dead — the meta turn ships as facts;
    # the memory hold still arms (comprehension repair is the MODEL's
    # judgment now).
    assert "mode" not in turn.parts
    assert "mode_decision" not in turn.parts

    # CHAR_PIN (incident class): no image machinery runs on a non-open
    # turn — an image arrives only via introduce R-B or the model's own
    # declaration; the meta turn serves none.
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
    # CHAR_PIN — the INTRODUCE plan keeps firing (shadow planner).
    assert "introduce_planned:me llamo:R-D" in turn2.notes

    # CHAR_PIN CHAR-BUG-006 RESOLVED, then scenes deleted entirely
    # (2026-08-03): no scene-script-derived image traffic can exist.
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
        "notes": note_families(result.notes),
        "intro_budget_remaining":
            s.pedagogy_memory.intro_budget_remaining(),
        "introduced_this_session": list(
            s.pedagogy_memory.introduced_this_session
        ),
        # §1.1 rewrite (2026-08-03): router scripts no longer ship — the
        # pin is their ABSENCE from the payload.
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

    # t1 — the §2.1a self-flag is a pure OBSERVATION now (router teardown
    # 2026-08-03: the instruction path + its ModeSessionState budget are
    # DELETED — every self-flag is a recorded fact); the realized plan
    # consumes introduce budget 2→1.
    t1 = s.user_turn("Muy bien, gracias. El pan (bread?) es muy rico.")
    assert t1.error is None
    assert "uptake_flagged:pan" in t1.notes
    assert "introduced:me llamo" in t1.notes
    assert s.pedagogy_memory.intro_budget_remaining() == 1
    views.append(_arc_view(ctx, s, t1, 1))

    # t2 — DECLARED DELTA (budget deleted): the consecutive self-flag is
    # observed too — it paced instruction injections, and there is no
    # instruction to pace.  The second introduce plan lands and consumes
    # the last slot 1→0.
    t2 = s.user_turn("La leche (milk?) es buena.")
    assert t2.error is None
    assert "uptake_flagged:leche" in t2.notes
    assert "introduce_planned:soy:R-D" in t2.notes
    assert "introduced:soy" in t2.notes
    assert s.pedagogy_memory.intro_budget_remaining() == 0
    views.append(_arc_view(ctx, s, t2, 2))

    # t3 — R-G: budget exhausted → the router refuses to plan (no
    # introduce_planned note).
    t3 = s.user_turn("Sí, hablo con mi familia cada día.")
    assert t3.error is None
    assert not any(n.startswith("introduce_planned:") for n in t3.notes)
    assert not any(n.startswith("introduced:") for n in t3.notes)
    # §1.1 rewrite: the budget refusal is shadow telemetry (notes above);
    # no script ships either way.
    assert "mode" not in ctx.fake.task_payload(3)
    views.append(_arc_view(ctx, s, t3, 3))

    # t4 — the fresh self-flag is observed as always. (The task phase +
    # scene bind died with the S9 deletions — no task notes exist.)
    t4 = s.user_turn("Quiero leche (milk?) en el desayuno.")
    assert t4.error is None
    assert "uptake_flagged:leche" in t4.notes
    assert not any("task" in str(n) for n in t4.notes)
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
# Golden (vii) DELETED 2026-08-03: the close phase died with the
# session-phase machinery (full-code-audit S9) — golden_close_phase.json
# removed; the first_seen/scaffold-exposure class it also pinned stays
# covered by golden_blank_zero_register_turn.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# CHAR-BUG-005 RESOLVED-BY-DELETION: the scene_modeled machine is GONE
# ---------------------------------------------------------------------------


def test_char_bug_005_and_scenes_stay_deleted(tutor_session_factory):
    # CHAR_PIN — CHAR-BUG-005 RESOLVED-BY-DELETION (Proposal A micro-batch,
    # 2026-07-29), then scenes DELETED ENTIRELY (full-code-audit S9,
    # 2026-08-03; USER: even goal/exit data is code-selected steering).
    # The pin now asserts the whole scene machine stays gone: no
    # tutor.scenes module, no scene fields on the mode store, and no CODE
    # reference to the deleted names in the owning modules (comments/
    # docstrings recording the deletion are fine).
    import ast
    import importlib.util
    import inspect

    ctx = tutor_session_factory(
        seed_sheet=_known_seed(), replies=[OPEN_KNOWN_REPLY],
    )
    s = ctx.session
    assert s.open_session().error is None

    assert importlib.util.find_spec("tutor.scenes") is None
    # The whole mode router died 2026-08-03 (full-code-audit S4) — the
    # module that owned the scene routing is itself gone.
    assert importlib.util.find_spec("tutor.modes") is None

    import tutor.turn_pipeline as tp_mod

    assert not hasattr(tp_mod, "stage_open_scenes")
    # Deletion lint: no CODE reference to the deleted names remains in the
    # owning module.
    dead = {"scene_modeled", "_scene_needs_model", "_scene_for_topic",
            "open_scene_ids", "open_scenes_for_sheet",
            "scene_hints_for_prompt"}
    tree = ast.parse(inspect.getsource(tp_mod))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in dead, node.attr
        elif isinstance(node, ast.Name):
            assert node.id not in dead, node.id
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.name not in dead, node.name
        elif isinstance(node, ast.Constant):
            # exact-string uses (dict keys) only — prose may mention them
            assert node.value not in dead, node.value
