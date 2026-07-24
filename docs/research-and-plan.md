# Pedagogy-First Teaching Model

**Status:** Research + plan, post-review (v0.2)  
**Date:** 2026-07-22  
**Project:** `ml_teacher`  

**2026-07-23 update:** Plan/realize controller path is **tabled**. Active direction: conversational Spanish + learner character sheet — see `docs/conversational-spanish-and-learner-model.md`.

---

## 1. Concept

### Problem

Most AI “tutors” are general-purpose language models prompted (or lightly tuned) to help with a subject. They tend to:

- Dump full answers instead of scaffolding
- Over-help and reduce productive struggle
- Optimize for correctness and fluency, not learning outcomes
- Couple teaching quality to domain expertise baked into pretraining

### Thesis

Train (or align) a model that is primarily an **expert in teaching**, not in Spanish, coding, or any single domain. Later, supply a **corpus** (course pack, textbook, internal docs). Because the model already knows *how* to teach, it becomes a strong instructor for that material.

### Working architecture (high level)

```text
┌─────────────────────────────────────┐
│  Teaching brain (pedagogy-aligned)  │  ← fine-tuned / RL-aligned for teaching moves
└─────────────────┬───────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
  Content corpus         Student state
  (RAG / course pack)    (goals, errors, progress)
        │                   │
        └─────────┬─────────┘
                  ▼
         Optional domain checkers
         (facts, code runner, grader)
```

### Positioning (honest version)

> A **pedagogy-first** model that is **content-agile** via corpora and tools — not a content-free oracle.

Pure “zero domain knowledge” is not viable. The product target is: strong transferable teaching behavior + plug-in curriculum + verification where truth matters.

---

## 2. Research background

### 2.1 Education theory: three knowledge types

Classic teacher knowledge (Shulman and successors) separates:

| Knowledge type | Definition | Examples |
|----------------|------------|----------|
| **Content knowledge** | Mastery of the subject | Spanish grammar, algorithms, history facts |
| **Pedagogical knowledge** | How people learn; general teaching craft | Scaffolding, feedback, questioning, cognitive load, spacing |
| **Pedagogical content knowledge (PCK)** | How to teach *this* subject | Typical misconceptions, good analogies, sequenced examples |

Implication for this project:

- We can invest heavily in **pedagogical knowledge** as a reusable skill layer.
- **PCK** only partially transfers; some subject-specific teaching knowledge must come from corpus, logs, or later specialization.
- **Content** can be injected via retrieval and tools rather than full pretraining on every domain.

### 2.2 Intelligent tutoring systems (ITS)

Decades of ITS design already modularize:

1. **Domain / knowledge module** — what is true in the subject  
2. **Pedagogical module** — how to instruct and intervene  
3. **Student model** — what the learner knows, struggles with, and needs next  

This project is essentially a modern LLM implementation of that split: pedagogy-aligned model + corpus as domain + optional student state.

### 2.3 Pedagogical fine-tuning (LLM era)

**Pedagogical fine-tuning** aligns pretrained models with teacher-like strategies (scaffolding, Socratic prompting, staged disclosure, personalization) rather than maximizing answer completeness alone.

Key findings from recent literature (cite before treating as established):

- Off-the-shelf LLMs systematically **over-help**: premature full solutions, reduced genuine learning (recurring theme in pedagogical-alignment work; quantify in our own evals).
- Curated tutor–student data + preference optimization (DPO / related methods) can increase Socratic guidance and reduce verbosity (see pedagogical-alignment literature, e.g. Sonkar et al. and follow-ons — attach DOIs in §9).
- Expert raters often **prefer** models optimized for pedagogical quality (guidance, mistake handling) over general chat models when scored on teaching rubrics; this is **not** the same as proven superior learning outcomes (see LearnLM below).
- High-quality pedagogical data is scarce; scraped “help” forums typically need heavy filtering. Plan for aggressive filtering and teacher review rather than assuming a fixed retention number.

Representative directions:

- Socratic method fine-tunes (math, programming, critical thinking)
- Preference-based pedagogical alignment (preferred teaching moves vs. answer dumps)
- Multi-objective rewards balancing student success and instructional quality (no answer leakage, scaffolding present)

### 2.4 Google LearnLM (closest large-scale analog)

Google’s **LearnLM** family (later infused into Gemini) is fine-tuned for **learning science**, not as a single-subject expert.

