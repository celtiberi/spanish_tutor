

---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-26 20:40 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll research SLA corrective-feedback meta-analyses (2010–2026) and map them against your four design choices, without deferring to the overview.# Grok independent review — Oral / Written Corrective Feedback (SLA pin-down)

**Role:** independent second author (contrarian). Inlined overview treated as DATA only.  
**Date of this review:** **2026-07-26**  
**Dimension:** ORAL/WRITTEN CORRECTIVE FEEDBACK for adult beginners in conversational tutoring  
**Subject:** `docs/system-overview.md` (status date **2026-07-26**) design choices (a)–(d)

---

## 1. My own picture (dated pins)

### 1.1 What the field actually says (2010–2026, meta-analyses first)

| Pin date | Source | Claim (effect sizes where published) | Implication for ml_teacher |
|----------|--------|--------------------------------------|----------------------------|
| **2010-06** | Li, S. *Language Learning* 60: CF meta-analysis (oral + lab + classroom) | CF overall **medium–large** positive vs no-CF controls; **explicit CF > implicit** on immediate and short-delayed posttests; implicit can catch up on longer delayed measures | Default soft recast-only is *not* the strongest learning lever; explicit/metalinguistic has short-term edge |
| **2010-04** | Lyster & Saito *SSLA* 32: classroom oral CF, **15 studies, N = 827** | CF durable; **prompts > recasts** on free constructed response; reported between-group *d* for recasts ≈ **0.53** (medium); prompts larger | For production accuracy, push-out (prompt/elicit) beats pure reformulation |
| **2006-10** | Ammar & Spada *SSLA*: prompts vs recasts by proficiency | **Low-proficiency** learners: prompts **significantly better** than recasts; high-proficiency: roughly equal | **A1 / false-beginner product path is exactly the band where “always recast” is weakest** |
| **1997** | Lyster & Ranta *SSLA*: immersion uptake taxonomy | Recasts most frequent classroom CF; **~70% of recasts → no uptake**; prompts/elicitation/metalinguistic → more learner-generated repair | Recast without repair opportunity is common and often invisible to the learner |
| **2016** | Brown *LTR* 20: descriptive meta of OCF types | Recasts ≈ **57%** of classroom CF; prompts ≈ **30%**; grammar most corrected (~**43%**) | “Always recast” matches teacher habit, not optimal design for learning |
| **2015** | Kang & Han *MLJ*: written CF meta-analysis | Written CF improves accuracy; effect **mediated** by focus, proficiency, genre — not a blank check for unfocused correction | Text channel can make CF more durable **if focused**; unfocused density is a liability |
| **2012** | Miller & Pan meta on recasts | Average weighted ES for recasts ≈ **0.38** (small–medium) | Recasts work, but modestly — not “correct enough” as sole strategy |
| **2017–2021** | Arroyo & Yilmaz; Shintani & Aubrey; Yilmaz & Sağdıç (text CMC reformulations) | In **text-based SCMC**, **immediate** reformulation > end-of-task delayed for Spanish/English targets | When product is typed chat, immediate short recast is better supported than delayed bundle |
| **2023-02** | Xu & Zeng *Front. Psychol.* systematic review of CF **timing** (20 studies, 2006–2021) | **No universal winner** immediate vs delayed; moderators: modality, explicitness, delay length. Text-CMC leans immediate; pure CALL timing often null; F2F mixed | Do not treat “always immediate recast” as settled science — it is modality-contingent |
| **2021** | Van Ha et al. review of EFL OCF beliefs | Teachers worry **over-correction of one student** damages affect/participation; learners often *prefer* explicit types when asked | Density and public face-threat matter; private 1:1 tutor is not classroom-identical but still affect-sensitive |
| **2013** (synthesis) | Lyster, Saito & Sato (and teacher-report literature through 2024) | Excess CF can **interrupt communication**, raise anxiety, reduce willingness to speak | Hard-break budgeting is directionally right; soft-recast flooding is still a risk |

**Arithmetic (rough Cohen band):**  
Lyster & Saito recast *d* ≈ 0.53 → medium. Miller & Pan recast ES ≈ 0.38 → small–medium.  
If prompts routinely outrank recasts by ~0.2–0.3 *d* in classroom free production (Lyster & Saito qualitative result; Ammar & Spada low-proficiency interaction), then a recast-default product leaves an estimated **~0.2–0.3 SD** of accuracy gain on the table for A1 morphosyntax — non-trivial for a pedagogy-first research product.

