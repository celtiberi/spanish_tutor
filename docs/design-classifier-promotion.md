# Pre-registration v2: intent-signal classifier, shadow → blocking (§4.3 gate)

**Opened:** 2026-07-30 · **Author:** ⬛ Claude · **v2 after ⬛ Grok countersign — all AMENDs adopted, no counters**
**Status:** CRITERIA RE-FROZEN 2026-07-30 — v1 was REJECTED as unfit before any measurement ran; **no promotion numbers have been collected against either version.**

**Trigger:** live incident 2026-07-30 session 133545 — a learner wrote "I do
not understand what you are asking. Too advanced for me", the regex intent
detector missed it (its pattern was contraction-shaped), the turn routed to
ordinary conversation, and the gate held the reply: the learner got SILENCE.
My first repair was MORE REGEX — a §4.2 violation patching an instance while
the lawful generator (tutor/signal_classifier.py, shadow-only since
2026-07-28) sat one flag away.

**Why v1 was rejected (recorded so the failure is auditable):**
1. **Sole-Grok gold** = single-annotator capture; the promotion would have
   been Grok-vs-Grok agreement laundered as measurement.
2. **Precision 0.85 was CRITERION DRIFT** — PEDAGOGY §8 E-CLASSIFIER SHADOW
   already froze P/R ≥ **0.90**; I silently loosened a frozen bar without a
   §7.3 reopen. That is precisely what §4.3 forbids, committed by the author
   of the §4.3 paragraph.
3. **The eval set could not answer the incident's question:** 15 real + 336
   AI-student utterances, with the English-distress class at ~1 item
   (0.3%). Both detectors could score "no regression" at zero coverage of
   the exact failure mode that started this.

## What is being decided

Whether `SIGNAL_CLASSIFIER_BLOCKING=true` for the INTENT signal family — the
LLM classifier's labels become authoritative for routing; regex demoted to
fallback for classifier timeout/failure only.

**In scope (intent — judgment):** help_request, topic_request,
meta_comprehension, non_understanding, boredom.
**Out of scope (surface — legitimately regex per §4.2, countersigned):**
word/phrase boundary membership (textnorm), pack-key and topic_vocab scans,
greet/estoy/name/gusta/origin/polite markers, and all wire-format parsing.
**Stays shadow regardless:** content_offer, self_flagged_form (§2.1a).
**Flagged for later demotion (Grok 2.3, not this gate):** spanish_ok /
english_only function-word counters are pseudo-judgment; they stay
non-blocking features until a separate round.

## Frozen criteria v2

**Reference labels (frozen procedure):** Dual-annotator gold.
(A) Primary labeler: a non-Grok model in blind mode (utterance + label
vocabulary ONLY — no regex output, no classifier output, not this document).
(B) Secondary: **human labels** (the USER) on a stratified subset of ≥40
utterances including ALL real-session positives for the five in-scope
signals plus a random real-session negative sample. Disagreements
adjudicated by a third pass (human wins on the human subset; otherwise mark
UNCERTAIN and exclude from the primary-gate denominator). Grok may run a
parallel blind audit for calibration but **Grok labels are NOT the reference
standard for promotion arithmetic.** Report Cohen's κ (or raw agreement) on
the dual-labeled subset; **κ < 0.60 → do not promote** (fix the vocabulary
first).

**Metric definitions (frozen, anti-gaming):**
- Multi-label: each in-scope signal scored independently (TP/FP/FN per label).
- Report BOTH macro-recall (unweighted mean over labels with support ≥ N_min)
  and micro-recall (pooled). **Primary gate uses macro**; micro is diagnostic
  (micro can pass while a rare label is dead).
- Parse failures / timeouts are NOT scored as empty-label successes; they
  count only toward the failure-path test.
- **N_min = 15** gold positives per signal for that signal to enter the
  primary gate; below that: "insufficient support — cannot promote that
  signal alone," and it stays shadow even if the aggregate passes.

**Primary gate (all must hold):**
1. **Macro-recall ≥ 0.90** for the classifier against the dual/human gold,
   AND strictly greater than regex macro-recall on the same set.
2. **Precision ≥ 0.90** on the union of in-scope intent labels. Rationale: a
   false intent arms §2.1 preemption and derails a healthy turn; aligned
   with §8 E-CLASSIFIER SHADOW. Lowering this requires a §7.3 reopen naming
   the new number **before** data.
3. **No per-signal regression:** for every in-scope signal with support ≥
   N_min, classifier recall ≥ regex recall − 0.05.
4. **Latency:** classifier p90 ≤ 1500 ms on the eval set; 8 s timeout stays
   the hard ceiling.
5. **Failure path proven:** with the classifier forced to fail/timeout,
   routing falls back to regex and no turn errors (test-pinned).

**Kill conditions:** precision < 0.90; any supported signal with recall <
regex − 0.05; fallback path unproven; cost/turn > $0.001; κ < 0.60.

**Evaluation set (frozen construction rule v2):**
1. **REAL:** every learner utterance from the last 30 chronological
   `logs/sessions/*-conversational-web.jsonl` sessions (jsonl only; exclude
   `*-md`, `controller-demo*`, `ai-student*`). Deduplicate verbatim; drop
   `(session open)` and blanks.
2. **AI:** learner utterances from ONE pinned referee student tree — the
   path is recorded in `utterances.json` before labeling.
3. **CRITICAL-CLASS BANK** (`evals/critical_class_bank.json`, written
   BEFORE any labeling or detector run; **not** mined from classifier
   misses): ≥30 distress/help paraphrases covering expanded vs contracted
   negation, "too advanced/hard/fast", "what are you asking" / "I don't
   follow" / "I'm lost", "no entiendo" / "no comprendo", how-say help, and
   topic fatigue / boredom. Evaluation items only — they may never be
   pasted into the classifier's system prompt after freeze.
4. **Three scorecards reported:** (a) REAL-only, (b) AI-only, (c)
   CRITICAL-CLASS. **All primary gates must pass on (a) and (c)**; (b) is
   diagnostic.
5. A signal with < 15 gold positives across (1)+(3) cannot be promoted alone.

**Explicitly NOT criteria:** "feels better", agreement with the regex (the
regex is the thing under suspicion), or any metric defined after seeing
results.

## Decision rule

All gates pass on REAL and CRITICAL-CLASS → promote intent signals to
blocking; regex becomes documented fallback; record in §4.2's enforcement
row. Any kill condition → stay shadow, record the failure, fix the
classifier, re-test. The 2026-07-30 regex patch remains the interim fallback
either way (tactical debt, not architecture).

**Author's stated expectation (recorded so it can be wrong):** classifier
wins decisively on the CRITICAL-CLASS bank (regex has no boredom pattern at
all and contraction-shaped negation patterns); roughly ties on REAL where
most utterances are plain Spanish answers with no intent signal.
