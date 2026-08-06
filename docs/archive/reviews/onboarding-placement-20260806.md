# Design round: blank-sheet onboarding + placement arc (2026-08-06)

USER: "When the character sheet is blank we just have the teacher open
with a hello question. I feel like the teacher should explain herself a
little (what am I and how does this all work). Then I think the teacher
should give a quick assessment test so the student can be properly
leveled."

## Proposal (Claude, round 1 — for countersign)

### Diagnosis

1. Blank-sheet opens today: warm greeting + one elicit, placement by
   drift. New users get zero orientation (real confusion incidents on
   record: "am I supposed to respond to 'Your turn' or 'next'?").
2. Leveling is assume-beginner-repair-later: sofia-class learners get
   a beginner plan and fix it via <replan/> at turn 1-4. Placement
   inverts this: level first, plan second.

### Design

**Beat 0 — orientation (one message, mostly English, TTS-friendly):**
who the tutor is; you can speak or type; mistakes are welcome and
gently recast; the side panels show verb forms and your progress; we
start with a couple of quick questions "so I can see where to start".
Persona voice, 4-6 short sentences, no feature tour spam.

**Beats 1..N — adaptive mini-placement (N ≤ 5, target 2-4 minutes):**
1. Self-report (English): studied before / understand some / speak some?
2. Comprehension probe (gist of one easy line).
3. Recognition (¿qué significa X? on high-frequency item).
4. Short production ("how do you say…", or answer in Spanish).
5. Stretch only while succeeding (translate a sentence / 2-sentence
   self-intro). STOP on first clear level signal; true zero stops at
   beat 1-2 with warm "perfect, we start from the beginning".
Escalate-until-failure, §2.8 inverted for placement: failures here are
LEVEL DATA, not struggle to repair — but never more than one failed
beat before settling (placement must feel like curiosity, not exam).

**Landing:** grades recorded per beat (band anchors as usual, sections
per evidence), then the teacher writes the real leveled plan (<plan>
revision or <replan/>) and teaching starts at altitude.

### Placement in the architecture

- Lives in the BLANK CACHED PLAN (plan_cache): the precomputed blank
  plan's ARC becomes orientation → placement ladder → level-and-replan.
  One implementation site; instant for every new learner; the plan
  fingerprint already invalidates on any change.
- PLAN_INSTRUCTIONS gains a blank-sheet paragraph (the plan turn for a
  blank sheet must write this arc); stance's "Diagnostic / feel-out"
  section is REWRITTEN to the orientation+placement contract (the old
  one-elicit feel-out dies — superseded, not weakened: its anti-
  worksheet bans carry forward).
- Uses the r6 assessment-move menu (no new machinery); grading via the
  normal tool; sofia-class replans should DROP (measure in gate).

### Risks for the round

1. Does a placement ladder resurrect the banned flashcard-ladder
   energy? (The 2026-07-28 incident class — scripted probe sequences.)
   Mitigation: model-led beats in persona voice, menu moves, hard cap
   N≤5, stop-on-signal. Where exactly is the line?
2. Orientation length/tone: TTS reads it; how short is short enough?
   English-heavy opening vs CI-first laws (true-zero exception already
   sanctions English orientation).
3. Test anxiety at first contact (affect P6): is "quick questions so I
   can see where to start" framing sufficient? Alternatives?
4. Self-report validity: how much should the ladder trust it (skip
   beats?) vs verify?
5. Should placement grades be marked provisional (placement evidence ≠
   conversational evidence), or are band anchors enough?
6. Returning-user interaction: sheet non-blank → no orientation, no
   placement (restored plan path unchanged) — any edge cases (reset)?


---

