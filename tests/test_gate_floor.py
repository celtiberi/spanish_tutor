"""still_fail floor (system review 2026-07-30, PEDAGOGY §6 amendment).

The 20260729-210545 incident: probe_loop fired, repair failed, the
repeated A/B check shipped anyway — "fail open" was policy. These pins
make the repeal permanent: ship-ban residuals get part surgery or a hold,
never the learner.
"""

import pytest

from tutor.session_memory import compose_topic_key
from tutor.tutor_response import compose_raw, process_tutor_raw

pytestmark = []


class TestComposeRaw:
    def test_round_trip_parts(self):
        parts = {
            "acknowledge": "¡Muy bien!",
            "model": "**Estoy bien.**",
            "try": "¿Y tú?",
        }
        vis, reparsed = process_tutor_raw(compose_raw(parts))
        d = reparsed.as_dict()
        self.check = d
        assert d["acknowledge"] == "¡Muy bien!"
        assert d["model"] == "**Estoy bien.**"
        assert d["try"] == "¿Y tú?"
        assert "Estoy bien" in vis

    def test_empty_parts_compose_empty_tutor(self):
        vis, reparsed = process_tutor_raw(compose_raw({}))
        assert vis == ""


class TestConceptClassFold:
    def test_person_variants_fold_to_one_class(self):
        # R3: «cómo estás» / «cómo está» are ONE meaning check for
        # anti-loop keys (the incident's second ask must not read novel).
        k1 = compose_topic_key("wellbeing", "cómo estás")
        k2 = compose_topic_key("wellbeing", "como esta")
        assert k1 == k2 == "wellbeing:como-estar"
        k3 = compose_topic_key("name", "cómo te llamas")
        k4 = compose_topic_key("name", "como se llama")
        assert k3 == k4 == "name:como-llamar"

    def test_ordinary_concepts_unfolded(self):
        assert compose_topic_key("size", "ciudad") == "size:ciudad"


# Reply fixtures: a probing A/B try on known wellbeing material — the
# incident's shape. The seed sheet below marks IP-04 known so
# seed_from_sheet registers ask_how as already-asked at open.
OPEN_OK_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Empezamos!</acknowledge>\n"
    "  <model>**Yo estoy muy contento hoy.**</model>\n"
    "  <try>¿Estás contento hoy también?</try>\n"
    "</tutor>"
)
# Model line stays on sheet-known material so the ONLY residual fault is
# the probe itself (surgery requires a pure probe_loop residual; anything
# else is rung b′ by design).
PROBE_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Muy bien!</acknowledge>\n"
    "  <model>**Estoy bien**, gracias.</model>\n"
    "  <try>¿«Cómo estás» es «How are you?»? ¿Sí o no?</try>\n"
    "</tutor>"
)
# Probe-only reply: stripping try leaves nothing to teach → remainder
# faults no_teach_move (ship-ban) → hold.
PROBE_ONLY_REPLY = (
    "<tutor>\n"
    "  <try>¿«¿Cómo estás?» significa «How are you?»? ¿Sí o no?</try>\n"
    "</tutor>"
)
# What a compliant rung-(b) recovery looks like: known material only, no
# quiz chrome, a real teach move.
RECOVERY_OK_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Muy bien!</acknowledge>\n"
    "  <model>**Estoy bien.**</model>\n"
    "  <try>¿Y tú? **Estoy bien.**</try>\n"
    "</tutor>"
)


def _known_wellbeing_seed():
    from tutor.character_sheet import default_sheet

    s = default_sheet()
    s["skills"]["IP-04"].update(
        {"confidence": 0.85, "status": "known", "solid_uses": 2,
         "evidence": ["said estoy bien repeatedly"]}
    )
    s["skills"]["IP-01"].update(
        {"confidence": 0.85, "status": "known", "solid_uses": 2,
         "evidence": ["greets naturally"]}
    )
    # Reply-surface keys are sheet-known so the unscaffolded scan stays
    # quiet — the strip test needs probe_loop as the SOLE residual.
    for key in ("estoy bien", "bien", "muy bien", "gracias", "cómo estás",
                "cómo está", "contento", "y tú"):
        s["lexicon"][key] = {
            "status": "known", "confidence": 0.8, "solid_uses": 2,
            "introduced_at": "2026-07-20",
        }
    return s


