"""Per-session pedagogy memory — what we already probed / they already showed.

Stops re-asking ¿Cómo estás? / ¿Cómo te llamas? after success.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .rules_planner import probe_signals


@dataclass
class SessionMemory:
    """Accumulates evidence and recent try-keys within one chat session."""

    shown: set[str] = field(default_factory=set)  # skills learner demonstrated
    asked: set[str] = field(default_factory=set)  # probe keys we already tried
    turns: int = 0
    last_learner: str = ""

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
        return sig

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

    def already_asked(self, *keys: str) -> bool:
        return any(k in self.asked for k in keys)

    def already_shown(self, *keys: str) -> bool:
        return any(k in self.shown for k in keys)

    def snapshot(self) -> dict:
        return {
            "shown": sorted(self.shown),
            "asked": sorted(self.asked),
            "turns": self.turns,
        }


def re_search_origin(low: str) -> bool:
    import re
    return bool(re.search(r"\bsoy\s+de\b", low) or re.search(r"\bde\s+(estados|ee\.?uu|usa|guatemala|méxico|mexico)\b", low))


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
    return r[:40] if r else ""
