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
            already_shown=set(),
        )
        self.assertTrue(g.ok, g.faults)
        self.assertTrue(
            any(n.startswith("tl_ratio=") for n in g.notes),
            g.notes,
        )

    def test_gate_loop_reask_name(self):
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
            already_shown={"name"},
        )
        self.assertFalse(g.ok)
        self.assertIn("gate:probe_loop", g.faults)

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
        self.assertIn("JSON", g.repair_instruction)


class TestUnscaffoldedNewItemGate(unittest.TestCase):
    """Phase 4 (r7 S3): gate:unscaffolded_new_item (critical) + gate:regloss
    (soft). Runs against the REAL pack association table like the router
    tests — enforcement is tested on shipped data."""

    @classmethod
    def setUpClass(cls) -> None:
        from pathlib import Path

        from tutor.association_table import load_association_table

        root = Path(__file__).resolve().parents[1]
        cls.table = load_association_table(root / "course_packs" / "spanish_a1")

    def _gate(self, parts, visible, *, sheet=None, table="real", **kw):
        from tutor.character_sheet import default_sheet

        return check_output_gate(
            parts,
            visible,
            is_open=False,
            mode=kw.pop("mode", "conversation"),
            association_table=(self.table if table == "real" else table),
            sheet=sheet if sheet is not None else default_sheet(),
            **kw,
        )

    def _parts(self, model, try_="¿Puedes decirlo?"):
        return {"model": model, "try": try_, "structured": True}

    def test_bare_unintroduced_mwu_is_critical_fault(self):
        g = self._gate(
            self._parts("Hasta luego."),
            "Hasta luego. ¿Puedes decirlo?",
        )
        self.assertIn("gate:unscaffolded_new_item", g.faults)
        self.assertIn("never seen", g.repair_instruction)
        self.assertIn("hasta luego", g.repair_instruction)
        self.assertIn("ONE", g.repair_instruction)
        self.assertTrue(
            any("gate:unscaffolded_new_item" in n for n in g.notes), g.notes
        )

    def test_glossed_new_item_passes(self):
        g = self._gate(
            self._parts("**Hasta luego** (see you later)."),
            "**Hasta luego** (see you later). ¿Puedes decirlo?",
        )
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)

    def test_two_glossed_same_theme_farewells_fault_the_extra(self):
        # r7 R-F cluster ban as CODE: one new item per turn — the second
        # farewell faults even though both carry glosses.
        parts = self._parts(
            "**Hasta luego** (see you later). **Adiós** (goodbye)."
        )
        g = self._gate(
            parts,
            "**Hasta luego** (see you later). **Adiós** (goodbye). "
            "¿Puedes decirlo?",
        )
        self.assertIn("gate:unscaffolded_new_item", g.faults)
        self.assertIn("adiós", g.repair_instruction)

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
        self.assertIn("gate:unscaffolded_new_item", g.faults)
        self.assertIn("adiós", g.repair_instruction)

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
        self.assertIn("re-gloss", g.repair_instruction)

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

    def test_placement_mode_is_exempt(self):
        g = self._gate(
            self._parts("Hasta luego."),
            "Hasta luego.",
            mode="placement",
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
        # Regression guard: r7 S3 must not blunt the wall. A long English
        # turn with a bare new item carries BOTH faults, and the repair
        # says one gloss only (no full-English rewrite invitation).
        parts = {
            "acknowledge": "Good job you nailed it, that was really great!",
            "model": "Hasta luego.",
            "try": "Please try to say the word again for me now.",
            "structured": True,
        }
        g = self._gate(parts, "Good job... Hasta luego.")
        self.assertIn("gate:english_wall", g.faults)
        self.assertIn("gate:unscaffolded_new_item", g.faults)
        self.assertIn("ONE", g.repair_instruction)

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
        self.assertNotIn("gate:unscaffolded_flood", g2.faults)
        self.assertNotIn("gate:regloss", g2.faults)
        # Skipped keys are not re-reported (no repeat first_seen writes).
        self.assertNotIn("gracias", g2.scaffold_saved)

    def test_formula_storm_softens_to_flood(self):
        # Round-2 storm soften — Grok's blank-sheet multi-formula storm:
        # 6 distinct bare keys → SOFT gate:unscaffolded_flood carrying the
        # key list, NO critical fault, no forced rewrite. Extended
        # 2026-07-28 (acknowledge-scan re-check): the greeting rides the
        # ACKNOWLEDGE part — the full-visible-text scan must find it there
        # and the storm must STILL soften to the soft flood, not go
        # critical (the formulaic-storm vector stays closed).
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
        self.assertIn("gate:unscaffolded_flood", g.faults)
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)
        self.assertEqual(
            set(g.flood_keys),
            {"hola", "buenos días", "cómo estás", "bien", "gracias", "y tú"},
        )
        self.assertTrue(
            any(n.startswith("gate:unscaffolded_flood ") for n in g.notes),
            g.notes,
        )
        # No forced rewrite: the flood fault must never enter conv_session's
        # critical set (soft by omission, like gate:regloss).
        import inspect

        import tutor.conv_session as conv_session

        self.assertNotIn(
            "gate:unscaffolded_flood", inspect.getsource(conv_session)
        )

    def test_two_bare_keys_stay_critical_no_flood(self):
        # <= 2 distinct bare keys → CRITICAL as today (dual-farewell shape
        # at N=2 is untouched by the soften).
        g = self._gate(
            self._parts("Hasta luego. Adiós."),
            "Hasta luego. Adiós. ¿Puedes decirlo?",
        )
        self.assertIn("gate:unscaffolded_new_item", g.faults)
        self.assertNotIn("gate:unscaffolded_flood", g.faults)

    def test_flood_plus_glossed_cluster_extra_keeps_critical(self):
        # 4 firing keys incl. 2 same-theme farewells: the glossed cluster
        # extra (adiós) stays CRITICAL at any count; the 3 bare non-cluster
        # keys ride the soft flood.
        g = self._gate(
            self._parts(
                "**Hasta luego** (see you later). **Adiós** (goodbye). "
                "¡Hola! Gracias. Bien."
            ),
            "**Hasta luego** (see you later). **Adiós** (goodbye). "
            "¡Hola! Gracias. Bien. ¿Puedes decirlo?",
        )
        self.assertIn("gate:unscaffolded_new_item", g.faults)
        self.assertIn("adiós", g.repair_instruction)
        self.assertIn("gate:unscaffolded_flood", g.faults)
        self.assertEqual(set(g.flood_keys), {"hola", "gracias", "bien"})
        # The kept glossed farewell was scaffold-saved; the cluster extra
        # faulted, so it must NOT earn a first_seen write.
        self.assertIn("hasta luego", g.scaffold_saved)
        self.assertNotIn("adiós", g.scaffold_saved)

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
        self.assertIn("mucho gusto", g.repair_instruction)
        self.assertNotIn("gate:unscaffolded_flood", g.faults)

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


class TestHardObserver(unittest.TestCase):
    def test_tool_path_still_bumps_from_learner_text(self):
        sheet = default_sheet()
        # Simulate tool that barely updates
        tool_delta = {
            "reason": "saw greeting",
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
        self.assertIn("hard_observer", notes)
        self.assertIn("tool_update", notes)
        # Rule evidence should raise intro / estoy skills even if tool was thin
        ip3 = (s.get("skills") or {}).get("IP-03") or {}
        ip4 = (s.get("skills") or {}).get("IP-04") or {}
        self.assertGreater(float(ip3.get("confidence") or 0), 0.05)
        self.assertGreater(float(ip4.get("confidence") or 0), 0.05)
        # Personal-data capture disabled (2026-07-28): no name is ever stored.
        self.assertIsNone((s.get("identity") or {}).get("preferred_name"))


if __name__ == "__main__":
    unittest.main()
