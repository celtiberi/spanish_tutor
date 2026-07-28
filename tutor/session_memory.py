"""Per-session pedagogy memory — what we already probed / they already showed.

Stops re-asking ¿Cómo estás? / ¿Cómo te llamas? after success.
Also tracks last tutor models/try for comprehension repair (re-ask same idea).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .observe import probe_signals

# r7 §5 precondition: max 2 new-item introductions per session at A1
# (docs/pedagogy-research-r7-association-intro.md; stopgap owner until the
# Phase-2 SessionPhaseController takes over budgets).
INTRO_BUDGET_PER_SESSION = 2


@dataclass
class SessionMemory:
    """Accumulates evidence and recent try-keys within one chat session."""

    shown: set[str] = field(default_factory=set)  # skills learner demonstrated
    asked: set[str] = field(default_factory=set)  # probe keys we already tried
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


def re_search_origin(low: str) -> bool:
    return bool(
        re.search(r"\bsoy\s+de\b", low)
        or re.search(r"\bde\s+(estados|ee\.?uu|usa|guatemala|méxico|mexico)\b", low)
    )


def _concepts_from_spanish(text: str) -> list[str]:
    from .observe import word_present

    low = (text or "").lower()
    out: list[str] = []
    mapping = [
        ("río", "rio"), ("rio", "rio"),
        ("bote", "bote"), ("barco", "bote"),
        ("café", "cafe"), ("cafe", "cafe"),
        ("música", "musica"), ("musica", "musica"),
        ("comida", "comida"),
        ("hola", "hola"),
        ("estoy", "estoy_bien"),
    ]
    seen: set[str] = set()
    for needle, concept in mapping:
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
