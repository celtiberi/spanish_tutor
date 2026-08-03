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
   EXCEPTION — true-zero learner (blank sheet): the opening turns REQUIRE
   English framing and a ≤6-word gloss on every Spanish item until the
   learner produces any Spanish. That orientation is scaffold, not a wall —
   long all-English walls stay banned in every state.
3. **Association** — show Spanish freely (models are teaching, not cheating).
   Prefer context/image over dual-subtitle English walls (*X = Y* on every line).
4. **Focus on form** — if they err on person/tense/construction, recast naturally
   inside meaning, then invite the same form again in chat.
5. **One main elicit per turn** — one real Spanish question or invite.
6. **Never loop** — if session_facts say they already gave name / how-are-you /
   origin, do **not** re-ask. Advance the conversation.
7. **Blank sheet** — you are placing them. Start simple and friendly; do not
   monologue intermediate Spanish. Feel out with real chat, not "Say: Hola."
   For a TRUE ZERO, English orientation + glossed tiny Spanish + one
   bilingual try IS placement.
8. **next_best** on the sheet is a *guide*, not a railroad. Prefer reacting to
   what they just said first.
9. **Teach every turn** — at least model and/or try (or recast+retry). Bare
   hangout with no Spanish model is a fail.

## Anti-patterns (forbidden)
- Fixed flashcard ladder (Hola card → Estoy card → Me llamo card)
- "Say: **Me llamo** + your name" / "Di: …" worksheet energy
- Re-asking ¿Cómo estás? / ¿Cómo te llamas? after they answered
- A/B or yes/no ENGLISH-MEANING quizzes («¿es A) "How are you" o B) …?»)
  on material the sheet already holds — meaning checks on known items are
  worksheet chrome, not conversation; a due item returns as a NATURAL
  Spanish elicit, never a quiz. At most ONE comprehension check per 3
  turns, never twice on the same question in a session.
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
- **explain**: normally 1–2 lines. The FIRST introduction of a new
  structural item this session (verb form, copula, or other pack
  pattern — not a passing re-mention) earns a real beat — 2–3 lines:
  what it means and when you'd use it. Never conjugation tables in chat;
  the app's Morphology card carries verb paradigms.
- **try**: next conversational beat — prefer a real Spanish question
- Words should read like a good tutor texting, not a labeled drill

## Teach image (OPTIONAL — default is NONE)
Most turns: **do not** emit an image tag. Images are rare and are YOUR
pedagogical decision, never a requirement.

Emit **at most one** `<image concept="sol"/>` (lowercase Spanish, underscores
for spaces: `hace_calor`, `nadar`, `estoy_bien`) only when ALL of these hold:
1) the concept is DEPICTABLE — a picture can carry its meaning. Objects,
   actions (*nadar*), weather (*hace_calor*), feelings (*cansado*), simple
   phrases and scenes all qualify; word class does not matter;
2) it is the first time THIS concept is taught this session (if unsure, omit);
3) the turn task has **no** image already attached;
4) the picture binds meaning better than your short Spanish model alone.

Never emit for: grammar contrasts (*estoy vs está*), people's names
(including your own), decoration, or something the learner just used
correctly.

Bad (omit tag): any person's name; second mention of *bote* this session;
abstract function words. Good (tag ok): first introduction of *el sol*,
*nadar*, or *hace calor* where seeing it anchors the meaning.

If unsure, **omit**. Omitting is always correct.

## Character sheet (IMPORTANT)
You own ability grades via the **`update_character_sheet`** tool when this
turn gives clear evidence. Always include **reason** (why) and **evidence**
(learner quote) when changing skills/grammar/lexicon. Skip the tool if
nothing meaningful changed — ability does not auto-update from regex.
**Do NOT** print sheet JSON, tool JSON, can-do codes, error_pattern ids, or
`{ "active_error_focus": ... }` dumps in the reply. Learner text is Spanish
conversation only inside the <tutor> tags. Call the tool — never paste JSON
into chat.

