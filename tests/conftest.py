"""Phase 0 characterization harness (docs/reviews-architecture-refactor.md).

Batch 1 of the adjudicated Phase 0 spec (Grok round-1 (c) replacement text,
BINDING per the closing adjudication):

- ``FakeModelClient`` — an anthropic-SDK-shaped fake for the provider client
  surface ``conv_session`` actually uses (``client.messages.create(...)``
  returning an object with ``.content`` text blocks, ``.stop_reason`` and
  ``.usage``).  Scriptable canned <tutor> bodies, records every outbound
  request.  NO network, NO keys.
- ``tutor_session_factory`` / ``tutor_session`` — a REAL
  ``ConversationalSession`` against the fake client with fully isolated
  state (tmp sheet, tmp progress ledger, tmp cost ledger, tmp teach-asset
  cache, no session log, focus/classifier/image side rails off).
- Truncation-law guard — the fixture asserts every captured request carried
  FULL history / sheet / pack (docs/teacher-context-no-truncate.md); it runs
  automatically on teardown for every factory-built session.

Injection point: ``config.make_client_for`` is monkeypatched (the session
does ``self.client = config.make_client_for(self.model)`` in ``__init__``;
there is no constructor param).  Zero production-code changes.

Nothing here is autouse — the existing 553 leaf tests are untouched.
"""

from __future__ import annotations

import os  # noqa: E402  (env clamp must precede any tutor import)

# Goldens characterize the historical FULL path; plan-mode tests opt in.
os.environ.setdefault("TEACHER_CONTEXT", "full")

import copy
import datetime
import json
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from tutor import config

# ---------------------------------------------------------------------------
# Fake provider client
# ---------------------------------------------------------------------------

# Default reply: acknowledge/model/try shape that parses through
# tutor_response AND passes the output gate on ordinary conversation turns
# («estoy» is a structural key; «bien» carries an in-reply gloss).
DEFAULT_TUTOR_BODY = (
    "<tutor>\n"
    "  <acknowledge>¡Perfecto!</acknowledge>\n"
    "  <model>**Estoy bien** (I'm fine).</model>\n"
    "  <try>Di: **Estoy bien** (I'm fine).</try>\n"
    "</tutor>"
)

DEFAULT_FAKE_USAGE = {
    "input_tokens": 120,
    "output_tokens": 60,
    "thinking_tokens": 0,
    "cached_input_tokens": 0,
}


