"""B0 realization context — floor completeness, same-turn slice, negative
projection, K floor, full-path byte-identity, completeness_v1 lint.

No live API. PEDAGOGY §3.3 (amended 2026-07-30); design:
docs/design-planner-rounds.md (round-2 A1 floor list).
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tutor import config, realization_context as rcmod
from tutor.association_table import load_association_table
from tutor.character_sheet import default_sheet
from tutor.conv_session import build_session_phase_state
from tutor.executor import build_ai_tutor_system, build_ai_tutor_user_message
from tutor.introduce_router import plan_introduction
from tutor.lesson_brief import assemble_lesson_brief
from tutor.modes import Mode, ModeDecision, ModeSessionState
from tutor.realization_context import (
    K_EXCHANGES,
    K_FLOOR,
    build_realization_context,
    resolve_key_or_nearest,
    table_keys_in_text,
)
from tutor.session_memory import SessionMemory
from tutor.turn_pipeline import TurnContext, stage_prompt_build

ROOT = Path(__file__).resolve().parents[1]
TABLE = load_association_table(config.DEFAULT_PACK_DIR)

# Import the lint by path (scripts/ is not a package).
_spec = importlib.util.spec_from_file_location(
    "check_completeness", ROOT / "scripts" / "check_completeness.py")
check_completeness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_completeness)
check_artifact = check_completeness.check_artifact


def make_sheet() -> dict:
    sheet = default_sheet()
    sheet["lexicon"]["hola"] = {
        "confidence": 0.3, "status": "emerging",
        "introduced_at": "2020-01-01", "next_due": "2020-01-02",
        "interval_days": 1,
    }
    sheet["lexicon"]["gracias"] = {"confidence": 0.8, "status": "known"}
    return sheet


def make_session(history=None) -> SimpleNamespace:
    sheet = make_sheet()
    return SimpleNamespace(
        sheet=sheet,
        association_table=TABLE,
        pedagogy_memory=SessionMemory(),
        mode_state=ModeSessionState(),
        phase_state=build_session_phase_state(sheet, config.DEFAULT_PACK_DIR),
        task_state=None,
        gate_still_fail_count=0,
        pack_dir=config.DEFAULT_PACK_DIR,
        history=list(history or []),
    )


def make_ctx(session, learner="Hola, ¿qué es café?", intro_key="pan"):
    ctx = TurnContext(learner=learner, is_open=False, ev=None)
    ctx.decision = ModeDecision(
        mode=Mode.CONVERSATION, reason="default_conversation")
    ctx.activity = session.phase_state.current_activity()
    ctx.obs = {
        "signals": [], "error_hits": [], "error_hit_ids": [],
        "active_errors": [], "next_best": {}, "blank_sheet": False,
    }
    if intro_key:
        ctx.intro_plan = plan_introduction(
            session.sheet, TABLE, session.pedagogy_memory.snapshot(),
            key=intro_key,
        )
    return ctx


def build_artifact(session=None, ctx=None):
    session = session or make_session(
        history=[{"role": "user", "content": "hola"},
                 {"role": "assistant", "content": "¡Hola! ¿Cómo estás?"}])
    ctx = ctx or make_ctx(session)
    brief = assemble_lesson_brief(session, ctx)
    rc = build_realization_context(session, ctx, brief)
    return session, ctx, rc


class TestFloorCompleteness(unittest.TestCase):
    def test_all_floor_members_present_and_lint_green(self):
        # completeness_v1 amendment 2026-07-30: 10 → 11 members —
        # reply_protocol added after the first live B0 arm shipped
        # without the structured-reply interface (pedagogy:no_teach_move
        # on 10/12 turns; the census named laws, not the interface).
        _s, _c, rc = build_artifact()
        floor = rc.artifact["floor"]
        for member in rcmod.FLOOR_MEMBERS:
            self.assertIn(member, floor, f"floor member missing: {member}")
        self.assertEqual(len(rcmod.FLOOR_MEMBERS), 11)
        self.assertTrue(floor["reply_protocol"]["present"])
        self.assertEqual(check_artifact(rc.artifact), [])

    def test_law_core_loaded_and_bounded(self):
        _s, _c, rc = build_artifact()
        law = rc.artifact["floor"]["law_core"]
        self.assertTrue(law["present"])
        # Census bound: operative core ≤1200 tokens ≈ ≤4800 chars.
        self.assertLessEqual(law["chars"], 4800)

    def test_pack_index_within_token_bound(self):
        _s, _c, rc = build_artifact()
        idx = rc.artifact["floor"]["pack_index"]
        self.assertTrue(idx["unit_topics"] or idx["themes"])
        self.assertLessEqual(
            len(json.dumps(idx, ensure_ascii=False)),
            rcmod.PACK_INDEX_MAX_CHARS)

    def test_k_floor_is_at_least_two(self):
        self.assertGreaterEqual(K_FLOOR, 2)
        self.assertGreaterEqual(K_EXCHANGES, K_FLOOR)
        _s, _c, rc = build_artifact()
        self.assertGreaterEqual(rc.artifact["k_exchanges"], 2)
        # Window is bounded by K pairs (2 messages per exchange).
        self.assertLessEqual(len(rc.window_messages), 2 * K_EXCHANGES)


class TestSameTurnSlice(unittest.TestCase):
    def test_key_detected_in_current_learner_text_enters_slice(self):
        # §2.1 same-turn resolve (round-1 REJECT of "next round"): a pack
        # word in the CURRENT learner utterance is in THIS turn's slice.
        session = make_session()
        ctx = make_ctx(session, learner="¿Qué es café?")
        brief = assemble_lesson_brief(session, ctx)
        rc = build_realization_context(session, ctx, brief)
        rows = rc.artifact["floor"]["dynamic_slice"]["rows"]
        self.assertIn("café", rows)
        self.assertIn("café",
                      rc.artifact["gate_key_classes"]["learner_detected"])
        # The row carries the association-table fields (gloss/theme).
        self.assertTrue(rows["café"]["gloss"])

    def test_slice_includes_due_and_introduce_keys(self):
        _s, _c, rc = build_artifact()
        rows = rc.artifact["floor"]["dynamic_slice"]["rows"]
        self.assertIn("hola", rows)   # due
        self.assertIn("pan", rows)    # allowed_new
        self.assertEqual(check_artifact(rc.artifact), [])

    def test_fallback_resolves_near_key_or_logs_slice_miss(self):
        session = make_session()
        # Self-flagged token with a gloss guess — near «café» (accent lost).
        ctx = make_ctx(session, learner="Quiero un cafe («cafe»)",
                       intro_key=None)
        brief = assemble_lesson_brief(session, ctx)
        rc = build_realization_context(session, ctx, brief)
        fb = rc.artifact["floor"]["fallback"]
        self.assertEqual(fb["resolved"].get("cafe"), "café")
        # A genuinely off-catalog span is a logged slice_miss, not free
        # invention (and not a new event kind).
        ctx2 = make_ctx(session, learner="I said «florble» to her",
                        intro_key=None)
        brief2 = assemble_lesson_brief(session, ctx2)
        rc2 = build_realization_context(session, ctx2, brief2)
        self.assertIn("florble",
                      rc2.artifact["floor"]["fallback"]["slice_miss"])

    def test_resolve_key_or_nearest(self):
        self.assertEqual(resolve_key_or_nearest("cafe", TABLE), "café")
        self.assertIsNone(resolve_key_or_nearest("florble", TABLE))
        self.assertIsNone(resolve_key_or_nearest("", TABLE))

    def test_table_scan_uses_boundary_discipline(self):
        # sol must not fire inside Marisol (the historical incident class).
        keys = table_keys_in_text("Hola Marisol", TABLE)
        self.assertNotIn("sol", keys)
        self.assertIn("hola", keys)


class TestNegativeProjection(unittest.TestCase):
    def test_cluster_mates_of_allowed_new_present(self):
        # Round-2 A1: missing cluster mates is a completeness FAULT.
        _s, ctx, rc = build_artifact()
        neg = rc.artifact["floor"]["negative_projection"]
        mates = neg["cluster_mates_of_allowed_new"]
        self.assertTrue(mates)
        # pan is theme "food" — a same-theme unintroduced mate must appear.
        food_mates = [k for k in TABLE
                      if TABLE[k]["theme"] == TABLE["pan"]["theme"]
                      and k != "pan"]
        self.assertTrue(set(mates) & set(food_mates))
        # And they match the router's own cluster ban list.
        for k in ctx.intro_plan.forbid_cluster_with:
            self.assertIn(k, mates)

    def test_denylist_known_and_asked_frames_present(self):
        session = make_session()
        session.pedagogy_memory.note_asked_topic("wellbeing", "")
        ctx = make_ctx(session)
        brief = assemble_lesson_brief(session, ctx)
        rc = build_realization_context(session, ctx, brief)
        neg = rc.artifact["floor"]["negative_projection"]
        self.assertIn("Scope boundaries", neg["denylist_excerpt"])
        self.assertIn("Gustar", neg["denylist_excerpt"])
        self.assertIn("wellbeing", neg["asked_frames"])
        self.assertIn("gracias", neg["known_no_quiz"])  # conf 0.8 → known
        self.assertTrue(neg["must_not"])


class TestFullPathUnchanged(unittest.TestCase):
    def _run_full(self, session, ctx):
        with mock.patch.object(config, "TEACHER_CONTEXT", "full"), \
                mock.patch("tutor.character_sheet.now_iso",
                           return_value="2026-07-30T00:00:00"):
            stage_prompt_build(session, ctx)
            from tutor.character_sheet import format_sheet_for_prompt
            from tutor.corpus import load_pack
            from tutor.scenes import scene_hints_for_prompt

            expected_system = build_ai_tutor_system(
                pack_palette=load_pack(session.pack_dir))
            # §1.1 rewrite (2026-08-03): the full path ships FACTS — no
            # mode/observations; due items ride as teaching_data.
            from tutor.retrieval_scheduler import due_items, frames_seen_of

            table = getattr(session, "association_table", None) or {}
            due_facts = [
                {
                    "key": d.key,
                    "kind": d.kind,
                    "gloss": str((table.get(d.key) or {}).get("gloss_en") or ""),
                    "frames_already_used": list(
                        frames_seen_of(session.sheet, d.key, d.kind)),
                }
                for d in due_items(session.sheet, max_due=5)
            ]
            expected_task = build_ai_tutor_user_message(
                learner=ctx.learner,
                is_open=ctx.is_open,
                session_memory=session.pedagogy_memory.snapshot(),
                teach_images=ctx.teach_images,
                blank_sheet=ctx.blank,
                open_scene_hints=scene_hints_for_prompt(ctx.open_scenes),
                sheet_summary=format_sheet_for_prompt(session.sheet),
                teaching_data={"due_for_review": due_facts},
            )
        return expected_system, expected_task

    def test_default_is_full(self):
        # TEACHER_CONTEXT unset → "full" (dual-path is NON-DEFAULT until
        # the pre-registered referee passes — §3.3 enactment condition iv).
        self.assertEqual(
            (config.TEACHER_CONTEXT or "full"), config.TEACHER_CONTEXT)
        self.assertIn(config.TEACHER_CONTEXT, ("full", "brief"))

    def test_full_path_byte_identical_to_historical_prompt(self):
        history = [
            {"role": "user", "content": "hola"},
            {"role": "assistant", "content": "¡Hola! ¿Cómo estás?"},
            {"role": "user", "content": "estoy bien"},
            {"role": "assistant", "content": "¡Qué bien! ¿Y hoy?"},
        ]
        session = make_session(history=history)
        ctx = make_ctx(session, intro_key=None)
        expected_system, expected_task = self._run_full(session, ctx)
        self.assertEqual(ctx.task, expected_task)
        self.assertEqual(ctx.system, expected_system)
        # Full history — no window on the full path.
        self.assertEqual(
            ctx.messages,
            config.history_for_model(session.history)
            + [{"role": "user", "content": ctx.task}],
        )
        # No artifact on the full path.
        self.assertIsNone(ctx.realization_artifact)


class TestBriefPathHook(unittest.TestCase):
    def test_brief_path_swaps_prompt_and_stashes_artifact(self):
        history = [
            {"role": "user", "content": f"turno {i}"} if i % 2 == 0
            else {"role": "assistant", "content": f"respuesta {i}"}
            for i in range(10)
        ]
        session = make_session(history=history)
        ctx = make_ctx(session)
        with mock.patch.object(config, "TEACHER_CONTEXT", "brief"):
            stage_prompt_build(session, ctx)
        self.assertIsNotNone(ctx.realization_artifact)
        self.assertEqual(check_artifact(ctx.realization_artifact), [])
        # System = law core + persona only (cache-stable pair).
        self.assertIn("Executor law core", ctx.system[0]["text"])
        self.assertNotIn("Course pack palette",
                         " ".join(b["text"] for b in ctx.system))
        # Task carries brief + slice + bans + manifest.
        for marker in ("lesson_brief", "dynamic_slice",
                       "negative_projection", "session_manifest"):
            self.assertIn(marker, ctx.task)
        # Messages = last-K window + task (K pairs, never full history).
        self.assertEqual(ctx.messages[-1]["content"], ctx.task)
        self.assertEqual(len(ctx.messages) - 1, 2 * K_EXCHANGES)
        self.assertEqual(
            [m["content"] for m in ctx.messages[:-1]],
            [m["content"] for m in history[-2 * K_EXCHANGES:]],
        )


class TestCompletenessLint(unittest.TestCase):
    def test_lint_green_on_good_artifact(self):
        _s, _c, rc = build_artifact()
        self.assertEqual(check_artifact(rc.artifact), [])

    def test_lint_fails_when_any_floor_member_removed(self):
        _s, _c, rc = build_artifact()
        for member in rcmod.FLOOR_MEMBERS:
            broken = json.loads(json.dumps(rc.artifact))
            del broken["floor"][member]
            faults = check_artifact(broken)
            self.assertTrue(
                any(member in f for f in faults),
                f"removing {member} did not fault: {faults}")

    def test_lint_fails_on_gate_key_missing_from_slice(self):
        # elfric regret #4: a gate-judged key the executor never saw.
        _s, _c, rc = build_artifact()
        broken = json.loads(json.dumps(rc.artifact))
        del broken["floor"]["dynamic_slice"]["rows"]["pan"]
        faults = check_artifact(broken)
        self.assertTrue(any("pan" in f for f in faults), faults)

    def test_lint_fails_on_k_below_floor(self):
        _s, _c, rc = build_artifact()
        broken = json.loads(json.dumps(rc.artifact))
        broken["k_exchanges"] = 1
        faults = check_artifact(broken)
        self.assertTrue(any("k_exchanges" in f for f in faults), faults)

    def test_lint_fails_on_empty_denylist(self):
        _s, _c, rc = build_artifact()
        broken = json.loads(json.dumps(rc.artifact))
        broken["floor"]["negative_projection"]["denylist_excerpt"] = ""
        faults = check_artifact(broken)
        self.assertTrue(any("denylist" in f for f in faults), faults)

    def test_cli_exits_nonzero_on_fault(self):
        import subprocess
        import sys
        import tempfile

        _s, _c, rc = build_artifact()
        good = json.dumps(rc.artifact)
        broken_d = json.loads(good)
        del broken_d["floor"]["law_core"]
        with tempfile.TemporaryDirectory() as td:
            gp = Path(td) / "good.json"
            bp = Path(td) / "bad.json"
            gp.write_text(good, encoding="utf-8")
            bp.write_text(json.dumps(broken_d), encoding="utf-8")
            script = str(ROOT / "scripts" / "check_completeness.py")
            ok = subprocess.run(
                [sys.executable, script, str(gp)], capture_output=True)
            bad = subprocess.run(
                [sys.executable, script, str(bp)], capture_output=True)
        self.assertEqual(ok.returncode, 0, ok.stdout)
        self.assertNotEqual(bad.returncode, 0)


if __name__ == "__main__":
    unittest.main()
