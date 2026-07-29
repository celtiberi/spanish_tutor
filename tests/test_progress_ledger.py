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


class TestRetraction(LedgerBase):
    """Honesty correction path (2026-07-28 false-planted incident): retract
    voids the pair for display AND dedupe; raw lines stay (append-only);
    sheet correction clears ONLY introduce fields, never ability fields."""

    def test_retract_excludes_pair_from_display_and_dedupe(self):
        pl.record_milestone(
            "planted", "buenas tardes", "Met «buenas tardes»",
            session_id="s1", item_kind="lexicon",
            ledger_path=self.path, now=T0,
        )
        pl.record_milestone(
            "planted", "hola", session_id="s1", item_kind="lexicon",
            ledger_path=self.path, now=T0,
        )
        pl.record_retraction(
            "planted", "buenas tardes",
            "Retracted planted «buenas tardes» — flawed key-presence rule",
            session_id="corr", item_kind="lexicon",
            ledger_path=self.path, now=T0 + datetime.timedelta(hours=1),
        )
        # Append-only law: all three raw lines remain on disk
        self.assertEqual(len(self._lines()), 3)
        # Display: neither the false milestone nor the correction row shows
        clusters = pl.read_recent(ledger_path=self.path)
        shown = [
            (e["kind"], e["key"]) for c in clusters for e in c["events"]
        ]
        self.assertNotIn(("planted", "buenas tardes"), shown)
        self.assertNotIn(("retracted", "buenas tardes"), shown)
        self.assertIn(("planted", "hola"), shown)
        # Dedupe: the voided milestone is re-earnable
        self.assertFalse(
            pl.has_milestone("planted", "buenas tardes", ledger_path=self.path)
        )
        self.assertNotIn(("planted", "buenas tardes"), pl.up_keys(self.path))
        # The correction itself remains a queryable fact
        self.assertTrue(
            pl.has_milestone(
                "retracted", "buenas tardes",
                polarity="down", ledger_path=self.path,
            )
        )
        # A later GENUINE introduction re-mints cleanly
        pl.record_milestone(
            "planted", "buenas tardes", session_id="s2", item_kind="lexicon",
            ledger_path=self.path, now=T0 + datetime.timedelta(days=2),
        )
        self.assertTrue(
            pl.has_milestone("planted", "buenas tardes", ledger_path=self.path)
        )

    def test_retraction_validation(self):
        with self.assertRaises(ValueError):
            pl.record_milestone(  # retracted must be polarity down
                "retracted", "x", polarity="up", retracts="planted",
                ledger_path=self.path,
            )
        with self.assertRaises(ValueError):
            pl.record_retraction("nope", "x", ledger_path=self.path)
        with self.assertRaises(ValueError):
            pl.record_milestone(  # retracts illegal off kind=retracted
                "planted", "x", retracts="planted", ledger_path=self.path,
            )

    def test_retract_introduction_clears_sheet_fields_only(self):
        from tutor.retrieval_scheduler import retract_introduction

        sheet = default_sheet()
        # Key WITH real use evidence: introduce fields cleared, ability kept
        sheet["lexicon"]["hola"] = {
            "status": "emerging", "confidence": 0.4, "solid_uses": 1,
        }
        sheet = mark_introduced(sheet, "hola", "lexicon", "keyword", today=D0)
        # Key with NO evidence: mark created the honest-zero shell
        sheet = mark_introduced(
            sheet, "buenas tardes", "lexicon", "keyword", today=D0
        )
        out = retract_introduction(sheet, "hola", "lexicon")
        out = retract_introduction(out, "buenas tardes", "lexicon")
        entry = out["lexicon"]["hola"]
        for f in ("introduced_at", "scaffold", "next_due", "interval_days",
                  "successive_successes"):
            self.assertNotIn(f, entry)
        # Confidence untouched (honesty law)
        self.assertEqual(entry["confidence"], 0.4)
        self.assertEqual(entry["status"], "emerging")
        self.assertEqual(entry["solid_uses"], 1)
        # The evidence-free shell is removed entirely (pre-introduce state)
        self.assertNotIn("buenas tardes", out["lexicon"])
        # Absent entry → no-op, no crash
        out2 = retract_introduction(out, "no-such-key", "lexicon")
        self.assertNotIn("no-such-key", out2["lexicon"])