class FakeModelClient:
    """Anthropic-SDK-shaped fake of the tutor's provider client.

    Mimics exactly the surface ``tutor.conv_session`` uses (see
    ``_call``/``tutor_turn`` there and ``tutor.providers.GeminiClient`` for
    the real shapes): ``client.messages.create(model=, max_tokens=,
    system=, messages=, tools=)`` returning an object with ``.content``
    (list of text blocks), ``.stop_reason`` and ``.usage`` (input / output /
    thinking / cached fields).

    - ``queue_reply(body, ...)`` scripts canned <tutor>-tagged bodies (FIFO);
      when the queue is empty ``default_body`` is served.
    - every request is recorded (deep-copied) in ``self.requests`` for
      assertions: dict(model, max_tokens, system, messages, tools).
    - ``stop_reason`` per call can be scripted via ``queue_stop_reason``.
    """

    def __init__(
        self,
        replies=None,
        *,
        default_body: str = DEFAULT_TUTOR_BODY,
        usage: dict | None = None,
    ):
        self._replies: list[str] = list(replies or [])
        self._stop_reasons: list[str] = []
        self.default_body = default_body
        self.usage_per_call = dict(usage or DEFAULT_FAKE_USAGE)
        self.requests: list[dict] = []
        self._lock = threading.Lock()
        self.messages = SimpleNamespace(create=self._create)

    # -- scripting ----------------------------------------------------------
    def queue_reply(self, *bodies: str) -> None:
        self._replies.extend(bodies)

    def queue_stop_reason(self, *reasons: str) -> None:
        self._stop_reasons.extend(reasons)

    # -- the provider surface ----------------------------------------------
    def _create(
        self,
        *,
        model,
        max_tokens,
        messages,
        system=None,
        tools=None,
        **kwargs,
    ):
        with self._lock:
            self.requests.append({
                "model": model,
                "max_tokens": max_tokens,
                "system": copy.deepcopy(system),
                "messages": copy.deepcopy(messages),
                "tools": copy.deepcopy(tools),
                "extra": copy.deepcopy(kwargs),
            })
            body = (
                self._replies.pop(0) if self._replies else self.default_body
            )
            stop = (
                self._stop_reasons.pop(0)
                if self._stop_reasons
                else "end_turn"
            )
        u = self.usage_per_call
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=body)],
            stop_reason=stop,
            usage=SimpleNamespace(
                input_tokens=u.get("input_tokens", 0),
                output_tokens=u.get("output_tokens", 0),
                thinking_tokens=u.get("thinking_tokens", 0),
                cache_read_input_tokens=u.get("cached_input_tokens", 0),
                cache_creation_input_tokens=0,
            ),
        )

    # -- assertion helpers ---------------------------------------------------
    def request(self, i: int = -1) -> dict:
        return self.requests[i]

    def task_text(self, i: int = -1) -> str:
        """The final user message (the per-turn task) of request ``i``."""
        msgs = self.requests[i]["messages"]
        content = msgs[-1]["content"]
        return content if isinstance(content, str) else json.dumps(content)

    def task_payload(self, i: int = -1) -> dict:
        """Parsed <tutor_turn_task> JSON of request ``i`` (AI-tutor path)."""
        text = self.task_text(i)
        start = text.find("{")
        end = text.rfind("}")
        assert start >= 0 and end > start, "no JSON task payload captured"
        return json.loads(text[start:end + 1])

    def system_texts(self, i: int = -1) -> list[str]:
        sys_blocks = self.requests[i]["system"] or []
        out = []
        for b in sys_blocks:
            if isinstance(b, dict):
                out.append(str(b.get("text") or ""))
            else:
                out.append(str(b))
        return out

    def history_messages(self, i: int = -1) -> list[dict]:
        """Chat history the model saw (everything before the task message)."""
        return list(self.requests[i]["messages"][:-1])


# ---------------------------------------------------------------------------
# Truncation-law guard (docs/teacher-context-no-truncate.md)
# ---------------------------------------------------------------------------

