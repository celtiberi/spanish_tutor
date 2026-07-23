# Course Pack v0.3 vs Modern Language-Teaching Research

**Date:** 2026-07-22
**Method:** two independent research tracks, cross-checked: (1) a Grok research round with web search (`docs/pedagogy-research.md`); (2) a Claude deep-research workflow (5 search angles → 23 sources fetched → 110 claims extracted → adversarial verification). The workflow's verification votes were cut short by a session usage cap: 2 claims formally verified, 23 carried as sourced-but-unverified (quota errors, **not** refutations). Where both tracks independently surfaced the same finding, it is marked **[convergent]**; single-track findings are marked **[single-source]**.

---

## 1. Verdict in one paragraph

The pack's *micro*-pedagogy is well supported by the evidence; its *macro*-architecture is not how modern language teaching builds a course. Explicit form-focused instruction is robustly effective — and the evidence suggests **beginners benefit from it most** — so the rule tables, misconception remediation, and attempt-before-reveal design rest on solid ground. But the pack is a **grammar-chapter spine with almost no Spanish input, no communicative tasks, and no multi-day practice schedule**, which is the profile of a 1990s "focus-on-forms" textbook, not of CEFR-era, task-based, input-rich practice. Grok's summary line is fair: *a strong diagnostic grammar tutor; a weak language course.*

---

## 2. What the evidence says (cross-checked)

### Explicit grammar instruction — the pack's core bet holds

- Focused L2 instruction produces large gains vs exposure alone (Norris & Ortega 2000, 49 studies, d≈0.96). **[convergent; workflow-verified 2-1]**
- Explicit instruction outperformed implicit in that era's studies (**[convergent; workflow-verified 3-0]**), and in the Goo et al. (2015) update. Spada & Tomita (2010, 41 studies) found the explicit advantage holds for both simple and complex features, and appears on free-production measures, not just discrete tests. **[single-source (workflow), consistent with both tracks]**
- Kang, Sok & Han (2019; 54 studies, N=5,051): form-focused instruction g=1.06 overall — and **novice learners gained most (g=1.45** vs 0.70 intermediate). Directly supports explicit teaching *at A1 specifically*. **[convergent on the meta; the novice moderator is workflow-only]**

**Two caveats the pack should respect:**
1. In Kang et al., **implicit instruction was more durable on delayed posttests** (g=1.76 vs 0.77 explicit) — a reversal of the older finding. Explicit-first gains fade without meaning-focused consolidation. **[workflow-only]**
2. Effect sizes partly reflect **measurement bias**: many studies test the kind of discrete knowledge explicit teaching produces. **[convergent]**

### Task-based teaching — real but oversold

