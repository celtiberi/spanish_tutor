"""Per-session pedagogy memory — what we already probed / they already showed.

Stops re-asking ¿Cómo estás? / ¿Cómo te llamas? after success.
Also tracks last tutor models/try for comprehension repair (re-ask same idea).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .observe import probe_signals


@dataclass
class SessionMemory:
    """Accumulates evidence and recent try-keys within one chat session."""

    shown: set[str] = field(default_factory=set)  # skills learner demonstrated
    asked: set[str] = field(default_factory=set)  # probe keys we already tried
    images_shown: set[str] = field(default_factory=set)  # teach-image concepts shown
    last_image_turn: int = -999  # session turn index when last image shown
    turns: int = 0
    last_learner: str = ""
    # Last tutor linguistic targets — for "I didn't understand" repair
    last_tutor_try: str = ""
    last_tutor_model: str = ""
    last_tutor_ack: str = ""
    last_concepts: list[str] = field(default_factory=list)
    # If True, next mode should repair same try (not advance topic)
    await_comprehension: bool = False

    @property
    def turns_since_image(self) -> int:
        if self.last_image_turn < 0:
            return 999
        return max(0, self.turns - self.last_image_turn)

    def note_learner(self, text: str) -> set[str]:
        sig = probe_signals(text)
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
        if "meta_comprehension" in sig or "english_only" in sig:
            self.await_comprehension = True
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

    def already_asked(self, *keys: str) -> bool:
        return any(k in self.asked for k in keys)

    def already_shown(self, *keys: str) -> bool:
        return any(k in self.shown for k in keys)

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
        }


def re_search_origin(low: str) -> bool:
    return bool(
        re.search(r"\bsoy\s+de\b", low)
        or re.search(r"\bde\s+(estados|ee\.?uu|usa|guatemala|méxico|mexico)\b", low)
    )


def _concepts_from_spanish(text: str) -> list[str]:
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
        if needle in low and concept not in seen:
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