def assert_full_teacher_context(ctx) -> None:
    """Every captured request carried FULL history / sheet.

    Enforces the no-silent-truncation law on the characterization harness
    itself: if anyone reintroduces [:N] slices or history[-N:] drops on the
    teacher path, these assertions fail before the goldens even diff.
    """
    fake, session = ctx.fake, ctx.session
    if not fake.requests:
        return
    # Testing mode really is uncapped.
    assert config.HISTORY_TURNS == 0, "HISTORY_TURNS must be 0 in tests"
    assert config.PACK_PROMPT_CHARS == 0
    assert config.STANCE_PROMPT_CHARS == 0
    assert config.SHEET_PROMPT_CHARS == 0

    def _blob(req):
        return "\n".join(
            str(b.get("text") or "") if isinstance(b, dict) else str(b)
            for b in (req["system"] or [])
        )

    def _is_round(req):
        # Plan-mode ROUND turns (USER architecture 2026-08-03) carry the
        # model's own plan instead of pack/pedagogy — a different contract,
        # asserted below, not an exemption from this guard.
        return "## Working from your plan" in _blob(req)

    # Course pack DELETED 2026-08-03 (USER: "the character sheet IS the
    # course pack") — no pack assertions; the sheet completeness checks
    # below are the curriculum guarantee.
    for i, req in enumerate(fake.requests):
        blob = _blob(req)
        if _is_round(req):
            content_i = req["messages"][-1]["content"]
            assert (
                isinstance(content_i, str)
                and '"your_session_plan"' in content_i
            ), (
                f"request {i}: ROUND turn task lacks your_session_plan — "
                "small context without the model's plan is a B0 regression"
            )
        elif "## Your session plan (required on this turn)" in blob:
            assert "# The teaching guide (yours)" in blob, (
                f"request {i}: PLAN turn missing the pedagogy guide"
            )
        # The per-turn task embeds the sheet as a complete JSON dump; a
        # [:N] slice would break the parse or drop trailing fields.
        content = req["messages"][-1]["content"]
        if isinstance(content, str) and "<tutor_turn_task>" in content:
            payload = json.loads(
                content[content.find("{"):content.rfind("}") + 1]
            )
            sheet_block = payload.get("student_character_sheet")
            if sheet_block is not None:
                sheet_json = json.loads(sheet_block["sheet"])  # parses fully
                for key in ("skills", "grammar", "lexicon", "updated_at"):
                    assert key in sheet_json, (
                        f"request {i}: sheet field {key!r} missing — "
                        "teacher sheet truncated"
                    )
                # §1.1a purge (full-code-audit S1b/S1c, 2026-08-03): the
                # model-facing projection must NOT carry code's agenda —
                # next_best stays on the sheet FILE (UI rail) only, and
                # teach_hint imperatives never ship.
                assert "next_best" not in sheet_json, (
                    f"request {i}: next_best shipped to the model — "
                    "code-owned agenda in the prompt (§1.1a)"
                )
                assert "teach_hint" not in sheet_block["sheet"], (
                    f"request {i}: teach_hint imperative shipped to the "
                    "model (§1.1a)"
                )
    # Full-history law: the LAST tutor request must carry the entire chat
    # history (open pair + every completed turn pair) with no [-N:] window.
    hist = session.history
    if len(hist) >= 2:
        expect = hist[:-2]  # history before the most recent exchange
        last = fake.requests[-1]
        got = last["messages"]
        if _is_round(last):
            # ROUND law (cache arm 2026-08-04): history is an append-only
            # SUFFIX of the full session history (the current plan cycle;
            # the plan turn digested the prefix). Marker-independent so a
            # failed plan call that already moved the cycle marker cannot
            # confuse the audit — no middle drops, tail-aligned.
            tail = got[:-1]
            assert expect[len(expect) - len(tail):] == tail, (
                "ROUND history is not an append-only suffix of the "
                "session history"
            )
        else:
            assert len(got) >= len(expect) + 1, (
                "last request dropped history messages"
            )
            assert got[:len(expect)] == expect, (
                "last request history diverges from full session history"
            )


# ---------------------------------------------------------------------------
# Session fixture
# ---------------------------------------------------------------------------


def _count_save_sheet(monkeypatch, record: list[str]) -> None:
    """Count conv_session save_sheet calls + their call sites (caller name)."""
    import tutor.conv_session as conv_session_mod
    from tutor.character_sheet import save_sheet as real_save_sheet

    def _counted(path, sheet):
        caller = sys._getframe(1).f_code.co_name
        record.append(caller)
        return real_save_sheet(path, sheet)

    monkeypatch.setattr(conv_session_mod, "save_sheet", _counted)


def _isolate_teach_assets(monkeypatch, request, tmp_path: Path) -> None:
    """Point the process-global teach-asset cache at an empty tmp dir.

    teach_assets state (_index, ASSETS_DIR, generator) is process-global
    across sessions (review doc E1).  For deterministic goldens the harness
    gives each test an empty cache: no image ever attaches, misses resolve
    to image_gen_disabled (no generator registered).
    """
    import tutor.teach_assets as ta

    assets = tmp_path / "teach_assets"
    (assets / "cache").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(ta, "ASSETS_DIR", assets)
    monkeypatch.setattr(ta, "CACHE_DIR", assets / "cache")
    monkeypatch.setattr(ta, "INDEX_PATH", assets / "cache_index.json")
    monkeypatch.setattr(ta, "MANIFEST_PATH", assets / "manifest.json")
    monkeypatch.setattr(ta, "GENERATE_ON_MISS", False)
    monkeypatch.setattr(ta, "_generator", None)
    monkeypatch.setattr(ta, "_index", None)

    def _reset_index():
        # After monkeypatch restores the real paths, force a lazy reload so
        # later (non-characterization) tests see the real on-disk index.
        ta._index = None

    request.addfinalizer(_reset_index)