class TestLearnerEpoch(LedgerBase):
    """Learner-epoch scope rotation (Phase 1 batch 2 declared delta 3,
    docs/reviews-architecture-refactor.md): sheet_reset appends an epoch
    mark; has_milestone/up_keys only consider events AFTER the latest mark
    (fresh learner re-mints, nothing retracted — nothing was false);
    display keeps pre-epoch history with the boundary row visible;
    retraction filtering is unaffected."""

    def test_epoch_rotates_dedupe_scope_and_reminits(self):
        pl.record_milestone(
            "planted", "bote", session_id="s1", item_kind="lexicon",
            ledger_path=self.path, now=T0,
        )
        self.assertTrue(pl.has_milestone("planted", "bote", ledger_path=self.path))
        ev = pl.record_epoch(
            session_id="s1", ledger_path=self.path,
            now=T0 + datetime.timedelta(hours=1),
        )
        self.assertEqual(ev["kind"], "epoch")
        self.assertEqual(ev["polarity"], "epoch")
        # Dedupe scope rotated: the crossing is re-earnable …
        self.assertFalse(pl.has_milestone("planted", "bote", ledger_path=self.path))
        self.assertEqual(pl.up_keys(self.path), set())
        # … and genuinely re-mints for the fresh learner.
        pl.record_milestone(
            "planted", "bote", session_id="s2", item_kind="lexicon",
            ledger_path=self.path, now=T0 + datetime.timedelta(hours=2),
        )
        self.assertTrue(pl.has_milestone("planted", "bote", ledger_path=self.path))
        self.assertIn(("planted", "bote"), pl.up_keys(self.path))
        # Append-only: all three raw lines remain
        self.assertEqual(
            [e["kind"] for e in self._lines()], ["planted", "epoch", "planted"]
        )
        # Only the LATEST epoch scopes: a second mark re-voids the scope
        pl.record_epoch(
            ledger_path=self.path, now=T0 + datetime.timedelta(hours=3)
        )
        self.assertFalse(pl.has_milestone("planted", "bote", ledger_path=self.path))

    def test_display_keeps_history_and_shows_boundary(self):
        pl.record_milestone(
            "planted", "bote", session_id="s1", item_kind="lexicon",
            ledger_path=self.path, now=T0,
        )
        pl.record_epoch(
            session_id="s1", ledger_path=self.path,
            now=T0 + datetime.timedelta(hours=1),
        )
        pl.record_milestone(
            "planted", "bote", session_id="s2", item_kind="lexicon",
            ledger_path=self.path, now=T0 + datetime.timedelta(hours=2),
        )
        days = pl.read_recent_days(ledger_path=self.path)
        self.assertEqual(len(days), 1)
        self.assertEqual(
            [e["kind"] for e in days[0]["events"]],
            ["planted", "epoch", "planted"],
        )
        payload = pl.build_progress_payload(
            default_sheet(), ledger_path=self.path
        )
        events = payload["clusters"][0]["events"]
        epoch_rows = [e for e in events if e["kind"] == "epoch"]
        self.assertEqual(len(epoch_rows), 1)
        self.assertEqual(epoch_rows[0]["display_state"], "boundary")
        self.assertEqual(
            epoch_rows[0]["display"], "Fresh start — progress reset"
        )

    def test_retraction_filtering_unaffected_by_epoch(self):
        # False plant, retracted; then an epoch; then a genuine plant.
        pl.record_milestone(
            "planted", "leche", session_id="s1", item_kind="lexicon",
            ledger_path=self.path, now=T0,
        )
        pl.record_retraction(
            "planted", "leche", "Retracted planted «leche» — test incident",
            ledger_path=self.path, now=T0 + datetime.timedelta(minutes=10),
        )
        pl.record_epoch(
            ledger_path=self.path, now=T0 + datetime.timedelta(minutes=20),
        )
        pl.record_milestone(
            "planted", "leche", session_id="s2", item_kind="lexicon",
            ledger_path=self.path, now=T0 + datetime.timedelta(minutes=30),
        )
        # The retracted pre-epoch pair never displays; the post-epoch plant
        # does; the correction stays a queryable fact (raw lines).
        shown = [
            (e["kind"], e["key"], e["session_id"])
            for c in pl.read_recent(ledger_path=self.path)
            for e in c["events"]
            if e["kind"] != "epoch"
        ]
        self.assertEqual(shown, [("planted", "leche", "s2")])
        self.assertTrue(
            pl.has_milestone(
                "retracted", "leche", polarity="down", ledger_path=self.path
            )
        )
        self.assertTrue(pl.has_milestone("planted", "leche", ledger_path=self.path))

    def test_epoch_is_not_a_milestone_kind(self):
        # Emit sites can never mint an epoch as a milestone …
        with self.assertRaises(ValueError):
            pl.record_milestone("epoch", "learner", ledger_path=self.path)
        # … and a retraction can never target one (nothing false to retract).
        with self.assertRaises(ValueError):
            pl.record_retraction("epoch", "learner", ledger_path=self.path)