Reported themes (primary: LearnLM reports / Google education materials, 2024–2025):

- Trained for pedagogical instruction-following and learning-science-oriented behavior (later partially infused into Gemini)
- Expert pedagogical raters preferred LearnLM over contemporaneous flagships in simulated learning scenarios (vendor-reported average preference strengths: **31% vs GPT-4o**, **11% vs Claude 3.5**, **13% vs Gemini 1.5 Pro**; see arXiv:2412.16429)
- Product integration emphasizes guided learning, personalization, and education-specific evaluation/safety
- Human studies and RCTs on real learning outcomes remain a separate, higher bar than rater preference

**Takeaway:** “Specialize the model in teaching behavior” is already a serious industrial research direction, not a speculative blog idea.

### 2.5 What does *not* work

| Failure mode | Why |
|--------------|-----|
| Pedagogy with no content competence | Empty Socratic loops; cannot diagnose misconceptions or judge correctness |
| Corpus dump without teaching alignment | RAG chatbot that retrieves text and still over-answers |
| Single-turn “explain this” as success metric | Optimizes lecturing, not tutoring over time |
| Ignoring PCK | Generic strategies miss subject-specific traps |
| No evaluation of learning process | “Sounds helpful” ≠ “students learn more” |

### 2.6 Feasibility verdict

| Claim | Feasible? | Notes |
|-------|-----------|--------|
| Model specialized in teaching *behavior* | **Yes** | LearnLM + pedagogical fine-tuning literature |
| Attach a corpus later and get a solid instructor | **Mostly yes** | Strong for structured curricula; weaker without verification for hard skills |
| Zero domain knowledge needed | **No** | Needs enough content skill, retrieval, or external checkers |
| Better than base model + prompt | **Often yes** | Alignment against over-helping is real value |
| Better than domain-expert model with no pedagogy | **Often yes for learning** | Experts dump; teachers structure learning |

---

## 3. Design principles

1. **Pedagogy is the primary training objective** — not next-token helpfulness defined as “give the answer.”
2. **Content is modular** — inject via corpus (RAG), structured lesson packs, and tools.
3. **Prefer guided discovery** — hints, questions, partial feedback before full solutions (policy-configurable).
4. **Measure teaching, not just correctness** — scaffolding quality, over-help rate, misconception handling, learning proxies.
5. **Subject transfer is the north-star test** — train pedagogical behavior on subjects A/B; evaluate on subject C with corpus only.
6. **Safety and grounding** — teaching confidently wrong is worse than declining; cite/retrieve curriculum when possible.
7. **Start thin, prove transfer** — experiment before large fine-tunes or product surface area.

---

## 4. System sketch

### 4.1 Components

| Component | Role | v0 approach |
|-----------|------|-------------|
| **Teaching policy** | Decides moves: probe, hint, explain, assess, recap | System prompt + optional SFT/DPO later |
| **Curriculum store** | Source of truth for content | Markdown / PDF / notes → chunked embeddings |
| **Retriever** | Pull relevant passages for current goal | Simple vector RAG |
| **Student state** | Goals, recent errors, mastery estimates | Session memory JSON (later: persistent profile) |
| **Response composer** | Grounded, pedagogically structured turn | LLM with teaching rubric in context |
| **Verifiers (optional)** | Ground truth for code, quizzes, facts | Code runner, answer keys, LLM judge |
| **Eval harness** | Score pedagogical quality + grounding | Rubrics + held-out subject tests |

### 4.2 Teaching move vocabulary (initial)

Reusable actions the teaching brain should learn:

- **Diagnose** — identify what the learner understands / confuses  
- **Set goal** — make the next micro-objective explicit  
- **Scaffold** — break the task; reduce cognitive load  
- **Hint** — progressive disclosure without full solution  
- **Socratic probe** — questions that force reasoning  
- **Worked example** — demonstrate once, then fade support  
- **Check** — mini-assessment / “explain back”  
- **Remediate** — target a specific misconception  
- **Recap & space** — summarize; schedule revisit  
- **Escalate to answer** — only when stuck or when policy allows  

### 4.3 Corpus contract

A “course pack” should eventually support:

- Learning objectives  
- Canonical explanations  
- Examples and non-examples  
- Common misconceptions (if available)  
- Practice items + answer keys  
- Scope boundaries (what not to invent)

v0 can start with unstructured notes + automatic chunking; structure improves quality later.

