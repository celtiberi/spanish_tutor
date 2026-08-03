"""Gate audit — no-hide policy (2026-08-01).

No repair rewrites, no probe stripping, no blank holds, no content scrub
that papers over model junk. Failures surface as gate_fail + raw reply.
"""

import pytest

from tutor.session_memory import compose_topic_key
from tutor.tutor_response import compose_raw, process_tutor_raw


class TestComposeRaw:
    def test_round_trip_parts(self):
        parts = {
            "acknowledge": "¡Muy bien!",
            "model": "**Estoy bien.**",
            "try": "¿Y tú?",
        }
        vis, reparsed = process_tutor_raw(compose_raw(parts))
        d = reparsed.as_dict()
        assert d["acknowledge"] == "¡Muy bien!"
        assert d["model"] == "**Estoy bien.**"
        assert d["try"] == "¿Y tú?"
        assert "Estoy bien" in vis

    def test_empty_parts_compose_empty_tutor(self):
        vis, reparsed = process_tutor_raw(compose_raw({}))
        assert vis == ""


class TestConceptClassFold:
    def test_person_variants_fold_to_one_class(self):
        k1 = compose_topic_key("wellbeing", "cómo estás")
        k2 = compose_topic_key("wellbeing", "como esta")
        assert k1 == k2 == "wellbeing:como-estar"
        k3 = compose_topic_key("name", "cómo te llamas")
        k4 = compose_topic_key("name", "como se llama")
        assert k3 == k4 == "name:como-llamar"

    def test_ordinary_concepts_unfolded(self):
        assert compose_topic_key("size", "ciudad") == "size:ciudad"


