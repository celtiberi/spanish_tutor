"""Executor: realize a PlanCard as structured tutor speech.

Does not invent phase/move/topic — only fills language for the card.
"""

from __future__ import annotations

import json

from .plan_card import PlanCard

EXECUTOR_SYSTEM = """# Spanish tutor EXECUTOR (voice only)

You realize a fixed **PlanCard**. You do NOT choose the lesson.
You do NOT invent a new topic, phase, or activity.

## Hard rules
1. Use the card's models and try_prompt (you may polish slightly, not replace).
2. Output structured tags only (see shape).
3. Association-first: SHOW Spanish models freely — that is teaching, not spoiling.
4. **Never bare praise.** Do not put only *¡Muy bien!* in acknowledge.
   If you praise, always attach what they did OR the meaning of the new form
   (use english_frame). Example: "¡Muy bien! — you said *estoy*. **Me llamo** = My name is…"
5. Stay under max_sentences from the card. Short for TTS.
6. If english_frame is non-empty: put it in <acknowledge> (primary). Do not drop it.
7. If move is recast_retry: include <recast> with the clean form, then <try> same form.
8. If move is associate: one new form; state plain meaning once; point to the picture.
9. If allow_new_topic is false: do not ask about unrelated topics (coffee, pets, travel…).
10. Never mention PlanCard, sheet, tools, or tag names to the learner.
11. A teaching image may appear with the models. You do not invent file names;
    the app shows it. You may say: "Picture = greeting / my name / I am fine."

## Structured reply shape
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
Omit empty parts. Prefer model + try always for production moves.
"""


def build_executor_user_message(
    card: PlanCard,
    *,
    learner: str = "",
    is_open: bool = False,
) -> str:
    """User-turn content for the executor model."""
    payload = {
        "plan": card.as_dict(),
        "learner_said": learner if not is_open else "(session open — no learner line yet)",
        "is_open": is_open,
        "instructions": (
            "Realize this plan now. Put models in <model>, production in <try>. "
            "If recast_retry, clean form in <recast> then <try> the same form."
        ),
    }
    return (
        "<executor_task>\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n</executor_task>\n"
    )


def build_executor_system(
    *,
    sheet_summary: str = "",
    pack_palette: str = "",
) -> list[dict]:
    """System blocks for executor (thin). Optional sheet for tone only."""
    blocks = [{"type": "text", "text": EXECUTOR_SYSTEM}]
    if sheet_summary:
        blocks.append({
            "type": "text",
            "text": (
                "# Learner context (do not override the PlanCard)\n"
                + sheet_summary[:4000]
            ),
        })
    if pack_palette:
        blocks.append({
            "type": "text",
            "text": "# Pack palette (in-scope language)\n" + pack_palette[:6000],
            "cache_control": {"type": "ephemeral"},
        })
    return blocks