**Dual-mode packs (decided 2026-07-22; see `docs/architecture-pack-debate.md`):** packs declare `content_mode: spec` or `content_mode: full`. **Mode `spec`** (domains the base model already knows, e.g. Spanish A1): the pack is a thin curriculum contract + PCK + frozen measurement — in-scope inventory, denylist, sequence/dependencies, misconception taxonomy, keyed eval items, task criteria, pedagogical directives, optional seed inputs — and the tutor generates in-scope content from its own knowledge under those constraints. **Mode `full`** (unknown domains, the Phase 3/5 transfer subject C, high-stakes truth): full content corpus with strict teach-only-from-pack grounding. Missing metadata defaults to `full`. Measurement artifacts (scope, sequence, M-IDs, item keys, task criteria) are frozen in both modes so research comparability survives. Rationale: writing content the model already knows is redundant authoring that suppresses superior parametric knowledge; the residual known-domain risks are scope creep and framing drift, which the frozen spec — not conjugation tables — mitigates.

---

## 5. Plan outline

### Phase 0 — Framing (this document)

- [x] Capture concept, research, constraints  
- [ ] Confirm success criteria with stakeholders  
- [x] Choose pilot train domain A: **Spanish A1** (locked 2026-07-22); train domain B and transfer subject C deferred until Phase 3 prep

**Pilot design**

| Role | Domain | Purpose |
|------|--------|---------|
| Pedagogy train A | **Spanish A1** (locked 2026-07-22) | Teaching dialogues + preferences; corpus = Claude-generated course pack |
| Pedagogy train B | TBD — e.g. intro Python or basic stats | Force domain-agnostic moves (decide before Phase 3) |
| Transfer test C | e.g. company onboarding doc / new textbook | Corpus only; no fine-tune on C |

**Locked build decisions (2026-07-22):**

- Phase 2 vertical slice = **Python CLI app** (corpus ingest + RAG + chat loop + session logging).
- Tutor model = `claude-opus-4-8` via the Anthropic Python SDK.
- Corpus for A = **Claude-generated course pack**, structured per §4.3 (objectives, canonical explanations, misconceptions, practice items + keys, scope boundaries). Caveat: a synthetic corpus weakens the "teach unfamiliar material" framing — mitigate by generating the pack independently of the tutor policy, grounding the tutor strictly in the pack (design principle 6), and seeding known misconceptions so diagnostic accuracy (rubric dimension 8) stays measurable.
- Spanish A1 eval caveat: no automatic verifier exists (unlike code); correctness scoring leans on the rubric, seeded-misconception scenarios, and simulated-student personas — consider a native/proficient speaker spot-check before Phase 3.

### Phase 1 — Spec & metrics

Deliverables:

- Written definition of “good teaching turn”  
- Rubric dimensions (see below)  
- Eval scenarios (single-turn + multi-turn; scenario classes below)  
- Decision: prompt-only v0 vs early fine-tune  
- **Rater protocol (locked before Phase 2 scoring begins):**
  - Rater type: human pedagogy-experienced raters for go/no-go decisions; LLM-as-judge only as a secondary, bias-documented screen (never the sole Phase 2/3/5 gate)
  - Count: ≥2 independent raters per dialogue for pilot; target ≥3 when budget allows
  - Blinding: raters do not see condition labels (base vs RAG vs pedagogy); randomize presentation order
  - Agreement target: Krippendorff’s α ≥ 0.60 on primary rubric dimensions after a calibration round; if α < 0.60, revise rubric/anchors before Phase 3
- **Pre-registered numeric success bar (locked before Phase 3 runs):**  
  After a Phase 1 calibration set only (not the Phase 3/5 test set), fix e.g. mean pedagogical composite margin Δ ≥ +0.5 on a 1–5 scale vs RAG-only **and** grounding score regression ≤ 0.25 points (adjust units to final rubric). Record the exact bar in `docs/experiments/` before any Phase 3 ratings.
