"""RetrievalScheduler + introduce ledger (Phase 1 pedagogy engine).

Covers: interval ladder + fake clock, honesty law (introduce/schedule never
changes confidence/status), kind interleaving, session intro budget, MWU key
normalize round-trip, and the DUE RE-ENCOUNTERS soft-wiring block.
"""

import datetime
import unittest

from tutor.character_sheet import (
    apply_delta,
    default_sheet,
    normalize_sheet,
)
from tutor.conv_session import due_elicit_block
from tutor.retrieval_scheduler import (
    INTERVAL_CAP_DAYS,
    DueItem,
    due_items,
    enqueue,
    has_first_seen,
    is_introduced,
    mark_first_seen,
    mark_introduced,
    record_outcome,
)
from tutor.session_memory import INTRO_BUDGET_PER_SESSION, SessionMemory

D0 = datetime.date(2026, 7, 1)


def _entry(sheet: dict, key: str, section: str = "lexicon") -> dict:
    return (sheet.get(section) or {}).get(key) or {}


class TestIntervalLadder(unittest.TestCase):
    def test_ladder_1_3_x2_cap14(self):
        s = default_sheet()
        s = mark_introduced(s, "hasta luego", "lexicon", "l1_micro_gloss", today=D0)
        e = _entry(s, "hasta luego")
        # introduce success → next_due tomorrow (r7 R-H)
        self.assertEqual(e["next_due"], (D0 + datetime.timedelta(days=1)).isoformat())
        self.assertEqual(e["interval_days"], 1)
        self.assertEqual(e["successive_successes"], 0)

        day = D0 + datetime.timedelta(days=1)
        s = record_outcome(s, "hasta luego", "lexicon", True, today=day)
        e = _entry(s, "hasta luego")
        # first success → +1d
        self.assertEqual(e["successive_successes"], 1)
        self.assertEqual(e["interval_days"], 1)
        self.assertEqual(e["next_due"], (day + datetime.timedelta(days=1)).isoformat())

        day = day + datetime.timedelta(days=1)
        s = record_outcome(s, "hasta luego", "lexicon", True, today=day)
        e = _entry(s, "hasta luego")
        # second success → +3d
        self.assertEqual(e["successive_successes"], 2)
        self.assertEqual(e["interval_days"], 3)
        self.assertEqual(e["next_due"], (day + datetime.timedelta(days=3)).isoformat())

        day = day + datetime.timedelta(days=3)
        s = record_outcome(s, "hasta luego", "lexicon", True, today=day)
        e = _entry(s, "hasta luego")
        # third success → ×2 = +6d
        self.assertEqual(e["interval_days"], 6)
        self.assertEqual(e["next_due"], (day + datetime.timedelta(days=6)).isoformat())

        day = day + datetime.timedelta(days=6)
        s = record_outcome(s, "hasta luego", "lexicon", True, today=day)
        self.assertEqual(_entry(s, "hasta luego")["interval_days"], 12)

        day = day + datetime.timedelta(days=12)
        s = record_outcome(s, "hasta luego", "lexicon", True, today=day)
        e = _entry(s, "hasta luego")
        # 12×2=24 → capped at 14
        self.assertEqual(e["interval_days"], INTERVAL_CAP_DAYS)
        self.assertEqual(
            e["next_due"],
            (day + datetime.timedelta(days=INTERVAL_CAP_DAYS)).isoformat(),
        )

    def test_fail_resets_to_1d(self):
        s = default_sheet()
        s = mark_introduced(s, "hasta luego", "lexicon", None, today=D0)
        for i in range(3):
            s = record_outcome(
                s, "hasta luego", "lexicon", True,
                today=D0 + datetime.timedelta(days=i + 1),
            )
        self.assertGreaterEqual(_entry(s, "hasta luego")["interval_days"], 6)
        day = D0 + datetime.timedelta(days=10)
        s = record_outcome(s, "hasta luego", "lexicon", False, today=day)
        e = _entry(s, "hasta luego")
        self.assertEqual(e["interval_days"], 1)
        self.assertEqual(e["successive_successes"], 0)
        self.assertEqual(e["next_due"], (day + datetime.timedelta(days=1)).isoformat())


