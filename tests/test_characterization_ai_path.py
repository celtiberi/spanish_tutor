"""Phase 0 batch 1 — golden-turn characterization of the AI tutor path.

Runs the PUBLIC API (open_session + user_turn → _execute_ai_tutor) on a REAL
ConversationalSession against the FakeModelClient (tests/conftest.py), with
fully isolated state, and pins today's behavior as goldens under
tests/characterizations/.

Taxonomy (docs/reviews-architecture-refactor.md — Grok round-1 (c)
replacement text, BINDING per the closing adjudication):

  CHAR_PIN     — desired behavior; drift must fail CI and be deliberate.
  CHAR_BUG     — documented accidental behavior; the test PASSES today and
                 must not silently flip without a bugfix PR that updates the
                 pin.  Registry: tests/characterizations/known_bugs.json.
  CHAR_DIVERGE — AI-vs-rules differences.  RESOLVED BY DELETION (E4,
                 2026-07-28): the rules path, its goldens and their pins
                 were deleted with the runtime; see known_bugs.json
                 "CHAR-DIVERGE-E4" and the review doc's E4 adjudication.

Assertion groups are labelled with their class in comments.  Golden files
regenerate ONLY via CHAR_GOLDEN_UPDATE=1 (never in CI) — see
conftest.check_golden.
"""

from __future__ import annotations

import datetime
import json

from conftest import check_golden, normalize_dates, note_families

from tutor.character_sheet import default_sheet

# ---------------------------------------------------------------------------
# Canned <tutor> replies — crafted to parse through tutor_response and pass
# the output gate deterministically (no repair round unless a test wants one).
# ---------------------------------------------------------------------------

OPEN_BLANK_REPLY = (
    "<tutor>\n"
    "  <model>**Hola** (hello). **Estoy bien** (I'm fine).</model>\n"
    "  <try>Say **Hola** (hello) to me!</try>\n"
    "</tutor>"
)

# Blank turn 1: no «hola» (the planned introduce lapses silently); «bien»
# carries an in-reply gloss → the gate's scaffold_saved → first_seen path.
TURN_BLANK_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Perfecto! Empezamos poco a poco.</acknowledge>\n"
    "  <model>**Estoy bien** (I'm fine).</model>\n"
    "  <try>Di: **Estoy bien** (I'm fine).</try>\n"
    "</tutor>"
)

OPEN_DUE_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Qué bueno verte otra vez!</acknowledge>\n"
    "  <model>**Me gusta el pan.** — I like bread.</model>\n"
    "  <try>¿Te gusta el pan?</try>\n"
    "</tutor>"
)

TURN_DUE_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Qué rico el pan!</acknowledge>\n"
    "  <model>**Yo bebo agua con el pan.**</model>\n"
    "  <try>¿Bebes mucha agua?</try>\n"
    "</tutor>"
)

OPEN_KNOWN_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Empezamos!</acknowledge>\n"
    "  <model>**Yo estoy muy contento hoy.**</model>\n"
    "  <try>¿Estás contento hoy también?</try>\n"
    "</tutor>"
)

# Introduce turn: presents the planned key WITH its scaffold → evidence →
# the introduce ledger write fires. Key changed hola→me llamo (R-D gloss)
# 2026-07-29: _known_seed is mid-stream (IP-01 known), so the
# encounter-variety round sorts openers last and the router plans
# «me llamo» (docs/design-encounter-variety.md).
TURN_INTRO_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Muy bien!</acknowledge>\n"
    "  <model>Para presentarte dices **me llamo** (my name is): "
    "Me llamo Marisol.</model>\n"
    "  <try>Di: **Me llamo** y tu nombre.</try>\n"
    "</tutor>"
)

TURN_ASSOC_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Ah, entiendo!</acknowledge>\n"
    "  <model>**Me gusta el café** (I like coffee).</model>\n"
    "  <try>¿Te gusta el café?</try>\n"
    "</tutor>"
)


# ---------------------------------------------------------------------------
# Seeds + observation helpers
# ---------------------------------------------------------------------------


