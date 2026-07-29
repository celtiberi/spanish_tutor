# Conversational Spanish + Learner Character Sheet

**Status:** Direction doc — **plan/realize controller RETIRED** (code deleted 2026-07-28; git history is the archive)  
**Date:** 2026-07-23  
**Authors:** project owner + session synthesis  

---

## 1. Decision: table the pedagogical planner + executor

### What we built

The dual-model path (`--arch controller`):

- **Planner** (e.g. grok-4.5): closed pedagogical decision object  
- **Executor** (e.g. gemini): learner-facing Spanish  
- **Harness:** lesson phases, gates, pack injection, session logs  

Artifacts remain in-repo:

| Area | Location |
|------|----------|
| Protocol | `docs/planner-executor-protocol.md` |
| Experiments | `docs/experiments/exp-002-*.md`, `exp-003-*.md` |
| Code | `tutor/planner.py`, `tutor/pedagogy_controller.py`, `tutor/lesson_flow.py`, `tutor/pack_lookup.py`, `tutor/session_log.py` |
| Run | `python -m tutor.pedagogy_controller session` |

### Why we table it (for now)

Live sessions showed a hard evaluation problem:

> **When the Spanish teaching experience is constrained and lame, we cannot judge whether the “pedagogical layer” is working.**

Observed failure modes (style, not just bugs):

- Stuck on greetings / time-of-day / formal *usted* loops  
- Spelling and accents treated like the main lesson  
- Worksheet voice (“try again with the formal version”) instead of conversation  
- Little sense of “you already know this — let’s go somewhere interesting”  
- Plan/realize added latency and complexity without unlocking *good class feel*

The architecture may still matter later (move selection, training targets, cheap executor). It is **not** the right place to invent what a good Spanish class feels like.

### What “tabled” means

- **Keep** code and docs; do not rip out  
- **Stop** optimizing dual-model gates as the primary product path  
- **Primary focus** shifts to: conversational Spanish experience + rich learner model  
- Return to plan/realize only when we have a **reference teaching style** worth enforcing  

---

## 2. We do not invent Spanish pedagogy

Conversational / example-driven language teaching is a **mature field**. This project should **adopt and operationalize** established approaches — not freestyle “what feels nice in chat.”

### 2.1 Established traditions (steal, don’t reinvent)

| Approach | Core idea | Use for us |
|----------|-----------|------------|
| **Communicative Language Teaching (CLT)** | Language for real communication; meaning first | Default session shape: talk to do something, not to finish a worksheet |
| **Task-Based Language Teaching (TBLT)** | Learn by completing tasks (plan, roleplay, solve) | Character sheet drives *which* micro-task; interaction stays task/conversation shaped |
| **Comprehensible Input (CI)** / Krashen-adjacent practice | Understandable messages slightly above level (*i+1*) | Tutor models rich-but-scaffolded Spanish; sheet estimates level |
| **TPRS / story-based CI** | Story + circling + personalization | Optional mode later: shared story, questions, student in the story |
| **ACTFL / proficiency orientation** | Can-do performance (novice → intermediate…), not pure grammar coverage | Skills on the character sheet map to can-dos; progression = what they can *do* |
| **Focus on form** (Long et al., not “focus on forms only”) | Brief attention to form *inside* meaningful use | Recasts / one-beat explanation mid-conversation — not a conjugation unit hijack |
| **Input → interaction → output** (interaction hypothesis) | Negotiation of meaning builds acquisition | Prefer dialogue over monologue drills |

**Non-goals of “figuring out Spanish teaching”:** inventing a new method, or treating our phase machine / move enums as a substitute for this literature.

**Our job:** encode *known* good practice into prompts, character-sheet fields, and activity selection — then measure against can-dos and engagement, not against home-grown gate quirks.

### 2.2 What that means in product terms

| Literature says | Product does |
|-----------------|--------------|
| Meaning before form | Open with message-bearing Spanish (dialogue, story, real Q) |
| Push output in real use | Roleplay / preference / plan-your-day — not “repeat formal greeting #4” |
| Recycle known language | Sheet marks *known* → stop drilling; keep it as social glue |
| Stretch *i+1* | `next_best` picks one stretch from palette + sheet, not the whole syllabus |
| Form in context | Recast + optional one-line focus-on-form when conceptual error appears |
| Assess performance | Skills/can-dos on sheet; “could they do X with a stranger?” |

