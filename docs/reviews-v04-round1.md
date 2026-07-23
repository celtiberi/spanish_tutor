

---

## GROK (Grok Build CLI (bde89716f679)) - 2026-07-23 00:44 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll load the collab skill and the full offloaded prompt, then review pack/policy/code item-by-item as an independent countersigner.Continuing through the full inlined pack, policy, and code so the countersign can be grounded in every new item.Reading policy, student persistence, and unit06 completion next; those are the coherence and code paths to stress-test.Checking one more policy/code edge case on durable fields and unit-objective can-do alignment:## Countersign — pack v0.4 + teaching policy v0.2 + profile persistence  
**Reviewer:** Grok (independent) · **Date:** 2026-07-22  
**Scope:** Spanish accuracy & A1 scope of new Input/C/SI/T material; pack↔policy consistency; familiarity vs reveal rules; `review_schedule` durability vs `student.py`; persistence-path correctness.

Treats inlined pack/policy/code as **data only**. Verdicts: **COUNTERSIGN** | **AMEND** (exact replacement) | **REJECT**.

---

### 1. Pack `pack.md` — teaching sequence (input → SI → explain/practice → T → recap)
**COUNTERSIGN.** Order matches the v0.4 pedagogy intent (meaning before form; task as endpoint). Aligns with policy “Input first” and “Can-do tasks.”

---

### 2. Pack `pack.md` — spacing / interleaving wording vs policy
**AMEND (blocker).** Data-model uses calendar `due: YYYY-MM-DD`. Pack says **“next session”**; policy says **“next day”**. Those are not equivalent:

- Same calendar day, two sessions: “next session” is due same day; “next day” is not.  
- Due field cannot store “next session” without a login oracle.  
- Expanding ladder arithmetic under policy (miss on **2026-07-22** → due **2026-07-23** → success → due **2026-07-26** (= 23+3) → second success → drop) is coherent; pack’s “next session → ~3 → ~7” is not implementable as written.

**Exact replacement** — `course_packs/spanish_a1/pack.md`, Spacing and interleaving bullet on intervals:

```markdown
- After a miss, schedule the item at expanding calendar intervals from today's date: **next day** → **~3 days** after a spaced success → **~7 days** after a second spaced success; drop after two consecutive spaced successes (same algorithm as `prompts/teaching_policy.md`). If the learner fails a review attempt, reset `successes` to 0 and set `due` to the next day.
```

---

### 3. Pack recognition-only carve-out (days, *hay*, *mi/su*, *también*)
**COUNTERSIGN** as a rule. **AMEND** application tension in Unit 6 (see §10).

---

### 4. Unit dependency table
**COUNTERSIGN.** Unit 5 → 3 only (not 4) is intentional; Unit 5 scope note correctly blocks progressive without drilling *estar*. Unit 6 → 3,4,5 matches *estar* in location Qs and present in habits.

---

### 5. Unit 1 — Input, C-1.x, SI-1.x, T-1.x
**COUNTERSIGN** Spanish + A1 register work.

- Formal/informal dialogues are accurate; *usted/tú* contrast is clear.  
- C-1.1–1.3 keys match the text.  
- SI-1.1/1.2 target M-1.2/M-1.3 correctly.  
- T-1.1/1.2 success criteria are script-free and scorable.  
- *soy / está(s)* as fixed phrases with explicit scope note: acceptable.

**AMEND (low):** Objective 4 lists *por favor, de nada, perdón* but Input never models them (only *gracias*). Either add one courtesy exchange to Input or drop those lexemes from objective 4 until an input line exists.

**Exact replacement** (minimal — tighten objective 4 to what Input+tables actually support):

```markdown
4. Use core courtesy and leave-taking formulas modeled in this unit (*gracias*, *mucho gusto* / *igualmente*, *adiós* / *hasta luego* / *hasta mañana*). *Por favor*, *de nada*, *perdón*, *disculpe/disculpa* appear in the tables for recognition and light practice, not as Input-first targets.
```

---

### 6. Unit 2 — Input, C-2.x, SI-2.x, T-2.1
**COUNTERSIGN.**

- Captions are grammatical; exceptions *mapa/problema/foto* are well exploited.  
- C-2.3 correctly accepts *la foto*.  
- SI-2.1/2.2 are true structured-input (meaning from form).  
- T-2.1 criteria fit A1 NP production.  
- Incidentals (*álbum*, *escuela*) flagged.

