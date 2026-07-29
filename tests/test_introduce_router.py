"""r7 S2 IntroducePlan router: budget, cluster ban, rule routing, wiring.

Runs against the REAL pack association table (course_packs/spanish_a1) so
rule routing is tested on shipped data, not fixtures. Laws under test
(docs/pedagogy-research-r7-association-intro.md §5 + build plan Phase 3):
R-G budget → None; R-F cluster ban lists only UNintroduced same-theme keys;
R-A never fires for a listed false friend; introduction never bumps
confidence; the INTRODUCE block only rides new_input + flavorable turns.
"""

import unittest
from pathlib import Path

from tutor.association_table import load_association_table
from tutor.character_sheet import default_sheet
from tutor.conv_session import introduce_block, mark_introduced_if_visible
from tutor.introduce_router import (
    PRIORITY_THEMES,
    candidate_keys,
    plan_introduction,
    plan_instructions,
)
from tutor.retrieval_scheduler import mark_introduced

ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "course_packs" / "spanish_a1"


def _fresh_snap() -> dict:
    return {"introduced_this_session": [], "intro_budget_remaining": 2}


def _sheet_with_introduced(*keys: str) -> dict:
    s = default_sheet()
    for k in keys:
        s = mark_introduced(s, k, "lexicon", "gloss")
    return s


class TableCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table = load_association_table(PACK_DIR)


class TestBudget(TableCase):
    def test_budget_exhausted_returns_none(self):
        snap = {
            "introduced_this_session": ["hola", "adiós"],
            "intro_budget_remaining": 0,
        }
        self.assertIsNone(plan_introduction(default_sheet(), self.table, snap))

    def test_two_introduced_without_remaining_field_returns_none(self):
        snap = {"introduced_this_session": ["hola", "adiós"]}
        self.assertIsNone(plan_introduction(default_sheet(), self.table, snap))

    def test_budget_left_plans(self):
        snap = {"introduced_this_session": ["hola"], "intro_budget_remaining": 1}
        plan = plan_introduction(default_sheet(), self.table, snap)
        self.assertIsNotNone(plan)


class TestClusterBan(TableCase):
    def test_hasta_luego_forbids_unintroduced_farewells(self):
        plan = plan_introduction(
            default_sheet(), self.table, _fresh_snap(), key="hasta luego"
        )
        self.assertEqual(plan.key, "hasta luego")
        self.assertIn("adiós", plan.forbid_cluster_with)
        self.assertIn("hasta mañana", plan.forbid_cluster_with)
        self.assertNotIn("hasta luego", plan.forbid_cluster_with)

    def test_introduced_same_theme_keys_not_listed(self):
        sheet = _sheet_with_introduced("adiós")
        plan = plan_introduction(
            sheet, self.table, _fresh_snap(), key="hasta luego"
        )
        self.assertNotIn("adiós", plan.forbid_cluster_with)
        self.assertIn("hasta mañana", plan.forbid_cluster_with)


