"""AI student (Grok) vs conversational Spanish tutor — simulation harness.

Runs a Grok-powered learner with a fixed personality / ability profile against
`ConversationalSession`, writing a **separate** character sheet so Patrick’s
live sheet is untouched.

  python -m tutor.ai_student
  python -m tutor.ai_student --turns 6 --persona alex_boat
  python -m tutor.ai_student --sheet logs/ai_student_sheet.json --reset-sheet

Env:
  AI_STUDENT_MODEL   default grok-4.5 (capable learner for useful sims)
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

# ---------------------------------------------------------------------------
# Personas
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
        # id aligns with character_sheet ERROR_PATTERN catalog when possible
        "error_tendencies": [
            {
                "id": "estar_yo_estoy_vs_esta",
                "label": "yo + está instead of estoy",
                "bad_examples": [
                    "Yo está en el bote",
                    "Yo está bien",
                    "Está en Río Dulce",  # intending "I am"
                ],
                "good_examples": ["Estoy en el bote", "Estoy bien", "Yo estoy aquí"],
                "strength": 0.85,
            },
            {
                "id": "register_tu_usted_mix",
                "label": "mix tú/usted casually without control",
                "bad_examples": ["Cómo está? (to a peer while also saying tú)"],
                "good_examples": ["¿Cómo estás?"],
                "strength": 0.4,
            },
        ],
        "learning_rate": 0.18,
        "notes": "Default sim student for sheet / recast testing.",
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
        "learning_rate": 0.12,
        "notes": "Slightly stronger base; different error focus.",
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
            f"Unknown persona {name!r}. Choose: {', '.join(PERSONAS)}"
        )
    return copy.deepcopy(PERSONAS[key])


# ---------------------------------------------------------------------------
# True ability state (ground truth — not the teacher's sheet)
# ---------------------------------------------------------------------------

@dataclass
class TrueAbility:
    """What the simulated student 'really' can do / still messes up."""

    error_strength: dict[str, float] = field(default_factory=dict)
    recasts_seen: dict[str, int] = field(default_factory=dict)
    turns: int = 0

    @classmethod
    def from_persona(cls, persona: dict) -> "TrueAbility":
        strengths = {
            e["id"]: float(e.get("strength") or 0.5)
            for e in persona.get("error_tendencies") or []
            if e.get("id")
        }
        return cls(error_strength=strengths)

    def on_tutor_reply(self, tutor_text: str, persona: dict) -> list[str]:
        """Weaken errors when tutor clearly models the good form."""
        notes: list[str] = []
        low = (tutor_text or "").lower()
        # Strip accents for matching
        fold = (
            low.replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )
        for err in persona.get("error_tendencies") or []:
            eid = err.get("id") or ""
            goods = err.get("good_examples") or []
            hit = False
            for g in goods:
                g_tokens = re.findall(r"[a-záéíóúüñ]{3,}", g.lower())
                # need at least one distinctive token present
                if g_tokens and any(t in low for t in g_tokens[:3]):
                    hit = True
                    break
            # pattern-specific boosts
            if eid == "estar_yo_estoy_vs_esta" and re.search(
                r"\bestoy\b", low
            ):
                hit = True
            if eid == "ser_estar_confuse" and (
                re.search(r"\bestoy\s+(nervios|bien|mal|feliz|triste)", fold)
                or re.search(r"\buse\s+\*?estar\*?\b", fold)
                or ("estar" in fold and "soy" in fold and "nerv" in fold)
            ):
                hit = True
            if hit and eid:
                self.recasts_seen[eid] = self.recasts_seen.get(eid, 0) + 1
                rate = float(persona.get("learning_rate") or 0.15)
                old = self.error_strength.get(eid, 0.5)
                new = max(0.05, old * (1.0 - rate))
                self.error_strength[eid] = new
                notes.append(f"learn:{eid} {old:.2f}→{new:.2f}")
        self.turns += 1
        return notes

    def snapshot(self) -> dict:
        return {
            "error_strength": dict(self.error_strength),
            "recasts_seen": dict(self.recasts_seen),
            "turns": self.turns,
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
    """Grok-backed learner that emits one student utterance per tutor turn."""

    def __init__(
        self,
        persona: dict[str, Any],
        *,
        model: str | None = None,
    ):
        config.load_env()
        self.persona = persona
        self.model = model or default_student_model()
        self.caps = config.caps_for(self.model)
        self.client = config.make_client_for(self.model)
        self.true = TrueAbility.from_persona(persona)
        self.history: list[dict] = []  # student-visible: user=tutor, assistant=self
        self._leave_streak = 0

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

    def _system_text(self, *, tutor_message: str = "") -> str:
        base = STUDENT_PROMPT.read_text() if STUDENT_PROMPT.exists() else (
            "You are a Spanish learner. Reply only as the student."
        )
        p = self.persona
        err_lines = []
        for e in p.get("error_tendencies") or []:
            eid = e.get("id") or "?"
            strength = self.true.error_strength.get(
                eid, float(e.get("strength") or 0.5)
            )
            prefer = (
                "PREFER GOOD forms now (strength low)"
                if strength < 0.4
                else "usually make the MISTAKE"
            )
            err_lines.append(
                f"- {eid} (strength={strength:.2f} — {prefer}): {e.get('label')}\n"
                f"  mistakes: {e.get('bad_examples')}\n"
                f"  good forms: {e.get('good_examples')}"
            )
        profile = {
            "name": p.get("name"),
            "personality": p.get("personality"),
            "ability": p.get("ability"),
            "L1": p.get("L1"),
            "interests": p.get("interests"),
            "solid_phrases": p.get("solid_phrases"),
            "learning_rate": p.get("learning_rate"),
            "error_strength_now": self.true.error_strength,
        }
        extra = ""
        if self._leave_looping():
            extra += (
                "\n## Harness override — STOP THE GOODBYE LOOP\n"
                "You already said goodbye. Do **not** say adiós/gracias only. "
                "Answer with a real chat line about the boat, weather, coffee, "
                "or how you feel — or ask a simple question.\n"
            )
        # If tutor models estoy and strength is moderate, nudge attempt
        if re.search(r"\bestoy\b", tutor_message or "", re.I):
            st = self.true.error_strength.get("estar_yo_estoy_vs_esta", 1.0)
            if st < 0.55:
                extra += (
                    "\n## Harness nudge\n"
                    "Tutor just modeled **estoy**. Try using *estoy* (not *está*) "
                    "for yourself this turn if you talk about where you are / how you are.\n"
                )
        return (
            base
            + "\n\n## Your profile (ground truth)\n"
            + json.dumps(profile, ensure_ascii=False, indent=2)
            + "\n\n## Error tendencies (follow these)\n"
            + ("\n".join(err_lines) if err_lines else "(none)")
            + f"\n\n## Name\nYou are **{p.get('name') or 'the student'}**.\n"
            + extra
        )

    def respond(self, tutor_message: str) -> tuple[str, dict]:
        """Return (student_utterance, usage)."""
        tutor_message = (tutor_message or "").strip()
        if not tutor_message:
            tutor_message = "(The tutor is waiting for you to say something.)"

        # history: from student POV, tutor is "user"
        self.history.append({"role": "user", "content": tutor_message})

        system = [{
            "type": "text",
            "text": self._system_text(tutor_message=tutor_message),
        }]
        # Keep last few exchanges only (cheap + focused)
        msgs = self.history[-12:]

        final = self.client.messages.create(
            model=self.caps.model,
            max_tokens=256,
            system=system,
            messages=msgs,
        )
        texts = []
        for b in getattr(final, "content", None) or []:
            if getattr(b, "type", None) == "text":
                t = getattr(b, "text", "") or ""
                if t:
                    texts.append(t)
        raw = "\n".join(texts).strip()
        raw = clean_student_utterance(
            raw, persona_name=str(self.persona.get("name") or "")
        )

        # Soft break if model still only goodbyes while looping
        if self._leave_looping() and _LEAVE_RE.search(raw) and len(raw.split()) <= 6:
            interests = self.persona.get("interests") or ["the boat"]
            topic = interests[self.true.turns % len(interests)]
            raw = f"Um… wait — about {topic}, it is nice today."

        self.history.append({"role": "assistant", "content": raw})
        if _LEAVE_RE.search(raw) and len(raw.split()) <= 6:
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
        }
        return raw, usage


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
            f"Sim student ({persona.get('id')}) — practice chat"
        ]
        save_sheet(sheet_path, sheet)

    teacher = ConversationalSession(
        model=tutor_model or config.MODEL,
        sheet_path=sheet_path,
        label=f"ai-student-{persona.get('id')}",
        focus_model=focus_model if focus_model is not None else "off",
    )
    student = AIStudentAgent(
        persona, model=student_model or default_student_model()
    )

    slog = SimLogger(
        label=persona.get("id") or "student",
        meta={
            "persona": persona.get("id"),
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
        student_text, _su = student.respond(tutor_msg)
        _live(f"student> {student_text}", "ok")
        tr = teacher.user_turn(student_text, input_mode="text")
        if tr.error:
            raise RuntimeError(f"teacher turn {i} failed: {tr.error}")
        _live(f"tutor> {tr.reply}", "tutor_label")
        ln = student.true.on_tutor_reply(tr.reply, persona)
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
    checks: list[dict] = []
    checks.append({
        "id": "teacher_replied",
        "ok": all(bool(t.student) and bool(t.tutor_reply) for t in log),
        "detail": f"{len(log)} complete exchanges",
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
    for eid, n in true.recasts_seen.items():
        if n <= 0 or not log:
            continue
        first = (log[0].true_ability.get("error_strength") or {}).get(eid)
        last = true.error_strength.get(eid)
        ok = first is None or last is None or last <= first + 1e-6
        checks.append({
            "id": f"learning_down_{eid}",
            "ok": ok,
            "detail": f"recasts={n} strength {first}→{last}",
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
        f"({report.get('persona')})",
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