@pytest.fixture
def tutor_session_factory(monkeypatch, tmp_path, request):
    """Factory building isolated real sessions against ``FakeModelClient``.

    Usage::

        ctx = tutor_session_factory(seed_sheet=..., replies=[...])
        ctx.session.open_session(); ctx.session.user_turn("hola")

    ``ctx`` fields: session, fake, sheet_path, progress_path, costs_path,
    save_calls (conv_session save_sheet call sites, in order).
    The truncation-law guard runs automatically on teardown.
    """
    import tutor.costs as costs_mod

    contexts: list[SimpleNamespace] = []

    # ---- process-global isolation (shared by every session this test) ----
    progress_path = tmp_path / "progress.jsonl"
    costs_path = tmp_path / "costs.jsonl"
    monkeypatch.setenv("PROGRESS_LEDGER_PATH", str(progress_path))
    monkeypatch.setenv("COST_LEDGER_PATH", str(costs_path))
    # costs.LEDGER_PATH is bound at import — patch the attribute too.
    monkeypatch.setattr(costs_mod, "LEDGER_PATH", costs_path)

    # Deterministic teacher path: planned AI tutor, no side-rail LLMs, no
    # sheet tool round-trips, full context (no truncation).
    monkeypatch.setattr(config, "TEACHER_MODE", "planned")
    monkeypatch.setattr(config, "SIGNAL_CLASSIFIER_MODEL", "off")
    monkeypatch.setattr(config, "SIGNAL_CLASSIFIER_BLOCKING", False)
    monkeypatch.setattr(config, "SHEET_TOOLS", False)
    # (config.GATE_REPAIR stub deleted 2026-08-03 — nothing to pin.)
    monkeypatch.setattr(config, "TEACHER_CONTEXT_TRUNCATE", False)
    monkeypatch.setattr(config, "HISTORY_TURNS", 0)
    monkeypatch.setattr(config, "PACK_PROMPT_CHARS", 0)
    monkeypatch.setattr(config, "STANCE_PROMPT_CHARS", 0)
    monkeypatch.setattr(config, "SHEET_PROMPT_CHARS", 0)
    monkeypatch.setenv("TEACHER_CONTEXT_TRUNCATE", "false")

    _isolate_teach_assets(monkeypatch, request, tmp_path)

    # Plan-reuse isolation (2026-08-04): the blank-plan cache and the
    # per-learner plan store derive their paths from the process-global
    # CHARACTER_SHEET_PATH. Without this, a fake-session test STORES its
    # fake plan into the LIVE logs/plan_cache/ (and later tests hit it) —
    # the suite must never write, or read, the operator's cache.
    monkeypatch.setattr(
        config, "CHARACTER_SHEET_PATH", tmp_path / "character_sheet.json"
    )

    save_calls: list[str] = []
    _count_save_sheet(monkeypatch, save_calls)

    def factory(
        *,
        seed_sheet: dict | None = None,
        replies=None,
        default_body: str = DEFAULT_TUTOR_BODY,
        label: str = "chartest",
        pack_dir: Path | None = None,
    ) -> SimpleNamespace:
        from tutor.character_sheet import save_sheet as real_save_sheet
        from tutor.conv_session import ConversationalSession

        fake = FakeModelClient(replies, default_body=default_body)
        # Injection point: conv_session.__init__ does
        # ``self.client = config.make_client_for(self.model)`` — cleanest
        # seam, no production change.  Any other module asking for a client
        # (defensively) also gets the fake: nothing can reach the network.
        monkeypatch.setattr(config, "make_client_for", lambda model: fake)

        sheet_path = tmp_path / f"sheet-{len(contexts)}.json"
        if seed_sheet is not None:
            real_save_sheet(sheet_path, seed_sheet)

        session = ConversationalSession(
            model="fake-model",
            pack_dir=pack_dir or config.DEFAULT_PACK_DIR,
            sheet_path=sheet_path,
            use_tools=False,
            label=label,
            log=False,  # no logs/sessions writes
        )
        ctx = SimpleNamespace(
            session=session,
            fake=fake,
            sheet_path=sheet_path,
            progress_path=progress_path,
            costs_path=costs_path,
            save_calls=save_calls,
        )
        contexts.append(ctx)
        return ctx

    yield factory

    # Truncation-law guard on every session the test built.
    for ctx in contexts:
        assert_full_teacher_context(ctx)


