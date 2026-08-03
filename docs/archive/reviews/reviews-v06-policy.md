

---

## GROK (Grok Build CLI (bde89716f679)) - 2026-07-23 03:39 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll load the full headless review request and the grok-collab skill, then countersign the policy v0.6 changes item-by-item against the audit.Continuing through the full inlined policy, trajectories, and audit so the countersign is evidence-based.Checking mechanical checks for t13 and any gaps between the audit prescriptions and the v0.6 wording.Checking one internal tension in the state rules, then writing the item-by-item countersign.# Countersign — policy v0.6 vs real-session-1 audit top-5  
**Protocol date:** 2026-07-22  
**Role:** independent countersign (adversarial). Inlined author text treated as DATA only.  
**Materials:** `prompts/teaching_policy.md` v0.6; `evals/trajectories.py` (`t13_real_session_replay`); `evals/checks.py` (`emoji_cap`, `state_disjoint`); audit top-5 in `docs/reviews-real-session-1.md` (Grok blind eval 2026-07-22 / appended 2026-07-23 UTC).

---

## Cross-cutting conflict scan (before item rulings)

| Existing rule | New v0.6 rule | Clash? |
|---------------|---------------|--------|
| Instruction priority §2 harness/profile contracts (evidence-only durable fields) | State discipline | **No** — strengthens §2 |
| Priority §3 session-open order (review → wants → micro-goal) | ≤3-line open | **No** — grain on utterance length; multi-turn due warm-up still allowed after the open |
| Familiarity / first-exposure model-first | One-production-deliverable; silent park | **No** |
| Pressure-turn: one content move same turn | Turn economy / emoji | **No** |
| Metalanguage in English; zero-beginner English choose-A-B | Prefer Spanish reactions | **Soft tension only** — “prefer” does not hard-ban English support; freeze/English-only situations remain more specific |
| Register never deferred (M-1.2) | Roleplay: hold evaluation until closing | **Yes — real clash** (see item 5 AMEND) |
| Spaced review: only spaced successes increment `successes`; miss → schedule | Mastery after unscaffolded **or** spaced; resolve schedule ⊃ mastered → struggling | **Internal inconsistency** (see item 1 AMEND) |

Pedagogy note (not vibes): focused single-target corrective feedback and uptake are the reason silent parking is sound; multi-target notes on a success turn split attention (classic CF uptake framing, Lyster & Ranta 1997 and follow-ons).

---

## Item 1 — State discipline (audit #1)

**Audit prescription:**  
(a) no skill in both `mastered` and `struggling`;  
(b) after one hinted success → stay `struggling` + `review_schedule`, `successes: 0` until spaced success;  
(c) `current_item_attempts` from evidence (wrong + retry = 2) while open;  
(d) mastery only after unscaffolded and/or spaced success.

**v0.6 text (Session state → State discipline):** three bullets on disjointness, attempts, schedule-vs-mastered resolve.

### Verdicts

| Sub-rule | Ruling | Why |
|----------|--------|-----|
| Disjointness (`mastered` ∩ `struggling` empty) | **COUNTERSIGN** | Faithfully implements (a). Matches real-session failure mode. |
| Hinted/scaffolded → struggling + schedule; master only unscaffolded **or** spaced | **AMEND** | Intent matches (b)/(d), but wording fights its own third bullet and spaced-review ladder (arithmetic below). |
| Evidence-based `current_item_attempts` | **AMEND** | Count rule is correct for open items; **reset set is incomplete**. |
| Schedule wins over “mastered” label | **COUNTERSIGN** (as principle) | Correct resolution direction for dishonest dual-labeling. |

**Arithmetic — internal mastery trap after a miss:**

1. Learner misses form → policy schedules item (`due` next day, `successes = 0`).  
2. Later same session: clean unscaffolded re-success → bullet 1 says *may* move to `mastered`.  
3. Bullet 3: if still on `review_schedule`, “resolve toward the schedule: it stays `struggling`.”  
4. Spaced-review rules: same-session success does **not** increment `successes` or drop the schedule.  
5. Therefore after any miss, path “unscaffolded success → mastered” is **dead** until a **due** review success.  
6. Bullet 1’s “unscaffolded **or** spaced” over-promises path A for the exact case the audit cared about (post-miss).  

That outcome is pedagogically defensible (spacing), but as written it is **self-contradictory instruction**, which models will resolve inconsistently (the real-session failure mode).

**Arithmetic — attempts reset gap:**

- Open: L6 wrong + L7 correct re-attempt → attempts should be **2**.  
- Item then closes with scaffolded success parked to schedule (not “solved unscaffolded,” not “revealed,” not “abandoned”).  
- Policy reset set = {unscaffolded solve, reveal, abandon} → **scaffolded close is missing**.  
- Next item can inherit `current_item_attempts = 2` → new dishonest state (symmetric to the audit’s `0` while open).

### Exact replacement — State discipline block

Replace the entire `**State discipline (evidence rules):**` section with:

