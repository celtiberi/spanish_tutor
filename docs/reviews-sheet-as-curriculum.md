# Review: the character sheet IS the course pack (2026-08-03)

> **Vocabulary correction (same day, Grok-countersigned —
> docs/reviews-sheet-vocabulary.md):** this doc's title/keys predate the
> terminology ruling. The sheet is a DOMAIN MODEL + LEARNER MODEL, never
> called a curriculum; payload keys shipped as `domain_scope` /
> `domain_targets_not_yet_touched`; data dir is `domain/spanish_a1/`.
> Filename kept for the audit trail.

**USER directive:** "The character sheet IS THE COURSE PACK. It contains
everything that we are trying to measure about the student's ability…
if we can show the AI what we want the student to learn it can generate
its own plan/course very easily. If the AI can't create a plan then we
need a better character sheet." Follow-up: "delete the course pack —
look at it for grading material/character sheet things that should move."

**Outcome:** prose pack (`course_packs/spanish_a1/`, pack.md + 6 units)
DELETED. Curriculum DATA relocated to `curriculum/spanish_a1/`
(association table = vocabulary target inventory, asset sidecar, scenes).
B0 "brief" arm deleted with it (it fed on the pack; referee + blind grade
had already halted it). Law: ENGINEERING.md §3.3 amendment addendum.

## What the pack audit found (full mining report: agent run 2026-08-03)

- **29 misconception entries** (M-1.1…M-6.6); only 1 fully covered by the
  sheet's ERROR_PATTERN_CATALOG, 4 partial, 24 missing.
- **Frozen form inventories** across 6 units; the sheet tracked 7 forms,
  with wrong content in three: `numbers_0_20` (pack law is 0–100),
  `present_regular_ar_er_ir` morphology teaching *me gusta / prefiero*
  (both OUT OF SCOPE per the pack), ser/estar paradigms missing plural
  forms. 18 target-form gaps overall.
- **Scope contract**: deferred-A1 list, out-of-scope decline list,
  recognition-only categories, LatAm default variety.
- **Measurement ideas**: task success criteria (T-x.y), grading
  tolerances, unit dependency graph, justification-before-answer
  protocol for ser/estar.

## Absorbed into the sheet (this commit)

1. `format_sheet_for_prompt` payload gains `curriculum_scope` (deferred /
   out-of-scope / recognition-only / variety law) and
   `curriculum_targets_not_yet_touched` (association-table inventory by
   theme, minus the learner's lexicon). Blank-learner sheet ≈ 14.2k chars
   — the sheet is now the whole curriculum artifact the model plans from.
2. `FORM_INVENTORY` + 7 target forms: `ser_estar_contrast`,
   `plural_formation`, `gender_exception_nouns`,
   `subject_pronouns_prodrop`, `negation_questions_no_auxiliary`,
   `question_words_inventory`, `profession_no_article`. Existing sheets
   backfill on load; `numbers_0_20` → `numbers_0_100` with state carried.
3. Fixed wrong morphology: regular-verbs paradigm now hablar/comer/vivir
   (gustar/preferir removed), ser/estar paradigms complete, numbers 0–100
   with the one-word/three-word writing law.
4. `ERROR_PATTERN_CATALOG` + 27 mined misconception ids with `source`
   M-IDs, **empty detect/resolve by design** — the model diagnoses and
   records via the sheet tool; regex judgment of Spanish stays retired.

## Deliberately NOT absorbed (with reasons)

- Teaching sequences, reveal rules, spacing prose — how-to-teach; the
  model's job (PEDAGOGY.md). This was the pack's category error.
- Seed dialogues, SI items, answer-keyed practice items — the model
  generates in-scope content (§1.1).
- Task success criteria (T-x.y) — good future material for evals/ blind
  grading rubrics, not for the sheet. Parked here.
- Example-only vocabulary (nación, flor, médico…) — rule examples, not
  targets; the grammar forms carry those rules now.
- M-1.3 (buenas-noches avoidance) — avoidance isn't an error pattern.
- Missing table keys the miner flagged (function words, numbers 21–29 as
  lexemes) — grammar-side forms cover them; the lexicon tracks content
  vocabulary.

## Known accepted losses

- `weather_hace` catalog entry + a few association keys (calor/frío…)
  were never pack-scoped; they stay (the sheet is the authority now).
- Accent-sensitive grading (M-2.5/M-4.4/M-6.6) can't run through
  `fold_prose` (NFD accent-strip); the model grades accents itself via
  the tool. Recorded, not built.
