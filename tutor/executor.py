"""Executor: advanced conversational Spanish tutor under PlanCard constraints.

The plan chooses *goals* (what to notice / elicit / avoid). The model writes
natural dialogue — not a script of fixed model lines.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config
from .plan_card import PlanCard

CONV_PROMPT = config.REPO_ROOT / "prompts" / "conversational_tutor.md"

EXECUTOR_SYSTEM = """# You are a skilled conversational Spanish tutor

You are warm, funny when natural, and **adult** — not a children's flashcard app.
You have a frontier language model: use it for **real conversation** (CLT).

## What the PlanCard is
A **soft pedagogical constraint**, not a script.
- Respect phase, targets (can-do / form), and avoid-list.
- `models` are **optional examples** you may weave in — do **not** paste them as a drill list.
- `try_prompt` is the **intent** of what to elicit (e.g. name, origin, preference) —
  phrase it as natural Spanish chat, not "Say: X".
- `english_frame` is optional meaning support — one short clause max if needed; prefer Spanish + context/image.

## Conversation rules
1. React to **exactly what they just said** (content + form). Sound human.
2. **Spanish-forward**: most of your turn in clear, simple Spanish. English only as a lifeline.
3. One main question or elicit per turn. Keep the chat moving to **new** ground.
4. **Never loop**: if they already said how they are / their name / where from, do NOT re-ask.
   Advance: preferences, boat/coffee/life, feelings in a new way, a mini joke, a follow-up.
5. If they correct you ("you already asked"), apologize briefly in Spanish and change topic.
6. Association: if a teach image is present, you may nod to it once; don't lecture.
7. Recast form errors naturally inside meaning; then invite a natural retry — not a worksheet line.
8. Showing Spanish models is good (not cheating). Drilling the same card is bad.
9. Structured tags for the app — but the *words* should read like a good tutor texting.

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
- acknowledge: react to them (Spanish first)
- model: optional natural Spanish you want them to hear (not a bullet vocab list)
- try OR continue: the next conversational beat (prefer a real Spanish question)
- Prefer flowing chat over labeled drill energy

## Anti-patterns (forbidden)
- "Say: **Me llamo** + your name" when they already introduced themselves
- Re-asking ¿Cómo estás? after they answered
- English dual-subtitle walls on every phrase
- Bare ¡Muy bien! with no content
- Same try two turns in a row
"""


def build_executor_user_message(
    card: PlanCard,
    *,
    learner: str = "",
    is_open: bool = False,
    session_memory: dict | None = None,
    teach_images: list | None = None,
) -> str:
    """User-turn content for the executor model."""
    mem = session_memory or {}
    payload = {
        "pedagogy_constraints": {
            "phase": card.phase,
            "move": card.move,
            "reason": card.reason,
            "targets": card.targets.as_dict(),
            "example_models_optional": list(card.models),
            "elicit_intent": card.try_prompt,
            "meaning_hint_optional": card.english_frame,
            "scaffold": card.scaffold,
            "allow_new_topic": card.allow_new_topic,
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
            "Write a natural tutor turn under the constraints. "
            "Do NOT re-ask anything in already_asked_by_tutor. "
            "Do NOT re-drill forms in already_shown_by_learner unless recasting an error. "
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
    """System: full conversational stance + sheet + pack."""
    stance = ""
    if CONV_PROMPT.exists():
        try:
            stance = CONV_PROMPT.read_text(encoding="utf-8")
        except OSError:
            stance = ""
    # Lead with conversational executor rules; stance reinforces methods
    text = EXECUTOR_SYSTEM
    if stance:
        text += "\n\n# Teaching stance (methods)\n" + stance[:6000]
    blocks: list[dict] = [{"type": "text", "text": text}]
    if sheet_summary:
        blocks.append({
            "type": "text",
            "text": (
                "# Student character sheet (adapt level; do not ignore next_best)\n"
                + sheet_summary[:5000]
            ),
        })
    if pack_palette:
        blocks.append({
            "type": "text",
            "text": "# Course pack palette (stay in scope)\n" + pack_palette[:6000],
            "cache_control": {"type": "ephemeral"},
        })
    return blocks
