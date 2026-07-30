"""Phase 1 — SessionState aggregate + reset-coverage census as code.

docs/reviews-architecture-refactor.md (Phase 1, Grok amendment (a)).
Batch 1 pinned the aggregate WITHOUT behavior change; batch 2 landed the
DECLARED deltas — this file's diff is the review artifact. Pinned now:

1. ``SessionState.fresh`` builds every store/attribute exactly the way the
   pre-aggregate ``ConversationalSession.__init__`` block did (including
   phase-plan equivalence with ``build_session_phase_state``).
2. Unified ``reset(kind)``: "new_chat" / "sheet_reset" reset EVERY
   session-scoped field (``UNIFIED_RESET``); "open_session" is a deprecated
   alias for "new_chat"; "full" replays construction; unknown kinds raise.
   Costs ruling: the per-chat tracker resets (the on-disk cost ledger is
   append-only forever). The phase plan is rebuilt from the CURRENT sheet.
3. The delegate properties keep the historical attribute surface working
   (including the ``__new__`` partial-session escape used by
   tests/test_debug_requests.py).
4. RESET_COVERAGE characterization: each production reset path resets
   exactly the fields the table documents — the new-chat LEAK CLOSURE
   (intro budget / asked_topics / cooldowns / phase clock / task state must
   NOT survive a new chat) is asserted through the real web endpoint.
5. Progress-ledger epoch (declared delta 3): ``reset_sheet`` appends a
   learner-epoch mark; the same milestone key re-mints for the fresh
   learner; display keeps both sides with the boundary row.
6. E2 ruling (WIRED): ``snapshot()`` / ``from_snapshot()`` round-trip —
   the documented persistence surface for future server-restart resume.
"""

from __future__ import annotations

import json
import time

import pytest

from tutor.character_sheet import default_sheet
from tutor.session_state import (
    DEBUG_RING_SIZE,
    RESET_COVERAGE,
    SESSION_STATE_FIELDS,
    UNIFIED_RESET,
    SessionState,
)

SENTINEL_TOPIC = "size:__sentinel__"
SENTINEL_TASK = object()


def _fresh_state(**over) -> SessionState:
    kw = {
        "source_label": "unittest",
        "pack_topics": ["Comida", "Viaje"],
        "due_count": 0,
        "blank": True,
    }
    kw.update(over)
    return SessionState.fresh(default_sheet(), **kw)


# ---------------------------------------------------------------------------
# 1. fresh()
# ---------------------------------------------------------------------------


class TestFresh:
    def test_builds_every_field_with_init_defaults(self):
        st = _fresh_state()
        assert st.history == []
        assert st.messages_for_ui == []
        assert st.focus_panel is None
        assert st.focus_key is None
        assert st.focus_meta == {"source": "static"}
        assert st.focus_version == 0
        assert st.focus_inflight is False
        assert st.focus_lock is not st.image_warm_lock
        assert st.image_warm_inflight == set()
        assert st.last_plan is None
        assert st.pedagogy_memory.turns == 0
        assert st.pedagogy_memory.sheet_seeded is False
        assert st.mode_state.learner_turn_index == 0
        assert st.task_state is None
        assert st.last_mode_decision is None
        assert st.debug_requests.maxlen == DEBUG_RING_SIZE
        assert len(st.debug_requests) == 0
        assert st.costs.source == "unittest"
        assert st.progress_session_id == ""

    def test_phase_plan_identical_to_conv_session_builder(self):
        """fresh() must build the SAME plan build_session_phase_state built
        pre-aggregate (same sheet, same pack)."""
        from tutor import config
        from tutor.conv_session import build_session_phase_state
        from tutor.corpus import pack_topic_titles
        from tutor.pedagogy_contract import is_blank_learner
        from tutor.retrieval_scheduler import due_items

        sheet = default_sheet()
        pack_dir = config.DEFAULT_PACK_DIR
        st = SessionState.fresh(
            sheet,
            source_label="unittest",
            pack_topics=pack_topic_titles(pack_dir),
            due_count=len(due_items(sheet)),
            blank=is_blank_learner(sheet),
        )
        expected = build_session_phase_state(sheet, pack_dir)
        assert st.phase_state.snapshot() == expected.snapshot()