TBLT programs show positive effects (Bryfonski & McKay 2019, d=0.93), but a corrected re-analysis (2022) cut this to **g=0.61** and documented methodological flaws in the original. **[workflow-only — a nuance Grok's account missed]** Net: a task layer is worth adding; it is a complement to form work, not a replacement. Norris & Ortega themselves found focus-on-form and focus-on-forms statistically *equivalent* on their measures.

### Corrective feedback — supports our hints, with one sharp constraint

- Oral corrective feedback works and is durable (Lyster & Saito 2010, 15 classroom studies; Li 2010, 33 studies). **[convergent]**
- **Prompts beat recasts**, especially on free production: in Lyster & Ranta's classroom data, recasts produced learner uptake only ~31% of the time and no self-repair, while elicitation led to uptake ~100% of the time. This is strong support for the teaching policy's hint-before-answer design. **[convergent]**
- **The constraint:** prompt-based negotiation **presupposes existing knowledge** — a learner cannot self-correct a form they have never acquired, and recasts/models serve low-proficiency learners better than prompts on first exposure. **[workflow-only — the sharpest finding for us]** Our current reveal policy applies hint-escalation uniformly; at true first exposure it risks empty Socratic loops (the exact failure mode the plan's §2.5 warns about).
- Li (2010) adds: implicit feedback's gains held up *better over time* than explicit correction's. Recasts aren't useless — they're the wrong default, not a wrong tool. **[workflow-only]**

### Spacing and retrieval — we implement the weakest version

Spacing effects in L2 are medium-to-large, and **longer, multi-day gaps beat same-session review on delayed tests** (Kim & Webb 2022; Cepeda et al.). **[single-source (Grok), consistent with the broader literature]** The pack/policy's `revisit_queue` is same-session only — real spacing needs cross-session persistence (state currently dies with the session). Attempt-before-reveal is genuine retrieval practice. **[convergent]**

### CEFR and what modern A1 actually contains

CEFR (2001; Companion Volume 2020) defines levels by **action-oriented can-do statements**, not grammar inventories. A conventional A1 syllabus carries lexis domains (family, food, time, places), *hay*, *ir*, basic sociopragmatics — most of which we explicitly deferred. Unit 1's objectives are already can-do-shaped; Units 2–6's are grammar-shaped. **[convergent]** Modern products split: Babbel (dialogue-first + explicit grammar tips — our nearest cousin), Duolingo (CEFR-aligned functional skills + massive spaced review), Dreaming Spanish (pure comprehensible input, no grammar), iTalki (human conversation tasks). None ships a bare grammar spine. **[Grok-only]**

### Comprehensible input

Input is necessary for acquisition on every account — hardline Krashen claims are overclaimed, but no serious position says A1 learners thrive on rule tables plus drill items with minutes of actual Spanish exposure. The pack has **no dialogue texts, no graded reading/listening, no story cycle**. This is its biggest structural gap. **[convergent]**

---

## 3. Scorecard: pack/policy bets vs evidence

| Bet | Evidence verdict |
|---|---|
| Explicit rules + tables at A1 | **Supported** — beginners gain most from form-focused instruction |
| Misconception IDs + targeted remediation | **Supported** (and doubles as eval gold labels) — keep and extend |
| Attempt-before-reveal, progressive hints | **Supported for practiced material**; **unsupported at first exposure** (prompts presuppose proficiency — model first) |
| Light-touch recasts in policy | **Acceptable as secondary**; ensure learner re-produces the corrected form (prompt-style) |
| English metalanguage | **Acceptable for adult explicit work; over-used** — every English minute is a lost Spanish-input minute |
| Closed vocabulary sets | **Good for eval validity; bad for can-do coverage** |
| Same-session revisit queue | **Weak** — spacing gains need multi-day schedules |
| Grammar-chapter unit spine | **Contradicts modern practice** (CEFR, TBLT, every major product) even though its content is individually sound |
| No input texts, no tasks | **The two clear structural gaps** |

---

## 4. Ranked recommendations (merged from both tracks, adjudicated)

1. **Add a comprehensible-input block to every unit** — an 8–15-turn recycled dialogue or micro-story at the unit's level, with comprehension checks *before* production drills. Biggest gap, cheapest fix, and it gives the tutor material for input-first teaching.
2. **Add 1–2 can-do tasks per unit with non-key success criteria** (e.g. "complete a 6-turn stranger introduction with correct register") and rewrite unit objectives as can-do statements. Aligns with CEFR and gives Phase 1 eval a task-completion metric beyond answer-matching.
3. **Calibrate the reveal policy by familiarity** (teaching-policy change, not pack): first exposure → worked example / model first; practiced material → prompt-escalation as now; after any remediation the learner re-produces the full corrected form. This resolves the sharpest evidence-based critique of hint-first tutoring at A1.
4. **Persist student state across sessions and schedule spaced returns** (app + policy change): failed items reappear next session, then at expanding intervals; interleave *ser/estar/tener* items rather than blocked unit mastery. The state plumbing already exists; it needs cross-session storage and a due-date field.
5. **Convert half the mechanical drills to structured-input items** (VanPatten): learner selects *meaning* from form (¿"está en casa" — location or identity?) before producing conjugations. Keeps keys and misconception IDs; changes what the item exercises.
6. **Keep** the misconception taxonomy, explicit explanations, closed sets *for evaluation scenarios*, and scope honesty — these are the pack's strengths and the research program's measurement backbone.

---

## 5. Research-program implication (why we shouldn't just chase "modern")

There is a real tension between **building the best A1 product** and **running the Phase 2/3 experiments**: the grammar-core pack's measurability (misconception IDs, keyed items, closed sets) is exactly what makes diagnostic-accuracy and over-help metrics computable. The recommendations above were chosen to *add* input/tasks/spacing **without destroying measurability** — tasks get explicit success criteria, input blocks get comprehension checks, structured-input items keep keys. Recommendation: apply #1–#5 as pack v0.4 + teaching-policy v0.2, and add "input-richness" and "task completion" to the Phase 1 rubric discussion.

---

## Sources

- Norris & Ortega (2000), *Language Learning* — [doi:10.1111/0023-8333.00136](https://onlinelibrary.wiley.com/doi/abs/10.1111/0023-8333.00136)
- Spada & Tomita (2010), *Language Learning* — [doi:10.1111/j.1467-9922.2010.00562.x](https://onlinelibrary.wiley.com/doi/10.1111/j.1467-9922.2010.00562.x)
- Goo, Granena, Yilmaz & Novella (2015), in *Implicit and Explicit Learning of Languages* — [benjamins.com/catalog/sibil.48.18goo](https://benjamins.com/catalog/sibil.48.18goo)
- Kang, Sok & Han (2019), *Language Teaching Research* — [researchgate.net/publication/326330342](https://www.researchgate.net/publication/326330342_Thirty-five_years_of_ISLA_on_form-focused_instruction_A_meta-analysis)
- Bryfonski & McKay (2019), *Language Teaching Research* — [doi:10.1177/1362168817744389](https://journals.sagepub.com/doi/abs/10.1177/1362168817744389); corrected re-analysis (2022) — [doi:10.1177/13621688221131127](https://journals.sagepub.com/doi/abs/10.1177/13621688221131127)
- Lyster & Saito (2010), *SSLA* — [cambridge.org](https://www.cambridge.org/core/journals/studies-in-second-language-acquisition/article/abs/oral-feedback-in-classroom-sla/4999EE1C8379B2BF026B148EAF373CA1)
- Li (2010), *Language Learning* — [researchgate.net/publication/229940242](https://www.researchgate.net/publication/229940242_The_Effectiveness_of_Corrective_Feedback_in_SLA_A_Meta-Analysis)
- Lyster & Ranta (1997), *SSLA* — [escholarship.mcgill.ca](https://escholarship.mcgill.ca/downloads/0p096b851)
- Ammar & Spada (2006) on proficiency × feedback type — [ERIC EJ924056](https://files.eric.ed.gov/fulltext/EJ924056.pdf)
- Kim & Webb (2022), *Language Learning* (spacing meta-analysis) — via Grok round, single-source
- Council of Europe, CEFR Companion Volume (2020) — action-oriented descriptors
- Grok independent research round: `docs/pedagogy-research.md`