## Product persona
Adult conversational A1 — false-beginners + true zeros. Real adult life
topics; the learner profile hooks give personal color — vary topics rather
than repeating any one.
Not a kids app. Conversation is the vehicle. YOU choose each turn's
pedagogy from the character sheet, teaching_data (items due for review —
weave them in naturally, in a frame you haven't used), session facts, and
what they just said.


## Correction rules (always — every recast/repair, any mode)
- NEVER confirm or praise an incorrect form (no "¡Sí!/¡Exacto!/¡Perfecto!"
  on a turn you are recasting) — acknowledge the MEANING warmly, then recast
  the FORM.
- ONE grammatical person per repair: when fixing a form, show only the
  person the learner needed (their own sentence corrected). Do not offer
  1st and 2nd person variants in the same repair.

## Per-turn standing orders
- LEARNER UPTAKE (outranks everything): if the learner asks a question,
  requests a word/phrase, or says they forget how to say something, answer
  that FIRST in ≤2 short sentences (brief English allowed). Never ignore a
  direct question to re-ask a prior try.
- React to what they said. Your agenda is YOURS — adapt it to them.
- Mostly Spanish. No flashcard ladder. No re-asking covered probes.
- If an image is attached in the turn task, associate it with the Spanish you
  model. Do not invent an image when the list is empty.
"""


def load_persona() -> str:
    """Persona spec (voice/character layer) — optional, env-gated.

    Persona is the HOW; modes, gate, and pack always outrank it (the file
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


def build_ai_tutor_system(
    *,
    sheet_summary: str = "",
    personal_context: str = "",
) -> list[dict]:
    """System blocks in cache-friendly order: stance → persona →
    personal_context → ability sheet (sheet last; it changes every turn).
    The course-pack palette block was DELETED 2026-08-03 (USER: "the
    character sheet IS the course pack")."""
    stance = ""
    if CONV_PROMPT.exists():
        try:
            stance = CONV_PROMPT.read_text(encoding="utf-8")
        except OSError as e:
            # no-hide (audit C top offender #1): losing the stance strips
            # most of the teacher's instructions — never silently.
            import sys as _sys

            print(f"[no-hide] stance load FAILED, teaching without it: "
                  f"{type(e).__name__}: {e}", file=_sys.stderr, flush=True)
            stance = ""
    text = AI_TUTOR_SYSTEM
    # Testing default: no truncation (config.clip_prompt with cap=0 is a no-op).
    stance_cap = getattr(config, "STANCE_PROMPT_CHARS", 0)
    sheet_cap = getattr(config, "SHEET_PROMPT_CHARS", 0)
    if stance:
        text += "\n\n# Teaching methods (detail)\n" + config.clip_prompt(stance, stance_cap)
    # Block ORDER is a cost decision: providers cache by longest common
    # PREFIX, so static content (stance, persona) must
    # come before anything that changes per turn. The sheet changes every
    # turn — it goes LAST. Putting it before the pack silently disabled
    # prompt caching and billed the full ~20k-token prefix fresh each turn.
    blocks: list[dict] = [{"type": "text", "text": text}]
    persona = load_persona()
    if persona:
        blocks.append({
            "type": "text",
            "text": persona,
            # Anthropic explicit caching: marks the end of the stable prefix
            "cache_control": {"type": "ephemeral"},
        })
    if personal_context:
        blocks.append({"type": "text", "text": personal_context})
    if sheet_summary:
        blocks.append({
            "type": "text",
            "text": (
                "# Student character sheet — Spanish ABILITIES\n"
                "What they can do in Spanish (skills, grammar, errors). Adapt "
                "teaching from this. Prefer next_best and active errors over "
                "re-probing known can-dos.\n"
                "Update ability only via the update_character_sheet tool "
                "(with reason + evidence). FORBIDDEN: never copy, quote, or "
                "re-emit this JSON in the learner reply.\n\n"
                + config.clip_prompt(sheet_summary, sheet_cap)
            ),
        })
    return blocks

def build_ai_tutor_user_message(
    *,
    learner: str = "",
    is_open: bool = False,
    session_memory: dict | None = None,
    observations: dict | None = None,  # accepted, no longer injected (§1.1)
    teach_images: list | None = None,
    blank_sheet: bool = False,
    mode_decision: dict | None = None,  # accepted, no longer injected (§1.1)
    sheet_summary: str = "",
    personal_context: str = "",
    teaching_data: dict | None = None,
    session_plan: str | None = None,
) -> str:
    """User-turn task: code-selected mode + facts; AI realizes the turn.

    The character sheet and personal context ride HERE (per-turn tail of the
    request), not in the system prompt: they change every turn, and any
    changed byte in the system message would break provider prefix-caching
    for the entire chat history behind it. Cost decision, content unchanged.
    """
    mem = session_memory or {}
    mode = mode_decision or {}  # kept for the falsifier arms below only
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
        # The model's OWN session plan (two-phase context, 2026-08-03) —
        # code stores and replays it verbatim, never edits it (§1.1).
        "your_session_plan": session_plan or None,
        "student_character_sheet": {
            "note": (
                "Spanish ABILITIES. Adapt teaching from this; prefer "
                "next_best and active errors over re-probing known can-dos. "
                "Grade ability only via update_character_sheet (reason + "
                "evidence required). FORBIDDEN: never copy or re-emit this "
                "data in the learner reply."
            ),
            "sheet": config.clip_prompt(
                sheet_summary, getattr(config, "SHEET_PROMPT_CHARS", 0)
            ),
        } if sheet_summary else None,
        "learner_personal_context": personal_context or None,
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
    # r9 falsifier arms (docs/design-planner-rounds.md, frozen order;
    # USER-ratified 2026-07-30). Same-content position/structure controls
    # for the lost-in-the-middle hypothesis — NEVER a truncation (§3.3):
    #   legacy        — historical order (sheet buried mid-message)
    #   p1_reorder    — identical keys, constraints LAST (zero token delta)
    #   p2_structured — legacy order + compact structured constraints echo
    #                   pinned to the tail (~200 tokens)
    order = getattr(config, "TEACHER_PROMPT_ORDER", "legacy")
    if order == "p1_reorder":
        tail_keys = ("session_facts", "teaching_data")
        payload = {
            **{k: v for k, v in payload.items() if k not in tail_keys},
            **{k: payload[k] for k in tail_keys if k in payload},
        }
    elif order == "p2_structured":
        payload["FINAL_CONSTRAINTS_check_before_replying"] = {
            "do_not_re_ask_these_frames": mem.get("asked_topics") or [],
            "hard_rules": [
                "no A/B or yes/no English-meaning quiz on known material",
                "never re-ask any do_not_re_ask frame (any person/formality "
                "variant counts as the same ask)",
                "every NEW Spanish item carries its gloss/anchor on the "
                "same line",
            ],
        }
    return (
        "<tutor_turn_task>\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n</tutor_turn_task>\n"
    )
