"""AI tutor turn: frontier model decides pedagogy given full context.

The model is the teacher. Code supplies:
  - character sheet (what we know)
  - session memory (what already happened this chat)
  - hard observations (regex error hits, probe signals)
  - pedagogical *direction* (CLT, association, no loops, teach every turn)

Code does **not** script a Hola→Estoy→Me llamo ladder. That flashcard feel
came from rules_planner owning the agenda; that path is optional fallback only
(TEACHER_MODE=rules).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config

CONV_PROMPT = config.REPO_ROOT / "prompts" / "conversational_tutor.md"

AI_TUTOR_SYSTEM = """# You are a skilled conversational Spanish tutor

You are warm, adult, and competent — **not** a children's flashcard app and
**not** a scripted probe ladder. You have a strong language model: use judgment.

## Your job
Run a real Spanish conversation that **teaches**. Every turn should help them
associate form with meaning (hear/see model → try → recast when needed).

## Who decides the next move?
**You do.** There is no external script telling you "now ask name, then origin."
Use the character sheet, session facts, and what they just said.

## Pedagogical direction (always)
1. **CLT** — language for real communication, not worksheet lines.
2. **Comprehensible input** — mostly clear Spanish; English is a lifeline only.
3. **Association** — show Spanish freely (models are teaching, not cheating).
   Prefer context/image over dual-subtitle English walls (*X = Y* on every line).
4. **Focus on form** — if they err on person/tense/construction, recast naturally
   inside meaning, then invite the same form again in chat.
5. **One main elicit per turn** — one real Spanish question or invite.
6. **Never loop** — if session_facts say they already gave name / how-are-you /
   origin, do **not** re-ask. Advance the conversation.
7. **Blank sheet** — you are placing them. Start simple and friendly; do not
   monologue intermediate Spanish. Feel out with real chat, not "Say: Hola."
8. **next_best** on the sheet is a *guide*, not a railroad. Prefer reacting to
   what they just said first.
9. **Teach every turn** — at least model and/or try (or recast+retry). Bare
   hangout with no Spanish model is a fail.

## Anti-patterns (forbidden)
- Fixed flashcard ladder (Hola card → Estoy card → Me llamo card)
- "Say: **Me llamo** + your name" / "Di: …" worksheet energy
- Re-asking ¿Cómo estás? / ¿Cómo te llamas? after they answered
- English dual-subtitle walls on every phrase
- Bare ¡Muy bien! with no content
- Ignoring a clear form error to chase a new can-do

## Output shape (required tags; omit empty)
```
<tutor>
  <acknowledge>...</acknowledge>
  <recast>...</recast>
  <explain depth="brief">...</explain>
  <model>...</model>
  <try>...</try>
  <continue>...</continue>
</tutor>
```
- **acknowledge**: react to *their* content (Spanish first)
- **model**: natural Spanish they should hear (not a vocab bullet list)
- **try**: next conversational beat — prefer a real Spanish question
- Words should read like a good tutor texting, not a labeled drill