class TestRuleRouting(TableCase):
    """Real-table routing: cognate → image → keyword → gloss (R-C deferred)."""

    def _plan(self, key: str, sheet: dict | None = None):
        return plan_introduction(
            sheet if sheet is not None else default_sheet(),
            self.table,
            _fresh_snap(),
            key=key,
        )

    def test_cognate_entry_routes_r_a(self):
        plan = self._plan("igualmente")
        self.assertEqual((plan.rule_id, plan.scaffold_type), ("R-A", "cognate"))
        self.assertEqual(
            plan.scaffold_payload["anchor"],
            self.table["igualmente"]["cognate_en"],
        )
        self.assertEqual(plan.scaffold_payload["note"], "false-friend-free")

    def test_adios_routes_r_d_not_loanword_cognate(self):
        # Grok AMEND 3a (2026-07-28): the r7 §5 worked example rules adiós a
        # conventional farewell → R-D micro-gloss; "adios (borrowed in
        # English)" was loanword circularity, not a true cognate anchor.
        plan = self._plan("adiós")
        self.assertEqual((plan.rule_id, plan.scaffold_type), ("R-D", "gloss"))
        self.assertEqual(
            plan.scaffold_payload["format"], "**adiós** (goodbye)"
        )
        self.assertIn("hasta luego", plan.forbid_cluster_with)
        self.assertIn("hasta mañana", plan.forbid_cluster_with)

    def test_function_mwu_por_favor_routes_cognate(self):
        plan = self._plan("por favor")
        self.assertEqual((plan.rule_id, plan.scaffold_type), ("R-A", "cognate"))

    def test_false_friend_never_gets_cognate(self):
        in_pack_traps = [
            k
            for k, v in self.table.items()
            if v.get("false_friend") and v.get("in_pack") is not False
        ]
        self.assertTrue(in_pack_traps)  # table must ship in-pack traps
        for key in in_pack_traps:
            plan = self._plan(key)
            self.assertIsNotNone(plan, key)
            self.assertNotEqual(plan.scaffold_type, "cognate", key)
            self.assertNotEqual(plan.rule_id, "R-A", key)

    def test_false_friend_imageable_falls_to_image(self):
        # vaso: listed trap + imageable → R-B, never R-A
        plan = self._plan("vaso")
        self.assertEqual((plan.rule_id, plan.scaffold_type), ("R-B", "image"))

    def test_imageable_non_cognate_routes_image_over_keyword(self):
        # casa has a curated keyword too — image outranks keyword (R-B > R-E)
        plan = self._plan("casa")
        self.assertEqual((plan.rule_id, plan.scaffold_type), ("R-B", "image"))
        self.assertEqual(plan.scaffold_payload["image_concept"], "casa")
        # r5 contiguity: caption is the Spanish form
        self.assertEqual(plan.scaffold_payload["caption"], "casa")

    def test_keyword_branch(self):
        plan = self._plan("hasta luego")
        self.assertEqual((plan.rule_id, plan.scaffold_type), ("R-E", "keyword"))
        self.assertEqual(
            plan.scaffold_payload["keyword"],
            self.table["hasta luego"]["keyword_en"],
        )

    def test_gloss_fallback(self):
        plan = self._plan("me llamo")
        self.assertEqual((plan.rule_id, plan.scaffold_type), ("R-D", "gloss"))

    def test_every_gloss_plan_format_contains_key_and_gloss(self):
        for key in self.table:
            plan = self._plan(key)
            if plan is None or plan.scaffold_type != "gloss":
                continue
            fmt = plan.scaffold_payload["format"]
            self.assertIn(key, fmt, key)
            self.assertIn(self.table[key]["gloss_en"], fmt, key)


class TestPlanInstructions(TableCase):
    def test_contains_forbid_list_and_closing_law(self):
        plan = plan_introduction(
            default_sheet(), self.table, _fresh_snap(), key="hasta luego"
        )
        text = plan_instructions(plan)
        self.assertIn("adiós", text)
        self.assertIn("hasta mañana", text)
        self.assertIn("Do NOT also introduce", text)
        self.assertTrue(text.endswith("Introduce NOTHING else new this turn."))

    def test_scaffold_specific_wording(self):
        cog = plan_introduction(
            default_sheet(), self.table, _fresh_snap(), key="igualmente"
        )
        self.assertIn("cognate", plan_instructions(cog))
        img = plan_introduction(
            default_sheet(), self.table, _fresh_snap(), key="casa"
        )
        img_text = plan_instructions(img)
        self.assertIn("image", img_text)
        self.assertIn("No L1 unless the learner fails", img_text)
        glo = plan_introduction(
            default_sheet(), self.table, _fresh_snap(), key="me llamo"
        )
        glo_text = plan_instructions(glo)
        self.assertIn("**me llamo** (my name is)", glo_text)
        self.assertIn("exactly once", glo_text)
        for text in (plan_instructions(cog), img_text, glo_text):
            self.assertTrue(
                text.endswith("Introduce NOTHING else new this turn.")
            )