def _known_seed() -> dict:
    """Non-blank learner: one can-do with real evidence, empty lexicon."""
    s = default_sheet()
    s["skills"]["IP-01"].update(
        {"confidence": 0.6, "status": "known", "evidence": ["said hola"]}
    )
    return s


_SEED_INTRO_DAY = (
    datetime.date.today() - datetime.timedelta(days=10)
).isoformat()


def _due_seed() -> dict:
    """Known learner with two lexicon items due YESTERDAY (pan, agua)."""
    s = _known_seed()
    yday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    for key in ("pan", "agua"):
        s["lexicon"][key] = {
            "status": "fragile",
            "confidence": 0.3,
            "introduced_at": _SEED_INTRO_DAY,
            "scaffold": "gloss",
            "next_due": yday,
            "interval_days": 1,
            "successive_successes": 0,
        }
    return s


_SCHEDULE_FIELDS = (
    "status", "confidence", "first_seen", "introduced_at", "scaffold",
    "next_due", "interval_days", "successive_successes",
)


def _entry_view(sheet: dict, section: str, key: str):
    entry = (sheet.get(section) or {}).get(key)
    if not isinstance(entry, dict):
        return None
    return {k: entry[k] for k in _SCHEDULE_FIELDS if k in entry}


def _progress_events(ctx) -> list[dict]:
    if not ctx.progress_path.exists():
        return []
    out = []
    for line in ctx.progress_path.read_text().splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        out.append({
            "kind": e.get("kind"),
            "key": e.get("key"),
            "polarity": e.get("polarity"),
        })
    return out


def _observe(ctx, result, *, save_slice, sheet_keys=()) -> dict:
    """One golden's observation of a single open/turn TurnResult."""
    s = ctx.session
    gate = (result.parts or {}).get("output_gate") or {}
    obs = {
        "reply": result.reply,
        "stop_reason": result.stop_reason,
        "error": result.error,
        "usage": dict(result.usage or {}),
        "notes": note_families(result.notes),
        "parts_keys": sorted((result.parts or {}).keys()),
        "gate": {
            "ok": gate.get("ok"),
            "faults": list(gate.get("faults") or []),
            "scaffold_saved": dict(gate.get("scaffold_saved") or {}),
        },
        # (phase observation DELETED 2026-08-03 — the session-phase clock
        # died with the S9 deletions; goldens regenerated.)
        "memory": {
            "turns": s.pedagogy_memory.turns,
            "shown": sorted(s.pedagogy_memory.shown),
            "asked": sorted(s.pedagogy_memory.asked),
            "asked_topics": sorted(s.pedagogy_memory.asked_topics),
            "images_shown": sorted(s.pedagogy_memory.images_shown),
            "introduced_this_session": list(
                s.pedagogy_memory.introduced_this_session
            ),
            "intro_budget_remaining":
                s.pedagogy_memory.intro_budget_remaining(),
        },
        "mode_state": {
            "hard_breaks_this_session":
                s.mode_state.hard_breaks_this_session,
            "turns_since_hard_break": s.mode_state.turns_since_hard_break,
            "last_mode": s.mode_state.last_mode,
            "english_only_streak": s.mode_state.english_only_streak,
            "learner_turn_index": s.mode_state.learner_turn_index,
            "form_focus_cooldown": dict(s.mode_state.form_focus_cooldown),
            "last_resolved_form": s.mode_state.last_resolved_form,
        },
        # CHAR_PIN — CHAR-BUG-001 RESOLVED (Phase 4 batch 4,
        # tests/characterizations/known_bugs.json): the call-site list pins
        # the ATOMIC turn — exactly one _commit_sheet per successful turn
        # (plus __init__ outside the turn on open observations).
        "save_sheet_calls": list(ctx.save_calls[save_slice]),
        "sheet": {
            f"{section}:{key}": _entry_view(s.sheet, section, key)
            for section, key in sheet_keys
        },
        "progress_events": _progress_events(ctx),
        "model_requests": len(ctx.fake.requests),
    }
    return normalize_dates(obs, extra={_SEED_INTRO_DAY: "<SEED_DAY>"})


# ---------------------------------------------------------------------------
# Harness smoke (E5 bar: the fixture itself must drive the real integrator)
# ---------------------------------------------------------------------------