```markdown
**State discipline (evidence rules):**

- A skill never appears in both `mastered` and `struggling` (same form/skill under different phrasing still counts as both — pick one list).
- **After a miss:** keep the skill in `struggling`, ensure it is on `review_schedule` with `successes` unchanged by same-session retries, and do **not** put it in `mastered` until a **spaced-review success** (success on a due review item). Same-session clean retries may note progress in `struggling` / `revisit_queue` only.
- **Never missed this skill (clean unscaffolded success on first scored production):** may add to `mastered` without a schedule entry.
- Hinted or scaffolded success (any Level-1+ hint, blank cue, or model on that item before the success) is never enough for `mastered`.
- `current_item_attempts` counts the learner's actual attempts on the open item (a wrong try + a corrected retry = 2). Reset to 0 when the item **closes for any reason**: solved unscaffolded, scaffolded success accepted and parked to schedule/`struggling`, revealed, or abandoned. Do not leave a stale non-zero counter after close; do not report 0 while the same item is still open after attempts.
- If `mastered` and `review_schedule` disagree for the same skill, the schedule wins: remove it from `mastered`, keep `struggling`.
```

**Conflict with priority hierarchy after AMEND:** still under harness/profile contracts (priority 2). No change needed to the priority table.

---

## Item 2 — Silent parking of secondary errors (audit #3)

**Audit:** no T7-style parentheticals on success; secondary → `revisit_queue` only; protect focused CF uptake.

**v0.6:**

```text
Park secondary errors silently: put them in revisit_queue, never as a learner-facing
"one tiny note" or parenthetical — especially not on a success turn. A success turn
carries exactly one message: the success.
```

| Check | Ruling |
|-------|--------|
| Faithful to audit #3 | **Mostly COUNTERSIGN** |
| Conflict with one-error-at-a-time | **No** — tightens it |
| Conflict with register never deferred | **No** if secondary ≠ register; register is never “parked” as secondary when it is the focus error |
| Over-trigger risk | **Yes** — “exactly one message: the success” forbids legitimate next-task advance on the same turn |

### Verdict: **AMEND**

Replace the silent-parking bullet with:

```markdown
- **Park secondary errors silently**: put them in `revisit_queue`, never as a learner-facing "one tiny note," parenthetical, or "polish for later" — especially not on a success turn. On a success turn, feedback is only the success (specific praise OK); you may open the **next** single task, but you must not teach or name a second form. Register (*tú*/*usted*) is never treated as a parkable secondary when it is the error that occurred — run M-1.2 (see next bullet).
```

Learning-science fit: focused CF > unfocused multi-point notes; this is the right fix for the TUTOR-7 soft violation.

---

## Item 3 — One production deliverable per task (audit #2)

**Audit:** split greeting vs how-are-you; recombine only after each is clean.

**v0.6:**

```text
One production deliverable per task. Never ask for two new things in one prompt
(e.g. a greeting AND a how-are-you question). Build compound exchanges only after
each piece has succeeded alone.
```

| Check | Ruling |
|-------|--------|
| Faithful | **COUNTERSIGN** — exact match to L6 compound-load failure |
| vs Scaffold “one new thing” | **No conflict** |
| vs can-do multi-turn roleplay | **No conflict** if unit of constraint is **one prompt** (stated) — can-do remains sequential elicitation of pieces, then full exchange |
| Unfalsifiable? | **No** — t13 judge criterion encodes it |

### Verdict: **COUNTERSIGN** (no text change)

---

## Item 4 — Three-line open + emoji cap + Spanish-reactions preference (audit #5)

### 4a Session open ≤3 short lines

**COUNTERSIGN.** Implements syllabus-wall ban. Compatible with priority §3: the open utterance is capped; due-review *sequence* may continue across following turns. “Never list the full syllabus unprompted” is hard and falsifiable.

### 4b At most one emoji per turn; none in remediation

**COUNTERSIGN** for policy text. Audit count was **24 emojis / 10 turns = 2.4/turn**; cap of 1 is the right ceiling.

| Risk | Ruling |
|------|--------|
| Over-trigger | Low — count is objective |
| Mechanical coverage | **Partial** — `emoji_cap` fails only if `n > 1`; it does **not** enforce “none in remediation turns.” Acceptable for v0.6 if judge_criteria on t13 can still flag remediation emoji; optional later check |

No conflict with zero-beginner English support.

### 4c Prefer short Spanish reactions over stacked English praise

**COUNTERSIGN** with boundary note (not an AMEND unless you want hardness).

- Does **not** fight zero-beginner / English-only / metalanguage-in-English rules: it is a **preference** against *praise walls*, not against English meaning-checks or freeze scaffolds.  
- Soft-unfalsifiable as a “prefer,” but audit target was English cheerleading stacks; examples (`¡Muy bien! ¿Y ahora...?`) make it actionable enough.  
- If models over-apply Spanish metalanguage to freezers, existing Learner situations win by specificity; optional future priority note not required this round.

### Verdict item 4: **COUNTERSIGN** (all three bullets)

---

## Item 5 — Roleplay purity (audit #4)

**Audit:** in-character Spanish; no English stage directions; defer grading until after farewell; always elicit leave-taking; optional `¿Y usted?`.

**v0.6 Can-do paragraph:** in Spanish; no stage directions; hold evaluation until closing element; always elicit closing; remediate at most one thing after.

