

---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-26 20:41 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll research comprehensible-input and repair evidence independently, then pressure-test the project's four product choices against that literature rather than the overview's framing.## Research round — Comprehensible Input & Comprehension Repair  
**Author:** Grok (independent second author)  
**Date:** 2026-07-26  
**Subject inlined:** `docs/system-overview.md` (as of 2026-07-26) + product choices (a)–(d)  
**Status:** adversarial research adjudication — not a countersign of the author’s framing

---

### 1. Independent picture (dated pins)

**Pin 2026-07-26 — What the evidence actually supports**

Comprehensible input (CI) is **necessary exposure**, not a complete pedagogy. Krashen’s *i*+1 (1982) remains a useful design heuristic and is still cited by ACTFL’s target-language guidance, but mainstream instructed-SLA treats pure “just make it clear” input as **under-specified**: acquisition also needs interaction, attention to form, and output opportunities.[[1]](https://www.researchgate.net/publication/31062007_Negotiation_for_Meaning_and_Peer_Assistance_in_Second_Language_Classrooms)

**Modified input vs interactional modification.**  
Loschky (1994, *SSLA*): three conditions for L2 Japanese — (1) unmodified, no interaction; (2) premodified, no interaction; (3) unmodified + negotiated interaction. **Moment-to-moment comprehension was highest under negotiated interaction**; the two non-interaction groups did not differ reliably on comprehension. That is the load-bearing empirical pin: **repair-through-interaction beats “write simpler sentences once and hope.”** Premodification alone is weak insurance.[[2]](https://eric.ed.gov/?id=EJ491191)

Related work (Ellis, Tanaka & Yamazaki 1994; Gass & Varonis 1994; Long Interaction Hypothesis line) converges on: interactional modification reliably improves **comprehension of the current message**; the leap to **durable acquisition** is weaker and more task-/feature-dependent. Design rule for a tutor: prioritize **same-message renegotiation**, not only a shorter paraphrase.

**Negotiation of meaning & comprehension checks.**  
Classic NfM inventory (Long 1996; Loewen review 2018): clarification requests, confirmation checks, comprehension checks after breakdown.[[3]](https://www.academia.edu/69921006/Comparison_of_Graduated_Prompt_and_Mediational_Dynamic_Assessment_and_Static_Assessment_with_Young_Children_Alternative_Assessments_of_Handicapped_A_Series_of_Technical_Reports_and_Working_Papers_Technical_Report_No_2)  
Foster & Ohta (2005, *Applied Linguistics*): in real classroom peer talk, textbook NfM moves are **relatively rare**; productive help often looks like **scaffolding / co-construction**, not ritual “Do you understand?” The implication for product design: **detect breakdown and re-mediate meaning**, do not ship empty comprehension-check turns as pedagogy. Teacher-facing “¿Entiendes?” without a verification task is low-information and often face-saving “yes.”

ACTFL still recommends **frequent comprehension checks**, but with **non-default-to-English** modalities (thieves-up, A/B, rearrange visuals, choose summary) — not English gloss as first resort.[[1]](https://www.researchgate.net/publication/31062007_Negotiation_for_Meaning_and_Peer_Assistance_in_Second_Language_Classrooms)

**Target-language ratio.**  
ACTFL (standing guidance, still current as of 2026-07-26): **≥90% of classroom time in the target language**; L1 ≤ ~10%, reserved for strategic purposes (brief concept that would take too long to mime; private deeper processing; orientation to method). English must **not** be the default meaning-check channel, or learners wait for the translation.[[1]](https://www.researchgate.net/publication/31062007_Negotiation_for_Meaning_and_Peer_Assistance_in_Second_Language_Classrooms)

This is a **policy target**, not an RCT-derived optimum for A1 adults. It is the strongest **institutional** pin available; empirical classroom studies show wide variance in actual TL% and frequent teacher under-shoot.

**Judicious L1 (how much English for A1 adults).**  
There is **no trustworthy single percentage** (e.g. “12% English optimal at A1”) from high-quality meta-analysis. The evidence cluster is qualitative/quasi-experimental:

| Claim | Status (2026-07-26) |
|--------|---------------------|
| Exclusive TL can raise anxiety / suppress participation for some adults | Supported (e.g. Eldridge 1996; classroom reports summarized in secondary reviews)[[4]](https://eric.ed.gov/?id=EJ728164) |
| Planned, brief L1 (vocabulary establish, sandwich, task clarify) can improve efficiency and oral production vs pure L2-only | Supported in small interventional studies (e.g. Yüzlü 2020 sandwich/systematic L1; Butzkamm sandwich tradition)[[5]](https://scholarspace.manoa.hawaii.edu/bitstreams/e0082a96-889f-4e81-b736-6448c41581aa/download) |
| Open dual-subtitle / English-heavy teacher talk reduces forced meaning-making | Supported by ACTFL rationale and CI classroom practice literature |
| Exact optimal L1 share for A1 adults | **Not established** — treat “mostly Spanish, English as instrument not medium” as the adjudicable design, not a fake decimal |

For **true zeros**, strategic L1 early often prevents affective collapse. For **false beginners**, the same L1 becomes a crutch. The product’s “blank sheet = unknown” is the right framing **if** placement discovers which path the learner is on within 1–3 turns.

**TPRS / story-based CI.**  
Practitioner-adjacent comparisons (Dziedzic 2012; various TPRS vs “traditional” / “communicative” classroom studies summarized in CI advocacy literature) often report **TPRS ≥ comparison on receptive measures**, sometimes stronger oral/written gains despite less forced production.[[6]](https://www.jstor.org/stable/44487746)  
**Quality caveat (do not over-claim):** many studies are small-N, quasi-experimental, teacher-confounded, and published outside top-tier SLA journals. Transferable mechanisms that survive skepticism: **high-frequency recycling, circling questions on the same narrative, meaning before form, brief L1 for new lexical items, then stay in TL**. TPRS is **not** pure Spanish-only; it is often more L1-tolerant for vocab setup than the product’s English-wall rhetoric implies.

**Arithmetic on ACTFL 90% (session-level illustration)**  
Assume a 20-turn tutor session, tutor speaks every turn, equal length:

- Allowed full-English (or mostly-English) tutor turns under a 90% TL session budget:  
  \(20 \times 0.10 = 2\) turns  
- If `english_wall` fires only when a **single turn** is majority English, a session can still fail 90% TL if many turns are 40–49% English (soft bilingual wallpaper).  
- Conversely, one strategic sandwich turn of 15 words Spanish + 2 English glosses may be **pedagogically optimal** but trip a naive word-ratio gate on a short turn:  
  Spanish words \(= 15\), English \(= 2\), total \(= 17\); Spanish ratio \(= 15/17 \approx 0.88\) (passes a 50% “majority Spanish” rule, fails a 90% turn-level rule).  
  **Therefore:** turn-level “mostly English” critical fault is **not the same** as ACTFL’s 90% session immersion. The product conflates these unless the threshold and exceptions are specified.

---

### 2. Verify / refute table — load-bearing claims in inlined `docs/system-overview.md` + choices (a)–(d)

| # | Claim (treated as DATA) | Ruling | Evidence / reason |
|---|-------------------------|--------|-------------------|
| 1 | CI = “mostly clear Spanish the learner can map to meaning” | **PARTIALLY VERIFY** | Necessary design goal; incomplete as learning theory (interaction + form + output matter). |
| 2 | Association (form↔image/context) before English gloss walls | **VERIFY** | Aligns with meaning-first CI, ACTFL visual/gesture support, referent binding. |
| 3 | Focus-on-form brief recast inside meaning | **VERIFY** (orthogonal to CI repair) | Supported by FF literature; not re-adjudicated here except that it must not replace comprehension repair when the problem is **receptive**. |
| 4 | Transfer = same form, new micro-context | **VERIFY** as practice design | Spaced/varied practice logic; separate from repair. |
| 5 | Every turn needs model/try/recast (hangout forbidden) | **AMEND** under CI lens | For true zeros mid-repair, a pure **comprehension verification** turn (image + A/B, no new try) can be more scientific than forced “try.” Contract may force production while input is still opaque. |
| 6 | `comprehension_repair`: same idea, simpler re-model, re-ask same intent, **no topic jump** | **VERIFY** core; **AMEND** mechanism | Topic continuity + same communicative intent is strongly supported (interactional modification of *this* message). “Simpler re-model” alone is **premodification** — Loschky shows negotiation > premod alone. |
| 7 | `comprehension_repair` **exempt from hard-break budget** | **VERIFY** with guardrails | Immediate repair after non-comprehension is correct; unlimited exemption without max depth / L1 exit risks repair loops and affective harm. |
| 8 | `comprehension_check` exists as enum/gate but **`select_mode` never returns it** | **VERIFY as architecture fact**; **REFUTE as complete pedagogy** | Soft fault `gate:comprehension_needs_check` is currently **dead**. Ritual CC mode is not required, but **verification after repair** is. |
| 9 | (a) Spanish-forward; English as **lifeline**, not dual-subtitle wallpaper | **VERIFY** | Matches ACTFL ≥90% TL + judicious-L1 consensus; “lifeline” must be operationalized. |
| 10 | (c) `gate:english_wall` = critical fault → rewrite | **VERIFY direction**; **AMEND metric** | Majority-English turns should rewrite. Must exempt tagged strategic sandwich / single-gloss / affect micro-L1, or gate fights good pedagogy. Session-level TL% still unmeasured. |
| 11 | (d) Blank sheet → **placement** with **wide-ceiling short Spanish**, not Hola ladder | **VERIFY vs ladder**; **AMEND vs pure ceiling** | Beats under-placing false beginners. Pure wide ceiling without fast step-down harms true zeros (affective filter). Closer to dynamic assessment / find-upper-bound then mediate down. |
| 12 | Teach images on association / comprehension repair bind referent↔Spanish | **VERIFY** | Strong CI support; images are interactional modification channel, not decoration. |
| 13 | Hard modes blocked while `turns_since_hard_break < 3`; repair & placement bypass | **VERIFY repair bypass**; budget number “3” is **engineering**, not evidence-derived | No SLA meta-analysis pins “3 turns.” Accept as product constant; do not cite as science. |
| 14 | Implicit: non-comprehension is detectable so repair mode can fire | **REFUTE completeness** | Overview states *what* repair does; does not pin reliable **signals** (¿cómo?, silence, off-target answer, English meta-comment, wrong yes/no). Without detectors, repair mode is aspirational. |

---

### 3. What the other author / product write-up **MISSED**

1. **Interactional modification ≠ shorter paraphrase.** The shipping description centers “simpler re-model.” Evidence prioritizes **dialogic renegotiation**: confirmation of meaning, choice questions, gesture/image, slower chunking, then re-ask. Premod-only is the weaker arm of Loschky (1994).

2. **Comprehension checks are not a mode you “forgot” — they are a *function* you under-specified.** Leaving `comprehension_check` unselected is fine if repair embeds **verification**. Soft-fault-only with unreachable mode is technical debt that hides a real pedagogical hole: **did the re-model work?**

3. **Graduated explicitness ladder (DA / Aljaafreh & Lantolf tradition; graduated prompts).** Repair should escalate:  
   same TL, simpler → visual/association → constrained choice (A/B or sí/no with content) → **one** L1 sandwich → only then English explanation. Jumping to English wall or looping TL forever both fail the ladder.

4. **TPRS contradiction.** TPRS often **uses L1 briefly to establish meaning of new items**, then floods TL. Product English-wall + “lifeline only” may be **stricter than the CI method family it partially channels**. Not fatal — but the write-up never reconciles this.

5. **False beginners vs true zeros share one blank-sheet path.** Wide-ceiling placement is good for unknowns **only if** one failed ceiling turn triggers a **true-zero soft path** (more visuals, slower, optional L1) rather than three more hard Spanish turns.

6. **No quantitative definition of `english_wall`.** “Mostly English” without: token ratio threshold, whether tags/acknowledge count, whether single glosses count, min turn length — is unadjudicable in evals.

7. **Repair loop economics.** Budget exemption without **max consecutive `comprehension_repair`** (e.g. 2) and without an L1 escape after repeated failure can dominate sessions and starve form_focus/transfer — ironically harming long-run acquisition while “doing CI.”

8. **Negotiation research caution (Foster & Ohta 2005):** do not fetishize NfM coding categories; value **assistance that restores shared meaning**. Product should log “meaning restored?” not “used simplification lexical density −20%.”

9. **ACTFL 90% is session immersion, not only critical-fault rewrite.** A tutor can pass every turn-level wall check and still deliver bilingual wallpaper at 60–70% Spanish. No session-level TL meter in the overview.

10. **Production contract during receptive failure.** Forcing `<try>` while the learner has not yet parsed the prior model can manufacture form errors that trigger form_focus — **mis-diagnosing comprehension failure as production error**.

---

### 4. Standing questions — answers (adjudicable)

| Question | Answer |
|----------|--------|
| Modified input vs interactional modification — which to privilege? | **Interactional modification of the same message**, with premodification as one tool inside it. |
| Efficacy of comprehension checks? | **Low** if bare “¿Entiendes?”; **moderate–high** if they force demonstration of meaning (A/B, image match, do-the-action). Prefer **post-repair verification** over a free-standing check mode. |
| How much English is optimal for A1 adults? | **No scientific exact %.** Design target: **≥90% Spanish tutor tokens session-wise** (ACTFL); English for (i) single-item establish, (ii) task clarity after TL failed, (iii) affect/crisis. True zeros temporarily higher L1; false beginners lower. |
| TPRS/story CI outcomes? | **Promising, method-quality mixed.** Steal circling + story recycling + brief L1 for new lexis; do not claim “TPRS proven superior” as settled science. |
| Target-language ratio findings? | Institutional pin **90%+ TL** (ACTFL); empirical classrooms often miss it; CI practitioners correctly note **incomprehensible 90% is worse than 80% comprehensible** — ratio is necessary-but-not-sufficient. |

---

### 5. Verdicts on product choices (a)–(d)

| Choice | Ruling | One-line adjudication |
|--------|--------|------------------------|
| **(a)** Spanish-forward; English lifeline | **COUNTERSIGN with operationalization** | Correct stance; “lifeline” needs a ladder and token budget, not vibes. |
| **(b)** comprehension_repair = same idea / simpler re-model / re-ask / no topic jump / budget-exempt | **COUNTERSIGN core; AMEND mechanism & bounds** | Keep same-intent + no topic jump + immediate availability; upgrade from “simpler re-model” to graduated interactional repair; cap loop depth. |
| **(c)** english_wall critical | **COUNTERSIGN as critical class; AMEND detection** | Keep rewrite on English-dominant turns; exempt strategic sandwich/gloss tags; add session TL telemetry. |
| **(d)** placement via wide-ceiling short Spanish, not Hola ladder | **COUNTERSIGN vs ladder; AMEND ceiling protocol** | Wide ceiling + short turns is right for unknowns; require rapid step-down and true-zero soft path. |

---

### 6. Concrete improvement proposals (ranked impact × cost)  
**Adjudicable = has a metric and a pass/fail you can run on logs by 2026-08-01 or later.**

| Rank | Proposal | Impact | Cost | How to adjudicate | Citations / basis |
|------|----------|--------|------|-------------------|-------------------|
| **1** | **Graduated comprehension-repair ladder (code + prompt)** after non-comprehension signal: (1) same intent, simpler TL + optional image; (2) constrained verify (A/B or image match); (3) one L1 sandwich on the opaque chunk; (4) only then English explain. Cap consecutive repairs at **2** before step (3). | **High** — fixes premod-only weakness + repair loops + true-zero drowning | **Med** (mode task text + mode_state counters + gate notes) | On labeled non-comprehension episodes: rate of **meaning restored within 2 tutor turns** ≥ baseline; English full-explain rate ↓; session abandon ↓ | Loschky 1994; ACTFL TL strategies; Butzkamm sandwich; DA graduated prompts |
| **2** | **Operationalize `english_wall`**: e.g. critical if Spanish token ratio \(< 0.50\) **and** ≥12 alphabetic tokens; **exempt** `<explain>` single gloss / marked sandwich; log session Spanish ratio (target ≥0.90 tutor tokens). | **High** — makes (a)(c) measurable | **Low** | Unit tests on fixture turns; session logs: critical rate vs false-positive sandwich rate | ACTFL 90%; arithmetic above |
| **3** | **Non-comprehension signal detector → force repair path** (learner: “no entiendo”, “¿qué?”, English meta, empty/minimal, answer mismatches last try intent). Do **not** route those to form_focus. | **High** — repair is useless if never selected | **Med** | Confusion matrix on 50 hand-labeled turns: precision/recall of detector; form_focus false trigger rate after opaque model | Long NfM; Foster & Ohta (assistance after trouble) |
| **4** | **Post-repair verification replace open re-ask when energy/affect limited**: image or A/B demonstrating the **same** proposition before free `<try>`. Temporarily relax “must try” if verify fails. | **Med–High** | **Med** | After repair, % correct verify before productive try; reduction in stacked form errors mis-tagged as production | ACTFL comprehension-check examples; CI meaning-before-production |
| **5** | **Placement protocol v2**: turn 1 wide-ceiling **short** Spanish (1 proposition); if fail signal → turn 2 step-down + image; if fail → mark `receptive.needs_english_scaffold` and allow sandwich. Never 4-step Hola ladder; never 4-step hard ceiling. | **Med** | **Low–Med** | Placement ≤3 turns classifies zero vs false-beginner with human agreement ≥0.8 on 20 sheets; boredom_risk after placement lower for false beginners vs ladder baseline | Dynamic assessment / ZPD; ACTFL “gist first” |

**Impact × cost scoring (explicit arithmetic, 1–5 scales)**  
Impact×Cost efficiency = Impact / Cost:

1. Ladder: \(5 / 3 \approx 1.67\)  
2. english_wall metric: \(5 / 2 = 2.50\) ← **best efficiency**  
3. Detector: \(5 / 3 \approx 1.67\)  
4. Verify-before-try: \(4 / 3 \approx 1.33\)  
5. Placement v2: \(3 / 2 = 1.50\)  

**Implementation order by efficiency then total impact:** **#2 → #1 / #3 (parallel) → #5 → #4.**

---

### 7. Bottom line (non-deferential)

The product’s CI stance is **directionally right and closer to ACTFL/Long than to pure Krashen monism**. The strongest choice is **(b)’s topic continuity + same intent + budget exemption for repair**. The weakest is treating **“simpler re-model” as sufficient repair** while `comprehension_check` is dead code and **non-comprehension detection is underspecified**. English-as-lifeline is evidence-compatible only if English is **late on a ladder**, not banned by a blunt wall nor invited as dual-subtitle wallpaper.

I do **not** countersign “we already do CI” without: (i) interactional repair ladder, (ii) measurable TL ratios, (iii) repair-vs-form_focus routing on receptive failure. Those three are the bar for the next engineering pass.

---

*End of Grok research round — Comprehensible Input & Comprehension Repair — 2026-07-26.*