class TestFakeClock(unittest.TestCase):
    def test_not_due_today_due_later(self):
        s = default_sheet()
        s = enqueue(s, "gracias", "lexicon", today=D0)  # next_due = D0+1
        self.assertEqual(due_items(s, today=D0), [])
        later = due_items(s, today=D0 + datetime.timedelta(days=2))
        self.assertEqual([d.key for d in later], ["gracias"])
        self.assertIsInstance(later[0], DueItem)
        self.assertEqual(later[0].kind, "lexicon")
        self.assertEqual(
            later[0].next_due, D0 + datetime.timedelta(days=1)
        )

    def test_oldest_due_first(self):
        s = default_sheet()
        s = enqueue(s, "gracias", "lexicon", today=D0)
        s = enqueue(s, "hola", "lexicon", today=D0 - datetime.timedelta(days=5))
        got = due_items(s, today=D0 + datetime.timedelta(days=2))
        self.assertEqual([d.key for d in got], ["hola", "gracias"])


class TestHonestyLaw(unittest.TestCase):
    def test_ledger_writes_never_change_confidence_or_status(self):
        s = default_sheet()
        s["lexicon"]["hasta luego"] = {
            "status": "fragile", "confidence": 0.42, "solid_uses": 1,
        }
        for step in (
            lambda x: mark_introduced(
                x, "hasta luego", "lexicon", "cognate", today=D0),
            lambda x: enqueue(x, "hasta luego", "lexicon", today=D0),
            lambda x: record_outcome(
                x, "hasta luego", "lexicon", True, today=D0),
            lambda x: record_outcome(
                x, "hasta luego", "lexicon", False, today=D0),
            lambda x: mark_first_seen(
                x, "hasta luego", "lexicon", "gloss", today=D0),
        ):
            s = step(s)
            e = _entry(s, "hasta luego")
            self.assertEqual(e["status"], "fragile")
            self.assertEqual(e["confidence"], 0.42)
            self.assertEqual(e["solid_uses"], 1)

    def test_grammar_and_skill_entries_also_protected(self):
        s = default_sheet()
        s["grammar"]["present_estar_person"]["confidence"] = 0.5
        s["grammar"]["present_estar_person"]["status"] = "emerging"
        s = enqueue(s, "present_estar_person", "grammar", today=D0)
        g = _entry(s, "present_estar_person", "grammar")
        self.assertEqual(g["confidence"], 0.5)
        self.assertEqual(g["status"], "emerging")

        before = dict(s["skills"]["IP-05"])
        s = mark_introduced(s, "IP-05", "skill", None, today=D0)
        sk = _entry(s, "IP-05", "skills")
        self.assertEqual(sk["confidence"], before.get("confidence"))
        self.assertEqual(sk["status"], before.get("status"))

    def test_new_entry_created_at_honest_zero(self):
        s = default_sheet()
        s = mark_introduced(s, "hasta luego", "lexicon", "image", today=D0)
        e = _entry(s, "hasta luego")
        self.assertEqual(e["status"], "unknown")
        self.assertEqual(e["confidence"], 0.0)
        self.assertTrue(is_introduced(s, "hasta luego", "lexicon"))

    def test_tool_delta_cannot_write_schedule_fields(self):
        # Code decides: model/tool deltas may not set due dates or ledger facts
        s = default_sheet()
        s = apply_delta(s, {
            "lexicon": {
                "hola": {
                    "status": "emerging", "confidence": 0.2,
                    "next_due": "2020-01-01", "introduced_at": "2020-01-01",
                    "first_seen": "2020-01-01",
                    "interval_days": 99, "successive_successes": 9,
                },
            },
        })
        e = _entry(s, "hola")
        self.assertNotIn("next_due", e)
        self.assertNotIn("introduced_at", e)
        self.assertNotIn("first_seen", e)
        self.assertNotIn("interval_days", e)
        self.assertNotIn("successive_successes", e)

    def test_mark_first_seen_is_not_an_introduction(self):
        # Round-2 AMEND 1c: durable "seen with in-reply scaffold" bit only.
        # No introduced_at (budget stays router-only), NO retrieval enqueue
        # (no next_due/interval), confidence/status untouched.
        s = default_sheet()
        s["lexicon"]["gracias"] = {
            "status": "fragile", "confidence": 0.15, "solid_uses": 0,
        }
        s = mark_first_seen(s, "gracias", "lexicon", "gloss", today=D0)
        e = _entry(s, "gracias")
        self.assertEqual(e["first_seen"], D0.isoformat())
        self.assertEqual(e["scaffold"], "gloss")
        self.assertNotIn("introduced_at", e)
        self.assertNotIn("next_due", e)
        self.assertNotIn("interval_days", e)
        self.assertEqual(e["status"], "fragile")
        self.assertEqual(e["confidence"], 0.15)
        self.assertTrue(has_first_seen(s, "gracias", "lexicon"))
        self.assertFalse(is_introduced(s, "gracias", "lexicon"))
        self.assertEqual(due_items(s, today=D0 + datetime.timedelta(days=30)),
                         [])
        # Idempotent: a later write keeps the original first_seen date.
        later = D0 + datetime.timedelta(days=5)
        s = mark_first_seen(s, "gracias", "lexicon", "anchor", today=later)
        e = _entry(s, "gracias")
        self.assertEqual(e["first_seen"], D0.isoformat())
        self.assertEqual(e["scaffold"], "gloss")

    def test_mark_first_seen_new_entry_honest_zero(self):
        s = default_sheet()
        s = mark_first_seen(s, "gracias", "lexicon", "anchor", today=D0)
        e = _entry(s, "gracias")
        self.assertEqual(e["status"], "unknown")
        self.assertEqual(e["confidence"], 0.0)
        self.assertEqual(e["scaffold"], "anchor")
        self.assertTrue(has_first_seen(s, "gracias", "lexicon"))
        self.assertFalse(is_introduced(s, "gracias", "lexicon"))