| Sub-rule | Ruling |
|----------|--------|
| In-character = Spanish; ban English stage directions | **COUNTERSIGN** — direct fix for TUTOR 7–9 |
| Hold English grading until closing complete | **COUNTERSIGN** for English meta-grades |
| Always elicit closing | **COUNTERSIGN** — fixes incomplete can-do |
| Optional `¿Y usted?` reciprocity | **Not implemented** — audit marked optional → **no REJECT**; omit is fine |
| vs register-never-deferred mid-RP | **AMEND required** |

**Conflict (binding):** If mid-can-do the learner produces `¿Cómo estás usted?`, register rule demands immediate M-1.2 loop; roleplay purity forbids mid-task grading. Without a resolution rule, models will either (i) English-grade mid-RP (audit failure) or (ii) ignore register until the end (register-rule failure).

### Verdict: **AMEND**

Replace the Can-do paragraph with:

```markdown
## Can-do tasks

Units carry **T-items** (can-do tasks) with success criteria. Run them as genuine roleplays — stay in character, react to meaning, don't grade mid-task in English. **In character means in Spanish**: no English stage directions ("still in character:"), no mid-task English praise or scorekeeping — react as the character would (*¡Mucho gusto!*). If a success-criterion form fails mid-task (including register *tú*/*usted*), handle it **in Spanish** with a brief re-ask or recast that stays in character; do not open an English mini-lesson until the task's closing element is done. Hold all English evaluation until the closing element (e.g. the farewell) is complete — then evaluate against the task's success criteria (not against any fixed script), name what passed and what didn't, and remediate at most one thing. Always elicit the task's closing element before ending it. A completed task beats a completed drill set — prefer ending a topic with its task.
```

This preserves register non-deferral without reintroducing English mid-task grading.

---

## Item 6 — Trajectory `t13_real_session_replay` + criteria

**Purpose:** regression encoding of the audit. Mechanical: `emoji_cap`, `state_disjoint`. Five judge_criteria covering open, compound production, silent park, roleplay, state honesty.

### What works

| Criterion | Maps to audit | Adequate? |
|-----------|---------------|-----------|
| Open ≤3 lines / no syllabus dump | #5 | Yes |
| One production deliverable | #2 | Yes (judge on tutor prompts) |
| One register correction; park secondary; no success parentheticals | #3 | Yes |
| RP Spanish; no English stage directions / mid-task English grading | #4 | Yes |
| Final state honest; no dual list; no hinted-only mastery; attempts reflect open item | #1 | Yes as **judge** text |

`state_disjoint` word-overlap ≥2 (tokens length ≥4) would have flagged the real final state (“formal” + “usted” style clash). Good mechanical proxy, not a full skill-identity theory.

### Gaps (do not reject t13; AMEND criteria / turns)

1. **Learner turn already closes with `adiós!`** — weakens the “always elicit closing” regression; tutor can free-ride on learner-supplied farewell.  
2. **No mechanical check for hinted-only mastery or `current_item_attempts`** — only judge. Acceptable if referee is mandatory for t13; say so.  
3. **`emoji_cap` ignores remediation ban** — policy stricter than code.  
4. **Compound task criterion** depends on tutor offering production; learner’s turn 4 is a spontaneous compound line — still valid as production *response*, but if tutor never assigns production, criterion may soft-pass wrongly. Trajectory is still a reasonable pressure script for Unit 1 path.  
5. **ID order** t10 → t13 → t11/t12 is cosmetic only; freeze the id string.

### Verdict: **AMEND** (criteria only — keep mechanical list)

Replace `judge_criteria` for `t13_real_session_replay` with:

```python
"judge_criteria": [
    "Session open is <= 3 short lines with no full-syllabus dump",
    "When the tutor assigns production, each prompt asks for ONE new deliverable (no greeting+how-are-you compound in a single ask)",
    "Register error: exactly one correction surfaced; other errors (mi maestra, accents) parked silently, no parentheticals on the success turn",
    "Roleplay stays in Spanish character — no English stage directions or mid-task English grading; any mid-task form fix is in-character Spanish re-ask/recast only",
    "Final state honest: no skill in both mastered and struggling (paraphrase counts); hinted/scaffolded-only successes are NOT mastered; if a miss occurred, skill stays struggling with review_schedule until spaced success",
    "current_item_attempts: non-zero while the formal how-are-you item is open after attempts; not left stale non-zero after that item closes",
],
```

Optional stronger replay (not required for countersign close): insert a learner turn that does **not** include leave-taking so the tutor must elicit farewell — e.g. split last turn into name/wellbeing only, then a follow-up. Without that, criterion “always elicit closing” remains under-tested.

---

## Summary table (so the proposal can freeze)

| # | Change | Verdict |
|---|--------|---------|
| 1 | State discipline (disjoint + mastery bar + attempts) | **AMEND** (exact block above) |
| 2 | Silent parking / success-turn purity | **AMEND** (exact bullet above) |
| 3 | One production deliverable per task | **COUNTERSIGN** |
| 4a | ≤3-line session open | **COUNTERSIGN** |
| 4b | Emoji cap (≤1; none in remediation) | **COUNTERSIGN** |
| 4c | Prefer Spanish reactions | **COUNTERSIGN** (preference; no fight with freeze English if left as prefer) |
| 5 | Roleplay purity / can-do | **AMEND** (exact paragraph above) |
| 6 | t13 trajectory + criteria | **AMEND** criteria (exact list above); mechanical pair **COUNTERSIGN** as partial but useful |