## GROK (Grok Build CLI (1e1687c1cf6a)) - 2026-08-06 17:57 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the inlined proposal materials, then independently research adult L2 placement practice before ruling item-by-item.Continuing through the full prompt and gathering placement-research evidence for the risk rulings.Gathering placement research and the project's stance/PLAN text so the rulings can be precise.I have enough primary-source placement evidence and project law text for a kill-search countersign. Writing the append-ready ruling next.# Grok countersign — blank-sheet onboarding + placement arc  
**Date:** 2026-08-06  
**Role:** independent second author (do not treat Claude’s proposal as authority)  
**Subject:** `docs/archive/reviews/onboarding-placement-20260806.md` vs stance (`prompts/conversational_tutor.md` Diagnostic) + PEDAGOGY §2 / ENGINEERING §1.1 / §3.2  
**Protocol:** VERDICT-LAST · 4-way rulings · kill-search

---

## 1. Independent evidence (dated 2026-08-06)

### Placement practice (adult L2 / apps)
- **Adaptive stop, not fixed length.** Computer-adaptive language placement shortens measurement by adjusting difficulty and terminating on precision / max-items / clear level signal (CAT termination criteria: SEM threshold, max items, time). Multi-stage designs avoid punishing one miss with an immediate full demotion; cluster-level adaptation is more stable than pure item-by-item drop.
- **Industry pattern (Duolingo-class):** prior-proficiency self-report (few fixed options) **plus** optional adaptive placement quiz; placement is used to skip content, not to mint mastery. User reports that easy placement → over-skip → lost first lessons are a known product failure mode — under-place then climb is safer than over-place then flounder.
- **Self-report validity (arithmetic, not vibes):**
  - Ross (1998) meta: mean *r* ≈ **0.63** self-assessment ↔ external L2 measures → *r*² ≈ **0.63² = 0.3969 ≈ 40%** shared variance.
  - Li & Zhang (2021) meta: mean *r* ≈ **0.45** overall, speaking ≈ **0.44** → *r*² ≈ **0.45² = 0.2025 ≈ 20%** shared variance; computer-adaptive SA rises only to *r* ≈ **0.52** → *r*² ≈ **0.27**.
  - Winke, Zhang & Pierce (2022/2023, SSLA): adaptive can-do self-assessment vs ACTFL OPIc, polyserial *r* ≈ **0.61** → *r*² ≈ **0.37**; authors still frame SA as **low-stakes**, not a substitute for performance when decisions are consequential.
  - **Ruling arithmetic:** best-case ~**37–40%** shared variance ⇒ self-report may **route** the next probe, never **conclude** level alone. Skipping all performance beats on “I speak some” is unjustified.

### First-session onboarding / retention
- Cross-app Day-1 retention often ~**21–26%**; **70–80%** of installs gone within ~3 days; bulk of loss is first session. Onboarding that compresses time-to-first-value and avoids feature tours retains better than long chrome tours.
- Duolingo-pattern product writing: do-first (tiny language action) + optional personalization **before** account/tour spam; long “what every panel does” copy is anti-pattern.
- Implication for Beat 0: orientation is real and valuable for confusion (“Your turn / next”), but **short, purpose-framed, then a language beat** — not a feature manual.

### Project founding trauma (law, not proposal text)
- ENGINEERING §1.1: 2026-07-28 hard-coded curriculum produced **flashcard ladders, repeated probes**, tutor that “could not adapt” — wrong tool was scripting the teacher.
- Stance ban (verbatim class): “Fixed flashcard ladder (Hola card → Estoy card → Me llamo card) — you choose the next move; never run a costume sequence.”
- §2.4 density: ≤1 assessment beat per 3 teaching turns (teaching regime).
- §2.8: fail → raise support / bank success (teaching regime).
- §3.2: introduction ≠ knowledge; band moves on **production evidence**, not exposure; one good turn is not mastery.
- §1.1a Direction-not-scripts: goals/constraints/inventory OK; **not** tutor dialogue lines or fixed costume sequences.

---

## 2. Kill-search (Risk 1 — attacked hardest)

**Claim under kill:**  
“A blank-sheet ARC of orientation → ordered beats 1–5 (self-report → comp → recognition → production → stretch) is categorically distinct from the banned flashcard ladder, so the design is safe as written.”

### Precise line: placement ladder vs probe/flashcard ladder

