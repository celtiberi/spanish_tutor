# Character sheet deep dive

**Status:** living product architecture note  
**Date:** 2026-07-24  
**Audience:** design + implementation for teaching *and* gamification  

The character sheet is not a report card the student studies. It is the **teacher’s working model of the learner** — and, soon, the **event bus for celebration, levels, comparison, and progression UX**.

If the sheet is wrong, teaching drifts and gamification lies.  
If the sheet is honest and rich, both teaching and game loops get free structure.

---

## 1. What it is (and is not)

### Is

| Role | Meaning |
|------|---------|
| **Memory** | Durable across sessions (today: `logs/character_sheet.json`) |
| **Steering** | Injected into the tutor system prompt every turn |
| **Adaptation engine** | `next_best`, scaffold, avoid, affect |
| **Evidence log** | Sparse traces of what they actually did |
| **Future game state** | Level, XP, streaks, unlocks, social rank — *derived from* this model |

### Is not

- A unit checklist the student must complete in order  
- A full grammar grammarbook  
- Hidden model “vibes” only in the context window  
- A leaderboard identity (game layer projects outward; sheet stays pedagogical truth)

**Principle:** one truth model → many surfaces (tutor, focus rail, morph rail, XP, sounds).

```text
                    ┌─────────────────────────┐
                    │   CHARACTER SHEET        │
                    │   (learner model v2+)    │
                    └───────────┬─────────────┘
           ┌────────────────────┼────────────────────┐
           ▼                    ▼                    ▼
     Teaching AI            Focus/morph          Game layer
     (level, scaffold,      rail (FOCUS_MODEL)   (XP, level badge,
      next_best, avoid)                          streaks, SFX, peers)
```

---

## 2. Schema anatomy (v2 today)

```text
version, framework
identity          who they are (name, L1, goals)
skills            ACTFL-oriented can-dos (IP/IT/PR)  ← primary progress
grammar           supporting forms (focus-on-form only)
lexicon           sparse lemmas they’ve used
receptive         scaffold need, Spanish streak
affect            boredom, energy, last meta
coverage          topics touched / never_touched
next_best         one stretch + avoid + reason
updated_at
```

### 2.1 Status vocabulary (shared by skills / grammar / lexicon)

| Status | Pedagogical meaning | Game translation (future) |
|--------|---------------------|---------------------------|
| `unknown` | No evidence | Locked / fog |
| `emerging` | Seen once or partial | Unlocked, low mastery bar |
| `fragile` | Works sometimes | Unstable — needs support, not XP spam |
| `known` | Stable in use | Mastered — stop drilling; maintenance XP only |
| `blocked` | Conceptual tangle | Boss fight / short form-focus quest |

Honesty knobs in harness (post tool-delta):

- Max **+0.25 / −0.35** confidence per turn  
- `known` requires **≥2 solid_uses** and conf ≥ 0.80  
- `preferred_name` never wiped once set  
- Limited time ≠ boredom  

### 2.2 Skills = can-dos (the real “levels”)

Source: `docs/spanish-can-dos-novice.md` + `tutor/can_dos.py`.

| Id | Mode | Role in product |
|----|------|-----------------|
| IP-01…IP-08 | interpersonal | Live chat progress (primary) |
| IT-01, IT-02 | interpretive | Under-instrumented today |
| PR-01 | presentational | Under-instrumented today |

Each skill entry (ideal):

```json
{
  "status": "emerging",
  "confidence": 0.5,
  "solid_uses": 2,
  "statement": "I can …",
  "mode": "interpersonal",
  "band": "NL-NM",
  "evidence": ["short quote or paraphrase"],
  "last_seen": "YYYY-MM-DD",
  "priority": "high|medium|low"
}
```

**Progress = what they can *do***, not how many greetings they conjugated.

### 2.3 Grammar = supporting forms

Not the goal. Supports can-dos (`supports: ["IP-04"]`).  
Morphology rail and focus-on-form recasts hang off this layer.

### 2.4 next_best = teacher’s next move

