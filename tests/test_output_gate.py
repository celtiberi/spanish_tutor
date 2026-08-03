"""Output gate — plumbing-only surface (S11, 2026-08-03) + hard observer.

The gate keeps exactly two faults (gate:truncated, gate:sheet_leak) and the
first-exposure bookkeeping scan.  Every deleted teaching-opinion check is
pinned ABSENT here; its transcript-level successor is tested in
tests/test_student_checks.py.  No live API.
"""

import unittest

from tutor.character_sheet import default_sheet, process_turn
from tutor.output_gate import (
    GateContext,
    OutputGateResult,
    check_output_gate,
    detect_sheet_leak,
    scan_first_exposures,
)

# Every fault id the runtime may emit (S11) — the closed vocabulary.
PLUMBING_FAULTS = {"gate:truncated", "gate:sheet_leak"}

# Every deleted teaching-opinion fault id (absence-pinned below).
DELETED_FAULTS = (
    "gate:english_wall",
    "gate:probe_loop",
    "gate:cluster_veto",
    "gate:unscaffolded_new_item",
    "gate:unscaffolded_flood",
    "gate:regloss",
    "gate:missing_recast",
    "gate:form_focus_needs_model",
    "gate:comprehension_needs_check",
    "pedagogy:no_teach_move",
    "pedagogy:open_needs_model_try",
    "pedagogy:recast_without_try",
)


def _real_table():
    from pathlib import Path

    from tutor.association_table import load_association_table

    root = Path(__file__).resolve().parents[1]
    return load_association_table(root / "domain" / "spanish_a1")


class TestPlumbingChecks(unittest.TestCase):
    def test_clean_turn_ok(self):
        parts = {
            "acknowledge": "¡Qué bien!",
            "model": "Me llamo Sofía.",
            "try": "¿Y tú? ¿Cómo te llamas?",
            "structured": True,
        }
        g = check_output_gate(
            parts, "¡Qué bien! Me llamo Sofía. ¿Cómo te llamas?"
        )
        self.assertTrue(g.ok, g.faults)
        self.assertEqual(g.faults, [])
        self.assertEqual(g.repair_instruction, "")

    def test_truncated_is_a_fault(self):
        g = check_output_gate(
            {"model": "Estoy", "structured": True},
            "Estoy",
            truncated=True,
        )
        self.assertFalse(g.ok)
        self.assertIn("gate:truncated", g.faults)
        self.assertIn("GATE FAIL", g.repair_instruction)
        self.assertTrue(
            any(n.startswith("gate:truncated") for n in g.notes), g.notes
        )

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

    def test_tool_name_in_prose_is_not_a_leak(self):
        # JSON-context tool-name rule (gate retune 2026-08-03, kept by S11):
        # the system prompt teaches the model the term — prose mention is
        # not a sheet dump; call-ish context is.
        self.assertEqual(
            detect_sheet_leak("I quietly use update_character_sheet after "
                              "each turn."),
            [],
        )
        self.assertTrue(
            detect_sheet_leak('{"update_character_sheet": {"skills": {}}}')
        )

    def test_fault_vocabulary_is_closed(self):
        # A turn engineered to trip every DELETED check at once emits ONLY
        # plumbing faults (here: none — nothing is truncated or leaked).
        table = _real_table()
        parts = {
            # english wall material + bare same-theme farewell pair +
            # a probing try — none of it faults anymore.
            "acknowledge": "Good job you nailed it, that was really great!",
            "model": "Hasta luego. Adiós.",
            "try": "Please try to say the whole word again for me now.",
            "structured": True,
        }
        g = check_output_gate(
            parts,
            "Good job you nailed it! Hasta luego. Adiós. Please try to "
            "say the whole word again for me now.",
            association_table=table,
            sheet=default_sheet(),
        )
        self.assertTrue(g.ok, g.faults)
        for fault in DELETED_FAULTS:
            self.assertNotIn(fault, g.faults)
        # ... but the exposure map still recorded the bare keys.
        self.assertEqual(g.scaffold_saved.get("hasta luego"), "bare")
        self.assertEqual(g.scaffold_saved.get("adiós"), "bare")


