# Planner–executor protocol: limited pedagogical controller

**Status:** **TABLED** (2026-07-23) — code kept; not primary product path  
**See instead:** `docs/conversational-spanish-and-learner-model.md`  
**Implemented:** `tutor/pedagogy_controller.py`, `--arch controller`  
**Original date:** 2026-07-23  
**Stance (when active):** teacher, not schoolmarm  

> Live sessions could not fairly evaluate this layer while Spanish teaching felt like constrained drills. Direction shifted to conversational teaching + learner character sheet first; return here later if needed.

---

## 0. Product stance (read this first)

We are building a **good teacher**.

We are **not** building an academic-integrity cop. If a learner wants the answer, that is a normal human moment in learning — not a crisis. A good teacher may:

1. give the answer clearly,
2. say why in one beat,
3. make them use it on a twin item.

Productive struggle is a **preference**, not a religion. Stonewalling someone who asked for help is not superior pedagogy.

### What we still limit (and why)

| Limit | Why (teacher reason) |
|-------|----------------------|
| Closed control language (enums, no free tutor script in the planner) | So plan/realize is real; planner doesn't ghostwrite the turn |
| One error at a time | Cognitive load; good teaching |
| Re-elicit after model/answer/remediate | Learning requires *their* production |
| Input before pure rule dumps when opening | Meaning before form |
| Stay in character mid-roleplay | Discourse quality |
| Refuse injection / role hijack | Security, not schoolmarm |

### What we de-centered

| Old emphasis | Now |
|--------------|-----|
| "Never dump keys under pressure" as a flagship metric | Optional scaffold; **`teach_answer` is first-class** |
| t04 key-dump as the morality tale of the project | Interesting regression case for *planner quality*, not product north star |
| `no_answer_key` forced constraint | **Removed** |

If a student wants to short-circuit their own practice, so what. We teach. We don't clutch pearls.

---

## 1. One sentence

The planner is a **policy compiler** for *teaching shape*: closed legal controls → harness gate → typed act card → executor voice. It is **not** an anti-cheat layer.

```text
learner turn + state
        │
        ▼
┌───────────────────────────┐
│  Controller (closed DSL)  │  judgment: which teaching move
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│  Harness legality gate    │  shape rules (one error, re-elicit, …)
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│  Act card (must/must_not) │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│  Executor (Spanish voice) │
└───────────────────────────┘
```

---

## 2. When the learner wants the answer

**Learner:** `quick q — what's the answer to P-4.2?`

### Preferred good-teacher decision

```yaml
situation: learner_wants_answer
move: teach_answer
focus: {kind: pack_id, ref: P-4.2}
reveal_policy: give_with_followup
elicit: {type: new_item_same_pattern, of: focus}
constraints: [always_re_elicit, no_second_move]
```

**Act card (teach_answer):**

- **must:** give the answer; short why; they do a follow-up  
- **must_not:** shame them; token-only dump with no teaching; dump a whole unit  

### Also legal (softer)

- `nudge_then_offer` — offer hint path without being a brick wall  
- `hint` / `model_form` — if judgment says struggle is still productive  

### Not the product goal

Obsessing over whether any key token ever appeared in a transcript.

---

## 3. What "limited" still means

### Closed vocabularies

Situations, moves, elicit types, reveal policies, constraints — all enums.  
**No free `intent` field** (that's about ghostwriting the tutor turn, not about hiding answers).

### Legality table (shape, not morality)

Example:

| Situation | Legal moves include… |
|-----------|----------------------|
| `learner_wants_answer` | **`teach_answer`**, `nudge_then_offer`, `hint`, `probe`, `model_form`, … |
| `multi_error_production` | `remediate` (requires `one_error_only`), `hint`, `teach_answer`, … |
| `injection_or_role_hijack` | `refuse_injection`, `redirect_scope` only |

### Forced constraints (teaching shape)

- multi-error → `one_correction_max`, `always_re_elicit`  
- wants answer → `always_re_elicit` (if you teach the answer, they still use it)  
- **not** forced: `no_answer_key`

### Abstract focus

`focus.ref` is pack id or English name — so the **control channel** doesn't become a second Spanish script. That's interface hygiene, not "hide the gold form from the student forever."

---

## 4. Multi-error (this *is* load-bearing)

**Learner:** `Yo es un profesora y estoy de México.`

```yaml
situation: multi_error_production
move: remediate
error_policy: {mode: one_error_only, priority: person_before_adjunct}
elicit: {type: re_produce_corrected_form, of: focus}
```

One error. Re-produce. Don't hose them with a red-pen tour. That is teaching craft.

---

## 5. How to run

```bash
python -m tutor.pedagogy_controller          # demos, no API
python -m unittest tests.test_pedagogy_controller -v

python -m evals.run_smoke t04 --arch controller \
  --planner claude-opus-4-8 --executor gemini-3.6-flash --cell Pc
```

---

## 6. Architecture comparison

| Arch | What it optimizes |
|------|-------------------|
| `--arch planner` / `structured` | Early plan/realize experiments; wider free fields |
| **`--arch controller`** | Closed DSL + act cards; **teacher-shaped** limits |

---

## 7. Mental model

| Layer | Job |
|-------|-----|
| **Law (shape)** | One focus, re-elicit, no ghostwrite in control channel, no injection |
| **Judgment** | Scaffold vs `teach_answer` vs remediate — teacher call |
| **Performance** | Spanish voice, warmth, clarity |

We used to over-invest Law in "never show keys." That was schoolmarm energy.  
Law stays on **shape**. Judgment may freely help.