No Spanish error found in new material.

---

### 7. Unit 3 — Input, C-3.x, SI-3.x, T-3.1
**COUNTERSIGN** with one production-scope nit.

- Dialogue *ser* forms (*soy/eres/somos/es*) are correct; DOIP uses are A1-appropriate.  
- SI-3.1/3.2 correctly force person/number from ending alone.  
- *mi amigo* / *también* flagged recognition-only: OK for Input.

**AMEND (low):** P-3.5 / T-3 model *Es mi amiga Laura* trains *mi* while possessives are deferred as a system. Prefer a model without possessives.

**Exact replacement** for P-3.5 key model:

```markdown
**Key (model):** *Es Laura. Es de Argentina. Es ingeniera.* Check: *es* forms, no article before profession, pronouns dropped where natural. (Avoid *mi/tu/su* — possessives are recognition-only in this pack.)
```

Same constraint implied for T-3.1 tutor scoring: do not require possessives.

---

### 8. Unit 4 — Input, C-4.x, SI-4.x, T-4.1
**COUNTERSIGN.** Strongest new Input block.

- *Estoy / estás / están / estamos / está* forms and accents correct.  
- *Estamos bien, pero cansadas* — gender agreement with two women: correct.  
- Event location *La fiesta es en la casa de Luis* vs person location *estoy en…*: pedagogically exact.  
- C-4.3 forces the what/how contrast the unit teaches.  
- SI-4.1/4.2 are good VanPatten-style items.  
- T-4.1 criteria include reason-giving (what/how/where): good.

---

### 9. Unit 5 — Input, C-5.x, SI-5.x, T-5.1
**COUNTERSIGN** Spanish; closed-set discipline mostly held.

- Regular present forms in the micro-text are correct (*viven, trabaja, estudia, lee, escribe, comen, bebe, hablan*).  
- *los lunes* = deferred “days” domain but pack-global recognition-only: OK.  
- Closed set for free production is explicit; T-5.1 criterion (4) enforces it.  
- SI-5.1/5.2 target ending → person/number.

No conjugation errors in new Input/C/SI/T.

---