# ---------------------------------------------------------------------------
# 2. reset("full")
# ---------------------------------------------------------------------------


def _mutate_everything(st: SessionState) -> dict[str, int]:
    """Sentinel-mutate every aggregate field; return pre-mutation ids."""
    ids = {f: id(getattr(st, f)) for f in SESSION_STATE_FIELDS}
    st.pedagogy_memory.asked_topics.add(SENTINEL_TOPIC)
    st.pedagogy_memory.turns = 99
    st.mode_state.english_only_streak = 77
    st.phase_state.frozen_turns = 55
    st.task_state = SENTINEL_TASK
    st.costs._by_category["__sentinel__"] = {"usd": 0.0}
    st.focus_panel = {"__sentinel__": True}
    st.focus_key = "__sentinel__"
    st.focus_meta = {"source": "__sentinel__"}
    st.focus_version = 44
    st.focus_inflight = True
    st.image_warm_inflight.add("__sentinel__")
    st.last_mode_decision = {"mode": "__sentinel__"}
    st.last_plan = {"plan": "__sentinel__"}
    st.debug_requests.append({"marker": "__sentinel__"})
    st.progress_session_id = "__sentinel__"
    st.history = [{"role": "user", "content": "__sentinel__"}]
    st.messages_for_ui = [{"role": "you", "content": "__sentinel__"}]
    return ids


class TestResetFull:
    def test_replays_construction_exactly(self):
        st = _fresh_state(source_label="resetter")
        twin = _fresh_state(source_label="resetter")
        pre_ids = _mutate_everything(st)
        st.reset("full")

        assert st.history == []
        assert st.messages_for_ui == []
        assert st.focus_panel is None
        assert st.focus_key is None
        assert st.focus_meta == {"source": "static"}
        assert st.focus_version == 0
        assert st.focus_inflight is False
        assert st.image_warm_inflight == set()
        assert st.last_plan is None
        assert st.last_mode_decision is None
        assert st.task_state is None
        assert st.progress_session_id == ""
        # Stores are RECONSTRUCTED (construction replay), not scrubbed
        for f in ("pedagogy_memory", "mode_state", "phase_state",
                  "debug_requests", "costs", "focus_lock",
                  "image_warm_lock"):
            assert id(getattr(st, f)) != pre_ids[f], f
        assert SENTINEL_TOPIC not in st.pedagogy_memory.asked_topics
        assert st.pedagogy_memory.turns == 0
        assert st.mode_state.english_only_streak == 0
        assert st.phase_state.snapshot() == twin.phase_state.snapshot()
        assert len(st.debug_requests) == 0
        assert st.debug_requests.maxlen == DEBUG_RING_SIZE
        assert st.costs.source == "resetter"
        assert "__sentinel__" not in st.costs._by_category

    def test_unknown_kind_raises(self):
        st = _fresh_state()
        for kind in ("nonsense", "", "partial"):
            with pytest.raises(ValueError):
                st.reset(kind)


# ---------------------------------------------------------------------------
# 2b. Unified reset kinds (Phase 1 batch 2 declared delta 1)
# ---------------------------------------------------------------------------


KEPT_ON_UNIFIED_RESET = frozenset(SESSION_STATE_FIELDS) - UNIFIED_RESET


