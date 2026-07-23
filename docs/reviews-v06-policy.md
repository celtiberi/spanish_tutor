

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