- **Simulated-student personas (define here; run from Phase 2 on):** minimum 4 personas, each = target misconception(s) + interaction style + success/failure criteria; at least one adversarial/pressure persona. Simulators are a **standard** (not optional) instrument from Phase 2 on — for reproducibility, regression testing, and seed trajectories for Phase 4 preference data.
- **Base-model & fine-tune feasibility decision (required before Phase 4 spend):**

  | Candidate class | Examples (fill at decision time) | SFT | DPO / preference FT | Adapter (LoRA) | Notes |
  |-----------------|----------------------------------|-----|---------------------|----------------|-------|
  | Open weights (local/GPU) | e.g. Llama-/Qwen-/Mistral-class instruct | Yes | Yes | Yes | Full thesis path (Phase 5) |
  | Open weights (hosted FT APIs) | provider-dependent | Often | Sometimes | Often | Check current API FT features |
  | Closed API chat-only | major lab APIs | No | No* | No | Prompt + RAG + judge only; *unless vendor offers preference FT |
  | Closed API with preference FT product | if offered | N/A | Via vendor | N/A | Document limits |

  Also lock: rough cost/latency budget per experiment (tokens × price; target latency for interactive tutoring, e.g. p95 < 5s for tutor turns on pilot hardware/API).
- **Ethics / consent checklist (prerequisite for any live pilot, however small):**
  - [ ] Population defined (adults only vs minors)
  - [ ] Informed consent / institutional review as applicable
  - [ ] Data retained: what, where, how long; deletion path
  - [ ] No secondary use of learner chats for training without explicit consent
  - [ ] Jurisdiction review (FERPA/GDPR-class obligations if US/EU educational data)
  - [ ] Incident path for harmful advice / self-harm / cheating facilitation
- **Public dataset shortlist:** start with MathDial (tutoring dialogues) and TutorEval/TutorChat (explanation eval / synthetic dialogues); license-check each; map which rubric dimensions they can and cannot cover; keep internal gold scenarios for transfer subject C and the adversarial class (see §9).

**Initial rubric dimensions**

1. Grounding (stays faithful to corpus / admits gaps)  
2. No over-help (does not leak full solution too early)  
3. Scaffolding quality (right-sized next step)  
4. Misconception handling  
5. Clarity & cognitive load  
6. Engagement / agency (learner does the work)  
7. Correctness when claims are made  
8. **Diagnostic accuracy** — on scripted dialogues with seeded misconceptions, does the tutor identify the correct misconception, and does remediation target it? Report separately from “sounds pedagogical.”  

**Scenario classes (required):**

1. Cooperative learner (good-faith scaffolding)
2. Multi-turn productive struggle
3. Seeded-misconception dialogues with gold diagnosis labels (feeds rubric dimension 8)
4. **Adversarial / pressure class:**
   - Explicit “just give me the answer”
   - Frustrated / time-pressured learner
   - Confident misdiagnosis of own gap
   - Jailbreak-style attempts to override the teaching policy
   - Premature “I’m stuck” after minimal effort

**Over-help scoring:** score resistance under pressure across the full dialogue, not first-turn behavior only. A single token probe followed by a full solution counts as over-help. Prefer graded metrics (“earliest full-solution turn,” “answer leaked before policy threshold”) over a binary hint-before-answer flag alone.

### Phase 2 — Vertical slice (prompt + RAG tutor)

Build the smallest end-to-end instructor:

1. Ingest a small corpus  
2. Retrieve relevant chunks for learner query  
3. Respond with a fixed teaching policy (system prompt + move vocabulary)  
4. Multi-turn session with light student state  
5. Run the Phase 1 simulated-student personas as a standard eval instrument  
6. Log conversations for later dataset mining  

**Exit criteria:** Demo on one subject; on 20–50 scripted dialogues, pedagogy policy + RAG beats base chat (and RAG-only if available) under the Phase 1 rater protocol. Phase 2 may use a *provisional* bar for engineering confidence only; the **pre-registered** bar for scientific go/no-go is locked before Phase 3 and must not be revised after Phase 3 data are seen.

### Phase 3 — Policy value test (prompt + RAG)

**Not the full thesis test.** This phase freezes a *prompt-based* (or light scaffold) teaching policy and measures whether that policy improves pedagogical quality over RAG-only baselines. Prompt policies transfer across domains by construction; a positive result here validates the teaching policy and eval harness, not trained-behavior generalization (that is Phase 5).

1. Freeze teaching policy (system prompt + move vocabulary; no A/B fine-tune required)  
2. Attach **only** corpus for held-out subject C  
3. Compare conditions:
   - Base model + generic helpful prompt  
   - Base model + RAG  
   - Pedagogy policy + RAG  