class TestDeletedSurface(unittest.TestCase):
    """Absence pins: the teaching-opinion machinery must not resurface."""

    def test_deleted_helpers_and_constants(self):
        import tutor.output_gate as og

        for name in (
            "MIN_SPANISH_RATIO", "MIN_ALPHA_TOKENS",
            "ZERO_MIN_SPANISH_RATIO", "MAX_EXPLAIN_GLOSS_WORDS",
            "spanish_token_ratio", "tutor_spanish_ratio",
            "explain_gloss_word_count", "ratio_blob_with_sandwich_exempt",
            "detect_tutor_probe_keys", "_PROBE_PATTERNS",
            "scan_unscaffolded_new_items", "FLOOD_MIN_DISTINCT",
            "_ES_RE", "_EN_RE", "evaluate_turn",
        ):
            self.assertFalse(hasattr(og, name), name)

    def test_result_field_census(self):
        # spanish_ratio (english-wall telemetry) died with the wall.
        self.assertEqual(
            sorted(OutputGateResult.__dataclass_fields__),
            sorted([
                "ok", "faults", "notes", "repair_instruction",
                "scaffold_saved",
            ]),
        )
        d = OutputGateResult(ok=True).as_dict()
        self.assertEqual(
            sorted(d),
            sorted([
                "ok", "faults", "notes", "repair_instruction",
                "scaffold_saved",
            ]),
        )

    def test_context_field_census(self):
        # S11 surface: the fields only teaching checks read are GONE
        # (is_open / already_asked / introduce_key / retrieval_failed_keys /
        # blank_zero / asked_topics / topic_nouns).
        self.assertEqual(
            sorted(GateContext.__dataclass_fields__),
            sorted([
                "parts", "visible", "raw", "truncated",
                "image_concepts", "association_table", "sheet",
                "learner_text",
            ]),
        )
        self.assertEqual(len(GateContext.__dataclass_fields__), 8)

    def test_deleted_faults_never_emitted_on_provocations(self):
        table = _real_table()
        provocations = [
            # probing try, previously gate:probe_loop material
            ({"model": "Me llamo Sofía.", "try": "¿Cómo te llamas?",
              "structured": True},
             "Me llamo Sofía. ¿Cómo te llamas?"),
            # long English, previously gate:english_wall material
            ({"acknowledge": "Good job you nailed it!",
              "model": "That means my name is.",
              "try": "Please say your name in Spanish now.",
              "structured": True},
             "Good job you nailed it! That means my name is. Please say "
             "your name in Spanish now."),
            # no teach move, previously pedagogy:no_teach_move material
            ({"acknowledge": "¡Hola amigo!", "continue": "¿Todo bien?",
              "structured": True},
             "¡Hola amigo! ¿Todo bien?"),
            # unstructured empty reply
            ({}, ""),
        ]
        for parts, visible in provocations:
            g = check_output_gate(
                parts, visible,
                association_table=table, sheet=default_sheet(),
            )
            self.assertTrue(g.ok, (parts, g.faults))
            self.assertTrue(set(g.faults) <= PLUMBING_FAULTS)