### 1.2 What “good CF” looks like for *this* product (my synthesis)

For **adult A1 conversational Spanish**, 1:1, mixed **text chat + optional speech**:

1. **CF works** (Li 2010; Lyster & Saito 2010) — no-CF chat-buddy is pedagogically indefensible.  
2. **At low proficiency, prompts/elicitation ≥ recasts** for durable production (Ammar & Spada 2006; Lyster & Saito 2010).  
3. **Recasts need salience + opportunity to re-produce**; bare reformulation is often not noticed, especially morphosyntax (Lyster & Ranta 1997; Ellis & Sheen 2006 line).  
4. **Immediate CF is preferred when the signal is implicit** (recast/reformulation); **timing is less critical when CF is explicit** (Xu & Zeng 2023).  
5. **Text chat can make recasts *more* noticable** than oral (permanence, visual contrast) — so typed short recasts are more defensible than oral-only literature implies (Arroyo & Yilmaz 2017/2018; Shintani line).  
6. **Focused, sparse hard intervention** beats dense unfocused correction (Kang & Han mediation; teacher affect literature).  
7. **Wrong→right contrast + one forced production** is a hybrid of **explicit correction + prompt** — closer to high-effect designs than pure recast.  
8. **Density:** no clean meta-analytic “max corrections per turn.” Best proxies = communication interruption + anxiety (Van Ha 2021; Lyster et al. teacher reports). Budgeting hard breaks is wise; **always** soft-recasting every form error is *not* free.

### 1.3 My map of *our* stack (independent of author’s self-description)

| Layer | What it actually implements (from overview DATA) | SLA name |
|-------|--------------------------------------------------|----------|
| `cf_recast` mode | Short `<recast>` + continue | Implicit/input-providing CF (recast) |
| `form_focus` after ≥2 pattern hits | Wrong→right contrast + produce once | Explicit correction + focused output / mini-prompt |
| Budget: hard modes blocked while `turns_since_hard_break < 3` | ≤ ~1 hard form break / 3 turns | Density / affect guardrail |
| Gate: `pedagogy:recast_without_try` = **soft** only | Recast without elicit not repaired | Allows input-only CF |
| Gate: `gate:missing_recast` critical when mode requires recast | Forces reformulation tag | Enforce CF presence, not CF type ladder |
| Teach-move contract: model / try / recast | At least one | Partial alignment with CF taxonomy (misses prompt as first-class) |

**Thesis (mine, not the overview’s):** The product correctly rejects “no correction.” It over-indexes on **recast-as-default**, under-indexes on **prompt-first / push-out for A1**, and treats **missing elicit after CF** as a bookkeeping note rather than a learning-critical failure. The form_focus ladder is the strongest design piece; the soft-fault policy is the weakest.

---

## 2. Verify / refute table — every load-bearing CF claim