def test_fake_client_default_reply_parses():
    # CHAR_PIN: the fake's default body survives the real parser with a
    # teach move (model + try) — the harness cannot silently feed the
    # session unteachable replies.
    from conftest import DEFAULT_TUTOR_BODY
    from tutor.tutor_response import process_tutor_raw

    visible, parts = process_tutor_raw(DEFAULT_TUTOR_BODY)
    assert parts.raw_had_structure
    assert parts.model and parts.try_
    assert "Estoy bien" in visible


def test_tutor_session_fixture_smoke(tutor_session):
    # CHAR_PIN: a real session runs open + one turn against the fake with
    # zero network and fully isolated files.
    s = tutor_session.session
    open_res = s.open_session()
    assert open_res.error is None
    turn = s.user_turn("Hola")
    assert turn.error is None
    assert len(tutor_session.fake.requests) == 2
    assert len(s.history) == 4  # open pair + turn pair, nothing dropped
    assert tutor_session.sheet_path.exists()
    # Cost events landed in the ISOLATED ledger, not logs/costs.jsonl.
    assert tutor_session.costs_path.exists()


# ---------------------------------------------------------------------------
# Golden (i): blank-sheet open (placement) + zero-register English turn
# ---------------------------------------------------------------------------


def test_golden_blank_open_and_zero_register_turn(tutor_session_factory):
    ctx = tutor_session_factory(
        seed_sheet=None,  # blank: sheet file absent → default_sheet
        replies=[OPEN_BLANK_REPLY, TURN_BLANK_REPLY],
    )
    s = ctx.session
    n_init = len(ctx.save_calls)

    open_res = s.open_session()
    assert open_res.error is None
    n_open = len(ctx.save_calls)

    # CHAR_PIN: blank open routes to placement (blank_open_placement).
    assert open_res.parts["mode"] == "placement"
    assert "mode_reason=blank_open_placement" in open_res.notes
    assert "pedagogy:diagnostic_open" in open_res.notes
    obs_open = _observe(
        ctx, open_res, save_slice=slice(0, n_open),
        sheet_keys=(("lexicon", "hola"), ("lexicon", "bien")),
    )
    obs_open["save_calls_init_plus_open"] = obs_open.pop("save_sheet_calls")
    check_golden("golden_blank_open", obs_open)

    turn = s.user_turn(
        "Thanks! I don't know any Spanish yet, where do we start?"
    )
    assert turn.error is None

    # CHAR_PIN: post-open English turn stays conversation (no hard break —
    # the open's placement break blocks another for 3 turns) and carries the
    # TRUE-ZERO register overlay + INTRODUCE plan (the session-phase layer
    # died 2026-08-03 — introduce rides flavorable turns directly).
    assert turn.parts["mode"] == "conversation"
    assert "mode_reason=default_conversation" in turn.notes
    # §1.1 rewrite (2026-08-03): the routers still COMPUTE (shadow notes
    # above prove it) but their scripts never reach the model.
    payload = ctx.fake.task_payload()
    assert "mode" not in payload
    assert "hard_observations" not in payload
    assert "teaching_data" in payload
    # CHAR_PIN: reply omitted the planned key → no introduce ledger write,
    # budget unconsumed (mere plan is not exposure).
    assert not any(n.startswith("introduced:") for n in turn.notes)
    assert s.pedagogy_memory.intro_budget_remaining() == 2
    # CHAR_PIN (Round-2 AMEND 1c + Phase 5 batch 2 declared delta): «estoy
    # bien» is a real in-pack table key since batch 2 (the batch-1 deferral
    # resolved), so the gate's longest-match overlap filter now keeps the
    # MWU span over bare «bien» — scaffold_saved {estoy bien: gloss} and the
    # durable first_seen bit land on «estoy bien», while «bien» stays
    # untouched (pinned below via sheet_keys).  Honesty laws unchanged: no
    # introduced_at, no retrieval enqueue, confidence untouched.
    assert "first_seen:estoy bien" in turn.notes
    assert "first_seen:bien" not in turn.notes
    # CHAR_PIN (2026-07-29 morph-card review; re-homed by the §1.1b
    # settlement round the same day): the tutor-side introduction engages
    # the Morphology card in the SAME turn — «estoy bien» → the estar
    # paradigm block, now settled into the frozen TurnRender (the
    # _turn_morph shared-dict stash is dead) which every sheet_public
    # repaint reads.
    assert "morph_card:estar" in turn.notes
    render = s.last_turn_render
    assert render is not None
    tm = render.card or {}
    assert tm.get("form_id") == "present_estar_person"
    assert tm.get("engaged_by") == "introduction"
    eb = s.sheet["lexicon"]["estoy bien"]
    assert eb.get("first_seen")
    assert not eb.get("introduced_at")
    assert not eb.get("next_due")
    assert float(eb.get("confidence") or 0.0) == 0.0
    assert "bien" not in s.sheet["lexicon"]

    obs_turn = _observe(
        ctx, turn, save_slice=slice(n_open, None),
        sheet_keys=(
            ("lexicon", "estoy bien"),
            ("lexicon", "bien"),
            ("lexicon", "hola"),
        ),
    )
    obs_turn["learner"] = "Thanks! I don't know any Spanish yet, where do we start?"
    check_golden("golden_blank_zero_register_turn", obs_turn)


