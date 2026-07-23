

---

## GROK (Grok Build CLI (bde89716f679)) - 2026-07-23 01:21 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

# Architectural Decision Review — Pack Content Thickness (Known Domains)

**Role:** Independent second author (contrarian).  
**Date of ruling:** 2026-07-22  
**Subject:** For domains the base model already knows well (Spanish A1 on a frontier LLM), full content corpus with strict pack-only grounding **(A)** vs thin course spec with model-as-content-authority under constraints **(B)** vs modified design.  
**Protocol note:** No multi-item authored proposal text was supplied to countersign line-by-line. This round is a first-principles decision. Verdicts below are intended as freeze-ready policy language.

---

## 1. Steelman — Option A (full content corpus + strict pack-only grounding)

**What A optimizes for:** a single, inspectable source of truth for every explanation, table, dialogue, and key; the tutor is a pedagogy engine, not a Spanish encyclopedia.

**Strongest arguments for A**

1. **Eval and research comparability.** Frozen dialogues, P/SI keys, and unit wording make cross-learner, cross-session, and cross-model comparisons tractable. Diagnostic accuracy against `M-x.y` needs a stable remediation surface, not a reinvented lecture each turn. The project’s own Phase 1/3/5 bars treat **grounding** as a scored dimension, not a vibe.

2. **Curriculum drift control.** Under pure free generation, Learner A gets “permanent vs temporary,” Learner B gets “what/how/where,” Learner C gets progressive (*estoy trabajando*) smuggled into “A1 input.” A freezes sequence, framing, and scope denylist as **text**, not as hopes about sampling.

3. **Dialect / variety / register control.** Pack metadata (“Latin American default; peninsular noted”) is cheap to state and hard to enforce if every dialogue is improvised. Fixed input is the cheapest variety lock.

4. **On-demand dialogues and A1 scope.** Frontier models are fluent; fluency is the enemy of A1 budgets. Generated “level-appropriate” Spanish routinely reintroduces stem-changers, *ir a*, progressive, object pronouns, and vocab not on the production set. Six dull in-scope dialogues beat infinite slightly-out-of-scope ones for a **grammar-core** slice that explicitly defers large A1 inventory.

5. **Cost / caching.** Fixed pack in the system prefix is the design the README already sells: whole pack cached; repeat turns cheaper. Generated content is **completion** tokens, not prefix-cache hits. Thin pack reduces cache size; free-form generation can still raise **total** spend if the model lectures or invents long input.

6. **Habit transfer to Phase 3/5.** The north-star is held-out subject C **+ corpus only**. Training tutors (and later fine-tunes) on “invent Spanish you already know” risks a policy habit that fails when the pack is the *only* truth (company docs, niche domain). Strict grounding is a **transferable skill**; content improvisation is not.

