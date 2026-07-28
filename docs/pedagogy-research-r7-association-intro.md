# Pedagogy research round 7 — introducing new language: association, glossing, and context inference

## Brief (Claude, 2026-07-28)

**User critique (verbatim, 2026-07-28):** "when the ai uses new phrases in spanish it should also tell me what they mean in english. What are we expecting the user to do with phrases and words they have never seen before? The best option is to learn by association. Here is a word you don't know but here is something that you do know that you can associate it with. Or to figure it out by context, but this needs to be part of the teaching and it currently is not."

**Concrete failure case (live transcript, 2026-07-28):** tutor reply — "Me llamo Marisol. Hoy vamos a practicar cómo cerrar una conversación en español. Para despedirnos (to say goodbye), podemos decir **hasta luego** o **adiós**. … ¿Cuál prefieres usar tú para despedirte: **hasta luego** o **adiós**?" — `despedirnos` got an English gloss; `hasta luego`/`adiós` got neither gloss, nor association anchor, nor meaning-revealing context. The learner is A1 and had never seen them.

**Current policy (so you know what to critique):** the tutor system prompt says "Comprehensible input — mostly clear Spanish; English is a lifeline only. Prefer context/image over dual-subtitle English walls (*X = Y* on every line)" and forbids "English dual-subtitle walls on every phrase." So we banned per-line glossing as a crutch but built NO machinery that makes new items comprehensible instead: no first-exposure tracking (the sheet's lexicon tracks evidence of USE, not what has been INTRODUCED), no association-anchor generation, no cognate exploitation, no context-engineering requirement on the model. The model is left to improvise, and it improvises inconsistently.

**Research question:** For adult A1 learners, what does the evidence say about how a NEW word/phrase should enter the learner's world? Specifically:
1. Glossing research (Nation, Laufer, and successors): when do L1 glosses help vs hurt? First exposure vs later retrievals? Inline vs on-demand?
2. Association techniques: keyword method, cognate mapping (rich ES↔EN cognate space), semantic/thematic clustering (and the evidence AGAINST clustering near-synonyms/antonyms at first exposure), dual coding with images, personalization effects.
3. Inferencing from context: what makes context actually meaning-revealing at A1 (coverage thresholds — the ~95–98% known-word findings), when inference fails, and how to ENGINEER an utterance so a target item is inferable rather than hoping.
4. First-exposure protocol: evidence-based sequence for introduce → anchor → immediate use → retrieval, and how many new items per session A1 can absorb.

**Required deliverable shape (build brief, not essay):**
- Ruling on the user's instinct: gloss-always vs associate vs context-infer — what the evidence actually supports, per exposure stage.
- A concrete NEW-ITEM INTRODUCTION PROTOCOL: decision rules a program can execute (e.g., "item unseen + cognate → cognate anchor, no gloss; unseen + concrete → image + engineered context; unseen + abstract/function phrase → inline gloss on first exposure only, retrieval next turn…"). Every rule must state its evidence.
- 2–4 SINGLE-PURPOSE SUBSYSTEM proposals with inputs/outputs, code-owned vs model-performed split, integration points (character sheet lexicon needs an "introduced/first-seen" ledger distinct from use-evidence; the mode runtime and output gate can enforce the protocol), and a testable success criterion each. Rank by impact-per-effort.
- Whether the existing "no dual-subtitle walls" rule survives, gets amended, or dies — with reasons.

Integrate with r3 (retrieval/spacing) and r5 (multimodal); do not re-litigate what they settled — build on it.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 14:43 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the research brief, then produce an independent round-7 deliverable with evidence-backed rulings and subsystem proposals.Continuing through the full prompt for r3/r5 findings and related evidence, then verifying key claims with web search.Pulling primary sources on glossing, cognates, semantic clustering, and lexical coverage so the protocol rests on verified evidence.# GROK — independent research round 7: ASSOCIATION, GLOSSING, AND NEW-ITEM INTRODUCTION  
**Date of adjudication:** 2026-07-28  
**Role:** contrarian second author (not a rubber-stamp of the Claude brief or product rhetoric)  
**Subject:** user critique + failure transcript (2026-07-28) + brief `docs/pedagogy-research-r7-association-intro.md` + product map in `docs/system-overview.md` (status as of 2026-07-27)  
**Integration:** build on r3 (retrieval/spacing, 2026-07-26) and r5 (multimodal dual coding, 2026-07-26); do not re-litigate their settled pins  
**Scope:** adult A1 Spanish; first exposure of lemmas/phrases; code-enforceable protocol (user authorized real subsystems)

---

## 1. Independent picture (dated pins)

| Pin | Claim I will defend | Anchor |
|-----|---------------------|--------|
| **P1 (2020)** | Glossing works: glossed reading yields **45.3%** immediate and **33.4%** delayed form–meaning gain vs **26.6% / 19.8%** nonglossed. Absolute gloss advantage = **45.3 − 26.6 = 18.7 pp** immediate; **33.4 − 19.8 = 13.6 pp** delayed. L1 glosses beat L2 glosses; no reliable L1×proficiency interaction that rescues “L2-only for beginners.” | Yanagisawa, Webb & Uchihara, *SSLA* 2020 (meta-regression; 359 ES, 42 studies, *N* = 3802) |
| **P2 (1997–2016 lineage)** | For low-proficiency learners, L1 glosses often match or beat L2 on delayed retention; L1 is not a moral failure. | Laufer & Shmueli 1997; Yoshii 2006; Choi et al. 2016; Hu et al. 2014 (lower-level → L1 advantage) |
| **P3 (2000 / 2011)** | Unassisted comprehension and successful **context inference** need ~**95%** (minimal) to ~**98%** (reliable) known-word coverage. Below that, “figure it out from context” is hope, not pedagogy. | Hu & Nation 2000; Schmitt et al. 2011; Laufer coverage framing |
| **P4 (arithmetic, A1 turns)** | A typical 20-token tutor model with **2** unknown targets has coverage **18/20 = 90%** — under the 95% floor. With **3** unknowns: **17/20 = 85%**. Inference is structurally disabled unless the utterance is **engineered** (one target, high known density). | Hu & Nation thresholds applied to product turn length |
| **P5 (1993–2008)** | **Semantic clustering** of near-synonyms/antonyms/coordinates at first exposure increases interference (cross-association). The failure case *hasta luego* OR *adiós* is textbook clustering of farewell near-synonyms. Prefer **thematic** frames or **one** target per introduce move. | Tinkham 1993/1997; Waring 1997; Erten & Tekin 2008; Nation 2000 advice |
| **P6 (1975)** | Keyword / acoustic-image association is powerful for form→meaning when an anchor exists: Spanish keyword classic **88%** vs free-study **28%** → absolute **+60 pp** (88 − 28). | Raugh & Atkinson 1975 |
| **P7 (cognate space)** | ES↔EN cognates are a large free resource (~**30–40%** of English lexicon has a Spanish relative); exploit true cognates, flag false friends. Cognate mapping is association **without** English dual-subtitle walls. | Colorín Colorado / bilingual cognate pedagogy (standard estimate); RHM early L2→L1 mediation (Kroll & Stewart 1994) |
| **P8 (r5, 2026-07-26)** | Concrete imageable nouns → dual code (image + Spanish form + contiguity); abstract/function phrases → L1 micro-lifeline is often better than fake pictures. Ordered scaffold: image → fail → short L1. | Settled r5 R2; Yoshii / Choi / Yanagisawa |
| **P9 (r3, 2026-07-26)** | First exposure without later retrieval wastes the gloss/associate investment. After introduce + try: **enqueue** for spaced re-encounter **without re-glossing**. | Kim & Webb 2022 spacing; Karpicke & Roediger 2008 retrieval after success |
| **P10 (product fact, 2026-07-28)** | Sheet `lexicon` tracks **use evidence**, not **introduction**. Policy bans dual-subtitle walls but provides **no** first-seen ledger, **no** anchor router, **no** coverage engineering, **no** gate for “naked new item.” Model improvises; failure case is structural, not a one-off bad turn. | Brief + system-overview §5 lexicon / §4.1 association rhetoric |

**Synthesis picture:** The user’s instinct (“tell me what new Spanish means”) is **directionally right for first exposure of non-inferable items** and **wrong as a permanent dual-subtitle habit**. Association and engineered context are preferred **when the conditions for them exist**; they are not free substitutes for meaning. Product currently has the anti-wall half of CI and is missing the **comprehensibility machinery** half — that is the load-bearing bug of this round.

---

## 2. Verify / refute table (load-bearing claims in inlined files)

| # | Claim | Verdict | Evidence & arithmetic |
|---|--------|---------|------------------------|
| C1 | User: “when the AI uses new phrases it should also tell me what they mean in English” (always) | **PARTIAL — AMEND** | Always-gloss = dual-subtitle habit → form neglect / CI collapse. First-exposure L1 micro-gloss for non-cognate, non-imageable, non-engineered items is **supported** (Yanagisawa: +18.7 pp immediate). Later turns: re-gloss is anti-retrieval. |
| C2 | User: best option is learn by association | **SUPPORT when anchor exists; OVERCLAIM as universal** | Keyword +60 pp class effects; dual coding for concrete nouns (r5). Abstract function phrases (*para despedirnos*) have weak image anchors — association alone is insufficient. |
| C3 | User: or figure it out by context, and that needs to be taught | **SUPPORT intent; REFUTE as current practice** | Context inference needs ~95–98% coverage + meaning-revealing cues. Product does not measure coverage or engineer utterances. A1 free chat routinely sits at 85–90% when multiple new items land. |
| C4 | Failure case: `despedirnos` glossed; `hasta luego` / `adiós` neither glossed nor anchored | **VERIFY as pedagogy failure** | Two farewell near-synonyms introduced together = semantic clustering interference (Tinkham/Waring). Forced choice without meaning = discrimination without form–meaning map. |
| C5 | Policy: “English is a lifeline only; prefer context/image over dual-subtitle walls” | **SUPPORT as anti-wall UI; REFUTE as complete first-exposure policy** | Anti-wall is correct. Absence of lifeline machinery makes “lifeline” rhetorical. r5 already AMEND’d pure no-English for image fails. |
| C6 | “We banned per-line glossing but built NO machinery that makes new items comprehensible” | **VERIFY** | No first-seen ledger; association mode exists but is not a general introduce protocol; gate has `english_wall` not `naked_new_item`. |
| C7 | Lexicon tracks USE not INTRODUCED | **VERIFY (architecture claim)** | Overview §5: lexicon = concrete words with confidence (use-side). Session memory tracks images shown, not full introduce ledger. |
| C8 | Association mode = form ↔ image (English wall or new concrete noun) | **PARTIAL** | Scope is too narrow for all first exposures (function phrases, multiword units). Correct for imageable nouns; incomplete protocol. |
| C9 | Comprehension repair: same idea, re-model, no topic jump | **SUPPORT as repair; NOT a substitute for first-exposure protocol** | Repair is reactive after failure; introduction should prevent many failures. |
| C10 | ~95–98% known-word findings justify “context over gloss” at A1 | **REFUTE if used to ban first-exposure gloss** | Those thresholds describe when inference **can** work — they justify **engineering** context or **not relying** on it when coverage is low, not banning L1. |
| C11 | Incidental encounter alone teaches new items | **REFUTE for A1 intentional teaching** | Webb et al. 2023 incidental gains are modest; gloss meta shows large relative gain from explicit meaning support during input. |
| C12 | “No dual-subtitle walls on every phrase” should stay absolute | **AMEND** | Survive as ban on walls; die as ban on single first-exposure micro-gloss / cognate anchor. |

---

## 3. What the other author / product picture MISSED

1. **Introduction ≠ repair ≠ review.** Product has repair and (weak) association; r3 called out missing review. This round’s missing third leg is **introduce**. Three different objectives: map meaning (E0), fix misunderstanding (repair), retrieve later (r3 due queue).

2. **Failure case is clustering, not only missing gloss.** Teaching *hasta luego* **and** *adiós* as simultaneous alternatives without sequential mastery is interference design. One target per introduce move is as important as gloss/associate choice.

3. **“Context inference” without coverage math is cargo-cult CI.** At 20 tokens / 2 new items → **90%** coverage → under Hu & Nation floor. Code must count unknown tokens against introduce budget, not hope the model “uses context.”

4. **Multiword units (MWUs) are first-class.** *hasta luego*, *me llamo*, *hace calor* are not bag-of-lemmas. Ledger and protocol must key on **normalized MWU or lemma**, not only single words.

5. **False friends need a deny list.** Cognate association without false-friend handling (*embarazada*, *éxito*, *actual*, *librería*) will encode wrong meaning confidently.

6. **Receptive introduce ≠ productive known.** Marking “introduced” must not bump `known` / solid_uses. r3 honesty gates stay: known still needs productive evidence + spacing.

7. **Gate asymmetry:** `gate:english_wall` exists; there is no `gate:unscaffolded_new_item` (new item in model/try with no gloss, cognate anchor, image caption, or engineered context flag). Policy without machine check = improvisation.

8. **Personalization anchors (profile hooks) unused for association.** Learner name, boat, café, interests are free dual-coding hooks for thematic association — not only stock images.

9. **Keyword method is under-used and over-risked.** Powerful (P6) but model-generated keywords can be silly/opaque; prefer **pack-curated** keyword/cognate tables for A1 palette; model only as fallback with length/quality lint.

10. **Progress score still ignores introduction quality.** You can “introduce” 10 items badly and score still rises only on production bumps — no metric for scaffolded first exposures.

---

## 4. Ruling: gloss-always vs associate vs context-infer (per exposure stage)

| Stage | Goal | Supported default | Explicitly avoid |
|-------|------|-------------------|------------------|
| **E0 — First exposure** (item never in introduce ledger) | Form ↔ meaning map is built | **Route by item class** (protocol below): cognate anchor / image dual-code / engineered context / **one** L1 micro-gloss. Prefer association when diagnostic; L1 when not. | Gloss walls; synonym pairs; bare bold Spanish; hoping for inference under &lt;95% coverage |
| **E1 — Immediate use** (same session, after E0) | Productive or forced-choice try on **same** item | Spanish elicit; **no** re-gloss if E0 succeeded; short recast on form error | Re-teaching meaning; introducing a near-synonym competitor |
| **E2 — Retrieval** (later turn / next due, r3) | Strengthen storage via retrieval | Cue in Spanish/context; **no** L1 gloss unless retrieval fails → then one lifeline (align r5 R2) | Full re-introduce; dual subtitles; massed synonym contrast |
| **Repair** (comprehension fail on already-introduced) | Restore meaning of **same** item | Image if concrete → else L1 ≤6 words → re-elicit (r5 R2) | Topic jump; second new item |

### Headline ruling on the user’s instinct

| Instinct | Ruling |
|----------|--------|
| Gloss-always | **REJECT as standing policy.** Survives only as **E0 tool for non-associable items** and **post-fail lifeline**. |
| Associate | **PREFERRED when a diagnostic anchor exists** (true cognate, imageable noun, known L2 paraphrase with conf≥0.80, personal hook). |
| Context-infer | **ALLOWED only when engineered:** ≤1 new target, estimated coverage ≥95%, and a meaning-revealing frame (definitional apposition, gesture/image, contrast with known opposite that is **already solid**). Otherwise treat as E0 failure mode. |

**Arithmetic justification for not gloss-always:** Yanagisawa shows gloss helps **vs no support**, not that continuous L1 is optimal for acquisition trajectory. Testing effect (r3) requires meaning to be retrieved later **without** the L1 crutch. Permanent dual subtitles maximize immediate comfort and minimize durable L2 form–meaning autonomy.

**Arithmetic justification for not context-always:** 2 unknowns / 20 tokens = **90%** &lt; 95% floor → inference disabled by construction for the failure-case style of turns.

---

## 5. NEW-ITEM INTRODUCTION PROTOCOL (executable decision rules)

**Preconditions (code):**  
- Normalize target → lemma or MWU key (`hasta luego`, not only `luego`).  
- `introduced[key]` ledger distinct from `lexicon[key].confidence` / solid_uses.  
- Session budget: **max 2 new introductions per session** at A1 (conservative absorb rate; prefer 1 hard MWU or 2 easy cognates). Third attempt → defer to next session or recast as review of prior introduce.  
- **One primary target per introduce move** (no synonym pairs at E0).

### Decision tree (first matching rule wins)

| Rule ID | Condition | Action (E0) | Evidence |
|---------|-----------|-------------|----------|
| **R-A Cognate** | Unseen ∧ true_cognate(key) ∧ not false_friend | Spanish form + **cognate anchor** (“like English *…*”) ≤6 EN words; **no** full gloss wall; optional stress/false-friend note if near-miss | Cognate facilitation; RHM early L1 mediation; avoids wall while giving association |
| **R-B Concrete image** | Unseen ∧ imageable_noun (pack flag or heuristic) | Pre-AI image + Spanish form **on/under image** (r5 contiguity) + short Spanish model; TTS of form after image visible; **no** L1 unless later fail | Paivio dual coding; Mayer contiguity; r5 R3/R4 |
| **R-C Engineered context** | Unseen ∧ can build frame with coverage ≥95% ∧ single target | One unknown token in model; rest high-frequency/known; meaning-revealing pattern (apposition, situation script, known opposite already solid). Optional yes/no comprehension check before free try | Hu & Nation 95–98%; avoids false “CI” under 90% coverage |
| **R-D Function / abstract / MWU** | Unseen ∧ (discourse marker ∨ abstract ∨ function phrase ∨ failed R-B/C) | **One** inline L1 micro-gloss ≤6 EN words on **first** exposure only (e.g. *hasta luego* (see you later)); then Spanish re-model; immediate try | Yanagisawa L1 advantage; Choi delayed L1; r5 lifeline discipline |
| **R-E Keyword fallback** | Unseen ∧ pack has curated keyword for key | Keyword image link (acoustic) + Spanish form; pack-owned, not free model improv | Raugh & Atkinson 1975 (+60 pp class result) |
| **R-F Cluster ban** | Candidate introduce set contains near-synonyms/antonyms | Introduce **one**; park the other until first is E1-success or next_due retrieval | Tinkham/Waring interference |
| **R-G Budget** | Session already introduced ≥2 keys | Do not introduce; use known palette; if discourse needs the item, R-D gloss only if unavoidable and mark deferred | A1 absorb limits; incidental meta modest gains |
| **R-H Post-E0** | After successful comprehension token or correct try | Write `introduced_at`, `scaffold_type`, `next_due` (r3 ladder: 1d → 3d → ×2 cap 14); **do not** set known | r3 spacing; Karpicke retrieval after success |
| **R-I Re-exposure** | `introduced` ∧ not due ∧ appears in chat | No re-gloss; light natural use OK | Avoid massed re-teaching |
| **R-J Retrieval fail** | Due reencounter fail or meta_comprehension on introduced item | r5 ladder: image if concrete else L1 ≤6 words once → re-elicit | r5 R2; Choi/Yoshii |

### Worked failure case (2026-07-28 transcript)

Bad: gloss *despedirnos*; introduce **both** *hasta luego* and *adiós* bare.  

Protocol rewrite:  
1. Pick **one** target: *adiós* (higher frequency / shorter) OR *hasta luego* (MWU) — not both (R-F).  
2. *adiós* is weakly imageable but highly conventional → **R-D**: “**Adiós** (goodbye).” Model: “Adiós, Ana.” Try: “¿Cómo se dice goodbye? / Di adiós.”  
3. Defer *hasta luego* until E1 success on *adiós* or next session (R-F, R-G).  
4. *despedirnos* as metalanguage: either avoid at A1 or R-D once; do not gloss the metalanguage while leaving the **targets** bare (priority inversion in the live turn).

---

## 6. “No dual-subtitle walls” — survives, amended, or dies?

| Piece | Ruling |
|-------|--------|
| Ban on English dual-subtitle wallpaper (X = Y on every line / mostly-English turns) | **SURVIVES.** Coherence + CI + gate `english_wall` remain. |
| Ban on any English at first exposure | **DIES.** Evidence does not support; user pain is real; Yanagisawa/Choi/Laufer line favors selective L1. |
| Operational amendment (exact policy text) | **AMEND to:** “English is a **lifeline and a first-exposure micro-scaffold**, not wallpaper. Allowed: (1) ≤1 L1 micro-gloss ≤6 words per **new** item on E0 when R-A–C do not apply; (2) cognate/keyword anchors; (3) post-fail lifeline per r5. Forbidden: dual-subtitle every phrase; multi-sentence English explain on hard breaks when image present (r5 R5); re-gloss of introduced items on E1/E2 without fail.” |

**Why not full death of the rule:** unrestricted gloss-always recreates the product non-goal (English dual-subtitle app) and undercuts retrieval (r3) and Spanish-forward persona.

---

## 7. SINGLE-PURPOSE SUBSYSTEM proposals (real code; ranked impact ÷ effort)

User authorized build — not prompt-only. Each subsystem is single-purpose; model realizes Spanish only after code decides scaffold.

### S1 — **Introduced-item ledger** (sheet + session)  
**Rank: #1 impact/effort**

| | |
|--|--|
| **Purpose** | Track first-seen ≠ use-evidence |
| **Inputs** | Normalized key (lemma/MWU), turn_id, scaffold_type, session_id, timestamp |
| **Outputs** | `sheet.lexicon[key].introduced_at` / `scaffold` / `introduce_count`; session `new_items_this_session`; query API `is_introduced(key)`, `session_intro_budget_remaining()` |
| **Code-owned** | Schema, migrate, write on successful E0, budget counters, never auto-bump known |
| **Model-performed** | None (ledger is pure code) |
| **Integration** | `character_sheet.py` + `session_memory.py`; seed on open; hard observer may suggest candidates but **code** commits introduce events from mode/gate metadata |
| **Success criterion** | Unit: introduce write does not change conf/solid_uses; after reset_sheet ledger clears; budget: 3rd introduce in one session rejected. Behavioral: logs show `introduced_at` for items that appeared in association/R-D turns. |

### S2 — **Introduce router + mode `introduce` (or association expand)**  
**Rank: #2**

| | |
|--|--|
| **Purpose** | Execute R-A…R-F; emit a structured **IntroducePlan** before AI realize |
| **Inputs** | Candidate keys from pack/next_best/model intent; ledger; cognate table; imageable flags; profile hooks; session budget |
| **Outputs** | `IntroducePlan{key, rule_id, scaffold_payload, forbid_cluster_with[]}` fed to executor task; may force mode `association` or new soft mode `introduce` |
| **Code-owned** | Decision tree, budget, cluster ban, plan object, pack lookups |
| **Model-performed** | Realize Spanish turn **following** plan (form placement, one try); optional cognate phrasing within plan limits |
| **Integration** | `modes.py` / planned pipeline step before tutor_turn; `executor.py` task builder; teach_assets for R-B |
| **Success criterion** | Offline fixture: failure-case input → plan picks one farewell + R-D or R-B, never both bare. Live: ≥90% of first appearances of pack A1 targets carry a non-null `rule_id` in logs over 50 sessions. |

### S3 — **Output gate: `gate:unscaffolded_new_item`**  
**Rank: #3**

| | |
|--|--|
| **Purpose** | Enforce protocol; stop improvisation |
| **Inputs** | Parsed tutor parts; IntroducePlan (or empty); ledger; bolded/candidate Spanish spans from pack matcher |
| **Outputs** | Critical fault if model presents unintroduced pack item in `<model>`/`<try>` without allowed scaffold signal (gloss span, cognate marker, image caption key, or plan flag); one repair instruction |
| **Code-owned** | Detection + repair directive; English micro-gloss length check (≤6 words, ≤1 per new item) |
| **Model-performed** | Repair rewrite only |
| **Integration** | `output_gate.py` critical table; align with `gate:english_wall` so repair cannot flip to full English wall |
| **Success criterion** | Unit tests: bare *hasta luego* first seen → fault; R-D glossed once → pass; second turn re-gloss without fail → soft fault `gate:regloss`. Regression: english_wall still trips on mostly-English turns. |

### S4 — **Pack association table (cognates, false friends, imageable, curated keywords)**  
**Rank: #4 (enables S2 quality; slightly lower solo impact)**

| | |
|--|--|
| **Purpose** | Deterministic anchors for Spanish A1 palette |
| **Inputs** | Static YAML/JSON under `course_packs/spanish_a1/association_table.json` |
| **Outputs** | Lookups: cognate_en, false_friend_note, imageable bool, keyword_en, thematic_group_id (for cluster ban) |
| **Code-owned** | File schema, loader, tests for false-friend list |
| **Model-performed** | Optional fill-in only for OOV with lint; not trusted for false friends |
| **Integration** | corpus/pack load; S2 router; teach_assets keys |
| **Success criterion** | 100% of unit01–02 high-frequency farewell/greeting MWUs covered; false-friend list includes ≥15 common ES traps; router never applies R-A to listed false friends. |

**Explicit non-subsystems (do not build now):** full SM-2 flashcards UI; model-only “please associate better” prompt tweak; automatic translate-every-span.

**Build order:** S1 → S4 (minimal table for greetings/farewells/boat nouns) → S2 → S3. S3 without S1/S2 is premature; S2 without S1 cannot be honest.

---

## 8. Integration with r3 and r5 (no re-litigation)

| Settled pin | How r7 uses it |
|-------------|----------------|
| r3 due queue 1→3→×2 cap 14 | R-H writes `next_due` on introduce success; E2 retrieval **without** re-gloss |
| r3 known honesty (caps, solid uses) | Introduce never grants known |
| r5 selective images | R-B only for imageable; no wallpaper |
| r5 L1 after image fail | R-J / repair ladder; E0 may use L1 **first** when non-imageable (R-D) — extension of r5, not contradiction: r5 ordered image→L1 for repair of concrete; r7 allows L1-first for function MWUs where image is non-diagnostic |
| r5 contiguity / no triple stack | Image caption = Spanish form; if image + R-D, suppress long explain |

**Amendment to r5 R2 wording (precise):** L1 lifeline is not only “after image fail.” For **non-imageable first exposures**, L1 micro-gloss is a **valid primary** scaffold (R-D), still ≤6 words, still once, still followed by Spanish try.

---

## 9. Ranking / critique (impact per effort)

| Rank | Item | Impact | Effort | Notes |
|------|------|--------|--------|-------|
| 1 | S1 ledger | High | Low | Unblocks everything; pure honesty |
| 2 | S4 minimal association table (greet/farewell/concrete) | High | Low–med | Makes router non-hallucinated |
| 3 | S2 introduce router + plan | High | Med | Fixes user critique + failure case |
| 4 | S3 unscaffolded_new_item gate | Med–high | Med | Enforcement; without it S2 is advisory |
| 5 | Policy text amend (anti-wall) | Med | Trivial | Docs + `conversational_tutor.md` — **after** S1–S3 or models ignore |
| — | Prompt-only “associate more” | Low | Low | Explicitly insufficient; user authorized code |

**Overall grade of current product on this dimension:** **D+** — correct anti-wall instinct, missing introduce machinery, live failure case is predicted by theory (clustering + sub-threshold coverage + no ledger).

---

## 10. Sources (absolute bibliographic pins)

- Yanagisawa, A., Webb, S., & Uchihara, T. (2020). How do different forms of glossing contribute to L2 vocabulary learning from reading? A meta-regression analysis. *Studies in Second Language Acquisition*. (45.3% / 33.4% vs 26.6% / 19.8%; L1 &gt; L2 glosses.)  
- Choi, S. (2016). Effects of L1 and L2 glosses on incidental vocabulary acquisition and lexical representations. *Learning and Individual Differences*.  
- Yoshii, M. (2006). L1 and L2 glosses: Their effects on incidental vocabulary learning. *Language Learning & Technology*.  
- Laufer, B., & Shmueli, K. (1997). Gloss type and L1/L2 vocabulary retention.  
- Hu, M., & Nation, P. (2000). Unknown vocabulary density and reading comprehension. *Reading in a Foreign Language*. (~95–98% coverage framing.)  
- Schmitt, N., Jiang, X., & Grabe, W. (2011). The percentage of words known in a text and reading comprehension.  
- Tinkham, T. (1993, 1997); Waring, R. (1997); Erten, İ. H., & Tekin, M. (2008). Semantic clustering interference; thematic preferred.  
- Raugh, M. R., & Atkinson, R. C. (1975). Keyword method; Spanish vocabulary ~88% vs ~28% free study.  
- Webb, S., Uchihara, T., & Yanagisawa, A. (2023). Incidental vocabulary learning meta-analysis (modest gains → intentional scaffold matters).  
- Kim, S. K., & Webb, S. (2022). Spacing meta (r3).  
- Karpicke & Roediger (2008); Roediger & Karpicke (2006). Retrieval after success (r3).  
- Mayer CTML contiguity/coherence; Paivio dual coding (r5).  
- Kroll & Stewart (1994). Revised Hierarchical Model — early L2–L1 links.  
- Product pins (2026-07-27/28): system-overview modes/gate/lexicon; r3/r5 Grok rounds 2026-07-26; live failure transcript 2026-07-28.

---

## 11. Bottom line (append-ready)

1. **User is right that naked new Spanish is malpractice at A1; wrong that the fix is permanent English subtitles.**  
2. **Evidence order at E0:** cognate associate → image dual-code → engineered ≥95% context → one L1 micro-gloss; never synonym pairs; max ~2 new items/session.  
3. **E1/E2 strip the scaffold** and feed r3 retrieval — that is how gloss helps without becoming a crutch.  
4. **“No dual-subtitle walls” AMENDS** (walls stay banned; selective E0 L1 and anchors become mandatory machinery).  
5. **Build S1→S4→S2→S3** as real code subsystems; prompt tweaks alone will reproduce the 2026-07-28 failure.

---

*End of Grok independent round 7 — ASSOCIATION / GLOSSING / NEW-ITEM INTRODUCTION — 2026-07-28.*

---

## Adjudication — r7 (Claude, 2026-07-28)

**ACCEPTED in full, two notes:**

1. The per-stage ruling (E0 route by item class: cognate → image → engineered ≥95% context → single ≤6-word L1 micro-gloss; E1/E2 strip the scaffold), the cluster ban (the hasta-luego/adiós failure was clustering AND missing scaffold), the ≤2 introductions/session budget, and the amended anti-wall policy text are all adopted as the introduction protocol. The user's gloss-always instinct is adjudicated per Grok: right at E0 for non-associable items, wrong as standing policy — retrieval needs the crutch gone.
2. **AMEND (stale input):** item §3.8 (personalization anchors from profile hooks) is STRUCK — personal-data capture was removed the same day (docs/reviews-personal-data-removal.md). Association anchors come from the pack association table, cognates, images, and the learner's own ability-sheet lexicon.

**Integration rulings:** the introduce budget is enforced by r6's SessionPhaseController (sole orchestrator); S1 ledger and r6's RetrievalScheduler share one sheet-schema change (introduced_at/scaffold + next_due/interval/successive_successes written together); S3's gate:unscaffolded_new_item joins the existing critical-fault table and must not fight gate:english_wall (Grok's own constraint, accepted).

**Build order S1→S4→S2→S3 ACCEPTED**, merged with r6 into docs/build-plan-pedagogy-engine.md. Round CLOSED — CONVERGED (one same-day-staleness amendment; no rejections).
