"""Progress journey ledger + emit wiring (docs/design-progression-view.md).

The design under test is the proposal AS AMENDED by Grok's countersign
(adjudicated 2026-07-28). Honesty laws asserted here (PEDAGOGY.md §3, §3.2):
- append-only history; polarity=down regressions are first-class events;
- an up-crossing fires ONCE per (kind, key);
- NO milestone without its code-owned evidence event;
- no mastery-language copy below the known band ("You can" only at known;
  "rooted" is durable SO FAR, never forever);
- the live-state join flags celebrated bands the sheet no longer supports
  (needs_recheck), never silent permanence;
- ledger/scheduler writes never move confidence/status (allowlist intact).
"""

import datetime
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tutor import progress_ledger as pl
from tutor.character_sheet import ERROR_PATTERN_HEALTHY_STREAK, default_sheet
from tutor.conv_session import ConversationalSession, emit_progress_events
from tutor.retrieval_scheduler import (
    mark_introduced,
    record_outcome,
    record_outcome_ex,
)

D0 = datetime.date(2026, 7, 1)
T0 = datetime.datetime(2026, 7, 1, 12, 0, tzinfo=datetime.timezone.utc)

BANNED_SUB_KNOWN_COPY = ("you can", "yours", "forever", "mastered", "fixed")


class LedgerBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "progress.jsonl"
        self._old_env = os.environ.get("PROGRESS_LEDGER_PATH")
        os.environ["PROGRESS_LEDGER_PATH"] = str(self.path)

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop("PROGRESS_LEDGER_PATH", None)
        else:
            os.environ["PROGRESS_LEDGER_PATH"] = self._old_env
        self._tmp.cleanup()

    def _lines(self):
        if not self.path.exists():
            return []
        return [
            json.loads(l)
            for l in self.path.read_text(encoding="utf-8").splitlines()
            if l.strip()
        ]


class TestLedgerCore(LedgerBase):
    def test_append_only_polarity_and_injected_clock(self):
        e1 = pl.record_milestone(
            "planted", "bote", "Met «bote»", session_id="s1",
            item_kind="lexicon", ledger_path=self.path, now=T0,
        )
        self.assertEqual(e1["polarity"], "up")
        first_raw = self.path.read_text(encoding="utf-8")
        e2 = pl.record_regression(
            "regression", "bote", "reset", session_id="s1",
            item_kind="lexicon", ledger_path=self.path,
            now=T0 + datetime.timedelta(minutes=5),
        )
        self.assertEqual(e2["polarity"], "down")
        lines = self._lines()
        self.assertEqual(len(lines), 2)
        # Append-only: the first line is byte-identical after the second write
        self.assertTrue(
            self.path.read_text(encoding="utf-8").startswith(first_raw)
        )
        self.assertEqual(lines[0]["ts"], T0.isoformat())
        self.assertEqual(lines[1]["kind"], "regression")

    def test_programmer_errors_raise(self):
        with self.assertRaises(ValueError):
            pl.record_milestone("session_kept", "x", ledger_path=self.path)
        with self.assertRaises(ValueError):
            pl.record_milestone(
                "regression", "x", polarity="up", ledger_path=self.path
            )
        with self.assertRaises(ValueError):
            pl.record_milestone("planted", "  ", ledger_path=self.path)

    def test_dedupe_queries(self):
        pl.record_milestone("taking_root", "bote", ledger_path=self.path, now=T0)
        pl.record_regression("regression", "bote", ledger_path=self.path, now=T0)
        self.assertTrue(
            pl.has_milestone("taking_root", "bote", ledger_path=self.path)
        )
        self.assertFalse(
            pl.has_milestone("rooted", "bote", ledger_path=self.path)
        )
        keys = pl.up_keys(self.path)
        self.assertIn(("taking_root", "bote"), keys)
        # Down events never satisfy up-dedupe
        self.assertNotIn(("regression", "bote"), keys)

    def test_read_recent_clusters_by_session_newest_first(self):
        pl.record_milestone(
            "planted", "bote", session_id="sA", ledger_path=self.path, now=T0
        )
        pl.record_milestone(
            "task_complete", "scene1", session_id="sA",
            ledger_path=self.path, now=T0 + datetime.timedelta(minutes=10),
        )
        pl.record_milestone(
            "planted", "leche", session_id="sB", ledger_path=self.path,
            now=T0 + datetime.timedelta(days=1),
        )
        clusters = pl.read_recent(ledger_path=self.path)
        self.assertEqual(len(clusters), 2)
        self.assertEqual(clusters[0]["session_id"], "sB")
        a = clusters[1]
        self.assertEqual([e["key"] for e in a["events"]], ["bote", "scene1"])
        self.assertEqual(a["summary"], {"planted": 1, "task_complete": 1})
        # limit_clusters
        only = pl.read_recent(ledger_path=self.path, limit_clusters=1)
        self.assertEqual(len(only), 1)
        self.assertEqual(only[0]["session_id"], "sB")
        # limit_days with injected today: only sB's day survives a 1-day window
        recent = pl.read_recent(
            ledger_path=self.path, limit_days=1,
            today=(T0 + datetime.timedelta(days=1)).astimezone().date(),
        )
        self.assertEqual([c["session_id"] for c in recent], ["sB"])