class TestUnifiedResetKinds:
    def test_kept_fields_are_locks_and_progress_id_only(self):
        assert KEPT_ON_UNIFIED_RESET == {
            "focus_lock", "image_warm_lock", "progress_session_id",
        }

    @pytest.mark.parametrize(
        "kind",
        ["new_chat", "new-chat", "sheet_reset", "sheet-reset",
         "open_session", "open-session"],
    )
    def test_unified_kinds_reset_everything_except_kept(self, kind):
        """new_chat / sheet_reset (and the deprecated open_session alias,
        both spellings) reset EVERY session-scoped field; the two runtime
        locks stay the same objects and progress_session_id is preserved
        (learner scope rotates via the ledger epoch, not the session id)."""
        st = _fresh_state(source_label="unify")
        pre_ids = _mutate_everything(st)
        st.reset(kind)

        for f in SESSION_STATE_FIELDS:
            if f in KEPT_ON_UNIFIED_RESET:
                continue
            assert _was_reset(f, st, pre_ids), (kind, f)
        # Kept: same lock objects, same (sentinel) progress_session_id
        assert id(st.focus_lock) == pre_ids["focus_lock"]
        assert id(st.image_warm_lock) == pre_ids["image_warm_lock"]
        assert st.progress_session_id == "__sentinel__"
        # Costs ruling: fresh per-chat tracker, same source label
        assert id(st.costs) != pre_ids["costs"]
        assert st.costs.source == "unify"
        # The batch-1 four misses, now covered
        assert st.focus_version == 0
        assert st.focus_inflight is False
        assert st.image_warm_inflight == set()

    def test_leak_class_closed_at_unit_level(self):
        """The census leak fields: intro budget, asked_topics, cooldowns,
        phase clock, task state — all fresh after new_chat."""
        st = _fresh_state()
        st.pedagogy_memory.introduced_this_session.extend(["hola", "pan"])
        st.pedagogy_memory.asked_topics.add("size:ciudad")
        st.mode_state.form_focus_cooldown["weather_hace"] = 3
        st.mode_state.content_uptake_last_turn = 4
        st.mode_state.learner_turn_index = 6
        st.phase_state.index = 2
        st.phase_state.turns_in_phase = 1
        from tutor.task_runtime import TaskState

        st.task_state = TaskState(scene_id="boat_likes")
        st.reset("new_chat")
        assert st.pedagogy_memory.intro_budget_remaining() == 2
        assert st.pedagogy_memory.asked_topics == set()
        assert st.mode_state.form_focus_cooldown == {}
        assert st.mode_state.content_uptake_last_turn == -999
        assert st.mode_state.learner_turn_index == 0
        assert st.phase_state.index == 0
        assert st.phase_state.turns_in_phase == 0
        assert st.task_state is None

    def test_phase_plan_rebuilt_from_current_sheet(self):
        """A new chat on a LEARNED sheet must rebuild the phase plan from
        that sheet (due count / blank flag recomputed), not replay the
        construction-time inputs."""
        from tutor.pedagogy_contract import is_blank_learner
        from tutor.retrieval_scheduler import due_items

        st = _fresh_state()  # blank construction-time sheet
        blank_snapshot = st.phase_state.snapshot()

        learned = default_sheet()
        learned["lexicon"]["pan"] = {
            "status": "fragile", "confidence": 0.4, "first_seen": "2026-07-01",
            "introduced_at": "2026-07-01", "next_due": "2026-07-02",
            "interval_days": 1, "successive_successes": 0,
        }
        learned["skills"]["IP-01"] = {"status": "known", "confidence": 0.9}
        assert not is_blank_learner(learned)
        assert len(due_items(learned)) == 1

        st.reset("new_chat", sheet=learned)
        twin = SessionState.fresh(
            learned,
            source_label="unittest",
            pack_topics=["Comida", "Viaje"],
            due_count=len(due_items(learned)),
            blank=is_blank_learner(learned),
        )
        assert st.phase_state.snapshot() == twin.phase_state.snapshot()
        assert st.phase_state.snapshot() != blank_snapshot
        # The remembered args updated: a later plain reset replays the
        # learned sheet, not the stale construction-time one.
        st.reset("new_chat")
        assert st.phase_state.snapshot() == twin.phase_state.snapshot()


