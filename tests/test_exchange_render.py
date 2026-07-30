"""§1.1b exchange settlement (docs/design-exchange-settlement.md).

Peripherals render projections of the REALIZED exchange, never the
agenda. Pins: projection purity (signature + closure lint + event
allowlist), pixel settlement (the café-class fixture — Grok-required),
repair re-settlement, confirmed-only bookkeeping, and the TurnRender
single-assignment/replace-whole contract.
"""

import inspect
import unittest
from pathlib import Path

from tutor.exchange_render import (
    PROJECTION_EVENT_ALLOWLIST,
    TurnRender,
    card_engagement,
    concept_present,
    exchange_surface,
    settle_images,
)


class TestProjectionPurity(unittest.TestCase):
    """The input law: projections admit no agenda inputs — enforced by
    signature pins AND a closure/source lint (signature tests alone are
    theater — Grok input-law AMEND)."""

    def test_signatures_admit_no_agenda_parameters(self):
        banned = {
            "session", "sheet", "next_best", "decision", "scene", "phase",
            "mode_decision", "targets",
        }
        for fn in (card_engagement, concept_present, settle_images,
                   exchange_surface):
            params = set(inspect.signature(fn).parameters)
            self.assertFalse(
                params & banned, f"{fn.__name__} takes agenda input"
            )

    def test_module_source_admits_no_agenda_reads(self):
        # AST lint (comments/docstrings may NAME the banned things — they
        # document the ban — so lint identifiers, not text): the projection
        # module must never reference live agenda state.
        # (teach_assets.concept_in_text is the one allowed import — a pure
        # matcher over pack data.)
        import ast

        import tutor.exchange_render as m

        tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
        banned = {
            "session", "sheet", "next_best", "scene", "phase_state",
            "mode_decision", "last_mode_decision", "decision",
        }
        idents: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                idents.add(node.id)
            elif isinstance(node, ast.Attribute):
                idents.add(node.attr)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    idents.add(alias.name.split(".")[0])
        self.assertFalse(
            idents & banned,
            f"agenda identifiers in projection module: {idents & banned}",
        )

    def test_event_allowlist_is_agenda_free(self):
        self.assertEqual(
            PROJECTION_EVENT_ALLOWLIST, {"introduced", "first_seen"}
        )


class TestPixelSettlement(unittest.TestCase):
    CAFE = {"concept": "cafe", "form": "el café", "url": "/x/cafe.png"}

    def test_cafe_class_fixture_drops(self):
        # THE incident (Grok-required integration fixture): scene agenda
        # attached café while the exchange was about the learner's house.
        surface = exchange_surface(
            "Mi mi casa es en ciudad antigua de Guatemala.",
            "¡Qué bonito! Para decir la ubicación usamos **estar**: "
            "*Mi casa **está** en Antigua Guatemala.* "
            "¿En qué ciudad estás tú?",
        )
        confirmed, drops = settle_images([self.CAFE], surface)
        self.assertEqual(confirmed, [])
        self.assertEqual(drops, [("cafe", "unconfirmed")])

    def test_exchange_that_touches_the_concept_confirms(self):
        surface = exchange_surface(
            "¿Qué bebes?", "Ahora bebo un café aquí en el bote."
        )
        confirmed, drops = settle_images([self.CAFE], surface)
        self.assertEqual(len(confirmed), 1)
        self.assertEqual(drops, [])

    def test_session_open_confirms_against_reply_alone(self):
        # OQ1: nothing leads pixels; the open has no learner text — the
        # reply alone decides.
        ok = exchange_surface("", "¡Hola! ¿Quieres un café?")
        confirmed, _ = settle_images([self.CAFE], ok)
        self.assertEqual(len(confirmed), 1)
        silent = exchange_surface("", "¡Hola! ¿Cómo estás?")
        confirmed2, drops2 = settle_images([self.CAFE], silent)
        self.assertEqual(confirmed2, [])
        self.assertEqual(drops2, [("cafe", "unconfirmed")])

    def test_conceptless_candidate_drops(self):
        surface = exchange_surface("hola", "hola")
        confirmed, drops = settle_images([{"url": "/x.png"}], surface)
        self.assertEqual(confirmed, [])
        self.assertEqual(drops, [("?", "unconfirmed")])


class TestTurnRenderContract(unittest.TestCase):
    def test_frozen_single_assignment(self):
        tr = TurnRender(images=({"concept": "cafe"},), card=None, drops=())
        with self.assertRaises(Exception):
            tr.images = ()

    def test_as_dict_round_trip_shape(self):
        tr = TurnRender(
            images=({"concept": "sol"},),
            card={"lemma": "estar", "paradigm": []},
            drops=(("image", "cafe", "unconfirmed"),),
        )
        d = tr.as_dict()
        self.assertEqual(d["images"][0]["concept"], "sol")
        self.assertEqual(d["card"]["lemma"], "estar")
        self.assertEqual(d["drops"], [["image", "cafe", "unconfirmed"]])


class TestPipelineSettlement(unittest.TestCase):
    """stage-level: settle_pixels shrinks ctx.teach_images pre-gate and
    emits render_dropped; settle_chrome freezes the TurnRender and does
    the confirmed-only bookkeeping."""

    def test_settle_pixels_shrinks_and_emits(self):
        from types import SimpleNamespace

        from tutor import turn_pipeline as tp
        from tutor.turn_events import TurnEventKind as EV, TurnEventLog

        ev = TurnEventLog()
        ctx = SimpleNamespace(
            teach_images=[
                {"concept": "cafe", "url": "/x.png"},
                {"concept": "sol", "url": "/y.png"},
            ],
            raw="<tutor><model>El sol es bonito.</model></tutor>",
            learner="me gusta",
            is_open=False,
            render_drops=[],
            ev=ev,
        )
        tp._settle_pixels(None, ctx)
        self.assertEqual(
            [i["concept"] for i in ctx.teach_images], ["sol"]
        )
        self.assertEqual(
            [(k, c, r) for k, c, r in ctx.render_drops],
            [("image", "cafe", "unconfirmed")],
        )
        dropped = ev.find(EV.RENDER_DROPPED)
        self.assertEqual([e.key for e in dropped], ["image:cafe"])


if __name__ == "__main__":
    unittest.main()