# ---------------------------------------------------------------------------
# Golden (ii): known sheet, due items — due block + scheduler outcome
# ---------------------------------------------------------------------------


def test_golden_due_elicit_turn(tutor_session_factory):
    ctx = tutor_session_factory(
        seed_sheet=_due_seed(),
        replies=[OPEN_DUE_REPLY, TURN_DUE_REPLY],
    )
    s = ctx.session
    open_res = s.open_session()
    assert open_res.error is None
    n_open = len(ctx.save_calls)

    # CHAR_PIN: known open + due queue → the due-offer event fires from the
    # due-DATA path (stage_prompt_build) with both due items (oldest-due
    # order: agua, pan).
    assert "mode_reason=known_open_from_sheet" in open_res.notes
    assert "due_elicit_offered:agua,pan" in open_res.notes
    # §1.1 rewrite: due items ship as FACTS, not a scripted DUE block.
    open_payload = ctx.fake.task_payload(0)
    assert "mode" not in open_payload
    due_keys = {d["key"] for d in open_payload["teaching_data"]["due_for_review"]}
    assert {"agua", "pan"} <= due_keys
    obs_open = _observe(
        ctx, open_res, save_slice=slice(0, n_open),
        sheet_keys=(("lexicon", "pan"), ("lexicon", "agua")),
    )
    check_golden("golden_due_open", obs_open)

    turn = s.user_turn("Me gusta mucho el pan.")
    assert turn.error is None

    # CHAR_PIN: learner used the due key → retrieval outcome recorded
    # PRE-call; ladder advances (successes 0→1, interval 1d, due tomorrow).
    assert "due_outcome_success:pan" in turn.notes
    # CHAR_PIN (r8 production milestones, 2026-07-29): first due success =
    # "said it without help" (re-encounter unscaffolded by construction);
    # no new_context (pan has no multi-frame history). Golden regenerated
    # for this one added note + progress event (the only delta).
    assert "progress_milestone:first_solo:pan" in turn.notes
    assert not any("new_context" in n for n in turn.notes)
    pan = s.sheet["lexicon"]["pan"]
    tomorrow = (
        datetime.date.today() + datetime.timedelta(days=1)
    ).isoformat()
    assert pan["successive_successes"] == 1
    assert pan["interval_days"] == 1
    assert pan["next_due"] == tomorrow
    # CHAR_PIN (honesty law): the scheduler moved ONLY schedule fields —
    # status untouched by the outcome write (any confidence motion belongs
    # to process_turn's hard observer, pinned in the golden).
    assert pan["status"] == "fragile"
    # CHAR_PIN: the still-due item rides the new turn's due facts alone.
    assert "due_elicit_offered:agua" in turn.notes
    turn_payload = ctx.fake.task_payload()
    turn_due = {d["key"] for d in turn_payload["teaching_data"]["due_for_review"]}
    assert "agua" in turn_due and "pan" not in turn_due
    agua = s.sheet["lexicon"]["agua"]
    assert agua["successive_successes"] == 0  # silence records nothing

    obs_turn = _observe(
        ctx, turn, save_slice=slice(n_open, None),
        sheet_keys=(("lexicon", "pan"), ("lexicon", "agua")),
    )
    obs_turn["learner"] = "Me gusta mucho el pan."
    check_golden("golden_due_turn", obs_turn)