### 2.3 What a good Spanish lesson *feels* like

Aligned with CLT/TBLT/CI — not a unit checklist or conjugation app. Closer to:

> Talking with someone who knows you’re learning Spanish, keeps you engaged, and **weaves** what you need into a live conversation — the way trained communicative teachers already work.

### Texture

| Good | Bad |
|------|-----|
| Back-and-forth that could almost be a chat with a bilingual friend | Prompt → grade → same prompt in a new costume |
| Spanish used *as communication* as soon as possible | English lecture with Spanish tokens to repeat |
| Teacher notices you can already greet and **moves on** | 15 minutes on *buenos días* / *usted* spelling |
| New grammar appears when the conversation needs it | Grammar is the conversation |
| Typos/accents fixed lightly in stride | Three retries for *uested* |
| You feel the lesson *going somewhere* | You feel stuck in a skill check |

### Progression (conceptual, not a rigid state machine)

```text
Connect (rapport, what do you want / how was your day)
    ↓
Talk — mostly Spanish when possible, English as scaffold
    ↓
Notice — what they can already do (character sheet updates)
    ↓
Stretch — one new bit (word, pattern, register) that fits *this* talk
    ↓
Use it — same conversation or a tiny role moment
    ↓
Leave a trail — character sheet + light recap, not a test battery
```

Greetings and grammar still matter. The difference is **when** and **how** they enter:

- The teacher **knows** the student needs greetings, present tense, *ser/estar*, etc. (curriculum map).  
- Those targets are **queued in the teacher’s head**, not forced as the only allowed topic.  
- They **drop in** when the chat makes room: a story, a preference, a joke, a plan for the weekend.  
- If the student already greets fine, greetings become **background**, not the grind.

### Adaptation (why we have AIs)

A human tutor constantly answers:

1. What can this person already *do* in Spanish?  
2. What’s the smallest useful stretch right now?  
3. Are they bored / lost / in flow?  
4. Should we stay in Spanish, dip to English, or model once and continue?

An AI tutor should do the same **explicitly**, via a living model of the student — not only via hidden context window vibes.

---

## 3. Curriculum as *palette*, not *railroad*

Keep the course pack (or a lighter syllabus) as:

- **Inventory** of in-scope language  
- **Misconception catalog** (when conceptual errors appear)  
- **Can-do goals** (what “A1 greetings done” means)  

Do **not** treat unit order as “you may not speak until Unit 1 drill 7 is green.”

| Railroad (old feel) | Palette (target feel) |
|---------------------|------------------------|
| Must finish greeting drills before anything else | Greetings are available colors; paint when useful |
| Phase locks that ban production during “input” | Prefer input when introducing, but don’t freeze the chat |
| Success = more variants of the same stem | Success = new conversational territory |

Unit structure can still inform **coverage** (have we ever practiced leave-taking?). It should not dictate **minute-by-minute topic monopoly**.

---

## 4. Student character sheet (learner model)

The missing product piece: a **continuously updated portrait** of the learner that **steers** the lesson.

Working name: **Character sheet** (or learner card). Not a gradebook. A tutor’s mental model made durable.

### 4.1 Design principles

1. **Sheet is context for the AI** — explains abilities so Spanish level and teaching targets fit the student.  
2. **AI keeps the sheet current** — after each exchange: “here’s how that went → update the model of the student.” (Not primarily regex bookkeeping.)  
3. **Confidence-weighted** — one lucky *estoy bien* ≠ mastery.  
4. **Separate surface from concept** — accents/typos ≠ “can’t do present *estar*.”  
5. **Actionable** — `next_best` answers: *so what do we do next?*  
6. **Visible** — `/sheet` for humans; full JSON for the model every turn.  
7. **Portable** — `logs/character_sheet.json` survives sessions.

### 4.1b Can-dos (machine + human)

Operational list: **`docs/spanish-can-dos-novice.md`**  
Code index: **`tutor/can_dos.py`**