# ---------------------------------------------------------------------------
# 2c. E2 ruling — snapshot()/from_snapshot() round-trip (WIRED, not deleted)
# ---------------------------------------------------------------------------


def _restore_kwargs() -> dict:
    return {
        "sheet": default_sheet(),
        "source_label": "unittest",
        "pack_topics": ["Comida", "Viaje"],
        "due_count": 0,
        "blank": True,
    }


class TestSnapshotRoundTrip:
    def _worked_state(self) -> SessionState:
        from tutor.task_runtime import TaskState

        st = _fresh_state()
        st.history = [
            {"role": "user", "content": "(session open)"},
            {"role": "assistant", "content": "¡Hola!"},
        ]
        st.messages_for_ui = [
            {"role": "tutor", "content": "¡Hola!", "input_mode": "text"},
        ]
        st.focus_panel = {"focus": {"title": "Greetings"}}
        st.focus_key = "abc123"
        st.focus_meta = {"source": "ai"}
        st.focus_version = 7
        st.last_plan = {"phase": "new_input"}
        st.last_mode_decision = {"mode": "conversation", "reason": "flow"}
        st.progress_session_id = "20260728-web"
        # memory — including the fields snapshot() alone omits
        m = st.pedagogy_memory
        m.note_learner("Estoy bien, gracias")
        m.note_asked_topic("size", "ciudad")
        m.note_introduced("hola")
        m.note_tutor_turn(model="**Hola**", try_="Di: hola",
                          acknowledge="¡Muy bien!", concepts=["hola"])
        m.images_generated = 2
        m.declared_image_cooldown = 1
        m.sheet_seeded = True
        # mode state — including the aggregate-only extras
        s = st.mode_state
        s.tick()
        s.tick()
        s.note_error_hits(["weather_hace"])
        s.set_cooldown("weather_hace", 3)
        s.note_content_uptake()
        s.english_only_streak = 1
        s.open_scene_ids = ["boat_meet_captain"]
        # phase progressed + a bound task
        st.phase_state.tick(consumed=True)
        st.phase_state.tick(consumed=False)
        st.task_state = TaskState(
            scene_id="boat_likes", slots_filled={"item": "pan"},
            turns_on_task=2,
        )
        return st

    def test_round_trip_snapshot_equality(self):
        st = self._worked_state()
        snap = st.snapshot()
        restored = SessionState.from_snapshot(snap, **_restore_kwargs())
        assert restored.snapshot() == snap

    def test_snapshot_is_json_serializable(self):
        import json

        json.dumps(self._worked_state().snapshot())

    def test_lossy_store_fields_survive_via_aggregate(self):
        """The per-store snapshot() shapes are pinned by prompt/debug
        consumers; the aggregate carries their omissions as sibling keys."""
        st = self._worked_state()
        restored = SessionState.from_snapshot(st.snapshot(), **_restore_kwargs())
        m = restored.pedagogy_memory
        assert m.last_learner == "Estoy bien, gracias"
        assert m.last_tutor_ack == "¡Muy bien!"
        assert m.images_generated == 2
        assert m.declared_image_cooldown == 1
        ms = restored.mode_state
        assert ms.learner_turn_index == 2
        assert ms.last_error_hit_turn == {"weather_hace": 2}
        assert ms.content_uptake_last_turn == 2
        # phase restored from the snapshot, not rebuilt
        assert restored.phase_state.index == st.phase_state.index
        assert restored.phase_state.frozen_turns == 1
        assert restored.task_state is not None
        assert restored.task_state.scene_id == "boat_likes"
        assert restored.task_state.slots_filled == {"item": "pan"}

    def test_excluded_runtime_fields_rebuilt_fresh(self):
        """Locks, inflight flags, debug ring and costs are excluded BY
        DESIGN (in-memory-only law / cost-ledger continuity ruling)."""
        st = self._worked_state()
        st.focus_inflight = True
        st.image_warm_inflight.add("hola")
        st.debug_requests.append({"marker": "x"})
        st.costs._by_category["tutor"] = {"usd": 1.0}
        snap = st.snapshot()
        for key in ("focus_inflight", "image_warm_inflight",
                    "debug_requests", "costs", "focus_lock",
                    "image_warm_lock"):
            assert key not in snap
        restored = SessionState.from_snapshot(snap, **_restore_kwargs())
        assert restored.focus_inflight is False
        assert restored.image_warm_inflight == set()
        assert len(restored.debug_requests) == 0
        assert restored.costs._by_category == {}