# ---------------------------------------------------------------------------
# Golden (iii): introduce-eligible new_input turn — plan + scaffold-evidence
# mark path
# ---------------------------------------------------------------------------


def test_golden_introduce_new_input_turn(tutor_session_factory):
    ctx = tutor_session_factory(
        seed_sheet=_known_seed(),
        replies=[OPEN_KNOWN_REPLY, TURN_INTRO_REPLY],
    )
    s = ctx.session
    open_res = s.open_session()
    assert open_res.error is None
    n_open = len(ctx.save_calls)

    # CHAR_PIN: the known open is introduce-flavorable, so a plan is
    # emitted on the OPEN too — but the canned open reply omits the key,
    # so nothing is marked. Key changed hola:R-E → me llamo:R-D 2026-07-29
    # (encounter-variety round: _known_seed is mid-stream — IP-01 known —
    # so openers sort last; docs/design-encounter-variety.md).
    assert "introduce_planned:me llamo:R-D" in open_res.notes
    assert not any(n.startswith("introduced:") for n in open_res.notes)
    obs_open = _observe(
        ctx, open_res, save_slice=slice(0, n_open),
        sheet_keys=(("lexicon", "me llamo"),),
    )
    check_golden("golden_introduce_open", obs_open)

    turn = s.user_turn("Muy bien, gracias.")
    assert turn.error is None

    # CHAR_PIN: plan re-emitted; reply presented «me llamo» WITH the R-D
    # gloss → introduce ledger write + session budget consumed + rail
    # milestone.
    assert "introduce_planned:me llamo:R-D" in turn.notes
    assert "introduced:me llamo" in turn.notes
    assert "progress_milestone:planted:me llamo" in turn.notes
    assert s.pedagogy_memory.introduced_this_session == ["me llamo"]
    assert s.pedagogy_memory.intro_budget_remaining() == 1
    # CHAR_PIN (honesty law): introduction NEVER grants ability — schedule
    # fields written, confidence/status untouched.
    me_llamo = s.sheet["lexicon"]["me llamo"]
    tomorrow = (
        datetime.date.today() + datetime.timedelta(days=1)
    ).isoformat()
    assert me_llamo["introduced_at"] == datetime.date.today().isoformat()
    assert me_llamo["scaffold"] == "gloss"
    assert me_llamo["next_due"] == tomorrow
    assert me_llamo["interval_days"] == 1
    assert me_llamo["successive_successes"] == 0
    assert float(me_llamo["confidence"] or 0.0) == 0.0
    assert me_llamo["status"] == "unknown"
    # CHAR_PIN — CHAR-BUG-001 RESOLVED (Phase 4 batch 4, known_bugs.json):
    # the atomic-turn save — ONE durable persist per successful turn at the
    # recorder commit point (_commit_sheet via stage_sheet_commit), AFTER
    # the introduce ledger wrote its fields.  The old two-site list
    # (_finish + _execute_ai_tutor mid-turn saves) flipped WITH the fix.
    assert ctx.save_calls[n_open:] == ["_commit_sheet"]

    obs_turn = _observe(
        ctx, turn, save_slice=slice(n_open, None),
        sheet_keys=(("lexicon", "me llamo"), ("lexicon", "muy bien")),
    )
    obs_turn["learner"] = "Muy bien, gracias."
    check_golden("golden_introduce_turn", obs_turn)


