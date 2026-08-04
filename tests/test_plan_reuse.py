"""Plan reuse (USER 2026-08-04): precreated blank plan + per-learner
plan persistence + recent-only grade rail + durable uid identity.

Session-level behavior (cached open turn skips the plan call) is verified
live against the running server — these are the unit contracts."""

import json
import tempfile
import unittest
from pathlib import Path

from tutor import config


class TestBlankPlanCache(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old = config.CHARACTER_SHEET_PATH
        config.CHARACTER_SHEET_PATH = Path(self._tmp.name) / "sheet.json"

    def tearDown(self):
        config.CHARACTER_SHEET_PATH = self._old
        self._tmp.cleanup()

    def test_roundtrip_and_stale_still_served(self):
        from tutor import plan_cache

        self.assertEqual(plan_cache.get_cached_blank_plan(), (None, False))
        plan_cache.store_blank_plan("LEARNER: blank\nGOALS: greet")
        self.assertEqual(
            plan_cache.get_cached_blank_plan(),
            ("LEARNER: blank\nGOALS: greet", True),
        )
        # USER ruling 2026-08-04: a server update means WE refresh the
        # cached plan (startup warm) — the request path never REJECTS
        # it. Stale ⇒ still served, flagged for the warm to regenerate.
        p = plan_cache._cache_path()
        d = json.loads(p.read_text())
        d["fingerprint"] = "stale-deploy"
        p.write_text(json.dumps(d))
        self.assertEqual(
            plan_cache.get_cached_blank_plan(),
            ("LEARNER: blank\nGOALS: greet", False),
        )

    def test_empty_plan_never_served(self):
        from tutor import plan_cache

        plan_cache.store_blank_plan("   ")
        self.assertEqual(plan_cache.get_cached_blank_plan(), (None, False))

    def test_fingerprint_is_clock_free(self):
        # 2026-08-04 incident: the formatted sheet embeds "now": <clock>,
        # so a fingerprint hashing it changed EVERY SECOND — the cache
        # could never hit after the moment it was stored and every blank
        # open paid a full plan turn (USER: "It still took forever").
        import time

        from tutor import plan_cache

        text = plan_cache._stable_default_sheet_text()
        self.assertNotIn('"now"', text)
        self.assertNotIn('"updated_at"', text)
        a = plan_cache.blank_plan_fingerprint()
        time.sleep(1.1)
        self.assertEqual(a, plan_cache.blank_plan_fingerprint())


class TestPlanStore(unittest.TestCase):
    def test_save_load_delete(self):
        from tutor import plan_store

        with tempfile.TemporaryDirectory() as tmp:
            sheet = Path(tmp) / "web-abc123.json"
            self.assertIsNone(plan_store.load_plan(sheet))
            plan_store.save_plan(sheet, "ARC: keep going")
            self.assertEqual(plan_store.load_plan(sheet), "ARC: keep going")
            # USER ruling 2026-08-04: a learner's stored plan is served
            # UNCONDITIONALLY — a code deploy does not change the
            # learner; <replan/> is the correction lever.
            p = plan_store._plan_path(sheet)
            d = json.loads(p.read_text())
            d["fingerprint"] = "old-deploy"
            p.write_text(json.dumps(d))
            self.assertEqual(plan_store.load_plan(sheet), "ARC: keep going")
            plan_store.delete_plan(sheet)
            self.assertIsNone(plan_store.load_plan(sheet))
            self.assertFalse(p.exists())


class TestRecentGradesFilter(unittest.TestCase):
    def test_old_rows_hidden_bad_ts_kept(self):
        import datetime

        from tutor.grade_log import _recent_only

        now = datetime.datetime.now(datetime.timezone.utc)
        fresh = {"ts": now.isoformat(), "field_id": "a"}
        old = {
            "ts": (now - datetime.timedelta(hours=48)).isoformat(),
            "field_id": "b",
        }
        # Unparseable clock must stay VISIBLE (hiding it would be a
        # silent drop — no-hide).
        broken = {"ts": "not-a-time", "field_id": "c"}
        out = _recent_only([fresh, old, broken], 24)
        self.assertEqual([r["field_id"] for r in out], ["a", "c"])


class TestUidCookie(unittest.TestCase):
    def _req(self, value):
        class R:
            cookies = {"ml_uid": value} if value is not None else {}

        return R()

    def test_valid_uid_kept_hostile_replaced(self):
        from tutor.web_app import _uid_for

        self.assertEqual(_uid_for(self._req("Ab1-_x")), "Ab1-_x")
        # Path traversal / injection attempts never reach a filename
        self.assertNotEqual(_uid_for(self._req("../../etc/passwd")),
                            "../../etc/passwd")
        self.assertNotEqual(_uid_for(self._req("a" * 200)), "a" * 200)
        fresh = _uid_for(self._req(None))
        self.assertGreaterEqual(len(fresh), 16)


if __name__ == "__main__":
    unittest.main()