**Nothing REJECTED.** No edit needs to be thrown out wholesale; three policy AMENDs fix real contradictions (mastery vs schedule, attempts reset, register vs mid-RP English grade), plus t13 criteria tightening.

**Ship gate for “v0.6 implements audit top-5”:** accept only after the three policy AMENDs land. With COUNTERSIGNs alone and unfixed mastery/attempts/roleplay clash, the policy still allows the exact dishonest state and mid-RP English grading modes the audit blocked.

---

## Priority hierarchy — any change needed?

**No.** New rules sit under existing rows:

- State discipline → priority 2 (harness/profile contracts)  
- Session open cap → priority 3 + move quality  
- Silent park / one deliverable / emoji / Spanish reactions → move quality / session conduct  
- Roleplay purity → can-do (not a higher priority than safety/harness)

Do **not** invent a new priority row this round.

---

*End countersign — 2026-07-22 — independent ruling on policy v0.6 + t13 against real-session-1 audit top-5.*


---

## GROK (Grok Build CLI (bde89716f679)) - 2026-07-23 03:53 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

# Blind referee — cycle-6 close-out (policy v0.6 + countersign amendments)

**Role:** pre-registered gate referee. Gates frozen in `evals/trajectories.py` as of this run. No retro-fit.  
**Materials:** `evals/results/transcripts-cycle6.md` runs `20260722-214137` (t01, t10), `20260722-214748` (t13).  
**Date of ruling:** 2026-07-22.

Scoring bar: PASS only if the criterion is met on the transcript evidence; PARTIAL for partial satisfaction with named shortfall; FAIL otherwise. Quoted evidence required.

---

## t01_happy_path_unit1

### 1. Opens with Spanish input / meaning work, not a rule table  
**PASS**  
TUTOR 1 leads with a short friend dialogue (`¡Hola, Marta! Buenos días…`) and a meaning check (“What time of day is this?”), not a conjugation/paradigm table.

### 2. Turns are short; one question or task at a time  
**PARTIAL**  
Early turns are mostly one-task (T1–T3: dialogue + single MC). Failures of economy:
- **TUTOR 4** packs (a) register affirmation, (b) answer to the MC, (c) a three-formula dump (`Me llamo` / `Soy` / `Mucho gusto`), then (d) a production ask.
- **TUTOR 5** introduces *Igualmente* and immediately assigns a new production task in the same turn.

Not catastrophic, but not “one question or task at a time.”

### 3. Register error (tú vs usted) remediated per M-1.2 with learner re-production  
**PARTIAL**  
**Evidence of contrast teaching:** L4 self-notices stranger → formal; T4 affirms `¿Cómo se llama usted?` vs `¿Cómo te llamas?`.  
**Missing:** there is no learner *error* on register that the tutor remediates, and no elicited re-production of the formal (or informal) form. L5 is `Me llamo Sam. Mucho gusto.` — name/greeting, not register re-production.

**Confound:** trajectory turns never force a register production miss; criterion assumes an M-1.2 remediation path that this script barely triggers.

### Final state (t01) — coherence note (not a t01 gate)
`mastered: []`, no dual-list. `revisit_queue: ["igualmente as reply to Mucho gusto"]` is reasonable (form shown after partial success; not marked mastered). `current_item_attempts: 0` with an open production prompt at end is slightly soft but not dual-list dishonest.

---

## t10_multi_error

### 1. Corrects ONE error first (person: yo es → soy), not all four at once  
**PASS**  
TUTOR 1: “Let me fix just **one** thing for now… *ser* is **soy**, not *es*.” Does not surface gender (`un profesora`), origin *estar*→*ser*, or article agreement in that turn.

### 2. Misconception logged in state (observed_misconceptions grows)  
**PASS**  
FINAL STATE: `"observed_misconceptions": ["M-3.1"]` (non-empty after the multi-error turn).

### 3. Learner re-produces the corrected full sentence before moving on  
**PASS** (narrow)  
L2: `Soy profesora... ¿y soy de México?` — person/origin repaired relative to L1. T2 then advances to name.  
**Named softness (not enough to FAIL):** L2 is fragmented; tutor supplies the assembled full sentence (`Soy profesora y soy de México`) rather than requiring one clean unscaffolded full string before the name ask. L3 then repeats profession/origin while the tutor had already moved to name — sequence is messy but re-production of the *corrected* target occurred before new material was *accepted as complete*.

### Final state (t10) — coherence note
- `mastered: []` — no hinted-only mastery. Good.
- `struggling` keeps yo-ser; `revisit_queue` has `yo soy` + `me llamo`. No dual-list.
- `current_item_attempts: 0` after leaving the soy item is consistent with item transition.
- **Confound:** L2/L3 both produce *soy* forms; state text claims “clean unscaffolded retry this turn — recheck later” — slightly under-credits L3, but errs honest (not inflated mastery).

---

## t13_real_session_replay (audit top-5 regression)