Skills on the sheet are **IP/IT/PR can-do ids** (e.g. `IP-03` = introduce myself), not ad-hoc labels. Supporting grammar lives under `grammar` and only supports can-dos (focus on form).

### 4.2 Draft schema (v0)

```json
{
  "identity": {
    "preferred_name": "Patrick",
    "l1": "en",
    "goals": ["travel basics", "order food", "small talk"],
    "engagement_notes": "gets bored on drills; likes real talk"
  },

  "lexicon": {
    "hola": {"status": "known", "confidence": 0.95, "last_seen": "2026-07-23", "contexts": ["greeting"]},
    "buenos días": {"status": "emerging", "confidence": 0.6, "last_seen": "2026-07-23", "notes": "omits accent; meaning clear"},
    "usted": {"status": "fragile", "confidence": 0.4, "notes": "spelling uested; concept of formal you partially there"}
  },

  "grammar": {
    "present_estar_person": {
      "status": "emerging",
      "confidence": 0.55,
      "evidence": ["esta bien → needed estoy", "later estoy bien ok"],
      "priority": "high"
    },
    "register_tu_usted": {
      "status": "fragile",
      "confidence": 0.45,
      "evidence": ["estas with senora"],
      "priority": "medium"
    },
    "present_ser": {"status": "unknown", "confidence": 0.0, "priority": "medium"},
    "gender_articles": {"status": "unknown", "confidence": 0.0, "priority": "low"}
  },

  "skills": {
    "greet_informal": {"status": "known", "confidence": 0.8},
    "greet_formal": {"status": "emerging", "confidence": 0.5},
    "introduce_self": {"status": "unknown", "confidence": 0.0},
    "small_talk_how_are_you": {"status": "emerging", "confidence": 0.6},
    "take_leave": {"status": "unknown", "confidence": 0.0}
  },

  "receptive": {
    "can_follow_short_dialogue": {"status": "emerging", "confidence": 0.5},
    "needs_english_scaffold": true
  },

  "affect": {
    "boredom_risk": "high_on_repetition",
    "last_meta": "asked what we are even doing — signal to change activity"
  },

  "coverage": {
    "touched": ["greetings_time_of_day", "register_tu_usted"],
    "never_touched": ["numbers", "food", "ser_basic", "family"]
  },

  "next_best": {
    "stretch": "introduce_self in same chat after greet",
    "avoid": "another formal greeting costume change",
    "reason": "greet path over-sampled; engagement drop"
  }
}
```

### 4.3 Status vocabulary

| Status | Meaning | Teaching implication |
|--------|---------|----------------------|
| `unknown` | No evidence | Can introduce lightly when relevant |
| `emerging` | Seen once or partial | Recycle in conversation; don’t test to death |
| `fragile` | Works sometimes / mixed | Support + natural reuse |
| `known` | Stable in use | Stop drilling; only maintain in flow |
| `blocked` | Conceptual tangle | Short focused fix, then back to talk |

### 4.4 Update loop — tool call from the teaching AI

```text
1. USE sheet as context → teaching AI replies to the student (normal talk)
2. Same turn, when evidence warrants: tool call update_character_sheet(delta)
3. Harness merges delta (can-do ids, confidence bounds) and persists sheet
4. Next turn starts at (1) with the updated sheet in context
```

The teaching model **decides when** the learner model should change. Skip the
tool on pure social turns with no new signal.

Implementation:

- Tool schema: `UPDATE_CHARACTER_SHEET_TOOL` in `tutor/character_sheet.py`  
- Loop: `tutor/conversational.py` → `tutor_turn()` (text + optional tool)  
- Merge: `apply_delta()` / `process_turn(tool_delta=...)`  
- Rules (`apply_rule_updates`) = **backup** only if the model skips the tool  

Delta guidance (in the tool description + tutor prompt):

- ground changes in **this turn’s evidence**  
- stay conservative on “known”  
- treat surface typos gently  
- set `needs_english_scaffold` from how much English they still need  
- refresh `next_best` when the stretch should change  

### 4.5 How the sheet steers the lesson

