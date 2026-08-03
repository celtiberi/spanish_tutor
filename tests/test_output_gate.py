"""Output gate + hard observer (no live API)."""

import re
import unittest

from tutor.character_sheet import default_sheet, process_turn
from tutor.output_gate import (
    MIN_ALPHA_TOKENS,
    MIN_SPANISH_RATIO,
    alphabetic_token_count,
    check_output_gate,
    detect_sheet_leak,
    detect_tutor_probe_keys,
    spanish_token_ratio,
    tutor_spanish_ratio,
)


class TestOutputGate(unittest.TestCase):
    def test_spanish_ratio_high(self):
        r = tutor_spanish_ratio("¡Hola! Estoy bien. ¿Cómo estás hoy?")
        self.assertIsNotNone(r)
        self.assertGreaterEqual(r, 0.5)

    def test_spanish_ratio_english_wall(self):
        r = tutor_spanish_ratio(
            "Good job! That means how are you. Please try to say the word hello."
        )
        self.assertIsNotNone(r)
        self.assertLess(r, 0.35)

    def test_spanish_token_ratio_always_float(self):
        self.assertIsInstance(spanish_token_ratio(""), float)
        self.assertEqual(spanish_token_ratio(""), 1.0)
        r = spanish_token_ratio(
            "Good job! That means how are you. Please try to say the word hello."
        )
        self.assertLess(r, 0.50)

    def test_probe_keys(self):
        k = detect_tutor_probe_keys("¿Cómo te llamas?")
        self.assertIn("ask_name", k)

    def test_gate_ok_spanish_teach(self):
        parts = {
            "acknowledge": "¡Qué bien!",
            "model": "Me llamo Sofía.",
            "try": "¿Y tú? ¿Cómo te llamas?",
            "structured": True,
        }
        g = check_output_gate(
            parts,
            "¡Qué bien! Me llamo Sofía. ¿Cómo te llamas?",
            is_open=False,
            already_asked=set(),
        )
        self.assertTrue(g.ok, g.faults)
        self.assertTrue(
            any(n.startswith("tl_ratio=") for n in g.notes),
            g.notes,
        )

    def test_gate_loop_reask_name(self):
        # This session's tutor already ASKED the name probe → re-ask faults.
        parts = {
            "acknowledge": "¡Hola!",
            "model": "Me llamo Sofía.",
            "try": "¿Cómo te llamas?",
            "structured": True,
        }
        g = check_output_gate(
            parts,
            "¿Cómo te llamas?",
            already_asked={"ask_name"},
        )
        self.assertFalse(g.ok)
        self.assertIn("gate:probe_loop", g.faults)

    def test_probe_scan_ignores_model_and_acknowledge(self):
        # Gate retune 2026-08-03: model/acknowledge text is roleplay
        # dialogue, not an ask (T2–T4 false positives in
        # evals/results/20260803-104618-student) — the scan reads the TRY
        # and CONTINUE parts only.
        parts = {
            "acknowledge": "¡Qué bien! ¿Cómo estás? es un saludo.",
            "model": "¡Hola! ¿Cómo estás hoy? — Estoy bien.",
            "try": "¿Dónde está el capitán?",
            "structured": True,
        }
        g = check_output_gate(
            parts,
            "¡Hola! ¿Cómo estás hoy? — Estoy bien. ¿Dónde está el capitán?",
            already_asked={"ask_how", "ask_name"},
        )
        self.assertNotIn("gate:probe_loop", g.faults)

    def test_no_shown_skill_permanent_ban(self):
        # The shown-skill ban is DELETED: a learner having demonstrated
        # «estoy» must not forbid ¿Cómo estás? forever — only a repeat of
        # THIS session's own ask (already_asked) faults.
        parts = {
            "acknowledge": "¡Hola!",
            "model": "Estoy bien.",
            "try": "¿Cómo estás hoy?",
            "structured": True,
        }
        g = check_output_gate(
            parts, "Estoy bien. ¿Cómo estás hoy?", already_asked=set(),
        )
        self.assertNotIn("gate:probe_loop", g.faults)

    def test_gate_english_wall(self):
        """Long mostly-English turn: ratio < 0.50 and alpha >= 12 → critical."""
        parts = {
            "acknowledge": "Good job you nailed it!",
            "model": "That means my name is.",
            "try": "Please say your name in Spanish now.",
            "structured": True,
        }
        blob = " ".join(
            str(parts.get(k) or "")
            for k in ("acknowledge", "recast", "explain", "model", "try", "continue")
        )
        # Arithmetic baked into the fixture: lexicon ratio 0.0; alpha >= 12.
        self.assertEqual(spanish_token_ratio(blob), 0.0)
        self.assertGreaterEqual(alphabetic_token_count(blob), MIN_ALPHA_TOKENS)
        g = check_output_gate(parts, "Good job...", is_open=False)
        self.assertFalse(g.ok)
        self.assertIn("gate:english_wall", g.faults)
        self.assertTrue(any(n.startswith("tl_ratio=") for n in g.notes), g.notes)
        self.assertIsNotNone(g.spanish_ratio)
        self.assertLess(g.spanish_ratio, MIN_SPANISH_RATIO)

    def test_gate_english_wall_short_mostly_english_no_trip(self):
        """Short mostly-English: ratio may be 0 but alpha < 12 → never wall."""
        parts = {
            "acknowledge": "Good job!",
            "model": "Try this.",
            "try": "Say it.",
            "structured": True,
        }
        blob = " ".join(
            str(parts.get(k) or "")
            for k in ("acknowledge", "recast", "explain", "model", "try", "continue")
        )
        # Good job Try this Say it → 6 alphabetic tokens; ratio 0.0 on lexicon hits.
        self.assertLess(alphabetic_token_count(blob), MIN_ALPHA_TOKENS)
        self.assertEqual(spanish_token_ratio(blob), 0.0)
        g = check_output_gate(parts, blob, is_open=False)
        self.assertNotIn("gate:english_wall", g.faults)
        self.assertTrue(any(n.startswith("tl_ratio=") for n in g.notes), g.notes)

    def test_gate_sandwich_gloss_exempt(self):
        """Short <explain> L1 gloss excluded from ratio → no english_wall.

        Body lexicon: es=8 (hola estoy bien gracias amigo / qué te gusta),
        en=5 (the and you are how) → r_body = 8/13 ≈ 0.615 (>= 0.50).
        Explain "means you the word phrase" = 5 non-ES words (≤ 6 → exempt):
        without exemption en=10 → r = 8/18 ≈ 0.444 (< 0.50, would trip);
        with exemption r = 8/13 → no trip. Full-blob alpha = 18 ≥ 12.
        """
        parts = {
            "acknowledge": "Hola estoy bien gracias amigo",
            "model": "The and you are how",
            "try": "Qué te gusta",
            "explain": "means you the word phrase",
            "structured": True,
        }
        full = " ".join(
            str(parts.get(k) or "")
            for k in ("acknowledge", "recast", "explain", "model", "try", "continue")
        )
        self.assertGreaterEqual(alphabetic_token_count(full), MIN_ALPHA_TOKENS)
        # Without exemption this fixture is under 0.50:
        self.assertLess(spanish_token_ratio(full), MIN_SPANISH_RATIO)

        g = check_output_gate(parts, full, is_open=False)
        self.assertNotIn("gate:english_wall", g.faults)
        self.assertIsNotNone(g.spanish_ratio)
        self.assertGreaterEqual(g.spanish_ratio, MIN_SPANISH_RATIO)
        ratio_notes = [n for n in g.notes if n.startswith("tl_ratio=")]
        self.assertEqual(len(ratio_notes), 1)
        self.assertRegex(ratio_notes[0], r"tl_ratio=0\.\d{2}")

    def test_gate_long_explain_not_exempt(self):
        """Explain with >6 non-ES words counts fully toward the wall."""
        parts = {
            "acknowledge": "Hola estoy bien gracias amigo",
            "model": "The and you are how",
            "try": "Qué te gusta",
            "explain": (
                "means you the word phrase please try say the sentence "
                "with your name right now"
            ),
            "structured": True,
        }
        g = check_output_gate(parts, "x", is_open=False)
        self.assertIn("gate:english_wall", g.faults)

    def test_tl_ratio_note_always_present(self):
        parts = {
            "acknowledge": "¡Qué bien!",
            "model": "Me llamo Sofía.",
            "try": "¿Cómo te llamas?",
            "structured": True,
        }
        g = check_output_gate(parts, "hola", is_open=False)
        self.assertTrue(
            any(re.match(r"tl_ratio=\d+\.\d{2}$", n) for n in g.notes), g.notes
        )
        # empty-ish visible fallback path
        g2 = check_output_gate({}, "", is_open=False)
        self.assertTrue(any(n.startswith("tl_ratio=") for n in g2.notes), g2.notes)

    def test_gate_no_teach_move(self):
        parts = {
            "acknowledge": "¡Hola amigo!",
            "continue": "¿Todo bien?",
            "structured": True,
        }
        g = check_output_gate(parts, "¡Hola!", is_open=False)
        self.assertFalse(g.ok)

    def test_gate_sheet_leak_is_hard_fault(self):
        raw = (
            '<tutor><model>Estoy bien.</model></tutor>\n'
            '```json {"active_error_focus":[{"id":"estar_yo_estoy_vs_esta"}],'
            '"grammar":{"present_estar_person":{"confidence":0.8,"solid_uses":2}}}\n```'
        )
        self.assertTrue(detect_sheet_leak(raw))
        parts = {"model": "Estoy bien.", "structured": True}
        g = check_output_gate(parts, "Estoy bien.", raw=raw)
        self.assertFalse(g.ok)
        self.assertIn("gate:sheet_leak", g.faults)
        self.assertIn("GATE FAIL", g.repair_instruction)
        self.assertFalse(g.ok)