| # | Design claim (from overview / round brief) | Verdict | Evidence | Notes / arithmetic |
|---|--------------------------------------------|---------|----------|--------------------|
| **A** | **Always short-recast form errors inline** | **AMEND** (partially supported, over-applied) | Recasts effective but modest (Miller & Pan ES≈0.38; Lyster & Saito *d*≈0.53). Li 2010: explicit often > implicit short-term. Ammar & Spada 2006: **low-proficiency benefit more from prompts**. Lyster & Ranta 1997: ~70% recasts no uptake | “Always” is the problem word. Short, focused, meaning-preserving recasts are good **default soft moves**, especially in **text** (immediate reformulation > delayed in SCMC Spanish studies). Not optimal as **sole** response for A1 morphosyntax |
| **A1** | Implicit: recast preserves flow / CLT | **VERIFY** (process, not outcome) | Classroom preference for recasts (Brown 2016 ~57%); affect literature: recasts less face-threatening than public explicit correction | Flow is a real product value. Must not be confused with acquisition efficacy |
| **A2** | Short recast sufficient for noticing at A1 | **REFUTE** (as general claim) | Low proficiency notices morphosyntactic recasts poorly without salience; uptake low (Lyster & Ranta; Ammar & Spada interaction) | Text + partial recast + highlight may salvage; pure “clean form in a tag” often fails noticing |
| **B** | **form_focus hard break after ≥2 hits of one pattern** (wrong→right, produce once) | **VERIFY** (directionally strong) | Focused CF > unfocused (Kang & Han mediation). Skill-acquisition / prompts support re-production (Lyster & Saito free-production effects). Recurring error_patterns on sheet = developmental readiness proxy | Threshold “≥2” is a **reasonable engineering prior**, not a meta-analytic constant. Pattern-level focus beats random single-error CF |
| **B1** | Wrong→right contrast | **VERIFY** | Cognitive comparison / “window of opportunity” (Doughty 2001, cited in Xu & Zeng 2023); explicit correction effective (Li 2010) | Salience fix for recast failure mode |
| **B2** | Produce once (one try) | **AMEND** | Lyster & Saito: free constructed response measures show larger CF effects when learners **produce**. One forced production is minimal push-out | One try is better than zero; for A1, **two successful productions** or spaced re-try often better for proceduralization (SAT / spacing — not fully implemented) |
| **C** | **Hard breaks budgeted ≤1 per ~3 turns** (`turns_since_hard_break < 3`) | **VERIFY** (as density guardrail) | No meta gives “3 turns”; teacher/learner reports: over-correction harms confidence & participation (Van Ha 2021). Excess CF interrupts communication (Lyster et al. syntheses) | 1 hard / 3 turns ≈ hard-CF rate ≤ **33%** of turns. Soft recasts can still fire every turn → **total CF density may still be high**. Budget only hard modes; does not cap recasts |
| **C1** | comprehension_repair / placement bypass budget | **AMEND** (product-rational, CF-risk) | Comprehension failure is not form CF — bypass is pedagogically OK. But back-to-back hard breaks can still spike affect | Track **combined** hard-break rate in logs, not only form_focus |
| **D** | **recast-without-elicit = soft fault only** (no rewrite) | **REFUTE** for A1 production goals | Soft fault = “we log it and ship.” At low proficiency, recast without try ≈ **input-only CF** with known weak uptake. Prompts > recasts for free production (Lyster & Saito). Teach-move contract allows recast *alone* as legal | If the product claims “transfer / produce,” this soft fault undercuts the claim. At least for `form_focus` and for **repeated error_pattern** hits, recast-without-try should escalate |
| **D1** | Soft faults stay in notes (don’t sanitize to green) | **VERIFY** (measurement hygiene) | Good science practice | Keep — but soft ≠ unimportant |
| **E** | (Implicit) Mode `cf_recast` vs `form_focus` ladder | **VERIFY** | Matches “negotiation of form” ladder: soft reformulation → hard contrast + production | Strongest architecture in the overview |
| **F** | (Implicit) Immediate CF in-chat | **VERIFY** for implicit/text | Xu & Zeng 2023: text-CMC and hybrid/implicit CF favor immediate; timing less critical when explicit | Aligns with always-inline short recast **if** channel is text; for **spoken** TTS replies, oral recasts remain less salient — may need more explicit marking |
| **G** | Gate forces `missing_recast` when mode requires it | **AMEND** | Enforces **presence** of reformulation, not **quality** (salience, partial vs full, target form) or **uptake opportunity** | Can pass gate with a recast the learner never notices |
| **H** | Progress score: + up to 5 for resolved error-pattern streaks | **AMEND** (measurement claim) | Resolving a streak ≠ durable acquisition (need delayed transfer) | OK as engagement signal; do not treat as learning proof |

### Summary scorecard on the four requested items

| Choice | Ruling |
|--------|--------|
| (a) Always short-recast form errors inline | **AMEND** — keep as soft default; do not treat as always optimal; add prompt path for A1 / repeated patterns |
| (b) form_focus after ≥2 pattern hits + contrast + produce once | **VERIFY** — best-supported piece; tighten “produce once” and threshold instrumentation |
| (c) ≤1 hard break / ~3 turns | **VERIFY** as hard-mode budget; **incomplete** as total CF density policy |
| (d) recast-without-elicit soft only | **REFUTE** as policy for learning-critical cases; keep soft for pure conversational soft CF only if intentional |

---

## 3. What the other author (system overview) MISSED