```json
{
  "can_do": "IP-05",
  "activity": "close_exchange_naturally",
  "stretch": "…",
  "statement": "I can end a short exchange politely.",
  "avoid": "return_to_greetings…",
  "reason": "…",
  "method": "CLT/TBLT + CI + focus_on_form"
}
```

Recompute path (rules): weakest open interpersonal can-do, boredom → change activity, limited time → shorten.  
AI tool path: may set `next_best` explicitly; harness preserves well-formed proposals.

### 2.5 receptive + affect

| Field | Teaching use | Game use |
|-------|--------------|----------|
| `needs_english_scaffold` | EN+ES vs more ES | Difficulty mode / comfort badge |
| `spanish_turn_streak` | Ease scaffold off | Streak counter (with care) |
| `boredom_risk` | Change task | Anti-grind trigger |
| `energy` | Session length | “Quick session” mode |
| `last_meta` | Human notes | Debug / support, not leaderboard |

---

## 3. How data flows (implementation)

### 3.1 Read path (every turn)

```text
load sheet
  → format_sheet_for_prompt(sheet) into system
  → harness: next_best + scaffold line
  → tutor generates learner-facing reply
```

Files: `tutor/conv_session.py`, `prompts/conversational_tutor.md`.

### 3.2 Write path (when evidence moves)

```text
tutor may call update_character_sheet(delta)
  → apply_delta (sanitize, clamp conf, known-gate, name sticky, coverage auto-touch)
  → process_turn
  → save logs/character_sheet.json
  → optional FOCUS_MODEL enrich for side rail (not sheet truth)
```

Backup if no tool: `apply_rule_updates` (regex heuristics).

### 3.3 Surfaces that consume the sheet

| Surface | What it uses |
|---------|----------------|
| Tutor model | Full slim sheet + next_best |
| Web Focus card | `next_best` + skill status + affect |
| Morphology card | can-do → form hooks + static paradigms + cheap Grok blurb |
| CLI `/sheet` | Human dump |
| Session logs | skills snapshot + notes + tool_delta |

**Important split:**  
FOCUS_MODEL personalizes *presentation*. It must **not** become the source of truth for scores.

---

## 4. Live audit (Patrick sheet, 2026-07-24)

Snapshot of `logs/character_sheet.json` after real sessions:

### Strengths

- **Name sticky:** Patrick  
- **Honest new climb:** IP-05 emerging 0.50 (solid_uses=2), IP-06 emerging 0.65 (solid_uses=3)  
- **Coverage moving:** food, preferences, leave_taking, etc.  
- **Lexicon starting:** estoy, me_gusta, prefiero, tomar…  
- **next_best coherent:** IP-05 leave-taking while greets look solid  

### Integrity problems (must fix for gamification)

| Issue | Detail | Risk if gamed |
|-------|--------|----------------|
| **Legacy `known` without solid_uses** | IP-01…04, IP-08 known pre-gate | Fake “level complete” fireworks |
| **IP-04 conf 1.0** | Evidence: *estoy bien* | Over-celebration |
| **Coverage lag** | `register_tu_usted`, `roleplay_tasks` still never_touched after marina RP | Wrong map of “world unlocked” |
| **IT/PR empty** | No interpretive/presentational tracking | No multi-mode progression |
| **Scaffold stuck true** | `spanish_turn_streak: 0` | Difficulty never eases |
| **Evidence sparse** | Few quotes per skill | Hard to recompute honesty later |
| **Single global sheet file** | One learner on disk | Blocks multiplayer / peers |

**Rule for product:** do not emit mastery SFX / “Level up!” until harness honesty would still call it `known` under post-gate rules (or a migration recalibrates legacy knowns).

---

## 5. What a great teacher needs from the sheet

A human tutor constantly answers four questions. Map them:

