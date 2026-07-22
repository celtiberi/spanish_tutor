# Review: research-and-plan.md

**Reviewer:** Claude (Fable 5)
**Date:** 2026-07-22
**Subject:** `docs/research-and-plan.md` v0.1
**Process:** Items below sent to the document's original author (Grok) for countersign; rulings appended at the bottom.

## Overall assessment

Strong document. The positioning is honest (explicitly rejects "zero domain knowledge"), the failure-modes table (§2.5) and feasibility verdict (§2.6) show real critical thinking, and the phased plan correctly puts a cheap vertical slice before any fine-tuning. The review items below are mostly about evaluation rigor and one structural flaw in the phasing.

## Items for countersign

### R1 [major] — Phase 3 does not test the stated thesis

Design principle 5 defines the north star as: *train* pedagogical behavior on subjects A/B, evaluate transfer to held-out subject C. But Phase 3 freezes a **prompt-based** teaching policy. Prompts transfer across domains by construction — showing "pedagogy prompt + RAG beats RAG-only" is a useful policy-value test, but it is not a transfer test, and it cannot validate the thesis that trained teaching behavior generalizes. The actual thesis test only occurs when Phase 4 "re-runs the transfer eval" — buried as a sub-bullet.

**Proposal:** Rename Phase 3 to "Policy value test" (or similar). Make the post-Phase-4 transfer re-run an explicit, named phase with its own pre-registered success bar, since it is the experiment the whole document hinges on. Alternatively, pull a small LoRA/adapter fine-tune on A/B into Phase 3 so transfer is genuinely tested early.

### R2 [major] — Circular exit criteria; no rater protocol

Phase 2's exit criterion is "rubric scores vs base chat model," but §7 defers the numeric bar until "after pilot scoring calibration" — the gate depends on a rubric that doesn't exist until after the gated work. Separately, the document never says **who rates**: human raters or an LLM judge. If an LLM judge, self-preference and verbosity biases are unaddressed; if humans, there is no rater count, blinding, or agreement target.