class TestUnscaffoldedNewItemGate(unittest.TestCase):
    """Phase 4 (r7 S3), RETUNED 2026-08-03 (full-code-audit S4, Grok
    AMENDs): gate:unscaffolded_new_item is a SOFT advisory (bare first
    exposures); gate:cluster_veto is the surviving CRITICAL (same-theme
    extras); every visibly-used key lands in scaffold_saved (exposure
    ledger, incl. kind "bare").  Runs against the REAL pack association
    table — enforcement is tested on shipped data."""

    @classmethod
    def setUpClass(cls) -> None:
        from pathlib import Path

        from tutor.association_table import load_association_table

        root = Path(__file__).resolve().parents[1]
        cls.table = load_association_table(root / "domain" / "spanish_a1")

    def _gate(self, parts, visible, *, sheet=None, table="real", **kw):
        from tutor.character_sheet import default_sheet

        return check_output_gate(
            parts,
            visible,
            is_open=False,
            association_table=(self.table if table == "real" else table),
            sheet=sheet if sheet is not None else default_sheet(),
            **kw,
        )

    def _parts(self, model, try_="¿Puedes decirlo?"):
        return {"model": model, "try": try_, "structured": True}

    def test_bare_unintroduced_mwu_is_soft_advisory(self):
        g = self._gate(
            self._parts("Hasta luego."),
            "Hasta luego. ¿Puedes decirlo?",
        )
        self.assertIn("gate:unscaffolded_new_item", g.faults)
        self.assertFalse(g.ok)
        self.assertTrue(
            any("gate:unscaffolded_new_item" in n for n in g.notes), g.notes
        )
        # SOFT severity (retune): never in the pipeline's critical set.
        from tutor.turn_pipeline import GATE_CRITICAL_FAULTS

        self.assertNotIn("gate:unscaffolded_new_item", GATE_CRITICAL_FAULTS)
        # AMEND 2a: bare use is still exposure — first_seen evidence "bare".
        self.assertEqual(g.scaffold_saved.get("hasta luego"), "bare")

    def test_glossed_new_item_passes(self):
        g = self._gate(
            self._parts("**Hasta luego** (see you later)."),
            "**Hasta luego** (see you later). ¿Puedes decirlo?",
        )
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)

    def test_same_turn_image_counts_as_scaffold(self):
        # AMEND 2b: an attached teach image for the key IS its scaffold.
        g = self._gate(
            self._parts("Hasta luego."),
            "Hasta luego. ¿Puedes decirlo?",
            image_concepts={"hasta_luego"},
        )
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)
        self.assertEqual(g.scaffold_saved.get("hasta luego"), "image")

    def test_two_glossed_same_theme_farewells_fault_the_extra(self):
        # r7 R-F cluster ban as CODE: one new item per turn — the second
        # farewell faults CRITICALLY (gate:cluster_veto) even though both
        # carry glosses.
        parts = self._parts(
            "**Hasta luego** (see you later). **Adiós** (goodbye)."
        )
        g = self._gate(
            parts,
            "**Hasta luego** (see you later). **Adiós** (goodbye). "
            "¿Puedes decirlo?",
        )
        self.assertIn("gate:cluster_veto", g.faults)
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)
        self.assertIn("GATE FAIL", g.repair_instruction)
        self.assertFalse(g.ok)
        from tutor.turn_pipeline import GATE_CRITICAL_FAULTS

        self.assertIn("gate:cluster_veto", GATE_CRITICAL_FAULTS)

    def test_introduce_plan_key_is_exempt(self):
        g = self._gate(
            self._parts("Hasta luego."),
            "Hasta luego. ¿Puedes decirlo?",
            introduce_key="hasta luego",
        )
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)

    def test_plan_key_holds_cluster_slot_extra_still_faults(self):
        parts = self._parts(
            "**Hasta luego** (see you later). **Adiós** (goodbye)."
        )
        g = self._gate(
            parts,
            "**Hasta luego** (see you later). **Adiós** (goodbye).",
            introduce_key="hasta luego",
        )
        self.assertIn("gate:cluster_veto", g.faults)
        self.assertIn("GATE FAIL", g.repair_instruction)
        self.assertFalse(g.ok)

    def _introduced_sheet(self, *keys):
        from tutor.character_sheet import default_sheet
        from tutor.retrieval_scheduler import mark_introduced

        s = default_sheet()
        for k in keys:
            s = mark_introduced(s, k, "lexicon", "gloss")
        return s

    def test_regloss_of_introduced_key_is_soft_fault(self):
        g = self._gate(
            self._parts("**Hasta luego** (see you later)."),
            "**Hasta luego** (see you later).",
            sheet=self._introduced_sheet("hasta luego"),
        )
        self.assertIn("gate:regloss", g.faults)
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)
        self.assertFalse(g.ok)

    def test_regloss_allowed_after_retrieval_failure(self):
        g = self._gate(
            self._parts("**Hasta luego** (see you later)."),
            "**Hasta luego** (see you later).",
            sheet=self._introduced_sheet("hasta luego"),
            retrieval_failed_keys={"hasta luego"},
        )
        self.assertNotIn("gate:regloss", g.faults)

    def test_introduced_key_bare_is_clean(self):
        g = self._gate(
            self._parts("Hasta luego."),
            "Hasta luego.",
            sheet=self._introduced_sheet("hasta luego"),
        )
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)
        self.assertNotIn("gate:regloss", g.faults)

    def test_sheet_evidence_key_never_trips(self):
        # The learner has produced hola (lexicon confidence > 0): not a
        # first exposure, no scaffold demanded.
        from tutor.character_sheet import default_sheet

        s = default_sheet()
        s["lexicon"]["hola"] = {"status": "emerging", "confidence": 0.3}
        g = self._gate(self._parts("¡Hola!"), "¡Hola!", sheet=s)
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)

    def test_structural_theme_keys_never_trip(self):
        # Pronouns / question words are paradigm infrastructure, not lexical
        # introductions — the near-synonym cluster ban does not apply.
        g = self._gate(
            self._parts("Yo. Tú. Usted.", "¿Qué es esto?"),
            "Yo. Tú. Usted. ¿Qué es esto?",
        )
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)

    def test_overlapping_keys_count_once(self):
        # «muy bien» must not also count «bien» as a same-theme cluster.
        g = self._gate(
            self._parts("**Muy bien** (very good)."),
            "**Muy bien** (very good).",
        )
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)

    def test_disabled_without_table(self):
        g = self._gate(
            self._parts("Hasta luego."),
            "Hasta luego.",
            table=None,
        )
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)

    def test_english_wall_still_trips_alongside(self):
        # Regression guard: the retune must not blunt the wall. A long
        # English turn with a bare new item carries BOTH faults (the wall
        # critical, the bare item a soft advisory).
        parts = {
            "acknowledge": "Good job you nailed it, that was really great!",
            "model": "Hasta luego.",
            "try": "Please try to say the word again for me now.",
            "structured": True,
        }
        g = self._gate(parts, "Good job... Hasta luego.")
        self.assertIn("gate:english_wall", g.faults)
        self.assertIn("gate:unscaffolded_new_item", g.faults)
        self.assertIn("GATE FAIL", g.repair_instruction)
        self.assertFalse(g.ok)

    # --- Round-2 amendments (docs/reviews-pedagogy-engine-build.md,
    # Adjudication Round 2 2026-07-28) -----------------------------------

    def test_first_seen_stops_gloss_then_bare_thrash(self):
        # AMEND 1c — Grok's executed thrash proof as a passing test:
        # turn1 glossed «gracias» passes and reports the scaffold-saved key;
        # after the durable first_seen write, turn2 BARE «gracias» is clean
        # (previously it re-faulted CRITICALLY forever).
        from tutor.character_sheet import default_sheet
        from tutor.retrieval_scheduler import is_introduced, mark_first_seen

        s = default_sheet()
        g1 = self._gate(
            self._parts("**Gracias** (thank you)."),
            "**Gracias** (thank you). ¿Puedes decirlo?",
            sheet=s,
        )
        self.assertNotIn("gate:unscaffolded_new_item", g1.faults)
        self.assertIn("gracias", g1.scaffold_saved)
        self.assertEqual(g1.scaffold_saved["gracias"], "gloss")
        # The session's post-turn wiring (conv_session) does exactly this:
        for key, kind in g1.scaffold_saved.items():
            s = mark_first_seen(s, key, "lexicon", kind)
        # first_seen is NOT an introduction: budget stays router-only.
        self.assertFalse(is_introduced(s, "gracias", "lexicon"))
        g2 = self._gate(self._parts("Gracias."), "Gracias.", sheet=s)
        self.assertNotIn("gate:unscaffolded_new_item", g2.faults)
        self.assertNotIn("gate:regloss", g2.faults)
        # Skipped keys are not re-reported (no repeat first_seen writes).
        self.assertNotIn("gracias", g2.scaffold_saved)

    def test_bare_first_seen_stops_refaulting(self):
        # AMEND 2a executed end-to-end: a BARE key soft-faults on turn 1
        # but its exposure lands in scaffold_saved ("bare"); after the
        # session's first_seen write the same bare key never faults again
        # (the «bien» fired-5× pathology in the baseline run).
        from tutor.character_sheet import default_sheet
        from tutor.retrieval_scheduler import is_introduced, mark_first_seen

        s = default_sheet()
        g1 = self._gate(
            self._parts("Gracias."), "Gracias. ¿Puedes decirlo?", sheet=s
        )
        self.assertIn("gate:unscaffolded_new_item", g1.faults)
        self.assertEqual(g1.scaffold_saved.get("gracias"), "bare")
        for key, kind in g1.scaffold_saved.items():
            s = mark_first_seen(s, key, "lexicon", kind)
        self.assertFalse(is_introduced(s, "gracias", "lexicon"))
        g2 = self._gate(
            self._parts("Gracias."), "Gracias. ¿Puedes decirlo?", sheet=s
        )
        self.assertNotIn("gate:unscaffolded_new_item", g2.faults)
        self.assertNotIn("gracias", g2.scaffold_saved)

    def test_formula_storm_is_one_soft_advisory(self):
        # Retune 2026-08-03: the >=3 flood split is DELETED (it INVERTED
        # severity — more bare keys read as softer).  A 6-key formula
        # storm is the same ONE soft advisory as a single bare key, every
        # key exposure-recorded.  («bien»/«y tú» ride how_are_you theme →
        # the extras beyond the first are the cluster veto's, which stays
        # critical at any count.)
        parts = {
            "acknowledge": "¡Hola! Buenos días.",
            "model": "¿Cómo estás? Bien, gracias. ¿Y tú?",
            "try": "¿Puedes decirlo?",
            "structured": True,
        }
        g = self._gate(
            parts,
            "¡Hola! Buenos días. ¿Cómo estás? Bien, gracias. ¿Y tú? "
            "¿Puedes decirlo?",
        )
        self.assertIn("gate:unscaffolded_new_item", g.faults)
        self.assertNotIn("gate:unscaffolded_flood", g.faults)
        # Every visibly-used key is exposure-recorded, faulted or not.
        for key in ("hola", "buenos días", "cómo estás", "bien", "gracias",
                    "y tú"):
            self.assertIn(key, g.scaffold_saved, key)
        # The flood machinery is dead: no threshold constant, no
        # flood_keys result field.
        import tutor.output_gate as output_gate_mod
        from tutor.output_gate import OutputGateResult

        self.assertFalse(hasattr(output_gate_mod, "FLOOD_MIN_DISTINCT"))
        self.assertNotIn(
            "flood_keys", OutputGateResult.__dataclass_fields__
        )

    def test_bare_same_theme_pair_is_cluster_veto(self):
        # Two bare farewells: the first is the soft bare advisory, the
        # second is the CRITICAL cluster extra — severity comes from
        # interference, not from the bare count.
        g = self._gate(
            self._parts("Hasta luego. Adiós."),
            "Hasta luego. Adiós. ¿Puedes decirlo?",
        )
        self.assertIn("gate:unscaffolded_new_item", g.faults)
        self.assertIn("gate:cluster_veto", g.faults)
        # No double-fault: the cluster extra is not also in the advisory.
        note = next(
            n for n in g.notes if n.startswith("gate:unscaffolded_new_item ")
        )
        self.assertNotIn("adiós", note)

    def test_cluster_extra_glossed_stays_critical_bare_keys_soft(self):
        # 5 firing keys incl. 2 same-theme glossed farewells: the glossed
        # cluster extra (adiós) is CRITICAL gate:cluster_veto; the 3 bare
        # non-cluster keys ride the ONE soft advisory.  ALL of them are
        # exposure-recorded (AMEND 2a — even the faulted extra: the
        # learner saw it).
        g = self._gate(
            self._parts(
                "**Hasta luego** (see you later). **Adiós** (goodbye). "
                "¡Hola! Gracias. Pan."
            ),
            "**Hasta luego** (see you later). **Adiós** (goodbye). "
            "¡Hola! Gracias. Pan. ¿Puedes decirlo?",
        )
        self.assertIn("gate:cluster_veto", g.faults)
        self.assertIn("gate:unscaffolded_new_item", g.faults)
        self.assertIn("GATE FAIL", g.repair_instruction)
        self.assertFalse(g.ok)
        self.assertEqual(g.scaffold_saved.get("hasta luego"), "gloss")
        self.assertEqual(g.scaffold_saved.get("adiós"), "gloss")
        self.assertEqual(g.scaffold_saved.get("hola"), "bare")
        self.assertEqual(g.scaffold_saved.get("gracias"), "bare")
        self.assertEqual(g.scaffold_saved.get("pan"), "bare")

    def test_structural_keys_soy_never_faults(self):
        # AMEND 3 option B: ser/estar surface forms are paradigm
        # infrastructure even where the table themes them elsewhere
        # («soy» sits under introductions).
        from tutor.character_sheet import default_sheet
        from tutor.output_gate import (
            STRUCTURAL_KEYS,
            STRUCTURAL_THEMES,
            scan_unscaffolded_new_items,
        )

        bare, extras, _reglossed, saved = scan_unscaffolded_new_items(
            self._parts("Yo soy estudiante."),
            "Yo soy estudiante. ¿Puedes decirlo?",
            table=self.table,
            sheet=default_sheet(),
        )
        self.assertNotIn("soy", bare)
        self.assertNotIn("soy", extras)
        self.assertNotIn("soy", saved)
        # Grok's exact frozen set — and the guardrail: formulaic themes
        # (greetings/how_are_you/farewells) must NOT be structural.
        self.assertEqual(STRUCTURAL_KEYS, frozenset({
            "soy", "eres", "es", "somos", "sois", "son",
            "estoy", "estás", "está", "estamos", "estáis", "están",
        }))
        for theme in ("greetings", "how_are_you", "farewells"):
            self.assertNotIn(theme, STRUCTURAL_THEMES)

    def test_learner_own_utterance_key_does_not_fault(self):
        # Round-2 soft residual: a key in the learner's OWN current
        # utterance is exposure evidence (observer lags the gate by one
        # turn) — the tutor echoing it bare never faults.
        g = self._gate(
            self._parts("Gracias."),
            "Gracias. ¿Puedes decirlo?",
            learner_text="Muchas gracias, amigo.",
        )
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)
        self.assertNotIn("gate:unscaffolded_flood", g.faults)
        # Control: without the learner utterance the same turn faults.
        g2 = self._gate(self._parts("Gracias."), "Gracias. ¿Puedes decirlo?")
        self.assertIn("gate:unscaffolded_new_item", g2.faults)

    def test_mucho_gusto_in_acknowledge_is_critical(self):
        # Incident regression (session 20260728-103617 turn 5, blind-grade
        # defect #2): bare «¡Mucho gusto, Patrick!» rode the ACKNOWLEDGE
        # part while the gate scanned only model/try — it reached the
        # learner with the gate live and never faulted. The scan now covers
        # ALL visible teaching text: one bare table key in acknowledge with
        # an unrelated model/try is a CRITICAL fault.
        parts = {
            "acknowledge": "¡Mucho gusto, Patrick! ¡Qué bien!",
            "model": "Yo también estoy en el bote.",
            "try": "¿Dónde estás hoy?",
            "structured": True,
        }
        g = self._gate(
            parts,
            "¡Mucho gusto, Patrick! ¡Qué bien! Yo también estoy en el "
            "bote. ¿Dónde estás hoy?",
            learner_text="estoy bien.  Me llamo Patrick",
        )
        self.assertIn("gate:unscaffolded_new_item", g.faults)
        self.assertIn("GATE FAIL", g.repair_instruction)
        self.assertFalse(g.ok)
        self.assertNotIn("gate:unscaffolded_flood", g.faults)

    def test_lapsed_planned_intro_records_scaffold_saved_not_bare(self):
        # Audit (a4) 2026-07-28 (Grok's encantado proof): an R-A cognate
        # plan whose reply delivers a GLOSS instead of the anchor must still
        # record scaffold_saved for the planned key (no bare fault) — the
        # session writes first_seen on the lapse so the glossed exposure is
        # not forgotten. Previously introduce_key was skipped entirely and
        # BOTH ledgers stayed blind → critical thrash on next bare use.
        from tutor.character_sheet import default_sheet
        from tutor.output_gate import scan_unscaffolded_new_items

        reply = "**encantado** (a short gloss)"
        bare, extras, _reglossed, saved = scan_unscaffolded_new_items(
            self._parts(reply),
            f"{reply} ¿Puedes decirlo?",
            table=self.table,
            sheet=default_sheet(),
            introduce_key="encantado",
        )
        self.assertEqual(bare, [])
        self.assertEqual(extras, [])
        self.assertEqual(saved.get("encantado"), "gloss")

    def test_planned_key_bare_no_fault_but_exposure_recorded(self):
        # Planned key with NO scaffold at all: the introduce path owns the
        # lapse (no bare fault) — but the exposure is still recorded (AMEND
        # 2a: EVERY visibly-used key gets first_seen; previously the lapsed
        # planned key left both ledgers blind → thrash on next bare use).
        from tutor.character_sheet import default_sheet
        from tutor.output_gate import scan_unscaffolded_new_items

        bare, _extras, _reglossed, saved = scan_unscaffolded_new_items(
            self._parts("Encantado."),
            "Encantado. ¿Puedes decirlo?",
            table=self.table,
            sheet=default_sheet(),
            introduce_key="encantado",
        )
        self.assertEqual(bare, [])
        self.assertEqual(saved.get("encantado"), "bare")

    def test_mucho_gusto_glossed_in_acknowledge_is_clean(self):
        # Same incident shape WITH the ≤6-word gloss — clean, and the key
        # earns its scaffold-saved first_seen credit.
        parts = {
            "acknowledge": "¡Mucho gusto (nice to meet you), Patrick!",
            "model": "Yo también estoy en el bote.",
            "try": "¿Dónde estás hoy?",
            "structured": True,
        }
        g = self._gate(
            parts,
            "¡Mucho gusto (nice to meet you), Patrick! Yo también estoy "
            "en el bote. ¿Dónde estás hoy?",
            learner_text="estoy bien.  Me llamo Patrick",
        )
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)
        self.assertEqual(g.scaffold_saved.get("mucho gusto"), "gloss")


