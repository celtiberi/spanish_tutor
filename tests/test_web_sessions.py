"""Session-reset race + orphan reaper (web_app), 2026-07-28 forensics.

Incident: /api/session/reset raced the client's startSession → the stale
cookie minted a second session and the first leaked with no session_end
(session 20260728-120331). Server rules under test:
  - reset FULLY replaces the session (every other live session is closed);
  - _get_or_create with a DEAD cookie closes unreachable orphans first;
  - sessions idle 2h are reaped with a real close().
No LLM calls: ConversationalSession is monkeypatched with a fake.
"""

import time
import unittest

from tutor import web_app


class FakeTurn:
    error = None
    stop_reason = "end_turn"

    def to_dict(self):
        return {"reply": "¡Hola!", "notes": [], "parts": {}, "usage": {}}


class FakeSession:
    def __init__(self, *args, **kwargs):
        self.closed = False
        self.close_calls = 0
        self.persisted = None
        self.sheet_path = None
        self.sheet = {}
        self.history = []
        self.messages_for_ui = []
        self.model = "fake-model"
        self.debug_requests = []
        self.costs = None
        self._focus_panel = None
        self._focus_key = None

    def open_session(self):
        return FakeTurn()

    def user_turn(self, *a, **k):
        return FakeTurn()

    def sheet_public(self):
        return {"skills": {}}

    def reset_sheet(self):
        self.sheet = {}
        return self.sheet

    def reset_profile(self):
        return {}

    def close(self, *, persist_sheet=True):
        self.closed = True
        self.close_calls += 1
        self.persisted = persist_sheet
        return None


class _WebSessionsBase(unittest.TestCase):
    def setUp(self):
        self._saved_sessions = dict(web_app._sessions)
        self._saved_cls = web_app.ConversationalSession
        web_app._sessions.clear()
        web_app.ConversationalSession = FakeSession

    def tearDown(self):
        web_app.ConversationalSession = self._saved_cls
        web_app._sessions.clear()
        web_app._sessions.update(self._saved_sessions)

    def _put(self, sid, *, touched=None, opened=True):
        sess = FakeSession()
        web_app._sessions[sid] = {
            "session": sess,
            "touched": time.time() if touched is None else touched,
            "opened": opened,
        }
        return sess


class TestOrphanReaper(_WebSessionsBase):
    def test_idle_two_hours_gets_closed_and_dropped(self):
        stale = self._put("stale", touched=time.time() - web_app.IDLE_REAP_SEC - 60)
        fresh = self._put("fresh")
        web_app._purge_stale()
        self.assertNotIn("stale", web_app._sessions)
        self.assertTrue(stale.closed)  # session_end written via close()
        self.assertIn("fresh", web_app._sessions)
        self.assertFalse(fresh.closed)

    def test_idle_under_threshold_survives(self):
        young = self._put("young", touched=time.time() - 60 * 30)  # 30 min
        web_app._purge_stale()
        self.assertIn("young", web_app._sessions)
        self.assertFalse(young.closed)


class TestGetOrCreateTolerant(_WebSessionsBase):
    def test_live_sid_returns_same_session(self):
        sess = self._put("live-sid")
        sid, got = web_app._get_or_create("live-sid")
        self.assertEqual(sid, "live-sid")
        self.assertIs(got, sess)
        self.assertFalse(sess.closed)

    def test_dead_cookie_reaps_orphans_before_creating(self):
        orphan = self._put("orphan-sid")
        sid, got = web_app._get_or_create("dead-cookie-sid")
        self.assertNotEqual(sid, "dead-cookie-sid")
        self.assertEqual(len(web_app._sessions), 1)
        self.assertIn(sid, web_app._sessions)
        self.assertTrue(orphan.closed)  # closed, not silently leaked

    def test_no_cookie_does_not_kill_other_sessions(self):
        # curl-style call with NO cookie must not destroy a live session
        # (the 2h reaper owns that class of leak).
        other = self._put("other-sid")
        sid, _ = web_app._get_or_create(None)
        self.assertEqual(len(web_app._sessions), 2)
        self.assertFalse(other.closed)


class TestResetStartSequence(_WebSessionsBase):
    def _client(self):
        from fastapi.testclient import TestClient

        return TestClient(web_app.app)

    def test_reset_then_start_yields_one_live_session(self):
        # The incident shape: the browser holds a DEAD cookie and another
        # session object is still live in the map (the raced create).
        # Cookies ride explicit headers (httpx jar conflicts on same-name
        # cookies across domains); Set-Cookie is asserted on the response.
        orphan = self._put("raced-orphan")
        client = self._client()

        r = client.post(
            "/api/session/reset",
            json={"reset_sheet": False},
            headers={"Cookie": f"{web_app.COOKIE}=long-dead-sid"},
        )
        self.assertEqual(r.status_code, 200)
        # Full replace: exactly ONE live session; the orphan got a close().
        self.assertEqual(len(web_app._sessions), 1)
        self.assertTrue(orphan.closed)
        new_sid = r.json()["session_id"]
        self.assertIn(new_sid, web_app._sessions)
        # Response carries the new sid cookie for the client
        self.assertIn(new_sid, r.headers.get("set-cookie", ""))

        client.cookies.clear()
        r2 = client.post(
            "/api/session/start",
            json={"fresh": True},
            headers={"Cookie": f"{web_app.COOKIE}={new_sid}"},
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(len(web_app._sessions), 1)  # still ONE live session

    def test_reset_closes_cookie_session_and_orphans(self):
        mine = self._put("my-sid")
        other = self._put("other-sid")
        client = self._client()
        r = client.post(
            "/api/session/reset",
            json={"reset_sheet": False},
            headers={"Cookie": f"{web_app.COOKIE}=my-sid"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(mine.closed)
        self.assertTrue(mine.persisted)  # keep sheet on plain new-chat reset
        self.assertTrue(other.closed)
        self.assertEqual(len(web_app._sessions), 1)


if __name__ == "__main__":
    unittest.main()
