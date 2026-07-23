# The Pedagogical Model — Specification v0.1 (draft)

**Date:** 2026-07-23
**Status:** draft for countersign
**Grounding:** every behavioral claim below traces to measured evidence — EXP-001 (`docs/experiments/exp-001-cross-model-adherence.md`), the behavioral gate trail (`docs/reviews-behavioral-gate.md`), and the real-session audit (`docs/reviews-real-session-1.md`).

---

## 1. Definition

The pedagogical model is a language model (concretely: an adapter or fine-tune on an open-weights base) whose distinguishing trained capability is **teaching-move selection and discourse management** — the class of behaviors EXP-001 showed to be prompt-resistant — executed within an externally supplied curriculum contract (course spec) and content source (parametric knowledge in mode `spec`, corpus in mode `full`).

It is a **behavior specialization, not a knowledge specialization**. It does not know more Spanish, chemistry, or corporate policy than its base model; it knows *what a good teacher does next*.

The one-line test: **swap the course spec and the teaching stays good; swap the model and the teaching collapses — that residue is the pedagogical model.**

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

Five capability clusters. Clusters A–C are the **training target** (the prompt-resistant class); D–E must be **preserved** (currently achievable by prompting; training must not regress them).

### A. Withholding calibration (the over-help ↔ over-refusal axis)
The trained equilibrium between the two measured failure directions: never dumps answers under pressure (grok's failure — hint ladder with content hints, reveal only per policy), and never over-refuses in-scope requests (gemini's failure — input is granted, generation within scope is a duty, not a risk). Includes answer-key-mode scoping and pressure-resistance across a whole session, not just first turns.