class TestAnchorAttachment(unittest.TestCase):
    """2026-07-29 floating-anchor incident: anchor_in_reply requires the
    item on the SAME LINE as the anchor (§2.2 attachment clause). key is
    REQUIRED — the keyless presence-anywhere form was killed by the
    countersign (zero callers; the keyless path IS the founding bug)."""

    ENTRY = {"cognate_en": "enchanted"}

    def test_same_line_attaches(self):
        from tutor.output_gate import anchor_in_reply

        text = "**Encantado** — like English 'enchanted'.\nDi: Encantado."
        self.assertTrue(anchor_in_reply(self.ENTRY, text, key="encantado"))

    def test_floating_anchor_rejected(self):
        from tutor.output_gate import anchor_in_reply

        text = (
            "Like English 'enchanted' — delighted.\n"
            "Me llamo Marisol. **Encantado**."
        )
        self.assertFalse(anchor_in_reply(self.ENTRY, text, key="encantado"))
        # empty key can never attach (presence-anywhere is dead)
        self.assertFalse(anchor_in_reply(self.ENTRY, text, key=""))

    def test_absent_anchor_stays_false(self):
        from tutor.output_gate import anchor_in_reply

        self.assertFalse(
            anchor_in_reply(self.ENTRY, "**Encantado** (mucho gusto).",
                            key="encantado")
        )