class TestLadderCrossings(LedgerBase):
    def _walk_to_interval(self, sheet, key, target_days):
        """Perfect on-schedule successes until interval reaches target."""
        day = D0
        transitions = []
        while True:
            entry = (sheet.get("lexicon") or {}).get(key) or {}
            interval = int(entry.get("interval_days") or 1)
            day = day + datetime.timedelta(days=interval)
            sheet, tr = record_outcome_ex(sheet, key, "lexicon", True, today=day)
            transitions.append(tr)
            if tr["interval_after"] >= target_days:
                return sheet, transitions, day

    def test_fake_clock_ladder_fires_each_crossing_once(self):
        s = default_sheet()
        s = mark_introduced(s, "bote", "lexicon", "image", today=D0)
        conf_before = json.dumps((s["lexicon"]["bote"].get("confidence"),
                                  s["lexicon"]["bote"].get("status")))
        seen = set()
        fired = []
        s, transitions, day = self._walk_to_interval(s, "bote", 14)
        for tr in transitions:
            for ev in pl.ladder_crossings(tr, seen=seen):
                fired.append(ev["kind"])
                seen.add((ev["kind"], ev["key"]))
        # Exactly one taking_root and one rooted over the whole climb
        self.assertEqual(fired, ["taking_root", "rooted"])
        # §3.2: the entire ladder never moved ability fields
        conf_after = json.dumps((s["lexicon"]["bote"].get("confidence"),
                                 s["lexicon"]["bote"].get("status")))
        self.assertEqual(conf_before, conf_after)
        # Re-running a crossing against `seen` re-fires nothing (dedupe law)
        again = pl.ladder_crossings(transitions[1], seen=seen)
        self.assertEqual(again, [])

    def test_fail_after_root_emits_regression_down(self):
        s = default_sheet()
        s = mark_introduced(s, "bote", "lexicon", "image", today=D0)
        s, transitions, day = self._walk_to_interval(s, "bote", 14)
        s, tr = record_outcome_ex(
            s, "bote", "lexicon", False,
            today=day + datetime.timedelta(days=14),
        )
        evs = pl.ladder_crossings(tr, seen={("taking_root", "bote"), ("rooted", "bote")})
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["kind"], "regression")
        self.assertEqual(evs[0]["polarity"], "down")
        # After the reset (interval 1) another fail is NOT a fresh regression
        s, tr2 = record_outcome_ex(
            s, "bote", "lexicon", False,
            today=day + datetime.timedelta(days=15),
        )
        self.assertEqual(pl.ladder_crossings(tr2, seen=set()), [])

    def test_record_outcome_compat_wrapper(self):
        s = default_sheet()
        s = mark_introduced(s, "bote", "lexicon", "image", today=D0)
        out = record_outcome(s, "bote", "lexicon", True, today=D0)
        self.assertIsInstance(out, dict)
        self.assertEqual(out["lexicon"]["bote"]["interval_days"], 1)