class TestCandidateKeys(TableCase):
    def test_excludes_confident_lexicon_entries(self):
        sheet = default_sheet()
        sheet["lexicon"]["hola"] = {"status": "emerging", "confidence": 0.6}
        self.assertNotIn("hola", candidate_keys(sheet, self.table))

    def test_low_confidence_still_candidate(self):
        sheet = default_sheet()
        sheet["lexicon"]["hola"] = {"status": "emerging", "confidence": 0.3}
        self.assertIn("hola", candidate_keys(sheet, self.table))

    def test_excludes_introduced_keys(self):
        sheet = _sheet_with_introduced("adiós")
        self.assertNotIn("adiós", candidate_keys(sheet, self.table))

    def test_excludes_out_of_pack_entries(self):
        # sopa is a false-friend reference entry with in_pack false
        self.assertNotIn("sopa", candidate_keys(default_sheet(), self.table))

    def test_priority_themes_before_rest_without_next_best(self):
        sheet = default_sheet()
        sheet["next_best"] = {}
        cands = candidate_keys(sheet, self.table)
        self.assertTrue(cands)
        self.assertIn(self.table[cands[0]]["theme"], PRIORITY_THEMES)
        self.assertLess(cands.index("hola"), cands.index("amigo"))

    def test_next_best_related_first(self):
        sheet = default_sheet()
        sheet["next_best"] = {"statement": "practice hasta luego next"}
        cands = candidate_keys(sheet, self.table)
        self.assertLess(cands.index("hasta luego"), cands.index("hola"))


class TestSessionExclusion(TableCase):
    """Audit (a1) 2026-07-28: covered_concepts ∪ images_shown are session
    exposure — the router must not plan a second "first introduce" of them,
    EVEN on an explicitly forced key (adjudicated: session-local honesty
    beats caller convenience)."""

    def _snap(self, **kw):
        snap = _fresh_snap()
        snap.update(kw)
        return snap

    def test_imaged_concept_not_in_candidates(self):
        snap = self._snap(images_shown=["casa"])
        self.assertIn("casa", candidate_keys(default_sheet(), self.table))
        self.assertNotIn(
            "casa",
            candidate_keys(default_sheet(), self.table, session_snapshot=snap),
        )

    def test_covered_concept_not_in_candidates(self):
        snap = self._snap(covered_concepts=["casa"])
        self.assertNotIn(
            "casa",
            candidate_keys(default_sheet(), self.table, session_snapshot=snap),
        )

    def test_forced_key_still_excluded(self):
        snap = self._snap(images_shown=["casa"], covered_concepts=["casa"])
        self.assertIsNone(
            plan_introduction(default_sheet(), self.table, snap, key="casa")
        )

    def test_unrelated_forced_key_still_plans(self):
        snap = self._snap(images_shown=["casa"])
        plan = plan_introduction(
            default_sheet(), self.table, snap, key="hasta luego"
        )
        self.assertIsNotNone(plan)
        self.assertEqual(plan.key, "hasta luego")

    def test_real_session_snapshot_fields_exclude(self):
        # conv_session passes pedagogy_memory.snapshot() — the shipped field
        # names (sorted lists) must exclude through the same wiring.
        from tutor.session_memory import SessionMemory

        mem = SessionMemory()
        mem.note_image("casa")
        mem.note_concept_covered("ciudad")
        snap = mem.snapshot()
        cands = candidate_keys(
            default_sheet(), self.table, session_snapshot=snap
        )
        self.assertNotIn("casa", cands)
        self.assertNotIn("ciudad", cands)
        self.assertIsNone(
            plan_introduction(default_sheet(), self.table, snap, key="casa")
        )