# ---------------------------------------------------------------------------
# 3. Delegate properties (source-compat surface)
# ---------------------------------------------------------------------------


class TestDelegates:
    def test_reads_and_writes_route_to_state(self, tutor_session):
        session = tutor_session.session
        assert session.pedagogy_memory is session.state.pedagogy_memory
        assert session.mode_state is session.state.mode_state
        assert session.phase_state is session.state.phase_state
        assert session.costs is session.state.costs
        assert session.debug_requests is session.state.debug_requests
        assert session._focus_lock is session.state.focus_lock
        assert session._image_warm_lock is session.state.image_warm_lock
        assert (
            session._image_warm_inflight
            is session.state.image_warm_inflight
        )
        # attribute write → aggregate field
        session.history = [{"role": "user", "content": "x"}]
        assert session.state.history == [{"role": "user", "content": "x"}]
        session._focus_version = 5
        assert session.state.focus_version == 5
        # aggregate write → attribute read
        session.state.last_plan = {"p": 1}
        assert session.last_plan == {"p": 1}

    def test_dunder_new_partial_sessions_keep_working(self):
        """tests/test_debug_requests.py builds sessions via __new__ and sets
        pedagogy_memory/debug_requests directly — the pre-aggregate escape."""
        from collections import deque

        from tutor.conv_session import ConversationalSession
        from tutor.session_memory import SessionMemory

        sess = ConversationalSession.__new__(ConversationalSession)
        with pytest.raises(AttributeError):
            sess.pedagogy_memory
        assert getattr(sess, "progress_session_id", "absent") == "absent"
        sess.pedagogy_memory = SessionMemory()
        sess.debug_requests = deque(maxlen=DEBUG_RING_SIZE)
        sess.pedagogy_memory.turns = 3
        assert sess.pedagogy_memory.turns == 3
        assert sess.debug_requests.maxlen == DEBUG_RING_SIZE


# ---------------------------------------------------------------------------
# 4. RESET_COVERAGE — census as code, characterized against today's paths
# ---------------------------------------------------------------------------


def _was_reset(field: str, st: SessionState, pre_ids: dict[str, int]) -> bool:
    """Did this aggregate field lose its sentinel (see _mutate_everything)?"""
    checks = {
        "pedagogy_memory": lambda: (
            SENTINEL_TOPIC not in st.pedagogy_memory.asked_topics
        ),
        "mode_state": lambda: st.mode_state.english_only_streak != 77,
        "phase_state": lambda: id(st.phase_state) != pre_ids["phase_state"],
        "task_state": lambda: st.task_state is not SENTINEL_TASK,
        "costs": lambda: "__sentinel__" not in st.costs._by_category,
        "focus_panel": lambda: st.focus_panel != {"__sentinel__": True},
        "focus_key": lambda: st.focus_key != "__sentinel__",
        "focus_meta": lambda: (
            (st.focus_meta or {}).get("source") != "__sentinel__"
        ),
        "focus_version": lambda: st.focus_version == 0,
        "focus_inflight": lambda: st.focus_inflight is False,
        "focus_lock": lambda: id(st.focus_lock) != pre_ids["focus_lock"],
        "image_warm_lock": lambda: (
            id(st.image_warm_lock) != pre_ids["image_warm_lock"]
        ),
        "image_warm_inflight": lambda: (
            "__sentinel__" not in st.image_warm_inflight
        ),
        "last_mode_decision": lambda: (
            st.last_mode_decision != {"mode": "__sentinel__"}
        ),
        "last_plan": lambda: st.last_plan != {"plan": "__sentinel__"},
        "debug_requests": lambda: not any(
            isinstance(e, dict) and e.get("marker") == "__sentinel__"
            for e in st.debug_requests
        ),
        "progress_session_id": lambda: (
            st.progress_session_id != "__sentinel__"
        ),
        "history": lambda: st.history != [
            {"role": "user", "content": "__sentinel__"}
        ],
        "messages_for_ui": lambda: st.messages_for_ui != [
            {"role": "you", "content": "__sentinel__"}
        ],
    }
    return checks[field]()