def test_notes_chronological_order(tutor_session_factory):
    # CHAR_PIN — CHAR-BUG-003 RESOLVED (Phase 3 batch 2, known_bugs.json):
    # result.notes is now the seq-ordered projection of the typed event log
    # ([render(e) for e in events]), so note order IS turn chronology:
    # select → instruct (plan) → gate verdict → sheet maintenance → record.
    # The old assembly (process_turn → gate_notes → sched_notes → tail) put
    # the gate verdict before the pre-call plan; that pin flipped WITH the
    # bugfix and the goldens were regenerated in the same change.
    ctx = tutor_session_factory(
        seed_sheet=_known_seed(),
        replies=[OPEN_KNOWN_REPLY, TURN_INTRO_REPLY],
    )
    s = ctx.session
    assert s.open_session().error is None
    turn = s.user_turn("Muy bien, gracias.")
    notes = list(turn.notes)
    mode_i = notes.index("mode=conversation")
    planned_i = notes.index("introduce_planned:me llamo:R-D")
    gate_i = notes.index("output_gate_ok")
    # Sheet maintenance note: tool-only ability (2026-07-31) emits
    # rules_backup when tools are off (test default) or tool_update when
    # the model grades. hard_observer is retired.
    if "tool_update" in notes:
        sheet_i = notes.index("tool_update")
    else:
        sheet_i = notes.index("rules_backup")
    marked_i = notes.index("introduced:me llamo")
    # True chronology: mode select → introduce plan (pre-call) → gate
    # (post-call) → sheet maintenance (_finish) → introduce mark (post-gate).
    assert mode_i < planned_i < gate_i < sheet_i < marked_i
    # And the notes list is exactly the rendered event log, in seq order.
    from tutor.turn_events import render

    assert notes == [render(e) for e in turn.events]


# ---------------------------------------------------------------------------
# CHAR-BUG-002 RESOLVED: english_only_streak single owner (Phase 4 batch 3)
# ---------------------------------------------------------------------------


def test_char_bug_002_resolved_single_streak_owner(tutor_session_factory):
    # CHAR_PIN — CHAR-BUG-002 RESOLVED (Phase 4 batch 3, known_bugs.json):
    # conv_session's stage_english_streak is the streak's single owner (it
    # counts the CURRENT turn before select_mode); modes guard 4 reads the
    # state only.  The old guard-4 `+ 1` double-counted the current turn,
    # so ONE English-only learner turn hard-broke into association; the
    # break now requires a GENUINE >=2 streak — the SECOND consecutive
    # English-only turn.  This pin flipped WITH the fix;
    # golden_english_streak regenerated in the same change (the pinned
    # association-break observation moved from turn 1 to turn 2).
    ctx = tutor_session_factory(
        seed_sheet=_known_seed(),
        replies=[OPEN_KNOWN_REPLY, TURN_BLANK_REPLY, TURN_ASSOC_REPLY],
    )
    s = ctx.session
    assert s.open_session().error is None

    # Turn 1 — FIRST English-only turn: streak is genuinely 1, NO break.
    t1 = s.user_turn(
        "That was a long day at the office and there is a lot to do."
    )
    assert t1.error is None
    assert t1.parts["mode"] != "association"
    assert "mode_reason=english_stuck_association" not in t1.notes
    assert "hard_break=False" in t1.notes
    assert s.mode_state.english_only_streak == 1
    assert s.mode_state.hard_breaks_this_session == 0
    n_t1 = len(ctx.save_calls)

    # Turn 2 — SECOND consecutive English-only turn: threshold met
    # honestly → association hard break.
    t2 = s.user_turn(
        "My day was long and there is so much work to finish tonight."
    )
    assert t2.error is None
    assert t2.parts["mode"] == "association"
    assert "mode_reason=english_stuck_association" in t2.notes
    assert "hard_break=True" in t2.notes
    assert s.mode_state.english_only_streak == 2
    assert s.mode_state.hard_breaks_this_session == 1

    obs_turn = _observe(
        ctx, t2, save_slice=slice(n_t1, None),
        sheet_keys=(("lexicon", "café"),),
    )
    obs_turn["learner"] = (
        "My day was long and there is so much work to finish tonight."
    )
    check_golden("golden_english_streak", obs_turn)


# ---------------------------------------------------------------------------
# CHAR-BUG-004 RESOLVED: image-miss note dedupe (Phase 4 batch 2)
# ---------------------------------------------------------------------------