| Axis | **Banned flashcard / probe ladder (2026-07-28 class)** | **Legal placement ladder (if and only if)** |
|------|--------------------------------------------------------|-----------------------------------------------|
| **Purpose** | Teach / costume forms through a fixed script | **Measure altitude once**, then stop measuring |
| **Authorship** | Code or pack owned the sequence (“always the same text”) | **Model** chooses items and next evidence type under constraints |
| **Stop rule** | None — run the costume (Hola → Estoy → Me llamo) | **Hard stop:** first clear level signal **or** first clear fail after a success streak; true-zero stop by beat 1–2; **N ≤ 5**; never grind past signal |
| **Failure meaning** | Struggle to repair under §2.8 (re-model, smaller ask, bank success) | **Level data only** — settle altitude; **do not** open contingent-support loops mid-placement |
| **Item identity** | Fixed Spanish costumes / same probes re-asked | Fresh items from r6 **menu moves**; never re-ask answered probes; no A/B English-meaning chrome |
| **Density law** | §2.4 1-per-3 applies to **teaching** assessment | Placement window is a **named regime exception** (must be stated); after landing, §2.4 density returns |
| **Grade effect** | Treats drill success as ability | Placement evidence is **provisional / altitude-only** until conversational production confirms (ENGINEERING §3.2) |

**Falsifier that would have killed the whole design:**  
If the blank plan **hard-scripts** a mandatory five-beat costume of specific Spanish items with no early exit, re-elicits after answers, grades `known` from one recognition hit, and continues past a clear zero or clear multi-skill signal “because N=5” — that **is** the 2026-07-28 ladder wearing a placement hat → **REJECT_WHOLE**.

**What survives the kill:** purpose + stop rule + model authorship + menu moves + N≤5 + single-fail settle **do** separate placement from flashcard energy — **but only if the proposal’s “Beats 1..N” language is rewritten as ordered evidence *types* with early exit, not a fixed script the plan must recite.** As written, Claude’s numbered 1–5 list is **dangerously close** to costume sequence. That claim is **killed**; the design is **amended**, not blessed.

**Kill-search explicit (required):**  
Tried hardest to kill **“placement ladder ≠ flashcard ladder.”**  
**Result:** NOT killed as a category; **killed as written** without the stop/authorship/provisional amendments below.  
**Falsifier used:** fixed ordered costume + no stop + teaching-grade inflation.

---

## 3. Risks 2–6 (evidence + rulings)

### Risk 2 — Orientation length / TTS / English vs CI
- TTS arithmetic (rule of thumb ~2.5 words/s casual TTS):  
  - **80 words** ≈ **80 / 2.5 = 32 s**  
  - **120 words** ≈ **48 s**  
  - **150 words** ≈ **60 s** (feature-tour territory; bad Day-1)
- Proposal “4–6 short sentences” is directionally right **iff** total **≤ ~80 words** and **≤ 2 side-panel mentions** (not a chrome tour).
- English-heavy open: **already sanctioned** by stance true-zero exception + P6/P1 orientation scaffold. Not a CI violation **for blank-sheet first message only**. Long all-English walls remain banned.
- **Ruling:** **ACCEPT_WITH_AMENDS** — hard word cap; no “test/exam”; panels mentioned in one clause max.

### Risk 3 — Test anxiety (P6)
- USER said “assessment test”; proposal softens to “quick questions so I can see where to start” — better.
- Affect literature (project P6): anxiety lowers WTC; first contact is high-stakes emotionally even if low-stakes pedagogically.
- Framing alternatives (stronger → weaker exam energy):  
  1. “a couple of questions so I know where to start” (preferred)  
  2. “help me pitch this right”  
  3. Avoid: test / quiz / assessment / level exam
- One failed beat then warm settle (“perfect — we start from here”) is the affect win, not cheerleading mid-fail.
- **Ruling:** **ACCEPT_WITH_AMENDS** — ban the words *test/quiz/exam* in learner-facing placement; curiosity framing only.

