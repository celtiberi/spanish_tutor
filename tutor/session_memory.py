"""Per-session pedagogy memory — what we already probed / they already showed.

Stops re-asking ¿Cómo estás? / ¿Cómo te llamas? after success.
Also tracks last tutor models/try for comprehension repair (re-ask same idea).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .association_table import cached_default_table, content_topic_keys
from .observe import probe_signals
# Phase 2 (docs/reviews-architecture-refactor.md): fold_lexical is the named
# home of the old local _deaccent — 6-vowel fold (incl. ü), KEEPS ñ, keeps
# spaces. Registry keys and output_gate's due-exemption share this policy.
from .textnorm import SPANISH_LETTERS, fold_asset_key, fold_lexical

# r7 §5 precondition: max 2 new-item introductions per session at A1
# (docs/pedagogy-research-r7-association-intro.md; stopgap owner until the
# Phase-2 SessionPhaseController takes over budgets).
INTRO_BUDGET_PER_SESSION = 2


# --- Asked-topic registry (2026-07-28 repetition forensics) -----------------
# The old `asked` set stored MODE NAMES (note_plan_try recorded
# decision.mode.value → "conversation", "association" …), which told the
# model nothing about WHAT was asked. The registry stores semantic keys
# derived from the composed try: "<frame>:<concept>" ("size:ciudad",
# "location:casa") or a bare frame ("wellbeing"). Surface-form spotting only
# — the legitimate §4.2 regex use; imperfect coverage is fine.
TOPIC_FRAME_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("wellbeing", re.compile(r"c[oó]mo\s+est[aá]s|how\s+are\s+you", re.I)),
    ("name", re.compile(r"c[oó]mo\s+te\s+llamas|your\s+name", re.I)),
    ("location", re.compile(r"\bd[oó]nde\b|\bwhere\b", re.I)),
    ("size", re.compile(r"\bgrande\b|pequeñ|\bsize\b|\bbig\b|\bsmall\b", re.I)),
]
_WHAT_VERB_RE = re.compile(rf"(?:¿\s*|\b)qu[eé]\s+([{SPANISH_LETTERS}]+)", re.I)

# ---------------------------------------------------------------------------
# Topic-concept palette — TABLE-DERIVED (Phase 5 batch 2 flip, BROADENED,
# docs/reviews-architecture-refactor.md).  The old hardcoded 21-string list
# is gone; membership now comes from the association table.  Two tiers:
#   1. Priority tier: the recorded legacy priority ORDER (incident nouns
#      ciudad/casa lead) — order is behavior-bearing because
#      topic_key_for_try binds the FIRST palette noun present in the try
#      («¿Está en una ciudad grande tu casa?» must stay size:ciudad).
#      Surfaces = table key + its accent-folded variant (word_present does
#      no accent folding; tutor tries may be typed unaccented).
#   2. Tail: every OTHER content table key (content_topic_keys — structural
#      themes/keys excluded), table order.
# Declared deltas vs the legacy production palette (conv_session._topic_nouns
# = 21 strings + ALL table keys): (a) pronouns / question words / copulas /
# numbers / hay no longer bind as topic concepts — CHAR-BUG-007 RESOLVED
# («¿Dónde estás tú?» → location, not location:tu); (b) the module default
# now EQUALS the production palette (the old module constant was a narrower
# divergent default used only when callers passed no nouns).
# ---------------------------------------------------------------------------

# Legacy priority membership + order (recorded, validated against the table).
_TOPIC_PRIORITY_KEYS: tuple[str, ...] = (
    "ciudad", "casa", "playa", "bote", "barco", "café", "música", "comida",
    "río", "edificio", "perro", "gato", "agua", "sol", "trabajo", "familia",
    "desayuno", "pan",
)


def topic_palette(table: dict | None) -> list[str]:
    """Topic-concept palette for ``table``: priority tier first (legacy
    order, accent variants included), then the table's remaining content
    keys.  ONE derivation for the module default AND the per-session
    palette (conv_session._topic_nouns) — no second list."""
    out: list[str] = []
    seen: set[str] = set()
    for key in _TOPIC_PRIORITY_KEYS:
        for surface in (key, fold_lexical(key)):
            if surface not in seen:
                seen.add(surface)
                out.append(surface)
    for key in content_topic_keys(table):
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _derived_topic_concept_nouns() -> tuple[str, ...]:
    table = cached_default_table()
    missing = [k for k in _TOPIC_PRIORITY_KEYS if k not in table]
    if missing:
        raise ValueError(
            f"topic priority keys not in association table: {missing}"
        )
    return tuple(topic_palette(table))


TOPIC_CONCEPT_NOUNS: tuple[str, ...] = _derived_topic_concept_nouns()

# ---------------------------------------------------------------------------
# _concepts_from_spanish needle→concept pairs — TABLE-DERIVED (Phase 5
# batch 2 flip, CONSERVATIVE).  Membership = the recorded legacy repair-
# concept set, validated against the table; concept ids = fold_asset_key of
# the table key (the asset/sidecar id, so repair images keep resolving).
# Needle strings remain learner/tutor-surface DETECTION text (§1.1a allowed
# class iv): key + accent-folded variant, plus the recorded authored extras.
# Deliberate keeps (batch-1 flags): «barco» stays its own TABLE key but maps
# to the «bote» asset id here (sidecar alias — one referent, one image);
# «estoy» stays a detection needle for the «estoy bien» formula (any
# estoy-sentence marks the wellbeing concept, exactly as before).
# This list feeds comprehension-repair image concepts (routing) → the brief
# prefers conservative: membership unchanged, now table-validated.
# ---------------------------------------------------------------------------

_REPAIR_CONCEPT_SPEC: tuple[tuple[str, str], ...] = (
    # (table key providing the concept id, table key/surface it rides on)
    ("río", "río"),
    ("bote", "bote"), ("bote", "barco"),
    ("café", "café"),
    ("música", "música"),
    ("comida", "comida"),
    ("hola", "hola"),
    ("estoy bien", "estoy bien"),
)
# Authored detection extras (§1.1a class iv — surface text, not inventory).
_REPAIR_AUTHORED_NEEDLES: dict[str, tuple[str, ...]] = {
    "estoy bien": ("estoy",),
}


def _derived_spanish_concept_pairs() -> tuple[tuple[str, str], ...]:
    table = cached_default_table()
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for concept_key, surface_key in _REPAIR_CONCEPT_SPEC:
        if concept_key not in table or surface_key not in table:
            raise ValueError(
                "repair concept spec references non-table keys: "
                f"{concept_key!r}/{surface_key!r}"
            )
        concept = fold_asset_key(concept_key)
        needles = [surface_key, fold_lexical(surface_key)]
        needles += list(_REPAIR_AUTHORED_NEEDLES.get(surface_key, ()))
        for needle in needles:
            if (needle, concept) not in seen:
                seen.add((needle, concept))
                pairs.append((needle, concept))
    return tuple(pairs)


SPANISH_CONCEPT_PAIRS: tuple[tuple[str, str], ...] = (
    _derived_spanish_concept_pairs()
)


def compose_topic_key(frame: str, concept: str = "") -> str:
    """Canonical registry key: "<frame>:<concept>" or the bare frame."""
    f = fold_lexical((frame or "").strip())
    if not f:
        return ""
    c = fold_lexical((concept or "").strip())
    return f"{f}:{c}" if c else f


def topic_key_for_try(
    try_text: str, nouns=None
) -> tuple[str, str]:
    """(frame, concept) semantic key for a composed tutor try, or ("", "").

    Question-frame patterns: dónde/where→location, grande|pequeñ|size→size,
    cómo estás→wellbeing, cómo te llamas→name, qué+verb→what:<verb>.
    Concept = first pack/table noun present via textnorm.word_present.
    """
    from .textnorm import word_present

    low = (try_text or "").lower()
    if not low.strip():
        return "", ""
    frame = ""
    for name, pat in TOPIC_FRAME_PATTERNS:
        if pat.search(low):
            frame = name
            break
    if not frame:
        m = _WHAT_VERB_RE.search(low)
        if m:
            frame = f"what:{fold_lexical(m.group(1))}"
    if not frame:
        return "", ""
    concept = ""
    for n in (nouns if nouns is not None else TOPIC_CONCEPT_NOUNS):
        if n and word_present(str(n), low):
            concept = fold_lexical(str(n))
            break
    return frame, concept


@dataclass
class SessionMemory:
    """Accumulates evidence and recent try-keys within one chat session."""

    shown: set[str] = field(default_factory=set)  # skills learner demonstrated
    asked: set[str] = field(default_factory=set)  # probe keys we already tried
    # Semantic asked-topic registry ("size:ciudad", "location:casa", …) —
    # 2026-07-28 repetition forensics; feeds do_not_re_ask + gate:probe_loop.
    asked_topics: set[str] = field(default_factory=set)
    # Concepts guard 6 (new_noun) already fired on THIS session — recorded
    # even when no image/lexicon write happened, so the same concept cannot
    # re-fire (the old conf<0.25 escape hatch re-fired new_noun:casa forever
    # on a reset sheet).
    covered_concepts: set[str] = field(default_factory=set)
    images_shown: set[str] = field(default_factory=set)  # teach-image concepts shown
    last_image_turn: int = -999  # session turn index when last image shown
    # Generation budget (novel images bill $0.039 each; caps in conv_session)
    images_generated: int = 0
    images_declared_generated: int = 0
    # Turns until the tutor may declare another image (anti over-declaration)
    declared_image_cooldown: int = 0
    turns: int = 0
    last_learner: str = ""
    # Last tutor linguistic targets — for "I didn't understand" repair
    last_tutor_try: str = ""
    last_tutor_model: str = ""
    last_tutor_ack: str = ""
    last_concepts: list[str] = field(default_factory=list)
    # If True, next mode should repair same try (not advance topic).
    # TTL-bounded: lives for exactly ONE following learner turn — a sticky
    # hold hijacked clean turns twice (Grok round-1 C, 2026-07-28).
    await_comprehension: bool = False
    await_comprehension_ttl: int = 0
    # True after seed_from_sheet — open must not treat them as blank
    sheet_seeded: bool = False
    # Introduce-ledger session counter (r7 S1): keys introduced THIS session.
    # Keys may be multiword units ("hasta luego"). Budget: ≤2 per session.
    introduced_this_session: list[str] = field(default_factory=list)

    @property
    def turns_since_image(self) -> int:
        if self.last_image_turn < 0:
            return 999
        return max(0, self.turns - self.last_image_turn)

    def note_learner(
        self, text: str, extra_signals: set[str] | None = None
    ) -> set[str]:
        """Record learner turn. `extra_signals` come from the LLM intent
        classifier (authority for routing intent); regex probe_signals remain
        for surface-form detection and as fallback."""
        sig = probe_signals(text) | set(extra_signals or [])
        # Map signals to stable skill keys
        mapping = {
            "greet": "greet",
            "estoy": "estoy",
            "name": "name",
            "ask_name": "ask_name",
            "ask_how": "ask_how",
            "gusta": "gusta",
            "topic_vocab": "topic",
            "spanish_ok": "spanish_ok",
            "multi_skill": "multi_skill",
            "english_only": "english_only",
            "meta_comprehension": "meta_comprehension",
        }
        for s, k in mapping.items():
            if s in sig:
                self.shown.add(k)
        # Origin
        low = (text or "").lower()
        if re_search_origin(low):
            self.shown.add("origin")
        self.last_learner = text or ""
        self.turns += 1
        if self.declared_image_cooldown > 0:
            self.declared_image_cooldown -= 1
        # Hold semantics (Grok round-1 C, 2026-07-28): arm ONLY on pure
        # non-comprehension (meta without own Spanish); help/topic requests
        # clear; TTL bounds the hold to ONE following learner turn.
        if "topic_request" in sig or "help_request" in sig:
            self.await_comprehension = False
            self.await_comprehension_ttl = 0
        elif "meta_comprehension" in sig and "spanish_ok" not in sig:
            self.await_comprehension = True
            self.await_comprehension_ttl = 1
        elif self.await_comprehension:
            # ttl=1 at arm → active on the next turn (ttl→0), gone after
            self.await_comprehension_ttl -= 1
            if self.await_comprehension_ttl < 0:
                self.await_comprehension = False
        return sig

    def note_image(self, concept: str | None) -> None:
        """Record that we displayed a teach image this turn."""
        c = (concept or "").strip().lower()
        if not c:
            return
        self.images_shown.add(c)
        self.last_image_turn = self.turns

    def note_tutor_turn(
        self,
        *,
        model: str = "",
        try_: str = "",
        acknowledge: str = "",
        concepts: list[str] | None = None,
    ) -> None:
        """Remember what we just taught / asked (for repair if they don't get it)."""
        self.last_tutor_model = (model or "").strip()
        self.last_tutor_try = (try_ or "").strip()
        self.last_tutor_ack = (acknowledge or "").strip()
        if concepts:
            self.last_concepts = [c for c in concepts if c]
        else:
            self.last_concepts = _concepts_from_spanish(
                f"{self.last_tutor_model} {self.last_tutor_try} {self.last_tutor_ack}"
            )
        # After we re-elicit successfully (learner answered in Spanish), clear below
        # Callers set await_comprehension False when learner produces Spanish_ok without meta

    def note_plan_try(self, reason: str, try_prompt: str) -> None:
        """Record what we asked so we don't loop."""
        key = _try_key(reason, try_prompt)
        if key:
            self.asked.add(key)
        # Also mark by content (try text + reason)
        blob = f"{reason or ''} {try_prompt or ''}".lower()
        flat = (
            blob.replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )
        if "como estas" in flat or "how they are" in flat or "how are you" in flat:
            self.asked.add("ask_how")
        if "como te llamas" in flat or "their name" in flat or "ask_name" in flat:
            self.asked.add("ask_name")
        if "donde eres" in flat or "where they" in flat or "origin" in flat:
            self.asked.add("ask_origin")
        if "gusta" in flat or "like" in flat or "preference" in flat:
            self.asked.add("ask_gusta")

    def note_asked_topic(self, frame: str, concept: str = "") -> str:
        """Record a semantic asked-topic key ("size:ciudad"); returns it."""
        key = compose_topic_key(frame, concept)
        if key:
            self.asked_topics.add(key)
        return key

    def note_concept_covered(self, concept: str) -> None:
        """Mark a guard-6 concept as covered for the rest of the session."""
        c = (concept or "").strip().lower()
        if c:
            self.covered_concepts.add(c)

    def clear_comprehension_hold(self) -> None:
        self.await_comprehension = False
        self.await_comprehension_ttl = 0

    def intro_budget_remaining(self) -> int:
        """New-item introductions still allowed this session (r7: max 2)."""
        return max(
            0, INTRO_BUDGET_PER_SESSION - len(self.introduced_this_session)
        )

    def note_introduced(self, key: str) -> bool:
        """Record an introduce event; False when the budget is exhausted.

        Never touches the ability sheet — the durable ledger write lives in
        tutor/retrieval_scheduler.mark_introduced.
        """
        k = (key or "").strip()
        if not k:
            return False
        if k in self.introduced_this_session:
            return True
        if self.intro_budget_remaining() <= 0:
            return False
        self.introduced_this_session.append(k)
        return True

    def already_asked(self, *keys: str) -> bool:
        return any(k in self.asked for k in keys)

    def already_shown(self, *keys: str) -> bool:
        return any(k in self.shown for k in keys)

    def seed_from_sheet(
        self, sheet: dict | None, profile: dict | None = None
    ) -> None:
        """Preload known can-dos so a new chat does not re-probe from zero.

        Character sheet is durable; chat memory is not. Without this, every
        page refresh treats Patrick like a blank placement learner. The
        learner's name comes from the profile (legacy sheets as fallback).
        """
        if not isinstance(sheet, dict):
            return
        skills = sheet.get("skills") or {}
        # can-do → session probe keys
        mapping = {
            "IP-01": ("greet",),
            "IP-03": ("name",),
            "IP-04": ("estoy",),
            "IP-06": ("gusta",),
            "IP-07": ("spanish_ok", "multi_skill"),
        }
        for cid, keys in mapping.items():
            sk = skills.get(cid) if isinstance(skills.get(cid), dict) else {}
            try:
                conf = float(sk.get("confidence") or 0)
            except (TypeError, ValueError):
                conf = 0.0
            status = str(sk.get("status") or "").lower()
            if conf >= 0.45 or status in ("known", "emerging", "fragile"):
                for k in keys:
                    self.shown.add(k)
        name = (
            (profile or {}).get("preferred_name")
            or (sheet.get("identity") or {}).get("preferred_name")
            or ""
        ).strip()
        if name:
            self.shown.add("name")
            # Do not re-ask name in a new chat when we already store it
            self.asked.add("ask_name")
        sk4 = skills.get("IP-04") if isinstance(skills.get("IP-04"), dict) else {}
        try:
            c4 = float(sk4.get("confidence") or 0)
        except (TypeError, ValueError):
            c4 = 0.0
        if c4 >= 0.55 or str(sk4.get("status") or "").lower() == "known":
            self.shown.add("estoy")
            # Mark ask_how so open/modes prefer advancing over wellbeing drill
            self.asked.add("ask_how")
        self.sheet_seeded = True

    def snapshot(self) -> dict:
        return {
            "shown": sorted(self.shown),
            "asked": sorted(self.asked),
            "asked_topics": sorted(self.asked_topics),
            "covered_concepts": sorted(self.covered_concepts),
            "images_shown": sorted(self.images_shown),
            "turns_since_image": self.turns_since_image,
            "last_image_turn": self.last_image_turn,
            "turns": self.turns,
            "last_tutor_try": self.last_tutor_try,
            "last_tutor_model": self.last_tutor_model,
            "last_concepts": list(self.last_concepts),
            "await_comprehension": self.await_comprehension,
            "await_comprehension_ttl": self.await_comprehension_ttl,
            "sheet_seeded": self.sheet_seeded,
            "introduced_this_session": list(self.introduced_this_session),
            "intro_budget_remaining": self.intro_budget_remaining(),
        }

    @classmethod
    def from_snapshot(cls, data: dict | None) -> "SessionMemory":
        """Rebuild from ``snapshot()`` output — the E2 persistence restore
        (Phase 1 batch 2, docs/reviews-architecture-refactor.md).

        ``snapshot()`` alone is lossy (its shape is pinned by prompt/debug
        consumers): last_learner, last_tutor_ack, images_generated,
        images_declared_generated and declared_image_cooldown do not appear
        in it. The SessionState aggregate supplies those as sibling keys in
        the same dict; absent keys restore to their dataclass defaults.
        Derived keys (turns_since_image, intro_budget_remaining) are
        ignored — they recompute from the restored fields.
        """
        d = data if isinstance(data, dict) else {}

        def _num(key: str, default: int) -> int:
            try:
                v = d.get(key, default)
                return default if v is None else int(v)
            except (TypeError, ValueError):
                return default

        m = cls()
        m.shown = {str(x) for x in d.get("shown") or []}
        m.asked = {str(x) for x in d.get("asked") or []}
        m.asked_topics = {str(x) for x in d.get("asked_topics") or []}
        m.covered_concepts = {str(x) for x in d.get("covered_concepts") or []}
        m.images_shown = {str(x) for x in d.get("images_shown") or []}
        m.last_image_turn = _num("last_image_turn", -999)
        m.images_generated = _num("images_generated", 0)
        m.images_declared_generated = _num("images_declared_generated", 0)
        m.declared_image_cooldown = _num("declared_image_cooldown", 0)
        m.turns = _num("turns", 0)
        m.last_learner = str(d.get("last_learner") or "")
        m.last_tutor_try = str(d.get("last_tutor_try") or "")
        m.last_tutor_model = str(d.get("last_tutor_model") or "")
        m.last_tutor_ack = str(d.get("last_tutor_ack") or "")
        m.last_concepts = [str(c) for c in d.get("last_concepts") or []]
        m.await_comprehension = bool(d.get("await_comprehension"))
        m.await_comprehension_ttl = _num("await_comprehension_ttl", 0)
        m.sheet_seeded = bool(d.get("sheet_seeded"))
        m.introduced_this_session = [
            str(k) for k in d.get("introduced_this_session") or []
        ]
        return m


def re_search_origin(low: str) -> bool:
    return bool(
        re.search(r"\bsoy\s+de\b", low)
        or re.search(r"\bde\s+(estados|ee\.?uu|usa|guatemala|méxico|mexico)\b", low)
    )


def _concepts_from_spanish(text: str) -> list[str]:
    from .textnorm import word_present

    low = (text or "").lower()
    out: list[str] = []
    seen: set[str] = set()
    for needle, concept in SPANISH_CONCEPT_PAIRS:
        # Word-boundary match: 'rio' must not fire inside 'serio'/'vario'
        if word_present(needle, low) and concept not in seen:
            seen.add(concept)
            out.append(concept)
    return out


def _try_key(reason: str, try_prompt: str) -> str:
    r = (reason or "").lower()
    if "open" in r or "comm_open" in r:
        return "ask_how"
    if "name" in r and "origin" not in r:
        return "ask_name"
    if "origin" in r:
        return "ask_origin"
    if "gusta" in r or "preference" in r:
        return "ask_gusta"
    if "comprehension" in r or "repair" in r:
        return "comprehension_repair"
    return r[:40] if r else ""