def test_char_bug_004_resolved_image_miss_note_dedupes(
    tutor_session_factory,
):
    # CHAR_PIN — CHAR-BUG-004 RESOLVED (Phase 4 batch 2, known_bugs.json):
    # ONE miss note per concept per turn.  The mode-attach site and the
    # assets_for_ai_turn fallback could both decide the SAME concept and
    # double-note it; _note_image_miss now dedupes against the typed
    # IMAGE_GEN_* events already in the turn log.  Miss VISIBILITY is
    # unchanged (the first note still lands — audit (e) contract) and
    # different concepts still note separately (the dedupe never hid
    # CHAR-BUG-006's script-derived bote+hola pair — that class is gone
    # since the Proposal B image-path ban).  This pin flipped WITH the
    # 004 fix; golden_blank_open/golden_due_turn regenerated then.
    from tutor.turn_events import begin_turn_log, render

    s = tutor_session_factory().session

    ev = begin_turn_log(s)
    s._note_image_miss("hola", source="mode", decision_reason="warm:mode")
    s._note_image_miss("hola", source="mode", decision_reason="warm:x")
    s._note_image_miss("bote", source="mode", decision_reason="warm:mode")
    # Generation is disabled in the harness → the miss kind is
    # image_gen_disabled; the duplicate «hola» emit is dropped, the
    # distinct «bote» emit is kept.
    assert [render(e) for e in ev.events] == [
        "image_gen_disabled:hola",
        "image_gen_disabled:bote",
    ]

    # The dedupe is PER TURN: a fresh turn log may miss the concept again
    # (a later turn's miss stays visible).
    ev2 = begin_turn_log(s)
    s._note_image_miss("hola", source="mode", decision_reason="warm:mode")
    assert [render(e) for e in ev2.events] == ["image_gen_disabled:hola"]


def test_char_bug_004_end_to_end_single_miss_note(tutor_session_factory):
    # CHAR_PIN: the original double-note site end-to-end — blank open
    # (placement wants «hola»; mode attach misses, the fallback decides the
    # SAME concept) now carries the miss note exactly ONCE in result.notes.
    ctx = tutor_session_factory(
        seed_sheet=None, replies=[OPEN_BLANK_REPLY, TURN_BLANK_REPLY]
    )
    open_res = ctx.session.open_session()
    assert open_res.error is None
    assert open_res.notes.count("image_gen_disabled:hola") == 1


# ---------------------------------------------------------------------------
# CHAR-BUG-006 RESOLVED: scene scripts banned from the image path
# (Proposal B pin-first batch, 2026-07-29). Scenes themselves were then
# DELETED ENTIRELY (full-code-audit S9, 2026-08-03) — the incident class
# (authored scene lines reaching the image path) is structurally
# unreachable; the ban lint below keeps the image chain script-free.
# ---------------------------------------------------------------------------


def test_char_bug_006_ban_lint_image_chain_free_of_model_lines():
    # CHAR_PIN (ast-level ban lint, same idiom as the CHAR-BUG-005
    # deletion lint): no code reference to «model_lines» anywhere in
    # tutor.turn_pipeline — the image chain (stage_mode_image /
    # stage_fallback_image / stage_image_costs) lives there and scripts
    # must never re-enter it via a "harmless" re-thread.  Names, attribute
    # access, string keys and keyword arguments all count; comments are
    # not in the AST and stay allowed.
    import ast
    import inspect

    import tutor.turn_pipeline as tp

    tree = ast.parse(inspect.getsource(tp))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "model_lines":
            offenders.append(f"Name@{node.lineno}")
        elif isinstance(node, ast.Attribute) and node.attr == "model_lines":
            offenders.append(f"Attribute@{node.lineno}")
        elif (
            isinstance(node, ast.Constant)
            and node.value == "model_lines"
        ):
            offenders.append(f"Constant@{node.lineno}")
        elif isinstance(node, ast.keyword) and node.arg == "model_lines":
            offenders.append(f"keyword@{node.value.lineno}")
    assert not offenders, (
        "model_lines reference(s) in tutor.turn_pipeline — the Proposal B "
        f"image-path ban forbids them: {offenders}"
    )