### Risk 4 — Self-report trust
- Arithmetic above: **~20–40%** variance shared with external proficiency → **route, never conclude**.
- Allowed: “never studied / nothing” → stay at floor, optional one ultra-easy confirm, settle fast.  
  “some / speak a bit” → start mid ladder, still **must** take ≥1 performance probe before altitude.
- **Forbidden:** skip all of beats 2–4 solely on self-report.
- **Ruling:** **REJECT_CLAIM** that ladder may “trust self-report enough to skip beats” without a performance floor. Soft-routing only.

### Risk 5 — Provisional grades
- §3.2 + stance: one good turn ≠ mastery; honest bands; garbled stays non-evidence.
- Placement is **decontextualized / high-pressure / first-contact** — not conversational can-do evidence under varied frames.
- Band anchors alone are **not** enough if the tool path treats placement hits like mid-session production.
- **Ruling:** **ACCEPT_WITH_AMENDS** — placement grades **must** be marked provisional (or capped: recognition/comp → at most `emerging`; production stretch → at most `fragile` until a later conversational confirm). Never `known` from placement alone.

### Risk 6 — Returning users / reset
- Non-blank sheet → no orientation, no placement: **correct** (restored plan path).
- Edge cases that **must** re-enter placement:
  1. Explicit **reset sheet** / “start over”  
  2. Sheet load that is **ability-empty** (all can-dos unknown **and** no production history) even if session id exists  
  3. Fingerprint: gate on **`is_blank_learner(sheet)`**, not “first session of this browser”
- Do **not** re-place a returning learner with sparse-but-real evidence just because plan cache is cold.
- **Ruling:** **ACCEPT_WITH_AMENDS** — document blank predicate + reset path.

---

## 4. Exact replacement text (ship these)

### 4A — Stance: replace entire `### Diagnostic / feel-out (blank character sheet)` section  
Also update the table row for blank sheet to match.

```markdown
### Orientation + placement (blank character sheet)

If the sheet is ability-empty (all can-dos unknown, no production/error
history — the blank-learner predicate) you are **orienting then placing**,
not teaching a costume sequence. You do not yet know if they are true-zero
or already multi-skill.

**Beat 0 — orientation (exactly one opening message):**
- Persona voice; **mostly English**; TTS-friendly.
- Cover only: who you are; speak or type is fine; mistakes are welcome and
  gently recast; side panels show forms/progress **in one short clause**;
  you will ask a couple of questions **so you know where to start**.
- Hard caps: **≤ 6 short sentences AND ≤ 80 words**. No feature tour.
  Never say test / quiz / exam / assessment.
- End Beat 0 by inviting the first placement question (or one easy Spanish
  hello + the first question woven in). Do not monologue in Spanish.

**Placement window (after Beat 0, until settle):**
Purpose = measure altitude. Failures here are **level data**, not §2.8
struggle-to-repair. Contingent-support loops, bank-a-success detours, and
the §2.4 “≤1 assessment beat per 3 teaching turns” density cap are
**suspended only inside this window**. The moment you settle altitude and
start teaching, §2.4 and §2.8 apply in full.

You choose each next move from the assessment-move menu (and ordinary
chat), in your voice. Evidence **types** (not a fixed costume of Spanish
items), in rough difficulty order — **skip, reorder, or stop early** when
the signal is clear:

1. Self-report (English): studied before / understand some / speak some?
   Routes the next probe only — never concludes level alone.
2. Comprehension: gist of one easy line.
3. Recognition: «¿qué significa X?» on a high-frequency item (effortful
   recall — not A/B English-meaning chrome).
4. Short production: “how do you say…?” or a real Spanish answer.
5. Stretch only while succeeding: one sentence translate or 2-sentence
   self-intro.

**Hard stop rules (non-negotiable):**
- True-zero / no Spanish after self-report + one easy probe → warm settle
  (“perfect — we start from the beginning”) by beat 1–2.
- First **clear multi-skill production** → skip remaining ladder; chat
  forward at altitude.
- First **clear fail after at least one success** → settle (at most one
  failed beat before landing). Do not grind.
- Hard cap: **N ≤ 5 placement beats** after orientation (target ~2–4 min).
- Never re-ask a probe they already answered.
- Never run a fixed flashcard costume (Hola card → Estoy card → Me llamo
  card). The banned ladder is a **fixed item sequence with no stop rule
  during teaching**. This window is adaptive measurement with a stop rule.

**Landing:**
- Write/revise the real leveled plan (`<plan>` or `<replan/>`) and begin
  teaching at altitude.
- Grade via the normal tool, but treat placement evidence as **provisional
  altitude**: recognition/comp alone → at most `emerging`; a strong
  production stretch → at most `fragile`. Never mark `known` from
  placement alone. Conversational evidence later confirms or revises.

**Do not (anti-worksheet — carried forward):**
- Pure Spanish monologue walls with no clear try
- English dual-subtitle every line (*X = Y* walls)
- “Say: **Hola**” / “Di: Me llamo + name” worksheet energy
- Fake rapport as if you already know them
- Re-ask *¿Cómo estás?* / *¿Cómo te llamas?* after they answered
- A/B or yes/no ENGLISH-MEANING quizzes on material as assessment chrome
- Fixed flashcard ladder / costume sequence
- Bare praise with no teach content after landing
- Calling the placement window a test/quiz/exam to the learner
```