# The open turn ASKS ¿Cómo estás? (recorded via note_plan_try → asked);
# the second reply re-asks the SAME probe → gate:probe_loop (the surviving
# true-positive class after the 2026-08-03 retune: this session's own
# repeat, not the deleted shown-skill ban).
OPEN_OK_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Empezamos!</acknowledge>\n"
    "  <model>**Yo estoy muy contento hoy.**</model>\n"
    "  <try>¿Cómo estás hoy?</try>\n"
    "</tutor>"
)
PROBE_REPLY = (
    "<tutor>\n"
    "  <acknowledge>¡Muy bien!</acknowledge>\n"
    "  <model>**Estoy bien**, gracias.</model>\n"
    "  <try>¿Cómo estás hoy también?</try>\n"
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
    for key in ("estoy bien", "bien", "muy bien", "gracias", "cómo estás",
                "cómo está", "contento", "y tú"):
        s["lexicon"][key] = {
            "status": "known", "confidence": 0.8, "solid_uses": 2,
            "introduced_at": "2026-07-20",
        }
    return s


class TestGateNoHide:
    def test_probe_loop_surfaces_raw_with_gate_fail(
        self, tutor_session_factory
    ):
        # No strip, no repair: the probing try is still in the reply so
        # the failure is visible.
        ctx = tutor_session_factory(
            seed_sheet=_known_wellbeing_seed(),
            replies=[OPEN_OK_REPLY, PROBE_REPLY],
        )
        s = ctx.session
        assert s.open_session().error is None
        turn = s.user_turn("Estoy muy bien, gracias.")
        assert turn.error is None
        assert any(
            n.startswith("output_gate_fail:") and "probe_loop" in n
            for n in turn.notes
        )
        # The repair KIND no longer exists (full-code-audit S2 absence pin).
        from tutor.turn_events import TurnEventKind

        assert not hasattr(TurnEventKind, "OUTPUT_GATE_REPAIRED")
        assert "output_gate_recovered" not in turn.notes
        assert "output_gate_stripped" not in turn.notes
        assert turn.parts.get("gate_fail") is True
        assert turn.parts.get("gate_hold") is not True
        # Raw attempt still present (including the bad probe) — not hidden.
        assert "Cómo estás" in (turn.reply or "") or "Estoy bien" in (turn.reply or "")
        assert getattr(s, "gate_still_fail_count", 0) >= 1

    def test_no_second_model_call_on_gate_fail(
        self, tutor_session_factory
    ):
        ctx = tutor_session_factory(
            seed_sheet=_known_wellbeing_seed(),
            replies=[OPEN_OK_REPLY, PROBE_REPLY],
        )
        s = ctx.session
        assert s.open_session().error is None
        n_before = len(ctx.fake.requests) if hasattr(ctx.fake, "requests") else None
        turn = s.user_turn("Estoy muy bien, gracias.")
        assert turn.error is None
        # One tutor call for the user turn only (open already consumed reply 0).
        # FakeModelClient: count requests if available.
        if hasattr(ctx, "fake") and hasattr(ctx.fake, "request"):
            # open used index 0; user turn used index 1 only — no repair call.
            with pytest.raises(IndexError):
                ctx.fake.request(2)

    def test_critical_fault_set_matches_retune(self):
        # Gate retune 2026-08-03: mode-keyed contracts gone; bare
        # unscaffolded items SOFT; cluster veto is the surviving critical.
        from tutor.turn_pipeline import (
            GATE_CRITICAL_FAULTS,
            GATE_SHIP_BAN_FAULTS,
        )

        assert GATE_CRITICAL_FAULTS == frozenset({
            "pedagogy:no_teach_move",
            "pedagogy:open_needs_model_try",
            "gate:english_wall",
            "gate:sheet_leak",
            "gate:truncated",
            "gate:cluster_veto",
            "gate:probe_loop",
        })
        assert GATE_SHIP_BAN_FAULTS == GATE_CRITICAL_FAULTS
        # Retired machinery stays retired (absence pins).
        import tutor.turn_pipeline as tp

        for name in ("_INTEGRITY_HOLD", "_DEGRADE_OK"):
            assert not hasattr(tp, name)
        for gone in (
            "gate:missing_recast", "gate:form_focus_needs_model",
            "gate:comprehension_needs_check", "gate:unscaffolded_flood",
            "gate:unscaffolded_new_item",
        ):
            assert gone not in GATE_CRITICAL_FAULTS


class TestNoHideInternalErrors:
    def test_progress_path_exception_surfaces_in_notes(
        self, tutor_session_factory, monkeypatch
    ):
        # No-hide (USER 2026-08-03): a broken side-channel emits a visible
        # internal_error note — never a silent return [].
        import tutor.progress_ledger as pl

        def boom(*a, **k):
            raise RuntimeError("ledger exploded")

        # sheet_crossings runs on EVERY ai turn (conv_session._finish)
        monkeypatch.setattr(pl, "sheet_crossings", boom)
        ctx = tutor_session_factory(seed_sheet=_known_wellbeing_seed(),
                                    replies=[OPEN_OK_REPLY])
        s = ctx.session
        res = s.open_session()
        assert res.error is None
        joined = " ".join(res.notes)
        # the open plants nothing on this seed, so trigger via a turn if
        # the open emitted no progress call; either surface is acceptable
        if "internal_error:" not in joined:
            turn = s.user_turn("Estoy muy bien, gracias.")
            joined = " ".join(turn.notes)
        assert "internal_error:" in joined
        assert "RuntimeError" in joined

    def test_strict_errors_reraises(self, tutor_session_factory, monkeypatch):
        from tutor import config as cfg
        import tutor.progress_ledger as pl
        import pytest as _pytest

        ctx = tutor_session_factory(seed_sheet=_known_wellbeing_seed(),
                                    replies=[OPEN_OK_REPLY, OPEN_OK_REPLY])
        s = ctx.session
        s.open_session()
        # Arm strict + the bomb only after a clean open.
        monkeypatch.setattr(cfg, "STRICT_ERRORS", True)
        monkeypatch.setattr(pl, "sheet_crossings",
                            lambda *a, **k: (_ for _ in ()).throw(
                                RuntimeError("boom")))
        with _pytest.raises(RuntimeError):
            s.user_turn("Estoy muy bien, gracias.")