class TestGroupingAndDisplayState(LedgerBase):
    """Rail grouping + single-state law (2026-07-28 rail incident): nodes
    cluster by association-table theme; skills → Abilities, tasks → Tasks,
    non-table keys → other; a node shows exactly ONE state."""

    TABLE = {
        "buenos días": {"theme": "greetings"},
        "buenas tardes": {"theme": "greetings"},
        "leche": {"theme": "drinks"},
    }

    def test_grouping_payload_shape(self):
        for key in ("buenos días", "buenas tardes"):
            pl.record_milestone(
                "planted", key, session_id="s1", item_kind="lexicon",
                ledger_path=self.path, now=T0,
            )
        pl.record_milestone(
            "can_do_known", "IP-01", session_id="s1", item_kind="skill",
            ledger_path=self.path, now=T0,
        )
        pl.record_milestone(
            "task_complete", "scene1", session_id="s1", item_kind="task",
            ledger_path=self.path, now=T0,
        )
        pl.record_milestone(
            "planted", "zzz-off-table", session_id="s1", item_kind="lexicon",
            ledger_path=self.path, now=T0,
        )
        payload = pl.build_progress_payload(
            {"skills": {"IP-01": {"status": "known", "confidence": 0.9}}},
            session_id="s1", table=self.TABLE,
            ledger_path=self.path, today=D0,
        )
        (cluster,) = payload["clusters"]
        groups = {g["theme"]: g for g in cluster["groups"]}
        self.assertEqual(
            set(groups), {"greetings", "abilities", "tasks", "other"}
        )
        g = groups["greetings"]
        self.assertEqual(g["label"], "Greetings")
        self.assertEqual(g["summary"], {"planted": 2})
        self.assertEqual(
            [e["key"] for e in g["events"]],
            ["buenos días", "buenas tardes"],
        )
        self.assertEqual(groups["abilities"]["label"], "Abilities")
        self.assertEqual(
            [e["key"] for e in groups["abilities"]["events"]], ["IP-01"]
        )
        self.assertEqual(groups["tasks"]["label"], "Tasks")
        self.assertEqual(
            [e["key"] for e in groups["other"]["events"]], ["zzz-off-table"]
        )
        # Flat events retained for compat; every event carries display_state
        self.assertEqual(len(cluster["events"]), 5)
        for e in cluster["events"]:
            self.assertIn(
                e["display_state"], ("celebrated", "recheck", "down")
            )

    def test_single_state_per_node(self):
        # Celebrated band the live sheet no longer supports → recheck ONLY
        ev = {"kind": "can_do_known", "key": "IP-01", "polarity": "up",
              "item_kind": "skill", "needs_recheck": True}
        self.assertEqual(pl.display_state(ev), "recheck")
        # Live state supports → celebrated (no badge)
        ev2 = dict(ev, needs_recheck=False)
        self.assertEqual(pl.display_state(ev2), "celebrated")
        # Down events are never celebrated and never badged
        ev3 = {"kind": "regression", "key": "bote", "polarity": "down",
               "needs_recheck": False}
        self.assertEqual(pl.display_state(ev3), "down")
        # Payload path: the IP-01 case verbatim — known event, reset sheet
        pl.record_milestone(
            "can_do_known", "IP-01", session_id="s1", item_kind="skill",
            ledger_path=self.path, now=T0,
        )
        payload = pl.build_progress_payload(
            {"skills": {"IP-01": {"status": "unknown", "confidence": 0.0}}},
            session_id="s1", ledger_path=self.path, today=D0,
        )
        (node,) = payload["clusters"][0]["events"]
        self.assertTrue(node["needs_recheck"])
        self.assertEqual(node["display_state"], "recheck")