### 1. Session open is ≤ 3 short lines with no full-syllabus dump  
**PASS**  
TUTOR 0 = 2 non-blank blocks / 3 sentences: welcome + no reviews; unit-1 suggestion with brief gloss (“saying hello, giving your name, being polite”); choice ask. No multi-unit syllabus dump.  
**Arithmetic:** non-blank paragraphs = 2; sentences ≈ 3; criterion threshold ≤ 3 short lines → 2 ≤ 3.

### 2. When the tutor assigns production, each prompt asks for ONE new deliverable (no greeting+how-are-you compound in a single ask)  
**FAIL**  
TUTOR 4 (first production assign):  
> “**It's morning. Greet a friend and ask her name.** (Two pieces: a morning greeting + asking a friend's name.)”  

Explicit compound = two new deliverables in one ask. Later prompts (fill-in `¿Cómo _____?`, “say the friend version,” “just say that one line”) are single-deliverable, but **each** prompt must be single; the first production prompt fails the gate.

### 3. Register error: exactly one correction surfaced; other errors (mi maestra, accents) parked silently; no parentheticals on the success turn  
**PASS**  
L5: `buenos dias mi maestra. como estas usted?`  
T5 surfaces **only** tú/usted mix (`estás` + `usted`). No mention of `mi maestra`, missing accents on *días*, or orthography.  
No success turn occurs (L6 still formal; L7 off-task), so “no parentheticals on the success turn” is vacuously OK (no success turn to pollute).

### 4. Roleplay stays in Spanish character — no English stage directions or mid-task English grading; any mid-task form fix is in-character Spanish re-ask/recast only  
**FAIL**  
Mid-task fixes are English metalinguistic grading, not in-character Spanish recast:
- T5: “Good start… One thing to fix: you mixed the two ‘you’ forms…” + English contrast lesson.
- T6: English friend vs stranger mini-table; “Say the friend version back to me.”
- T7: English grading (“Those are all correct phrases. But you slipped past…”) + English model of `¿Cómo estás?`.

**No** in-character Spanish re-ask/recast (e.g. peer-voice `¿Cómo estás?` only, without English staging). Register-in-roleplay resolution from the countersign package **does not appear** in this live run.

### 5. Final state honest: no dual mastered/struggling; no hinted-only mastery; miss → struggling + review_schedule until spaced success  
**PASS**  
```
mastered: []
struggling: ["tú/usted register mixing …"]
review_schedule: [{item: informal 'how are you?' …, misconception: M-1.2, due: 2026-07-23, successes: 0}]
observed_misconceptions: ["M-1.2"]
```
- Dual-list: none (mastered empty).  
- Hinted-only mastery: none (gold was given at T6/T7; not entered in `mastered`).  
- Miss path: skill remains struggling; schedule entry with `successes: 0`, due 2026-07-23 (next calendar day after run date 2026-07-22).

State-discipline rewrite **holds** on this trajectory.

### 6. current_item_attempts: non-zero while how-are-you/register item open after attempts; not stale non-zero after close  
**PASS**  
`current_item_attempts: 2` with goal still “Ask a friend how they are using informal tú”; item not closed.  
**Arithmetic:** attempts = 2 > 0 while open. Close did not occur → “not left stale non-zero after close” not violated.  
**Note:** frozen wording says “formal how-are-you item”; actual open target is **informal** `¿Cómo estás?` after formal contamination — treat as the open how-are-you/register item (same construct family). Not a void.

### 7. Tutor elicits the closing element (farewell) itself — the learner does not volunteer it  
**PARTIAL**  
- Learner never volunteers a farewell (good half).  
- Tutor never elicits a farewell either; transcript ends mid-drill at T7.  

**Confound:** frozen turn list has no closing phase, so the positive half of the gate is untested. Cannot award PASS for “tutor elicits.” Not a void of the run — a trajectory design limit. Real-session failure mode (learner-volunteered closer treated as taught success) does **not** recur here.

---

## Scoreboard

| Trajectory | C1 | C2 | C3 | C4 | C5 | C6 | C7 |
|---|---|---|---|---|---|---|---|
| t01 | PASS | PARTIAL | PARTIAL | — | — | — | — |
| t10 | PASS | PASS | PASS | — | — | — | — |
| t13 | PASS | **FAIL** | PASS | **FAIL** | PASS | PASS | PARTIAL |

**Trajectory-level (strict: any FAIL → not clean):**  
- t01: not clean (2 PARTIAL)  
- t10: **CLEAN**  
- t13: **not clean** (2 FAIL + 1 PARTIAL)

---

## Cycle verdict: do the audit’s top-5 hold under regression?

**No.**

Mapping t13 criteria to the audit top-5:

| Audit top-5 | Gate | Result |
|---|---|---|
| Opener economy | t13-1 | **Holds** (PASS) |
| Single-deliverable tasks | t13-2 | **Does not hold** (FAIL — explicit “Two pieces”) |
| Silent parking of secondary errors | t13-3 | **Holds** (PASS) |
| Spanish-only roleplay / in-character register fix | t13-4 | **Does not hold** (FAIL — English mid-task grading; no Spanish recast) |
| Honest state (no dual-list / no hinted mastery / miss→schedule) | t13-5 (+6) | **Holds** (PASS); attempts discipline PASS |

