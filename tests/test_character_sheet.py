"""Character sheet updates (no API)."""

import json
import tempfile
import unittest
from pathlib import Path

from tutor.character_sheet import (
    UPDATE_CHARACTER_SHEET_TOOL,
    apply_delta,
    apply_rule_updates,
    clear_session_scoped_affect,
    default_sheet,
    extract_sheet_delta,
    format_sheet_human,
    is_session_scoped_energy,
    load_sheet,
    normalize_sheet,
    parse_sheet_json,
    process_turn,
    recompute_next_best,
    save_sheet,
    sanitize_tool_delta,
)


class TestSheetCore(unittest.TestCase):
    def test_default_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sheet.json"
            s = default_sheet()
            save_sheet(p, s)
            s2 = load_sheet(p)
            self.assertGreaterEqual(s2["version"], 2)
            self.assertIn("present_estar_person", s2["grammar"])
            self.assertIn("IP-01", s2["skills"])
            self.assertIn("statement", s2["skills"]["IP-01"])

    def test_estoy_bumps_grammar(self):
        s = apply_rule_updates(default_sheet(), "Hola, estoy bien")
        self.assertGreater(s["grammar"]["present_estar_person"]["confidence"], 0.1)
        self.assertIn("hola", s["lexicon"])
        self.assertGreater(s["skills"]["IP-04"]["confidence"], 0.05)

    def test_esta_bien_lowers_estar(self):
        s = apply_rule_updates(default_sheet(), "Esta bien y tu?")
        self.assertLess(
            s["grammar"]["present_estar_person"]["confidence"], 0.5)
        self.assertTrue(s["grammar"]["present_estar_person"]["evidence"])

    def test_formal_mismatch(self):
        s = apply_rule_updates(
            default_sheet(), "Buenos dias senora. Como estas?")
        g = s["grammar"]["register_tu_usted"]
        self.assertLess(g["confidence"], 0.5)
        self.assertLess(s["skills"]["IP-02"]["confidence"], 0.5)

    def test_meta_sets_boredom(self):
        s = apply_rule_updates(
            default_sheet(), "what are we even doing right now?")
        self.assertEqual(s["affect"]["boredom_risk"], "high")
        s = recompute_next_best(s)
        self.assertEqual(s["next_best"]["can_do"], "IP-08")

    def test_sheet_delta_strip(self):
        raw = (
            "¡Hola!\n\n"
            "<sheet_delta>\n"
            '{"identity": {"preferred_name": "Sam"}}\n'
            "</sheet_delta>"
        )
        visible, delta = extract_sheet_delta(raw)
        self.assertEqual(visible, "¡Hola!")
        # Parser passes the block through …
        self.assertEqual(delta["identity"]["preferred_name"], "Sam")
        # … but applying it can never store a name (capture disabled).
        s = apply_delta(default_sheet(), delta)
        self.assertIsNone((s.get("identity") or {}).get("preferred_name"))

    def test_process_turn_tool_delta(self):
        base = default_sheet()
        delta = {
            "reason": "said name as Me llama es Patrick",
            "identity": {"preferred_name": "Patrick"},
            "skills": {"IP-03": {"status": "emerging", "confidence": 0.4}},
            "receptive": {"needs_english_scaffold": True},
            "next_best": {
                "can_do": "IP-03",
                "activity": "name_exchange_in_chat",
                "avoid": "greeting_drills",
                "reason": "greets ok; stretch introduce",
            },
        }
        s, vis, notes = process_turn(
            base, "estoy bien. Me llama es Patrick",
            "¡Mucho gusto, Patrick!",
            tool_delta=delta,
        )
        self.assertEqual(vis, "¡Mucho gusto, Patrick!")
        # Personal-data capture disabled: the tool identity delta is dropped.
        self.assertIsNone((s.get("identity") or {}).get("preferred_name"))
        # harness caps +0.25/turn from 0
        self.assertAlmostEqual(s["skills"]["IP-03"]["confidence"], 0.25)
        self.assertTrue(s["receptive"]["needs_english_scaffold"])
        self.assertEqual(s["next_best"]["can_do"], "IP-03")
        self.assertIn("tool_update", notes)
        self.assertTrue(any(n.startswith("why=") for n in notes))

    def test_process_turn_ai_revised_sheet(self):
        base = default_sheet()
        revised = default_sheet()
        revised["identity"]["preferred_name"] = "Alex"
        revised["skills"]["IP-03"]["confidence"] = 0.5
        revised["skills"]["IP-03"]["status"] = "emerging"
        s, vis, notes = process_turn(
            base, "Me llamo Alex", "Nice to meet you.",
            revised_sheet=revised,
        )
        self.assertEqual(vis, "Nice to meet you.")
        # Personal-data capture disabled: AI rewrite identity is stripped.
        self.assertIsNone((s.get("identity") or {}).get("preferred_name"))
        self.assertEqual(s["skills"]["IP-03"]["confidence"], 0.5)
        self.assertIn("ai_update", notes)

    def test_process_turn_rules_backup(self):
        raw = "Nice.\n<sheet_delta>{\"identity\": {\"preferred_name\": \"Sam\"}}</sheet_delta>"
        s, vis, notes = process_turn(default_sheet(), "Me llamo Sam", raw)
        self.assertEqual(vis, "Nice.")
        # Personal-data capture disabled: inline sheet_delta identity dropped.
        self.assertIsNone((s.get("identity") or {}).get("preferred_name"))
        self.assertIn("rules_backup", notes)

    def test_cap_tool_plus_observer_single_use(self):
        """One utterance may not double-count: conf capped, one solid use."""
        base = default_sheet()
        delta = {
            "reason": "said name",
            "skills": {"IP-03": {"status": "emerging", "confidence": 0.4}},
        }
        s, _vis, _notes = process_turn(
            base, "Me llama es Patrick", "¡Mucho gusto!", tool_delta=delta,
        )
        self.assertAlmostEqual(s["skills"]["IP-03"]["confidence"], 0.25)
        self.assertEqual(s["skills"]["IP-03"]["solid_uses"], 1)

    def test_erroneous_me_llama_es_earns_no_ser_credit(self):
        """The 'es' in 'me llama es' is the error, not ser evidence."""
        s, _vis, _notes = process_turn(
            default_sheet(), "Me llama es Patrick", "¡Mucho gusto!")
        self.assertEqual(
            float((s["skills"].get("IP-07") or {}).get("confidence") or 0), 0.0)

    def test_correct_soy_still_earns_ser_credit(self):
        s, _vis, _notes = process_turn(
            default_sheet(), "Yo soy Patrick", "¡Mucho gusto!")
        self.assertGreater(
            float((s["skills"].get("IP-07") or {}).get("confidence") or 0), 0.0)

    def test_cap_stacked_bumps_cannot_reach_known(self):
        """Stacked success bumps: conf <= start+0.25; known re-gated below gate."""
        base = default_sheet()
        base["skills"]["IP-03"] = {
            "status": "emerging", "confidence": 0.5, "solid_uses": 1,
        }
        s, _vis, _notes = process_turn(base, "Me llamo Alex", "¡Mucho gusto!")
        entry = s["skills"]["IP-03"]
        self.assertLessEqual(entry["confidence"], 0.75)
        self.assertLessEqual(entry["solid_uses"], 2)
        self.assertNotEqual(entry["status"], "known")

    def test_apply_delta_receptive_and_sanitize(self):
        dirty = {
            "identity": {"preferred_name": "Pat"},
            "receptive": {"needs_english_scaffold": False},
            "evil_key": {"drop": True},
            "skills": {"IP-01": {"status": "emerging", "confidence": 0.4}},
        }
        clean = sanitize_tool_delta(dirty)
        self.assertNotIn("evil_key", clean)
        # Personal-data capture disabled: identity is not a trusted key.
        self.assertNotIn("identity", clean)
        s = apply_delta(default_sheet(), dirty)
        self.assertIsNone((s.get("identity") or {}).get("preferred_name"))
        self.assertFalse(s["receptive"]["needs_english_scaffold"])
        self.assertEqual(s["skills"]["IP-01"]["status"], "emerging")
        # per-turn cap: 0 → at most +0.25
        self.assertAlmostEqual(s["skills"]["IP-01"]["confidence"], 0.25)

    def test_confidence_cap_and_known_gate(self):
        """One tool turn cannot jump 0 → known 0.9; known needs uses + conf."""
        s = apply_delta(
            default_sheet(),
            {"skills": {"IP-02": {"status": "known", "confidence": 0.9}}},
        )
        self.assertLessEqual(s["skills"]["IP-02"]["confidence"], 0.25)
        self.assertNotEqual(s["skills"]["IP-02"]["status"], "known")
        # Climb over several solid updates
        for _ in range(4):
            s = apply_delta(
                s,
                {"skills": {"IP-02": {"status": "known", "confidence": 0.95}}},
            )
        self.assertEqual(s["skills"]["IP-02"]["status"], "known")
        self.assertGreaterEqual(s["skills"]["IP-02"]["confidence"], 0.8)

    def test_identity_stripped_never_preserved(self):
        # Personal-data capture disabled 2026-07-28: _preserve_identity is
        # now a STRIPPER — a pre-existing name is removed, never restored.
        base = default_sheet()
        base["identity"]["preferred_name"] = "Patrick"
        s = apply_delta(
            base,
            {
                "identity": {"preferred_name": "NewName", "engagement_notes": "x"},
                "skills": {"IP-04": {"confidence": 0.3, "status": "emerging"}},
            },
        )
        self.assertIsNone(s["identity"]["preferred_name"])
        self.assertEqual(s["identity"].get("engagement_notes") or "", "")

    def test_limited_time_not_boredom(self):
        s = apply_rule_updates(
            default_sheet(),
            "gracias. Yo solo tango un pequito tiemp. I only have a little time",
        )
        self.assertEqual(s["affect"]["energy"], "limited_time")
        self.assertNotEqual(s["affect"].get("boredom_risk"), "high")
        s = recompute_next_best(s)
        # Must NOT force boredom change_activity reason
        self.assertNotIn("boredom", (s["next_best"].get("reason") or "").lower())
        self.assertIn("limited time", (s["next_best"].get("reason") or "").lower())

    def test_session_energy_clears_on_new_session(self):
        """'Few minutes' from yesterday must not haunt today's open."""
        s = default_sheet()
        s["identity"]["preferred_name"] = "Patrick"
        s["affect"]["energy"] = "a_few_minutes"
        s["affect"]["last_meta"] = "I only have a few minutes today"
        s["next_best"] = {
            "can_do": "IP-05",
            "activity": "close_exchange_naturally",
            "reason": "limited time — keep it short | leave-taking",
            "avoid": "dragging_out_session_when_time_limited",
        }
        self.assertTrue(is_session_scoped_energy("a_few_minutes"))
        cleared = clear_session_scoped_affect(s)
        self.assertEqual(cleared["affect"]["energy"], "unknown")
        self.assertIsNone(cleared["affect"]["last_meta"])
        # Personal-data capture disabled: session open strips any residual name.
        self.assertIsNone(cleared["identity"]["preferred_name"])
        # limited-time reason should be gone after recompute
        self.assertNotIn(
            "limited time",
            (cleared.get("next_best") or {}).get("reason", "").lower(),
        )

    def test_coverage_auto_from_skills(self):
        s = apply_delta(
            default_sheet(),
            {
                "skills": {
                    "IP-08": {"status": "emerging", "confidence": 0.4},
                    "IP-02": {"status": "emerging", "confidence": 0.3},
                },
            },
        )
        touched = s["coverage"]["touched"]
        self.assertIn("roleplay_tasks", touched)
        self.assertIn("register_tu_usted", touched)
        never = s["coverage"]["never_touched"]
        self.assertNotIn("roleplay_tasks", never)

    def test_tool_delta_clears_false_boredom_for_time(self):
        s = apply_delta(
            default_sheet(),
            {
                "affect": {
                    "last_meta": "Has only a little time today",
                    "boredom_risk": "high",
                    "energy": "limited_time",
                },
                "next_best": {
                    "can_do": "IP-08",
                    "activity": "short_roleplay",
                    "reason": "learner signalled boredom/plan confusion — new task (TBLT)",
                },
            },
        )
        self.assertNotEqual(s["affect"]["boredom_risk"], "high")
        self.assertNotIn("boredom", (s["next_best"].get("reason") or "").lower())

    def test_tool_schema_shape(self):
        t = UPDATE_CHARACTER_SHEET_TOOL
        self.assertEqual(t["name"], "update_character_sheet")
        self.assertIn("input_schema", t)
        self.assertIn("skills", t["input_schema"]["properties"])
        # Personal-data capture disabled: no identity in schema or description.
        self.assertNotIn("identity", t["input_schema"]["properties"])
        self.assertNotIn("preferred_name", t["description"])
        self.assertIn("Do not record learner names", t["description"])

    def test_parse_sheet_json(self):
        raw = '```json\n{"version": 2, "identity": {"preferred_name": "Pat"}}\n```'
        d = parse_sheet_json(raw)
        self.assertEqual(d["identity"]["preferred_name"], "Pat")
        n = normalize_sheet(d)
        self.assertIn("IP-01", n["skills"])
        # Personal-data capture disabled: normalize strips identity data.
        self.assertIsNone(n["identity"]["preferred_name"])

    def test_greet_known_shifts_next_best(self):
        s = default_sheet()
        for _ in range(6):
            s = apply_rule_updates(s, "Hola! Buenos dias")
        s = recompute_next_best(s)
        # after strong greet (IP-01), prefer another can-do e.g. introduce
        self.assertNotEqual(s["next_best"].get("can_do"), "IP-01")
        self.assertIn(s["next_best"].get("can_do"), ("IP-03", "IP-04", "IP-05", "IP-06", "IP-07", "IP-08", None))

    def test_human_format(self):
        t = format_sheet_human(default_sheet())
        self.assertIn("Next best", t)
        self.assertIn("Can-dos", t)
        self.assertIn("IP-01", t)

    def test_me_llama_es_earns_ip03_but_stores_no_name(self):
        # Personal-data capture disabled (2026-07-28): the introduction
        # surface form still earns IP-03 ability credit, but no name is
        # ever written to the sheet.
        s = apply_rule_updates(default_sheet(), "estoy bien. Me llama es Patrick")
        self.assertIsNone((s.get("identity") or {}).get("preferred_name"))
        self.assertGreater(s["skills"]["IP-03"]["confidence"], 0.1)

    def test_scaffold_stays_on_with_english_meta(self):
        from tutor.character_sheet import update_scaffold_flag
        s = default_sheet()
        s = apply_rule_updates(s, "estoy bien")
        s = update_scaffold_flag(s, "what does ves mean?")
        self.assertTrue(s["receptive"]["needs_english_scaffold"])

    def test_legacy_sheet_migrates(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "old.json"
            old = {
                "version": 1,
                "skills": {
                    "greet_informal": {"status": "known", "confidence": 0.9},
                    "introduce_self": {"status": "unknown", "confidence": 0.0},
                },
            }
            p.write_text(json.dumps(old))
            s = load_sheet(p)
            self.assertGreaterEqual(s["skills"]["IP-01"]["confidence"], 0.9)
            self.assertIn("IP-03", s["skills"])


if __name__ == "__main__":
    unittest.main()