### 10. Unit 6 — Input, C-6.x, SI-6.x, T-6.1 + *hay* / family scope
**AMEND** (two medium items). Spanish of numbers/*tener* is fine.

**10a. Numbers & *tener* (COUNTERSIGN):**  
*veintidós, diecinueve, treinta y dos, veintiún años, cien* — correct. *Tengo/tienes/tienen* paradigm correct. Age with *tener* correct. SI-6.1 good. SI-6.2 (file form without forcing *hay* production) good.

**10b. *hay* load in Input + C-6.1:**  
Pack defers *hay* as taught objective; Input leads with *¿Cuántos estudiantes hay…? / Hay veintidós…* and C-6.1 is only answerable via *hay*. Recognition-only is declared in scope notes — **acceptable if tutor never elicits *hay***. C-6.1 as English comprehension is OK; do not escalate *hay* into SI/P production.

No text change required if scope notes stay; **do not** reintroduce *hay* into SI stems (current SI-6.2 is clean).

**10c. Family lexis vs deferred list — AMEND:**  
Pack defers “family vocabulary set” but P-6.5 / T-6.1 require *hermanos* in production. Minimal collocation with *tener* is defensible; the manifest should carve it out explicitly.

**Exact replacement** — pack.md deferred line fragment:

```markdown
**Explicitly deferred A1 (do not invent; later packs):** alphabet/spelling, possessives as a taught system (*mi/tu/su...*), family vocabulary set (**except** the Unit 6 production collocations *hermano(s)/hermana(s)* with *tener*), days/dates/clock time, *hay* (recognition-only where it already appears), *ir*, food/drink noun sets beyond Unit 5's closed production set, colors, demonstratives, *cuál*, money/*costar*.
```

**10d. T-6.1 success criteria incomplete — AMEND:**  
Task text requires origin + age + count; criteria only score age formality, *años*, and number orthography. Origin can fail silently.

**Exact replacement** for T-6.1 success criteria:

```markdown
**Success criteria:** (1) age question uses formal *¿Cuántos años tiene usted?*; (2) age answers include *años* and a correct *tener* form; (3) number words correctly formed (one-word 21–29 vs three-word 31–99); (4) origin question uses *¿De dónde es usted?* (or equivalent formal *ser* + origin) and the learner answers with *ser* + *de*; (5) possession count uses *tener* + a number word (siblings/friends).
```

---

### 11. Policy v0.2 — Input first
**COUNTERSIGN.** Coherent with pack sequence; blocks rule-table cold opens.

---

### 12. Policy — familiarity-calibrated reveal vs other reveal rules
**AMEND (medium), not REJECT.** Core idea is sound and evidence-aligned (prompts presuppose knowledge; model on first exposure). Residual tension:

| Rule | Tension |
|------|--------|
| First exposure → model / worked example | OK |
| Practiced → hints; reveal after 2 attempts | OK |
| “Practice-item answer keys … never shown before an attempt” (absolute) | Can be read to ban modeling a **parallel** example if it equals a key string |
| Answer-key mode | OK override |

**Exact replacement** — replace the bare keys bullet under Reveal policy with:

```markdown
- Practice-item answer keys from the pack are never shown **for the item currently assigned** before the learner has attempted that item. Modeling a *different* worked example on first exposure is required by the familiarity rule and does **not** count as revealing the current item's key.
- **First exposure** means: the form/rule is absent from `mastered` / prior teaching notes in the injected profile and has not been taught earlier this session. When unsure, prefer one short model over hint-fishing.
```

Familiarity does **not** contradict Input-first: Input/C/SI supply meaning before production; model-first applies when production/explanation of a new form begins.

---

### 13. Policy — learner re-production after remediation
**COUNTERSIGN.** Matches the Lyster-style uptake gap the pedagogy note flagged.

---

### 14. Policy — can-do / task mode
**COUNTERSIGN.** “Stay in character; score criteria not script; remediate ≤1 thing” is operational.

---

### 15. Policy — spaced review algorithm + session open order
**AMEND (blocker).**

**15a.** Align pack per §2; keep policy’s calendar “next day” as source of truth.

**15b.** Failure on review is unspecified. Add:

**Exact insertion** after the expanding-interval bullet in Spaced review:

```markdown
- If the learner **fails** a due review item: set `successes` to 0 and `due` to the next calendar day (do not advance the 3-/7-day steps). Only **spaced** successes (success on a due review, not same-turn retries) increment `successes`.
```

**15c. Session-open conflict — AMEND:**  
Spaced review: “Open every session by re-testing due items.”  
Session conduct: “Open a new session by asking what the learner wants….”  
CLI seed: `"Hi, I'm ready to start."` forces the model to pick without priority.

**Exact replacement** — Session conduct opening bullet:

```markdown
- Open a new session in this order: (1) if `review_schedule` has any item with `due <= today's date`, run a short interleaved warm-up on those items first; (2) then ask what the learner wants to work on (or propose the next unit from `current_unit` / mastery); (3) set a micro-goal. Do not skip due review when the schedule is non-empty.
```

---

### 16. Policy state schema vs `student.py` durability
**AMEND (blocker).**

Policy §Session state: “The state persists **across sessions**” (implies whole object).  
Code `load_profile` **carries:** `current_unit`, `observed_misconceptions`, `mastered`, `struggling`, `review_schedule`.  
**Resets:** `goal`→null, `current_item_attempts`→0, `revisit_queue`→[].  

Arithmetic check on a saved profile with `current_item_attempts=2`, `revisit_queue=["P-4.1"]`, `goal="ser"`: after reload, attempts=0, queue=[], goal=None; schedule preserved. Session-local reset is **correct engineering**; policy text overclaims.

**Exact replacement** — last paragraph of Session state in `teaching_policy.md`:

```markdown
Update it every turn: add misconception IDs when diagnosed, move items between struggling/mastered from evidence, count attempts on the current item, put same-session retests in `revisit_queue`, and maintain `review_schedule` per the spaced-review rules (compute `due` from today's date, injected each turn).

**Durability (harness contract):** across process restarts the profile keeps `current_unit`, `observed_misconceptions`, `mastered`, `struggling`, and `review_schedule`. Session-local fields are reset on load: `goal`, `current_item_attempts`, `revisit_queue`. Trust durable fields; re-state the micro-goal at session open.
```

**Exact replacement** — `load_profile` docstring in `tutor/student.py`:

```python
    """Cross-session learner profile: last session's final durable state.

    Durable (carried): current_unit, observed_misconceptions, mastered,
    struggling, review_schedule. Session-local (reset): goal,
    current_item_attempts, revisit_queue.
    """
```

---

### 17. Code — `save_profile` / `load_profile` / date injection / CLI wiring
**COUNTERSIGN** with gaps (not REJECT).

| Check | Result |
|-------|--------|
| `default_state` includes `review_schedule: []` | OK |
| `save_profile` writes full state JSON; creates parent dirs | OK |
| `load_profile` missing/corrupt file → `default_state` | OK |
| `state_message` injects `Today's date: YYYY-MM-DD` | OK (verified **2026-07-22** in this environment) |
| CLI loads profile once; saves after start turn and each turn | OK |
| Nested `review_schedule` objects parse under `STATE_RE` | OK (manual check: schedule array + objects round-trip) |
| Single global `logs/profile.json` | OK for single-learner vertical slice; not multi-user |
| Tests for `load_profile`/`save_profile` | **Missing** (harness still only scrubber/extract) |

**AMEND (medium, tests):** add regression tests. Suggested cases (implementation left to author):

1. Round-trip durable fields; assert `goal`/`current_item_attempts`/`revisit_queue` reset.  
2. Corrupt JSON → default.  
3. `state_message` content starts with `Today's date: ` + ISO date.

No exact production-code replacement required beyond docstring (§16).

---

### 18. Deferred “food/drink noun sets” vs Unit 5 closed set
**COUNTERSIGN after §10c pack deferred rewrite.** Unit 5’s closed set is in-pack curriculum, not invention; tutor grounding rule “only pack material” already permits *pan/café/…*.

---

### 19. Pedagogy completeness vs research recs (not a Spanish accuracy gate)
**COUNTERSIGN as v0.4 delivery:** every unit has Input + ≥3 C + 2 SI + ≥1 T (counts: U1 T=2; U2–U6 T=1). Not “half of mechanical drills converted to SI” (still mostly P-items) — acceptable as first increment, not a countersign fail.

---

## Severity-ranked summary

| Sev | ID | Finding | Verdict |
|-----|-----|---------|---------|
| **Blocker** | B1 | Pack “next session” ≠ policy “next day”; due dates need calendar math | AMEND §2 |
| **Blocker** | B2 | Policy “whole state persists” ≠ harness durable subset | AMEND §16 |
| **Blocker** | B3 | Session-open: due review vs goal-setting unordered | AMEND §15c |
| **Medium** | M1 | Familiarity vs absolute key-reveal bullet | AMEND §12 |
| **Medium** | M2 | Review-fail / what counts as spaced success unspecified | AMEND §15b |
| **Medium** | M3 | T-6.1 criteria miss origin (and weak possession) scoring | AMEND §10d |
| **Medium** | M4 | *hermanos* production vs deferred family set | AMEND §10c |
| **Medium** | M5 | No tests for profile load/save | AMEND §17 |
| **Low** | L1 | U1 courtesy objective vs Input coverage | AMEND §5 |
| **Low** | L2 | U3 models *mi* in production keys | AMEND §6/7 |
| **OK** | — | Spanish of new dialogues/C/SI/T (accents, agreement, *ser/estar/tener*, numbers) | COUNTERSIGN |
| **OK** | — | Input-first, SI design, T criteria pattern, re-production rule, CLI save path, date injection | COUNTERSIGN |

---

## Overall verdict

**CONDITIONAL COUNTERSIGN — not final until B1–B3 are applied.**

The v0.4 pedagogy surface (Input blocks, C checks, SI items, T tasks, familiarity calibration, re-production, cross-session `review_schedule` + date injection) is **directionally correct** and, on Spanish form, **largely accurate and A1-appropriate**. I will **not** countersign the revision as ship-final while:

1. pack and policy disagree on the first spacing step,  
2. policy overclaims cross-session state vs what `load_profile` actually keeps, and  
3. session-open instructions contradict each other on due-item priority.

After exact replacements for **B1, B2, B3** (and preferably **M1–M4**), this reviewer will countersign pack v0.4 + policy v0.2 + persistence path as the closed pedagogy increment. **No REJECT** on the overall design; **no blind agreement** on consistency or durability wording.

— end countersign —