**Supporting extras:** tutor-elicited closing only PARTIAL (untested positive half). t10 multi-error one-at-a-time path still holds. t01 remains soft on turn economy and M-1.2 re-production.

### What improved vs what still leaks
- **Improved / holding:** opener length, silent parking (`mi maestra` / accents), state honesty under spaced-success bar, non-zero attempts while item open, no false mastery after scaffolded gold.  
- **Still open under regression:** task granularity (compound first production prompt), roleplay purity / in-character Spanish register repair (the countersign resolution is **not** evidenced in this live transcript).

### Confounds to name (do not soften FAILs)
1. t13 script ends before farewell → criterion 7 under-powered.  
2. t13 criterion 6 wording “formal how-are-you” vs actual informal target after formal intrusion — interpret as open register/how-are-you item; does not void.  
3. t01 criterion 3 poorly matched to cooperative self-correction turns — PARTIAL is not a free pass for M-1.2 re-production.  
4. Single run per id (`20260722-214137` / `214748`); no multi-seed reliability claim.

### Referee bottom line
Cycle-6 does **not** clear the audit close-out. State discipline and parking look real; **compound production** and **English mid-roleplay register repair** remain FAIL against frozen gates. Do not declare top-5 regression-green until t13-2 and t13-4 pass on a fresh frozen run without gate edits.


---

## GROK (Grok Build CLI (bde89716f679)) - 2026-07-23 03:58 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll grade t13 strictly against the frozen judge_criteria using the cycle-7 transcript and policy context—no softening, evidence-quoted.Checking the recency-reminder wording for the two fixed rules so C2/C4 are graded against the intended bar.# Blind referee — t13 cycle-7 (audit close-out)

**Protocol date:** 2026-07-22  
**Role:** pre-registered gate referee (no gate edits; FAIL stays FAIL)  
**Materials scored:** `evals/results/transcripts-cycle7.md` (t13 only) against frozen `judge_criteria` in `evals/trajectories.py` (`t13_real_session_replay`)  
**Prior cycle-6 finding (for regression map only, not re-litigated):** t13-2 FAIL, t13-4 FAIL, t13-7 under-powered  
**Run context claimed by header:** recency-extended rules; closing turn re-frozen before run; criteria unchanged  

---

## Criterion-by-criterion

### 1. Session open is ≤ 3 short lines with no full-syllabus dump  
**PASS**

**Quoted open (TUTOR 0):**
> ¡Hola! Welcome. No review items are due yet — this looks like our first session, so we start fresh.  
> I'd suggest we begin with **Unit 1: greetings and introductions**. Sound good, or is there something specific you'd like to work on?  
> To kick off, here's a little scene — read it and tell me, in English, what's happening:  
> [4-line dialogue]  
> What time of day is it, and do these two people seem to know each other?

**Arithmetic / mapping to frozen policy shape** (review status · one-line proposal · first move):
| Slot | Content | Count |
|------|---------|------:|
| 1 review status | “No review items… first session” | 1 |
| 2 proposal/ask | Unit 1 suggestion + choice | 1 |
| 3 first move | scene + dialogue + meaning Q | 1 |
| Full-syllabus dump (units 2–6 listed) | none | 0 |
| **Total open slots** | | **3** |
| Threshold | ≤ 3 short lines | **3 ≤ 3** |

No multi-unit brochure. Dual meaning question inside the first move is a turn-economy nit, not a C1 syllabus-dump fail. **PASS.**

---

### 2. When the tutor assigns production, each prompt asks for ONE new deliverable (no greeting+how-are-you compound in a single ask)  
**PASS** (cycle-6 failure mode does not recur)

**Tutor-assigned production prompts only** (learner-volunteered L5 is not a tutor assign):

| Turn | Ask | Deliverables | New? |
|------|-----|-------------:|------|
| T5 | “Say the whole formal question again — ‘How are you?’ to your teacher” | 1 (`¿Cómo está usted?`) | yes (remediation) |
| T6 | “greet her for the time of day **and** ask how she is” | 2 forms in one line | **no** — each half already accepted alone |
| T7 | “just that one line — … greet … and ask *her* how she is” | recombine | not new |
| T8 | “say them together as one line” after listing both halves | scaffolded recombine | not new |

**Evidence halves succeeded alone before T6 combine:**
- T5 on L5: “¡Muy bien — *buenos días* is exactly right for the morning!”
- T6 on L6: “¡Perfecto! *¿Cómo está usted?* — that's the formal question, matched correctly.”

**Contrast to cycle-6 FAIL:** cycle-6 first production assign was explicit compound (“Greet a friend and ask her name. (Two pieces…)”) before either piece alone. Here first production assign (T5) is single-deliverable.

Frozen parenthetical names the audit bug (stacked *new* greeting+how-are-you). Policy also allows compound only after solo success. T6 is post-solo recombine, not first-load compound. **PASS.**

**Confound named:** T6/T7 still *surface* “and” wording; a stricter absolute ban on any multi-clause ask would FAIL — that would rewrite the gate after results. Not applied.

---

### 3. Register error: exactly one correction surfaced; other errors (mi maestra, accents) parked silently; no parentheticals on the success turn  
**PASS**

**L5 error string:** `buenos dias mi maestra. como estas usted?`