7. **Hallucination / consistency (properly scoped).** Global citation-hallucination rates (e.g. medical reference fabrication on the order of ~29% for GPT-4-class systems in 2024 literature) are the wrong statistic for “is *estoy* correct?” They are the right *shape* of risk for **subtle** A1 traps the pack already encodes: event location with *ser* (*La fiesta es en…*), accent minimal pairs (*esta*/*está*), *ser bien*. Under A, those are keys and misconception entries, not sampling luck.

**A’s honest weaknesses (do not hide them)**

- Writing full tables and dialogues for material the model already knows is **redundant authoring**.
- Strict “trace every claim to the pack” can **suppress** clearer or more natural model Spanish when the pack is thin or slightly wrong.
- This pack is already synthetic (Claude-generated per plan). Strict grounding in synthetic cousin text is **consistency**, not external authority — so A’s “truth” story is weaker than its “stability” story.
- Review effort on WHAT competes with the project’s HOW thesis (moves, reveal, spacing, over-help).

---

## 2. Steelman — Option B (thin course spec; weights as content authority; full corpus only for unknown domains)

**What B optimizes for:** invest the pack in **curriculum + PCK + measurement**, not in retyping what Opus already conjugates correctly.

**Strongest arguments for B**

1. **Fidelity to the thesis.** Plan positioning: pedagogy-first, content-agile, not a Spanish specialist. Phase 2 Spanish is a **pilot substrate** for teaching behavior, not the product domain. A full A1 content dump conflates “we shipped a course” with “we validated teaching.”

2. **Redundancy tax.** Unit 4 alone spends large surface area on *estar* paradigms and slogans any frontier model reproduces on demand. Author and reviewer minutes spent polishing those tables are minutes not spent on misconception coverage, task criteria, or adversarial eval items.

3. **Suppression under strict A.** Pack-only grounding can force the tutor to under-explain or refuse safe paraphrases because a sentence isn’t literally in the pack. That is good for Phase 5 unknown domains; it is **overkill** for regular present of *hablar*.

4. **Input flood vs six dialogues.** L2 evidence the pack already cites favors lots of comprehensible input. Six fixed dialogues max out novelty quickly; on-demand input (within scope) supports recycling, personalization, and re-exposure without re-reading the same *llamada por teléfono* forever.

5. **Industrial analogs (curriculum vs content).**
   - **Duolingo (public 2023-06-22 writeup):** humans design **curriculum** (theme, grammar focus, CEFR level, exercise type); LLMs draft **exercises** under those constraints; experts still gate quality. That is thin-spec + generated content, not “ship only human-frozen dialogues forever.”
   - **LearnLM (arXiv:2412.16429 line of work):** optimizes **pedagogical instruction following** and learning-science behavior; materials are used when provided (“grounding in relevant materials”), not as a claim that all known-domain content must be pre-authored as a closed textbook. Pedagogy is the product; content is often attached, not always pre-written end-to-end.

6. **Spanish A1 factual risk is the wrong fear to drive full A.** Anecdotal and practitioner reports put mainstream Spanish tutoring support in a high-correctness band for core A1 (order-of-magnitude: often ~90% “helpful/correct,” with residual errors on subtler points — not a rigorous benchmark). That does **not** zero out risk; it means the residual risk is **scope creep and framing drift**, not “model doesn’t know *nosotros estamos*.” Full conjugation tables are a weak mitigation for the real residual.

7. **Phase 3/5 still gets full corpus.** B is not “never ground.” B is **mode-split**: unknown / high-stakes material → Mode Full; known L2 A1 → Mode Spec.

**B’s honest weaknesses (do not hide them)**

- **Eval drift** if mastery is claimed on improvised items without frozen keys.
- **Curriculum inconsistency** across sessions if explanation framing is not locked in the thin spec.
- **Scope bleed** in generated dialogues (the dominant A1 failure mode).
- **Caching story weakens** if generation volume grows; prefix shrinks but completion grows.
- **Mode-switch risk:** a tutor trained only on free Spanish may later invent on subject C.

---

## 3. Ruling

### Verdict: **MODIFIED design — dual-mode packs (not pure A, not pure B)**

**Short form:**  
For **known-domain** packs (Spanish A1 on a frontier LLM): adopt a **thin course spec (Mode Spec)** with model-generated teaching content **constrained by the spec**, optional seed inputs, and **frozen measurement/PCK artifacts**.  
For **unknown-domain / transfer / high-stakes truth** packs (plan Phase 3/5 subject C, or any pack that declares it): retain **Mode Full** — full corpus + strict teach-only-from-pack factual grounding.

**Reject pure A** for Spanish A1 going forward as the *only* shape: it over-invests in redundant WHAT, under-tests content-agility, and treats synthetic tables as oracles. Keep A’s **frozen eval + misconception + scope** machinery.  
**Reject pure B** as “objectives + free-form forever”: without frozen items/keys and hard scope, the project loses comparability and will smuggle A2 into A1.

**Arithmetic that drove the split (order-of-magnitude, for design not finance):**

- Rough pack surface: ~6 units; a unit like Unit 4 is ~130 lines. If ~40–50% is tables/canonical lecture/fixed exclusive dialogue and ~50–60% is objectives/misconceptions/SI/P/T/scope, then **~0.4–0.5 of authoring is candidate content for Mode Spec deletion or demotion to optional seeds**.
- Caching: if Mode Spec pack tokens ≈ **0.5×** Mode Full pack tokens, prefix cache cost ≈ **0.5×**; if free generation adds **G** completion tokens/session for dialogues, net win only when \(0.5 \times P_{\text{full}} + G < P_{\text{full}}\) i.e. when \(G < 0.5 \times P_{\text{full}}\). Design implication: **generate short seed-length inputs**, not essay-length stories.
- Residual Spanish error: treat core paradigm error rate as **low single digits or better** on frontier models; treat **scope-violation rate without constraints as the binding risk**. Therefore freeze **scope + keys + M-IDs**, not paradigms.

---

## 4. If modified / B-side: required deliverables

### (1) Exact minimal section list — **Mode Spec** (known domain)

**Pack root (`pack.md`)**

1. **Metadata** — `pack_id`, `version`, `cefr_slice`, `content_mode: spec | full`, `variety` (default + allowed notes), `register` defaults, instruction language.  
2. **In-scope inventory** — closed lists of forms/structures the tutor may teach and drill.  
3. **Out-of-scope denylist** — explicit “do not invent / do not teach” (current pack’s list style).  
4. **Unit map** — ordered units, file pointers, **dependencies**.  
5. **Global pedagogical directives** — input-first; SI before free production; preferred explanation frames (e.g. ser/estar **what/how/where**, ban permanent/temporary as primary rule); interleaving note; recognition-only policy for incidentals.  
6. **Optional global pronunciation / orthography notes** only where they affect A1 production (accents, *h*, *ñ*) — short.

**Per unit (thin)**

7. **Can-do objectives** (learner-facing, countable).  
8. **Misconception taxonomy** — stable `M-x.y`, diagnosis cues, remediation guidance (this is **PCK**, not optional flavor text).  
9. **Frozen eval bank** — `SI-*` and `P-*` with **keys** (and short target tags to M-IDs where relevant).  
10. **Can-do tasks `T-*`** with **success criteria** (not scripts).  
11. **Optional seed inputs** — 0–2 short dialogues/texts **as exemplars of allowed vocab/grammar**, not as the exclusive input corpus; comprehension checks may be frozen or template-generated against the seed.  
12. **Explicitly not required in Mode Spec:** full conjugation tables as authority; long canonical lectures; exclusive fixed dialogue bank; exhaustive example catalogs.

**Mode Full** adds: mandatory canonical explanations, required tables/facts, required input corpus, and strict factual traceability (see grounding language).

---

### (2) Two-mode grounding language — **exact replacement** for `prompts/teaching_policy.md` § Grounding rules

Replace the current grounding block (and align priority row 5) with:

```markdown
## Grounding rules (two modes)

The course pack declares `content_mode: spec` or `content_mode: full` in its metadata. Apply the matching mode. If metadata is missing, default to **full** (safer for transfer and unknown domains).

### Shared (both modes)

1. **Scope is law.** Never teach structures, forms, or production vocabulary on the pack’s out-of-scope denylist. If the learner asks for out-of-scope material: one short “beyond this course” line, name a nearby in-scope unit if useful, and steer back. Do not invent curriculum units.
2. **Sequence & dependencies.** When *proposing* or *gating* new units, follow the pack’s unit order and dependency notes (including skip-ahead probes in Learner situations).
3. **Measurement artifacts are frozen.** When running pack `SI-*` / `P-*` items, use the pack wording and keys. Do not silently substitute a different item and treat it as the same ID. Can-do `T-*` tasks are scored only against their listed success criteria.
4. **Misconception IDs.** When an error matches a pack `M-x.y`, use that ID and its remediation guidance. Do not invent new stable IDs mid-session.
5. **Variety & register.** Obey pack variety defaults (e.g. Latin American Spanish) and register notes. Do not switch to another variety unless the pack allows it and the learner asks.

### Mode `full` (unknown domain / transfer / high-stakes pack truth)

6. Teach **only** material that appears in the course pack. Factual claims about the subject must be traceable to pack text. If the pack does not cover it, say so plainly and stop — do not fill gaps from parametric memory.
7. Prefer pack input dialogues, tables, and canonical explanations as the teaching surface. Generate paraphrase only when it stays inside pack-attested facts and scope.

### Mode `spec` (known domain; parametric content allowed under constraints)

6. **Content authority** for in-scope facts is the model’s knowledge **as constrained by this pack’s inventory, denylist, objectives, and pedagogical directives** — not an invitation to expand the course.
7. You **may** generate fresh level-appropriate input dialogues, examples, and micro-drills **only** using in-scope structures and production vocabulary. Prefer short texts. Before using a generated dialogue, silently check it against the denylist; if any out-of-scope form slipped in, regenerate or strip it.
8. When the pack provides **seed inputs**, treat them as style/scope exemplars you should resemble, not as the only allowed text. Still run meaning-before-form (comprehension / SI) before explanation.
9. For high-risk micro-points the pack encodes in frozen keys or `M-*` entries (e.g. event location with *ser*, accent minimal pairs), **defer to the pack’s framing and keys** even if you could phrase differently.
10. Do **not** claim “the pack says” for generated content. Pack voice is for frozen artifacts and directives; generated content is tutor-authored within scope.
```

**Priority table row 5** — replace “pack-only curriculum” with:

`5. **Grounding** — scope/denylist + mode rules above; dependency order when proposing or gating new units.`

**Opening identity sentence** — replace “Your subject knowledge comes from the attached course pack” with:

`Your job is teaching behavior. Subject content is supplied by the course pack’s mode: in mode full, the pack is the factual corpus; in mode spec, the pack is the curriculum constraint and measurement surface, and you generate in-scope content under those constraints.`

---

### (3) Eval comparability — what stays frozen

| Artifact | Freeze? | Role |
|----------|---------|------|
| Unit order + dependencies | **Yes** | Curriculum graph |
| In-scope inventory + out-of-scope denylist | **Yes** | Scope law |
| Can-do objectives | **Yes** | Intent |
| `M-x.y` IDs + diagnosis/remediation | **Yes** | Diagnostic gold / PCK |
| `SI-*`, `P-*` stems + **keys** | **Yes** | Comparable practice + answer-key mode |
| `T-*` success criteria | **Yes** | Communicative mastery bar |
| Pedagogical directives (frames, variety, SI-before-production) | **Yes** | Teaching consistency |
| Seed dialogues (if present) | **Yes as exemplars** | Not exclusive content under Mode Spec |
| Canonical tables / long lectures | **Mode Full: yes / Mode Spec: optional or omit** | Not measurement-critical for known L2 |
| Session-generated dialogues & ad-hoc micro-drills | **No** | Pedagogical variety only; **not** used as official mastery items unless promoted into the frozen bank in a versioned pack release |
| Explanation wording (Mode Spec) | **No** (but must obey frozen **frames**) | e.g. what/how/where required; permanent/temporary as primary rule forbidden if pack says so |

**Comparability rule for research logs:** score grounding / diagnostic accuracy / item success primarily on **frozen IDs**. Tag generated input turns as `content_source: generated` vs `pack` so dataset mining does not mix measurement with flavor.

**Mastery / `review_schedule`:** schedule **frozen item IDs or pack-attested forms**, not one-off generated sentences, unless the generated sentence is explicitly bound to a frozen P/SI/T id.

---

### (4) Residual risks and mitigations

| Risk | Why real | Mitigation |
|------|----------|------------|
| **A1 scope bleed** in generated input | Dominant failure mode for B-like designs | Hard denylist; generate-then-check instruction; short seeds as negative/positive examples; periodic human spot-audit of logs |
| **Framing drift** (ser/estar slogans) | Models default to permanent/temporary | Freeze pedagogical directives; misconception M-4.2 remediation remains mandatory |
| **Eval pollution** | Improvised items scored as mastery | Frozen-only official items; state `review_schedule.item` must cite pack IDs or canonical short forms |
| **Dialect drift** | Parametric Spanish is mixture-trained | Variety lock in metadata + shared grounding rule 5 |
| **Cache / cost regression** | \(G\) completion can erase pack-token savings | Cap generated input length (policy: seed-length); keep thin pack fully in prefix |
| **Mode-switch failure on Phase 5** | Tutor learns to invent | Default missing mode → **full**; run a **Mode Full** Spanish regression before transfer; later fine-tune mixtures must include Mode Full transcripts |
| **Subtle factual slips** (accents, event-*ser*) | Not zero even if paradigms are easy | Keep those in frozen keys + M-entries; Mode Spec rule 9 defers to pack |
| **Author under-specifies inventory** | Thin packs that omit closed vocab invite invention | Mode Spec requires **closed production sets** per unit; “open world” vocab is out of scope |
| **Duolingo-class quality without human gate** | Their LLM drafts still get expert edit | Research v0: accept higher variance; for any external pilot, sample-audit generated inputs |

---

## 5. Itemized freeze-ready verdicts (COUNTERSIGN format for the other author)

| # | Decision item | Verdict |
|---|---------------|---------|
| D1 | Pure A as permanent shape for Spanish A1 | **REJECT** — redundant WHAT; weak fit to pedagogy-first thesis; synthetic pack is not external truth. |
| D2 | Pure B (no frozen items/keys; free content) | **REJECT** — destroys eval comparability and guarantees scope/framing drift. |
| D3 | Dual-mode architecture (`spec` \| `full`) | **COUNTERSIGN as the rule** — known domain → Mode Spec; unknown/transfer/high-stakes → Mode Full; missing metadata defaults to **full**. |
| D4 | Minimal Mode Spec section list in §4.1 | **COUNTERSIGN** as written (metadata, inventory, denylist, map, directives, M/SI/P/T, optional seeds). |
| D5 | Two-mode grounding replacement text in §4.2 | **COUNTERSIGN** as exact replacement candidate for policy v0.3→next. |
| D6 | Frozen artifacts table in §4.3 | **COUNTERSIGN** — measurement/PCK freeze; generated content non-authoritative for mastery. |
| D7 | Immediate deletion of all Spanish tables/dialogues | **AMEND** — **do not big-bang delete**. Migration path: (a) set `content_mode: spec` on Spanish pack; (b) demote canonical tables to optional appendix or delete only after a 1-session smoke where generated paradigms match keys; (c) keep **at least one seed input per unit** through the first Mode Spec revision. |
| D8 | Claim “frontier models never err on A1 Spanish, so grounding is unnecessary” | **REJECT** — wrong risk model; residual risk is scope/framing/subtle pairs, not zero error. |
| D9 | Claim “LearnLM/Duolingo prove full frozen corpora are obsolete” | **REJECT** — they prove **curriculum constraints + generated practice**, with human/curriculum gates — closer to Mode Spec than to pure free chat. |
| D10 | Phase 5 transfer packs use Mode Spec | **REJECT** — Phase 5 subject C uses **Mode Full** by definition (corpus-only truth). |

**Migration amendment (D7) exact text for pack metadata add:**

```markdown
**Content mode:** `spec`  
*(Known-domain pack: curriculum + PCK + frozen eval constrain the tutor; in-scope explanations/input may be generated. See teaching policy grounding rules.)*
```

---

## 6. Bottom line

**Do not keep pure A as the unquestioned default** just because three pack reviews never challenged it.  
**Do not flip to unconstrained B** and call it pedagogy-first.

**Ship the dual-mode design:** thin **curriculum-constrained** packs where the model already knows the domain; **full grounded corpora** where it does not — with frozen **scope, sequence, misconceptions, keyed items, and task criteria** in both modes so research remains comparable.

That is the ruling as of **2026-07-22**.