4. Human (or expert-panel) rating on rubric per the Phase 1 rater protocol  
5. Simulated-student runs (Phase 1 personas) as a standard instrument; live pilot optional and **blocked until the ethics/consent checklist (Phase 1 / §6) is complete**  

**Exit criteria:** Pedagogy+RAG beats RAG-only on pedagogical metrics without large grounding regression, using the **pre-registered** numeric bar locked in Phase 1 (not calibrated after the fact).

### Phase 4 — Pedagogical data & alignment

If Phase 3 is positive:

1. Collect / synthesize multi-domain tutor dialogues labeled with teaching moves  
2. Preference pairs: good scaffold vs over-help  
3. If open-weights path: SFT and/or DPO (or equivalent preference optimization) on the chosen base.  
   If API-only path: prompt/policy + any vendor preference layer; **do not claim DPO** without weight access or a documented vendor preference-FT product.  
   Revisit the Phase 1 feasibility matrix before committing GPU/API budget.  
4. Hand off to Phase 5 (trained-behavior transfer); do not treat Phase 4 alone as thesis validation  

**Risk note:** Data quality dominates; plan for heavy filtering and teacher review.

### Phase 5 — Trained-behavior transfer (thesis test)

**This is the north-star experiment** (Design principle 5). Run only if the Phase 3 policy-value test is positive and Phase 4 has produced an aligned model/adapter.

1. Train pedagogical behavior on domains A/B only (SFT and/or DPO per Phase 4; no C-domain fine-tune)  
2. Freeze the resulting teaching model/adapter  
3. Attach **only** corpus for held-out subject C  
4. Compare at minimum:
   - Base model + RAG  
   - Pedagogy **prompt** + RAG (Phase 3 winner)  
   - Pedagogy **trained** model/adapter + RAG  
5. Same rater protocol and pre-registered success bar as Phase 1/3; report pedagogical margin **and** grounding regression separately  

**Exit criteria (thesis validated):** On held-out C + corpus only, the trained pedagogy system outperforms the strong RAG baseline (and ideally the prompt-pedagogy system) on the teaching rubric by the pre-registered margin, without grounding regression beyond the pre-registered threshold.

### Phase 6 — Productization (only after evidence)

- Course-pack format and upload UX  
- Persistent learner profiles (the Phase 1 ethics/consent checklist is a prerequisite here, not a productization-phase invention)  
- Assessment generation + mastery tracking  
- Domain tools (code exec, flashcards, speech later)  
- Safety eval suite for educational settings  
- Ops: cost, latency, eval regression suite  

### Phase 7 — Optional specialization

- Light per-domain adapters for high-value subjects (PCK boost)  
- Keep shared pedagogy backbone; avoid one giant multi-domain dump that forgets teaching style  

---

## 6. Risks and open questions

| Risk / question | Mitigation |
|-----------------|------------|
| Pedagogy does not transfer across domains | Force multi-domain train set; explicit transfer eval early |
| Model invents curriculum | Strict grounding mode; cite corpus; refuse when missing |
| Over-alignment → unhelpful withholding | Policy for when to reveal answers; user/role modes (tutor vs answer key) |
| Data scarcity for good teaching | Synthetic dialogues + teacher edit; preference ranking over full scripts |
| Eval is subjective | Multi-rater rubrics per Phase 1 protocol; objective proxies scored on adversarial dialogues (earliest-full-solution turn, answer-leak rate, retrieval faithfulness) — not a binary hint-before-answer flag |
| Student outcomes hard to measure | Start with process metrics; add small outcome pilots later |
| Live learners / minors / personal data without ethics plan | Consent, age gates, retention limits, and jurisdiction (FERPA/GDPR-class) checklist **before** any live pilot; default to synthetic + staff-only until cleared; no persistent profiles of minors without legal review |
| Scope creep into full LMS | Keep v0 = tutoring conversation + corpus |

**Open research questions for this repo**

1. How much base capability is required before pedagogical alignment helps?  
2. Does move-labeled data beat free-form “be a good tutor” data?  
3. What corpus structure (raw text vs objectives + misconceptions) most improves transfer?  
4. Can a student model be lightweight (session features) and still improve scaffolding?  
5. When does a domain verifier become mandatory (coding, medicine, law, etc.)?

---

## 7. Success criteria (initial)

### Research success (thesis validated)

