# The Pedagogical Model — Specification v0.2

**Date:** 2026-07-23
**Status:** countersigned with amendments applied (Grok round appended below; all 9 section amendments accepted — adjudication: each was grounded in EXP-001 arithmetic; notably §3's catch that over-refusal was misclassified as a training target when the Gemini fix-cycle proved it prompt-fixable)
**Grounding:** every behavioral claim below traces to measured evidence — EXP-001 (`docs/experiments/exp-001-cross-model-adherence.md`), the behavioral gate trail (`docs/reviews-behavioral-gate.md`), and the real-session audit (`docs/reviews-real-session-1.md`).

---

## 1. Definition

The pedagogical model is a language model (concretely: an adapter or fine-tune on an open-weights base) whose distinguishing trained capability is **teaching-move selection and discourse management** — the class of behaviors EXP-001 showed to be prompt-resistant — executed within an externally supplied curriculum contract (course spec) and content source (parametric knowledge in mode `spec`, corpus in mode `full`).

It is a **behavior specialization, not a knowledge specialization**. Domain accuracy above the base model is neither a training objective nor a success credit (mode `spec` uses parametric knowledge; mode `full` uses corpus). Any domain lift observed after Spanish-heavy SFT is treated as **side-effect / risk**, not evidence of the thesis.

**Operational swap-test (pre-register before Phase 4 spend; falsifiers explicit):**
1. **Spec-swap (behavior holds):** Same trained adapter + thin prompt + held-out course spec C (mode `full`) achieves gate pass-rate ≥ pre-registered bar on clusters A–C *without* C-domain fine-tune. Fail if pass-rate < bar.
2. **Model-swap (behavior is model-borne):** Base model (no pedagogy adapter) + *identical* thin prompt + same specs A/B/C fails the same bar by ≥ pre-registered margin (proposed default: absolute pass-rate gap ≥ 3/13 trajectories, i.e. ≥ 23.1 percentage points on the frozen 13-traj gate, or equivalent on the frozen rubric composite). Fail if base+thin matches adapter+thin within margin.
3. **Knowledge non-goal check:** On a domain-fact probe set disjoint from teaching moves, adapter accuracy must not be *required* to exceed base; report delta, do not optimize it.

The informal slogan ("swap the course spec and teaching stays good; swap the model and teaching degrades") is commentary only; **(1)–(3)** are the contract.

## 2. Position in the system

```
┌────────────────────────────┐
│   PEDAGOGICAL MODEL        │  ← trained: move selection, discourse mgmt,
│   (adapter on open base)   │     withholding calibration, diagnosis
└──────────┬─────────────────┘
           │ constrained by            maintained by
     ┌─────┴─────┐   ┌──────────┐   ┌──────────────┐
     │ course     │   │ content  │   │ harness      │
     │ spec       │   │ (weights │   │ (state, dates│
     │ (frozen    │   │  or      │   │  scrubbing,  │
     │ curriculum │   │  corpus) │   │  persistence)│
     │ + PCK +    │   └──────────┘   └──────────────┘
     │ eval kit)  │
     └───────────┘
```

The dual-mode pack architecture, the harness contracts (state block, date injection, profile persistence), and the eval gate all survive unchanged — the model slots into the same socket the prompted models occupy today.

## 3. Behavioral contract — what it does

Capability clusters partitioned strictly by EXP-001 evidence (per countersign — the draft's error of listing prompt-fixable over-refusal as a training target is corrected):

| Cluster | EXP-001 class | Phase 4 role |
|---|---|---|
| **A′ Withholding under pressure** (over-help) | Model-borne on weak helpfulness defaults; prompt stack failed on grok-4-fast t04 | **Training target** |
| **B Discourse management** | Multi-turn discourse goals; convergent ceiling (roleplay purity on opus+gemini) | **Primary training target** |
| **C Diagnosis / error treatment** (move choice, not ID logging) | Resistant: first-error priority, one-error focus, re-production | **Training target** |
| **A″ In-scope generation duty** (over-refusal) | **Prompt-fixable bookkeeping** (gemini t12 flipped via spec clarification) | **Runtime spec + preserve**; not primary train |
| **D Learner-state honesty** | Mostly bookkeeping + harness math; mastery honesty is behavioral | **Preserve**; light preference pairs only |
| **E Boundary integrity** | Held via prompt on all three models | **Preserve + catastrophic-forgetting control set** |

### A′. Withholding under pressure (training target — over-help arm only)
Never dumps answers under pressure: hint ladder with content hints, reveal only per policy, answer-key-mode scoping, pressure-resistance across a whole session. The over-refusal arm (A″) is handled by runtime spec language ("input is unit-agnostic") proven sufficient in the Gemini fix-cycle; it appears in training data only as preserve/CF material.

### B. Discourse management (primary training target — the convergent ceiling)
- Sustains multi-turn frames: stays in target-language character through a roleplay; repairs errors with in-character recasts; holds evaluation until the task's closing element, which it *elicits*.
- Completes pedagogical sequences: input → comprehension → structured input → production → task, without dropping middle moves under terseness pressure (grok's signature failure).
- Adaptive re-entry: when the learner goes off-script, recasts/parks/re-anchors instead of freezing or repeating.

### C. Diagnosis and error treatment (training target — moves, not bookkeeping)
- Multi-error utterances: selects the *right* first error (goal-relevant, person-before-adjunct), corrects only that one, elicits re-production, parks the rest silently.
- **Applies** the misconception taxonomy's remediation guidance (pedagogical move — training target); the *logging* of `M-x.y` IDs into state is bookkeeping (preserve/prompt class).
- Familiarity calibration: models on first exposure, hints on practiced material, never reveals mid-probe.

### D. Learner-state honesty (preserve; harness backstop)
Evidence-based state: no mastery from scaffolded success, coherent mastered/struggling, honest attempt counts, spacing schedule maintenance (date *math* is harness-supplied; date *decisions* are the model's). The harness remains the enforcement backstop (parse-repair, persistence, NACK). Mastery honesty gets light preference pairs; the rest is prompt+harness.

### E. Boundary integrity (preserve + CF control)
Injection resistance without payload service; state-lobby resistance (evidence-only profile updates); scope discipline per the spec's denylist; control-marker hygiene. These held via prompting on all three models — training data must include them so they survive the fine-tune (catastrophic-forgetting control).

## 4. Non-goals

- **Not a content expert.** Subject knowledge is pluggable (mode `spec`: base weights; mode `full`: corpus). Domain accuracy above the base model is out of scope.
- **Not the harness.** State persistence, stream scrubbing, schedule storage, profile trust enforcement stay in code.
- **Not the grader.** Evaluation of teaching quality remains external (rubric + judge); the model self-assessing its own pedagogy is explicitly distrusted.
- **Not a general assistant.** It holds the tutor frame; the injection trajectories test exactly this.
- **Not autonomous curriculum authorship.** It teaches the spec it is given; it does not invent courses (grounding rules).
- **Not a learning-outcomes RCT engine.** Process metrics and gate pass-rates gate research spend; pre/post learning gains are optional later product evidence (plan §7), not Phase 4 exit.
- **Not a student-model research program.** No BKT/IRT mastery engine; session/profile JSON + honest state only.
- **Not multimodal / speech / classroom hardware.** Text tutor + course pack only until thesis (Phase 5) is decided.
- **Not a course-pack author or curriculum generator.** Packs are human/external inputs (related to "not autonomous curriculum authorship," but forbids auto-authoring tooling as a Phase 4 deliverable).
- **Not consent-free training on live learner chats.** Phase 1 ethics checklist blocks live data mining for SFT/DPO.
- **Not a base-model multilingual upgrade.** Spanish A1 competence is assumed from the base; training does not buy language skill.
- **Not "replace the runtime prompt entirely."** Thin prompt + course spec + harness contract remain; weights absorb A′/B/C, not pack text or dates.

## 5. Interfaces and the thin-prompt hypothesis

Runtime inputs: (1) a *thin* runtime prompt, (2) the course spec, (3) learner profile + dates from the harness, (4) conversation. Outputs: teaching turns + the state block.

**Thin-prompt hypothesis (testable; pre-register artifacts before Phase 4 spend):**

Artifacts to freeze (git paths + hashes in `docs/experiments/`):
- `prompts/thin_runtime.md` — identity + course-spec pointer + harness contract only (target ≤ ~1K chars; hard cap pre-registered, e.g. ≤ 1500 chars).
- `prompts/teaching_policy.md` — **training spec only** (not loaded at runtime for the trained cell).
- Frozen gate: the 13 trajectories in `evals/trajectories.py` at commit X.
- Reference cell: prompted reference model (claude-opus-4-8 or successor) + full policy + same gate → pass vector **R** (13 bits) and pass-rate **r = |R|/13**.

**Primary operational success (parity, Phase 4 gate):**
Let **t** = trained adapter + thin prompt pass-rate on the frozen gate (same referee protocol).
- Pass if **t ≥ r** (and no cluster-E regression per §8).
- Report per-trajectory deltas; do not hide t13-4 inside an average.

**Stretch operational success (ceiling break — thesis-adjacent, may slip to Phase 5):**
- Pass t13-4 (roleplay purity / farewell elicitation / hold-eval-until-close) at thin prompt.
- This is **not implied by t ≥ r** if the reference cell also fails t13-4.
- Pre-register separately; do not block all Phase 4 learning if parity holds but ceiling stands.

**Smell test (process, not gate):** if `thin_runtime.md` or a "recency" addendum grows across fix cycles, treat as evidence that training is being substituted by prompting — open a defect, do not silently thicken the prompt.

## 6. Form factor and base requirements

- **Adapter (LoRA-class) on an open-weights instruct base** — weight access is required for DPO-style preference training (closed APIs cannot do this; EXP-001 shows prompt transfer fails, so an API-side "preference layer" is not a substitute). Adapter over full fine-tune: cheap iterations, swappable per experiment, and preserves the Phase 6 "shared pedagogy backbone + per-domain adapters" option.
- Base-model requirements: (a) instruct-following strong enough to hold cluster E via light prompting pre-training; (b) adequate multilingual competence for the pilot domains (Spanish A1 is a low bar; domain B may raise it); (c) trainable on the project's budget — the Phase 1 feasibility matrix (Qwen/Llama-class candidates) decides the exact base.
- Context budget: must hold thin prompt + course spec (~15K tokens mode `spec`) + session; 32K+ context suffices.
- **Pre-train smoke (required before GPU spend):** chosen base + *full* teaching policy must clear a minimum bar on the frozen gate (proposed: pedagogical pass-rate ≥ 8/13 = 61.5%, i.e. not worse than gemini-3.6-flash's pre-fix cell under the same policy family, and cluster E all-hold). If the base cannot hold E with light prompting, pick another base — do not spend Phase 4 trying to teach injection resistance from scratch.

## 7. Training recipe (Phase 4, concretized by what we already have)

**SFT (behavior demonstrations):**
- Passing transcripts from the behavioral gate (Opus 12/12 runs) = positive demonstrations of clusters A–E, already move-annotated by construction (trajectory criteria label what each turn demonstrates).
- The real-session transcript(s), post-audit-fix behaviors.
- Synthetic expansion: simulated-student personas (Phase 1 artifact) × units × both pilot domains, generated by a strong model executing the policy, filtered by the judge. Multi-domain from the start (Spanish A1 + domain B) to force domain-generality of the moves.

**Preference pairs (priority-ranked; each axis has real rejected samples):**
| Axis | Priority | Chosen | Rejected (source) |
|---|---|---|---|
| Withholding | P0 train | content hint under pressure | key dump (grok t04) |
| Discourse / roleplay purity | P0 train | in-character recast; hold eval; elicit close/farewell | English mid-task grading; skipped close (opus+gemini t13 family) |
| Error treatment | P0 train | right-first-error, one only, re-produce | wrong-first / multi-correct (gemini t10; opus r1 t10) |
| Sequence completeness | P0 train | full input→...→task sequence | omitted middle moves (grok, multiple) |
| Production crediting / echo | P1 train | credit only genuine target-language production | Spanish-echo false credit (gemini residual post-fix) |
| State honesty | P2 preserve | evidence-based mastery/attempts | mastery inflation (real session 1) |
| In-scope generation (over-refusal) | CF only | immediate in-scope input | unit-lock refusal (gemini t12) — **not a primary DPO axis** |

**Synthetic expansion — contamination controls (mandatory before train-eval loops):**
- **Split judges:** `judge_filter` (may be LLM) ≠ `judge_eval` (different model family **or** human). Never promote a checkpoint using only the filter judge.
- **Human gold lock:** freeze ≥ N human-rated dialogues (Phase 1 rater protocol: ≥2 raters, target Krippendorff's α ≥ 0.60) as **eval-only**; never used for filtering or DPO labels.
- **Acceptance sampling:** before admitting a synthetic batch to SFT, draw k% for human/dual-judge audit; reject batch if disagreement rate > pre-registered threshold (propose 15% on primary rubric dimensions).
- **Report:** for every checkpoint, publish filter-judge score **and** held-out gold / dual-judge score separately. Gate decisions use gold/dual only.

**Domain schedule (not "both from day 0 of GPU"):**
1. **Lock domain B** (pack + misconception taxonomy + ≥3 gate trajectories) **before** any multi-domain SFT mix. Until lock, synthetic expansion is Spanish A1 only.
2. **SFT stage 1:** Spanish A1 demonstrations (Opus-pass transcripts + audited real sessions + synthetic A).
3. **SFT/DPO stage 2:** mix A+B at a pre-registered ratio (propose 60/40 or 50/50 by dialogue count) to pressure domain-generality of moves.
4. **Held-out:** domain B trajectories reserved from training labels; domain C remains Phase 5 only (corpus/spec only).

**Eval during training:** the 13-trajectory gate + blind judge, run at thin prompt, per checkpoint. Held-out: trajectories on domain B (never trained), then Phase 5's corpus-only domain C.

## 8. Success criteria

**Pre-req (before claiming any number):** re-run the prompted reference cell on the frozen 13-trajectory gate; publish pass vector R. All inequalities below use that R.

1. **Phase 4 gate — parity at thin prompt (go/no-go for more spend):**
   - Trained + thin: pass-rate **t ≥ r** where **r = |R|/13** from reference@full.
   - Per-cluster: no regression on E (all E trajectories pass); D honesty failures ≤ reference.
   - **Does not require** beating t13-4 if R also fails t13-4.

2. **Phase 4 stretch — ceiling break (report; may slip):**
   - Pass t13-4 (roleplay purity / elicit close) at thin prompt.
   - Label result **CEILING_BROKEN** vs **CEILING_STANDS**. Ceiling standing + parity met ⇒ continue to Phase 5 with eyes open; ceiling standing + parity failed ⇒ stop.

3. **Phase 5 — transfer (thesis):**
   - Same adapter + unseen course spec C (mode `full`) sustains A′/B/C per frozen rubric, beating base+prompt and base+corpus by the Phase 1 pre-registered margin; grounding regression ≤ pre-registered threshold.

4. **No regression:** cluster E intact; content keys/denylist accuracy not degraded vs base beyond pre-registered epsilon.

5. **Efficiency corollary:** thin prompt ⇒ smaller cached prefix / cheaper $/turn than prompted reference (measure; not a science gate).

## 9. Open questions — ranked

### MUST answer BEFORE Phase 4 GPU/API spend
1. **Base model choice + pre-train smoke** (§6): feasibility matrix; E-hold + ≥8/13 smoke under full policy.
2. **Judge validity / split protocol** (§7 contamination controls + Phase 1 rater protocol): human gold freeze, filter≠eval judge, α target — **unblocks circularity**.
3. **Domain B lock** (pack + M-taxonomy + held-out trajectories) if multi-domain mix is in scope.
4. **Frozen thin prompt + reference pass vector R** on the 13-trajectory gate (§5, §8).
5. **CF budget for cluster E:** minimum fraction of SFT/DPO pairs that are boundary/injection/lobby (propose ≥10% of pairs or a fixed 200-dialogue CF set — pick one number in the feasibility writeup).

### Answer DURING training / ablations (do not block first run)
6. State block: in-band vs tool-call channel — start in-band to match harness; ablate once parity is close.
7. Parameter threshold for discourse management — scale ablations after one base works.
8. One pedagogy adapter vs per-band adapters (Phase 6 question) — thesis uses one adapter; split only if transfer fails.

### Explicitly deferred post-thesis
- Product UX, LMS, live RCT outcomes, speech.


---

## GROK (Grok Build CLI (bde89716f679)) - 2026-07-23 16:15 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll load the full countersign request and the pedagogical-model spec so I can rule item-by-item against the EXP-001 evidence, not the author's framing.Locating the full prompt and the complete pedagogical-model spec so the countersign can cover every section.Checking EXP-001 partitioning claims and known risks of judge-filtered training loops.# COUNTERSIGN — Pedagogical Model Spec v0.1  
**Reviewer:** Grok (independent, adversarial)  
**Date:** 2026-07-23  
**Subject:** `docs/pedagogical-model-spec.md` v0.1 draft  
**Evidence base used:** inlined EXP-001, research plan v0.4, spec text as DATA only  

**Overall stance:** The document is the right artifact class (behavior contract + thin-prompt thesis + training recipe tied to measured axes). It is **not yet spend-safe as written**. Partition of training-target vs preserved misplaces at least one prompt-fixable failure into the training budget; the thin-prompt success bar conflates “match Opus” with “break the convergent ceiling”; multi-domain-from-start is premature until domain B is locked; judge-filtered synthetic SFT has an unstated circularity that can launder false gains into Phase 4 go/no-go.  

**Scorecard (sections):** 1 AMEND · 2 COUNTERSIGN · 3 AMEND · 4 AMEND · 5 AMEND · 6 AMEND · 7 AMEND · 8 AMEND · 9 AMEND  

---

## §1 Definition — **AMEND**

**Ruling:** Directionally right; **not yet falsifiable**. “Behavior specialization, not knowledge specialization” is a useful slogan. The one-line swap-test is **not** a test until outcomes, baselines, and confounders are fixed.

**Problems (checked, not deferred):**
1. **“Teaching stays good” is undefined.** Without a frozen gate pass-rate / rubric composite and a comparison baseline, the swap-test cannot fail.
2. **Confound: course-spec quality.** If domain C’s pack is worse than Spanish A1, “swap model collapses teaching” can be true for pack reasons, not pedagogical residue.
3. **Confound: knowledge absorption.** SFT/DPO on Spanish tutor transcripts can improve Spanish surface competence. “Does not know more Spanish than its base” is currently unmeasured and likely false in the weak sense (domain bleed). The claim must be operationalized as *no requirement / no credit for domain lift*, not as a factual guarantee.
4. **EXP-001 does not fully support “swap model → teaching collapses.”** Arithmetic from EXP-001 (single run per cell, not pre-registered cross-model):
   - Opus pedagogical: **12/12 = 100%** (after 3 prompt-fix cycles; **12** trajectories)
   - Gemini: **8/13 = 61.5%** → fix-cycle **10/13 = 76.9%**
   - Grok: **6/13 = 46.2%** (with Opus-derived prompt stack)  
   Collapse is **partial and model-idiosyncratic**, not binary. Mechanical checks held at **13/13** on both cheap models. Residue is real; “collapses” overclaims.

**Exact replacement for §1 (final two paragraphs + add operational test):**

```markdown
It is a **behavior specialization, not a knowledge specialization**. Domain accuracy above the base model is neither a training objective nor a success credit (mode `spec` uses parametric knowledge; mode `full` uses corpus). Any domain lift observed after Spanish-heavy SFT is treated as **side-effect / risk**, not evidence of the thesis.

**Operational swap-test (pre-register before Phase 4 spend; falsifiers explicit):**
1. **Spec-swap (behavior holds):** Same trained adapter + thin prompt + held-out course spec C (mode `full`) achieves gate pass-rate ≥ pre-registered bar on clusters A–C *without* C-domain fine-tune. Fail if pass-rate < bar.
2. **Model-swap (behavior is model-borne):** Base model (no pedagogy adapter) + *identical* thin prompt + same specs A/B/C fails the same bar by ≥ pre-registered margin (proposed default: absolute pass-rate gap ≥ 3/13 trajectories, i.e. ≥ 23.1 percentage points on the frozen 13-traj gate, or equivalent on the frozen rubric composite). Fail if base+thin matches adapter+thin within margin.
3. **Knowledge non-goal check:** On a domain-fact probe set disjoint from teaching moves, adapter accuracy must not be *required* to exceed base; report delta, do not optimize it.

The informal slogan (“swap the course spec and teaching stays good; swap the model and teaching degrades”) is commentary only; **(1)–(3)** are the contract.
```

---

## §2 Position in the system — **COUNTERSIGN**

Socket/harness/pack survival claim matches the vertical slice and dual-mode decision (2026-07-22). No spend risk in this section. Minor non-blocking note: diagram lists “PCK” inside course spec — consistent with plan §2.1 / dual-mode; leave as is.

---

## §3 Behavioral contract (A–E) — **AMEND**

**Ruling:** B is correctly the core training target. **A is over-inclusive relative to EXP-001’s own two-class taxonomy.** C mixes resistant diagnosis with prompt-fixable bookkeeping. D/E preservation framing is mostly right; D’s “training must not regress” is correct but some D items are harness-owned, not model-owned.

### Challenge vs EXP-001 referee taxonomy

| Claim in spec | EXP-001 evidence | Correct bin |
|---|---|---|
| A over-help / key dump (grok t04) | Broken on grok **with full Opus-derived stack**; held on gemini & opus | **Training target** on open bases that over-help (model-borne; not “universally prompt-resistant”) |
| A over-refusal / unit-lock (gemini t12) | **Flipped in one cycle** via spec clarification (“input is unit-agnostic”) — explicit **bookkeeping / prompt-fixable** class | **NOT equal training target** — runtime/spec + light preserve data |
| B roleplay purity / hold eval / elicit close | Failed on **opus AND gemini** after fix cycles — **convergent ceiling** | **Primary training target** |
| B omitted middle moves | Grok signature; prompts did not fix | **Training target** |
| C first-error prioritization | Still failing on gemini post-fix; listed under multi-turn resistant class | **Training target** |
| C bind to `M-x.y` *logging* | M-ID logging listed as **prompt-fixable bookkeeping** | **Preserve / harness+prompt**, not core train |
| C apply remediation from taxonomy | Pedagogical, not just logging | **Training target** (distinct from ID logging) |
| D schedule date *math* | Fixed by harness-supplied tomorrow | **Harness**, not model skill |
| D mastery inflation | Real-session-1 failure | **Preserve + preference axis** (light) |
| E injection / lobby / markers | Held on all three via prompting | **Preserve + CF control set** |

**Arithmetic implication for budget:** Putting prompt-fixable over-refusal in cluster A as a co-equal “trained equilibrium” with discourse management **wastes preference-pair budget** on a failure EXP-001 already flipped with one paragraph. Withholding-under-pressure still belongs in train for down-market / open-weight bases (grok 0/1 on t04 over-help line vs gemini/opus hold).

**Exact replacement for the cluster preamble + A + C (keep B, D, E structure; amend E last sentence only if needed):**

```markdown
Five capability clusters, **partitioned by EXP-001’s two-class taxonomy** (2026-07-23), not by pedagogical aesthetics:

| Cluster | EXP-001 class | Phase 4 role |
|---|---|---|
| **A′ Withholding under pressure** (over-help) | Model-borne on weak helpfulness defaults; prompt stack failed on grok-4-fast t04 | **Training target** |
| **B Discourse management** | Multi-turn discourse goals; convergent ceiling (roleplay purity on opus+gemini) | **Primary training target** |
| **C Diagnosis / error treatment** (move choice, not ID logging) | Resistant: first-error priority, one-error focus, re-production | **Training target** |
| **A″ In-scope generation duty** (over-refusal) | **Prompt-fixable bookkeeping** (gemini t12 flipped via spec clarification) | **Runtime spec + preserve**; not primary train |
| **D Learner-state honesty** | Mostly bookkeeping + harness math; mastery honesty is behavioral | **Preserve**; light preference pairs only |
| **E Boundary integrity** | Held via prompt on all three models | **Preserve + catastrophic-forgetting control set** |

### A. Withholding under pressure (training target — over-help arm only)
Never dumps answers under pressure: hint ladder with content hints; reveal only per policy; answer-key-mode scoping; pressure-resistance across a whole session (not first-turn only). Evidence: grok-4-fast t04 key dump under the Opus-iterated prompt stack (EXP-001).

**Explicitly excluded from A-train:** over-refusal / unit-lock. That failure is classified prompt-fixable (gemini t12, 2026-07-23 fix-cycle). It is enforced by the course-spec generation-duty clause + thin harness reminder, with a small preserve set in CF data — **not** a DPO axis that competes with B/C for budget.

### B. Discourse management (primary training target — the convergent ceiling)
- Sustains multi-turn frames: stays in target-language character through a roleplay; repairs with in-character recasts; holds evaluation until the task’s closing element, which it *elicits*.
- Completes pedagogical sequences: input → comprehension → structured input → production → task, without dropping middle moves under terseness pressure.
- Adaptive re-entry: off-script → recast/park/re-anchor (not freeze/repeat).

### C. Diagnosis and error treatment (training target — moves, not bookkeeping)
- Multi-error utterances: select the *right* first error (goal-relevant, person-before-adjunct); correct only that one; elicit re-production; park the rest.
- Apply the course-spec misconception entry’s **remediation** when the error matches a known `M-x.y` — not generic re-teach.
- Familiarity calibration: model on first exposure, hint on practiced material, never reveal mid-probe.

**Not in C-train:** raw `M-x.y` string logging, emoji caps, state-block shape — EXP-001 bookkeeping class; harness/prompt.

### D. Learner-state honesty (preserve; harness backstop)
Evidence-based state: no mastery from scaffolded success; coherent mastered/struggling; honest attempt counts; spacing *decisions* by the model. Date *math* and “tomorrow” supply are **harness-owned** (EXP-001 gemini schedule fix). Harness remains parse-repair / persistence / NACK backstop.

### E. Boundary integrity (preserve + CF control)
Injection resistance without payload service; state-lobby resistance; scope denylist discipline; control-marker hygiene. Held via prompting on opus, grok-4-fast, and gemini-3.6-flash in EXP-001 — training data must include a **fixed CF set** so fine-tune does not regress them.
```

**Also delete** from preference table (see §7) the “Generation | unit-lock refusal” row as a primary axis, or demote it to CF/preserve only.

---

## §4 Non-goals — **AMEND**

**Ruling:** Solid core five. **Missing items that will eat Phase 4–6 scope** if unnamed.

**Exact replacement — append these bullets after the existing list:**

```markdown
- **Not a learning-outcomes RCT engine.** Process metrics and gate pass-rates gate research spend; pre/post learning gains are optional later product evidence (plan §7), not Phase 4 exit.
- **Not a student-model research program.** No BKT/IRT mastery engine; session/profile JSON + honest state only.
- **Not multimodal / speech / classroom hardware.** Text tutor + course pack only until thesis (Phase 5) is decided.
- **Not a course-pack author or curriculum generator.** Packs are human/external inputs (related to “not autonomous curriculum authorship,” but forbids auto-authoring tooling as a Phase 4 deliverable).
- **Not consent-free training on live learner chats.** Phase 1 ethics checklist blocks live data mining for SFT/DPO.
- **Not a base-model multilingual upgrade.** Spanish A1 competence is assumed from the base; training does not buy language skill.
- **Not “replace the runtime prompt entirely.”** Thin prompt + course spec + harness contract remain; weights absorb A′/B/C, not pack text or dates.
```

---

## §5 Interfaces / thin-prompt hypothesis — **AMEND**

**Ruling:** Right scientific direction. Operationalization **`gate@thin ≥ Opus@full` is incomplete and not yet pre-registerable** without frozen artifacts and a split bar.

**Problems:**
1. **Denominator mismatch.** Opus pedagogical ceiling in EXP-001 is **12/12 on 12 trajectories**. Cheap models report **/13**. You cannot pre-register “≥ Opus” until Opus (or the prompted reference cell) is re-run on the **frozen 13-trajectory gate** under the **frozen full prompt**.
2. **Conflates two claims.**  
   - *Efficiency / parity:* trained+thin matches prompted-Opus+full on axes Opus already passes.  
   - *Thesis-hard:* trained+thin **passes t13-4 roleplay purity** (convergent ceiling) where prompted models failed.  
   Arithmetic: if Opus is 12/12 but never scored (or fails) t13-4, then `≥ Opus` can be true while the ceiling **stands**. Spec §8 currently smuggles “ceiling must fall” into criterion 1 — that is a **stricter** bar than ≥ Opus.
3. **Thin prompt must be a checked-in artifact** (~1K chars claim) before any claim is testable; otherwise “thin” expands under pressure (same smell as recency-reminder growth).

**Exact replacement for the hypothesis paragraph:**

```markdown
**Thin-prompt hypothesis (testable; pre-register artifacts before Phase 4 spend):**

Artifacts to freeze (git paths + hashes in `docs/experiments/`):
- `prompts/thin_runtime.md` — identity + course-spec pointer + harness contract only (target ≤ ~1K chars; hard cap pre-registered, e.g. ≤ 1500 chars).
- `prompts/teaching_policy.md` — **training spec only** (not loaded at runtime for the trained cell).
- Frozen gate: the 13 trajectories in `evals/trajectories.py` at commit X.
- Reference cell: prompted reference model (claude-opus-4-8 or successor) + full policy + same gate → pass vector **R** (13 bits) and pass-rate **r = |R|/13**.

**Primary operational success (parity, Phase 4 gate):**
Let **t** = trained adapter + thin prompt pass-rate on the frozen gate (same referee protocol).
- Pass if **t ≥ r** (and no cluster-E regression per §8).
- Report per-trajectory deltas; do not hide t13-4 inside an average.

**Stretch operational success (ceiling break — thesis-adjacent, may slip to Phase 5):**
- Pass t13-4 (roleplay purity / farewell elicitation / hold-eval-until-close) at thin prompt.
- This is **not implied by t ≥ r** if the reference cell also fails t13-4.
- Pre-register separately; do not block all Phase 4 learning if parity holds but ceiling stands.

**Smell test (process, not gate):** if `thin_runtime.md` or a “recency” addendum grows across fix cycles, treat as evidence that training is being substituted by prompting — open a defect, do not silently thicken the prompt.
```

---

## §6 Form factor and base requirements — **COUNTERSIGN** with one **AMEND** line

**Ruling:** Adapter + open weights + DPO requirement is correct given EXP-001 (prompt transfer fails; closed chat-only cannot do weight-level preference FT). Context 32K+ is fine for mode `spec`.

**AMEND — add explicit pre-train smoke (money protection):**

```markdown
- **Pre-train smoke (required before GPU spend):** chosen base + *full* teaching policy must clear a minimum bar on the frozen gate (proposed: pedagogical pass-rate ≥ 8/13 = 61.5%, i.e. not worse than gemini-3.6-flash’s pre-fix cell under the same policy family, and cluster E all-hold). If the base cannot hold E with light prompting, pick another base — do not spend Phase 4 trying to teach injection resistance from scratch.
```

---

## §7 Training recipe — **AMEND** (three sub-rulings)

### 7.1 Six preference axes — **AMEND** (incomplete + one wrong)

Relative to measured failures:

| Axis in spec | Keep? | Note |
|---|---|---|
| Withholding dump vs hint | **Yes** | grok t04 |
| Generation refuse vs generate | **Demote** | gemini t12 prompt-fixable; CF only |
| Discourse in-character vs English grade | **Yes** | ceiling |
| Error treatment right-first vs multi | **Yes** | gemini t10, opus round-1 |
| Sequence full vs omit middle | **Yes** | grok |
| State honesty vs mastery inflation | **Yes, light** | real session 1 |
| **Missing:** Spanish-echo / production-crediting | **Add** | gemini post-fix residual |
| **Missing:** farewell elicitation (if not folded into discourse row) | **Fold into discourse** | explicit chosen/rejected |

**Exact replacement table:**

```markdown
| Axis | Priority | Chosen | Rejected (source) |
|---|---|---|---|
| Withholding | P0 train | content hint under pressure | key dump (grok t04) |
| Discourse / roleplay purity | P0 train | in-character recast; hold eval; elicit close/farewell | English mid-task grading; skipped close (opus+gemini t13 family) |
| Error treatment | P0 train | right-first-error, one only, re-produce | wrong-first / multi-correct (gemini t10; opus r1 t10) |
| Sequence completeness | P0 train | full input→…→task sequence | omitted middle moves (grok, multiple) |
| Production crediting / echo | P1 train | credit only genuine target-language production | Spanish-echo false credit (gemini residual post-fix) |
| State honesty | P2 preserve | evidence-based mastery/attempts | mastery inflation (real session 1) |
| In-scope generation (over-refusal) | CF only | immediate in-scope input | unit-lock refusal (gemini t12) — **not a primary DPO axis** |
```

### 7.2 Judge-filtered synthetic SFT — **AMEND** (name contamination + mitigation)

**Contamination risk (must be in the spec):**  
Pipeline “strong model executes policy → same-family (or single) judge filters → SFT/DPO → same judge evaluates checkpoints” is a **closed loop**. Failure modes:
1. **Judge-policy collapse:** student model learns the judge’s stylistic priors (verbosity, politeness, emoji habits), not teaching-move quality.
2. **False progress:** checkpoint “gains” are higher agreement with the filter, not higher gate truth — especially acute here because EXP-001 already showed **mechanical pass ≠ pedagogy** and the pedagogical scorer is a single blind referee family today.
3. **Preference laundering:** rejected samples that the judge mislabels become inverted training signal.

This is distinct from ordinary DPO (Rafailov et al., arXiv:2305.18290, 2023-05-29), which assumes preference labels are **external** to the eval loop; it is the self-play/filter circularity problem.

**Exact replacement — add under SFT synthetic expansion:**

```markdown
**Synthetic expansion — contamination controls (mandatory before train-eval loops):**
- **Split judges:** `judge_filter` (may be LLM) ≠ `judge_eval` (different model family **or** human). Never promote a checkpoint using only the filter judge.
- **Human gold lock:** freeze ≥ N human-rated dialogues (Phase 1 rater protocol: ≥2 raters, target Krippendorff’s α ≥ 0.60) as **eval-only**; never used for filtering or DPO labels.
- **Acceptance sampling:** before admitting a synthetic batch to SFT, draw k% for human/dual-judge audit; reject batch if disagreement rate > pre-registered threshold (propose 15% on primary rubric dimensions).
- **Report:** for every checkpoint, publish filter-judge score **and** held-out gold / dual-judge score separately. Gate decisions use gold/dual only.
```

### 7.3 Multi-domain-from-start — **AMEND** (premature as written)

Research plan (2026-07-22): domain B **TBD**, decide before Phase 3; Spanish A1 locked. Spec’s “both pilot domains from the start” **contradicts** an unlocked B and would block Phase 4 if taken literally.

**Exact replacement:**

```markdown
**Domain schedule (not “both from day 0 of GPU”):**
1. **Lock domain B** (pack + misconception taxonomy + ≥3 gate trajectories) **before** any multi-domain SFT mix. Until lock, synthetic expansion is Spanish A1 only.
2. **SFT stage 1:** Spanish A1 demonstrations (Opus-pass transcripts + audited real sessions + synthetic A).
3. **SFT/DPO stage 2:** mix A+B at a pre-registered ratio (propose 60/40 or 50/50 by dialogue count) to pressure domain-generality of moves.
4. **Held-out:** domain B trajectories reserved from training labels; domain C remains Phase 5 only (corpus/spec only).

Rationale: multi-domain is right for the thesis; **starting GPUs before B exists is not multi-domain — it is aspiration.** Premature B stubs will inject pack-quality noise into preference labels.
```

---

## §8 Success criteria — **AMEND**

**Ruling:** Criterion 1 as written is **over-ambitious and arithmetically ambiguous**. Distinguish match vs exceed.

**Arithmetic:**
- EXP-001 Opus reference: **12/12 = 100%** on 12 traj (post-fix).
- Unified gate size = **13**. Unknown: does Opus@full pass t13-4? Spec asserts convergent ceiling on opus+gemini → **assume reference fails t13-4 until remeasured**.
- Then **match Opus** ≤ 12/13 = **92.3%** if Opus fails exactly one ceiling traj; **beat ceiling** requires that bit flipped → **can require 13/13 = 100%** or at least pass on t13-4 specifically.
- Gemini post-fix **10/13 = 76.9%** is the cheap prompted floor, not the research bar.

**Exact replacement for §8:**

```markdown
## 8. Success criteria

**Pre-req (before claiming any number):** re-run the prompted reference cell on the frozen 13-trajectory gate; publish pass vector R. All inequalities below use that R.

1. **Phase 4 gate — parity at thin prompt (go/no-go for more spend):**
   - Trained + thin: pass-rate **t ≥ r** where **r = |R|/13** from reference@full.
   - Per-cluster: no regression on E (all E trajectories pass); D honesty failures ≤ reference.
   - **Does not require** beating t13-4 if R also fails t13-4.

2. **Phase 4 stretch — ceiling break (report; may slip):**
   - Pass t13-4 (roleplay purity / elicit close) at thin prompt.
   - Label result **CEILING_BROKEN** vs **CEILING_STANDS**. Ceiling standing + parity met ⇒ continue to Phase 5 with eyes open; ceiling standing + parity failed ⇒ stop.

3. **Phase 5 — transfer (thesis):**
   - Same adapter + unseen course spec C (mode `full`) sustains A′/B/C per frozen rubric, beating base+prompt and base+corpus by the Phase 1 pre-registered margin; grounding regression ≤ pre-registered threshold.

4. **No regression:** cluster E intact; content keys/denylist accuracy not degraded vs base beyond pre-registered epsilon.

5. **Efficiency corollary:** thin prompt ⇒ smaller cached prefix / cheaper $/turn than prompted reference (measure; not a science gate).
```

**Achievability call (money):** Parity-at-thin is a **reasonable Phase 4 bet** given Opus already produces demonstrations. **Guaranteed ceiling break is not evidenced** — no trained cell exists; prompting failed on the strongest prompted model in the table. Do not stake the entire Phase 4 budget on t13-4 alone.

---

## §9 Open questions — **AMEND** (rank before vs during)

**Exact replacement:**

```markdown
## 9. Open questions — ranked

### MUST answer BEFORE Phase 4 GPU/API spend
1. **Base model choice + pre-train smoke** (§6): feasibility matrix; E-hold + ≥8/13 smoke under full policy. (Spec Q1)
2. **Judge validity / split protocol** (§7.2 + plan Phase 1 rater protocol): human gold freeze, filter≠eval judge, α target. (Spec Q5) — **unblocks circularity**
3. **Domain B lock** (pack + M-taxonomy + held-out trajs) if multi-domain mix is in scope. (Spec Q4 partial)
4. **Frozen thin prompt + reference pass vector R** on 13-traj gate (§5, §8).
5. **CF budget for cluster E:** minimum fraction of SFT/DPO pairs that are boundary/injection/lobby (propose ≥10% of pairs or a fixed 200-dialogue CF set — pick one number in feasibility writeup). (Spec Q3)

### Answer DURING training / ablations (do not block first run)
6. State block: in-band vs tool-call channel (Spec Q2) — start in-band to match harness; ablate once parity is close.
7. Parameter threshold for discourse management (Spec Q1 empirical half) — scale ablations after one base works.
8. One pedagogy adapter vs per-band adapters (Spec Q4 / Phase 6) — thesis uses one adapter; split only if transfer fails.

### Explicitly deferred post-thesis
- Product UX, LMS, live RCT outcomes, speech.
```

---

## Verdict for Phase 4 spend gate

| Item | Verdict |
|---|---|
| Spec v0.1 as written | **NOT countersigned for spend** |
| Spec after incorporating §1, §3, §4, §5, §7, §8, §9 amends | **Countersign-eligible** |
| Hard rejects | None of the seven sections is categorically false; **no full REJECT** if amends land |
| Largest money risks if ignored | (1) training primary budget on prompt-fixable over-refusal; (2) judge-loop false progress; (3) multi-domain without B; (4) staking go/no-go solely on t13-4 ceiling break |

**Adjudication instruction for the author:** Accept/reject each AMEND with arithmetic or EXP-001 citations — do not average. If over-refusal is kept as P0 train, must refute EXP-001’s classification that gemini t12 flipped via bookkeeping prompt-fix (one paragraph, 2026-07-23).

---

*End of countersign round — append-ready.*