class TestInterleaving(unittest.TestCase):
    def test_two_lexicon_one_grammar_returns_both_kinds(self):
        s = default_sheet()
        past = D0 - datetime.timedelta(days=3)
        s = enqueue(s, "hola", "lexicon", today=past)
        s = enqueue(s, "gracias", "lexicon", today=past)
        s = enqueue(s, "present_estar_person", "grammar", today=past)
        got = due_items(s, today=D0, max_due=3)
        self.assertEqual(len(got), 3)
        self.assertEqual({d.kind for d in got}, {"lexicon", "grammar"})

    def test_never_max_due_of_one_kind_when_another_is_due(self):
        s = default_sheet()
        past = D0 - datetime.timedelta(days=5)
        for k in ("hola", "gracias", "adiós", "hasta luego"):
            s = enqueue(s, k, "lexicon", today=past)
        # grammar item due LATER than all lexicon items — still must appear
        s = enqueue(s, "present_ser", "grammar", today=past + datetime.timedelta(days=2))
        got = due_items(s, today=D0, max_due=3)
        self.assertEqual(len(got), 3)
        self.assertIn("grammar", {d.kind for d in got})

    def test_single_kind_fills_all_slots(self):
        s = default_sheet()
        past = D0 - datetime.timedelta(days=2)
        for k in ("hola", "gracias", "adiós"):
            s = enqueue(s, k, "lexicon", today=past)
        got = due_items(s, today=D0, max_due=3)
        self.assertEqual([d.kind for d in got], ["lexicon"] * 3)