- **Thesis (Phase 5):** On held-out subject C + corpus only, the *trained* pedagogy-aligned system outperforms the strong RAG baseline on the teaching rubric by the pre-registered numeric margin locked in Phase 1.  
- **Policy value (Phase 3):** Prompt pedagogy + RAG beats RAG-only on the same rubric (supporting evidence; does not substitute for Phase 5).  
- Grounding / hallucination rate does not regress beyond the pre-registered threshold.  

### Product success (later)

- Instructor can upload a course pack and run a multi-session tutor without fine-tuning.  
- Learners report more “I figured it out” moments; fewer pure answer dumps (instrumented).  
- Optional: measurable gain on pre/post checks vs non-pedagogical control.  

### Non-goals (for now)

- Replacing human teachers  
- Training a foundation model from scratch  
- Full LMS (grades, rostering, accreditation)  
- Claiming zero-shot expert-level PCK in every domain  

---

## 8. Near-term next actions

1. **Lock pilot domains** (2 train + 1 transfer).  
2. **Write v0 teaching system prompt** + move vocabulary as a checked-in artifact.  
3. **Define rubric sheet** and 20 gold dialogue scenarios.  
4. **Stand up corpus ingest + RAG + chat loop** (minimal app or notebook).  
5. **Run baseline comparisons** and document results in `docs/experiments/`.  
6. **Decide go/no-go**: fine-tuning after Phase 3 (policy value test); thesis verdict after Phase 5 (trained-behavior transfer).  

---

## 9. References & related work (seed list)

Use these as starting points for deeper literature review; not exhaustive.

### Products / industrial

- Google LearnLM / Gemini guided learning (pedagogy-tuned models; education evaluations)
  - LearnLM team, *LearnLM: Improving Gemini for Learning* (arXiv:2412.16429) — source of the §2.4 expert-rater preference figures (vendor-reported)
  - Jurenka et al., *Towards responsible development of generative AI for education* (arXiv:2407.12687)
- Classic ITS architectures (domain + pedagogy + student model)

### Research themes

- Pedagogical fine-tuning / pedagogical alignment of LLMs  
- Socratic tutoring fine-tunes (e.g. math and programming tutors)  
- Preference optimization for teaching moves (DPO-style pedagogical preferences)  
- Over-helping and “answer dumping” as failure modes of helpful assistants  
- Shulman: pedagogical content knowledge  

### Benchmarks & datasets (seed shortlist; license-check before use)

| Resource | Type | Notes (as of 2026-07-22) |
|----------|------|---------------------------|
| MathDial (Macina et al., 2023; arXiv:2305.14536) | Teacher–student tutoring dialogues (math) | ~3k dialogues with pedagogical annotations; primary dialogue seed for Phase 1/4 |
| TutorEval + TutorChat (Chevalier et al., 2024; arXiv:2402.11111) | Explanation eval over STEM textbook chapters + ~80k synthetic tutoring dialogues | TutorEval scores tutor-style explanation (not multi-turn dialogue) — use as an eval; TutorChat as a synthetic-dialogue resource |
| Internal gold set | Scripted + adversarial + seeded-misconception | Still required: public sets will not cover the corpus-transfer thesis (subject C) |

### Suggested search terms for ongoing review

- `pedagogical fine-tuning LLM`  
- `Socratic tutor DPO`  
- `LearnLM Gemini education`  
- `intelligent tutoring system pedagogical module`  
- `pedagogical content knowledge AI tutor`  

---

## 10. Document history

| Version | Date | Notes |
|---------|------|--------|
| 0.1 | 2026-07-22 | Initial research synthesis and plan outline |
| 0.2 | 2026-07-22 | Applied countersigned review change set R1–R9 (see `docs/review-research-and-plan.md`): Phase 3 renamed to policy value test; new Phase 5 trained-behavior transfer (thesis test); rater protocol + pre-registered success bars; adversarial scenario class; diagnostic-accuracy rubric dimension; ethics gate; base-model feasibility matrix; citations and dataset shortlist |
| 0.3 | 2026-07-22 | Locked Phase 0/2 build decisions: pilot domain A = Spanish A1; corpus = Claude-generated course pack; vertical slice = Python CLI app on `claude-opus-4-8` |
| 0.4 | 2026-07-22 | Dual-mode pack architecture (`spec` vs `full`) adopted after user challenge + Grok debate (`docs/architecture-pack-debate.md`); Spanish A1 pack set to mode `spec`; §4.3 corpus contract updated |