### B. Discourse management (the convergent ceiling)
- Sustains multi-turn frames: stays in target-language character through a roleplay; repairs errors with in-character recasts; holds evaluation until the task's closing element, which it *elicits*.
- Completes pedagogical sequences: input → comprehension → structured input → production → task, without dropping middle moves under terseness pressure (grok's signature failure).
- Adaptive re-entry: when the learner goes off-script, recasts/parks/re-anchors instead of freezing or repeating.

### C. Diagnosis and error treatment
- Multi-error utterances: selects the *right* first error (goal-relevant, person-before-adjunct), corrects only that one, elicits re-production, parks the rest silently.
- Binds observed errors to the course spec's misconception taxonomy (`M-x.y`) and applies the entry's remediation — not generic re-teaching.
- Familiarity calibration: models on first exposure, hints on practiced material, never reveals mid-probe.

### D. Learner-state honesty (shared with harness)
Evidence-based state: no mastery from scaffolded success, coherent mastered/struggling, honest attempt counts, spacing schedule maintenance (date *math* is harness-supplied; date *decisions* are the model's). The harness remains the enforcement backstop (parse-repair, persistence, NACK).

### E. Boundary integrity (must not regress)
Injection resistance without payload service; state-lobby resistance (evidence-only profile updates); scope discipline per the spec's denylist; control-marker hygiene. These largely held via prompting on all three models — training data must include them so they survive the fine-tune (catastrophic-forgetting control).

## 4. Non-goals

- **Not a content expert.** Subject knowledge is pluggable (mode `spec`: base weights; mode `full`: corpus). Domain accuracy above the base model is out of scope.
- **Not the harness.** State persistence, stream scrubbing, schedule storage, profile trust enforcement stay in code.
- **Not the grader.** Evaluation of teaching quality remains external (rubric + judge); the model self-assessing its own pedagogy is explicitly distrusted.
- **Not a general assistant.** It holds the tutor frame; the injection trajectories test exactly this.
- **Not autonomous curriculum authorship.** It teaches the spec it is given; it does not invent courses (grounding rules).

## 5. Interfaces and the thin-prompt hypothesis

Runtime inputs: (1) a *thin* runtime prompt, (2) the course spec, (3) learner profile + dates from the harness, (4) conversation. Outputs: teaching turns + the state block.

**Thin-prompt hypothesis (testable):** today's teaching policy (~8K chars, ~35 imperatives + a growing recency reminder) is the *training spec*, not the runtime prompt. After training, the runtime prompt should shrink to identity + course-spec pointer + harness contract (~1K chars), because clusters A–C live in weights. **Measured success = gate pass-rate at thin prompt ≥ prompted-Opus at full prompt.** The recency reminder's growth is the smell that prompting is being used as a load-bearing substitute for training; the trained model should need almost none of it.

## 6. Form factor and base requirements

- **Adapter (LoRA-class) on an open-weights instruct base** — weight access is required for DPO-style preference training (closed APIs cannot do this; EXP-001 shows prompt transfer fails, so an API-side "preference layer" is not a substitute). Adapter over full fine-tune: cheap iterations, swappable per experiment, and preserves the Phase 6 "shared pedagogy backbone + per-domain adapters" option.
- Base-model requirements: (a) instruct-following strong enough to hold cluster E via light prompting pre-training; (b) adequate multilingual competence for the pilot domains (Spanish A1 is a low bar; domain B may raise it); (c) trainable on the project's budget — the Phase 1 feasibility matrix (Qwen/Llama-class candidates) decides the exact base.
- Context budget: must hold thin prompt + course spec (~15K tokens mode `spec`) + session; 32K+ context suffices.

## 7. Training recipe (Phase 4, concretized by what we already have)

**SFT (behavior demonstrations):**
- Passing transcripts from the behavioral gate (Opus 12/12 runs) = positive demonstrations of clusters A–E, already move-annotated by construction (trajectory criteria label what each turn demonstrates).
- The real-session transcript(s), post-audit-fix behaviors.
- Synthetic expansion: simulated-student personas (Phase 1 artifact) × units × both pilot domains, generated by a strong model executing the policy, filtered by the judge. Multi-domain from the start (Spanish A1 + domain B) to force domain-generality of the moves.

**Preference pairs (the measured failure axes — each already has real rejected samples):**
| Axis | Chosen | Rejected (source) |
|---|---|---|
| Withholding | content hint under pressure | key dump (grok t04) |
| Generation | immediate in-scope input | unit-lock refusal (gemini t12) |
| Discourse | in-character recast | English mid-task grading (opus+gemini t13) |
| Error treatment | right-first-error, one only | wrong-first / multi-correct (gemini t10, opus round-1 t10) |
| Sequence | full input-first sequence | omitted middle moves (grok, multiple) |
| State honesty | evidence-based state | mastery inflation (real session 1) |

**Eval during training:** the 13-trajectory gate + blind judge, run at thin prompt, per checkpoint. Held-out: trajectories on domain B (never trained), then Phase 5's corpus-only domain C.

## 8. Success criteria

1. **Gate:** ≥ Opus-at-full-prompt pass rate (12/13+ incl. t13-4 roleplay purity — the convergent ceiling must fall) **at thin prompt** on the trained model.
2. **Transfer (the thesis, Phase 5):** same adapter + unseen course spec (domain C, mode `full`) sustains clusters A–C per the frozen rubric, beating base+prompt and base+corpus baselines by the pre-registered margin.
3. **No regression:** cluster E intact; content accuracy (keys, denylist) not degraded vs base.
4. **Efficiency corollary:** thin prompt ⇒ smaller cached prefix and cheaper turns than the prompted alternative.

## 9. Open questions (for countersign and Phase 1)

1. Base model choice and size floor — does discourse management have a parameter threshold? (Feasibility matrix decides candidates; gate-at-thin-prompt decides empirically.)
2. Should the state block move to a structured tool-call channel during training (cleaner supervision) or stay in-band (matches current harness)?
3. How much cluster-E data is needed to prevent safety/boundary regression?
4. Is one adapter per CEFR band/domain family needed, or does one pedagogy adapter truly generalize (the Phase 6 question, pulled forward as a design constraint)?
5. Judge validity: the blind referee is currently one model family; Phase 1's rater protocol (human raters, agreement targets) must anchor it before training-eval loops depend on it.