class TestSheetCrossings(LedgerBase):
    def _err(self, count, streak):
        return {"count": count, "resolved_streak": streak, "label": "yo estoy"}

    def _skill(self, conf, status):
        return {"confidence": conf, "status": status}

    def test_error_recovered_at_healthy_gate_only(self):
        prev = {"error_patterns": {"p1": self._err(0, 2)}}
        cur = {"error_patterns": {"p1": self._err(0, ERROR_PATTERN_HEALTHY_STREAK)}}
        evs = pl.sheet_crossings(prev, cur, seen=set())
        self.assertEqual([e["kind"] for e in evs], ["error_recovered"])
        self.assertEqual(evs[0]["key"], "p1")
        # Residual count blocks recovery (amended (a): streak>=3 AND count==0)
        cur_bad = {"error_patterns": {"p1": self._err(1, 5)}}
        self.assertEqual(pl.sheet_crossings(prev, cur_bad, seen=set()), [])
        # Already-healthy prev state is history, not a fresh milestone
        self.assertEqual(pl.sheet_crossings(cur, cur, seen=set()), [])
        # Ledger dedupe
        self.assertEqual(
            pl.sheet_crossings(prev, cur, seen={("error_recovered", "p1")}), []
        )

    def test_can_do_emerging_crossing(self):
        prev = {"skills": {"IP-03": self._skill(0.5, "fragile")}}
        cur = {"skills": {"IP-03": self._skill(0.6, "emerging")}}
        evs = pl.sheet_crossings(prev, cur, seen=set())
        self.assertEqual([e["kind"] for e in evs], ["can_do_emerging"])
        # A negative band at the same confidence is not celebrated
        cur_frag = {"skills": {"IP-03": self._skill(0.6, "fragile")}}
        self.assertEqual(pl.sheet_crossings(prev, cur_frag, seen=set()), [])
        # No crossing → no event
        self.assertEqual(pl.sheet_crossings(cur, cur, seen=set()), [])

    def test_can_do_known_needs_status_change(self):
        prev = {"skills": {"IP-03": self._skill(0.78, "emerging")}}
        cur = {"skills": {"IP-03": self._skill(0.85, "known")}}
        evs = pl.sheet_crossings(prev, cur, seen=set())
        self.assertEqual([e["kind"] for e in evs], ["can_do_known"])
        # Sub-known band never mints the known milestone
        cur_e = {"skills": {"IP-03": self._skill(0.85, "emerging")}}
        self.assertEqual(
            [e["kind"] for e in pl.sheet_crossings(prev, cur_e, seen=set())],
            [],
        )

    def test_no_milestone_without_evidence_event(self):
        """The honesty test: introduction alone and unchanged high bands
        must mint NOTHING."""
        s = default_sheet()
        before = json.loads(json.dumps(s))
        after = mark_introduced(s, "bote", "lexicon", "image", today=D0)
        self.assertEqual(pl.sheet_crossings(before, after, seen=set()), [])
        rich = {
            "skills": {"IP-03": self._skill(0.9, "known")},
            "error_patterns": {"p1": self._err(0, 5)},
        }
        self.assertEqual(pl.sheet_crossings(rich, rich, seen=set()), [])


class TestDisplayCopyHonesty(unittest.TestCase):
    def test_no_mastery_copy_below_known_band(self):
        details = {
            "planted": pl.detail_for("planted", "bote", scaffold="image"),
            "taking_root": pl.detail_for("taking_root", "bote", interval=3),
            "rooted": pl.detail_for("rooted", "bote"),
            "regression": pl.detail_for("regression", "bote", was=14),
            "error_recovered": pl.detail_for(
                "error_recovered", "p1", label="yo estoy", streak=3
            ),
            "can_do_emerging": pl.detail_for("can_do_emerging", "IP-03"),
            "task_complete": pl.detail_for("task_complete", "scene1", desc="x"),
        }
        for kind, text in details.items():
            low = text.lower()
            for banned in BANNED_SUB_KNOWN_COPY:
                self.assertNotIn(
                    banned, low,
                    f"{kind} detail uses mastery copy {banned!r}: {text}",
                )
        # Band-true copy pins
        self.assertIn("not yet knowledge", details["planted"])
        self.assertIn("so far", details["rooted"])
        self.assertIn("starting to land", details["can_do_emerging"])

    def test_known_band_owns_mastery_language(self):
        text = pl.detail_for("can_do_known", "IP-03")
        self.assertTrue(text.startswith("You can "))
        self.assertIn("known", text)


