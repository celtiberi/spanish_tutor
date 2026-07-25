"""AI student (Grok) vs conversational Spanish tutor — simulation harness.

Grok maintains a structured **learner_state** each turn (forms noticed,
confidence, can_try_now) so it can simulate learning across the full chat.

  python -m tutor.ai_student
  python -m tutor.ai_student --turns 8 --persona alex_boat
  python -m tutor.ai_student --level intermediate_low --persona jordan_travel

Env:
  AI_STUDENT_MODEL   default grok-4.5
  TUTOR_MODEL        teacher model (default gemini-3.6-flash)
  GROK_API_KEY       required for the student
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config
from .character_sheet import (
    format_sheet_human,
    load_sheet,
)
from .conv_session import ConversationalSession
from .term import paint, palette

STUDENT_PROMPT = config.REPO_ROOT / "prompts" / "ai_student.md"
DEFAULT_STUDENT_SHEET = config.REPO_ROOT / "logs" / "ai_student_sheet.json"
DEFAULT_STUDENT_MODEL = "grok-4.5"
DEFAULT_TURNS = 6

LEARNER_STATE_OPEN = re.compile(r"<learner_state>", re.I)
LEARNER_STATE_CLOSE = re.compile(r"</learner_state>", re.I)

# ---------------------------------------------------------------------------
# Ability levels (first-class bands Grok must obey)
# ---------------------------------------------------------------------------

ABILITY_LEVELS: dict[str, dict[str, Any]] = {
    "novice_low": {
        "id": "novice_low",
        "label": "Novice Low",
        "description": (
            "Very limited Spanish. Mostly English with a few memorized words. "
            "Heavy hesitation. Fragments OK. Often wrong person on estar."
        ),
        "english_ratio": 0.55,
        "max_spanish_words": 10,
        "sentence_complexity": "fragments_or_one_clause",
        "inventory": [
            "hola", "gracias", "sí", "no", "ok", "um", "café", "bote", "bien",
        ],
        "avoid_grammar": [
            "subjunctive", "past tense", "long relative clauses", "por/para nuance",
        ],
        "default_form_seeds": {
            "estoy_yo": {
                "status": "error_prone",
                "confidence": 0.15,
                "attempts": 0,
                "successes": 0,
                "note": "tends to say yo está",
            },
            "greetings": {
                "status": "emerging",
                "confidence": 0.4,
                "attempts": 0,
                "successes": 0,
            },
        },
    },
    "novice_mid": {
        "id": "novice_mid",
        "label": "Novice Mid",
        "description": (
            "Can do short formulaic exchanges. Mixes EN/ES. Some correct "
            "present-tense phrases; still confuses ser/estar and articles."
        ),
        "english_ratio": 0.35,
        "max_spanish_words": 18,
        "sentence_complexity": "one_or_two_simple_clauses",
        "inventory": [
            "hola", "gracias", "me llamo", "me gusta", "sí", "no", "café",
            "familia", "hoy", "un poco",
        ],
        "avoid_grammar": ["subjunctive", "compound past", "conditionals"],
        "default_form_seeds": {
            "ser_estar": {
                "status": "error_prone",
                "confidence": 0.25,
                "attempts": 0,
                "successes": 0,
                "note": "soy nerviosa / soy bien",
            },
            "me_gusta": {
                "status": "emerging",
                "confidence": 0.45,
                "attempts": 0,
                "successes": 0,
            },
            "greetings": {
                "status": "usable",
                "confidence": 0.6,
                "attempts": 0,
                "successes": 0,
            },
        },
    },
    "intermediate_low": {
        "id": "intermediate_low",
        "label": "Intermediate Low",
        "description": (
            "Can handle simple personal questions in Spanish with some English "
            "backup. Occasional agreement errors; past tense rare and shaky."
        ),
        "english_ratio": 0.15,
        "max_spanish_words": 35,
        "sentence_complexity": "connected_simple_sentences",
        "inventory": [
            "present tense", "me gusta", "porque", "también", "pero",
            "questions with qué/dónde/cómo",
        ],
        "avoid_grammar": ["subjunctive", "advanced connectors"],
        "default_form_seeds": {
            "estoy_yo": {
                "status": "usable",
                "confidence": 0.65,
                "attempts": 0,
                "successes": 0,
            },
            "me_gusta": {
                "status": "usable",
                "confidence": 0.7,
                "attempts": 0,
                "successes": 0,
            },
            "simple_questions": {
                "status": "emerging",
                "confidence": 0.4,
                "attempts": 0,
                "successes": 0,
            },
        },
    },
}

# ---------------------------------------------------------------------------
# Personas (personality + focus errors on top of an ability band)
# ---------------------------------------------------------------------------

PERSONAS: dict[str, dict[str, Any]] = {
    "alex_boat": {
        "id": "alex_boat",
        "name": "Alex",
        "personality": (
            "Friendly English-speaking sailor living on a small boat. "
            "Curious, a bit shy about Spanish, good-humored. Talks about "
            "weather, coffee, the river, and travel."
        ),
        "ability": "novice_low",
        "L1": "English",
        "interests": ["boats", "Río Dulce", "coffee", "weather", "simple travel"],
        "solid_phrases": ["hola", "gracias", "sí", "no", "ok", "um"],
        "error_tendencies": [
            {
                "id": "estar_yo_estoy_vs_esta",
                "form_key": "estoy_yo",
                "label": "yo + está instead of estoy",
                "bad_examples": [
                    "Yo está en el bote",
                    "Yo está bien",
                    "Está en Río Dulce",
                ],
                "good_examples": ["Estoy en el bote", "Estoy bien", "Yo estoy aquí"],
                "strength": 0.85,
            },
            {
                "id": "register_tu_usted_mix",
                "form_key": "register_tu",
                "label": "mix tú/usted casually without control",
                "bad_examples": ["Cómo está? (to a peer while also saying tú)"],
                "good_examples": ["¿Cómo estás?"],
                "strength": 0.4,
            },
        ],
        "learning_rate": 0.22,
        "notes": "Default sim — form focus + boat life.",
    },
    "maya_shy": {
        "id": "maya_shy",
        "name": "Maya",
        "personality": (
            "Quiet, careful, slightly anxious English speaker. Prefers short "
            "answers. Apologizes when wrong. Loves food and family topics."
        ),
        "ability": "novice_mid",
        "L1": "English",
        "interests": ["coffee", "family", "food", "pets"],
        "solid_phrases": ["hola", "gracias", "me llamo Maya", "sí", "no"],
        "error_tendencies": [
            {
                "id": "ser_estar_confuse",
                "form_key": "ser_estar",
                "label": "ser/estar confusion for location and mood",
                "bad_examples": [
                    "Soy nerviosa",
                    "Soy bien",
                    "Soy en la casa",
                    "Estoy estudiante",
                ],
                "good_examples": [
                    "Estoy nerviosa",
                    "Estoy bien",
                    "Estoy en la casa",
                    "Soy estudiante",
                ],
                "strength": 0.7,
            },
        ],
        "learning_rate": 0.18,
        "notes": "Novice mid — ser/estar feelings.",
    },
    "jordan_travel": {
        "id": "jordan_travel",
        "name": "Jordan",
        "personality": (
            "Outgoing traveler who has had some Spanish classes. Risks longer "
            "sentences, mixes codes, laughs off mistakes. Loves cities and food."
        ),
        "ability": "intermediate_low",
        "L1": "English",
        "interests": ["travel", "food", "cities", "music"],
        "solid_phrases": ["hola", "me gusta", "porque", "también", "¿dónde está?"],
        "error_tendencies": [
            {
                "id": "ser_estar_confuse",
                "form_key": "ser_estar",
                "label": "occasional ser/estar slip under pressure",
                "bad_examples": ["Soy cansado después del viaje"],
                "good_examples": ["Estoy cansado después del viaje"],
                "strength": 0.35,
            },
        ],
        "learning_rate": 0.25,
        "notes": "Stronger learner — tests transfer and lighter scaffolding.",
    },
}


def default_student_model() -> str:
    return os_env("AI_STUDENT_MODEL", DEFAULT_STUDENT_MODEL)


def os_env(key: str, default: str) -> str:
    import os

    return (os.environ.get(key) or default).strip()


def get_persona(name: str | None) -> dict[str, Any]:
    key = (name or "alex_boat").strip().lower()
    if key not in PERSONAS:
        raise SystemExit(
            f"Unknown persona {name!r}. Choose: {', '.join(sorted(PERSONAS))}"
        )
    return copy.deepcopy(PERSONAS[key])


def get_ability_level(level_id: str | None, persona: dict | None = None) -> dict[str, Any]:
    lid = (level_id or (persona or {}).get("ability") or "novice_low").strip().lower()
    if lid not in ABILITY_LEVELS:
        raise SystemExit(
            f"Unknown ability level {level_id!r}. Choose: {', '.join(sorted(ABILITY_LEVELS))}"
        )
    return copy.deepcopy(ABILITY_LEVELS[lid])


def initial_learner_state(persona: dict, ability: dict) -> dict[str, Any]:
    """Seed structured state from ability band + persona error foci."""
    forms = copy.deepcopy(ability.get("default_form_seeds") or {})
    still_hard = []
    for e in persona.get("error_tendencies") or []:
        fk = e.get("form_key") or e.get("id") or "form"
        strength = float(e.get("strength") or 0.5)
        forms[fk] = {
            "status": (
                "error_prone" if strength >= 0.55
                else "emerging" if strength >= 0.35
                else "usable"
            ),
            "confidence": max(0.05, 1.0 - strength),
            "attempts": 0,
            "successes": 0,
            "note": e.get("label") or "",
            "error_id": e.get("id"),
            "bad_examples": list(e.get("bad_examples") or []),
            "good_examples": list(e.get("good_examples") or []),
        }
        still_hard.append(e.get("label") or fk)
    return {
        "level": ability.get("id") or "novice_low",
        "forms": forms,
        "noticed_this_session": [],
        "can_try_now": [],
        "still_hard": still_hard,
        "recent_recasts": [],
        "topic_intent": "respond naturally",
        "self_check": "session start",
        "turns": 0,
    }


def extract_learner_output(raw: str) -> tuple[str, dict | None, bool]:
    """Split model output into (utterance, learner_state, parse_ok).

    Prefer explicit <learner_state>...</learner_state> tags (handles nested JSON).
    """
    text = (raw or "").strip()
    m_open = LEARNER_STATE_OPEN.search(text)
    m_close = LEARNER_STATE_CLOSE.search(text)
    if m_open and m_close and m_close.start() > m_open.end():
        visible = text[: m_open.start()].strip()
        body = text[m_open.end() : m_close.start()].strip()
        try:
            state = json.loads(body)
            if not isinstance(state, dict):
                return visible, None, False
            return visible, state, True
        except json.JSONDecodeError:
            return visible, None, False
    # Truncated open tag — hide from tag onward so tutor never sees it
    if m_open:
        return text[: m_open.start()].strip(), None, False
    # Fallback: trailing JSON object with "forms" key
    brace = text.rfind("\n{")
    if brace >= 0:
        candidate = text[brace:].strip()
        try:
            state = json.loads(candidate)
            if isinstance(state, dict) and "forms" in state:
                return text[:brace].strip(), state, True
        except json.JSONDecodeError:
            pass
    return text, None, False


def merge_learner_state(prev: dict, incoming: dict | None) -> tuple[dict, list[str]]:
    """Merge model state with previous; clamp; return (state, change_notes)."""
    notes: list[str] = []
    if not incoming:
        return copy.deepcopy(prev), ["state_parse_failed"]

    out = copy.deepcopy(prev)
    out["turns"] = int(prev.get("turns") or 0) + 1

    # lists
    for key in ("noticed_this_session", "can_try_now", "still_hard", "recent_recasts"):
        if key in incoming and isinstance(incoming[key], list):
            old = list(out.get(key) or [])
            new = [str(x)[:120] for x in incoming[key] if x is not None]
            # union, prefer new order, cap length
            merged: list[str] = []
            for x in new + old:
                if x not in merged:
                    merged.append(x)
            out[key] = merged[:12]
            if new != old[: len(new)]:
                notes.append(f"{key}↻")

    for key in ("topic_intent", "self_check", "level"):
        if key in incoming and incoming[key] is not None:
            val = str(incoming[key])[:200]
            if val != out.get(key):
                notes.append(f"{key}={val[:40]}")
            out[key] = val

    # forms
    forms_in = incoming.get("forms")
    if isinstance(forms_in, dict):
        forms = dict(out.get("forms") or {})
        for fk, fv in forms_in.items():
            if not isinstance(fv, dict):
                continue
            prev_f = dict(forms.get(fk) or {})
            conf = fv.get("confidence", prev_f.get("confidence", 0.2))
            try:
                conf = float(conf)
            except (TypeError, ValueError):
                conf = float(prev_f.get("confidence") or 0.2)
            conf = max(0.0, min(1.0, conf))
            status = fv.get("status") or prev_f.get("status") or "emerging"
            if status not in ("error_prone", "emerging", "usable", "solid"):
                status = prev_f.get("status") or "emerging"
            try:
                attempts = int(fv.get("attempts", prev_f.get("attempts") or 0))
            except (TypeError, ValueError):
                attempts = int(prev_f.get("attempts") or 0)
            try:
                successes = int(fv.get("successes", prev_f.get("successes") or 0))
            except (TypeError, ValueError):
                successes = int(prev_f.get("successes") or 0)
            # Prevent magical jumps: conf can't leap more than +0.35 per turn
            old_c = float(prev_f.get("confidence") or 0.2)
            if conf > old_c + 0.35:
                conf = old_c + 0.35
                notes.append(f"clamp:{fk}")
            if conf < old_c - 0.25:
                conf = old_c - 0.25
            new_f = {
                **prev_f,
                "status": status,
                "confidence": round(conf, 3),
                "attempts": max(0, attempts),
                "successes": max(0, successes),
            }
            if fv.get("note"):
                new_f["note"] = str(fv.get("note"))[:120]
            if prev_f.get("confidence") != new_f["confidence"] or prev_f.get("status") != status:
                notes.append(
                    f"form:{fk} {prev_f.get('status')}/{old_c:.2f}→{status}/{conf:.2f}"
                )
            forms[fk] = new_f
        out["forms"] = forms

    return out, notes


# ---------------------------------------------------------------------------
# True ability (derived view for checks — from learner_state)
# ---------------------------------------------------------------------------

@dataclass
class TrueAbility:
    """Projection of learner_state for verification checks."""

    error_strength: dict[str, float] = field(default_factory=dict)
    recasts_seen: dict[str, int] = field(default_factory=dict)
    turns: int = 0
    learner_state: dict = field(default_factory=dict)

    @classmethod
    def from_persona(cls, persona: dict, ability: dict | None = None) -> "TrueAbility":
        ability = ability or get_ability_level(persona.get("ability"), persona)
        state = initial_learner_state(persona, ability)
        strengths = {}
        for e in persona.get("error_tendencies") or []:
            eid = e.get("id")
            if not eid:
                continue
            fk = e.get("form_key") or eid
            form = (state.get("forms") or {}).get(fk) or {}
            conf = float(form.get("confidence") or 0.2)
            strengths[eid] = max(0.05, 1.0 - conf)
        return cls(
            error_strength=strengths,
            learner_state=state,
            turns=0,
        )

    def sync_from_state(self, state: dict, persona: dict) -> None:
        self.learner_state = copy.deepcopy(state)
        self.turns = int(state.get("turns") or self.turns)
        forms = state.get("forms") or {}
        for e in persona.get("error_tendencies") or []:
            eid = e.get("id")
            if not eid:
                continue
            fk = e.get("form_key") or eid
            form = forms.get(fk) or {}
            conf = float(form.get("confidence") or 0.2)
            self.error_strength[eid] = max(0.05, min(0.95, 1.0 - conf))
            # treat successes as recast-driven learning signal
            self.recasts_seen[eid] = int(form.get("successes") or 0)

    def on_tutor_reply(self, tutor_text: str, persona: dict) -> list[str]:
        """Legacy hook — learning now primarily via model learner_state.

        Still bumps recast counters lightly for logging when tutor models forms.
        """
        notes: list[str] = []
        low = (tutor_text or "").lower()
        for err in persona.get("error_tendencies") or []:
            eid = err.get("id") or ""
            goods = err.get("good_examples") or []
            hit = any(
                any(t in low for t in re.findall(r"[a-záéíóúüñ]{3,}", g.lower())[:2])
                for g in goods
            )
            if eid == "estar_yo_estoy_vs_esta" and re.search(r"\bestoy\b", low):
                hit = True
            if hit and eid:
                self.recasts_seen[eid] = self.recasts_seen.get(eid, 0) + 1
                notes.append(f"tutor_modeled:{eid}")
        return notes

    def snapshot(self) -> dict:
        return {
            "error_strength": dict(self.error_strength),
            "recasts_seen": dict(self.recasts_seen),
            "turns": self.turns,
            "learner_state": copy.deepcopy(self.learner_state),
        }


# ---------------------------------------------------------------------------
# Student agent
# ---------------------------------------------------------------------------

_LEAVE_RE = re.compile(
    r"\b(adi[oó]s|hasta\s+luego|hasta\s+mañana|bye|goodbye|gracias)\b",
    re.I,
)
# Student model sometimes pastes tutor praise / models into its own turn
_TUTOR_LEAK_MARKERS = (
    "¡muy bien",
    "muy bien, alex",
    "natural spanish",
    "perfect!",
    "perfecto!",
    "to say ",
    "remember,",
    "remember:",
    "spot on",
    "that's wonderful",
    "that's great",
    "let's try",
    "fill in the blank",
    "**estoy",
    "**(yo) estoy",
)


def clean_student_utterance(raw: str, *, persona_name: str = "") -> str:
    """Drop tutor-like leakage and keep a single learner turn."""
    text = (raw or "").strip()
    if not text:
        return "um… hola?"
    # Strip markdown fences / bold
    text = re.sub(r"^```.*?\n", "", text)
    text = re.sub(r"\n```$", "", text)
    text = text.replace("**", "")
    # Cut at first tutor-ish segment
    low = text.lower()
    cut = len(text)
    for m in _TUTOR_LEAK_MARKERS:
        i = low.find(m)
        if i > 8:
            cut = min(cut, i)
    # Also cut if name + praise pattern
    if persona_name:
        for pat in (
            rf"¡?\s*muy bien,?\s*{re.escape(persona_name)}",
            rf"great job,?\s*{re.escape(persona_name)}",
        ):
            mm = re.search(pat, text, re.I)
            if mm and mm.start() > 5:
                cut = min(cut, mm.start())
    text = text[:cut].strip()
    # Prefer first 1–3 sentences for novices
    parts = re.split(r"(?<=[\.\!\?])\s+", text)
    if len(parts) > 3:
        text = " ".join(parts[:3]).strip()
    text = text.strip().strip('"').strip()
    # Drop trailing tutor question prompts accidentally kept
    text = re.sub(
        r"\s*(Where is|What's your|How would you|Can you try).*$",
        "",
        text,
        flags=re.I,
    ).strip()
    if not text or len(text) < 2:
        return "um… hola?"
    return text


class AIStudentAgent:
    """Grok-backed learner with structured learner_state + full chat memory."""

    def __init__(
        self,
        persona: dict[str, Any],
        *,
        model: str | None = None,
        ability_level: str | None = None,
    ):
        config.load_env()
        self.persona = copy.deepcopy(persona)
        self.ability = get_ability_level(
            ability_level or self.persona.get("ability"), self.persona
        )
        # CLI --level overrides persona default band
        self.persona["ability"] = self.ability.get("id") or self.persona.get("ability")
        self.model = model or default_student_model()
        self.caps = config.caps_for(self.model)
        self.client = config.make_client_for(self.model)
        self.true = TrueAbility.from_persona(self.persona, self.ability)
        self.learner_state: dict[str, Any] = copy.deepcopy(self.true.learner_state)
        self.history: list[dict] = []  # full session: user=tutor, assistant=self
        self._leave_streak = 0
        self.last_state_notes: list[str] = []
        self.last_state_parse_ok: bool = False

    def _leave_looping(self) -> bool:
        """True if last few student lines were only leave-taking."""
        recent = [
            m["content"]
            for m in self.history
            if m.get("role") == "assistant"
        ][-3:]
        if len(recent) < 2:
            return False
        return all(
            _LEAVE_RE.search(t or "") and len((t or "").split()) <= 6
            for t in recent
        )

    def _form_guidance_lines(self) -> list[str]:
        """Translate learner_state forms into actable instructions."""
        lines: list[str] = []
        forms = self.learner_state.get("forms") or {}
        for e in self.persona.get("error_tendencies") or []:
            eid = e.get("id") or "?"
            fk = e.get("form_key") or eid
            form = forms.get(fk) or {}
            conf = float(form.get("confidence") or 0.2)
            status = form.get("status") or "error_prone"
            if conf >= 0.55 or status in ("usable", "solid"):
                prefer = "PREFER GOOD forms (you've been learning this)"
            elif conf >= 0.35 or status == "emerging":
                prefer = "MIXED — try good form if tutor just modeled it, else may err"
            else:
                prefer = "usually make the MISTAKE"
            lines.append(
                f"- {eid} / form={fk} (status={status}, conf={conf:.2f} — {prefer}): "
                f"{e.get('label')}\n"
                f"  mistakes: {e.get('bad_examples')}\n"
                f"  good forms: {e.get('good_examples')}"
            )
        return lines

    def _system_text(self, *, tutor_message: str = "") -> str:
        base = STUDENT_PROMPT.read_text() if STUDENT_PROMPT.exists() else (
            "You are a Spanish learner. Reply only as the student, then emit "
            "<learner_state> JSON."
        )
        p = self.persona
        ab = self.ability
        profile = {
            "name": p.get("name"),
            "personality": p.get("personality"),
            "ability": ab.get("id"),
            "ability_label": ab.get("label"),
            "L1": p.get("L1"),
            "interests": p.get("interests"),
            "solid_phrases": p.get("solid_phrases"),
            "learning_rate": p.get("learning_rate"),
        }
        ability_block = {
            "id": ab.get("id"),
            "label": ab.get("label"),
            "description": ab.get("description"),
            "english_ratio": ab.get("english_ratio"),
            "max_spanish_words": ab.get("max_spanish_words"),
            "sentence_complexity": ab.get("sentence_complexity"),
            "inventory": ab.get("inventory"),
            "avoid_grammar": ab.get("avoid_grammar"),
        }
        err_lines = self._form_guidance_lines()
        extra = ""
        if self._leave_looping():
            topics = ", ".join((p.get("interests") or ["boats", "coffee"])[:4])
            extra += (
                "\n## Harness override — STOP THE GOODBYE LOOP\n"
                "You already said goodbye. Do **not** say adiós/gracias only. "
                f"Answer with a real chat line about {topics}, "
                "or how you feel — or ask a simple question.\n"
            )
        # If tutor models estoy and confidence is rising, nudge attempt
        if re.search(r"\bestoy\b", tutor_message or "", re.I):
            form = (self.learner_state.get("forms") or {}).get("estoy_yo") or {}
            conf = float(form.get("confidence") or 0.2)
            if conf >= 0.35 or "estoy" in " ".join(
                self.learner_state.get("can_try_now") or []
            ).lower():
                extra += (
                    "\n## Harness nudge\n"
                    "Tutor just modeled **estoy**. Try using *estoy* (not *está*) "
                    "for yourself this turn if you talk about where you are / how you are. "
                    "Update learner_state if you succeed or notice the form.\n"
                )
        can_try = self.learner_state.get("can_try_now") or []
        if can_try:
            extra += (
                "\n## Forms you can try now\n"
                + "\n".join(f"- {x}" for x in can_try[:6])
                + "\n"
            )
        return (
            base
            + "\n\n## Your profile\n"
            + json.dumps(profile, ensure_ascii=False, indent=2)
            + "\n\n## Ability band (hard constraints)\n"
            + json.dumps(ability_block, ensure_ascii=False, indent=2)
            + "\n\n## Current learner_state (your memory — update every turn)\n"
            + json.dumps(self.learner_state, ensure_ascii=False, indent=2)
            + "\n\n## Form guidance (from learner_state + persona)\n"
            + ("\n".join(err_lines) if err_lines else "(none)")
            + f"\n\n## Name\nYou are **{p.get('name') or 'the student'}**.\n"
            + extra
            + "\nRemember: first the spoken reply only, then <learner_state> JSON.\n"
        )

    def respond(self, tutor_message: str) -> tuple[str, dict]:
        """Return (student_utterance, usage). Updates learner_state each turn."""
        tutor_message = (tutor_message or "").strip()
        if not tutor_message:
            tutor_message = "(The tutor is waiting for you to say something.)"

        # Full memory: tutor is "user" from the student's POV
        self.history.append({"role": "user", "content": tutor_message})

        system = [{
            "type": "text",
            "text": self._system_text(tutor_message=tutor_message),
        }]
        # Full conversation history (sims are short; memory is the point)
        msgs = list(self.history)

        final = self.client.messages.create(
            model=self.caps.model,
            max_tokens=768,  # room for utterance + learner_state JSON
            system=system,
            messages=msgs,
        )
        texts = []
        for b in getattr(final, "content", None) or []:
            if getattr(b, "type", None) == "text":
                t = getattr(b, "text", "") or ""
                if t:
                    texts.append(t)
        raw_full = "\n".join(texts).strip()
        visible, state_in, parse_ok = extract_learner_output(raw_full)
        self.last_state_parse_ok = parse_ok
        utterance = clean_student_utterance(
            visible, persona_name=str(self.persona.get("name") or "")
        )

        # Soft break if model still only goodbyes while looping
        if (
            self._leave_looping()
            and _LEAVE_RE.search(utterance)
            and len(utterance.split()) <= 6
        ):
            interests = self.persona.get("interests") or ["the boat"]
            topic = interests[int(self.learner_state.get("turns") or 0) % len(interests)]
            utterance = f"Um… wait — about {topic}, it is nice today."

        # Merge structured learning memory
        self.learner_state, state_notes = merge_learner_state(
            self.learner_state, state_in
        )
        self.true.sync_from_state(self.learner_state, self.persona)
        self.last_state_notes = list(state_notes)
        if not parse_ok:
            self.last_state_notes = list(state_notes) + ["state_parse_failed"]

        # History stores only what the tutor hears (no state tags)
        self.history.append({"role": "assistant", "content": utterance})
        if _LEAVE_RE.search(utterance) and len(utterance.split()) <= 6:
            self._leave_streak += 1
        else:
            self._leave_streak = 0

        usage = {
            "input_tokens": getattr(
                getattr(final, "usage", None), "input_tokens", 0
            ),
            "output_tokens": getattr(
                getattr(final, "usage", None), "output_tokens", 0
            ),
            "model": self.model,
            "state_parse_ok": parse_ok,
            "state_notes": list(self.last_state_notes),
        }
        return utterance, usage


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

@dataclass
class SimTurn:
    n: int
    tutor_prompt: str  # what student answered
    student: str
    tutor_reply: str  # teacher response after student
    sheet_notes: list[str]
    next_best: dict
    learn_notes: list[str]
    parts: dict
    true_ability: dict
    tool_delta: dict | None = None
    sheet_diff: list[str] = field(default_factory=list)


def _jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    return str(obj)


def _sheet_diff(before: dict, after: dict) -> list[str]:
    """Human-readable high-signal sheet changes."""
    lines: list[str] = []

    def conf_map(s: dict, key: str) -> dict[str, tuple]:
        block = s.get(key) or {}
        out = {}
        if not isinstance(block, dict):
            return out
        for k, v in block.items():
            if not isinstance(v, dict):
                continue
            out[k] = (v.get("status"), v.get("confidence"))
        return out

    for section in ("skills", "grammar", "lexicon"):
        b, a = conf_map(before, section), conf_map(after, section)
        for k in sorted(set(b) | set(a)):
            if b.get(k) != a.get(k):
                lines.append(f"{section}.{k}: {b.get(k)} → {a.get(k)}")

    be = before.get("error_patterns") or {}
    ae = after.get("error_patterns") or {}
    if not isinstance(be, dict):
        be = {}
    if not isinstance(ae, dict):
        ae = {}
    b_ids = {k for k, v in be.items() if isinstance(v, dict) and k != "active"}
    a_ids = {k for k, v in ae.items() if isinstance(v, dict) and k != "active"}
    for pid in sorted(a_ids - b_ids):
        ent = ae[pid]
        lines.append(
            f"error_patterns.+{pid}: count={ent.get('count')} "
            f"examples={ent.get('last_examples')}"
        )
    for pid in sorted(a_ids & b_ids):
        bc, ac = (be[pid] or {}).get("count"), (ae[pid] or {}).get("count")
        if bc != ac:
            lines.append(
                f"error_patterns.{pid}: count {bc}→{ac} "
                f"examples={(ae[pid] or {}).get('last_examples')}"
            )
        bex = (be[pid] or {}).get("last_examples")
        aex = (ae[pid] or {}).get("last_examples")
        if bex != aex and bc == ac:
            lines.append(f"error_patterns.{pid}: examples→{aex}")

    bnb = before.get("next_best") or {}
    anb = after.get("next_best") or {}
    for k in ("can_do", "activity", "stretch", "form_focus", "error_pattern", "reason"):
        if bnb.get(k) != anb.get(k) and (bnb.get(k) or anb.get(k)):
            lines.append(f"next_best.{k}: {bnb.get(k)!r} → {anb.get(k)!r}")

    ba = before.get("affect") or {}
    aa = after.get("affect") or {}
    for k in ("energy", "mood", "time_budget"):
        if ba.get(k) != aa.get(k) and (ba.get(k) or aa.get(k)):
            lines.append(f"affect.{k}: {ba.get(k)!r} → {aa.get(k)!r}")

    br = before.get("receptive") or {}
    ar = after.get("receptive") or {}
    if br.get("needs_english_scaffold") != ar.get("needs_english_scaffold"):
        lines.append(
            f"receptive.needs_english_scaffold: "
            f"{br.get('needs_english_scaffold')} → {ar.get('needs_english_scaffold')}"
        )

    bi = before.get("identity") or {}
    ai = after.get("identity") or {}
    for k in ("name", "L1", "goals"):
        if bi.get(k) != ai.get(k) and (bi.get(k) or ai.get(k)):
            lines.append(f"identity.{k}: {bi.get(k)!r} → {ai.get(k)!r}")

    return lines


class SimLogger:
    """Write conversation + sheet deltas to jsonl + markdown under logs/sessions/."""

    def __init__(self, *, label: str, meta: dict | None = None):
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.session_id = f"{stamp}-ai-student-{label}"
        self.jsonl_path = config.LOG_DIR / f"{self.session_id}.jsonl"
        self.md_path = config.LOG_DIR / f"{self.session_id}.md"
        self._md_lines: list[str] = []
        start = {
            "event": "session_start",
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "session_id": self.session_id,
            **(meta or {}),
        }
        self._write_jsonl(start)
        self._md_lines.append(f"# AI student simulation `{self.session_id}`\n")
        self._md_lines.append("```json\n" + json.dumps(meta or {}, indent=2) + "\n```\n")
        self._flush_md()

    def _write_jsonl(self, obj: dict) -> None:
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(_jsonable(obj), ensure_ascii=False) + "\n")

    def _flush_md(self) -> None:
        self.md_path.write_text("\n".join(self._md_lines), encoding="utf-8")

    def open_tutor(self, reply: str, notes: list[str]) -> None:
        self._write_jsonl({
            "event": "open",
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "tutor": reply,
            "sheet_notes": notes,
        })
        self._md_lines.append("## Open\n")
        self._md_lines.append(f"**Tutor:**\n\n{reply}\n")
        if notes:
            self._md_lines.append(f"*sheet notes:* `{'`; `'.join(notes)}`\n")
        self._flush_md()

    def turn(
        self,
        *,
        n: int,
        student: str,
        tutor_reply: str,
        sheet_notes: list[str],
        sheet_diff: list[str],
        tool_delta: dict | None,
        learn_notes: list[str],
        parts: dict,
        next_best: dict,
        true_ability: dict,
    ) -> None:
        self._write_jsonl({
            "event": "turn",
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "n": n,
            "student": student,
            "tutor_reply": tutor_reply,
            "sheet_notes": sheet_notes,
            "sheet_diff": sheet_diff,
            "tool_delta": tool_delta,
            "learn_notes": learn_notes,
            "parts": parts,
            "next_best": next_best,
            "true_ability": true_ability,
        })
        self._md_lines.append(f"## Turn {n}\n")
        self._md_lines.append(f"**Student:**\n\n{student}\n")
        self._md_lines.append(f"**Tutor:**\n\n{tutor_reply}\n")
        if parts.get("recast"):
            self._md_lines.append(f"**Recast:** {parts.get('recast')}\n")
        if parts.get("explain"):
            self._md_lines.append(f"**Explain:** {parts.get('explain')}\n")
        if sheet_notes:
            self._md_lines.append(
                f"**Sheet notes:** `{'`; `'.join(sheet_notes)}`\n"
            )
        if sheet_diff:
            self._md_lines.append("**Character sheet changes:**\n")
            for line in sheet_diff:
                self._md_lines.append(f"- `{line}`\n")
        else:
            self._md_lines.append("**Character sheet changes:** *(none)*\n")
        if tool_delta:
            self._md_lines.append(
                "**Tool delta:**\n\n```json\n"
                + json.dumps(tool_delta, ensure_ascii=False, indent=2)[:3000]
                + "\n```\n"
            )
        if learn_notes:
            self._md_lines.append(
                f"**Student learning (ground truth):** `{'`; `'.join(learn_notes)}`\n"
            )
        nb = next_best or {}
        self._md_lines.append(
            f"**next_best:** `{nb.get('can_do')}` / `{nb.get('activity') or nb.get('stretch')}` "
            f"— {nb.get('reason', '')[:200]}\n"
        )
        self._flush_md()

    def close(self, report: dict) -> None:
        self._write_jsonl({
            "event": "session_end",
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "checks": report.get("checks"),
            "true_ability_final": report.get("true_ability_final"),
            "sheet_error_patterns": report.get("sheet_error_patterns"),
            "sheet_next_best": report.get("sheet_next_best"),
        })
        self._md_lines.append("## End\n")
        self._md_lines.append("### Checks\n")
        for c in report.get("checks") or []:
            mark = "PASS" if c.get("ok") else "FAIL"
            self._md_lines.append(
                f"- **{mark}** `{c.get('id')}`: {c.get('detail')}\n"
            )
        self._md_lines.append("### True ability final\n\n```json\n")
        self._md_lines.append(
            json.dumps(report.get("true_ability_final"), indent=2, ensure_ascii=False)
        )
        self._md_lines.append("\n```\n")
        self._md_lines.append("### Sheet error_patterns\n\n```json\n")
        self._md_lines.append(
            json.dumps(
                report.get("sheet_error_patterns"), indent=2, ensure_ascii=False
            )[:4000]
        )
        self._md_lines.append("\n```\n")
        self._flush_md()


def run_simulation(
    *,
    turns: int | None = DEFAULT_TURNS,
    minutes: float | None = None,
    persona_id: str = "alex_boat",
    ability_level: str | None = None,
    student_model: str | None = None,
    tutor_model: str | None = None,
    sheet_path: Path | None = None,
    reset_sheet: bool = True,
    focus_model: str | None = "off",
    live_print: bool = True,
) -> dict[str, Any]:
    """Run student↔tutor exchanges for N turns and/or wall-clock minutes."""
    config.load_env()
    persona = get_persona(persona_id)
    ability = get_ability_level(ability_level or persona.get("ability"), persona)
    sheet_path = Path(sheet_path or DEFAULT_STUDENT_SHEET)
    if reset_sheet and sheet_path.exists():
        sheet_path.unlink()

    # Seed a blank sheet with the AI student name for nicer greets
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    if reset_sheet or not sheet_path.exists():
        from .character_sheet import default_sheet, save_sheet

        sheet = default_sheet()
        sheet.setdefault("identity", {})["name"] = persona.get("name") or "Alex"
        sheet["identity"]["L1"] = persona.get("L1") or "English"
        sheet["identity"]["goals"] = [
            f"Sim student ({persona.get('id')}, {ability.get('id')}) — practice chat"
        ]
        save_sheet(sheet_path, sheet)

    teacher = ConversationalSession(
        model=tutor_model or config.MODEL,
        sheet_path=sheet_path,
        label=f"ai-student-{persona.get('id')}",
        focus_model=focus_model if focus_model is not None else "off",
    )
    student = AIStudentAgent(
        persona,
        model=student_model or default_student_model(),
        ability_level=ability.get("id"),
    )

    slog = SimLogger(
        label=persona.get("id") or "student",
        meta={
            "persona": persona.get("id"),
            "ability_level": ability.get("id"),
            "student_model": student.model,
            "tutor_model": teacher.model,
            "sheet": str(sheet_path),
            "turns_cap": turns,
            "minutes_cap": minutes,
        },
    )
    p = palette() if live_print else None

    def _live(msg: str, style: str = "meta") -> None:
        if live_print:
            print(paint(msg, style, p=p) if p else msg, flush=True)

    open_turn = teacher.open_session()
    if open_turn.error:
        raise RuntimeError(f"teacher open failed: {open_turn.error}")

    slog.open_tutor(open_turn.reply, list(open_turn.notes or []))
    _live(f"log: {slog.md_path}", "meta")
    _live("── open ──", "tutor_label")
    _live(f"tutor> {open_turn.reply}", "tutor_label")

    log: list[SimTurn] = []
    tutor_msg = open_turn.reply
    student.true.on_tutor_reply(tutor_msg, persona)
    sheet_before = copy.deepcopy(load_sheet(sheet_path))

    t0 = time.monotonic()
    max_turns = turns if turns is not None else 10_000
    i = 0
    while i < max_turns:
        if minutes is not None and (time.monotonic() - t0) >= minutes * 60:
            _live(f"time limit {minutes}m reached after {i} turns", "meta")
            break
        i += 1
        _live(f"── turn {i} ──", "tutor_label")
        student_text, su = student.respond(tutor_msg)
        _live(f"student> {student_text}", "ok")
        tr = teacher.user_turn(student_text, input_mode="text")
        if tr.error:
            raise RuntimeError(f"teacher turn {i} failed: {tr.error}")
        _live(f"tutor> {tr.reply}", "tutor_label")
        # Tutor modeling signals (logging) + student's own state merge notes
        model_notes = student.true.on_tutor_reply(tr.reply, persona)
        state_notes = list(student.last_state_notes or [])
        if su.get("state_parse_ok") is False:
            state_notes = list(state_notes) + ["parse_miss"]
        ln = state_notes + model_notes
        sheet_after = copy.deepcopy(load_sheet(sheet_path))
        diff = _sheet_diff(sheet_before, sheet_after)
        if tr.notes:
            _live(f"  [sheet notes: {'; '.join(tr.notes)}]", "sheet")
        if diff:
            _live("  [sheet changes]", "sheet")
            for line in diff:
                _live(f"    • {line}", "sheet")
        else:
            _live("  [sheet changes: none]", "meta")
        if ln:
            _live(f"  [learn: {'; '.join(ln)}]", "ok")
        if (tr.parts or {}).get("recast"):
            _live(f"  [recast] {(tr.parts or {}).get('recast')}", "ok")
        ls = student.learner_state
        _live(
            f"  [learner_state turns={ls.get('turns')} "
            f"can_try={ls.get('can_try_now')!r} "
            f"parse_ok={su.get('state_parse_ok')}]",
            "meta",
        )

        slog.turn(
            n=i,
            student=student_text,
            tutor_reply=tr.reply,
            sheet_notes=list(tr.notes or []),
            sheet_diff=diff,
            tool_delta=tr.tool_delta,
            learn_notes=ln,
            parts=dict(tr.parts or {}),
            next_best=dict(tr.next_best or {}),
            true_ability=student.true.snapshot(),
        )
        log.append(
            SimTurn(
                n=i,
                tutor_prompt=tutor_msg,
                student=student_text,
                tutor_reply=tr.reply,
                sheet_notes=list(tr.notes or []),
                next_best=dict(tr.next_best or {}),
                learn_notes=ln,
                parts=dict(tr.parts or {}),
                true_ability=student.true.snapshot(),
                tool_delta=tr.tool_delta,
                sheet_diff=diff,
            )
        )
        sheet_before = sheet_after
        tutor_msg = tr.reply

    elapsed = time.monotonic() - t0
    sheet = load_sheet(sheet_path)
    report = {
        "persona": persona.get("id"),
        "ability_level": ability.get("id"),
        "student_name": persona.get("name"),
        "student_model": student.model,
        "tutor_model": teacher.model,
        "sheet_path": str(sheet_path),
        "turns": len(log),
        "elapsed_sec": round(elapsed, 1),
        "log_md": str(slog.md_path),
        "log_jsonl": str(slog.jsonl_path),
        "session_id": slog.session_id,
        "true_ability_final": student.true.snapshot(),
        "learner_state_final": copy.deepcopy(student.learner_state),
        "sheet_error_patterns": (sheet.get("error_patterns") or {}),
        "sheet_next_best": sheet.get("next_best") or {},
        "sheet_skills_sample": {
            k: {
                "status": v.get("status"),
                "confidence": v.get("confidence"),
            }
            for k, v in list((sheet.get("skills") or {}).items())[:8]
        },
        "log": [
            {
                "n": t.n,
                "student": t.student,
                "tutor_seen": t.tutor_prompt,
                "tutor_reply": t.tutor_reply,
                "sheet_notes": t.sheet_notes,
                "sheet_diff": t.sheet_diff,
                "tool_delta": t.tool_delta,
                "learn_notes": t.learn_notes,
                "next_best_can_do": (t.next_best or {}).get("can_do"),
                "has_recast": bool((t.parts or {}).get("recast")),
                "true_ability": t.true_ability,
            }
            for t in log
        ],
        "checks": _verification_checks(sheet, student.true, log),
    }
    slog.close(report)
    return report


def _verification_checks(
    sheet: dict, true: TrueAbility, log: list[SimTurn]
) -> list[dict]:
    """Lightweight expectations for harness health (not a full eval suite)."""
    from .pedagogy_contract import has_teach_move

    checks: list[dict] = []
    checks.append({
        "id": "teacher_replied",
        "ok": all(bool(t.student) and bool(t.tutor_reply) for t in log),
        "detail": f"{len(log)} complete exchanges",
    })
    # Pedagogy system: fraction of tutor turns with a teach move (model/try/recast)
    if log:
        n_teach = sum(1 for t in log if has_teach_move(t.parts or {}))
        rate = n_teach / max(1, len(log))
        checks.append({
            "id": "pedagogy_teach_move_rate",
            "ok": rate >= 0.5,  # soft floor; contract v1 aims higher
            "detail": f"{n_teach}/{len(log)} turns ({rate:.0%}) with model/try/recast",
        })
    student_blob = " ".join(t.student.lower() for t in log)
    used_yo_esta = bool(
        re.search(r"\byo\s+est[aá]\b", student_blob)
        or re.search(r"\best[aá]\s+en\s+(el|mi|un)\s+bote\b", student_blob)
    )
    eps = sheet.get("error_patterns") or {}
    # Sheet may store patterns as top-level ids or under "active"
    active = eps.get("active") if isinstance(eps.get("active"), dict) else {}
    pattern_ids = set(active.keys()) | {
        k for k, v in eps.items()
        if k not in ("active", "history", "resolved") and isinstance(v, dict)
    }
    noted = "estar_yo_estoy_vs_esta" in pattern_ids or any(
        "estar" in str(k).lower() or "estoy" in str(k).lower() for k in pattern_ids
    )
    # soft: pass if recast appeared even if pattern not yet stamped
    any_recast = any(t.parts.get("recast") for t in log)
    checks.append({
        "id": "error_pattern_or_recast",
        "ok": (not used_yo_esta) or noted or any_recast or len(log) < 2,
        "detail": (
            f"used_yo_esta={used_yo_esta} noted={noted} "
            f"any_recast={any_recast} patterns={list(pattern_ids)[:6]}"
        ),
    })
    # Learning via learner_state: if model raised conf on a form, strength should fall
    ls = true.learner_state or {}
    forms = ls.get("forms") or {}
    if log and forms:
        first_ls = (log[0].true_ability.get("learner_state") or {})
        first_forms = first_ls.get("forms") or {}
        improved = []
        for fk, fv in forms.items():
            if not isinstance(fv, dict):
                continue
            c0 = float((first_forms.get(fk) or {}).get("confidence") or 0)
            c1 = float(fv.get("confidence") or 0)
            if c1 > c0 + 0.05:
                improved.append(f"{fk}:{c0:.2f}→{c1:.2f}")
        checks.append({
            "id": "learner_state_present",
            "ok": bool(forms),
            "detail": (
                f"forms={list(forms.keys())[:6]} "
                f"turns={ls.get('turns')} improved={improved or 'none'}"
            ),
        })
    for eid, n in true.recasts_seen.items():
        if n <= 0 or not log:
            continue
        first = (log[0].true_ability.get("error_strength") or {}).get(eid)
        last = true.error_strength.get(eid)
        # Strength should not *increase* after successful practice signals
        ok = first is None or last is None or last <= first + 0.05
        checks.append({
            "id": f"learning_down_{eid}",
            "ok": ok,
            "detail": f"success_signals={n} strength {first}→{last}",
        })
    name = (sheet.get("identity") or {}).get("name")
    checks.append({
        "id": "sheet_has_name",
        "ok": bool(name),
        "detail": f"name={name!r}",
    })
    return checks


def print_report(report: dict, *, verbose: bool = True) -> None:
    p = palette()
    print(paint(
        f"AI student sim — {report.get('student_name')} "
        f"({report.get('persona')}, {report.get('ability_level')})",
        "header",
        p=p,
    ))
    print(paint(
        f"  student={report.get('student_model')}  "
        f"tutor={report.get('tutor_model')}  "
        f"sheet={report.get('sheet_path')}",
        "meta",
        p=p,
    ))
    if report.get("log_md"):
        print(paint(f"  transcript={report.get('log_md')}", "meta", p=p))
        print(paint(f"  jsonl={report.get('log_jsonl')}", "meta", p=p))
    if report.get("elapsed_sec") is not None:
        print(paint(
            f"  turns={report.get('turns')}  elapsed={report.get('elapsed_sec')}s",
            "meta",
            p=p,
        ))
    print()
    if verbose:
        for t in report.get("log") or []:
            print(paint(f"── turn {t['n']} ──", "tutor_label", p=p))
            print(paint("tutor> ", "tutor_label", p=p) + (t.get("tutor_seen") or "")[:500])
            print(paint("student> ", "ok", p=p) + (t.get("student") or ""))
            print(paint("tutor> ", "tutor_label", p=p) + (t.get("tutor_reply") or "")[:500])
            notes = t.get("sheet_notes") or []
            if notes:
                print(paint(f"  [sheet: {'; '.join(notes)}]", "sheet", p=p))
            for line in t.get("sheet_diff") or []:
                print(paint(f"  [Δ {line}]", "sheet", p=p))
            if t.get("learn_notes"):
                print(paint(
                    f"  [learn: {'; '.join(t['learn_notes'])}]", "ok", p=p
                ))
            if t.get("has_recast"):
                print(paint("  [recast present]", "ok", p=p))
            print()
    print(paint("## Verification checks", "header", p=p))
    for c in report.get("checks") or []:
        mark = "✓" if c.get("ok") else "✗"
        style = "ok" if c.get("ok") else "err"
        print(paint(f"  {mark} {c.get('id')}: {c.get('detail')}", style, p=p))
    print()
    print(paint("## True ability (student ground truth)", "header", p=p))
    print(json.dumps(report.get("true_ability_final"), indent=2, ensure_ascii=False))
    print()
    if report.get("learner_state_final"):
        print(paint("## Learner state final", "header", p=p))
        print(json.dumps(report.get("learner_state_final"), indent=2, ensure_ascii=False)[:2500])
        print()
    print(paint("## Sheet error_patterns (teacher model)", "header", p=p))
    print(json.dumps(report.get("sheet_error_patterns"), indent=2, ensure_ascii=False)[:2000])
    print()
    print(paint("## Sheet next_best", "header", p=p))
    print(json.dumps(report.get("sheet_next_best"), indent=2, ensure_ascii=False)[:1500])


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="Simulate a Grok AI student against the Spanish tutor"
    )
    ap.add_argument(
        "--persona",
        default="alex_boat",
        choices=sorted(PERSONAS.keys()),
        help="Student persona preset",
    )
    ap.add_argument(
        "--level",
        default=None,
        choices=sorted(ABILITY_LEVELS.keys()),
        help="Ability band override (default: persona's ability)",
    )
    ap.add_argument(
        "--turns",
        type=int,
        default=None,
        help=f"Max exchanges (default {DEFAULT_TURNS} if --minutes not set)",
    )
    ap.add_argument(
        "--minutes",
        type=float,
        default=None,
        help="Run until this many wall-clock minutes (optional with --turns)",
    )
    ap.add_argument(
        "--student-model",
        default=None,
        help=f"Grok model for student (default {DEFAULT_STUDENT_MODEL})",
    )
    ap.add_argument(
        "--tutor-model",
        default=None,
        help="Teacher model (default TUTOR_MODEL / gemini)",
    )
    ap.add_argument(
        "--sheet",
        type=Path,
        default=DEFAULT_STUDENT_SHEET,
        help="Character sheet path (default logs/ai_student_sheet.json)",
    )
    ap.add_argument(
        "--reset-sheet",
        action="store_true",
        default=True,
        help="Wipe AI student sheet before run (default: true)",
    )
    ap.add_argument(
        "--keep-sheet",
        action="store_true",
        help="Do not wipe sheet (continue learning across runs)",
    )
    ap.add_argument(
        "--focus-model",
        default="off",
        help="FOCUS_MODEL for rail (default off for faster sim)",
    )
    ap.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write full report JSON to this path",
    )
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    reset = not args.keep_sheet
    turns = args.turns
    minutes = args.minutes
    if turns is None and minutes is None:
        turns = DEFAULT_TURNS
    if turns is not None:
        turns = max(1, turns)
    report = run_simulation(
        turns=turns,
        minutes=minutes,
        persona_id=args.persona,
        ability_level=args.level,
        student_model=args.student_model,
        tutor_model=args.tutor_model,
        sheet_path=args.sheet,
        reset_sheet=reset,
        focus_model=args.focus_model,
        live_print=not args.quiet,
    )
    # live_print already streamed turns; print summary checks always
    print_report(report, verbose=False)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2)
        )
        print(paint(f"Wrote {args.json_out}", "meta"))

    failed = [c for c in report.get("checks") or [] if not c.get("ok")]
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