class TestLapsedIntroFirstSeen(TableCase):
    """Audit (a4) 2026-07-28 — Grok's encantado thrash proof as regression:
    R-A plan + gloss-only reply → introduce_lapsed + scaffold_saved records
    the planned key + first_seen sticks → next-turn bare use is CLEAN."""

    def test_encantado_lapse_writes_first_seen_next_bare_clean(self):
        from tutor.conv_session import introduce_scaffold_evidence
        from tutor.output_gate import (
            check_output_gate,
            scan_unscaffolded_new_items,
        )
        from tutor.retrieval_scheduler import (
            has_first_seen,
            is_introduced,
            mark_first_seen,
        )

        sheet = default_sheet()
        plan = plan_introduction(
            sheet, self.table, _fresh_snap(), key="encantado"
        )
        self.assertEqual(
            (plan.rule_id, plan.scaffold_type), ("R-A", "cognate")
        )
        reply = "**encantado** (a short gloss)"
        # Wrong-scaffold exposure: cognate anchor absent, gloss present.
        self.assertFalse(introduce_scaffold_evidence(plan, reply))
        updated, note = mark_introduced_if_visible(sheet, plan, reply)
        self.assertEqual(note, "introduce_lapsed:encantado:no_scaffold")
        self.assertIs(updated, sheet)  # budget unconsumed, no ledger write
        # Gate scan WITH the planned key: no bare fault; scaffold recorded.
        bare, _extras, _reglossed, saved = scan_unscaffolded_new_items(
            {"model": reply, "try": "¿Puedes decirlo?", "structured": True},
            f"{reply} ¿Puedes decirlo?",
            table=self.table,
            sheet=sheet,
            introduce_key="encantado",
        )
        self.assertEqual(bare, [])
        self.assertEqual(saved.get("encantado"), "gloss")
        # conv_session's post-turn loop (intro_plan skip DROPPED): the
        # lapsed-but-glossed exposure sticks as first_seen.
        for fs_key, fs_kind in saved.items():
            if is_introduced(sheet, fs_key, "lexicon"):
                continue
            if has_first_seen(sheet, fs_key, "lexicon"):
                continue
            sheet = mark_first_seen(sheet, fs_key, "lexicon", fs_kind)
        self.assertTrue(has_first_seen(sheet, "encantado", "lexicon"))
        self.assertFalse(is_introduced(sheet, "encantado", "lexicon"))
        # Next turn: bare re-use is a re-encounter, not a fresh CRITICAL.
        g = check_output_gate(
            {"model": "Encantado.", "try": "¿Puedes decirlo?",
             "structured": True},
            "Encantado. ¿Puedes decirlo?",
            is_open=False,
            mode="conversation",
            association_table=self.table,
            sheet=sheet,
        )
        self.assertNotIn("gate:unscaffolded_new_item", g.faults)
        self.assertNotIn("gate:unscaffolded_flood", g.faults)

    def test_first_seen_loop_no_longer_skips_plan_key(self):
        # The conv_session first_seen loop must not skip intro_plan.key
        # (successful introduces already hit is_introduced upstream).
        import inspect

        import tutor.conv_session as conv_session

        self.assertNotIn(
            "fs_key == intro_plan.key", inspect.getsource(conv_session)
        )


class TestIntroduceBlockWiring(TableCase):
    """conv_session.introduce_block — the smallest wiring function."""

    def test_block_on_new_input_default_conversation(self):
        block, plan = introduce_block(
            default_sheet(),
            self.table,
            _fresh_snap(),
            mode="conversation",
            reason="default_conversation",
            activity_hint="new_input",
        )
        self.assertIn("INTRODUCE", block)
        self.assertIsNotNone(plan)
        self.assertIn("Introduce NOTHING else new this turn.", block)

    def test_block_on_known_open(self):
        block, plan = introduce_block(
            default_sheet(),
            self.table,
            _fresh_snap(),
            mode="conversation",
            reason="known_open_from_sheet",
            activity_hint="new_input",
        )
        self.assertIn("INTRODUCE", block)
        self.assertIsNotNone(plan)

    def test_guard_repair_recast_turns_produce_nothing(self):
        for mode, reason in (
            ("conversation", "learner_topic_request"),
            ("conversation", "learner_help_request"),
            ("conversation", "grammar_question_inline"),
            ("conversation", "boredom_new_topic"),
            ("comprehension_repair", "meta_comprehension_stay_on_topic"),
            ("cf_recast", "single_error:weather_hace"),
            ("form_focus", "error_streak:weather_hace"),
            ("placement", "blank_open_placement"),
        ):
            block, plan = introduce_block(
                default_sheet(),
                self.table,
                _fresh_snap(),
                mode=mode,
                reason=reason,
                activity_hint="new_input",
            )
            self.assertEqual(block, "", f"{mode}/{reason}")
            self.assertIsNone(plan, f"{mode}/{reason}")

    def test_non_new_input_phases_produce_nothing(self):
        for activity in ("retrieval", "task", "free", None):
            block, plan = introduce_block(
                default_sheet(),
                self.table,
                _fresh_snap(),
                mode="conversation",
                reason="default_conversation",
                activity_hint=activity,
            )
            self.assertEqual(block, "", str(activity))
            self.assertIsNone(plan)

    def test_missing_table_disables_router(self):
        block, plan = introduce_block(
            default_sheet(),
            None,
            _fresh_snap(),
            mode="conversation",
            reason="default_conversation",
            activity_hint="new_input",
        )
        self.assertEqual(block, "")
        self.assertIsNone(plan)

    def test_exhausted_budget_produces_nothing(self):
        block, plan = introduce_block(
            default_sheet(),
            self.table,
            {"introduced_this_session": ["a", "b"], "intro_budget_remaining": 0},
            mode="conversation",
            reason="default_conversation",
            activity_hint="new_input",
        )
        self.assertEqual(block, "")
        self.assertIsNone(plan)


