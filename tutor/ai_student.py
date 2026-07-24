"""AI student (Grok) vs conversational Spanish tutor — simulation harness.

Runs a Grok-powered learner with a fixed personality / ability profile against
`ConversationalSession`, writing a **separate** character sheet so Patrick’s
live sheet is untouched.

  python -m tutor.ai_student
  python -m tutor.ai_student --turns 6 --persona alex_boat
  python -m tutor.ai_student --sheet logs/ai_student_sheet.json --reset-sheet

Env:
  AI_STUDENT_MODEL   default grok-3-mini (cheap learner)
  TUTOR_MODEL        teacher model (default gemini-3.6-flash)
  GROK_API_KEY       required for the student
"""

from __future__ import annotations

import argparse
import copy
import json
import re
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
DEFAULT_STUDENT_MODEL = "grok-3-mini"
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
                "bad_examples": ["Soy en la casa", "Estoy estudiante"],
                "good_examples": ["Estoy en la casa", "Soy estudiante"],
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
        for err in persona.get("error_tendencies") or []:
            eid = err.get("id") or ""
            goods = err.get("good_examples") or []
            hit = False
            for g in goods:
                # loose match: key tokens present
                g_tokens = re.findall(r"[a-záéíóúüñ]{3,}", g.lower())
                if g_tokens and all(t in low for t in g_tokens[:2]):
                    hit = True
                    break
            # pattern-specific boosts
            if eid == "estar_yo_estoy_vs_esta" and re.search(
                r"\bestoy\b", low
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

    def _system_text(self) -> str:
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
            err_lines.append(
                f"- {eid} (strength={strength:.2f}): {e.get('label')}\n"
                f"  prefer mistakes like: {e.get('bad_examples')}\n"
                f"  only use good forms like {e.get('good_examples')} "
                f"if strength is low or tutor just modeled them"
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
        return (
            base
            + "\n\n## Your profile (ground truth)\n"
            + json.dumps(profile, ensure_ascii=False, indent=2)
            + "\n\n## Error tendencies (follow these)\n"
            + ("\n".join(err_lines) if err_lines else "(none)")
            + f"\n\n## Name\nYou are **{p.get('name') or 'the student'}**.\n"
        )

    def respond(self, tutor_message: str) -> tuple[str, dict]:
        """Return (student_utterance, usage)."""
        tutor_message = (tutor_message or "").strip()
        if not tutor_message:
            tutor_message = "(The tutor is waiting for you to say something.)"

        # history: from student POV, tutor is "user"
        self.history.append({"role": "user", "content": tutor_message})

        system = [{"type": "text", "text": self._system_text()}]
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
        # Strip accidental meta wrappers
        raw = re.sub(r"^```.*?\n", "", raw)
        raw = re.sub(r"\n```$", "", raw)
        raw = raw.strip().strip('"')
        if not raw:
            raw = "um… hola?"

        self.history.append({"role": "assistant", "content": raw})
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


def run_simulation(
    *,
    turns: int = DEFAULT_TURNS,
    persona_id: str = "alex_boat",
    student_model: str | None = None,
    tutor_model: str | None = None,
    sheet_path: Path | None = None,
    reset_sheet: bool = True,
    focus_model: str | None = "off",
) -> dict[str, Any]:
    """Run N student↔tutor exchanges. Returns report dict."""
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

    open_turn = teacher.open_session()
    if open_turn.error:
        raise RuntimeError(f"teacher open failed: {open_turn.error}")

    log: list[SimTurn] = []
    tutor_msg = open_turn.reply
    student.true.on_tutor_reply(tutor_msg, persona)

    for i in range(1, turns + 1):
        student_text, _su = student.respond(tutor_msg)
        tr = teacher.user_turn(student_text, input_mode="text")
        if tr.error:
            raise RuntimeError(f"teacher turn {i} failed: {tr.error}")
        ln = student.true.on_tutor_reply(tr.reply, persona)
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
            )
        )
        tutor_msg = tr.reply

    sheet = load_sheet(sheet_path)
    report = {
        "persona": persona.get("id"),
        "student_name": persona.get("name"),
        "student_model": student.model,
        "tutor_model": teacher.model,
        "sheet_path": str(sheet_path),
        "turns": turns,
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
                "learn_notes": t.learn_notes,
                "next_best_can_do": (t.next_best or {}).get("can_do"),
                "has_recast": bool((t.parts or {}).get("recast")),
                "true_ability": t.true_ability,
            }
            for t in log
        ],
        "checks": _verification_checks(sheet, student.true, log),
    }
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
    ap.add_argument("--turns", type=int, default=DEFAULT_TURNS)
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
    report = run_simulation(
        turns=max(1, args.turns),
        persona_id=args.persona,
        student_model=args.student_model,
        tutor_model=args.tutor_model,
        sheet_path=args.sheet,
        reset_sheet=reset,
        focus_model=args.focus_model,
    )
    print_report(report, verbose=not args.quiet)
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