class TestDayClustering(LedgerBase):
    """Day clustering (2026-07-28 journey-rail incident): the visual unit is
    the LOCAL calendar day — sessions within a day merge into one cluster;
    events keep session_id for tooltip/debug; midnight splits clusters."""

    LOCAL_TZ = datetime.datetime.now().astimezone().tzinfo

    def test_two_sessions_same_local_day_one_cluster(self):
        t1 = datetime.datetime(2026, 7, 1, 10, 0, tzinfo=self.LOCAL_TZ)
        pl.record_milestone(
            "planted", "hola", session_id="sA", item_kind="lexicon",
            ledger_path=self.path, now=t1,
        )
        pl.record_milestone(
            "planted", "adiós", session_id="sB", item_kind="lexicon",
            ledger_path=self.path, now=t1 + datetime.timedelta(minutes=5),
        )
        clusters = pl.read_recent_days(ledger_path=self.path)
        self.assertEqual(len(clusters), 1)
        c = clusters[0]
        self.assertEqual(c["date"], "2026-07-01")
        self.assertEqual(c["sessions"], ["sA", "sB"])
        self.assertEqual(c["session_count"], 2)
        # Sessions merged, chronological; each event keeps its session_id
        self.assertEqual(
            [(e["key"], e["session_id"]) for e in c["events"]],
            [("hola", "sA"), ("adiós", "sB")],
        )
        self.assertEqual(c["summary"], {"planted": 2})

    def test_cross_midnight_two_clusters_newest_first(self):
        t1 = datetime.datetime(2026, 7, 1, 23, 50, tzinfo=self.LOCAL_TZ)
        t2 = t1 + datetime.timedelta(minutes=20)  # crosses local midnight
        pl.record_milestone(
            "planted", "hola", session_id="sNight", item_kind="lexicon",
            ledger_path=self.path, now=t1,
        )
        pl.record_milestone(
            "planted", "adiós", session_id="sNight", item_kind="lexicon",
            ledger_path=self.path, now=t2,
        )
        clusters = pl.read_recent_days(ledger_path=self.path)
        self.assertEqual(len(clusters), 2)
        self.assertEqual(
            [c["date"] for c in clusters], ["2026-07-02", "2026-07-01"]
        )
        # Same session on both sides of midnight — day wins, session recorded
        for c in clusters:
            self.assertEqual(c["sessions"], ["sNight"])
            self.assertEqual(len(c["events"]), 1)

    def test_payload_uses_day_clusters(self):
        t1 = datetime.datetime(2026, 7, 1, 10, 0, tzinfo=self.LOCAL_TZ)
        for sid, key in (("sA", "hola"), ("sB", "adiós")):
            pl.record_milestone(
                "planted", key, session_id=sid, item_kind="lexicon",
                ledger_path=self.path, now=t1,
            )
        payload = pl.build_progress_payload(
            {}, session_id="sB", ledger_path=self.path, today=D0,
        )
        (c,) = payload["clusters"]
        self.assertEqual(c["date"], "2026-07-01")
        self.assertEqual(c["session_count"], 2)
        self.assertIn("sB", c["sessions"])