def _assert_coverage(kind: str, st: SessionState, pre_ids: dict) -> None:
    entry = RESET_COVERAGE[kind]
    for f in SESSION_STATE_FIELDS:
        if f in entry["churn"]:
            continue  # non-reset overwrite documented in the table
        want_reset = f in entry["current"]
        got_reset = _was_reset(f, st, pre_ids)
        assert got_reset == want_reset, (
            f"{kind}: field {f!r} {'was' if got_reset else 'was NOT'} reset "
            f"but RESET_COVERAGE says {'reset' if want_reset else 'keep'} — "
            "if the change is DELIBERATE (batch 2), update the table AND "
            "this characterization in the same commit"
        )


class TestCoverageTableShape:
    def test_kinds_and_fields(self):
        assert set(RESET_COVERAGE) == {
            "fresh", "new-chat", "sheet-reset", "open-session",
        }
        allf = set(SESSION_STATE_FIELDS)
        for kind, entry in RESET_COVERAGE.items():
            assert set(entry["current"]) <= allf, kind
            assert set(entry["churn"]) <= allf, kind
            assert set(entry["pre_batch2"]) <= allf, kind
            assert entry["ruling"], kind  # every kind records its ruling
        assert set(RESET_COVERAGE["fresh"]["current"]) == allf

    def test_unified_coverage_landed(self):
        """Batch 2's visible diff: the three partial kinds now share the
        UNIFIED coverage (everything except locks + progress_session_id)."""
        for kind in ("new-chat", "sheet-reset", "open-session"):
            assert RESET_COVERAGE[kind]["current"] == UNIFIED_RESET, kind
        assert UNIFIED_RESET == (
            frozenset(SESSION_STATE_FIELDS)
            - {"focus_lock", "image_warm_lock", "progress_session_id"}
        )

    def test_pre_batch2_audit_trail(self):
        """The batch-1 census (5 paths / 5 subsets bug class) preserved as
        the audit trail of exactly what the unification changed."""
        assert RESET_COVERAGE["new-chat"]["pre_batch2"] == frozenset({
            "history", "messages_for_ui", "focus_panel", "focus_key",
            "costs",
        })
        assert RESET_COVERAGE["open-session"]["pre_batch2"] == frozenset({
            "costs", "history", "messages_for_ui",
        })
        assert len(RESET_COVERAGE["sheet-reset"]["pre_batch2"]) == 12