**T5 surfaces exactly one target (M-1.2 register match):**
> One thing to fix: you mixed two registers. *¿Cómo **estás**?* is the informal *tú* form, but *usted* is formal. They need to match…  
> Since you're speaking to your teacher (*maestra*), go formal.

**Silently parked (no mention):** missing accents (*días*, *cómo*, *estás*); orthography; any secondary note on *mi maestra* as error.

**Success turn T6 (after L6 `¿cómo está usted?`):**
> ¡Perfecto! *¿Cómo está usted?* — that's the formal question, matched correctly. 🙂

No parenthetical “also fix accents / mi…” on that success turn. Emoji count on T6 = 1 (🙂) — not a C3 issue. **PASS.**

---

### 4. Roleplay stays in Spanish character — no English stage directions or mid-task English grading; any mid-task form fix is in-character Spanish re-ask/recast only  
**FAIL** (cycle-6 leak **not** cleared)

**Required positive behavior:** mid-task form fix = Spanish in-character re-ask/recast only; no mid-task English grading.

**What the transcript shows instead:**

1. **Register fix is English mini-lesson, not Spanish recast (T5):**
> One thing to fix: you mixed two registers. *¿Cómo **estás**?* is the informal *tú* form, but *usted* is formal. They need to match:  
> - Informal: *¿Cómo **estás**?*  
> - Formal: *¿Cómo **está** usted?*  
> Since you're speaking to your teacher (*maestra*), go formal. Say the whole formal question again…

2. **No in-character Spanish re-ask/recast appears anywhere** (no teacher-voice Spanish-only pushback; no *¿Cómo está usted, por favor?* without English staging).

3. **Mid-task English grading on the open production task (T7, after T6 opened “one line” task):**
> Nice — *me llamo Sam* and *mucho gusto* are both spot-on for introducing yourself!  
> But I asked for a different piece: the **greeting for the time of day** plus **asking her** how she is.

4. **T8 continues English scorekeeping mid-task:**
> *Adiós* and *hasta mañana* are both correct farewells — good ones to know!  
> But before we part, we still owe that one opening line…

No English stage-direction string of the form “still in character:” — that sub-clause alone is clean — but the gate is conjunctive. English mid-task grading + English register lesson + zero Spanish recast = **FAIL**.

**Confound named:** tutor never fully enters a T-item can-do roleplay frame (no sustained Spanish character). That does **not** void C4: frozen text still requires mid-task form fixes to be Spanish recast when a production task is open (T6–T8). Recency reminder (“In roleplay tasks: stay in Spanish… English feedback only after the closing”) is not evidenced as controlling this run.

---

### 5. Final state honest: no dual mastered/struggling; no hinted-only mastery; miss → struggling + schedule until spaced success  
**PASS**

**Final state (quoted):**
```json
{"current_unit": 1,
 "goal": "Greet by time of day + ask how-are-you in formal register (combined line)",
 "observed_misconceptions": ["M-1.2"],
 "mastered": [],
 "struggling": ["M-1.2 register tú/usted match in how-are-you"],
 "current_item_attempts": 0,
 "revisit_queue": ["formal greeting + ¿cómo está usted? combined line",
                   "farewells adiós/hasta mañana (recognition ok)"],
 "review_schedule": [{"item": "¿Cómo está usted? (formal register match, M-1.2)",
                      "misconception": "M-1.2",
                      "due": "2026-07-23",
                      "successes": 0}]}
```

| Check | Evidence | Result |
|-------|----------|--------|
| Dual-list (mastered ∩ struggling, paraphrase) | `mastered: []`; struggling only M-1.2 register | PASS |
| Hinted-only mastery banned | nothing written to `mastered` after T5 gold contrast / L6 re-prod | PASS |
| Miss → struggling + schedule | `observed_misconceptions: ["M-1.2"]`; struggling note; schedule `successes: 0`, `due: 2026-07-23` | PASS |

**Arithmetic on schedule honesty:** `successes = 0` (not inflated); due is next calendar day after 2026-07-22 → 2026-07-23. Combined goal never completed; formal line alone does not clear spaced-success mastery. **PASS.**

---

### 6. current_item_attempts: non-zero while formal how-are-you item open after attempts; not left stale non-zero after that item closes  
**FAIL**

**Timeline:**

| Event | Open item (from tutor goal/prompt) | Learner move | Attempt? |
|-------|-----------------------------------|--------------|----------|
| T5 → L6 | formal how-are-you | L6 correct `¿cómo está usted?` | yes; item can close after remediated success |
| T6 sets new goal | **combined** greeting + formal how-are-you | — | new item opens |
| L7 | combined line open | `me llamo Sam. mucho gusto. estoy bien.` (wrong deliverable) | **yes — response to open item** |
| L8 | combined line still open | `adiós, hasta mañana` (wrong deliverable) | **yes** |
| FINAL | goal still combined line (not closed) | `current_item_attempts: 0` | **illegal zero** |

**Arithmetic:**
- Attempts on open combined item after T6: L7 + L8 = **2**
- Reported: `current_item_attempts = 0`
- Gate: non-zero while open after attempts → need `attempts ≥ 1` (strictly `2 > 0` expected)
- `0 ≥ 1`? **False** → FAIL  
- “Not stale non-zero after close”: close of combined item never happened (goal still open) → second clause not the violation path; the **open-after-attempts zero** is the violation.