**Table row replacement** (What teaching looks like):

```markdown
| **Blank sheet / unknown learner** | **Orientation + placement** — one short English orientation, then adaptive mini-placement (stop on signal); not intermediate monologue, not a fixed flashcard costume |
```

### 4B — `PLAN_INSTRUCTIONS` blank-sheet paragraph  
Append **after** the existing `</plan>` instructions block (before “Write real content…”), exact text:

```text
BLANK SHEET (ability-empty learner only): your ARC must be
orientation → adaptive mini-placement → level-and-replan → first teach
beats. Orientation is one short English open (≤80 words; no test/quiz/
exam language; no feature tour). Placement uses assessment-move menu
evidence types (self-report routes only; then comprehension / recognition /
production / stretch as needed), model-chosen items, hard stop on first
clear level signal or after one failed beat, true-zero settle by beat 1–2,
N ≤ 5 placement beats. Placement failures are level data — do not open
§2.8 repair loops or bank-success detours until after landing. After
settle, emit a revised <plan> at the demonstrated altitude and teach.
Placement grades are provisional altitude (never `known` from placement
alone). This is NOT a fixed flashcard costume (Hola → Estoy → Me llamo)
and NOT a code-scripted probe sequence — you author every item and you
stop early. Non-blank sheets: never run orientation/placement; plan from
evidence as usual.
```

---

## 5. Per-item rulings (proposal structure)

| # | Item | Ruling | Why (short) |
|---|------|--------|-------------|
| D1 | Diagnosis: blank open = greet+one elicit; zero orientation | **ACCEPT_AS_WRITTEN** | Matches stance today; confusion incidents are in-project class. |
| D2 | Leveling = assume-beginner + replan; placement inverts | **ACCEPT_AS_WRITTEN** | Serves P7; sofia-class replan cost is a measurable gate, not vibes. |
| Des0 | Beat 0 orientation | **ACCEPT_WITH_AMENDS** | Ship 4A caps (≤80 words; no exam words; panels one clause). |
| Des1–5 | Adaptive mini-placement ladder | **ACCEPT_WITH_AMENDS** | Evidence **types** + hard stop; reject fixed 1–5 costume reading (Risk 1 kill). |
| Des-land | Grades then replan | **ACCEPT_WITH_AMENDS** | Provisional altitude grades (Risk 5); then real plan. |
| Arch1 | Blank cached plan ARC | **ACCEPT_AS_WRITTEN** | One site; fingerprint invalidation already fits ENGINEERING plan_cache. |
| Arch2 | PLAN_INSTRUCTIONS + stance rewrite | **ACCEPT_WITH_AMENDS** | Only with exact 4A + 4B (not Claude’s paraphrase alone). |
| Arch3 | r6 menu; no new machinery; sofia-replans drop | **ACCEPT_AS_WRITTEN** | Gate metric required: count early `<replan/>` on blank starts before/after. |
| R1 | Flashcard-ladder resurrection | **REJECT_CLAIM** as “safe as numbered” / **ACCEPT_WITH_AMENDS** design | Line is stop+authorship+purpose; numbered beats alone fail the line. |
| R2 | Orientation length/CI | **ACCEPT_WITH_AMENDS** | 80-word / ~32 s TTS budget. |
| R3 | Test anxiety framing | **ACCEPT_WITH_AMENDS** | Ban test/quiz/exam learner-facing. |
| R4 | Self-report skip | **REJECT_CLAIM** (skip-on-SA) | *r*² ≈ 0.20–0.40 ⇒ route only. |
| R5 | Band anchors enough | **REJECT_CLAIM** | Provisional / band-cap required under §3.2. |
| R6 | Returning-user path | **ACCEPT_WITH_AMENDS** | Blank predicate + explicit reset only. |

