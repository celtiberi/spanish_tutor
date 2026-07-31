"""Teaching modes + select_mode — code owns when to break from conversation.

See docs/teaching-system.md. Conversation is the outer loop; modes are pedagogy.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .association_table import cached_default_table
from .character_sheet import (
    ERROR_PATTERN_CATALOG,
    active_error_patterns,
    detect_error_pattern_hits,
    detect_error_pattern_resolves,
)
from .pedagogy_contract import is_blank_learner
from .textnorm import fold_asset_key

# ---------------------------------------------------------------------------
# Guard-6 concept lists — TABLE-DERIVED (Phase 5 batch 2 flip, CONSERVATIVE,
# docs/reviews-architecture-refactor.md).  ASSOCIATION_NOUNS (zero readers)
# is DELETED.  Membership for _noun_from_text / _new_concrete_noun is the
# recorded legacy set, validated at import against the association table
# with the IMAGEABLE law enforced:
#
#   Image SELECTION for guard-6 / association (R-B dual-coding) derives from
#   table entries with ``imageable: true`` — the table's `imageable` answers
#   "can THIS concept be dual-coded for meaning".  The asset SIDECAR answers
#   the different question "do we have an asset" and never widens selection.
#   The one adjudicated exemption is the placement-open image: the blank
#   open's ``decision.image_concept = "hola"`` (guard 2 below) is SCENE-
#   SETTING for the true-zero opening — a code-owned decision channel with
#   its own justification, NOT R-B meaning-binding — so it is exempt from
#   the imageable filter (hola is imageable:false; its greeting illustration
#   lives in the pack asset sidecar).
#
# Needle strings remain learner-surface DETECTION text (§1.1a allowed class
# iv); their ORDER is behavior-bearing (first match wins in _noun_from_text)
# and reproduces the legacy priority exactly, including the deliberate
# split: «río dulce» (place name, most specific) outranks everything while
# plain «río» ranks below the other nouns.  «barco» stays its own table key
# (real distinct word, topic-palette member) but maps to the «bote» asset
# id here — the sidecar alias collapse, kept deliberately (batch-1 flag).
# ---------------------------------------------------------------------------

# (needle surface, table key providing the concept id) — legacy priority
# order, recorded.  Concept ids are fold_asset_key(table key).
_GUARD6_NEEDLE_SPEC: tuple[tuple[str, str], ...] = (
    ("río dulce", "río"), ("rio dulce", "río"),
    ("café", "café"), ("cafe", "café"),
    ("barco", "bote"), ("bote", "bote"),
    ("música", "música"), ("musica", "música"),
    ("comida", "comida"),
    ("edificios", "edificio"), ("edificio", "edificio"),
    ("casa", "casa"),
    ("playa", "playa"),
    ("perro", "perro"),
    ("gato", "gato"),
    ("agua", "agua"),
    ("sol", "sol"),
    ("río", "río"), ("rio", "río"),
    ("calor", "calor"),
    ("frío", "frío"), ("frio", "frío"),
)

# _new_concrete_noun candidate membership + order (recorded legacy).
_NEW_CONCRETE_TABLE_KEYS: tuple[str, ...] = (
    "café", "bote", "música", "comida", "río",
)


def _imageable_concept_id(table: dict, key: str, source: str) -> str:
    entry = table.get(key)
    if not isinstance(entry, dict):
        raise ValueError(f"{source}: {key!r} is not an association-table key")
    if not entry.get("imageable"):
        raise ValueError(
            f"{source}: {key!r} is imageable:false — guard-6/association "
            "selection derives from imageable:true entries only (the "
            "placement-open image_concept channel is the one exemption)"
        )
    return fold_asset_key(key)


def _derived_noun_text_pairs() -> tuple[tuple[str, str], ...]:
    table = cached_default_table()
    return tuple(
        (needle, _imageable_concept_id(table, key, "NOUN_TEXT_PAIRS"))
        for needle, key in _GUARD6_NEEDLE_SPEC
    )


def _derived_new_concrete_nouns() -> tuple[str, ...]:
    table = cached_default_table()
    return tuple(
        _imageable_concept_id(table, key, "NEW_CONCRETE_NOUNS")
        for key in _NEW_CONCRETE_TABLE_KEYS
    )


NOUN_TEXT_PAIRS: tuple[tuple[str, str], ...] = _derived_noun_text_pairs()
NEW_CONCRETE_NOUNS: tuple[str, ...] = _derived_new_concrete_nouns()

HARD_BREAK_MODES = frozenset({
    "form_focus",
    "association",
    "comprehension_check",
    "comprehension_repair",
    "placement",
})


class Mode(str, Enum):
    PLACEMENT = "placement"
    CONVERSATION = "conversation"
    CF_RECAST = "cf_recast"
    FORM_FOCUS = "form_focus"
    COMPREHENSION_CHECK = "comprehension_check"
    COMPREHENSION_REPAIR = "comprehension_repair"  # didn't get last Spanish — stay on it
    ASSOCIATION = "association"
    TRANSFER = "transfer"  # conversation with explicit transfer try


@dataclass
class ModeDecision:
    mode: Mode
    reason: str
    hard_break: bool = False
    targets: dict[str, Any] = field(default_factory=dict)
    scene_ids: list[str] = field(default_factory=list)
    image_concept: str | None = None
    instructions: str = ""

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["mode"] = self.mode.value
        return d


# A sheet-streak form_focus hard break needs the error to be RECENT (this
# session, within K learner turns) — stale counts must not hijack clean turns
# (Grok countersign 2026-07-28, Lyster & Ranta-style feedback-at-source).
K_STREAK_RECENCY = 4


@dataclass
class ModeSessionState:
    """Session-scoped mode runtime (not the character sheet)."""

    hard_breaks_this_session: int = 0
    turns_since_hard_break: int = 999
    last_hard_mode: str | None = None
    form_focus_cooldown: dict[str, int] = field(default_factory=dict)  # pattern_id → turns left
    english_only_streak: int = 0
    open_scene_ids: list[str] = field(default_factory=list)
    # scene_modeled DELETED (Proposal A, 2026-07-29): the prefer-unmodeled
    # ledger predated phases/§1.1a and was unlawful when alive (CHAR-BUG-005
    # RESOLVED-BY-DELETION — docs/reviews-architecture-refactor.md).
    last_mode: str | None = None
    last_resolved_form: str | None = None  # form just resolved → transfer next
    # Error patterns resolved at least once THIS session (close-phase summary)
    resolved_this_session: list[str] = field(default_factory=list)
    # Error recency for streak hard breaks (session-local turn distance)
    learner_turn_index: int = 0
    last_error_hit_turn: dict[str, int] = field(default_factory=dict)
    # §2.1a content-uptake budget (BINDING, 2026-07-28): ≤1 content-uptake
    # deferral per 3 teaching turns, never consecutive — the ≥3-turn gap
    # enforces both clauses with one field.
    content_uptake_last_turn: int = -999

    def tick(self) -> None:
        self.turns_since_hard_break = min(self.turns_since_hard_break + 1, 999)
        self.learner_turn_index += 1
        cooled = {}
        for k, v in self.form_focus_cooldown.items():
            if v > 1:
                cooled[k] = v - 1
        self.form_focus_cooldown = cooled

    def note_error_hits(self, hit_ids) -> None:
        for pid in hit_ids or []:
            if pid:
                self.last_error_hit_turn[str(pid)] = self.learner_turn_index

    def error_recent(self, pid: str, *, k: int = K_STREAK_RECENCY) -> bool:
        last = self.last_error_hit_turn.get(str(pid))
        if last is None:
            return False
        return (self.learner_turn_index - last) <= k

    def note_resolved(self, pattern_ids) -> None:
        for pid in pattern_ids or []:
            if pid and str(pid) not in self.resolved_this_session:
                self.resolved_this_session.append(str(pid))

    def content_uptake_allowed(self) -> bool:
        """§2.1a budget check (rate + no-consecutive in one gap test)."""
        return (self.learner_turn_index - self.content_uptake_last_turn) >= 3

    def note_content_uptake(self) -> None:
        self.content_uptake_last_turn = self.learner_turn_index

    def note_hard_break(self, mode: Mode) -> None:
        self.hard_breaks_this_session += 1
        self.turns_since_hard_break = 0
        self.last_hard_mode = mode.value

    def set_cooldown(self, pattern_id: str, turns: int = 4) -> None:
        self.form_focus_cooldown[pattern_id] = turns

    def snapshot(self) -> dict[str, Any]:
        return {
            "hard_breaks_this_session": self.hard_breaks_this_session,
            "turns_since_hard_break": self.turns_since_hard_break,
            "last_hard_mode": self.last_hard_mode,
            "form_focus_cooldown": dict(self.form_focus_cooldown),
            "english_only_streak": self.english_only_streak,
            "open_scene_ids": list(self.open_scene_ids),
            "last_mode": self.last_mode,
            "last_resolved_form": self.last_resolved_form,
            "resolved_this_session": list(self.resolved_this_session),
            "content_uptake_last_turn": self.content_uptake_last_turn,
        }

    @classmethod
    def from_snapshot(cls, data: dict | None) -> "ModeSessionState":
        """Rebuild from ``snapshot()`` output — the E2 persistence restore
        (Phase 1 batch 2, docs/reviews-architecture-refactor.md).

        ``snapshot()`` alone is lossy (shape pinned by debug consumers):
        learner_turn_index and last_error_hit_turn do not appear in it. The
        SessionState aggregate supplies them as sibling keys in the same
        dict; absent keys restore to their dataclass defaults.
        """
        d = data if isinstance(data, dict) else {}

        def _num(key: str, default: int) -> int:
            try:
                v = d.get(key, default)
                return default if v is None else int(v)
            except (TypeError, ValueError):
                return default

        s = cls()
        s.hard_breaks_this_session = _num("hard_breaks_this_session", 0)
        s.turns_since_hard_break = _num("turns_since_hard_break", 999)
        s.last_hard_mode = (
            str(d["last_hard_mode"]) if d.get("last_hard_mode") else None
        )
        s.form_focus_cooldown = {
            str(k): int(v)
            for k, v in (d.get("form_focus_cooldown") or {}).items()
        }
        s.english_only_streak = _num("english_only_streak", 0)
        s.open_scene_ids = [str(x) for x in d.get("open_scene_ids") or []]
        # Legacy snapshots may carry a "scene_modeled" key — ignored
        # (field deleted; Proposal A, 2026-07-29).
        s.last_mode = str(d["last_mode"]) if d.get("last_mode") else None
        s.last_resolved_form = (
            str(d["last_resolved_form"])
            if d.get("last_resolved_form") else None
        )
        s.resolved_this_session = [
            str(x) for x in d.get("resolved_this_session") or []
        ]
        s.learner_turn_index = _num("learner_turn_index", 0)
        s.last_error_hit_turn = {
            str(k): int(v)
            for k, v in (d.get("last_error_hit_turn") or {}).items()
        }
        s.content_uptake_last_turn = _num("content_uptake_last_turn", -999)
        return s


# Session-phase layer (Phase 2, tutor/session_phases.py): reasons that FREEZE
# the phase clock — guard turns and comprehension repair never consume phase
# budget (r6 §4.2 rule 1). conv_session uses this to compute tick(consumed).
PHASE_FREEZE_REASONS = frozenset({
    "time_pressure_inline_recast",
    "time_pressure_chat",
    "learner_topic_request",
    "learner_help_request",
    "boredom_new_topic",
    "grammar_question_inline",
    "meta_comprehension_stay_on_topic",
    "blank_open_placement",  # placement open happens before the plan engages
})


def _phase_prefix(activity_hint: str | None, mem: dict) -> str:
    """Instruction prefix for the session-phase activity hint.

    Applied ONLY on the default CONVERSATION fallthrough and the known-open
    block — guards ignore the hint entirely, and intervention decisions
    (cf_recast/form_focus/association/transfer) ride WITHIN phases unmodified.
    "free" (and unknown hints) keep current behavior: no prefix.
    """
    if activity_hint == "retrieval":
        return (
            "SESSION PHASE: RETRIEVAL — this turn's priority is the DUE "
            "RE-ENCOUNTERS block below; weave one due item into a natural "
            "exchange before anything new."
        )
    if activity_hint == "new_input":
        try:
            remaining = int(mem.get("intro_budget_remaining"))
        except (TypeError, ValueError):
            remaining = None
        if remaining is None:
            budget_note = "introduce budget unknown — assume at most 1"
        elif remaining <= 0:
            budget_note = (
                "introduce budget EXHAUSTED (0 left) — introduce NOTHING "
                "new; recycle already-introduced items model-heavy"
            )
        else:
            budget_note = f"introduce budget: {remaining} left this session"
        return (
            "SESSION PHASE: NEW INPUT — introduce at most ONE new pack-legal "
            f"item this turn IF the session introduce budget allows "
            f"({budget_note}); model-heavy, keep the try simple (a yes/no or "
            "A/B comprehension check is acceptable instead of free "
            "production). If an INTRODUCE block follows, it is THE new item "
            "— follow it exactly."
        )
    if activity_hint == "task":
        return (
            "SESSION PHASE: TASK — drive toward ONE concrete conversational "
            "goal from the open scenes/pack topics and finish it; no topic "
            "drift until done."
        )
    if activity_hint == "close":
        # PEDAGOGY §1.2 Close phase (USER-ratified 2026-07-28).
        return (
            "SESSION PHASE: CLOSE — end the session now: (1) ONE short "
            "English line naming what they practiced this session (use the "
            "session summary data provided); (2) a real Spanish farewell "
            "exchange using a farewell they have met (hasta luego / adiós "
            "per the sheet ledger); no new items, no corrections unless the "
            "farewell itself fails."
        )
    return ""


def _topic_suggestion_line(pack_topics: list[str] | None) -> str:
    """Course-pack topic palette for change-topic instructions (never hardcoded)."""
    topics = [t for t in (pack_topics or []) if t]
    if not topics:
        return " Pick any fresh everyday topic inside the course-pack scope."
    return " Fresh-topic palette from the course pack: " + "; ".join(topics) + "."


def _fallback_association_concept(
    sheet: dict,
    images_shown: set[str] | None = None,
) -> str:
    """Least-confident unshown concrete noun from the learner's own lexicon.

    Replaces the old hardcoded 'bote' default that dragged every stuck-English
    moment back to the boat.
    """
    shown = set(images_shown or [])
    lex = sheet.get("lexicon") or {}
    best: tuple[float, str] | None = None
    for noun in ("cafe", "comida", "musica", "rio", "bote"):
        if noun in shown:
            continue
        entry = lex.get(noun) or {}
        conf = float(entry.get("confidence") or 0) if isinstance(entry, dict) else 0.0
        if best is None or conf < best[0]:
            best = (conf, noun)
    return best[1] if best else "cafe"


def _affect_energy(sheet: dict) -> str:
    aff = sheet.get("affect") or {}
    return str(aff.get("energy") or "unknown").lower()


def _can_hard_break(state: ModeSessionState) -> bool:
    # ≤1 hard break per 3 turns; never two consecutive
    if state.turns_since_hard_break < 3 and state.hard_breaks_this_session > 0:
        # Allow if never broken yet is false; if last turn was hard break, block
        if state.turns_since_hard_break == 0:
            return False
        if state.turns_since_hard_break < 3:
            return False
    return True


def _top_active_error(sheet: dict) -> dict | None:
    active = active_error_patterns(sheet, min_count=2)
    if not active:
        # also hot count ≥2 raw even if weaning logic differs
        for pid, ent in (sheet.get("error_patterns") or {}).items():
            if isinstance(ent, dict) and int(ent.get("count") or 0) >= 2:
                return {
                    "id": pid,
                    "count": int(ent["count"]),
                    "form_id": ent.get("form_id") or (ERROR_PATTERN_CATALOG.get(pid) or {}).get("form_id"),
                    "teach_hint": ent.get("teach_hint") or (ERROR_PATTERN_CATALOG.get(pid) or {}).get("teach_hint") or "",
                    "label": ent.get("label") or pid,
                }
        return None
    return active[0]


def _new_concrete_noun(
    signals: set[str] | list[str],
    sheet: dict,
    *,
    images_shown: set[str] | None = None,
) -> str | None:
    """Return a concrete noun concept if learner/topic suggests one."""
    shown = set(images_shown or [])
    lex = sheet.get("lexicon") or {}
    if "topic_vocab" not in set(signals):
        return None
    for noun in NEW_CONCRETE_NOUNS:
        if noun in shown:
            continue
        entry = lex.get(noun) or {}
        conf = float((entry or {}).get("confidence") or 0) if isinstance(entry, dict) else 0
        if conf < 0.35 or noun not in shown:
            return noun
    return None


def _noun_from_text(
    text: str,
    sheet: dict,
    *,
    images_shown: set[str] | None = None,
) -> str | None:
    """First session mention of a concrete noun → associate (generate image if needed).

    `images_shown` membership is AUTHORITATIVE dedup (2026-07-28 repetition
    forensics): the old `conf < 0.25` escape hatch re-fired new_noun:casa on
    every mention for a reset learner (empty lexicon ⇒ conf 0.0 forever),
    producing byte-identical association turns. A concept already shown /
    covered this session never re-fires here, whatever its confidence.
    """
    from .observe import word_present

    low = (text or "").lower()
    shown = set(images_shown or [])
    # Known pairs first (longer needles first). Any concept can be generated.
    for needle, concept in NOUN_TEXT_PAIRS:
        if word_present(needle, low) and concept not in shown:
            return concept
    return None


def _scene_for_topic(
    open_scenes: list[dict],
    *,
    learner: str = "",
    signals: set[str] | None = None,
) -> dict | None:
    """Pick open scene matching live topic (boat/location/likes) before generic next_best.

    Keyword scoring ONLY (Proposal A KEEP-5, 2026-07-29): passive /
    live-topic scene pursuit is not covered by task bind order. The
    prefer-unmodeled `+1` and the `_scene_needs_model` fallback were
    DELETED with the scene_modeled ledger (CHAR-BUG-005
    RESOLVED-BY-DELETION) — no topic match, no scene.
    """
    low = (learner or "").lower()
    sigs = set(signals or [])
    scored: list[tuple[int, dict]] = []
    for sc in open_scenes or []:
        score = 0
        blob = json.dumps(sc, ensure_ascii=False).lower()
        if any(w in low for w in ("bote", "barco", "río", "rio", "guatemala", "dulce")):
            if "bote" in blob or "rio" in blob or "captain" in blob or "boat" in blob:
                score += 3
        if any(w in low for w in ("gusta", "café", "cafe", "música", "musica")):
            if "gusta" in blob or "like" in blob or "cafe" in blob:
                score += 3
        if "estoy" in low or "dónde" in low or "donde" in low or "origin" in sigs:
            if "estar" in blob or "estoy" in blob or "ip-04" in blob or "ip-07" in blob:
                score += 2
        if score:
            scored.append((score, sc))
    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


# Appended to every non-open decision while the learner is still a TRUE ZERO
# (blank sheet AND no successful Spanish this turn). Incident 2026-07-28:
# a reset beginner got 100% Spanish — PEDAGOGY P1 (comprehensible meaning is
# necessary raw material) + §2.3 (English scaffold jobs). The blank open
# branch carries its own full true-zero text; this note keeps the register
# consistent on the turns AFTER the open until any spanish_ok de-escalates.
ZERO_REGISTER_NOTE = (
    "TRUE-ZERO REGISTER (blank sheet, no successful Spanish from them yet): "
    "English support is REQUIRED here, not banned — keep one short English "
    "orientation sentence and put a ≤6-word English gloss on EVERY Spanish "
    "item; at most 3 Spanish items this turn. This is the zero state only — "
    "the moment they produce ANY Spanish, drop it and return to the standard "
    "mostly-Spanish register."
)


def select_mode(
    sheet: dict,
    *,
    observations: dict | None = None,
    is_open: bool = False,
    learner: str = "",
    mode_state: ModeSessionState | None = None,
    open_scenes: list[dict] | None = None,
    images_shown: set[str] | list[str] | None = None,
    session_memory: dict | None = None,
    pack_topics: list[str] | None = None,
    profile: dict | None = None,  # accepted for compat; personal data unused
    activity_hint: str | None = None,  # session-phase layer; guards ignore it
) -> ModeDecision:
    """Mode selection + true-zero register overlay.

    Routing lives in _select_mode_impl (frozen guard chain, first matching
    guard wins). This wrapper appends ZERO_REGISTER_NOTE while the sheet is
    blank AND the learner has not produced any successful Spanish this turn
    (no spanish_ok signal) — graded de-escalation: the first spanish_ok turn
    reverts to the standard mostly-Spanish register, and once the sheet has
    ability evidence is_blank_learner turns the overlay off for good. The
    blank open branch (blank_open_placement) already carries its own full
    true-zero text and is skipped here.
    """
    decision = _select_mode_impl(
        sheet,
        observations=observations,
        is_open=is_open,
        learner=learner,
        mode_state=mode_state,
        open_scenes=open_scenes,
        images_shown=images_shown,
        session_memory=session_memory,
        pack_topics=pack_topics,
        profile=profile,
        activity_hint=activity_hint,
    )
    obs = observations or {}
    blank = bool(
        obs.get("blank_sheet") if "blank_sheet" in obs else is_blank_learner(sheet)
    )
    signals = set(obs.get("signals") or [])
    if (
        blank
        and "spanish_ok" not in signals
        and decision.reason != "blank_open_placement"
    ):
        decision.instructions = (
            (decision.instructions or "").rstrip() + "\n" + ZERO_REGISTER_NOTE
        ).strip()
    return decision


def _select_mode_impl(
    sheet: dict,
    *,
    observations: dict | None = None,
    is_open: bool = False,
    learner: str = "",
    mode_state: ModeSessionState | None = None,
    open_scenes: list[dict] | None = None,
    images_shown: set[str] | list[str] | None = None,
    session_memory: dict | None = None,
    pack_topics: list[str] | None = None,
    profile: dict | None = None,  # accepted for compat; personal data unused
    activity_hint: str | None = None,  # session-phase layer; guards ignore it
) -> ModeDecision:
    """Deterministic mode selection — first matching guard wins.

    See docs/teaching-system.md § Break-from-conversation policy.
    activity_hint (tutor/session_phases.py) flavors ONLY the known-open block
    and the default CONVERSATION fallthrough; every guard and intervention
    branch ignores it (frozen guard chain has absolute priority) — with ONE
    adjudicated exception: guard 7's topic scene pick is SUPPRESSED on
    new_input/close activities (PHASE HOST rule 6, Proposal A 2026-07-29 —
    introduce owns new_input, close owns close per PEDAGOGY §6.4).
    """
    obs = observations or {}
    mem = session_memory or {}
    state = mode_state or ModeSessionState()
    signals = set(obs.get("signals") or [])
    open_scenes = open_scenes or []
    shown_imgs = set(images_shown or [])
    blank = bool(obs.get("blank_sheet") if "blank_sheet" in obs else is_blank_learner(sheet))
    hits = detect_error_pattern_hits(learner) if learner and not is_open else []
    hit_ids = {pid for pid, _ in hits}
    resolves = set(detect_error_pattern_resolves(learner)) if learner and not is_open else set()
    can_hard = _can_hard_break(state)
    energy = _affect_energy(sheet)

    last_try = (mem.get("last_tutor_try") or "").strip()
    last_model = (mem.get("last_tutor_model") or "").strip()
    last_concepts = list(mem.get("last_concepts") or [])
    await_comp = bool(mem.get("await_comprehension"))
    topic_line = _topic_suggestion_line(pack_topics)

    # 0) Time pressure — no hard break
    if energy == "limited_time":
        if hits:
            return ModeDecision(
                Mode.CF_RECAST,
                reason="time_pressure_inline_recast",
                hard_break=False,
                targets={"error_hits": list(hit_ids)},
                instructions="Short Spanish; recast form errors inline; no mini-lesson.",
            )
        return ModeDecision(
            Mode.CONVERSATION,
            reason="time_pressure_chat",
            instructions="Keep it short; one Spanish question; no drills.",
        )

    # 0b) Learner steered the lesson (new topic / activity request) — honor it
    #     in THIS reply. English is how novices make this request; it must
    #     never be routed to comprehension repair or deferred with "first
    #     answer my question".
    if not is_open and "topic_request" in signals:
        nb = sheet.get("next_best") or {}
        return ModeDecision(
            Mode.CONVERSATION,
            reason="learner_topic_request",
            hard_break=False,
            targets={
                "honor_request": True,
                "form_focus": nb.get("form_focus"),
                "error_pattern": nb.get("error_pattern"),
            },
            instructions=(
                "They asked to change the topic or activity — do it NOW, in "
                "this reply. Re-read their message for what they want and "
                "build the turn around it. Do not finish your previous "
                "question first and do not return to earlier topics."
                + topic_line
                + " Keep weaving any active form focus into the NEW topic."
            ),
        )

    # 0c) Learner asked how to say a word/phrase — answer it, always. This
    #     outranks comprehension repair: a help request is uptake to honor,
    #     not evidence of non-understanding (Grok round-1 F, 2026-07-28).
    if not is_open and "help_request" in signals:
        return ModeDecision(
            Mode.CONVERSATION,
            reason="learner_help_request",
            hard_break=False,
            targets={"honor_request": True, "answer_language_question": True},
            instructions=(
                "They asked how to say a word/phrase. FIRST give the Spanish form "
                "(+ brief English gloss). Model one short example. Then one try that "
                "elicits THAT form in the live context. Do not re-ask an unrelated "
                "prior greeting/try."
            ),
        )

    # Boredom routing DELETED 2026-07-30 (junk audit): affect.boredom_risk
    # was set in 0 of 207 real turns; the branch sat ABOVE comprehension
    # repair in the guard chain. P6 stays theory; machinery returns only
    # under the omission-ledger revive condition.

    # 1b) Comprehension repair — they didn't understand OUR Spanish
    #     MUST stay on same idea: explain + image + re-ask simplified SAME question
    #     Never jump to a brand-new topic (¿Te gusta el río? after explaining saludarte).
    if (
        not is_open
        and (
            "meta_comprehension" in signals
            or await_comp
            or re_search_no_entiendo(learner)
        )
        and (last_try or last_model)
    ):
        # They understood enough to ANSWER in their OWN Spanish while asking
        # about the language (por vs para, what is "son") — that is a grammar
        # question, not failed comprehension. Answer it; don't re-ask the try.
        # Quoted tutor Spanish and literal "no entiendo" are stripped first:
        # echoing our words or saying they don't understand is evidence of
        # NON-comprehension, not of production.
        import re as _re

        from .observe import probe_signals as _probe, strip_quoted as _strip

        own_text = _re.sub(
            r"\bno\s+(?:lo\s+)?entiendo\b", " ", _strip(learner or ""),
            flags=_re.I,
        )
        own_sig = _probe(own_text)
        if "meta_comprehension" in signals and "spanish_ok" in own_sig:
            return ModeDecision(
                Mode.CONVERSATION,
                reason="grammar_question_inline",
                hard_break=False,
                targets={"answer_language_question": True},
                instructions=(
                    "They answered you AND asked about the language "
                    "(grammar/word meaning). FIRST answer their language "
                    "question clearly — brief English is fine here. THEN "
                    "react to the content of their answer and continue the "
                    "same conversation with one new try. Do NOT re-ask the "
                    "question they already answered."
                ),
            )
        # Incident 2026-07-28 (hola image on a digo/dices grammar question):
        # when the learner wrote a substantive turn (meta/grammar question,
        # partial answer), THIS turn teaches what they asked about — the
        # prior repair target is image-relevant only if their own message
        # actually contains it (code-owned surface check, no LLM). Nothing
        # relevant → NO image: an absent image beats a wrong one (r5).
        # Only a true non-comprehension turn («no entiendo» / pure echo of
        # tutor Spanish) keeps the repair-target image, because there the
        # prior concept IS the content being re-taught (dual-coding).
        from .teach_assets import concept_in_text

        # Strict: «no entiendo» / "don't understand" / pure echo only.
        # NOT the "what does X mean" pattern — that is a meta question
        # about X and must pass the learner-text relevance check instead.
        noncomp_only = not own_text.strip() or bool(_re.search(
            r"\bno\s+(?:lo\s+)?entiendo\b|\bno\s+comprendo\b"
            r"|(?:don'?t|do\s+not|dont)\s+understand\b",
            learner or "", _re.I,
        ))
        if noncomp_only:
            img = None
            for c in last_concepts:
                if c and c not in shown_imgs:
                    img = c
                    break
            if not img and last_concepts:
                img = last_concepts[0]
            # Prefer image for dual-coding even if already shown once
            if not img:
                img = _noun_from_text(
                    f"{last_try} {last_model} {learner}", sheet, images_shown=set()
                )
        else:
            img = next(
                (c for c in last_concepts if c and concept_in_text(c, learner)),
                None,
            ) or _noun_from_text(learner, sheet, images_shown=set())
        simple_try = _simplify_try(last_try) or last_try
        return ModeDecision(
            Mode.COMPREHENSION_REPAIR,
            reason="meta_comprehension_stay_on_topic",
            hard_break=True,
            image_concept=img,
            targets={
                "last_try": last_try,
                "last_model": last_model,
                "rephrase_try": simple_try,
                "concepts": last_concepts,
                "require_same_topic": True,
                "forbid_new_topic": True,
            },
            instructions=(
                "COMPREHENSION REPAIR — prior Spanish may not have landed; stay on the "
                "SAME communicative intent (no new topic / new can-do).\n"
                "0) UPTAKE FIRST: if this learner turn contains any question or help "
                "request (word, phrase, grammar, 'how do I say…', 'I always forget…'), "
                "answer it briefly FIRST. That is not a topic jump.\n"
                "1) Brief English or ultra-simple Spanish: what the KEY phrase meant "
                f"(from: {last_model!r} / try: {last_try!r}).\n"
                "2) If an image is attached, use it to bind the noun/meaning.\n"
                "3) <model> the same idea in SIMPLER Spanish (shorter, high-frequency words).\n"
                f"4) <try> re-ask the SAME communicative intent (e.g. {simple_try!r}) ONLY "
                "if they still have not shown understanding of that intent and did not "
                "already answer it. If they only asked a language question while producing "
                "their own Spanish content, do NOT re-ask the old try — continue from "
                "their content.\n"
                "5) Keep the turn short. forbid_new_topic = no new scene/topic; questions "
                "about language are allowed and required."
            ),
        )

    # 2) Placement / known open
    if is_open and blank:
        # TRUE-ZERO opening (incident 2026-07-28: reset beginner got 100%
        # Spanish). PEDAGOGY P1 + §2.3: for a zero, English orientation is a
        # REQUIRED scaffold, not a banned wall — every item is first exposure
        # (§2.2 R-D), so every item is glossed. Wide ceiling preserved: a
        # stronger learner can answer past the scaffold and de-escalates it.
        return ModeDecision(
            Mode.PLACEMENT,
            reason="blank_open_placement",
            hard_break=True,
            # Placement-open image ruling (Phase 5 batch 2): «hola» is
            # imageable:false in the association table (it cannot be R-B
            # meaning-bound), yet it IS the open-turn image — this is the
            # decision.image_concept SCENE-SETTING channel (a friendly
            # greeting illustration orienting a true-zero learner), exempt
            # from the imageable selection filter by adjudicated ruling.
            # The asset itself lives in the pack sidecar ("do we have an
            # asset"), which never widens R-B/association SELECTION.
            image_concept="hola",
            instructions=(
                "TRUE-ZERO OPENING (blank sheet — assume they may understand NO "
                "Spanish yet; every Spanish item here is a first exposure). "
                "REQUIRED shape: "
                "(1) ONE warm English welcome sentence framing what will happen "
                "— e.g. \"We'll go slowly — I'll always show you what things "
                "mean.\" "
                "(2) Tiny Spanish only: a greeting plus a name exchange — at "
                "most 3 Spanish items this turn. "
                "(3) EVERY Spanish item gets a short English gloss (≤6 words) "
                "right where it appears — nothing unglossed. "
                "(4) Make the try explicitly bilingual: «Try: Me llamo ___ — my "
                "name is ___». "
                "Wide-ceiling placement still applies: if they answer with more "
                "Spanish than this, follow them up. The English orientation is "
                "for the zero state ONLY — the moment they produce ANY Spanish, "
                "drop it and return to the standard mostly-Spanish register."
            ),
            scene_ids=[s.get("id") for s in open_scenes if s.get("id")],
        )
    if is_open and not blank:
        # Open from sheet abilities ONLY. Personal-data capture is disabled
        # (2026-07-28): no stored name, no personal hooks, no care rules.
        nb = sheet.get("next_best") or obs.get("next_best") or {}
        skills = sheet.get("skills") or {}

        def _conf(cid: str) -> float:
            sk = skills.get(cid) if isinstance(skills.get(cid), dict) else {}
            try:
                return float(sk.get("confidence") or 0)
            except (TypeError, ValueError):
                return 0.0

        shown = set(mem.get("shown") or [])
        lines = [
            "KNOWN LEARNER open — use the character sheet.",
            "We do NOT store the learner's name — greet warmly WITHOUT any "
            "name; never invent or guess one."
            " Warm SIMPLE A1 Spanish only; no intermediate idioms.",
        ]
        # Skip re-probing can-dos they already own
        if _conf("IP-04") >= 0.55 or "estoy" in shown:
            lines.append(
                "IP-04 / how-are-you is already solid — brief Hola is enough; "
                "do NOT make «¿Cómo estás?» the main try."
            )
        if _conf("IP-03") >= 0.4 or "name" in shown:
            lines.append(
                "They can already introduce themselves — do NOT ask "
                "«¿Cómo te llamas?» again."
            )
        if nb.get("can_do") or nb.get("activity") or nb.get("statement"):
            lines.append(
                "Steer the try toward sheet next_best: "
                f"{nb.get('can_do') or ''} / {nb.get('activity') or nb.get('stretch') or ''} — "
                f"{nb.get('statement') or nb.get('reason') or ''}."
            )
        if nb.get("error_pattern") or nb.get("form_focus") or nb.get("teach_hint"):
            lines.append(
                "Lightly weave form focus from sheet: "
                f"{nb.get('error_pattern') or nb.get('form_focus') or ''} — "
                f"{nb.get('teach_hint') or ''}"
            )
        elif obs.get("active_errors"):
            top = (obs.get("active_errors") or [{}])[0]
            if isinstance(top, dict) and top.get("id"):
                lines.append(
                    f"Active error on sheet: {top.get('id')} — recast/weave if natural."
                )
        lines.append(
            "One clear try that advances the sheet agenda — "
            "not a zero-placement greeting ladder."
        )
        phase_prefix = _phase_prefix(activity_hint, mem)
        if phase_prefix:
            lines.insert(0, phase_prefix)
        return ModeDecision(
            Mode.CONVERSATION,
            reason="known_open_from_sheet",
            hard_break=False,
            image_concept=None,
            scene_ids=[s.get("id") for s in open_scenes if s.get("id")],
            targets={
                "next_best": {
                    "can_do": nb.get("can_do"),
                    "activity": nb.get("activity") or nb.get("stretch"),
                    "error_pattern": nb.get("error_pattern"),
                },
                "preferred_name": None,
            },
            instructions=" ".join(lines),
        )

    # 3) Form errors FIRST — short correction must not be skipped for association
    #    (association after english_stuck used to bury recasts like está calor → hace calor)
    top = _top_active_error(sheet)
    if top and int(top.get("count") or 0) >= 2:
        pid = top["id"]
        # A correct use this turn resolves the pattern — never hard-break on a
        # form the learner just produced right; transfer/conversation handles it.
        if (
            pid not in resolves
            and pid not in state.form_focus_cooldown
            and can_hard
            and (pid in hit_ids or state.error_recent(pid))
        ):
            # Recency gate: no hard break on a stale count alone — the error
            # must have occurred this turn or within the last K learner turns.
            cat = ERROR_PATTERN_CATALOG.get(pid) or {}
            fresh_hit = pid in hit_ids
            base_instr = (
                f"Hard break pedagogical grammar for {pid}. Show short contrast "
                f"(wrong vs right). One choice or produce correct form. Then exit to transfer."
            )
            if not fresh_hit:
                # Streak fired from the SHEET, not from this message. Correcting
                # a clean turn reads as scolding for a mistake they didn't make
                # (2026-07-27: re-corrected 'llama' on a turn about travel).
                base_instr += (
                    " IMPORTANT: their CURRENT message did NOT contain this "
                    "error — do NOT correct or 're-correct' them now. First "
                    "respond to what they actually said, then frame the form "
                    "work as quick practice of a tricky form (playful, "
                    "'¿te acuerdas?'), never as fixing their message."
                )
            return ModeDecision(
                Mode.FORM_FOCUS,
                reason=f"error_streak:{pid}",
                hard_break=True,
                targets={
                    "error_pattern": pid,
                    "form_id": top.get("form_id") or cat.get("form_id"),
                    "teach_hint": top.get("teach_hint") or cat.get("teach_hint") or "",
                    "label": top.get("label") or pid,
                    "good_models": _good_models(pid),
                    "contrast": _contrast_for(pid),
                    "fresh_hit": fresh_hit,
                },
                instructions=base_instr,
            )

    # Soft recast: any clear form hit this turn — keep chat moving after a short correction
    if hits:
        pid = hits[0][0]
        good = _good_models(pid)
        contrast = _contrast_for(pid)
        return ModeDecision(
            Mode.CF_RECAST,
            reason=f"single_error:{pid}",
            hard_break=False,
            # No auto-picked image: dual-coding on a recast is the TUTOR's
            # call now (<image concept="…"/>), not a noun-scanner's
            targets={
                "error_pattern": pid,
                "snippet": hits[0][1],
                "good_models": good,
                "contrast": contrast,
                "require_recast_tag": True,
            },
            instructions=(
                "REQUIRED: put the clean form in <recast> (one short line, Spanish). "
                f"Prefer: {good[0] if good else 'correct form'}. "
                "Do NOT only bury the fix inside acknowledge. "
                "Then continue the conversation with one try — do not derail into a grammar lecture. "
                "English only if they asked 'why' / meta about the form."
            ),
        )

    # 4) Stuck English → association (picture kills English wall)
    #    Only after form-error handling so broken Spanish is not misrouted here.
    #    CHAR-BUG-002 RESOLVED (Phase 4 batch 3): the streak has ONE owner —
    #    conv_session's stage_english_streak, which counts the CURRENT turn
    #    BEFORE select_mode runs.  Guard 4 reads the state only; the old
    #    `+ 1` here double-counted the current turn, so the >=2 hard break
    #    fired on the FIRST English-only turn.  A hard break now requires a
    #    GENUINE streak (second consecutive English-only turn) or no_entiendo.
    eng_streak = state.english_only_streak
    no_entiendo = bool(
        learner and re_search_no_entiendo(learner)
    )
    if can_hard and (eng_streak >= 2 or no_entiendo) and "spanish_ok" not in signals:
        concept = _noun_from_text(learner, sheet, images_shown=shown_imgs) or (
            _fallback_association_concept(sheet, shown_imgs)
        )
        return ModeDecision(
            Mode.ASSOCIATION,
            reason="english_stuck_association",
            hard_break=True,
            image_concept=concept,
            targets={"concept": concept, "form": _form_for_concept(concept)},
            instructions=(
                f"Hard break: show meaning with image for '{concept}'. Spanish form only; "
                "minimal English. Invite them to use the form about the picture."
            ),
        )

    # 5) Just resolved focus form → transfer
    if state.last_resolved_form or (resolves & set((sheet.get("error_patterns") or {}).keys())):
        form = state.last_resolved_form
        if not form and resolves:
            form = next(iter(resolves))
        return ModeDecision(
            Mode.TRANSFER,
            reason="success_transfer",
            hard_break=False,
            targets={"form_id": form, "transfer": True},
            instructions=(
                "They just used the form well. Same form, NEW micro-context "
                "(different place/person/topic). Do not re-drill."
            ),
            scene_ids=[s.get("id") for s in open_scenes if s.get("id")],
        )

    # 6) Concrete noun first-time this session → association (+ image)
    noun = _noun_from_text(learner, sheet, images_shown=shown_imgs) or _new_concrete_noun(
        signals, sheet, images_shown=shown_imgs
    )
    if noun:
        # Prefer hard association when budget allows; always set image_concept
        hard = can_hard
        return ModeDecision(
            Mode.ASSOCIATION if hard else Mode.CONVERSATION,
            reason=f"new_noun:{noun}",
            hard_break=hard,
            image_concept=noun,
            targets={"concept": noun, "form": _form_for_concept(noun)},
            instructions=(
                f"Bind '{noun}' / {_form_for_concept(noun)} to meaning with the image. "
                "Spanish-forward; one try about the referent. Minimal English."
            ),
        )

    # 7) Topic-matched open scene (before weak next_best).
    #    PHASE HOST rule 6 (Proposal A, 2026-07-29): the pick does NOT run
    #    when the session phase is new_input or close — introduce owns
    #    new_input and close owns close (PEDAGOGY §6.4); those turns fall
    #    through to default_conversation so the flavorable content blocks
    #    fire. The prefer-unmodeled fallback is DELETED (CHAR-BUG-005
    #    RESOLVED-BY-DELETION): only a live topic match reaches a scene here.
    sc = None
    if activity_hint not in ("new_input", "close"):
        sc = _scene_for_topic(open_scenes, learner=learner, signals=signals)
    if sc:
        goal = sc.get("goal") or {}
        inp = sc.get("input") or {}
        img = inp.get("image_concept")
        if img and img in shown_imgs:
            img = None  # already shown this session — don't re-wallpaper
        return ModeDecision(
            Mode.CONVERSATION,
            reason=f"scene_goal:{sc.get('id')}",
            hard_break=False,
            image_concept=img,
            targets={
                "can_do": goal.get("can_do"),
                "target_forms": goal.get("target_forms") or [],
                "model_lines": inp.get("model_lines") or [],
                "elicit": (sc.get("production") or {}).get("elicit"),
                "transfer": (sc.get("transfer") or {}).get("elicit"),
                "prefer_over_next_best": True,
            },
            scene_ids=[sc.get("id")] if sc.get("id") else [],
            instructions=(
                f"Pursue open scene goal '{sc.get('id')}' (can-do {goal.get('can_do')}) "
                "in natural chat — not a flashcard list. Prefer this over unrelated "
                "next_best stretches. Model target forms; one elicit; advance if they already can."
            ),
        )

    # 8) Default conversation (next_best is a weak guide only)
    nb = (sheet.get("next_best") or {})
    default_instr = (
        "Real Spanish conversation. React to them first. One elicit. Teach with model+try. "
        "No re-asking covered probes. next_best is optional if the live topic is richer."
    )
    phase_prefix = _phase_prefix(activity_hint, mem)
    if phase_prefix:
        default_instr = phase_prefix + "\n" + default_instr
    return ModeDecision(
        Mode.CONVERSATION,
        reason="default_conversation",
        hard_break=False,
        targets={
            "can_do": nb.get("can_do"),
            "next_best": nb.get("statement") or nb.get("activity"),
            "next_best_is_optional": True,
        },
        scene_ids=[s.get("id") for s in open_scenes if s.get("id")],
        instructions=default_instr,
    )


def re_search_no_entiendo(text: str) -> bool:
    import re
    low = (text or "").lower()
    return bool(
        re.search(r"\bno\s+entiendo\b|\bdon'?t\s+understand\b|\bwhat\s+does\s+.+\s+mean\b", low)
    )


def _simplify_try(try_text: str) -> str:
    """Heuristic simpler re-elicit of the same intent (not a new topic)."""
    t = (try_text or "").strip()
    if not t:
        return ""
    low = t.lower()
    # Map common intermediate opens to simpler A1
    if "cómo van" in low or "como van" in low or "las cosas" in low:
        if "río" in low or "rio" in low or "dulce" in low:
            return "¿Cómo estás hoy en Río Dulce?"
        return "¿Cómo estás hoy?"
    if "saludarte" in low or "gusto" in low:
        return "¡Hola! ¿Cómo estás?"
    if "dónde estás" in low or "donde estas" in low:
        return "¿Dónde estás?"
    if "te gusta" in low:
        return t  # already simple
    # Default: keep same try (executor will simplify wording)
    return t


def _form_for_concept(concept: str) -> str:
    return {
        "cafe": "el café",
        "bote": "el bote",
        "musica": "la música",
        "comida": "la comida",
        "rio": "el río",
        "edificio": "el edificio",
        "casa": "la casa",
        "playa": "la playa",
        "perro": "el perro",
        "gato": "el gato",
        "agua": "el agua",
        "sol": "el sol",
        "calor": "el calor",
        "frio": "el frío",
        "hola": "Hola",
        "estoy_bien": "Estoy bien",
        "me_llamo": "Me llamo…",
    }.get(concept or "", concept or "")


def _good_models(pid: str) -> list[str]:
    if pid == "estar_yo_estoy_vs_esta":
        return ["Estoy bien.", "Estoy en el bote."]
    if pid == "me_llamo_es":
        return ["Me llamo…"]
    if pid == "soy_de_origin":
        return ["Soy de…"]
    if pid == "ser_estar_confuse":
        return ["Estoy bien.", "Soy de Colombia."]
    if pid == "gender_number_article":
        return ["los edificios", "las casas", "Me gustan los edificios."]
    if pid == "weather_hace":
        return ["Hace calor.", "Hace un poco de calor.", "Hace frío."]
    return ["Estoy bien."]


def _contrast_for(pid: str) -> dict[str, str]:
    if pid == "estar_yo_estoy_vs_esta":
        return {"avoid": "Yo está bien", "prefer": "Estoy bien", "hint": "With yo use estoy."}
    if pid == "ser_estar_confuse":
        return {"avoid": "Soy bien", "prefer": "Estoy bien", "hint": "Feelings/location → estar."}
    if pid == "me_llamo_es":
        return {"avoid": "Me llamo es…", "prefer": "Me llamo…", "hint": "No es after me llamo."}
    if pid == "soy_de_origin":
        return {"avoid": "Estoy de…", "prefer": "Soy de…", "hint": "Origin → ser de."}
    if pid == "gender_number_article":
        return {
            "avoid": "la edificios / me gusta los…",
            "prefer": "los edificios / me gustan los…",
            "hint": "Article and noun must match number/gender; plural often *gustan*.",
        }
    if pid == "weather_hace":
        return {
            "avoid": "Está calor / Es calor",
            "prefer": "Hace calor",
            "hint": "Weather heat/cold → hace (not está).",
        }
    return {"prefer": "Estoy bien.", "hint": ""}


def mode_executor_brief(decision: ModeDecision) -> str:
    """Short instructions block for the AI tutor."""
    lines = [
        f"MODE: {decision.mode.value}",
        f"REASON: {decision.reason}",
        f"HARD_BREAK: {decision.hard_break}",
        decision.instructions,
    ]
    if decision.targets:
        lines.append(f"TARGETS: {decision.targets}")
    if decision.image_concept:
        lines.append(f"IMAGE_CONCEPT: {decision.image_concept}")
    if decision.scene_ids:
        lines.append(f"OPEN_SCENES: {decision.scene_ids}")
    return "\n".join(lines)