1. **Proficiency interaction is load-bearing.** Overview optimizes for A1 but implements a recast-default that literature says is **worst for A1**. No mention of Ammar & Spada–style proficiency moderation.  
2. **Prompt / elicitation is not a first-class mode.** Taxonomy in product: model / try / recast. “Try” is open elicit for content; **form-focused prompt** (metalinguistic clue, repetition of error, “¿Cómo se dice…?” with target slot) is missing as a distinct CF move.  
3. **Uptake is unmeasured.** Sheet tracks `error_patterns` hits; no turn-level **uptake/repair** flag after CF (Lyster & Ranta’s core dependent measure). Without it, you cannot know if recasts work *in this system*.  
4. **Oral vs written CF are conflated.** Product has text chat + STT + TTS. Literature: **text recasts more salient** than oral. Overview does not branch CF strategy by channel.  
5. **“Always recast” can raise total density while hard budget looks fine.** Soft recasts every form error + one hard break / 3 turns can still feel like constant correction. No soft-CF budget / sampling policy.  
6. **No delayed CF arm.** Xu & Zeng 2023: timing not settled; delayed spaced CF can help explicit knowledge / reconsolidation. Product is 100% immediate. Optional end-of-scene “one pattern, one contrast” is unexplored.  
7. **Affect is session labels only** (`energy`, `boredom_risk`) — no link from **CF rate** → affect. Literature’s main risk of dense CF is affect, not just pedagogy contract.  
8. **Metalinguistic depth is unstructured.** `<explain depth="brief">` exists, but no rule when brief metalinguistic > recast (e.g. *estar* vs *ser* heat: “està calor → hace calor” is lexical-constructional — often needs **explicit label**, which commit `f7649e1` already partially fixed).  
9. **Transfer mode is mentioned; CF→transfer chain not instrumented.** After form_focus success, transfer should be the delayed test of CF. Not in gate metrics.  
10. **Written CF research (Kang & Han 2015) largely unused** despite typed chat being a writing-adjacent channel (focused direct correction in text is highly actionable).

---

## 4. Standing questions (answered)

| Question | Answer |
|----------|--------|
| Recasts vs prompts for adult beginners? | **Prompts ≥ recasts for production**, especially low proficiency (Ammar & Spada 2006; Lyster & Saito 2010). Recasts OK as low-cost soft CF. |
| Immediate vs delayed? | **No universal winner** (Xu & Zeng 2023). Immediate better for **implicit / text reformulation**; delayed viable for **explicit** end-of-task. Product’s always-immediate is defensible for chat, incomplete as policy. |
| Text vs spoken? | **Text favors noticing of recasts**; oral recasts more ambiguous. Branch by modality. |
| Noticing/uptake of recasts at low proficiency? | **Low** in classic oral classroom (~70% no uptake Lyster & Ranta 1997); worse for morphosyntax. Do not assume short recast = noticed. |
| Tolerable density before affect damage? | **No meta-analytic N.** Teacher/learner reports: correcting one learner too often harms confidence. Hard budget ~1/3 turns is reasonable; **must also cap or sample soft recasts** and monitor affect. |
| Is recast-without-elicit OK as soft only? | **No** for repeated A1 form patterns if goal is production. Yes only for one-off soft maintenance of flow. |

---

## 5. Ranked improvement proposals (adjudicable)

Ranked by **expected learning impact / implementation cost**. Each must be falsifiable in logs or evals.

### P1 — Prompt-before-hard-break for A1 pattern hits (highest impact / medium cost)

**Change:** On **first** detected hit of a tracked `error_pattern` at A1, prefer **form prompt** (partial elicit / metalinguistic clue / “try again with X”) over pure recast; keep short recast only if prompt fails or affect is fragile. On **≥2 hits**, keep `form_focus` (contrast + produce).  

**Why:** Ammar & Spada 2006; Lyster & Saito 2010 (prompts > recasts, free production).  

**Adjudication:**  
- A/B trajectories (same scripts): **prompt-first** vs **recast-always**.  
- Metric: same-pattern re-error rate over next 5 learner turns; delayed transfer success on `transfer` mode.  
- Target: ≥ **15% relative reduction** in re-error within 5 turns (if baseline re-error = 0.40, target ≤ 0.40 × 0.85 = **0.34**).

### P2 — Escalate `recast_without_try` when pattern is hot (high impact / low cost)

**Change:** Keep soft for isolated recasts. If `error_pattern.hits ≥ 2` OR mode is `form_focus` OR `cf_recast` after a prior hit this session → treat missing try/elicit as **critical** (gate rewrite), not soft.  

**Why:** Directly attacks the soft-fault hole; aligns gate with skill-acquisition need for production.  