class TestHumanization(LedgerBase):
    """Humanized display names (2026-07-28 rail incident: raw keys and
    "Theme — N planted" rows said nothing): lexicon → the Spanish + gloss;
    can-do id → statement snippet (mastery frame ONLY at known); task →
    scene goal; unknown key → raw key fallback. Derived, never invented."""

    TABLE = {"hola": {"gloss_en": "hi / hello", "theme": "greetings"}}

    def test_lexicon_display_is_spanish_with_gloss(self):
        out = pl.humanize_event(
            {"kind": "planted", "key": "hola", "item_kind": "lexicon"},
            self.TABLE,
        )
        self.assertEqual(out["display"], "hola")
        self.assertEqual(out["gloss"], "hi / hello")

    def test_unknown_key_raw_fallback(self):
        out = pl.humanize_event(
            {"kind": "planted", "key": "zzz-off-table", "item_kind": "lexicon"},
            self.TABLE,
        )
        self.assertEqual(out["display"], "zzz-off-table")
        self.assertEqual(out["gloss"], "")
        # Unknown can-do id also falls back to the raw key
        self.assertEqual(
            pl.can_do_display("XX-99", "can_do_known"), "XX-99"
        )

    def test_can_do_statement_snippet_and_band_copy(self):
        # Real can_dos.py statement: "I can greet a peer and respond to a
        # simple greeting." — shortened sensibly, no id soup.
        self.assertEqual(
            pl.can_do_display("IP-01", "can_do_known"), "Can greet a peer"
        )
        # Sub-known band never wears the mastery frame ("Can ...")
        emerging = pl.can_do_display("IP-01", "can_do_emerging")
        self.assertEqual(emerging, "Greet a peer")
        self.assertFalse(emerging.lower().startswith("can "))

    def test_task_display_is_scene_goal(self):
        goals = {"boat_meet_captain": "meet the captain"}
        out = pl.humanize_event(
            {"kind": "task_complete", "key": "boat_meet_captain",
             "item_kind": "task"},
            None, goals,
        )
        self.assertEqual(out["display"], "Meet the captain")
        # No goal known → raw key fallback
        out2 = pl.humanize_event(
            {"kind": "task_complete", "key": "mystery_scene",
             "item_kind": "task"},
            None, {},
        )
        self.assertEqual(out2["display"], "mystery_scene")

    def test_goal_short_derivation(self):
        self.assertEqual(
            pl._goal_short(
                "Info-gap task: the learner meets the captain and must find "
                "out the captain's name and how he is today."
            ),
            "meets the captain",
        )

    def test_payload_events_carry_display_fields(self):
        pl.record_milestone(
            "planted", "hola", session_id="s1", item_kind="lexicon",
            ledger_path=self.path, now=T0,
        )
        pl.record_milestone(
            "can_do_known", "IP-01", session_id="s1", item_kind="skill",
            ledger_path=self.path, now=T0,
        )
        payload = pl.build_progress_payload(
            {"skills": {"IP-01": {"status": "known", "confidence": 0.9}}},
            session_id="s1", table=self.TABLE,
            ledger_path=self.path, today=D0,
        )
        by_key = {
            e["key"]: e for c in payload["clusters"] for e in c["events"]
        }
        self.assertEqual(by_key["hola"]["display"], "hola")
        self.assertEqual(by_key["hola"]["gloss"], "hi / hello")
        self.assertEqual(by_key["IP-01"]["display"], "Can greet a peer")