class TestCoverageCharacterization:
    def test_sheet_reset_path(self, tutor_session_factory):
        ctx = tutor_session_factory()
        session = ctx.session
        pre_ids = _mutate_everything(session.state)
        pre_deque_id = id(session.state.debug_requests)
        session.reset_sheet()
        _assert_coverage("sheet-reset", session.state, pre_ids)
        # Batch-2 semantics: EVERY store reconstructed as a new object —
        # including the debug ring (batch 1 cleared it in place).
        assert id(session.state.debug_requests) != pre_deque_id
        assert id(session.state.pedagogy_memory) != pre_ids["pedagogy_memory"]
        assert id(session.state.mode_state) != pre_ids["mode_state"]
        assert id(session.state.costs) != pre_ids["costs"]
        assert session.state.focus_version == 0
        # Declared delta 3: the learner-epoch mark landed in the (isolated)
        # progress ledger, tagged with the kept progress_session_id.
        lines = [
            json.loads(l)
            for l in ctx.progress_path.read_text().splitlines() if l.strip()
        ]
        assert [e["kind"] for e in lines] == ["epoch"]
        assert lines[0]["key"] == "learner"
        assert lines[0]["session_id"] == "__sentinel__"  # id preserved

    def test_open_session_path(self, tutor_session_factory, monkeypatch):
        """open_session on a LIVE object = the deprecated 'open_session'
        alias = full new_chat semantics (batch 2 closed the 3-store
        residual)."""
        from tutor.conv_session import TurnResult

        ctx = tutor_session_factory()
        session = ctx.session
        # Isolate open_session's RESET actions from turn execution (turn
        # effects — memory ticks, focus repaint, debug capture — are the
        # goldens' business, not the census's).
        monkeypatch.setattr(
            session,
            "_execute_planned",
            lambda learner, **kw: TurnResult(reply="¡Hola!"),
        )
        pre_ids = _mutate_everything(session.state)
        result = session.open_session()
        assert not result.error
        _assert_coverage("open-session", session.state, pre_ids)
        # Batch-2 semantics: memory RECONSTRUCTED (new object), THEN seeded
        # from the durable sheet (new chat ≠ new learner); transcript
        # replaced with the open pair.
        assert id(session.state.pedagogy_memory) != pre_ids["pedagogy_memory"]
        assert session.pedagogy_memory.sheet_seeded is True
        assert session.state.focus_version == 0
        assert session.history == [
            {"role": "user", "content": "(session open)"},
            {"role": "assistant", "content": "¡Hola!"},
        ]

    def test_new_chat_web_resume_path(self, tutor_session_factory, monkeypatch):
        """LEAK CLOSURE (batch-2 declared delta 1) through the REAL
        endpoint: the resume branch of /api/session/start routes through
        SessionState.reset('new_chat') — intro budget, asked_topics,
        cooldowns, phase clock, task state, debug ring and per-chat costs
        are ALL fresh; the sheet and progress_session_id survive."""
        from fastapi.testclient import TestClient

        from tutor import web_app
        from tutor.conv_session import TurnResult

        ctx = tutor_session_factory()
        session = ctx.session
        monkeypatch.setattr(
            session,
            "_execute_planned",
            lambda learner, **kw: TurnResult(reply="¡Hola!"),
        )
        pre_ids = _mutate_everything(session.state)
        # The census leak class, seeded explicitly (budget/topics/cooldowns)
        session.pedagogy_memory.introduced_this_session.extend(
            ["hola", "pan"])
        session.mode_state.form_focus_cooldown["weather_hace"] = 3

        saved = dict(web_app._sessions)
        web_app._sessions.clear()
        web_app._sessions["nc-sid"] = {
            "session": session,
            "touched": time.time(),
            "opened": True,
        }
        try:
            client = TestClient(web_app.app)
            r = client.post(
                "/api/session/start",
                json={"fresh": False, "resume": True},
                headers={"Cookie": f"{web_app.COOKIE}=nc-sid"},
            )
            assert r.status_code == 200
            assert r.json()["session_id"] == "nc-sid"  # same live session
        finally:
            web_app._sessions.clear()
            web_app._sessions.update(saved)

        _assert_coverage("new-chat", session.state, pre_ids)
        # Churn column, pinned: the same-response sheet_public() repaint
        # rewrote focus_meta and re-bumped focus_version AFTER the reset —
        # from 0, not from the sentinel 44.
        assert 0 <= session.state.focus_version < 44
        assert (session.state.focus_meta or {}).get("source") != "__sentinel__"
        # THE LEAK, CLOSED — batch 1 pinned every one of these surviving:
        assert SENTINEL_TOPIC not in session.pedagogy_memory.asked_topics
        assert session.pedagogy_memory.intro_budget_remaining() == 2
        assert session.mode_state.english_only_streak == 0
        assert session.mode_state.form_focus_cooldown == {}
        assert id(session.phase_state) != pre_ids["phase_state"]
        assert session.phase_state.index == 0
        assert session.task_state is None
        # Kept on purpose: same live session id for the progress rail
        assert session.progress_session_id == "__sentinel__"
        # New chat ≠ new learner: reconstructed memory re-seeded from sheet
        assert session.pedagogy_memory.sheet_seeded is True

    def test_fresh_path(self, tutor_session_factory):
        """__init__ IS the fresh kind: a factory session's aggregate matches
        SessionState.fresh output (all fields covered by construction)."""
        ctx = tutor_session_factory(label="freshcheck")
        st = ctx.session.state
        assert st.costs.source == "freshcheck"
        assert st.debug_requests.maxlen == DEBUG_RING_SIZE
        assert st.history == [] and st.messages_for_ui == []
        assert st.task_state is None and st.last_plan is None
        # progress_session_id assigned post-logger (log=False → "-nolog")
        assert st.progress_session_id.endswith("-freshcheck-nolog")