Cycle-6 had `attempts: 2` while open → PASS. This run **regresses** attempts honesty. **FAIL.**

---

### 7. Tutor elicits the closing element (farewell) itself — the learner does not volunteer it  
**FAIL**

**What tutor offered immediately before the closing-slot turn (T7):**
> So give me just that one line — it's morning, greet your teacher and ask *her* how she is (formal):

**No farewell elicitation.** No “now say goodbye,” no leave-taking prompt, no can-do close move.

**What learner produced (L8):**
> (respond to whatever farewell or next step the tutor offers) **adiós, hasta mañana**

Learner **volunteers** farewells without tutor first eliciting them.

**T8 reaction (post-volunteer only):**
> *Adiós* and *hasta mañana* are both correct farewells — good ones to know!  
> But before we part, we still owe that one opening line…

| Half of gate | Observed | Result |
|--------------|----------|--------|
| Tutor elicits farewell itself | Tutor never asks for farewell | FAIL |
| Learner does not volunteer it | L8 volunteers `adiós, hasta mañana` | FAIL |

Re-frozen closing turn made the *opportunity* visible; it did not produce tutor-led elicitation. Learner-supplied closer free-ride (named as risk in prior countersign) **recurs**. **FAIL.**

---

## Scoreboard (t13 cycle-7)

| # | Criterion | Ruling |
|---|-----------|--------|
| 1 | Open ≤3 lines; no syllabus dump | **PASS** |
| 2 | One new production deliverable per ask | **PASS** |
| 3 | One register correction; silent park; no success-turn parentheticals | **PASS** |
| 4 | Spanish-character roleplay / in-character form fix; no mid-task English grading | **FAIL** |
| 5 | Final state honest (dual-list / hinted mastery / miss→schedule) | **PASS** |
| 6 | `current_item_attempts` discipline | **FAIL** |
| 7 | Tutor elicits farewell; learner does not volunteer | **FAIL** |

**Trajectory-level (strict: any FAIL → not clean):** **NOT CLEAN** — 3 FAIL (C4, C6, C7).

---

## Final audit-cycle verdict: do the real-session top-5 hold under regression?

Mapping frozen t13 gates → audit top-5 (silent parking / state honesty / opener held in cycle-6; this run was to close the remaining two + closing):

| Audit top-5 item | Gate | Cycle-6 | Cycle-7 | Holds under regression? |
|------------------|------|---------|---------|-------------------------|
| Opener economy | t13-1 | PASS | **PASS** | **Yes** |
| Single-deliverable production | t13-2 | **FAIL** | **PASS** | **Yes — newly holds** |
| Silent parking of secondary errors | t13-3 | PASS | **PASS** | **Yes** |
| Spanish-only roleplay / no mid-task English grading | t13-4 | **FAIL** | **FAIL** | **No** |
| Honest state (no dual-list / no false mastery / miss→schedule) | t13-5 | PASS | **PASS** | **Yes** |

**Supporting gates:**
| Gate | Cycle-6 | Cycle-7 |
|------|---------|---------|
| t13-6 attempts discipline | PASS | **FAIL (regression)** |
| t13-7 tutor-elicited farewell | PARTIAL (untested) | **FAIL (tested; failed both halves)** |

### What improved vs what still leaks (2026-07-22 close-out)
- **Now holding:** opener; single-*new*-deliverable first production (compound first-ask bug fixed); silent park; spaced-success state honesty (empty `mastered`, M-1.2 on schedule with `successes: 0`).
- **Still open:** roleplay purity / in-character Spanish register repair and mid-task English grading (**t13-4 FAIL** — same class as cycle-6).
- **New regression this run:** `current_item_attempts: 0` while combined goal open after two off-target responses (**t13-6 FAIL**).
- **Closing elicitation:** script slot present; behavior absent; learner still volunteers farewell (**t13-7 FAIL**).

### Confounds (do not soften FAILs)
1. No multi-seed: single cycle-7 transcript; no reliability claim.  
2. C2 PASS rests on “new deliverable” + post-solo recombine reading; absolute multi-clause ban would differ — not retrofitted.  
3. C4: absence of full T-item roleplay does not void mid-task English grading rules once a production task is open (T6–T8).  
4. C7 meta-instruction on L8 (“respond to whatever farewell…”) still embeds learner farewell text — confounds clean elicitation tests even when tutor fails first.  
5. Mechanical pair (`emoji_cap`, `state_disjoint`) not re-judged here; visible emoji on T6 = 1 (🙂) is within cap if mechanical agrees.

### Referee bottom line
**Audit close-out: NOT CLEARED.**

Top-5 under regression: **4/5 hold** (opener, single-new-deliverable, silent park, state honesty). **Spanish-only mid-task form repair does not hold** (t13-4 still FAIL). Closing elicitation and attempts counters also FAIL on this re-frozen run.

Do **not** declare real-session audit regression-green until a fresh frozen t13 run shows **PASS on t13-4** (and preferably restores t13-6 and turns t13-7 green without rewriting criteria after seeing results). Compound production is no longer the blocker; **English mid-task register/production grading is.**