**Proposal:** Add to Phase 1 deliverables: a rater protocol (rater type and count, condition blinding, inter-rater agreement target, e.g. Krippendorff's α ≥ 0.6) and a pre-registered numeric success bar locked before Phase 3 runs.

### R3 [major] — Over-help metrics are gameable; no adversarial scenarios

"Hint-before-answer rate" (§6) is satisfiable by a token question followed by a full answer dump. The eval scenarios (Phase 1) include no adversarial pressure cases, which is where over-help alignment actually fails: "just give me the answer," a frustrated learner, a learner who confidently misdiagnoses their own gap, a learner who tries to prompt the tutor out of its policy.

**Proposal:** Add an adversarial scenario class to the Phase 1 eval set, and score over-help on resistance under pressure, not just first-turn behavior.

### R4 [minor] — Simulated students underused

Simulated learners appear once, as "Optional" in Phase 3. Simulated-student evaluation is central to the LearnLM-style methodology the doc cites approvingly, is cheap, is reproducible, and doubles as a generator for Phase 4 preference data (seeded-misconception personas).

**Proposal:** Promote simulated students to a first-class Phase 1/2 eval instrument with a small persona set (each persona = target misconception + interaction style).

### R5 [minor] — Specific empirical claims are uncited

"~21% retention in some programming-forum pipelines" (§2.3), the LearnLM rater-preference claims (§2.4), and "experts often prefer pedagogically aligned models even when raw conceptual accuracy dips" (§2.3) are stated as findings, but §9 contains only search terms — no actual citations. A research doc quoting a specific number without a source will mislead future readers.

**Proposal:** Either attach real citations to these claims or soften them to explicitly unverified recollections until cited.

### R6 [major] — No base-model or fine-tune feasibility decision

The plan never names candidate base models, and Phase 4 says "SFT and/or DPO on open model (or preference layer on API model if applicable)" — DPO is generally not possible on closed API models, so this branch may be a dead end. There is also no cost/latency budget anywhere.

**Proposal:** Add a Phase 1 decision item: candidate base models with a fine-tune feasibility matrix (open-weights vs API, adapter support, cost per experiment).

### R7 [major] — Ethics/privacy gap for live pilots

Phase 3 floats a "small live pilot" and Phase 5 adds persistent learner profiles, but the doc has no treatment of consent, minors, data retention, or FERPA/GDPR-class obligations. For an education product this is a launch blocker, not a polish item.

**Proposal:** Add a row to the §6 risks table and make an ethics/consent checklist a prerequisite for any live pilot, however small.

### R8 [minor] — Student-state accuracy is never evaluated

The teaching moves Diagnose and Remediate depend on the student model, but nothing in the eval plan measures whether the tutor's diagnoses are *correct* — only whether its turns look pedagogically well-formed.

**Proposal:** Add a diagnostic-accuracy metric: scripted dialogues with seeded misconceptions, scored on whether the tutor identifies the right one.

### R9 [minor] — Existing tutoring benchmarks/datasets not leveraged

The plan builds all eval scenarios from scratch. Public tutoring dialogue datasets and benchmarks exist (e.g. MathDial's teacher-student tutoring dialogues; TutorEval-style tutoring benchmarks) and could seed the Phase 1 scenario set and Phase 4 training data. (Author should verify current names/availability via search.)

**Proposal:** Add a "benchmarks & datasets" subsection to §9 and a Phase 1 task to shortlist and license-check them.

---


---

## GROK (Grok Build CLI (bde89716f679)) - 2026-07-22 19:26 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll rule item-by-item on R1–R9 as author, verify the empirical claims in R5 and the benchmark names in R9 with web search, then give append-ready COUNTERSIGN/AMEND/REJECT verdicts with exact edits.## Author countersign rulings — `docs/research-and-plan.md` v0.1

**Author:** Grok (original author)  
**Date:** 2026-07-22  
**Subject:** Independent review items R1–R9 in `docs/review-research-and-plan.md`  
**Method:** Item-by-item COUNTERSIGN / AMEND / REJECT; web checks on R5 empirical claims and R9 dataset/benchmark names.

---

### R1 [major] — Phase 3 does not test the stated thesis

**COUNTERSIGN** (prefer rename path; reject early LoRA-into-Phase-3 as default)

The review is right. Design principle 5 is about **trained** pedagogical behavior transferring to held-out C. Phase 3 freezes a **prompt** policy; prompt text transfers by construction, so “pedagogy prompt + RAG > RAG-only” is a **policy-value** result, not a transfer-of-trained-behavior result. Burying the real thesis re-run under Phase 4 is a structural flaw.

Pulling a small LoRA into Phase 3 is a valid alternative but premature as the default: it spends fine-tune budget before the cheap policy-value gate has proven the rubric and vertical slice. Adopt the rename + explicit post-alignment phase.

**Exact edits to `docs/research-and-plan.md`:**

1. **§5 Phase 3** — replace the Phase 3 header and body with:

```markdown
### Phase 3 — Policy value test (prompt + RAG)

**Not the full thesis test.** This phase freezes a *prompt-based* (or light scaffold) teaching policy and measures whether that policy improves pedagogical quality over RAG-only baselines. Prompt policies transfer across domains by construction; a positive result here validates the teaching policy and eval harness, not trained-behavior generalization.

1. Freeze teaching policy (system prompt + move vocabulary; no A/B fine-tune required)
2. Attach **only** corpus for held-out subject C
3. Compare conditions:
   - Base model + generic helpful prompt  
   - Base model + RAG  
   - Pedagogy policy + RAG  
4. Human (or expert-panel) rating on rubric per Phase 1 rater protocol  
5. Optional: simulated-student runs (see Phase 1 personas); no live pilot until ethics checklist (§6) is complete  

**Exit criteria:** Pedagogy+RAG beats RAG-only on pedagogical metrics without large grounding regression, using the **pre-registered** numeric bar locked in Phase 1 (not calibrated after the fact).
```

2. **Insert new phase after Phase 4** (renumber old Phase 5 → 6, Phase 6 → 7):

```markdown
### Phase 5 — Trained-behavior transfer (thesis test)

**This is the north-star experiment** (Design principle 5). Run only if Phase 3 policy-value test is positive and Phase 4 has produced an aligned model/adapter.

1. Train pedagogical behavior on domains A/B only (SFT and/or DPO per Phase 4; no C-domain fine-tune)
2. Freeze the resulting teaching model/adapter
3. Attach **only** corpus for held-out subject C
4. Compare at minimum:
   - Base model + RAG  
   - Pedagogy **prompt** + RAG (Phase 3 winner)  
   - Pedagogy **trained** model/adapter + RAG  
5. Same rater protocol and pre-registered success bar as Phase 1/3; report pedagogical margin **and** grounding regression separately  

**Exit criteria (thesis validated):** On held-out C + corpus only, the trained pedagogy system outperforms the strong RAG baseline (and ideally the prompt-pedagogy system) on the teaching rubric by the pre-registered margin, without grounding regression beyond the pre-registered threshold.
```

3. **§5 Phase 4** — change the last bullet from “Re-run transfer eval” to: “Hand off to Phase 5 (trained-behavior transfer); do not treat Phase 4 alone as thesis validation.”

4. **§7 Research success** — replace the first bullet with:

```markdown
- **Thesis (Phase 5):** On held-out subject C + corpus only, the *trained* pedagogy-aligned system outperforms strong RAG baseline on the teaching rubric by the pre-registered numeric margin locked in Phase 1.  
- **Policy value (Phase 3):** Prompt pedagogy + RAG beats RAG-only on the same rubric (supporting but not substituting for Phase 5).  
```

5. **§8 item 6** — replace with: “Decide go/no-go for fine-tuning after Phase 3; decide thesis go/no-go after Phase 5.”

---

### R2 [major] — Circular exit criteria; no rater protocol

**COUNTERSIGN**

Phase 2 exit (“rubric scores vs base”) and §7 (“define numeric bar after pilot scoring calibration”) form a closed loop: the gate depends on a bar chosen after seeing gated work. Missing rater type, blinding, n, and agreement target is also a real gap.

**Exact edits:**

1. **§5 Phase 1 deliverables** — append:

```markdown
- **Rater protocol (locked before Phase 2 scoring begins):**
  - Rater type: human pedagogy-experienced raters for go/no-go decisions; LLM-as-judge only as a secondary, bias-documented screen (never sole Phase 2/3/5 gate)
  - Count: ≥2 independent raters per dialogue for pilot; target ≥3 when budget allows
  - Blinding: raters do not see condition labels (base vs RAG vs pedagogy); randomize presentation order
  - Agreement target: Krippendorff’s α ≥ 0.60 on primary rubric dimensions after calibration round; if α < 0.60, revise rubric/anchors before Phase 3
- **Pre-registered numeric success bar (locked before Phase 3 runs):**  
  After a Phase 1 calibration set only (not the Phase 3/5 test set), fix e.g. mean pedagogical composite margin Δ ≥ +0.5 on a 1–5 scale vs RAG-only **and** grounding score regression ≤ 0.25 points (adjust units to final rubric). Record the exact bar in `docs/experiments/` before any Phase 3 ratings.
```

2. **§5 Phase 2 exit criteria** — replace with:

```markdown
**Exit criteria:** Demo on one subject; on 20–50 scripted dialogues, pedagogy policy + RAG beats base chat (and RAG-only if available) under the Phase 1 rater protocol. Phase 2 may use a *provisional* bar for engineering confidence only; the **pre-registered** bar for scientific go/no-go is locked before Phase 3 and must not be revised after Phase 3 data are seen.
```

3. **§7** — delete “define numeric bar after pilot scoring calibration”; point to Phase 1 lock.

**Arithmetic note on α ≥ 0.60:** Conventional lower bound for “acceptable” ordinal agreement in many social-science pilots (Krippendorff). With 2 raters and ~30 dialogues × 7 dimensions ≈ 210 items, α is estimable; if observed α = 0.45 on a dimension, that dimension is not usable as a gate until anchors are fixed (no arithmetic dispute with the proposal’s 0.6 target).

---

### R3 [major] — Over-help metrics are gameable; no adversarial scenarios

**COUNTERSIGN**

“Hint-before-answer rate” is gameable: one token question + full dump still “hints first.” Adversarial pressure is where over-help alignment fails.

**Exact edits:**

1. **§5 Phase 1** — under eval scenarios, add:

```markdown
**Scenario classes (required):**
1. Cooperative learner (good-faith scaffolding)
2. Multi-turn productive struggle
3. **Adversarial / pressure class (required):**
   - Explicit “just give me the answer”
   - Frustrated / time-pressured learner
   - Confident misdiagnosis of own gap
   - Jailbreak-style attempts to override teaching policy
   - Premature “I’m stuck” after minimal effort

**Over-help scoring:** Score resistance under pressure across the full dialogue (not first-turn only). A single token probe followed by a full solution counts as over-help. Prefer graded “earliest full-solution turn” and “answer leaked before policy threshold” over a binary hint-before-answer flag alone.
```

2. **§6** — change the “hint-before-answer rate” proxy row note to mention adversarial dialogues and earliest-full-solution turn.

---

### R4 [minor] — Simulated students underused

**AMEND** (promote, but sequence after rubric definition)

Agree they should not be a buried optional. Disagree that they should be co-equal “first-class Phase 1 instrument” before the human rubric and gold scenarios exist—simulators inherit rubric/persona definitions. Phase 1 defines personas; Phase 2+ uses them as a standard instrument.

**Exact replacement proposal:**

```markdown
**Simulated students (Phase 1 define → Phase 2+ run):**
- Phase 1 deliverable: small persona set (each = target misconception(s) + interaction style + success/failure criteria). Minimum 4 personas, including at least one adversarial/pressure persona (R3).
- Phase 2+: run simulated multi-turn eval as a **standard** (not optional) instrument alongside scripted human-rated dialogues. Use for reproducibility, regression, and as seed trajectories for Phase 4 preference data.
- Phase 3 live pilot remains optional and blocked on ethics checklist (R7).
```

Edit Phase 3 optional bullet accordingly; remove “Optional: simulated student” hedging for the sim path.

---

### R5 [minor] — Specific empirical claims are uncited

**COUNTERSIGN** (with verification results)

Web check as of 2026-07-22:

| Claim in §2.3/§2.4 | Verdict | Evidence |
|--------------------|---------|----------|
| LearnLM: expert raters prefer pedagogical quality over general models | **Supported** | LearnLM tech report / Google materials: expert pedagogical raters preferred LearnLM with average preference strengths of **31% over GPT-4o**, **11% over Claude 3.5**, **13% over Gemini 1.5 Pro** (scenario-based eval; pedagogy beyond mere accuracy). |
| “~21% retention in some programming-forum pipelines” | **Unverified** | No reliable primary source found for this exact figure in this session. Treat as unsupported until cited. |
| “Experts often prefer pedagogically aligned models even when raw conceptual accuracy dips slightly” | **Partially supported, overstated** | Preference-for-pedagogy is real (LearnLM). A general “accuracy dips but experts still prefer” tradeoff is **not** cleanly established as a settled finding from the searches run; soft to “preference can favor pedagogy when accuracy is held comparable or is not the sole criterion.” |

**Exact edits to §2.3:**

Replace the bullet list under “Key findings from recent literature” with:

```markdown
Key findings from recent literature (cite before treating as established):

- Off-the-shelf LLMs systematically **over-help**: premature full solutions, reduced genuine learning (recurring theme in pedagogical-alignment work; quantify in our own evals).
- Curated tutor–student data + preference optimization (DPO / related methods) can increase Socratic guidance and reduce verbosity (see pedagogical-alignment literature, e.g. Sonkar et al. and follow-ons — attach DOIs in §9).
- Expert raters often **prefer** models optimized for pedagogical quality (guidance, mistake handling) over general chat models when scored on teaching rubrics; this is **not** the same as proven superior learning outcomes (see LearnLM below).
- High-quality pedagogical data is scarce; scraped “help” forums typically need heavy filtering. **[Unverified recollection removed: do not cite “~21% retention” until a primary source is attached.]** Plan for aggressive filtering and teacher review rather than a fixed retention number.
```

**Exact edits to §2.4:**

Replace “Reported themes” bullets with cited claims:

```markdown
Reported themes (primary: LearnLM reports / Google education materials, 2024–2025):

- Trained for pedagogical instruction-following and learning-science-oriented behavior (later partially infused into Gemini)
- Expert pedagogical raters preferred LearnLM over contemporaneous flagships in simulated learning scenarios (reported average preference strengths: **31% vs GPT-4o**, **11% vs Claude 3.5**, **13% vs Gemini 1.5 Pro** base)
- Product integration emphasizes guided learning, personalization, and education-specific evaluation/safety
- Human studies and RCTs on real learning outcomes remain a separate, higher bar than rater preference

**Citations to add in §9:**
- LearnLM team, *LearnLM: Improving Gemini for Learning* (arXiv:2412.16429 and/or goo.gle/LearnLM materials)
- Jurenka et al., *Towards responsible development of generative AI for education* (arXiv:2407.12687)
- Google Cloud / Gemini for Education LearnLM product pages (note: vendor-reported preferences)
```

---

### R6 [major] — No base-model or fine-tune feasibility decision

**COUNTERSIGN**

“SFT and/or DPO on open model (or preference layer on API model)” is underspecified: full DPO generally requires weight access (or a provider preference-fine-tune product). No named candidates or cost envelope is a planning hole.

**Exact edits — add to Phase 1 deliverables:**

```markdown
- **Base-model & fine-tune feasibility decision (required before Phase 4 spend):**
  | Candidate class | Examples (fill at decision time) | SFT | DPO / preference FT | Adapter (LoRA) | Notes |
  |-----------------|----------------------------------|-----|---------------------|----------------|-------|
  | Open weights (local/GPU) | e.g. Llama-/Qwen-/Mistral-class instruct | Yes | Yes | Yes | Full thesis path (Phase 5) |
  | Open weights (hosted FT APIs) | provider-dependent | Often | Sometimes | Often | Check current API FT features |
  | Closed API chat-only | major lab APIs | No | No* | No | Prompt + RAG + judge only; *unless vendor offers preference FT |
  | Closed API with preference FT product | if offered | N/A | Via vendor | N/A | Document limits |

  Also lock: rough cost/latency budget per experiment (tokens × price; target latency for interactive tutoring, e.g. p95 < 5s for tutor turns on pilot hardware/API).
```

**§5 Phase 4** — replace the open-ended SFT/DPO sentence with:

```markdown
3. If open-weights path: SFT and/or DPO (or equivalent preference optimization) on the chosen base.  
   If API-only path: prompt/policy + any vendor preference layer; **do not claim DPO** without weight-access or documented vendor preference-FT.  
   Revisit Phase 1 feasibility matrix before committing GPU/API budget.
```

---

### R7 [major] — Ethics/privacy gap for live pilots

**COUNTERSIGN**

Education + persistent profiles + “small live pilot” without consent/minors/retention/FERPA–GDPR-class treatment is a launch blocker, not polish.

**Exact edits:**

1. **§6 risks table** — add row:

```markdown
| Live learners / minors / personal data without ethics plan | Consent, age gates, retention limits, and jurisdiction (e.g. FERPA/GDPR-class) checklist **before** any live pilot; default to synthetic + staff-only until cleared; no persistent profiles of minors without legal review |
```

2. **§5 Phase 3** — add hard gate: “No live pilot until ethics/consent checklist complete (see §6).”

3. **§5 Phase 5 (productization, after renumber)** — move “Safety eval suite” earlier note: ethics checklist is a **prerequisite**, not a Phase 5 invention.

4. **New short subsection or Phase 1 deliverable:**

```markdown
**Ethics / consent checklist (prerequisite for any live pilot, however small):**
- [ ] Population defined (adults only vs minors)
- [ ] Informed consent / institutional review as applicable
- [ ] Data retained: what, where, how long; deletion path
- [ ] No secondary use of learner chats for training without explicit consent
- [ ] Jurisdiction review (FERPA/GDPR-class obligations if US/EU educational data)
- [ ] Incident path for harmful advice / self-harm / cheating facilitation
```

---

### R8 [minor] — Student-state accuracy is never evaluated

**COUNTERSIGN**

Diagnose/Remediate without measuring diagnostic correctness rewards “well-formed” tutoring that chases the wrong misconception.

**Exact edit — Phase 1 rubric / metrics:**

```markdown
8. **Diagnostic accuracy** — On scripted dialogues with **seeded misconceptions**, score whether the tutor identifies the correct misconception (and whether remediation targets that misconception). Report separately from “sounds pedagogical.”
```

Add matching scenario class under Phase 1: “seeded-misconception dialogues with gold diagnosis labels.”

---

### R9 [minor] — Existing tutoring benchmarks/datasets not leveraged

**AMEND** (accept task; correct names after search)

Building everything from scratch is unnecessary. Web check as of 2026-07-22:

| Name | Status |
|------|--------|
| **MathDial** (Macina et al., Findings of EMNLP 2023; arXiv:2305.14536) | **Confirmed** — ~3k one-to-one teacher–student tutoring dialogues grounded in multi-step math problems; public GitHub `eth-nlped/mathdial` |
| **TutorEval** | **Not confirmed as a single canonical public benchmark** under that exact name in this search pass. Review’s “TutorEval-style” hedge is appropriate; do not list TutorEval as a settled primary source until a citable artifact is found. |
| Related landscape | Other tutoring/dialogue resources exist (ITS corpora, various math-tutor dialogue collections); Phase 1 shortlist should license-check each. |

**Exact edits:**

1. **§9** — add subsection:

```markdown
### Benchmarks & datasets (seed shortlist; license-check before use)

| Resource | Type | Notes (as of 2026-07-22) |
|----------|------|---------------------------|
| MathDial (Macina et al., 2023) | Teacher–student tutoring dialogues (math) | ~3k dialogues; pedagogical annotations; strong Phase 1/4 seed candidate |
| (TBD) additional tutor dialogue corpora | Varies | Shortlist in Phase 1; do not assume “TutorEval” exists as a single standard without a citation |
| Internal gold set | Scripted + adversarial + seeded-misconception | Still required: public sets will not cover our corpus-transfer thesis (subject C) |
```

2. **Phase 1 deliverables** — add: “Shortlist public tutoring datasets/benchmarks (start with MathDial); license-check; map which rubric dimensions they can and cannot cover; keep internal gold scenarios for transfer subject C and adversarial class.”

---

## Summary table

| Item | Severity | Ruling | Adopts? |
|------|----------|--------|---------|
| R1 | major | **COUNTERSIGN** | Rename Phase 3 → policy value; new Phase 5 = trained transfer (thesis). Do **not** default to early LoRA-in-Phase-3. |
| R2 | major | **COUNTERSIGN** | Rater protocol + pre-registered bar before Phase 3. |
| R3 | major | **COUNTERSIGN** | Adversarial scenario class; non-gameable over-help metrics. |
| R4 | minor | **AMEND** | Personas in Phase 1; sims standard from Phase 2+ (not optional), not co-equal before rubric exists. |
| R5 | minor | **COUNTERSIGN** | Cite LearnLM numbers; **drop ~21%** until sourced; soften accuracy-dip claim. |
| R6 | major | **COUNTERSIGN** | Feasibility matrix + cost/latency; fix DPO/API confusion. |
| R7 | major | **COUNTERSIGN** | Ethics row + live-pilot hard gate. |
| R8 | minor | **COUNTERSIGN** | Diagnostic accuracy on seeded misconceptions. |
| R9 | minor | **AMEND** | Add datasets subsection + Phase 1 shortlist; MathDial yes; TutorEval not confirmed as named standard. |

**Rejected proposals:** none wholesale. **Partial rejects inside countersigns:** (R1) early LoRA-into-Phase-3 as the preferred fix; (R4) making sims a Phase 1 scoring instrument before the rubric/personas exist; (R9) treating “TutorEval” as a verified primary benchmark without a citation.

**Net document status:** After applying the above edits, v0.1 → **v0.2** is ready for a short consistency pass (phase renumbering: old 5→6, old 6→7; cross-links in §7–§8). No remaining major review item is left as “agree without edit.”

---

## Adjudication (Claude, 2026-07-22)

Round 1 outcome: **converged**. Rulings adjudicated as follows.

- **R1, R2, R3, R5, R6, R7, R8 — accepted as countersigned.** On R1, Grok's partial reject of the LoRA-in-Phase-3 alternative is accepted: the rename + explicit "Phase 5 — Trained-behavior transfer (thesis test)" path preserves the cheap-gate-first sequencing and is the better fix. On R5, both authors now agree the "~21% retention" figure is unsourced and must be dropped; the LearnLM preference figures (31% vs GPT-4o, 11% vs Claude 3.5, 13% vs Gemini 1.5 Pro) match the LearnLM report (arXiv:2412.16429) and may be cited as vendor-reported.
- **R4 — Grok's amendment accepted.** Defining personas in Phase 1 and running simulators as a standard instrument from Phase 2+ is strictly better sequencing than the original "first-class Phase 1 instrument" proposal, since simulators inherit rubric and persona definitions that don't exist until Phase 1 completes.
- **R9 — amendment structure accepted; factual finding overruled by evidence.** Grok could not confirm TutorEval; verification (2026-07-22) confirms it exists: **TutorEval**, Chevalier et al., *Language Models as Science Tutors*, arXiv:2402.11111 (2024), 800+ expert-written questions over STEM textbook chapters, with the companion **TutorChat** dataset (~80k synthetic tutoring dialogues); code at `princeton-nlp/LM-Science-Tutor`. Caveat for the §9 table: TutorEval evaluates tutor-style explanation over long textbook context, not multi-turn tutoring dialogue — **MathDial remains the primary dialogue seed**, with TutorEval/TutorChat listed as an eval and synthetic-dialogue resource respectively.

**Final scoreboard:** 9/9 review items sustained (7 countersigned, 2 amended); 1 of Grok's 3 partial rejections overruled (TutorEval existence), 2 accepted. The exact edits above, plus the corrected R9 table row, constitute the agreed v0.2 change set for `docs/research-and-plan.md`. Not yet applied.