| Tutor question | Sheet field(s) | Gap today |
|----------------|----------------|-----------|
| What can they **do**? | `skills` statuses | IT/PR weak; known overstated |
| What’s the **smallest useful stretch**? | `next_best` | Sometimes greets/farewells too early in session |
| Are they **bored / tired / short on time**? | `affect` | Limited-time fixed; boredom ok |
| EN or ES? | `receptive` | Streak rarely rises |
| What **words/forms** to weave? | lexicon + grammar | Thin lexicon; no frequency/decay |
| What **not** to drill? | status=known + avoid | Legacy knowns pollute |
| What’s their **story**? | identity, goals, engagement | goals empty; no interests graph |

### Missing dimensions for “great teacher memory”

1. **Interests / persona graph** — boat, Río Dulce, coffee, marina (durable hooks)  
2. **Session history summary** — last 3 sessions in 5 bullets  
3. **Error patterns** — `me llamo es`, *tango*/*tengo*, gender on *pizza* (not one-off evidence)  
4. **Recency / decay** — known that isn’t used for 14 days → fragile  
5. **Mode balance** — force occasional IT input if only IP production  
6. **Multi-learner identity** — user_id → sheet path  
7. **Provenance** — each delta: tool | rules | teacher_override | eval  

---

## 6. Gamification: derive from the sheet, don’t invent a second economy

### 6.1 Core idea

```text
Pedagogical events (sheet deltas)
        ↓
  Game event projector
        ↓
 XP / level / streaks / unlocks / peer rank / SFX triggers
```

The projector is **deterministic** and testable. The AI does not award XP ad hoc.

### 6.2 Proposed derived game fields (v3 sheet or sibling `game_state`)

Keep pedagogical truth clean; either nest `progression` on the sheet or store `logs/game_state.json` keyed the same way.

```json
{
  "progression": {
    "band_label": "Novice Mid — Interpersonal",
    "level": 4,
    "xp": 1280,
    "xp_to_next": 400,
    "streak_days": 3,
    "session_minutes_total": 47,
    "can_do_mastered": ["IP-01"],
    "can_do_in_progress": ["IP-05", "IP-06"],
    "titles": ["Harbor greeter"],
    "last_celebration": null
  }
}
```

### 6.3 XP event catalog (examples)

| Event | Source signal | XP | SFX / anim |
|-------|---------------|-----|------------|
| First solid use of a can-do | solid_uses 0→1 | small | soft chime |
| Status → emerging | harness | medium | unlock pulse on skill card |
| Status → known (gated) | solid_uses≥2 + conf | large | level-up / confetti |
| Successful recast uptake | said form correctly after model | medium | spark |
| Completed micro-task (IP-08 beat) | tool evidence | large | quest complete |
| Stretch without English meta | spanish_turn_streak++ | small | flame streak |
| Boredom recovery | affect high→low + new domain | medium | scene change |
| **No XP** | pure English glossary ask | 0 | none |
| **No XP** | same known skill drilled | 0 or tiny maintenance | none |

**Anti-farming:** cap XP per can-do per day; no XP for tool spam without learner text; decaying returns on known skills.

### 6.4 Level design (pedagogy-aligned)

Levels should track **band × can-do mass**, not raw chat turns:

```text
Level ≈ f(
  sum conf(skills interpersonal),
  count known can-dos,
  coverage breadth,
  recent active days
)
```

Display to learner as:

- “You can greet, introduce yourself, and hold a short marina check-in.”  
- Not “Level 12 Grammar Wizard.”

### 6.5 Peer comparison (careful)

Compare **anonymized can-do profiles**, not raw XP:

- “Learners like you usually unlock preferences next”  
- Percentile on **active days** or **can-dos known**, with opt-in  
- Never shame scaffold need or L1  

Data requirement: multi-user store + privacy.

### 6.6 Sounds & animations (trigger map)

| Trigger | UI |
|---------|-----|
| `celebration: can_do_known` | skill card gold + short sting |
| `celebration: first_name_saved` | welcome badge |
| `celebration: streak_3` | streak flame |
| `signal: boredom` | soft UI color shift; tutor already changes task |
| `signal: limited_time` | compact session chrome |
| `morph highlight` | morphology row pulse when they produce the form |

All triggers emitted by projector reading **before/after sheet** on each turn.

---

## 7. Target architecture (v3)

### 7.1 Split concerns

| Layer | Owner | Mutates sheet? |
|-------|-------|----------------|
| Teaching AI tool delta | Tutor model | Yes (clamped) |
| Rules backup | Harness | Yes |
| Honesty / gates | Harness | Yes (always) |
| next_best recompute | Harness or AI | Yes |
| Focus/morph copy | FOCUS_MODEL | **No** (view only) |
| Game projector | Deterministic code | Writes `progression` only |
| Teacher override UI | Human | Yes, audited |

### 7.2 Suggested schema additions

```text
identity.interests[]          # {topic, strength, last_seen}
skills.*.solid_uses           # required for all (migrate defaults)
skills.*.evidence[]           # ring buffer max 5
skills.*.last_reward_at       # anti-farm
error_patterns[]              # {pattern_id, count, last_example}
sessions_summary[]            # last N {date, minutes, highlights}
progression { ... }           # game projection
meta.user_id, meta.locale
```

### 7.3 Migration: honesty pass on load

On `load_sheet`:

1. Ensure every skill has `solid_uses` (default 0).  
2. If `status==known` and `solid_uses < 2`, demote to `emerging` and cap conf at 0.75 **unless** `legacy_trusted=true` after human review.  
3. Recompute coverage from skills/grammar evidence.  
4. Bump `version` to 3 when progression block present.

### 7.4 Multiplayer / peers

- One sheet per `user_id`  
- Optional aggregate: distribution of conf per can-do for “learners at your stage”  
- No PII in aggregates  

---

## 8. Product principles (lock these in)

1. **One learner model.** Game and teaching read the same skills.  
2. **Celebrate only gated mastery.** Fireworks follow harness truth.  
3. **Can-dos over conjugations** for level labels.  
4. **Affect is for care, not for shaming.**  
5. **Cheap models decorate; they don’t score.**  
6. **Evidence > vibes.** Prefer short quotes in `evidence[]`.  
7. **Decay is honest.** Unused “known” softens.  
8. **Opt-in social.** Comparison is invitation, not pressure.  

---

## 9. Near-term roadmap (ordered)

| # | Work | Why |
|---|------|-----|
| 1 | **Honesty migration** on load for legacy knowns | Unblocks safe celebrations |
| 2 | **Event projector** (before/after sheet → XP events) | Gamification spine |
| 3 | **progression block** + web level chip | Visible progress |
| 4 | **interests / error_patterns** | Better teaching + quest flavor |
| 5 | **SFX hooks** in web on celebration events | Feel |
| 6 | **user_id sheets** | Real multiplayer prep |
| 7 | **Peer aggregates** (opt-in) | Social |
| 8 | Revisit plan/realize as *critic* of sheet-driven teaching | Quality control |

---

## 10. Code map

| Concern | Location |
|---------|----------|
| Schema default / load / save | `tutor/character_sheet.py` |
| Can-do inventory | `tutor/can_dos.py`, `docs/spanish-can-dos-novice.md` |
| Tool merge + gates | `apply_delta`, `process_turn` |
| Session loop | `tutor/conv_session.py` |
| Focus rail static | `build_focus_panel` |
| Focus rail AI | `tutor/focus_enrich.py` (`FOCUS_MODEL`) |
| Web surface | `tutor/web_static/*`, `tutor/web_app.py` |
| Direction | `docs/conversational-spanish-and-learner-model.md` |

---

## 11. Bottom line

The character sheet is already the right **concept**:

> Living, can-do-oriented memory that steers conversation.

It is not yet a complete **product platform**:

- Honesty still polluted by pre-gate knowns  
- Thin interests / errors / decay  
- No first-class progression or celebration events  
- Single-file identity  

**Investment order:**  
**truth → events → game chrome → social.**  

Not the reverse. Gamifying a soft sheet produces a casino, not a good Spanish class.

When those layers are clean, the same sheet that tells the tutor “stretch leave-taking, keep EN+ES” also tells the UI “soft chime, IP-05 bar to 50%, streak +1” — without a second brain inventing scores.
