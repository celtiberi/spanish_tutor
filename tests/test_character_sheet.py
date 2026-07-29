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
        """One tool turn cannot jump 0 → known 0.9; known needs OBSERVED uses.

        CHAR-BUG-008 fix (2026-07-29): the old version of this test pinned
        a 4-call claim climb to known (each merge minted a solid use via
        the rose/promoted heuristic). Uses now come only from code
        observation, so claim-only climbing stalls at emerging forever and
        promotion lands only once the sheet's own recorded uses reach the
        gate.
        """
        s = apply_delta(
            default_sheet(),
            {"skills": {"IP-02": {"status": "known", "confidence": 0.9}}},
        )
        self.assertLessEqual(s["skills"]["IP-02"]["confidence"], 0.25)
        self.assertNotEqual(s["skills"]["IP-02"]["status"], "known")
        # Claim-only climbing: conf ceilings at 0.75, status stays
        # emerging, zero uses minted — the gate is uncrossable by claim.
        for _ in range(4):
            s = apply_delta(
                s,
                {"skills": {"IP-02": {"status": "known", "confidence": 0.95}}},
            )
        self.assertEqual(s["skills"]["IP-02"]["status"], "emerging")
        self.assertEqual(s["skills"]["IP-02"]["solid_uses"], 0)
        self.assertLessEqual(s["skills"]["IP-02"]["confidence"], 0.75)
        # Once code observation supplies the uses, the same claim promotes.
        s["skills"]["IP-02"]["solid_uses"] = 2  # code-observed (_bump_status)
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