class TestOperatorRetractionDisplay(LedgerBase):
    """2026-07-28 operator-pollution incident: milestones minted by agent
    verification chats are retracted via the append-only API — the raw lines
    (false milestone + correction) stay on disk, and NEITHER appears in the
    display payload; genuine learner events are untouched."""

    def test_operator_retractions_raw_present_display_absent(self):
        op = "20260728-999999-conversational-web"
        pl.record_milestone(
            "planted", "buenas noches", session_id=op, item_kind="lexicon",
            ledger_path=self.path, now=T0,
        )
        pl.record_milestone(
            "can_do_known", "IP-01", session_id=op, item_kind="skill",
            ledger_path=self.path, now=T0,
        )
        pl.record_milestone(
            "planted", "hola", session_id="learner-session",
            item_kind="lexicon", ledger_path=self.path, now=T0,
        )
        for target, key, ik in (
            ("planted", "buenas noches", "lexicon"),
            ("can_do_known", "IP-01", "skill"),
        ):
            pl.record_retraction(
                target, key,
                "operator-verification pollution — one-turn automation "
                "session, not the learner",
                session_id="correction-op", item_kind=ik,
                ledger_path=self.path,
                now=T0 + datetime.timedelta(hours=1),
            )
        # Raw ledger keeps all five lines (append-only law)
        raw = self._lines()
        self.assertEqual(len(raw), 5)
        self.assertEqual(
            sum(1 for e in raw if e["kind"] == "retracted"), 2
        )
        # Display payload shows ONLY the learner's genuine event
        payload = pl.build_progress_payload(
            {}, ledger_path=self.path, today=D0,
        )
        shown = [
            (e["kind"], e["key"])
            for c in payload["clusters"]
            for e in c["events"]
        ]
        self.assertEqual(shown, [("planted", "hola")])
        # Dedupe: the retracted milestones are honestly re-earnable
        self.assertNotIn(("planted", "buenas noches"), pl.up_keys(self.path))
        self.assertNotIn(("can_do_known", "IP-01"), pl.up_keys(self.path))


