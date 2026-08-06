"""AI tutor turn: frontier model decides pedagogy given full context.

The model is the teacher. Code supplies:
  - character sheet (what we know)
  - session memory (what already happened this chat)
  - hard observations (regex error hits, probe signals)
  - pedagogical *direction* (CLT, association, no loops, teach every turn)

Code does **not** script a Hola→Estoy→Me llamo ladder. That flashcard feel
came from the old rules_planner PlanCard ladder — deleted outright (E4,
docs/reviews-architecture-refactor.md, 2026-07-28).
"""

from __future__ import annotations

import json
from pathlib import Path
from . import config

CONV_PROMPT = config.REPO_ROOT / "prompts" / "conversational_tutor.md"



def load_persona() -> str:
    """Persona spec (voice/character layer) — optional, env-gated.

    Persona is the HOW; the gate and the teaching guide outrank it (the file
    itself opens with that rule). TUTOR_PERSONA=off disables.
    """
    if not getattr(config, "PERSONA_ENABLED", True):
        return ""
    path = getattr(config, "PERSONA_PATH", None)
    if not path or not Path(path).exists():
        return ""
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def build_ai_tutor_system() -> list[dict]:
    """STATIC system blocks only: stance → persona.  The per-turn sheet
    rides in the task message (build_ai_tutor_user_message) — any changed
    byte here would break provider prefix-caching for the whole chat.
    (The sheet_summary / personal_context params were DELETED 2026-08-03,
    full-code-audit S2: zero callers passed them — the sheet ships in the
    task payload and personal-data capture is disabled.)"""
    # SINGLE stance source (2026-08-04): the old inline AI_TUTOR_SYSTEM
    # shipped as a SECOND full prompt ahead of this file — two competing
    # shape contracts (its stale <continue> slot included), doubled rules,
    # and a line handing morphology to "the app" — which flattened the
    # persona and suppressed <morph> emission. Deleted outright (§4.6);
    # its unique rules were folded into conversational_tutor.md.
    text = ""
    try:
        text = CONV_PROMPT.read_text(encoding="utf-8")
    except OSError as e:
        # no-hide (audit C top offender #1): losing the stance strips
        # most of the teacher's instructions — never silently.
        import sys as _sys

        print(f"[no-hide] stance load FAILED, teaching without it: "
              f"{type(e).__name__}: {e}", file=_sys.stderr, flush=True)
        text = "# Conversational Spanish tutor\nTeach Spanish conversationally."
    # Testing default: no truncation (config.clip_prompt with cap=0 is a no-op).
    text = config.clip_prompt(text, getattr(config, "STANCE_PROMPT_CHARS", 0))
    # Block ORDER is a cost decision: providers cache by longest common
    # PREFIX, so static content (stance, persona) must come before anything
    # that changes per turn.
    blocks: list[dict] = [{"type": "text", "text": text}]
    persona = load_persona()
    if persona:
        blocks.append({
            "type": "text",
            "text": persona,
            # Anthropic explicit caching: marks the end of the stable prefix
            "cache_control": {"type": "ephemeral"},
        })
    return blocks

def build_ai_tutor_user_message(
    *,
    learner: str = "",
    is_open: bool = False,
    session_memory: dict | None = None,
    teach_images: list | None = None,
    blank_sheet: bool = False,
    sheet_summary: str = "",
    teaching_data: dict | None = None,
    session_plan: str | None = None,
    learner_text_facts: dict | None = None,
) -> str:
    """User-turn task: facts only; the AI is the teacher (§1.1).

    (The mode_decision parameter DELETED 2026-08-03 with the mode router;
    observations= and personal_context/learner_personal_context DELETED
    2026-08-03, full-code-audit S2 — no caller passed them and nothing
    injected them.)  The character sheet rides HERE (per-turn tail of the
    request), not in the system prompt: it changes every turn, and any
    changed byte in the system message would break provider prefix-caching
    for the entire chat history behind it. Cost decision, content unchanged.
    """
    mem = session_memory or {}
    payload = {
        "turn": {
            "learner_said": (
                learner if not is_open
                else "(session open — they have not spoken yet)"
            ),
            "is_open": is_open,
            "blank_character_sheet": blank_sheet,
        },
        # §1.1 REWRITE (USER 2026-08-03): the mode/phase/introduce routers'
        # instruction blocks NO LONGER SHIP — the model is the teacher and
        # plans from the facts below. Router output stays visible in
        # notes/debug as shadow telemetry only. (open_scene_goals DELETED
        # 2026-08-03 with scenes — full-code-audit S9.)
        "teaching_data": teaching_data or None,
        # Offline dictionary facts about THIS learner message (§1.1
        # fact-surface clause, 2026-08-05; experiment arms via
        # config.TEXT_FACTS — None when off or nothing to report).
        "learner_text_facts": learner_text_facts or None,
        # The model's OWN session plan (two-phase context, 2026-08-03) —
        # code stores and replays it verbatim, never edits it (§1.1).
        "your_session_plan": session_plan or None,
        "student_character_sheet": {
            "note": (
                "Spanish ABILITIES + the domain inventory. Adapt teaching "
                "from this; address active errors rather than re-probing "
                "known can-dos. "
                "Grade ability only via update_character_sheet (reason + "
                "evidence required). FORBIDDEN: never copy or re-emit this "
                "data in the learner reply."
            ),
            "sheet": config.clip_prompt(
                sheet_summary, getattr(config, "SHEET_PROMPT_CHARS", 0)
            ),
        } if sheet_summary else None,
        "session_facts": {
            "skills_learner_already_showed": mem.get("shown") or [],
            # Semantic asked-topic registry (2026-07-28 repetition forensics):
            # the old "topics_tutor_already_asked" carried MODE NAMES
            # ("ask_how","association",…) — useless to the model. These are
            # frame:concept keys ("size:ciudad") the tutor must not re-ask.
            "do_not_re_ask": mem.get("asked_topics") or [],
            "images_already_shown": mem.get("images_shown") or [],
            "turn_index": mem.get("turns") or 0,
            "from_character_sheet": mem.get("sheet_seeded") or False,
        },
        # hard_observations DROPPED (§1.1 rewrite): regex probe signals and
        # next_best were code's opinion of the lesson; the model reads the
        # learner's actual words and the sheet itself.
        "visual": {
            "attached_this_turn": [
                {
                    "concept": t.get("concept"),
                    "form": t.get("form"),
                    "caption": t.get("caption"),
                }
                for t in (teach_images or [])
            ],
        },
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    # The r9 TEACHER_PROMPT_ORDER falsifier arms (p1_reorder /
    # p2_structured FINAL_CONSTRAINTS) were DELETED 2026-08-03
    # (full-code-audit S1f): dormant script blocks; the referee run
    # settled the question and the arms had no live selector.
    return (
        "<tutor_turn_task>\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n</tutor_turn_task>\n"
    )