class TestFirstExposureScan(unittest.TestCase):
    """The surviving bookkeeping half (exposure map → first_seen ledger).

    Runs against the REAL pack association table — bookkeeping is tested
    on shipped data."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = _real_table()

    def _gate(self, parts, visible, *, sheet=None, table="real", **kw):
        return check_output_gate(
            parts,
            visible,
            association_table=(self.table if table == "real" else table),
            sheet=sheet if sheet is not None else default_sheet(),
            **kw,
        )

    def _parts(self, model, try_="¿Puedes decirlo?"):
        return {"model": model, "try": try_, "structured": True}

    def test_bare_key_recorded_no_fault(self):
        g = self._gate(
            self._parts("Hasta luego."),
            "Hasta luego. ¿Puedes decirlo?",
        )
        self.assertTrue(g.ok, g.faults)
        self.assertEqual(g.scaffold_saved.get("hasta luego"), "bare")

    def test_glossed_key_recorded_as_gloss(self):
        g = self._gate(
            self._parts("**Hasta luego** (see you later)."),
            "**Hasta luego** (see you later). ¿Puedes decirlo?",
        )
        self.assertEqual(g.scaffold_saved.get("hasta luego"), "gloss")

    def test_same_turn_image_counts_as_scaffold(self):
        # AMEND 2b: an attached teach image for the key IS its scaffold.
        g = self._gate(
            self._parts("Hasta luego."),
            "Hasta luego. ¿Puedes decirlo?",
            image_concepts={"hasta_luego"},
        )
        self.assertEqual(g.scaffold_saved.get("hasta luego"), "image")

    def test_every_visible_key_recorded_formula_storm(self):
        # A 6-key formula storm: no fault of any kind, every key exposure-
        # recorded (the deleted flood/cluster opinions live in evals now).
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
        self.assertTrue(g.ok, g.faults)
        for key in ("hola", "buenos días", "cómo estás", "bien", "gracias",
                    "y tú"):
            self.assertIn(key, g.scaffold_saved, key)

    def _introduced_sheet(self, *keys):
        from tutor.retrieval_scheduler import mark_introduced

        s = default_sheet()
        for k in keys:
            s = mark_introduced(s, k, "lexicon", "gloss")
        return s

    def test_introduced_key_not_recorded(self):
        g = self._gate(
            self._parts("Hasta luego."),
            "Hasta luego.",
            sheet=self._introduced_sheet("hasta luego"),
        )
        self.assertTrue(g.ok)
        self.assertNotIn("hasta luego", g.scaffold_saved)

    def test_first_seen_key_not_re_recorded(self):
        # AMEND 1c/2a: after the durable first_seen write the key stops
        # being reported (no repeat ledger writes; the «bien» fired-5×
        # pathology stays dead).
        from tutor.retrieval_scheduler import is_introduced, mark_first_seen

        s = default_sheet()
        g1 = self._gate(
            self._parts("Gracias."), "Gracias. ¿Puedes decirlo?", sheet=s
        )
        self.assertEqual(g1.scaffold_saved.get("gracias"), "bare")
        # The session's post-turn wiring (stage_first_seen) does exactly this:
        for key, kind in g1.scaffold_saved.items():
            s = mark_first_seen(s, key, "lexicon", kind)
        # first_seen is NOT an introduction (honesty law).
        self.assertFalse(is_introduced(s, "gracias", "lexicon"))
        g2 = self._gate(
            self._parts("Gracias."), "Gracias. ¿Puedes decirlo?", sheet=s
        )
        self.assertNotIn("gracias", g2.scaffold_saved)

    def test_sheet_evidence_key_not_recorded(self):
        # The learner has produced hola (lexicon confidence > 0): not a
        # first exposure.
        s = default_sheet()
        s["lexicon"]["hola"] = {"status": "emerging", "confidence": 0.3}
        g = self._gate(self._parts("¡Hola!"), "¡Hola!", sheet=s)
        self.assertNotIn("hola", g.scaffold_saved)

    def test_learner_own_utterance_key_not_recorded(self):
        # A key in the learner's OWN current utterance is their exposure
        # (observer lags the gate) — not recorded as tutor exposure.
        g = self._gate(
            self._parts("Gracias."),
            "Gracias. ¿Puedes decirlo?",
            learner_text="Muchas gracias, amigo.",
        )
        self.assertNotIn("gracias", g.scaffold_saved)
        # Control: without the learner utterance the exposure records.
        g2 = self._gate(self._parts("Gracias."), "Gracias. ¿Puedes decirlo?")
        self.assertEqual(g2.scaffold_saved.get("gracias"), "bare")

    def test_structural_keys_and_themes_never_recorded(self):
        # Pronouns / copula surface forms are paradigm infrastructure
        # (Round-2 AMEND 3B) — «soy» sits under introductions in the table
        # but stays exempt.
        from tutor.output_gate import STRUCTURAL_KEYS, STRUCTURAL_THEMES

        saved = scan_first_exposures(
            self._parts("Yo soy estudiante."),
            "Yo soy estudiante. ¿Puedes decirlo?",
            table=self.table,
            sheet=default_sheet(),
        )
        self.assertNotIn("soy", saved)
        # Grok's exact frozen set — and the guardrail: formulaic themes
        # (greetings/how_are_you/farewells) must NOT be structural.
        self.assertEqual(STRUCTURAL_KEYS, frozenset({
            "soy", "eres", "es", "somos", "sois", "son",
            "estoy", "estás", "está", "estamos", "estáis", "están",
        }))
        for theme in ("greetings", "how_are_you", "farewells"):
            self.assertNotIn(theme, STRUCTURAL_THEMES)

    def test_overlapping_keys_count_once(self):
        # «muy bien» must not also record «bien» (longest key wins).
        g = self._gate(
            self._parts("**Muy bien** (very good)."),
            "**Muy bien** (very good).",
        )
        self.assertEqual(g.scaffold_saved.get("muy bien"), "gloss")
        self.assertNotIn("bien", g.scaffold_saved)

    def test_scan_covers_all_visible_parts(self):
        # Incident 2026-07-28 (blind-grade defect #2): «mucho gusto» in the
        # ACKNOWLEDGE part reaches the learner — the scan covers EVERY part.
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
        self.assertEqual(g.scaffold_saved.get("mucho gusto"), "bare")
        self.assertTrue(g.ok, g.faults)

    def test_disabled_without_table(self):
        g = self._gate(
            self._parts("Hasta luego."),
            "Hasta luego.",
            table=None,
        )
        self.assertEqual(g.scaffold_saved, {})


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


class TestGateContextParity(unittest.TestCase):
    """E3 (Phase 4 batch 3): check_output_gate(GateContext) is the
    surface; the legacy kwarg call is a thin shim building the same
    context.  Parity on a fault-rich case (truncation + leak + exposure
    scan engaged)."""

    def _inputs(self):
        table = _real_table()
        parts = {
            "acknowledge": "¡Qué bien!",
            "model": "Hasta luego.",
            "try": "¿Qué te gusta?",
            "structured": True,
        }
        visible = "¡Qué bien! Hasta luego. ¿Qué te gusta?"
        kwargs = dict(
            image_concepts=set(),
            raw='<tutor>' + visible + '</tutor>\n```json {"skills": {}}```',
            truncated=True,
            association_table=table,
            sheet=default_sheet(),
            learner_text="see you later",
        )
        return parts, visible, kwargs

    def test_shim_path_equals_context_path(self):
        parts, visible, kwargs = self._inputs()
        legacy = check_output_gate(parts, visible, **kwargs)
        via_ctx = check_output_gate(
            GateContext(parts=parts, visible=visible, **kwargs)
        )
        self.assertEqual(legacy.as_dict(), via_ctx.as_dict())
        # Fault-rich on purpose: both plumbing checks trip and the scan ran.
        self.assertIn("gate:truncated", legacy.faults)
        self.assertIn("gate:sheet_leak", legacy.faults)
        self.assertEqual(legacy.scaffold_saved.get("hasta luego"), "bare")

    def test_context_defaults_match_shim_defaults(self):
        parts = {"model": "Estoy bien.", "try": "¿Y tú?", "structured": True}
        legacy = check_output_gate(parts, "Estoy bien. ¿Y tú?")
        via_ctx = check_output_gate(
            GateContext(parts=parts, visible="Estoy bien. ¿Y tú?")
        )
        self.assertEqual(legacy.as_dict(), via_ctx.as_dict())


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