class TestProjectionContract(LedgerBase):
    """Phase 1.5 batch 2: ledger-projection pins (adjudicated (b) law).

    The progress ledger is a PROJECTION of selected machine crossings —
    machine A (retrieval_scheduler schedule axis) and machine B
    (character_sheet ability axis) own their sheet fields; the ledger NEVER
    writes either machine's fields, and every milestone kind maps to a
    named transition/crossing (mapping table in
    docs/reviews-architecture-refactor.md, Phase 1.5 batch 2 runbook).
    """

    def test_record_functions_take_no_sheet_and_write_none(self):
        import inspect

        for fn in (pl.record_milestone, pl.record_epoch, pl.record_retraction):
            self.assertNotIn("sheet", inspect.signature(fn).parameters)
        sheet = default_sheet()
        sheet["lexicon"]["hola"] = {
            "status": "emerging", "confidence": 0.4,
            "introduced_at": "2026-07-01", "next_due": "2026-07-05",
            "interval_days": 3, "successive_successes": 2,
        }
        before = json.loads(json.dumps(sheet))
        pl.record_milestone(
            "planted", "hola", item_kind="lexicon",
            ledger_path=self.path, now=T0,
        )
        pl.record_retraction(
            "planted", "hola", "projection-contract probe",
            ledger_path=self.path, now=T0,
        )
        pl.record_epoch(ledger_path=self.path, now=T0)
        self.assertEqual(sheet, before)
        self.assertEqual(len(self._lines()), 3)

    def test_projection_functions_never_mutate_inputs(self):
        sheet = default_sheet()
        sheet["lexicon"]["pan"] = {
            "status": "known", "confidence": 0.9, "solid_uses": 3,
            "interval_days": 14, "next_due": "2026-08-01",
        }
        prev = json.loads(json.dumps(sheet))
        cur = json.loads(json.dumps(sheet))
        cur["skills"]["IP-01"] = {"status": "known", "confidence": 0.9}
        prev_snap = json.loads(json.dumps(prev))
        cur_snap = json.loads(json.dumps(cur))
        pl.sheet_crossings(prev, cur, seen=set())
        self.assertEqual(prev, prev_snap)
        self.assertEqual(cur, cur_snap)
        tr = {
            "key": "pan", "kind": "lexicon", "success": True,
            "interval_before": 1, "interval_after": 3,
            "successes_before": 1, "successes_after": 2,
        }
        tr_snap = dict(tr)
        pl.ladder_crossings(tr, seen=set())
        self.assertEqual(tr, tr_snap)
        pl.record_milestone(
            "rooted", "pan", item_kind="lexicon",
            ledger_path=self.path, now=T0,
        )
        sheet_snap = json.loads(json.dumps(cur))
        pl.build_progress_payload(cur, ledger_path=self.path, today=D0)
        self.assertEqual(cur, sheet_snap)
        ev = {"kind": "rooted", "key": "pan", "item_kind": "lexicon"}
        pl.live_state_supports(ev, cur)
        self.assertEqual(cur, sheet_snap)

    def test_ledger_module_holds_no_machine_writer(self):
        """Namespace + import pin: the ledger never even references a
        machine writer (grep proof recorded in the runbook)."""
        import inspect
        import re as _re

        writers = (
            "save_sheet", "mark_introduced", "mark_first_seen", "enqueue",
            "record_outcome", "record_outcome_ex", "retract_introduction",
            "ability_transition", "apply_delta", "apply_rule_updates",
            "process_turn", "_bump_status", "_write",
        )
        for name in writers:
            self.assertFalse(
                hasattr(pl, name),
                f"progress_ledger must not hold writer {name!r}",
            )
        import_lines = [
            ln for ln in inspect.getsource(pl).splitlines()
            if _re.search(r"^\s*(from|import)\b", ln)
        ]
        for name in writers:
            for ln in import_lines:
                self.assertIsNone(
                    _re.search(rf"\b{name}\b", ln),
                    f"progress_ledger imports writer {name!r}: {ln!r}",
                )

    def test_kind_vocabulary_matches_mapping_table(self):
        """Every milestone kind has a named source (runbook mapping table)."""
        self.assertEqual(
            set(pl.KINDS),
            {
                "planted",          # machine A via="introduce"
                "taking_root",      # machine A outcome data: interval >= 3
                "rooted",           # machine A outcome data: interval >= 14
                "regression",       # machine A outcome fail from >= 3d
                "error_recovered",  # sheet healthy gate (count 0, streak >= 3)
                "can_do_emerging",  # machine B conf crossing (EMERGING_CONF)
                "can_do_known",     # machine B band edge * -> known
                "task_complete",    # task_runtime verdict (neither machine)
                "retracted",        # honesty correction (pairs machine A retract)
            },
        )
        # Threshold pins share the machines' constants — never softer.
        from tutor.character_sheet import EMERGING_MIN_CONF
        from tutor.retrieval_scheduler import INTERVAL_CAP_DAYS

        self.assertEqual(pl.EMERGING_CONF, EMERGING_MIN_CONF)
        self.assertEqual(pl.ROOTED_DAYS, INTERVAL_CAP_DAYS)
        self.assertEqual(pl.TAKING_ROOT_DAYS, 3)

    def test_planted_maps_to_introduce_transition(self):
        """planted ↔ machine A via="introduce" (absent/first_seen →
        on_ladder); the ability axis stays untouched (introduction is never
        knowledge) so sheet_crossings mints nothing from it."""
        from tutor.retrieval_scheduler import item_state, transition

        s = default_sheet()
        before = json.loads(json.dumps(s))
        s2, crossing = transition(
            s, "bote", "lexicon", to_state="on_ladder", via="introduce",
            evidence={"caller": "test"}, today=D0, scaffold="image",
        )
        self.assertEqual(crossing["via"], "introduce")
        self.assertEqual(crossing["from_state"], "absent")
        self.assertEqual(crossing["to_state"], "on_ladder")
        self.assertEqual(item_state(s2["lexicon"]["bote"]), "on_ladder")
        self.assertEqual(pl.sheet_crossings(before, s2, seen=set()), [])

    def test_ladder_kinds_map_to_outcome_crossings(self):
        """taking_root / rooted / regression ↔ machine A via="outcome"
        interval telemetry at the pinned thresholds."""
        s = default_sheet()
        s["lexicon"]["pan"] = {
            "status": "unknown", "confidence": 0.0,
            "next_due": D0.isoformat(), "interval_days": 1,
            "successive_successes": 1,
        }
        s2, tr = record_outcome_ex(s, "pan", "lexicon", True, today=D0)
        self.assertEqual((tr["interval_before"], tr["interval_after"]), (1, 3))
        evs = pl.ladder_crossings(tr, seen=set())
        self.assertEqual([e["kind"] for e in evs], ["taking_root"])
        s2["lexicon"]["pan"]["interval_days"] = 7
        s2["lexicon"]["pan"]["successive_successes"] = 3
        s3, tr = record_outcome_ex(s2, "pan", "lexicon", True, today=D0)
        self.assertEqual(tr["interval_after"], pl.ROOTED_DAYS)
        evs = pl.ladder_crossings(tr, seen={("taking_root", "pan")})
        self.assertEqual([e["kind"] for e in evs], ["rooted"])
        _s4, tr = record_outcome_ex(s3, "pan", "lexicon", False, today=D0)
        evs = pl.ladder_crossings(tr, seen=set())
        self.assertEqual(
            [(e["kind"], e["polarity"]) for e in evs],
            [("regression", "down")],
        )

    def test_can_do_known_is_the_band_edge(self):
        """can_do_known fires IFF ability_band crosses * → known (machine B
        edge), including out-of-vocabulary statuses (band unknown)."""
        from tutor.character_sheet import ability_band

        statuses = ("unknown", "emerging", "fragile", "known", "blocked",
                    "Known", "durable", "")
        for p_st in statuses:
            for c_st in statuses:
                prev = {"skills": {"IP-03": {
                    "confidence": 0.6, "status": p_st,
                }}}
                cur = {"skills": {"IP-03": {
                    "confidence": 0.85, "status": c_st,
                }}}
                evs = pl.sheet_crossings(prev, cur, seen=set())
                minted = "can_do_known" in [e["kind"] for e in evs]
                edge = (
                    ability_band(cur["skills"]["IP-03"]) == "known"
                    and ability_band(prev["skills"]["IP-03"]) != "known"
                )
                self.assertEqual(
                    minted, edge,
                    f"prev={p_st!r} cur={c_st!r}: crossing != band edge",
                )

    def test_error_recovered_maps_to_healthy_gate(self):
        """error_recovered ↔ the character_sheet healthy gate (count == 0
        AND resolved_streak >= ERROR_PATTERN_HEALTHY_STREAK), no other rule."""
        gate = ERROR_PATTERN_HEALTHY_STREAK
        prev = {"error_patterns": {"p1": {
            "count": 1, "resolved_streak": 0, "label": "x",
        }}}
        for count, streak, expect in (
            (0, gate, True),
            (0, gate - 1, False),
            (1, gate + 2, False),
        ):
            cur = {"error_patterns": {"p1": {
                "count": count, "resolved_streak": streak, "label": "x",
            }}}
            evs = pl.sheet_crossings(prev, cur, seen=set())
            self.assertEqual(
                "error_recovered" in [e["kind"] for e in evs], expect,
                f"count={count} streak={streak}",
            )


if __name__ == "__main__":
    unittest.main()
