# Blind teaching-quality rubric v1 — FROZEN 2026-07-30

**Frozen before any transcript was graded, before the B0 soak completed,
and before the grader saw which arm produced which transcript.** Required
by the r9 referee's promotion bound (4): gate metrics measure whether the
tutor BREAKS FEWER RULES; this rubric is the only instrument that asks
whether it TEACHES BETTER.

## Task given to the blind grader

You will read a transcript of a conversation between an adult beginner
learning Spanish and an AI tutor. You do not know which system produced
it. Score the TUTOR only. Return STRICT JSON:
`{"scores": {"responsiveness": n, "teaching_move": n, "scaffolding": n,
"spanish_level": n, "coherence": n}, "one_line": "..."}` — each n is
1–5 (integers only).

## Dimensions (1 = bad, 3 = acceptable, 5 = excellent)

1. **responsiveness** — Does the tutor react to what the learner actually
   said? 1 = ignores the learner / pushes its own agenda / repeats a
   question already answered. 5 = every turn visibly builds on the
   learner's content, including their questions and confusion.
2. **teaching_move** — Does each turn actually teach (a model to imitate,
   a correction, a real elicitation)? 1 = chat with no teaching, or
   worksheet drilling with no communication. 5 = every turn carries a
   natural teaching move inside real conversation.
3. **scaffolding** — When new Spanish appears, is it made comprehensible
   at the moment it appears (gloss, cognate, context)? 1 = new words
   dumped bare, or the learner is left guessing. 5 = nothing arrives
   unexplained and support is stripped once known.
4. **spanish_level** — Is the Spanish pitched to a beginner? 1 = far too
   advanced or so trivial nothing is learned. 5 = consistently just
   beyond what the learner already produced.
5. **coherence** — Does the session feel like one conversation with a
   direction? 1 = disjointed topic-hopping or aimless loops. 5 = a
   through-line the learner could describe afterwards.

`one_line`: the single most important thing this tutor did well or badly.

## Scoring protocol (frozen)

- Transcripts are shuffled and stripped of arm labels, notes, model
  names, and costs before grading. The grader sees learner/tutor text only.
- Grader: a non-Grok model in blind mode (Grok is the referee elsewhere;
  it may run a parallel calibration pass that is NOT the reference).
- Composite = unweighted mean of the five dimensions.
- **Promotion bound (already frozen in design-planner-rounds.md):** B0
  composite ≥ A composite − 0.5.
- Report per-dimension means, not just the composite: a composite can
  pass while responsiveness (the dimension the incidents live in) falls.
- Small-N banner required if fewer than 10 transcripts per arm.
