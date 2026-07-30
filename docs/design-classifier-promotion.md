# Pre-registration: intent-signal classifier, shadow → blocking (§4.3 gate)

**Opened:** 2026-07-30 · **Author:** ⬛ Claude · **Status:** CRITERIA FROZEN — no results collected at write time
**Trigger:** live incident 2026-07-30 session 133545 — a learner wrote "I do
not understand what you are asking. Too advanced for me", the regex
intent detector missed it (it matched only the contracted "don't"), the
turn routed to ordinary conversation, and the gate held the reply: the
learner got SILENCE. The repair I shipped first was MORE REGEX — a §4.2
violation ("regex for judgment is a smell"; user directive 2026-07-28)
patching an instance while the lawful generator (tutor/signal_classifier.py,
built, working, shadow-only since 2026-07-28) sat one flag away.

## What is being decided

Whether `SIGNAL_CLASSIFIER_BLOCKING=true` for the INTENT signal family —
i.e. the LLM classifier's labels become authoritative for routing, with
regex demoted to fallback when the classifier is unavailable.

**In scope (intent — judgment):** help_request, topic_request,
meta_comprehension, non_understanding, boredom.
**Out of scope (surface — legitimately regex, §4.2):** greet, estoy, name,
gusta, origin, polite, topic_vocab, spanish_ok, english_only, and every
pack-key surface scan. These stay pattern-matched and are NOT part of this
decision.
**Stays shadow regardless:** content_offer, self_flagged_form
(OBSERVATIONAL_SIGNALS — §2.1a architecture clause holds them out).

## Frozen criteria (written before any measurement)

**Evaluation set (frozen construction rule, not cherry-picked):** every
learner utterance from the last 20 real session logs under logs/sessions/
(chronological, no filtering, deduplicated verbatim), PLUS the AI-student
transcripts from the referee run. Utterances are labeled by ⬛ Grok in
`blind-score` mode — it sees the utterance and the label vocabulary ONLY,
never the regex output, never the classifier output, never this document's
hypothesis. Grok's labels are the reference standard.

**Primary gate (all must hold):**
1. **Recall on intent signals ≥ 0.90** for the classifier, measured
   against the blind reference, AND **strictly greater than the regex
   detector's recall** on the same set.
2. **Precision ≥ 0.85** for the classifier (a false "they're confused"
   derails a healthy turn; this is the cost of over-firing).
3. **No regression on any single signal:** for every in-scope signal, the
   classifier's recall ≥ regex recall − 0.05 (no signal may get worse by
   more than noise while the aggregate improves).
4. **Latency:** classifier p90 ≤ 1500 ms measured on the eval set; the
   existing 8 s timeout stays as the hard ceiling.
5. **Failure path proven:** with the classifier forced to fail/timeout,
   routing falls back to regex signals and no turn errors (test-pinned).

**Kill conditions (any one blocks promotion):**
- Classifier precision < 0.85 (over-firing risk to healthy turns).
- Any in-scope signal where classifier recall < regex recall − 0.05.
- Fallback path not proven by test.
- Cost per turn > $0.001 for the classifier call.

**Explicitly NOT criteria** (guarding against post-hoc rationalization):
overall "feels better", agreement rate with the regex (the regex is the
thing under suspicion — agreement with it is not evidence), or any metric
computed after seeing results.

## Decision rule

- All primary gates pass → promote intent signals to blocking; regex
  becomes the documented fallback; §4.2's "shadow-first, promotion-gated"
  is satisfied and the promotion is recorded in PEDAGOGY §4.2's
  enforcement row.
- Any kill condition → stay shadow, record the failure, and fix the
  classifier (prompt/model) before re-testing. The regex patch from
  2026-07-30 stays as the interim fallback either way.

## Measurement plan (executed only after this file is committed)

1. Extract the utterance set by the frozen rule → `evals/results/
   classifier-promotion-<stamp>/utterances.json`.
2. Blind-label with Grok (`blind-score`, vocabulary + utterances only).
3. Run both detectors over the same set; compute per-signal recall,
   precision, latency, cost.
4. Report against the table above; promote or don't.

**Author's stated expectation (recorded so it can be wrong):** I expect
the classifier to win on recall for meta_comprehension and boredom
(regex has no boredom pattern at all) and to be roughly equal on
help_request/topic_request. If precision fails, the likely cause is
over-labeling short Spanish answers as non_understanding.