class TestMarkOnVisible(TableCase):
    """Introduce-move EVIDENCE rule (2026-07-28 false-planted incident):
    key presence alone is natural use, never an introduction. Marking
    requires the plan's scaffold visibly in the reply (gloss parenthetical /
    anchor text / attached image)."""

    def _plan(self, key: str):
        return plan_introduction(
            default_sheet(), self.table, _fresh_snap(), key=key
        )

    def test_gloss_scaffold_marks_introduced_confidence_untouched(self):
        sheet = default_sheet()
        sheet["lexicon"]["me llamo"] = {"status": "emerging", "confidence": 0.3}
        plan = self._plan("me llamo")
        self.assertEqual(plan.rule_id, "R-D")  # gloss scaffold
        updated, note = mark_introduced_if_visible(
            sheet, plan, "**Me llamo** (my name is) Marisol. ¿Y tú?"
        )
        self.assertEqual(note, "introduced:me llamo")
        entry = updated["lexicon"]["me llamo"]
        self.assertTrue(entry.get("introduced_at"))
        self.assertEqual(entry.get("scaffold"), plan.scaffold_type)
        self.assertTrue(entry.get("next_due"))  # R-H enqueue
        # Honesty law: ability fields untouched by the ledger write
        self.assertEqual(entry.get("confidence"), 0.3)
        self.assertEqual(entry.get("status"), "emerging")

    def test_buenas_tardes_natural_greeting_lapses(self):
        """The user's live case verbatim (2026-07-28): plan for «buenas
        tardes», tutor replies with it as a natural greeting — no keyword
        anchor, no gloss. NO mark, NO milestone basis, budget unconsumed."""
        sheet = default_sheet()
        plan = self._plan("buenas tardes")
        self.assertEqual(plan.rule_id, "R-E")  # keyword scaffold planned
        updated, note = mark_introduced_if_visible(
            sheet, plan, "¡Buenas tardes! ¿Cómo estás hoy?"
        )
        self.assertEqual(note, "introduce_lapsed:buenas tardes:no_scaffold")
        self.assertIs(updated, sheet)  # untouched — budget not consumed
        self.assertNotIn("buenas tardes", updated.get("lexicon") or {})

    def test_keyword_anchor_present_marks(self):
        plan = self._plan("hola")
        self.assertEqual(plan.scaffold_type, "keyword")
        updated, note = mark_introduced_if_visible(
            default_sheet(), plan,
            "¡**Hola**! Suena como 'hello' en inglés. ¿Cómo estás?",
        )
        self.assertEqual(note, "introduced:hola")
        self.assertTrue(updated["lexicon"]["hola"].get("introduced_at"))

    def test_keyword_anchor_missing_lapses(self):
        sheet = default_sheet()
        plan = self._plan("hola")
        updated, note = mark_introduced_if_visible(
            sheet, plan, "¡Hola! ¿Cómo estás?"
        )
        self.assertEqual(note, "introduce_lapsed:hola:no_scaffold")
        self.assertIs(updated, sheet)

    def test_cognate_anchor_evidence(self):
        plan = self._plan("gracias")
        self.assertEqual(plan.rule_id, "R-A")
        _u, note = mark_introduced_if_visible(
            default_sheet(), plan,
            "**Gracias** — como 'gratitude' en inglés. ¡Gracias!",
        )
        self.assertEqual(note, "introduced:gracias")
        _u2, note2 = mark_introduced_if_visible(
            default_sheet(), plan, "¡Gracias, amigo!"
        )
        self.assertEqual(note2, "introduce_lapsed:gracias:no_scaffold")

    def test_image_plan_requires_attached_image(self):
        plan = self._plan("hermano")
        self.assertEqual(plan.rule_id, "R-B")
        sheet = default_sheet()
        # No teach_image attached this turn → lapse (belt-and-suspenders:
        # conv_session already downgrades R-B→R-D pre-mark on a miss)
        updated, note = mark_introduced_if_visible(
            sheet, plan, "Mira: mi **hermano**.", teach_images=[]
        )
        self.assertEqual(note, "introduce_lapsed:hermano:no_scaffold")
        self.assertIs(updated, sheet)
        # Image actually attached → introduce move happened
        updated2, note2 = mark_introduced_if_visible(
            sheet, plan, "Mira: mi **hermano**.",
            teach_images=[{"concept": "hermano", "path": "x.png"}],
        )
        self.assertEqual(note2, "introduced:hermano")
        self.assertTrue(updated2["lexicon"]["hermano"].get("introduced_at"))

    def test_downgraded_image_plan_requires_gloss(self):
        """conv_session's R-B→R-D downgrade (image never attached) produces a
        gloss plan — the mark then demands the gloss parenthetical."""
        from tutor.introduce_router import IntroducePlan

        gloss = self.table["hermano"]["gloss_en"]
        plan = IntroducePlan(
            key="hermano",
            rule_id="R-D",
            scaffold_type="gloss",
            scaffold_payload={
                "gloss": gloss, "format": f"**hermano** ({gloss})",
            },
        )
        _u, note = mark_introduced_if_visible(
            default_sheet(), plan, "Mi **hermano** está en casa."
        )
        self.assertEqual(note, "introduce_lapsed:hermano:no_scaffold")
        _u2, note2 = mark_introduced_if_visible(
            default_sheet(), plan, f"Mi **hermano** ({gloss}) está en casa."
        )
        self.assertEqual(note2, "introduced:hermano")

    def test_mwu_key_boundary_containment(self):
        plan = self._plan("hasta luego")
        updated, note = mark_introduced_if_visible(
            default_sheet(), plan,
            "**Hasta luego** — como 'hasta la vista'. ¡Hasta luego, amigo!",
        )
        self.assertEqual(note, "introduced:hasta luego")
        self.assertTrue(
            updated["lexicon"]["hasta luego"].get("introduced_at")
        )
        # A different farewell must NOT mark (or lapse) this key
        _updated2, note2 = mark_introduced_if_visible(
            default_sheet(), plan, "¡Hasta mañana!"
        )
        self.assertIsNone(note2)

    def test_new_entry_created_at_honest_zero(self):
        plan = self._plan("me llamo")
        updated, note = mark_introduced_if_visible(
            default_sheet(), plan, "**Me llamo** (my name is) Marisol. ¿Y tú?"
        )
        self.assertEqual(note, "introduced:me llamo")
        entry = updated["lexicon"]["me llamo"]
        self.assertEqual(entry.get("confidence"), 0.0)
        self.assertEqual(entry.get("status"), "unknown")

    def test_no_plan_is_noop(self):
        sheet = default_sheet()
        updated, note = mark_introduced_if_visible(sheet, None, "Hola.")
        self.assertIs(updated, sheet)
        self.assertIsNone(note)


if __name__ == "__main__":
    unittest.main()