**Adjudication:**  
- Gate notes rate: critical `recast_without_try` on hot patterns → 0 after repair.  
- Uptake: share of CF turns with learner re-attempt of target form within next turn ≥ **0.50** (vs baseline; measure before/after).

### P3 — Instrument uptake + CF density (medium–high impact / low cost; enables all science)

**Change:** Per turn log: `cf_type` ∈ {none, recast, prompt, explicit_contrast, metalinguistic}, `cf_target`, `learner_uptake` ∈ {none, acknowledge, repair, needs_repair}, `soft_cf_count_last_3_turns`. Cap or sample soft recasts if soft CF on **>2 of last 3 turns** (example prior: max soft recast density **2/3**).  

**Why:** Without uptake, “always recast” is unfalsifiable. Density literature is qualitative; product must measure.  

**Adjudication:**  
- Dashboard: mean soft-CF rate, uptake rate by type.  
- Affect: if `boredom_risk` or energy drop correlates with soft-CF rate > **0.67** (2/3), tighten cap.  
- Learning: repair after prompt vs recast (chi-square on logged cells).

### P4 — Channel-aware salience (medium impact / medium cost)

**Change:**  
- **Text:** short partial recast + optional visual contrast (wrong→right in recast tag already).  
- **Speech/TTS:** add brief explicit marker (“Se dice…”) or slow partial recast; pure full-utterance oral recast last.  

**Why:** Text SCMC immediate reformulation advantage (Arroyo & Yilmaz 2017/2018); oral recast ambiguity (Lyster & Ranta line).  

**Adjudication:**  
- Split evals by mic vs type.  
- Noticing proxy: uptake rate oral vs text; expect text recast uptake − oral recast uptake ≥ **0.15** absolute if current oral is undersalient.

### P5 — Spaced second production after form_focus (medium impact / medium cost)

**Change:** After successful `form_focus` produce-once, schedule **transfer** within **3–6 turns** (or next scene beat) requiring same form in new context; if fail, one more mini-prompt (not full hard break if budget exhausted).  

**Why:** Spacing / reconsolidation (Butler et al. via Xu & Zeng 2023); Lyster & Saito free-production measures; product already has `transfer` mode — wire it to CF success.  

**Adjudication:**  
- Transfer success rate within 6 turns after form_focus ≥ **0.60**.  
- Re-error of same pattern at session+1 (sheet) lower than no-transfer control.

---

## 6. Critique ranking of *current* design (mine)

| Rank | Component | Grade | One-line critique |
|------|-----------|-------|-------------------|
| 1 | form_focus ladder (≥2 hits → contrast → produce) | **A−** | Best SLA-aligned piece; “once” is thin |
| 2 | Hard-break budget (~1/3 turns) | **B+** | Good affect proxy; doesn’t govern soft CF |
| 3 | Structured recast tag + missing_recast critical | **B** | Enforces presence, not noticing or repair |
| 4 | Always short-recast default | **C+** | Teacher-like, CLT-friendly, **suboptimal for A1 accuracy** |
| 5 | recast_without_try soft only | **D+** | Actively under-enforces the production half of “focus on form” |

**Overall CF architecture grade: B−** — correct that conversation needs CF; wrong default weight on recasts for the stated learner; soft-fault policy weakens the best ladder (form_focus).

---

## 7. Bottom line (append-ready adjudication)

- **Do not rubber-stamp “always short-recast.”** Meta-analytic and proficiency-moderated evidence from **2010–2026** favors **prompts/elicitation and focused explicit contrast** for adult beginners’ **production**, with recasts as a **low-cost, high-flow soft move**, stronger in **text** than pure oral.  
- **Keep and instrument form_focus ≥2 + budget.** Those are the designs most consistent with focused CF and affect constraints.  
- **Reject soft-only treatment of recast-without-elicit for hot patterns.** That is the highest-leverage policy bug relative to cited SLA.  
- **Next research round should not write more stance prose** until P3 (uptake + density logs) lands — otherwise every CF debate stays vibes.

**Citations used (primary):** Li (2010); Lyster & Saito (2010); Ammar & Spada (2006); Lyster & Ranta (1997); Brown (2016); Kang & Han (2015); Miller & Pan (2012); Arroyo & Yilmaz (2017/2018); Shintani & Aubrey (2016); Xu & Zeng (2023); Van Ha et al. (2021).

— Grok (independent collab), **2026-07-26**
