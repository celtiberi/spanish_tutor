# Pedagogy research sweep — synthesis and adjudication

**Date:** 2026-07-26
**Process:** 5 independent Grok research rounds (multi-modal sweep, one dimension each), each given `docs/system-overview.md` as data and told to verify/refute our design against 2010–2026 evidence. Claude (Fable 5) adjudicated. Round trails:

| Round | Dimension | File |
|-------|-----------|------|
| R1 | Corrective feedback | `docs/pedagogy-research-r1-corrective-feedback.md` |
| R2 | Comprehensible input & repair | `docs/pedagogy-research-r2-input-repair.md` |
| R3 | Retrieval, spacing, durability | `docs/pedagogy-research-r3-retrieval-spacing.md` |
| R4 | Task design, motivation, affect | `docs/pedagogy-research-r4-tasks-affect.md` |
| R5 | Multimodal & dual coding | `docs/pedagogy-research-r5-multimodal.md` |

**Citation verification (Claude, spot-checks on least-familiar pins):**
- Miller & Pan 2012 recast meta (IRAL): **verified** — avg weighted ES 0.38 as cited.
- Kim & Webb 2022 spacing meta (*Language Learning*): **verified** (98 ES / 48 experiments / N=3,411; equal ≈ expanding) — but reported g magnitudes vary by contrast (web summary g=0.76 imm / 1.15 delayed vs Grok's 0.58/0.80); **direction and design confirmed, magnitudes treated as ranges**.
- Lyu et al. 2025 chatbot meta (*IJAL*): **verified** — g=0.608 overall, g=0.645 affective, exact.
- Ammar & Spada 2006, Lyster & Saito 2010, Lyster & Ranta 1997, Loschky 1994, Foster & Ohta 2005, Cepeda 2008, Karpicke & Roediger 2008, Mayer CTML: known-real from training knowledge.
- Ye et al. 2026 (PLOS ONE, AI images): post-2025, **plausible, unverified** — treat as supporting, not load-bearing.

---

## 1. Where the system is vindicated (all rounds)

- **Conversation-as-vehicle + budgeted reactive form breaks** — countersigned as the right architecture family (Long-style focus-on-form) by R1, R2, R4.
- **form_focus ladder** (≥2 hits → contrast → produce) — R1's best grade (A−).
- **comprehension_repair core** (same intent, no topic jump, budget-exempt) — R2 countersign.
- **Selective teach images, never wallpaper** — R5 countersign (coherence principle).
- **TTS default on** — R5 countersign (L2 bimodal support).
- **Interest personalization** (sister, Río Dulce) — R4: "strongest cheap engagement lever you already have."
- **Blank-sheet placement over Hola ladder** — R2, R4 countersign.
- **Confidence caps / known-gate honesty** — R3 countersign (as anti-overclaim; not as durability).

## 2. Convergent findings (independent rounds agreeing = strongest signal)

**F1 — Production elicit after correction is under-enforced; recast-default is weakest at A1.** (R1 lead finding; R4 concurs from the affect side.) Prompts/elicitation ≥ recasts for low-proficiency production (Ammar & Spada 2006; Lyster & Saito 2010); ~70% of classroom recasts get no uptake (Lyster & Ranta 1997). Our `recast_without_try` soft fault graded D+.

**F2 — Purity rules should become graduated ladders with a late-but-legal L1 step.** R2 (repair ladder: simpler TL → constrained verify → **one L1 sandwich** → English explain) and R5 (image → **minimal L1 lifeline** after second failure) converged on this independently. L1-gloss research (Yoshii 2006; Choi 2016; gloss metas) says brief L1 is competitive-to-better for beginners; "lifeline" must be an operationalized rung, not vibes.

**F3 — Between-session durability is the biggest architectural gap.** (R3 lead; R1-P5 concurs.) Spacing g≈0.6–1.15 on delayed tests (Kim & Webb 2022); retrieval-after-success is the engine (Karpicke & Roediger 2008). We have **no decay, no due-queue**, `last_seen` written but never read, an **orphaned legacy scheduler** (`tutor/student.py` `review_schedule`, `lesson_flow.due_items`) never ported to the conversational path, and a progress score that is "a monotonic career high-water mark, not current retrievability."

**F4 — Instrument before more policy.** R1 (uptake + CF density), R2 (english_wall thresholds + session TL%), R3 (re-encounter success definition), R4 (affect actuators unmeasured), R5 (channel telemetry). Unanimous in spirit: most current debates are unfalsifiable in our own logs.

**F5 — Affect model too thin for adult WTC.** (R4 lead; R1, R2 concur on CF-density/repair-loop affect risk.) Anxiety is the strongest negative predictor of willingness-to-communicate; we track neither anxiety nor enjoyment, and existing labels have no policy actuators.

**F6 — Repair needs verification, and comprehension failure must not be misrouted.** R2: "simpler re-model" alone is the weak arm of Loschky 1994 (negotiation > premodification); post-repair constrained verification (A/B, image-match) is the missing function behind the dead `comprehension_check` mode; forcing free production mid-repair can manufacture form errors that misroute to form_focus.

## 3. Adjudications on contested invariants (Claude rulings)

**A1 — Teach-move contract survives; "try" gains a constrained form.** R2 and R4 both push for input-only turns (contract exception). Ruling: **no exception needed** — a constrained verify (A/B, image-match, sí/no with content) *is* a `<try>` under the contract. The change is mode-task guidance (repair/high-anxiety turns prefer constrained tries over free production), not a contract amendment. This simultaneously satisfies R1's elicit-enforcement and R4's evaluation-threat concern.

**A2 — `recast_without_try` escalates to critical only on hot patterns.** Accept R1-P2 as scoped: isolated conversational recasts stay soft; hot-pattern (≥2 hits) and form_focus contexts make a missing elicit critical. Constrained tries count (per A1).

**A3 — L1 lifeline becomes a ladder rung, not a wall breach.** Accept the R2/R5 convergent design: one short L1 gloss (≤6 words) is legal at rung 3 of repair or after a failed image association; `gate:english_wall` gains an exemption for tagged sandwich glosses; session-level Spanish-token ratio (target ≥0.90) becomes telemetry. The wall keeps rewriting majority-English turns.

**A4 — Spacing MVP accepted; flashcard surface rejected.** Accept R3's minimal scheduler (due date + 1→3→×2-cap-14 interval ladder + soft conversational re-encounter, max one due elicit per ~4 turns, invisible to the learner). Explicitly reject SM-2/Leitner UI as persona-hostile — as R3 itself did. Expanding-vs-equal A/B deferred (equal ≈ expanding in the meta).

**A5 — Scene restructure deferred, micro-goal visibility accepted.** R4-P2 (convergent info-gap scenes + complexity sequencing) is the right direction but high-cost; defer behind Tier 1–3. R4-P4 (learner-visible "today's task" + completion moment) is low-cost and accepted earlier.

**A6 — Budget constant "3" is a product hypothesis, not science.** R1/R4 both note no SLA pin exists for ≤1-hard-break-per-3-turns. Keep, label as engineering prior, A/B when telemetry exists.

## 4. Ranked improvement plan

**Tier 1 — Instrument + cheapest levers (do first; unlocks everything):**
1. **Telemetry change set:** per-turn `cf_type` / `cf_target` / `learner_uptake`, soft-CF density window, session Spanish-token ratio, image/TTS/text channel stack per turn, repair-episode outcome ("meaning restored within 2 turns?"). (R1-P3, R2-#2, R5 metrics)
2. **english_wall operationalization:** critical iff Spanish ratio <0.50 AND ≥12 alphabetic tokens; exempt tagged sandwich glosses. Unit-testable. (R2-#2)
3. **TTS rate + pause policy:** ~0.85–0.90 rate default, ≥400ms gap after `<model>` before `<try>`, slower/normal toggle. Highest comprehension-per-dollar change. (R5-R1)

**Tier 2 — CF and repair policy ladders:**
4. **Prompt-first CF:** first hit of a tracked pattern → form prompt (elicit with slot/clue) before pure recast; ≥2 hits → form_focus as today. (R1-P1)
5. **Hot-pattern elicit enforcement:** `recast_without_try` critical when pattern hot or mode form-focused; constrained tries satisfy. (R1-P2 + A1/A2)
6. **Graduated repair ladder:** simpler TL+image → constrained verify → one L1 sandwich → English explain; cap 2 consecutive repairs before the sandwich; non-comprehension detector routes to repair, never form_focus. (R2-#1/#3/#4, R5-R2)

**Tier 3 — Durability architecture:**
7. **MVP due-queue + soft re-encounter mode** + retrievability/status split (progress score uses retrievability; `known` stays evidence-historical) + transfer wired to delayed re-encounter (immediate transfer once, then enqueue). (R3-#1/#2/#3, R1-P5)

**Tier 4 — Engagement & polish:**
8. **Affect v2:** behavioral WTC proxy (latency, English-escape, one-word replies) + anxiety/enjoyment labels with concrete mode actuators. (R4-P1)
9. **Learner-visible micro-goal + task-done moment**; interest tags as task content on boredom signal. (R4-P4/P5)
10. **Image contiguity + referent stability:** Spanish caption on every teach image; stable identity cache keys + style freeze; channel budget on hard breaks (image XOR long explain). (R5-R3/R4/R5)
11. **Scene v2** (single convergent exit, info-gap roles, complexity sequencing) — deferred, revisit after Tiers 1–3. (R4-P2)

## 5. Governance

Per the project validation convention: **none of the above may be claimed "improved" on doc review**. Each accepted tier lands with (a) unit tests, (b) conv-gate trajectories where behavior is observable (`evals/run_conv_smoke.py`), and (c) the telemetry from Tier 1 so the pre-registered acceptance metrics in each round's proposals can actually be computed. R1's closing rule stands: no further stance-prose debates until uptake/density logging exists.

*Adjudicated and compiled by Claude (Fable 5), 2026-07-26. Round content is Grok's; rulings are Claude's; disagreements preserved in the per-round files.*