## Tools
Call `update_character_sheet` in the same turn when you get new evidence
(name, can-do production, form errors, scaffold needs). Partial delta only.
Never put sheet JSON or can-do codes in learner-facing text.
"""


def build_ai_tutor_system(
    *,
    sheet_summary: str = "",
    pack_palette: str = "",
) -> list[dict]:
    """System blocks: stance + sheet + pack."""
    stance = ""
    if CONV_PROMPT.exists():
        try:
            stance = CONV_PROMPT.read_text(encoding="utf-8")
        except OSError:
            stance = ""
    text = AI_TUTOR_SYSTEM
    stance_cap = getattr(config, "STANCE_PROMPT_CHARS", 2200)
    pack_cap = getattr(config, "PACK_PROMPT_CHARS", 1800)
    sheet_cap = 2500
    if stance:
        # Methods reinforce; keep short for latency (was 5–6k chars)
        text += "\n\n# Teaching methods (detail)\n" + stance[:stance_cap]
    blocks: list[dict] = [{"type": "text", "text": text}]
    if sheet_summary:
        blocks.append({
            "type": "text",
            "text": (
                "# Student character sheet — your model of this learner\n"
                "Adapt level and stretch. Do not ignore fragile forms or "
                "next_best, but never ignore what they just said.\n\n"
                + sheet_summary[:sheet_cap]
            ),
        })
    if pack_palette:
        blocks.append({
            "type": "text",
            "text": "# Course pack palette (stay in scope)\n" + pack_palette[:pack_cap],
            "cache_control": {"type": "ephemeral"},
        })
    return blocks

def build_ai_tutor_user_message(
    *,
    learner: str = "",
    is_open: bool = False,
    session_memory: dict | None = None,
    observations: dict | None = None,
    teach_images: list | None = None,
    blank_sheet: bool = False,
    mode_decision: dict | None = None,
    open_scene_hints: list | None = None,
) -> str:
    """User-turn task: code-selected mode + facts; AI realizes the turn."""
    mem = session_memory or {}
    obs = observations or {}
    mode = mode_decision or {}
    payload = {
        "turn": {
            "learner_said": (
                learner if not is_open
                else "(session open — they have not spoken yet)"
            ),
            "is_open": is_open,
            "blank_character_sheet": blank_sheet,
        },
        "mode": {
            "name": mode.get("mode") or "conversation",
            "reason": mode.get("reason") or "",
            "hard_break": bool(mode.get("hard_break")),
            "targets": mode.get("targets") or {},
            "instructions": mode.get("instructions") or "",
            "image_concept": mode.get("image_concept"),
            "scene_ids": mode.get("scene_ids") or [],
        },
        "open_scene_goals": open_scene_hints or [],
        "session_facts": {
            "skills_learner_already_showed": mem.get("shown") or [],
            "topics_tutor_already_asked": mem.get("asked") or [],
            "images_already_shown": mem.get("images_shown") or [],
            "turn_index": mem.get("turns") or 0,
        },
        "hard_observations": {
            "probe_signals": obs.get("signals") or [],
            "form_error_hits": obs.get("error_hits") or [],
            "active_error_patterns_on_sheet": obs.get("active_errors") or [],
            "next_best_can_do": obs.get("next_best") or {},
        },
        "visual": {
            "attached_this_turn": [
                {
                    "concept": t.get("concept"),
                    "form": t.get("form"),
                    "caption": t.get("caption"),
                }
                for t in (teach_images or [])
            ],
            "note": (
                "If an image is attached, associate it with the Spanish you model. "
                "Do not invent an image when the list is empty."
            ),
        },
        "product_persona": {
            "who": (
                "Adult conversational A1 — false-beginners + true zeros. "
                "Boat/café life OK. Not a kids app."
            ),
            "system": (
                "Conversation is the vehicle. MODE is the pedagogy for this turn — "
                "obey mode.instructions. Hard breaks leave free-chat shape "
                "(contrast, choice, image-led). Soft modes stay in chat."
            ),
        },
        "mode_playbooks": {
            "placement": "Wide ceiling open; model short Spanish; one elicit; not a worksheet.",
            "conversation": "React, model, one real Spanish question; advance topics.",
            "cf_recast": (
                "REQUIRED short <recast> with clean Spanish (one line). "
                "Then continue chat — do not derail into a long grammar lecture."
            ),

            "form_focus": (
                "HARD BREAK: brief wrong→right contrast for the error_pattern; "
                "one choice or produce; then transfer try in new micro-context."
            ),
            "association": (
                "HARD BREAK: form + image meaning; Spanish-forward; try about the picture."
            ),
            "comprehension_check": "Yes/no or A/B on meaning of the model — not free production.",
            "comprehension_repair": (
                "They did not understand your last Spanish. Explain briefly, use image if present, "
                "re-model simpler Spanish of the SAME idea, re-ask the SAME question — "
                "NEVER a brand-new topic."
            ),
            "transfer": "Same form, new context; celebrate briefly; no re-drill.",
        },

        "instructions": [
            "Realize MODE only — do not invent a different agenda.",
            "React to what they said when in conversation/recast/transfer.",
            "Mostly Spanish. No flashcard ladder. No re-asking covered probes.",
            "Open scene goals are optional quests — close them opportunistically if natural.",
        ],
    }
    return (
        "<tutor_turn_task>\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n</tutor_turn_task>\n"
    )


# ---------------------------------------------------------------------------
# Legacy PlanCard executor (TEACHER_MODE=rules only)
# ---------------------------------------------------------------------------

EXECUTOR_SYSTEM = """# You are a skilled conversational Spanish tutor (rules PlanCard mode)

PlanCard is a soft constraint, not a flashcard script. Write natural Spanish chat.
"""


def build_executor_user_message(
    card: Any,
    *,
    learner: str = "",
    is_open: bool = False,
    session_memory: dict | None = None,
    teach_images: list | None = None,
) -> str:
    """Legacy: PlanCard-bound user message (rules mode)."""
    mem = session_memory or {}
    payload = {
        "pedagogy_constraints": {
            "phase": getattr(card, "phase", ""),
            "move": getattr(card, "move", ""),
            "reason": getattr(card, "reason", ""),
            "targets": (
                card.targets.as_dict()
                if hasattr(card, "targets") and hasattr(card.targets, "as_dict")
                else {}
            ),
            "example_models_optional": list(getattr(card, "models", None) or []),
            "elicit_intent": getattr(card, "try_prompt", ""),
            "meaning_hint_optional": getattr(card, "english_frame", ""),
            "scaffold": getattr(card, "scaffold", "es_forward"),
            "allow_new_topic": getattr(card, "allow_new_topic", True),
            "avoid_loop": True,
            "already_shown_by_learner": mem.get("shown") or [],
            "already_asked_by_tutor": mem.get("asked") or [],
            "image_concepts": [
                (t.get("concept"), t.get("form"), t.get("caption"))
                for t in (teach_images or [])
            ],
        },
        "learner_said": (
            learner if not is_open else "(session open — greet them and start a real chat)"
        ),
        "is_open": is_open,
        "instructions": (
            "Write a natural tutor turn. Do not re-ask already_asked topics. "
            "Advance the conversation. Mostly Spanish."
        ),
    }
    return (
        "<tutor_turn_task>\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n</tutor_turn_task>\n"
    )


def build_executor_system(
    *,
    sheet_summary: str = "",
    pack_palette: str = "",
) -> list[dict]:
    """Legacy alias → AI tutor system (same stance either way)."""
    return build_ai_tutor_system(
        sheet_summary=sheet_summary,
        pack_palette=pack_palette,
    )