| Sheet says | Teacher does |
|------------|--------------|
| `greet_informal: known` | Don’t open with greeting drills; use greetings as social glue only |
| `present_estar_person: fragile` | In “how are you?” chat, model *estoy/estás/está* once if needed |
| `introduce_self: unknown` + chat is going well | Stretch: *Me llamo… ¿Y tú?* |
| `never_touched: food` + student mentions lunch | Pivot into food vocab — in scope |
| `boredom_risk` + same skill 3 turns | Change activity immediately |
| Many `known` at A1 slice | Offer freer talk, stories, preferences — still in inventory |

The sheet is the **adaptation engine**. The curriculum is the **menu of legal stretches**.

---

## 5. Target teaching loop (single model first)

Until conversational quality is real, prefer **one strong tutor model** with:

1. System: conversational tutor stance + syllabus palette  
2. **Character sheet** in context (and persisted)  
3. Each turn: talk (+ optional `update_character_sheet` tool) → persist → next  
4. Logs: transcript + sheet diffs / tool deltas (teaching *and* modeling)

Plan/realize can return later as:

- Optional **critic** that scores turns against sheet-driven goals  
- Or training data generator for pedagogical moves  
- Not the primary mouth of the product

```text
┌──────────────────────────────────────────┐
│  Conversational tutor (single LM)        │
│  - natural Spanish + light English       │
│  - weave targets from character sheet    │
└─────────────────┬────────────────────────┘
                  │ reads / writes
                  ▼
┌──────────────────────────────────────────┐
│  Character sheet (persistent learner)    │
│  lexicon · grammar · skills · affect     │
│  coverage · next_best                    │
└─────────────────┬────────────────────────┘
                  │ constrained by
                  ▼
┌──────────────────────────────────────────┐
│  Syllabus palette (pack / can-dos)       │
│  what may be taught — not the rail order │
└──────────────────────────────────────────┘
```

---

## 6. What “good” looks like in a sample 5 minutes

1. **Open:** “Hey — want to just chat in easy Spanish? We’ll sneak in useful bits.”  
2. **Talk:** How’s your day / plans — Spanish when easy, English bridge when not.  
3. **Notice:** They greet fine; *estoy* needed one recast. Sheet: greet known, estar emerging.  
4. **Stretch:** “By the way — *Me llamo…* how would you introduce yourself to a classmate?” one beat, then back to chat.  
5. **Not:** five formal greeting scenarios after they already produced a good *¿Cómo está usted?*

If the student asks “what are we doing?”: honest answer — “Building small talk you can actually use; you already have X, we’re adding Y.”

---

## 7. Near-term work (when we pick this up)

### Phase A — Spec only (this doc)

- [x] Table plan/realize with rationale  
- [x] Describe lesson feel + character sheet  

### Phase B — Character sheet v0

- [x] Freeze JSON schema + update rules (`tutor/character_sheet.py`)  
- [x] Persist `logs/character_sheet.json`  
- [x] `/sheet` + `/next` + `/reset` on conversational path  
- [x] Hybrid updates: rules each turn + optional `<sheet_delta>` from model  

### Phase C — Conversational tutor path

- [x] Single-model chat: `python -m tutor.conversational`  
- [x] Soft syllabus via pack palette in system; denylist via pack  
- [ ] Evaluation: “would a human say this was a good 10 minutes?” not only gate trajectories  

### Phase D — Revisit plan/realize (optional)

- [ ] Only if we need cheaper/faster mouth or train pedagogical control  
- [ ] Judge against **character-sheet goals**, not only 13 mechanical trajectories  

---

## 8. Explicit non-goals (for this direction)

- Perfect CEFR placement testing before talking  
- Zero English (scaffold is fine)  
- Never teaching grammar (weave it; don’t worship it)  
- Proving dual-model superiority before conversational quality exists  

---

## 9. One-line summary

**Stop optimizing a pedagogical middleware on top of a boring Spanish class.**  
**First build a class that feels like adaptive conversation — powered by a living character sheet of what the student can do — and only then ask whether a separate planner improves that.**

---

## Document history

| Version | Date | Notes |
|---------|------|--------|
| 0.1 | 2026-07-23 | Table plan/realize; conversational feel; character sheet draft; next phases |
