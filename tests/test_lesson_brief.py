"""LessonBrief schema v2 — validation + code-only assembly (B0, §3.3).

No live API. The synthetic session is a SimpleNamespace carrying the REAL
stores (SessionMemory / ModeSessionState / PhaseState / sheet / table) —
the same shapes the pipeline threads.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from tutor import config
from tutor.association_table import load_association_table
from tutor.character_sheet import default_sheet
from tutor.conv_session import build_session_phase_state
from tutor.introduce_router import plan_introduction
from tutor.lesson_brief import (
    LessonBrief,
    OUTPUT_SHAPE,
    assemble_lesson_brief,
    parse_lesson_brief,
)
from tutor.modes import Mode, ModeDecision, ModeSessionState
from tutor.session_memory import SessionMemory
from tutor.turn_pipeline import TurnContext

TABLE = load_association_table(config.DEFAULT_PACK_DIR)


def make_sheet() -> dict:
    sheet = default_sheet()
    sheet["lexicon"]["hola"] = {
        "confidence": 0.3, "status": "emerging",
        "introduced_at": "2020-01-01", "next_due": "2020-01-02",
        "interval_days": 1,
    }
    sheet["lexicon"]["gracias"] = {"confidence": 0.8, "status": "known"}
    return sheet


def make_session(sheet: dict | None = None) -> SimpleNamespace:
    sheet = sheet if sheet is not None else make_sheet()
    return SimpleNamespace(
        sheet=sheet,
        association_table=TABLE,
        pedagogy_memory=SessionMemory(),
        mode_state=ModeSessionState(),
        phase_state=build_session_phase_state(sheet, config.DEFAULT_PACK_DIR),
        task_state=None,
        gate_still_fail_count=0,
        pack_dir=config.DEFAULT_PACK_DIR,
        history=[],
    )


def make_ctx(session, learner: str = "Hola, estoy bien",
             intro_key: str | None = "pan") -> TurnContext:
    ctx = TurnContext(learner=learner, is_open=False, ev=None)
    ctx.decision = ModeDecision(
        mode=Mode.CONVERSATION, reason="default_conversation")
    ctx.activity = session.phase_state.current_activity()
    if intro_key:
        ctx.intro_plan = plan_introduction(
            session.sheet, TABLE, session.pedagogy_memory.snapshot(),
            key=intro_key,
        )
    return ctx


def valid_brief_data(**overrides) -> dict:
    data = {
        "phase": "free",
        "targets": [
            {"key": "hola", "gloss": "hello", "anchor": "", "move": "elicit"},
        ],
        "allowed_new": [],
        "banned_asks": [],
        "due_frames": [
            {"key": "hola", "kind": "lexicon", "avoid_frames": []},
        ],
        "budgets": {
            "introduce_left": 2, "form_focus_cooldown": 0,
            "content_uptake_left": 1, "checker_left": 1,
        },
        "must_not": ["no dual-subtitle English walls"],
        "cf_target": None,
        "register": "adult informal A1 (tú), Spanish-first",
        "scene_goal": None,
        "exit_criteria": "phase free: 0/2 consuming turns used",
        "output_shape": list(OUTPUT_SHAPE),
        "session_manifest": {
            "introduced_this_session": [], "cf_targets": [],
            "still_fail_count": 0, "phase_id": "0:free",
        },
    }
    data.update(overrides)
    return data


class TestParseLessonBrief(unittest.TestCase):
    def test_valid_brief_parses(self):
        brief = parse_lesson_brief(
            valid_brief_data(), table=TABLE, sheet=make_sheet())
        self.assertIsInstance(brief, LessonBrief)
        self.assertEqual(brief.phase, "free")
        self.assertEqual(brief.targets[0]["key"], "hola")

    def test_unknown_top_level_key_rejected(self):
        data = valid_brief_data()
        data["lesson_script"] = "say hola then estoy"  # free-prose intent
        with self.assertRaises(ValueError) as cm:
            parse_lesson_brief(data, table=TABLE, sheet=make_sheet())
        self.assertIn("lesson_script", str(cm.exception))

    def test_unknown_nested_field_rejected(self):
        data = valid_brief_data(targets=[{
            "key": "hola", "gloss": "hello", "anchor": "", "move": "elicit",
            "script_line": "¡Hola amigo!",
        }])
        with self.assertRaises(ValueError) as cm:
            parse_lesson_brief(data, table=TABLE, sheet=make_sheet())
        self.assertIn("script_line", str(cm.exception))

    def test_invented_key_rejected(self):
        # elfric trap #13: a key outside association table ∪ sheet.
        data = valid_brief_data(targets=[{
            "key": "florble", "gloss": "??", "anchor": "", "move": "elicit",
        }])
        with self.assertRaises(ValueError) as cm:
            parse_lesson_brief(data, table=TABLE, sheet=make_sheet())
        self.assertIn("florble", str(cm.exception))

    def test_allowed_new_must_be_subset_of_router_plan(self):
        # 'pan' is a real table key, but the router planned nothing —
        # the brief may never widen what code decided.
        data = valid_brief_data(allowed_new=[
            {"key": "pan", "rule_id": "R-D", "anchor": ""},
        ])
        with self.assertRaises(ValueError) as cm:
            parse_lesson_brief(
                data, table=TABLE, sheet=make_sheet(), intro_plan_keys=[])
        self.assertIn("introduce plan", str(cm.exception))
        # Same data with the router plan present is legal.
        brief = parse_lesson_brief(
            data, table=TABLE, sheet=make_sheet(), intro_plan_keys=["pan"])
        self.assertEqual(brief.allowed_new[0]["key"], "pan")

    def test_budgets_must_be_code_numbers(self):
        data = valid_brief_data(budgets={
            "introduce_left": "two", "form_focus_cooldown": 0,
            "content_uptake_left": 1, "checker_left": 1,
        })
        with self.assertRaises(ValueError) as cm:
            parse_lesson_brief(data, table=TABLE, sheet=make_sheet())
        self.assertIn("introduce_left", str(cm.exception))

    def test_missing_budget_field_rejected(self):
        data = valid_brief_data(budgets={"introduce_left": 2})
        with self.assertRaises(ValueError):
            parse_lesson_brief(data, table=TABLE, sheet=make_sheet())


class TestAssembleLessonBrief(unittest.TestCase):
    def test_assembled_brief_is_schema_valid_and_code_derived(self):
        session = make_session()
        ctx = make_ctx(session)
        brief = assemble_lesson_brief(session, ctx)
        # Roundtrip through the validator (assemble already validates; a
        # second parse proves the dict form is schema-clean too).
        reparsed = parse_lesson_brief(
            brief.as_dict(), table=TABLE, sheet=session.sheet,
            intro_plan_keys=["pan"])
        self.assertEqual(reparsed.phase, brief.phase)
        for b in ("introduce_left", "form_focus_cooldown",
                  "content_uptake_left", "checker_left"):
            self.assertIsInstance(brief.budgets[b], int)
        self.assertEqual(brief.budgets["introduce_left"], 2)
        # Due queue (hola past-due) became due_frames + an elicit target.
        due_keys = [d["key"] for d in brief.due_frames]
        self.assertIn("hola", due_keys)
        self.assertIn(
            "hola", [t["key"] for t in brief.targets if t["move"] == "elicit"])

    def test_allowed_new_packages_router_plan_only(self):
        session = make_session()
        ctx = make_ctx(session, intro_key="pan")
        brief = assemble_lesson_brief(session, ctx)
        self.assertEqual(len(brief.allowed_new), 1)
        entry = brief.allowed_new[0]
        self.assertEqual(entry["key"], "pan")
        self.assertEqual(entry["rule_id"], ctx.intro_plan.rule_id)
        # No plan → empty allowed_new (code decided nothing new).
        ctx2 = make_ctx(session, intro_key=None)
        brief2 = assemble_lesson_brief(session, ctx2)
        self.assertEqual(brief2.allowed_new, [])

    def test_manifest_and_banned_asks_are_mechanical(self):
        session = make_session()
        session.pedagogy_memory.note_asked_topic("wellbeing", "")
        session.pedagogy_memory.introduced_this_session.append("hola")
        session.gate_still_fail_count = 2
        ctx = make_ctx(session, intro_key=None)
        brief = assemble_lesson_brief(session, ctx)
        self.assertIn("wellbeing", brief.banned_asks)
        m = brief.session_manifest
        self.assertEqual(m["introduced_this_session"], ["hola"])
        self.assertEqual(m["still_fail_count"], 2)
        self.assertTrue(m["phase_id"])
        # Introduce budget reflects the session counter (2 - 1 used).
        self.assertEqual(brief.budgets["introduce_left"], 1)

    def test_cf_target_only_from_router_decision(self):
        session = make_session()
        ctx = make_ctx(session, intro_key=None)
        ctx.decision = ModeDecision(
            mode=Mode.CF_RECAST, reason="error_hit",
            targets={"error_pattern": "estar_yo_estoy_vs_esta"})
        brief = assemble_lesson_brief(session, ctx)
        self.assertIsNotNone(brief.cf_target)
        self.assertEqual(brief.cf_target["pattern"], "estar_yo_estoy_vs_esta")
        self.assertEqual(brief.cf_target["move"], "recast")


if __name__ == "__main__":
    unittest.main()