@pytest.fixture
def tutor_session(tutor_session_factory):
    """Default isolated session: blank sheet, default canned reply."""
    return tutor_session_factory()


# ---------------------------------------------------------------------------
# Golden-file helpers (tests/characterizations/)
# ---------------------------------------------------------------------------

CHARACTERIZATIONS_DIR = Path(__file__).parent / "characterizations"

# Note families whose payloads are volatile across unrelated sheet edits —
# collapsed to a stable family key in goldens (the brief: "set of prefixes,
# not exact strings where volatile").  Everything else is pinned verbatim.
_VOLATILE_NOTE_PREFIXES = (
    "can-dos ",
    "next=",
    "why=",
)


def note_families(notes) -> list[str]:
    out = []
    for n in notes or []:
        n = str(n)
        for pref in _VOLATILE_NOTE_PREFIXES:
            if n.startswith(pref):
                n = pref.rstrip(" =") + "=*"
                break
        out.append(n)
    return out


def normalize_dates(obj, extra: dict[str, str] | None = None):
    """Replace today/tomorrow/yesterday ISO dates with stable placeholders."""
    day = datetime.date.today()
    table = {
        day.isoformat(): "<TODAY>",
        (day + datetime.timedelta(days=1)).isoformat(): "<TOMORROW>",
        (day - datetime.timedelta(days=1)).isoformat(): "<YESTERDAY>",
    }
    table.update(extra or {})

    def _walk(x):
        if isinstance(x, str):
            for raw, ph in table.items():
                x = x.replace(raw, ph)
            return x
        if isinstance(x, list):
            return [_walk(v) for v in x]
        if isinstance(x, dict):
            return {k: _walk(v) for k, v in x.items()}
        return x

    return _walk(obj)


def check_golden(name: str, observed: dict) -> None:
    """Compare ``observed`` against tests/characterizations/<name>.json.

    Deliberate regeneration only: CHAR_GOLDEN_UPDATE=1 rewrites the golden
    (never set in CI).  A CHAR_BUG-tagged golden must not be regenerated
    without the paired bugfix PR updating the pin (Phase 0 law).
    """
    path = CHARACTERIZATIONS_DIR / f"{name}.json"
    if os.environ.get("CHAR_GOLDEN_UPDATE", "").strip().lower() in (
        "1", "true", "yes", "on",
    ):
        CHARACTERIZATIONS_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        return
    assert path.exists(), (
        f"golden {path} missing — run once with CHAR_GOLDEN_UPDATE=1"
    )
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert observed == expected, (
        f"characterization drift vs {path.name} — if the change is "
        "DELIBERATE, update the golden with CHAR_GOLDEN_UPDATE=1 and say so "
        "in the PR (CHAR_BUG pins additionally need the bugfix note; see "
        "tests/characterizations/known_bugs.json)"
    )