class TestEnglishWallZeroExemption(unittest.TestCase):
    """2026-07-28 zero-English incident: a COMPLIANT true-zero opening
    (English framing + glossed tiny Spanish, tl_ratio 0.32-0.40) tripped
    gate:english_wall, whose forced "Rewrite Spanish-forward" re-ask
    reproduced the 100%-Spanish opening. blank_zero turns use min_ratio
    0.25 (the placement-MODE arm died with the router — the blank_zero
    flag, re-derived in turn_pipeline.stage_gate_context, is the only
    true-zero path); genuine all-English still faults."""

    # Measured ratio 0.35, alpha 34 (fixture arithmetic asserted below).
    ZERO_OPEN_PARTS = {
        "acknowledge": (
            "Welcome! We will go slowly and I will always show you what "
            "things mean."
        ),
        "model": "Hola (hello). Estoy bien (I am fine). Me llamo Marisol "
                 "(my name is Marisol).",
        "try": "Try: Me llamo ___ — my name is ___",
        "structured": True,
    }

    def _blob(self, parts):
        return " ".join(
            str(parts.get(k) or "")
            for k in ("acknowledge", "recast", "explain", "model", "try",
                      "continue")
        )

    def test_fixture_ratio_is_in_the_zero_band(self):
        from tutor.output_gate import ratio_blob_with_sandwich_exempt

        parts = self.ZERO_OPEN_PARTS
        r = spanish_token_ratio(
            ratio_blob_with_sandwich_exempt(parts, self._blob(parts))
        )
        self.assertGreaterEqual(r, 0.32)
        self.assertLessEqual(r, 0.40)
        self.assertGreaterEqual(
            alphabetic_token_count(self._blob(parts)), MIN_ALPHA_TOKENS
        )

    def test_compliant_zero_open_passes_with_blank_zero(self):
        # The open turn of a true zero rides the same blank_zero flag
        # (stage_gate_context: blank sheet AND no spanish_ok this turn).
        parts = self.ZERO_OPEN_PARTS
        g = check_output_gate(
            parts, self._blob(parts), is_open=True, blank_zero=True,
        )
        self.assertNotIn("gate:english_wall", g.faults)

    def test_compliant_zero_turn_passes_with_blank_zero_flag(self):
        parts = self.ZERO_OPEN_PARTS
        g = check_output_gate(
            parts, self._blob(parts), is_open=False, blank_zero=True,
        )
        self.assertNotIn("gate:english_wall", g.faults)

    def test_same_turn_without_blank_zero_still_walls(self):
        # Normal-learner thresholds unchanged: ratio 0.35 < 0.50 faults in a
        # plain turn.
        parts = self.ZERO_OPEN_PARTS
        g = check_output_gate(parts, self._blob(parts), is_open=False)
        self.assertIn("gate:english_wall", g.faults)

    def test_all_english_still_faults_everywhere(self):
        # Genuine all-English (ratio 0.0) faults even under blank_zero.
        parts = {
            "acknowledge": "Good job you nailed it!",
            "model": "That means my name is.",
            "try": "Please say your name in Spanish now.",
            "structured": True,
        }
        blob = self._blob(parts)
        self.assertEqual(spanish_token_ratio(blob), 0.0)
        g1 = check_output_gate(parts, blob, is_open=True, blank_zero=True)
        self.assertIn("gate:english_wall", g1.faults)
        g2 = check_output_gate(parts, blob, is_open=False, blank_zero=True)
        self.assertIn("gate:english_wall", g2.faults)
        g3 = check_output_gate(parts, blob, is_open=False)
        self.assertIn("gate:english_wall", g3.faults)
        for g in (g1, g2, g3):
            self.assertIn("GATE FAIL", g.repair_instruction)
            self.assertFalse(g.ok)