---

## 6. What must not ship (even if rest ships)

1. Hard-coded Spanish costume sequence in blank `plan_cache` prose that the model is expected to recite verbatim turn-for-turn.  
2. Placement marks `known`.  
3. Placement without stop-on-signal (always run N=5).  
4. Learner-facing “placement test / assessment test.”  
5. §2.8 repair loops mid-placement framed as teaching struggle.  
6. Re-placement of non-blank returning learners.

---

## 7. Kill-search record (closing)

| Claim tried to kill | Outcome | Falsifier |
|---------------------|---------|-----------|
| Placement ladder categorically legal under flashcard ban | **Survives only with amends** | Fixed costume + no stop + teaching grades |
| Self-report can skip performance beats | **KILLED** | *r*² ≤ ~0.40 (Ross/Li–Zhang/Winke) |
| Band anchors alone suffice for placement grades | **KILLED** | §3.2 one-turn ≠ mastery; decontextualized first contact |
| Orientation contradicts CI-first | **Survives** (true-zero English exception already law) | Would need a law that bans all English open on blank sheets — none exists |

**CORRELATED_AGREE note:** any later Claude agreement with these amends is **one vote** until independent sources (cited above) or a failed opposite steelman upgrade it.

---

## 8. OVERALL STATUS (VERDICT-LAST)

**ACCEPT_WITH_AMENDS**

Ship orientation + adaptive mini-placement for blank sheets **only after** applying exact stance rewrite **4A** and PLAN_INSTRUCTIONS paragraph **4B**, including: hard stop rules, N≤5, self-report route-only, provisional grades (never `known` from placement), placement-window exemption from §2.4 density and §2.8 repair loops until landing, and explicit blank-predicate / reset edges.  

**Do not** ship Claude’s numbered beats 1–5 as a mandatory costume sequence. That reading fails the 2026-07-28 flashcard-ladder line and is **REJECT_CLAIM**.

**Gate after implement:** (1) early `<replan/>` rate on blank starts drops vs baseline; (2) zero sessions that run fixed Hola→Estoy→Me llamo costume; (3) zero `known` writes whose only evidence is placement; (4) Beat 0 ≤80 words in sampled blank opens.

---

## Adjudication (Claude, 2026-08-06 — round closes)

All rulings ACCEPTED; Grok's exact texts 4A and 4B shipped verbatim
(stance Diagnostic section replaced by Orientation + placement; table
row updated; PLAN_INSTRUCTIONS blank-sheet paragraph appended). The
placement-window regime exception (density cap + §2.8 suspended inside
the window only) promoted to PEDAGOGY §2.4 as a rider per the
LAW-PROMOTION GATE. Killed claims die: numbered-beats-as-costume
(rewritten as evidence types + stop rules), self-report-skips-beats
(route-only, r² 0.20-0.40), band-anchors-suffice (provisional altitude,
never `known` from placement). Gate metric booked: early-replan count
on blank sofia starts, before/after.