class TestPayloadAndJoin(LedgerBase):
    def _seed_ledger(self):
        pl.record_milestone("planted", "bote", item_kind="lexicon",
                            session_id="s1", ledger_path=self.path, now=T0)
        pl.record_milestone("taking_root", "bote", item_kind="lexicon",
                            session_id="s1", ledger_path=self.path, now=T0)
        pl.record_milestone("rooted", "bote", item_kind="lexicon",
                            session_id="s1", ledger_path=self.path, now=T0)
        pl.record_milestone("error_recovered", "p1", item_kind="error_pattern",
                            session_id="s1", ledger_path=self.path, now=T0)
        pl.record_milestone("can_do_known", "IP-03", item_kind="skill",
                            session_id="s1", ledger_path=self.path, now=T0)

    def test_needs_recheck_join_and_counts(self):
        self._seed_ledger()
        # Live sheet no longer supports any celebrated band
        sheet = {
            "lexicon": {"bote": {"interval_days": 1, "next_due": "2026-06-30"}},
            "skills": {
                "IP-03": {"status": "emerging", "confidence": 0.6},
                "IP-01": {"status": "known", "confidence": 0.9},
            },
            "error_patterns": {"p1": {"count": 1, "resolved_streak": 0}},
        }
        payload = pl.build_progress_payload(
            sheet, session_id="s1", ledger_path=self.path, today=D0,
        )
        for k in ("clusters", "counts", "due_soon", "session_id", "empty", "score"):
            self.assertIn(k, payload)
        self.assertFalse(payload["empty"])
        nodes = {e["kind"]: e for c in payload["clusters"] for e in c["events"]}
        # History stays; downgraded bands carry the quiet badge
        self.assertTrue(nodes["taking_root"]["needs_recheck"])
        self.assertTrue(nodes["rooted"]["needs_recheck"])
        self.assertTrue(nodes["error_recovered"]["needs_recheck"])
        self.assertTrue(nodes["can_do_known"]["needs_recheck"])
        # Encounter history claims nothing about ability — never badged
        self.assertFalse(nodes["planted"]["needs_recheck"])
        # Countable header: regressed root is NOT durable; strict sheet bands
        self.assertEqual(payload["counts"]["durable"], 0)
        self.assertEqual(payload["counts"]["known"], 1)
        self.assertEqual(payload["counts"]["emerging"], 1)
        # Informational due footer (next_due in the past at D0+)
        self.assertGreaterEqual(payload["due_soon"], 1)

    def test_durable_counts_when_live_state_holds(self):
        self._seed_ledger()
        sheet = {
            "lexicon": {"bote": {"interval_days": 14}},
            "skills": {"IP-03": {"status": "known", "confidence": 0.85}},
            "error_patterns": {
                "p1": {"count": 0,
                       "resolved_streak": ERROR_PATTERN_HEALTHY_STREAK}
            },
        }
        payload = pl.build_progress_payload(
            sheet, ledger_path=self.path, today=D0,
        )
        self.assertEqual(payload["counts"]["durable"], 1)
        nodes = {e["kind"]: e for c in payload["clusters"] for e in c["events"]}
        self.assertFalse(nodes["rooted"]["needs_recheck"])
        self.assertFalse(nodes["can_do_known"]["needs_recheck"])
        self.assertFalse(nodes["error_recovered"]["needs_recheck"])

    def test_empty_payload(self):
        payload = pl.build_progress_payload({}, ledger_path=self.path)
        self.assertTrue(payload["empty"])
        self.assertEqual(payload["clusters"], [])
        self.assertEqual(payload["counts"],
                         {"durable": 0, "known": 0, "emerging": 0})


class TestEmitWiring(LedgerBase):
    """Exercises the real conv_session emit helpers (unbound, fake self) so
    the wiring under test is the shipped code, not a re-implementation."""

    def _fake(self, sheet=None):
        return SimpleNamespace(progress_session_id="sess-1",
                               sheet=sheet or {})

    def test_progress_note_dedupes_once_per_key(self):
        fake = self._fake()
        n1 = ConversationalSession._progress_note(
            fake, "planted", "bote", item_kind="lexicon",
            detail_ctx={"scaffold": "image"},
        )
        self.assertEqual(n1, ["progress_milestone:planted:bote"])
        n2 = ConversationalSession._progress_note(
            fake, "planted", "bote", item_kind="lexicon",
        )
        self.assertEqual(n2, [])
        lines = self._lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["session_id"], "sess-1")

    def test_progress_ladder_emits_and_dedupes(self):
        fake = self._fake()
        tr = {"key": "bote", "kind": "lexicon", "success": True,
              "interval_before": 1, "interval_after": 3}
        n1 = ConversationalSession._progress_ladder(fake, tr)
        self.assertEqual(n1, ["progress_milestone:taking_root:bote"])
        # The same crossing NEVER fires twice (ledger-side dedupe)
        n2 = ConversationalSession._progress_ladder(fake, tr)
        self.assertEqual(n2, [])

    def test_progress_ladder_regression_note(self):
        fake = self._fake()
        tr = {"key": "bote", "kind": "lexicon", "success": False,
              "interval_before": 14, "interval_after": 1}
        notes = ConversationalSession._progress_ladder(fake, tr)
        self.assertEqual(notes, ["progress_regression:regression:bote"])
        self.assertEqual(self._lines()[0]["polarity"], "down")

    def test_progress_sheet_crossings_wiring(self):
        prev = {"skills": {"IP-03": {"confidence": 0.5, "status": "fragile"}}}
        cur = {"skills": {"IP-03": {"confidence": 0.6, "status": "emerging"}}}
        fake = self._fake(sheet=cur)
        notes = ConversationalSession._progress_sheet_crossings(fake, prev)
        self.assertEqual(notes, ["progress_milestone:can_do_emerging:IP-03"])

    def test_emit_progress_events_tags(self):
        notes = emit_progress_events(
            [{"kind": "task_complete", "key": "scene1", "polarity": "up",
              "item_kind": "task", "detail": "Task done: x"}],
            session_id="sess-1", ledger_path=self.path,
        )
        self.assertEqual(notes, ["progress_milestone:task_complete:scene1"])


if __name__ == "__main__":
    unittest.main()