class TestStillFailFloor:
    def test_probe_repair_probe_gets_stripped_not_shipped(
        self, tutor_session_factory
    ):
        # open ok; turn 1 probes known wellbeing → probe_loop (critical
        # since 2026-07-30) → repair ALSO probes → still_fail → floor
        # rung (a): try/continue dropped, remainder re-gated and shipped.
        ctx = tutor_session_factory(
            seed_sheet=_known_wellbeing_seed(),
            replies=[OPEN_OK_REPLY, PROBE_REPLY, PROBE_REPLY],
        )
        s = ctx.session
        assert s.open_session().error is None
        turn = s.user_turn("Estoy muy bien, gracias.")
        assert turn.error is None
        assert any(
            n.startswith("output_gate_fail:") and "probe_loop" in n
            for n in turn.notes
        )
        assert "output_gate_stripped" in turn.notes
        # The probing question is GONE from the shipped reply.
        assert "Sí o no" not in turn.reply
        assert "How are you" not in turn.reply
        # The compliant remainder survived.
        assert "Estoy bien" in turn.reply
        assert not turn.parts.get("gate_hold")

    def test_recovery_rung_ships_a_real_turn_instead_of_silence(
        self, tutor_session_factory
    ):
        # Incident 2026-07-30 (session 133545): a learner wrote "I do not
        # understand what you are asking. Too advanced for me" and got
        # SILENCE — strip could not fix a mixed residual and the floor
        # fell straight to hold. Rung (b) is the fix: ONE constrained
        # regeneration (bans only, model still performs Spanish) before
        # any hold. A compliant recovery must SHIP.
        ctx = tutor_session_factory(
            seed_sheet=_known_wellbeing_seed(),
            replies=[OPEN_OK_REPLY, PROBE_ONLY_REPLY, PROBE_ONLY_REPLY,
                     RECOVERY_OK_REPLY],
        )
        s = ctx.session
        assert s.open_session().error is None
        turn = s.user_turn("I do not understand what you are asking.")
        assert turn.error is None
        assert "output_gate_recovered" in turn.notes
        assert not turn.parts.get("gate_hold")
        assert "Estoy bien" in turn.reply
        assert "Sí o no" not in turn.reply
        # The recovery prompt states the bans and never dictates Spanish.
        recovery_msg = ctx.fake.request(3)["messages"][-1]["content"]
        assert "RECOVERY" in recovery_msg
        assert "Do NOT introduce ANY new Spanish" in recovery_msg
        assert "Estoy bien" not in recovery_msg  # no code-authored Spanish

    def test_every_rung_failing_still_ships_something(
        self, tutor_session_factory
    ):
        # THE ANTI-SILENCE LAW (junk audit 2026-07-30, priority #1: "a
        # silent tutor is not a tutor"). Probe-only replies defeat repair,
        # strip, AND constrained recovery — the learner STILL gets a turn.
        # A repeated question is a bad turn; silence ends the exchange.
        ctx = tutor_session_factory(
            seed_sheet=_known_wellbeing_seed(),
            replies=[OPEN_OK_REPLY, PROBE_ONLY_REPLY, PROBE_ONLY_REPLY,
                     PROBE_ONLY_REPLY],
        )
        s = ctx.session
        assert s.open_session().error is None
        turn = s.user_turn("Estoy muy bien, gracias.")
        assert turn.error is None
        assert any(n.startswith("output_gate_degraded:") for n in turn.notes)
        assert turn.reply.strip(), "learner must never get silence"
        assert not turn.parts.get("gate_hold")
        # Operator surface: the session still counts its still-fails.
        assert getattr(s, "gate_still_fail_count", 0) >= 1

    def test_harmful_content_is_scrubbed_before_degraded_ship(self):
        # Degraded ≠ shipping garbage: tool/sheet JSON and mid-sentence
        # truncation are removed first (the two HARMFUL_TO_SHOW classes).
        from tutor.turn_pipeline import _scrub_harmful

        leak = 'Muy bien. {"lexicon": {"hola": 0.8}, "status": "known"}'
        assert "lexicon" not in _scrub_harmful(leak)
        assert "Muy bien" in _scrub_harmful(leak)
        assert _scrub_harmful("Estoy bien. Y tú puedes decir") == "Estoy bien."
        assert _scrub_harmful("Hola. ¿Cómo estás?") == "Hola. ¿Cómo estás?"