class TestProbeLoopTopicRegistry(unittest.TestCase):
    """2026-07-28 repetition forensics: gate:probe_loop generalized past the
    4 hardcoded social regexes via the asked-topic registry (same extractor
    that writes SessionMemory.asked_topics)."""

    # Verbatim session 20260728-120335 turn-3 try (the city-size question the
    # learner complained was re-asked: "didnt you just ask this?").
    CITY_TRY = "¿Y tu casa? ¿Está en una ciudad grande o en una ciudad pequeña?"

    def _parts(self, try_text):
        return {
            "acknowledge": "¡Muy bien!",
            "model": "Mi casa está en una ciudad pequeña.",
            "try": try_text,
            "structured": True,
        }

    def test_second_identical_city_size_try_faults(self):
        from tutor.session_memory import SessionMemory, topic_key_for_try

        mem = SessionMemory()
        frame, concept = topic_key_for_try(self.CITY_TRY)
        key = mem.note_asked_topic(frame, concept)
        self.assertEqual(key, "size:ciudad")
        # Turn 5 re-asks the same size:ciudad question verbatim → fault.
        g = check_output_gate(
            self._parts(self.CITY_TRY),
            self.CITY_TRY,
            is_open=False,
            asked_topics=mem.asked_topics,
        )
        self.assertIn("gate:probe_loop", g.faults)
        self.assertTrue(
            any("topic:size:ciudad" in n for n in g.notes), g.notes
        )
        self.assertIn("GATE FAIL", g.repair_instruction)
        self.assertFalse(g.ok)

    def test_new_frame_on_same_concept_does_not_fault(self):
        # A NEW frame on the same concept ("what's IN your house" after
        # location:casa) is a legitimate follow-up, not a loop.
        g = check_output_gate(
            self._parts("¿Qué hay en tu casa?"),
            "¿Qué hay en tu casa?",
            is_open=False,
            asked_topics={"location:casa"},
        )
        self.assertNotIn("gate:probe_loop", g.faults)

    def test_registry_check_uses_try_not_model(self):
        # The registry key comes from the composed TRY; a model sentence
        # mentioning the noun must not fault the turn.
        g = check_output_gate(
            self._parts("¿Te gusta el café?"),
            "Mi casa está en una ciudad pequeña. ¿Te gusta el café?",
            is_open=False,
            asked_topics={"size:ciudad"},
        )
        self.assertNotIn("gate:probe_loop", g.faults)

    def _due_sheet(self, key):
        s = default_sheet()
        s["lexicon"][key] = {
            "status": "emerging",
            "confidence": 0.3,
            "next_due": "2020-01-01",
            "interval_days": 1,
        }
        return s

    def test_due_concept_exempt_from_topic_probe_loop(self):
        # Audit (a2) 2026-07-28: retrieval outranks anti-repeat (P3 spacing
        # is law; do_not_re_ask is a courtesy) — a currently-due «casa» may
        # be re-elicited even with location:casa already in the registry.
        g = check_output_gate(
            self._parts("¿Dónde está tu casa?"),
            "¿Dónde está tu casa?",
            is_open=False,
            asked_topics={"location:casa"},
            sheet=self._due_sheet("casa"),
        )
        self.assertNotIn("gate:probe_loop", g.faults)
        self.assertTrue(
            any("probe_loop_due_exempt:location:casa" in n for n in g.notes),
            g.notes,
        )

    def test_same_topic_without_due_still_faults(self):
        # Control for the (a2) exemption: same registry hit, no due «casa».
        g = check_output_gate(
            self._parts("¿Dónde está tu casa?"),
            "¿Dónde está tu casa?",
            is_open=False,
            asked_topics={"location:casa"},
            sheet=default_sheet(),
        )
        self.assertIn("gate:probe_loop", g.faults)
        self.assertTrue(
            any("topic:location:casa" in n for n in g.notes), g.notes
        )

    def test_due_exemption_matches_accented_ledger_key(self):
        # Ledger keys keep accents («café»); the extractor deaccents its
        # concept ("cafe") — the exemption compares through the same
        # _deaccent transform, exact key match otherwise.
        g = check_output_gate(
            self._parts("¿Dónde está el café?"),
            "¿Dónde está el café?",
            is_open=False,
            asked_topics={"location:cafe"},
            sheet=self._due_sheet("café"),
        )
        self.assertNotIn("gate:probe_loop", g.faults)

    def test_social_fast_path_still_fires_without_registry(self):
        # Regression: the 4 social regexes keep working with no registry
        # (the T8/T9 true-positive class — a near-identical try re-asked).
        parts = {
            "acknowledge": "¡Hola!",
            "model": "Me llamo Sofía.",
            "try": "¿Cómo te llamas?",
            "structured": True,
        }
        g = check_output_gate(
            parts,
            "¿Cómo te llamas?",
            already_asked={"ask_name"},
        )
        self.assertIn("gate:probe_loop", g.faults)