# ---------------------------------------------------------------------------
# 5. Progress-ledger learner epoch through the SESSION API (declared delta 3)
# ---------------------------------------------------------------------------


class TestLearnerEpochThroughSession:
    def test_plant_reset_replant_reminits(self, tutor_session_factory):
        """plant → sheet_reset → the SAME key plants again for the fresh
        learner (dedupe scope rotated by the epoch mark, nothing
        retracted); the ledger keeps all three rows (append-only)."""
        from tutor import progress_ledger as pl

        ctx = tutor_session_factory()
        session = ctx.session

        notes1 = session._progress_note(
            "planted", "hola", item_kind="lexicon",
            detail_ctx={"scaffold": "gloss"},
        )
        assert notes1 == ["progress_milestone:planted:hola"]
        # Dedupe holds within the learner's scope
        assert session._progress_note(
            "planted", "hola", item_kind="lexicon") == []
        assert pl.has_milestone("planted", "hola")

        session.reset_sheet()

        # Fresh learner: the previous learner's milestone no longer
        # suppresses the crossing …
        assert not pl.has_milestone("planted", "hola")
        assert ("planted", "hola") not in pl.up_keys()
        # … and the same key genuinely re-mints.
        notes2 = session._progress_note(
            "planted", "hola", item_kind="lexicon",
            detail_ctx={"scaffold": "gloss"},
        )
        assert notes2 == ["progress_milestone:planted:hola"]
        assert pl.has_milestone("planted", "hola")

        lines = [
            json.loads(l)
            for l in ctx.progress_path.read_text().splitlines() if l.strip()
        ]
        assert [e["kind"] for e in lines] == ["planted", "epoch", "planted"]

    def test_display_shows_only_the_fresh_epoch(
        self, tutor_session_factory
    ):
        """History is real ON DISK (append-only: planted/epoch/planted all
        remain raw, pinned above); the DISPLAY shows the current epoch only
        (2026-07-29 concept rail: a state view must not present pre-reset
        events as the reset learner's current truth — the day view's
        boundary row died with the day view)."""
        from tutor import progress_ledger as pl

        ctx = tutor_session_factory()
        session = ctx.session
        session._progress_note("planted", "hola", item_kind="lexicon")
        session.reset_sheet()
        session._progress_note("planted", "hola", item_kind="lexicon")

        nodes = pl.concept_nodes(ledger_path=ctx.progress_path)
        assert [(n["kind"], n["key"]) for n in nodes] == [("planted", "hola")]

        payload = pl.build_progress_payload(
            session.sheet, ledger_path=ctx.progress_path
        )
        items = [n for g in payload["groups"] for n in g["items"]]
        assert [n["kind"] for n in items] == ["planted"]
        # one node for the re-planted item, counting only this epoch
        assert items[0]["events_count"] == 1