class TestSessionBudgetAndMWU(unittest.TestCase):
    def test_intro_budget_2_1_0(self):
        mem = SessionMemory()
        self.assertEqual(mem.intro_budget_remaining(), INTRO_BUDGET_PER_SESSION)
        self.assertEqual(mem.intro_budget_remaining(), 2)
        self.assertTrue(mem.note_introduced("adiós"))
        self.assertEqual(mem.intro_budget_remaining(), 1)
        self.assertTrue(mem.note_introduced("hasta luego"))
        self.assertEqual(mem.intro_budget_remaining(), 0)
        # third introduce rejected (r7 R-G)
        self.assertFalse(mem.note_introduced("buenas noches"))
        self.assertEqual(mem.intro_budget_remaining(), 0)
        # re-noting an already-introduced key is not a new introduction
        self.assertTrue(mem.note_introduced("adiós"))
        self.assertEqual(mem.intro_budget_remaining(), 0)
        snap = mem.snapshot()
        self.assertEqual(
            snap["introduced_this_session"], ["adiós", "hasta luego"]
        )
        self.assertEqual(snap["intro_budget_remaining"], 0)

    def test_mwu_key_survives_normalize_round_trip(self):
        s = default_sheet()
        s = mark_introduced(s, "hasta luego", "lexicon", "l1_micro_gloss", today=D0)
        s2 = normalize_sheet(s)
        e = _entry(s2, "hasta luego")
        self.assertTrue(e, "MWU key 'hasta luego' lost in normalize")
        self.assertEqual(e["introduced_at"], D0.isoformat())
        self.assertEqual(e["scaffold"], "l1_micro_gloss")
        self.assertEqual(
            e["next_due"], (D0 + datetime.timedelta(days=1)).isoformat()
        )
        self.assertEqual(e["interval_days"], 1)
        self.assertEqual(e["successive_successes"], 0)

    def test_normalize_coerces_garbage_schedule_fields(self):
        s = default_sheet()
        s["lexicon"]["hola"] = {
            "status": "emerging", "confidence": 0.2,
            "next_due": "not-a-date", "interval_days": "x",
            "successive_successes": None, "first_seen": "garbage",
        }
        s2 = normalize_sheet(s)
        e = _entry(s2, "hola")
        self.assertIsNone(e["next_due"])
        self.assertEqual(e["interval_days"], 1)
        self.assertEqual(e["successive_successes"], 0)
        self.assertEqual(e["confidence"], 0.2)
        self.assertIsNone(e["first_seen"])


class TestDueElicitWiring(unittest.TestCase):
    def _due_sheet(self) -> dict:
        s = default_sheet()
        s = enqueue(s, "hasta luego", "lexicon", today=D0 - datetime.timedelta(days=5))
        return s

    def test_block_built_for_conversation(self):
        block, due = due_elicit_block(
            self._due_sheet(), mode="conversation", reason="default_conversation",
        )
        self.assertIn("DUE RE-ENCOUNTERS", block)
        self.assertIn("hasta luego", block)
        self.assertIn("no flashcard framing", block)
        self.assertEqual([d.key for d in due], ["hasta luego"])

    def test_block_built_for_transfer(self):
        block, _ = due_elicit_block(
            self._due_sheet(), mode="transfer", reason="success_transfer",
        )
        self.assertIn("DUE RE-ENCOUNTERS", block)

    def test_no_block_on_repair_or_guard_turns(self):
        s = self._due_sheet()
        for mode, reason in (
            ("comprehension_repair", "meta_comprehension_stay_on_topic"),
            ("form_focus", "error_streak:x"),
            ("placement", "blank_open_placement"),
            ("conversation", "learner_topic_request"),
            ("conversation", "learner_help_request"),
            ("conversation", "grammar_question_inline"),
        ):
            block, due = due_elicit_block(s, mode=mode, reason=reason)
            self.assertEqual(block, "", f"{mode}/{reason} should not carry due block")
            self.assertEqual(due, [])

    def test_no_block_during_new_input_phase(self):
        # Grok AMEND 4a (2026-07-28): new_input owns introduce — DUE and
        # INTRODUCE must never stack on one turn.
        s = self._due_sheet()
        block, due = due_elicit_block(
            s, mode="conversation", reason="default_conversation",
            activity_hint="new_input",
        )
        self.assertEqual(block, "")
        self.assertEqual(due, [])
        # Other phases keep the block.
        for hint in ("retrieval", "task", "free", None):
            block, _ = due_elicit_block(
                s, mode="conversation", reason="default_conversation",
                activity_hint=hint,
            )
            self.assertIn("DUE RE-ENCOUNTERS", block, str(hint))

    def test_no_block_when_nothing_due(self):
        s = default_sheet()
        block, due = due_elicit_block(
            s, mode="conversation", reason="default_conversation",
        )
        self.assertEqual(block, "")
        self.assertEqual(due, [])

    def test_fake_clock_injectable(self):
        s = default_sheet()
        s = enqueue(s, "gracias", "lexicon", today=D0)
        block, _ = due_elicit_block(
            s, mode="conversation", reason="default_conversation", today=D0,
        )
        self.assertEqual(block, "")
        block, _ = due_elicit_block(
            s, mode="conversation", reason="default_conversation",
            today=D0 + datetime.timedelta(days=2),
        )
        self.assertIn("gracias", block)


if __name__ == "__main__":
    unittest.main()