class TestGateContextParity(unittest.TestCase):
    """E3 (Phase 4 batch 3): check_output_gate(GateContext) is the
    surface; the legacy kwarg call is a thin shim building the same
    context.  Parity: both paths must return identical results on
    identical inputs — including a fault-rich case exercising the r7 S3
    table/sheet checks and the probe fast path.  (The mode-keyed fields —
    mode / already_shown / require_recast / image_present — died with the
    mode-keyed contracts, gate retune 2026-08-03; image_concepts joined.)"""

    def _inputs(self):
        from pathlib import Path

        from tutor.association_table import load_association_table

        root = Path(__file__).resolve().parents[1]
        table = load_association_table(root / "domain" / "spanish_a1")
        parts = {
            "acknowledge": "Good job you nailed it, that was really great!",
            "model": "Hasta luego.",
            "try": "¿Qué te gusta?",
            "structured": True,
        }
        visible = (
            "Good job you nailed it, that was really great! "
            "Hasta luego. ¿Qué te gusta?"
        )
        kwargs = dict(
            is_open=False,
            already_asked={"ask_gusta"},
            image_concepts=set(),
            raw="<tutor>" + visible + "</tutor>",
            truncated=True,
            association_table=table,
            sheet=default_sheet(),
            introduce_key=None,
            retrieval_failed_keys={"agua"},
            learner_text="see you later",
            blank_zero=False,
            asked_topics=set(),
            topic_nouns=[],
        )
        return parts, visible, kwargs

    def test_shim_path_equals_context_path(self):
        from tutor.output_gate import GateContext

        parts, visible, kwargs = self._inputs()
        legacy = check_output_gate(parts, visible, **kwargs)
        via_ctx = check_output_gate(
            GateContext(parts=parts, visible=visible, **kwargs)
        )
        self.assertEqual(legacy.as_dict(), via_ctx.as_dict())
        # The case is fault-rich on purpose — parity on a trivial OK turn
        # would prove nothing.  Three distinct check families trip: the
        # truncation flag, the r7 S3 table/sheet scan («hasta luego» bare
        # + unglossed) and the probe fast path (ask_gusta re-asked).
        for fault in (
            "gate:truncated",
            "gate:unscaffolded_new_item", "gate:probe_loop",
        ):
            self.assertIn(fault, legacy.faults)

    def test_context_defaults_match_shim_defaults(self):
        from tutor.output_gate import GateContext

        parts = {"model": "Estoy bien.", "try": "¿Y tú?", "structured": True}
        legacy = check_output_gate(parts, "Estoy bien. ¿Y tú?")
        via_ctx = check_output_gate(
            GateContext(parts=parts, visible="Estoy bien. ¿Y tú?")
        )
        self.assertEqual(legacy.as_dict(), via_ctx.as_dict())

    def test_context_field_census(self):
        # The dataclass carries EXACTLY the retuned surface (15 fields —
        # the 18-arg seam minus mode/already_shown/require_recast/
        # image_present, plus image_concepts).
        from tutor.output_gate import GateContext

        assert sorted(GateContext.__dataclass_fields__) == sorted([
            "parts", "visible",
            "is_open", "already_asked", "image_concepts", "raw",
            "truncated",
            "association_table", "sheet", "introduce_key",
            "retrieval_failed_keys", "learner_text", "blank_zero",
            "asked_topics", "topic_nouns",
        ])
        assert len(GateContext.__dataclass_fields__) == 15