class TestAbilityStateMachine(unittest.TestCase):
    """Phase 1.5 batch 2 (machine B): explicit ability-axis machine.

    Write-path formalization only — field outcomes are unchanged (goldens
    pin them); the machine validates band edges per via and rejects
    cross-axis (schedule-field) writes, the mirror of machine A's _write
    allowlist. The known gate stays in the writers, never the edge set
    (adjudication: "KNOWN-gate evidence stays a gate, not an enum").
    """

    def test_ability_band_classification(self):
        from tutor.character_sheet import STATUSES, ability_band

        self.assertEqual(ability_band(None), "unknown")
        self.assertEqual(ability_band({}), "unknown")
        self.assertEqual(ability_band({"confidence": 0.9}), "unknown")
        self.assertEqual(ability_band({"status": "Known"}), "unknown")  # strict
        self.assertEqual(ability_band({"status": "durable"}), "unknown")
        for st in STATUSES:
            self.assertEqual(ability_band({"status": st}), st)

    def test_band_vocabulary_matches_reality_not_sketch(self):
        """Sketch said unknown/fragile/emerging/known; code has 5 statuses."""
        from tutor.character_sheet import (
            ABILITY_BANDS,
            ABILITY_TRANSITIONS,
            STATUSES,
        )

        self.assertEqual(ABILITY_BANDS, STATUSES)
        self.assertEqual(set(ABILITY_TRANSITIONS), set(STATUSES))
        self.assertIn("fragile", ABILITY_BANDS)   # real, not sketch-only
        self.assertIn("blocked", ABILITY_BANDS)   # sketch omitted it

    def test_union_graph_matches_via_edges(self):
        from tutor.character_sheet import (
            ABILITY_TRANSITIONS,
            _ABILITY_VIA_EDGES,
        )

        derived = {}
        for edges in _ABILITY_VIA_EDGES.values():
            for f, t in edges:
                derived.setdefault(f, set()).add(t)
        self.assertEqual(derived, ABILITY_TRANSITIONS)

    def test_bump_cannot_mint_blocked_and_escapes_it(self):
        from tutor.character_sheet import _ABILITY_VIA_EDGES, _bump_status

        self.assertFalse(
            any(t == "blocked" for _f, t in _ABILITY_VIA_EDGES["bump"])
        )
        e = _bump_status({"status": "blocked", "confidence": 0.3}, success=True)
        self.assertEqual(e["status"], "emerging")
        e = _bump_status({"status": "blocked", "confidence": 0.3}, success=False)
        self.assertEqual(e["status"], "unknown")

    def test_down_edges_are_real(self):
        """Demotion exists in code: known → fragile/unknown (bump fail),
        known → emerging (_cap_turn_confidence re-gate)."""
        from tutor.character_sheet import _bump_status, _cap_turn_confidence

        e = _bump_status(
            {"status": "known", "confidence": 0.82, "solid_uses": 3},
            success=False,
        )
        self.assertEqual(e["status"], "fragile")
        e = _bump_status(
            {"status": "known", "confidence": 0.3, "solid_uses": 3},
            success=False,
        )
        self.assertEqual(e["status"], "unknown")
        # Cap re-gate: known with uses below gate demotes to emerging.
        final = {"skills": {"IP-01": {
            "status": "known", "confidence": 0.9, "solid_uses": 0,
        }}}
        start = {"skills": {"IP-01": {
            "status": "known", "confidence": 0.9, "solid_uses": 0,
        }}}
        out = _cap_turn_confidence(start, start, final)
        self.assertEqual(out["skills"]["IP-01"]["status"], "emerging")

    def test_known_self_loop_survives_failure_at_gate(self):
        from tutor.character_sheet import _bump_status

        e = _bump_status(
            {"status": "known", "confidence": 1.0, "solid_uses": 3},
            success=False,
        )
        self.assertEqual(e["status"], "known")  # conf still >= gate

    def test_unknown_success_skips_fragile(self):
        """The bands below known are evidence-direction siblings, not
        ordered rungs: first success goes straight to emerging."""
        from tutor.character_sheet import _bump_status

        e = _bump_status({"status": "unknown", "confidence": 0.0}, success=True)
        self.assertEqual(e["status"], "emerging")

    def test_cap_and_normalize_vias_are_narrow(self):
        from tutor.character_sheet import _ABILITY_VIA_EDGES, STATUSES

        self.assertEqual(
            _ABILITY_VIA_EDGES["cap"],
            frozenset({(s, s) for s in STATUSES} | {("known", "emerging")}),
        )
        self.assertEqual(
            _ABILITY_VIA_EDGES["normalize"],
            frozenset((s, s) for s in STATUSES),
        )

    def test_transition_rejects_unknown_via_and_illegal_edge(self):
        from tutor.character_sheet import (
            IllegalAbilityTransition,
            ability_transition,
        )

        with self.assertRaises(ValueError):
            ability_transition({}, {"status": "emerging"}, via="teleport")
        # unknown → known is not a "cap" edge (cap only clips/demotes)
        with self.assertRaises(IllegalAbilityTransition) as ctx:
            ability_transition(
                {"status": "unknown"}, {"status": "known"},
                via="cap", evidence={"probe": "x"},
            )
        self.assertIn("probe", str(ctx.exception))  # evidence in message
        # emerging → known is not a "normalize" edge (coercion only)
        with self.assertRaises(IllegalAbilityTransition):
            ability_transition(
                {"status": "emerging"}, {"status": "known"}, via="normalize",
            )

    def test_ability_writer_cannot_move_schedule_fields(self):
        """BUILD 4 mirror: machine A already restores ability fields; machine
        B must reject schedule-field moves (changed, added, or removed)."""
        from tutor.character_sheet import ability_transition

        laddered = {
            "status": "emerging", "confidence": 0.4,
            "next_due": "2027-01-01", "interval_days": 3,
            "introduced_at": "2026-07-01",
        }
        for staged in (
            {**laddered, "next_due": "2027-06-01"},          # changed
            {**laddered, "first_seen": "2026-07-01"},        # added
            {k: v for k, v in laddered.items() if k != "next_due"},  # removed
        ):
            with self.assertRaises(ValueError) as ctx:
                ability_transition(laddered, staged, via="bump")
            self.assertIn("honesty law", str(ctx.exception))
        # Pass-through of unchanged schedule fields stays legal.
        out = ability_transition(
            laddered, {**laddered, "confidence": 0.5}, via="bump",
        )
        self.assertEqual(out["next_due"], "2027-01-01")

    def test_cross_axis_symmetry_both_directions(self):
        """One place that shows BOTH guards: schedule writers cannot touch
        ability fields (machine A) and ability writers cannot touch
        schedule fields (machine B)."""
        from tutor.character_sheet import ability_transition
        from tutor.retrieval_scheduler import _write

        for illegal in (
            {"confidence": 0.9}, {"status": "known"}, {"solid_uses": 3},
        ):
            with self.assertRaises(ValueError):
                _write({"status": "unknown", "confidence": 0.0}, illegal)
        with self.assertRaises(ValueError):
            ability_transition(
                {"status": "unknown"},
                {"status": "emerging", "next_due": "2027-01-01"},
                via="bump",
            )

    def test_ability_fields_match_scheduler_protected(self):
        """Cross-module sync pin (test, not import — the scheduler stays
        stdlib-only): the two axes name the same field sets."""
        from tutor import retrieval_scheduler as rs
        from tutor.character_sheet import (
            ABILITY_FIELDS,
            SCHEDULE_ENTRY_FIELDS,
        )

        self.assertEqual(ABILITY_FIELDS, rs._PROTECTED_FIELDS)
        self.assertEqual(set(SCHEDULE_ENTRY_FIELDS), set(rs.SCHEDULE_FIELDS))

    def test_writers_preserve_schedule_fields_through_process_turn(self):
        """End-to-end cross-axis guard: a full tool-delta turn on a laddered
        sheet leaves every schedule field byte-identical."""
        base = default_sheet()
        base["lexicon"]["pan"] = {
            "status": "emerging", "confidence": 0.4, "solid_uses": 1,
            "introduced_at": "2026-07-01", "first_seen": "2026-07-01",
            "scaffold": "gloss", "next_due": "2026-07-05",
            "interval_days": 3, "successive_successes": 2,
        }
        sched_before = {
            k: base["lexicon"]["pan"][k]
            for k in (
                "introduced_at", "first_seen", "scaffold", "next_due",
                "interval_days", "successive_successes",
            )
        }
        s, _vis, _notes = process_turn(
            base, "me gusta el pan", "¡Qué rico!",
            tool_delta={"lexicon": {"pan": {
                "status": "emerging", "confidence": 0.6,
                "next_due": "2020-01-01",  # cross-axis attempt: stripped
            }}},
        )
        after = s["lexicon"]["pan"]
        self.assertEqual(
            {k: after.get(k) for k in sched_before}, sched_before
        )

    def test_char_bug_008_009_resolved_tool_cannot_jump_bands(self):
        """CHAR-BUG-008/009 RESOLVED (2026-07-29): the model's sheet tool
        lost the power to inflate the diagnosis (PEDAGOGY §3.2/P7 — the
        sheet is the targeting instrument; §4.5 — capability removal).

        008: solid_uses claims are no longer evidence — the merge starts
        from the sheet's own recorded (observed) count, a claim may LOWER
        it but never raise it, and no merge heuristic mints uses. The
        known gate (conf ≥ 0.80 + 2 solid uses) is uncrossable by claim
        alone. 009: apply_delta's lexicon branches (dict + bare-string)
        route through _clamp_skill_entry (via="delta_lexicon") — no branch
        mints band/confidence unclamped; a new-word known-claim at conf
        1.0 lands emerging at the +0.25 first-appearance ceiling.
        Inverted from the Phase 1.5 batch 2 characterization pin; the
        registry entries flipped RESOLVED in the same change (Phase 0 law).
        """
        # Unchanged guard: unknown at conf 0 cannot reach known.
        s, _v, _n = process_turn(
            default_sheet(), "hola", "¡Hola!",
            tool_delta={"skills": {"IP-02": {
                "status": "known", "confidence": 0.9, "solid_uses": 5,
            }}},
        )
        self.assertEqual(s["skills"]["IP-02"]["status"], "emerging")
        self.assertAlmostEqual(s["skills"]["IP-02"]["confidence"], 0.25)
        self.assertEqual(s["skills"]["IP-02"]["solid_uses"], 0)
        # 008 INVERTED: the old one-call crossing claim now lands clamped —
        # emerging at the 0.75 over-claim ceiling, uses still 0.
        base = default_sheet()
        base["skills"]["IP-02"] = {
            **base["skills"]["IP-02"],
            "status": "emerging", "confidence": 0.6, "solid_uses": 0,
        }
        s, _v, _n = process_turn(
            base, "hola", "¡Hola!",
            tool_delta={"skills": {"IP-02": {
                "status": "known", "confidence": 0.85, "solid_uses": 2,
            }}},
        )
        self.assertEqual(s["skills"]["IP-02"]["status"], "emerging")
        self.assertAlmostEqual(s["skills"]["IP-02"]["confidence"], 0.75)
        self.assertEqual(s["skills"]["IP-02"]["solid_uses"], 0)
        # 008 lawful landing: with OBSERVED uses at the gate the same claim
        # promotes — the diagnosis follows evidence, not claims.
        base = default_sheet()
        base["skills"]["IP-02"] = {
            **base["skills"]["IP-02"],
            "status": "emerging", "confidence": 0.6, "solid_uses": 2,
        }
        s, _v, _n = process_turn(
            base, "hola", "¡Hola!",
            tool_delta={"skills": {"IP-02": {
                "status": "known", "confidence": 0.85,
            }}},
        )
        self.assertEqual(s["skills"]["IP-02"]["status"], "known")
        # A uses claim may LOWER the observed count (honest demotion).
        base = default_sheet()
        base["skills"]["IP-02"] = {
            **base["skills"]["IP-02"],
            "status": "emerging", "confidence": 0.6, "solid_uses": 3,
        }
        s, _v, _n = process_turn(
            base, "hola", "¡Hola!",
            tool_delta={"skills": {"IP-02": {"solid_uses": 1}}},
        )
        self.assertEqual(s["skills"]["IP-02"]["solid_uses"], 1)
        # 009 INVERTED: lexicon absent + claim {known, 1.0, uses 2} lands
        # emerging at the first-appearance ceiling, zero uses.
        s, _v, _n = process_turn(
            default_sheet(), "hola", "¡Hola!",
            tool_delta={"lexicon": {"perro": {
                "status": "known", "confidence": 1.0, "solid_uses": 2,
            }}},
        )
        self.assertEqual(s["lexicon"]["perro"]["status"], "emerging")
        self.assertAlmostEqual(s["lexicon"]["perro"]["confidence"], 0.25)
        self.assertEqual(s["lexicon"]["perro"]["solid_uses"], 0)
        # Without the uses claim the landing is the same — pre-fix, conf
        # 1.0 survived the cap re-gate demotion; now the merge clamps it.
        s, _v, _n = process_turn(
            default_sheet(), "hola", "¡Hola!",
            tool_delta={"lexicon": {"perro": {
                "status": "known", "confidence": 1.0,
            }}},
        )
        self.assertEqual(s["lexicon"]["perro"]["status"], "emerging")
        self.assertAlmostEqual(s["lexicon"]["perro"]["confidence"], 0.25)

    def test_tool_vias_tightened_char_bug_008_009(self):
        """The tool_merge/delta_lexicon edge tables are no longer
        edge-complete: unknown → known and blocked → known are gone. The
        rule per case: routine inflation is CLAMPED in the writer (the
        _cap_turn_confidence philosophy — the claim lands, demoted);
        the machine RAISES only on the two impossible promotions, which
        the fixed writer can no longer stage (production-unreachable
        backstop, mirror of the batch-1 double-introduce ruling)."""
        from tutor.character_sheet import (
            _ABILITY_VIA_EDGES,
            STATUSES,
            IllegalAbilityTransition,
            ability_transition,
        )

        expected = frozenset(
            {(f, t) for f in STATUSES
             for t in ("unknown", "emerging", "fragile", "blocked")}
            | {(f, "known") for f in ("emerging", "fragile", "known")}
        )
        self.assertEqual(_ABILITY_VIA_EDGES["tool_merge"], expected)
        self.assertEqual(_ABILITY_VIA_EDGES["delta_lexicon"], expected)
        for via in ("tool_merge", "delta_lexicon"):
            for frm in ({}, {"status": "blocked"}):
                with self.assertRaises(IllegalAbilityTransition):
                    ability_transition(
                        frm, {"status": "known", "confidence": 1.0}, via=via,
                    )

    def test_clamp_keeps_legacy_known_without_uses(self):
        """Why the known gate stays in writers, not the machine: legacy /
        seeded sheets legally hold known with solid_uses 0, and the tool
        merge preserves that claim (prev-known + conf >= gate)."""
        from tutor.character_sheet import _clamp_skill_entry

        merged = _clamp_skill_entry(
            {"status": "known", "confidence": 0.9},
            {"status": "known", "confidence": 0.9},
        )
        self.assertEqual(merged["status"], "known")
        self.assertEqual(merged["solid_uses"], 0)


if __name__ == "__main__":
    unittest.main()