class TestToolOnlyAbility(unittest.TestCase):
    """Tool-only ability (2026-07-31): no regex hard-observer grade path."""

    def test_tool_grades_only_what_was_claimed(self):
        sheet = default_sheet()
        tool_delta = {
            "reason": "saw greeting",
            "evidence": "Hola",
            "skills": {
                "IP-01": {"status": "emerging", "confidence": 0.2},
            },
        }
        s, _, notes = process_turn(
            sheet,
            "Hola, estoy bien. Me llamo Patrick.",
            "¡Hola Patrick!",
            tool_delta=tool_delta,
        )
        self.assertNotIn("hard_observer", notes)
        self.assertIn("tool_update", notes)
        self.assertTrue(any(n.startswith("why=") for n in notes))
        # Only claimed IP-01 moves; IP-03/IP-04 stay frozen without tool claims.
        ip1 = (s.get("skills") or {}).get("IP-01") or {}
        ip3 = (s.get("skills") or {}).get("IP-03") or {}
        ip4 = (s.get("skills") or {}).get("IP-04") or {}
        self.assertGreater(float(ip1.get("confidence") or 0), 0.05)
        self.assertEqual(float(ip3.get("confidence") or 0), 0.0)
        self.assertEqual(float(ip4.get("confidence") or 0), 0.0)
        # Personal-data capture disabled: no name is ever stored.
        self.assertIsNone((s.get("identity") or {}).get("preferred_name"))

    def test_no_tool_freezes_ability_but_scaffold_still_updates(self):
        s, _, notes = process_turn(
            default_sheet(),
            "what does ves mean?",
            "Ves means you see.",
        )
        self.assertIn("rules_backup", notes)
        self.assertNotIn("hard_observer", notes)
        self.assertEqual(
            float((s.get("skills") or {}).get("IP-01", {}).get("confidence") or 0),
            0.0,
        )
        self.assertTrue(s["receptive"]["needs_english_scaffold"])


if __name__ == "__main__":
    unittest.main()
