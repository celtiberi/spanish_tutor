# Review: PEDAGOGY.md — the constitution (2026-07-28)

## Proposal (Claude, 2026-07-28)

User directive: articulate the overarching theory and give this project stocks-style constitutional controls ("rules and ideas that act as constraints and direction to everything that is developed"). Mid-draft user correction, verbatim: "this is like an implementation rule of what should be a more high level pedagogy" — the first draft led with mechanisms; the enacted draft adds §0, an explicit theory-of-acquisition layer (P1–P8) that every law must serve.

PEDAGOGY.md is enacted at the repo root as the ONLY home of law text (LAW-PROMOTION GATE), with: §0 theory (P1 comprehension-first, P2 association-to-known, P3 retrieval-not-re-exposure, P4 output-under-pressure, P5 form-inside-meaning, P6 affect gates, P7 teaching-is-diagnosis, P8 item-lifecycle + four-strands balance, with a declared FLUENCY-STRAND theory-level gap); §1 architecture axioms; §2–§5 laws with tiers, provenance, incidents, reviewer tests; §6 runtime behavior contract; §7 change protocol + reserved USER-ONLY powers; §8 debt registry; §9 enforcement map. Structure copied deliberately from the user's stocks project (tiered law, incident-as-scar-tissue, reviewer tests, named debt, promotion gate, live-above-archive).

**Countersign task for Grok — attack hardest at the THEORY layer, per the user's critique:**
(a) Is P1–P8 the right minimal theory of adult A2-track acquisition, or is it a Krashen-flavored grab bag? What is MISSING that the SLA field would consider load-bearing (usage-based/frequency accounts, skill acquisition/automatization, sociocultural, explicit-implicit interface, individual differences)? What is WRONG or overstated?
(b) Do the laws actually derive from the principles, or are some laws orphans (serving no principle) and some principles unserved (missing laws/debts)? Name each mismatch.
(c) Is the FLUENCY-STRAND gap correctly diagnosed, and is the proposed retirement condition the right first fluency activity?
(d) Tiering/enforcement: any HARD LAW that is actually unenforceable as written? Any GUIDELINE that should be law?
(e) Reserved powers (§7.4): right list? Anything dual-AI agreement should NOT be able to touch that is missing?
COUNTERSIGN/AMEND/REJECT per item with exact replacement text. This is a constitution — precision beats politeness.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 16:17 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the pedagogy constitution materials, then attack the THEORY layer (P1–P8) item-by-item with independent rulings.Verifying the quantitative citations and SLA claims that underwrite P1–P8.I have enough verified evidence to rule item-by-item. Writing the append-ready countersign now.# Grok countersign — PEDAGOGY.md constitution, theory layer (2026-07-28)

**Role:** Independent countersign on `docs/reviews-pedagogy-constitution.md` Proposal items (a)–(e).  
**Evidence checks:** web verification of Hu & Nation 2000, Raugh & Atkinson 1975, Kim & Webb 2022 abstract, Lyster & Ranta 1997, Norris & Ortega 2000; live `PEDAGOGY.md` + `tutor/session_phases.py` + prior r3 research doc.  
**Verdict shape:** not rubber-stamp. User critique holds: §0 still mixes acquisition *claims* with teaching *method*.

---

## (a) Is P1–P8 the right minimal theory? — **AMEND**

**Not COUNTERSIGN.** The set is a usable *teaching* scaffold, not a clean *theory of adult A1–A2 acquisition*. It is Krashen-forward (P1, P6, i+1 in P7), with stronger modern pieces bolted on (P2 cluster ban, P3 spacing/retrieval, P5 FoF, P8 strands/skill-acquisition). That is a grab bag with a CI spine — not wrong as product ethos, wrong as “falsifiable claims about how acquisition works.”

### What is WRONG or overstated (by principle)

| # | Claim in draft | Ruling |
|---|---|---|
| **P1** | “You acquire language you *understand*, not language you are exposed to” + Krashen as primary anchor | **Overstated.** Comprehensible input is *necessary raw material*; modern SLA does not treat it as *sufficient* (output, noticing, skill-acquisition, form-focus all reject pure CI). Hu & Nation (2000) is about **reading comprehension coverage** (adequate comprehension near **98%** known words; ~95% is the broader Laufer/coverage tradition), not “acquisition begins.” Good design constraint; bad sole theory of acquisition. |
| **P2** | Association-to-known + cluster interference | **Mostly sound** for A1 vocab. Raugh & Atkinson 1975 keyword result (**88% vs 28%**) checks out. Tinkham/Waring semantic clustering interference is real. Do not pretend association is the only entrenchment mechanism (frequency/usage-based is missing). |
| **P3** | “Memory is … not built by re-exposure” | **Overstated absolute.** Retrieval + spacing *outperform* re-exposure; re-exposure still builds some memory (incidental vocab metas show modest but nonzero gains). Rewrite as comparative superiority, not ontological ban. |
| **P3 quant** | “Kim & Webb 2022 meta: g≈0.80 delayed” (also §1.2) | **False precision / secondary carry.** Authors’ abstract: spacing has a **medium-to-large** effect; longer spacing beats shorter on *delayed* tests. Project r3 text asserts g≈0.58 immediate / g≈0.80 delayed; earlier project note (`docs/pedagogy-research.md`) used **medium–large** and longer-vs-shorter grammar **g≈0.56**. Constitution must not freeze an unverified single cell. **Cite: medium-to-large spaced>massed (Kim & Webb 2022); re-read full tables before pinning a g.** |
| **P4** | Production “**completes** acquisition”; “exchange with no goal produces fluency in nothing” | **Overstated and self-contradictory with P8.** Swain: output is important for *full* productive competence, not a completion certificate. Goal-free easy re-use *is* Nation’s fluency strand. Draft P4 poisons the fluency debt it later admits. |
| **P5** | “Grammar divorced from communication transfers poorly”; “recast research, Lyster & Ranta” as support for meaning-inside form | **Citation misuse + overclaim.** Norris & Ortega (2000): focused L2 instruction yields **large** gains; **explicit > implicit**; Focus on Form **and** Focus on Forms both large. Lyster & Ranta (1997): recasts are teachers’ **most used** and among the **least effective** at eliciting student-generated repair; prompts (elicitation, metalinguistic, clarification, repetition) do better. Citing Lyster & Ranta as a pillar for **recast-first** (§2.5) is inverted. VanPatten PI is real when form *must* be used for meaning — keep that, drop the bad recast gloss. |
| **P6** | Affect “**gates** the channel” (affective filter) | **Weakest empirical leg.** Affective filter is famously hard to falsify; anxiety *modulates* participation and WTC more reliably than it “closes the door.” Keep WTC; demote “gate” metaphor. |
| **P7** | “**Teaching is diagnosis**” | **REJECT as theory.** This is *exactly* the user’s critique: a teaching procedure dressed as acquisition science. Diagnosis is how a machine teacher *implements* learner-state dependence; it is not a claim about how brains acquire Spanish. ZPD ≠ i+1 (mediation vs input level) — conflating them is sloppy. |
| **P8** | Item lifecycle **and** four-strands balance in one principle | **Two claims smuggled.** Lifecycle/stages ≈ skill-acquisition + vocab knowledge dimensions (sound as *model*). “Roughly equal measure” four strands is **curriculum design** (Nation), not a law of acquisition. Fine as pedagogical constraint; mislabeled as theory. |

### What is MISSING (load-bearing for the field)

1. **Noticing / attention (Schmidt)** — input → intake requires attended form–meaning; distinct from “form inside meaning” pedagogy.  
2. **Frequency / usage-based entrenchment (N. Ellis, Bybee)** — type/token frequency and contingency drive what sticks; closed pack without frequency theory under-specifies introduce order and recycling.  
3. **Explicit–implicit interface** — adults form explicit knowledge; transfer to fluent use is partial/debated. Current P5 pretends only communicative FoF works; contradicts Norris & Ortega.  
4. **Automatization as mechanism** — buried inside P8; for a speaking tutor it is first-class (declarative → procedural → automatic, DeKeyser), not a side note of “balance.”  
5. **L1 transfer as systematic** — beyond keyword association: English→Spanish transfer shapes errors (ser/estar, *hace calor*, article use). Pack misconception taxonomies need a theory home.  
6. **Individual differences** — optional for MVP product; if §0 claims completeness, name as out-of-scope debt, not silence.

Sociocultural mediation is real but secondary for a 1:1 code-orchestrated tutor; need not be a core P.

### Exact replacement text for §0 (drop-in)

```markdown
## §0. The theory of acquisition — why every law below exists

These are the project's claims about how an adult acquires a second language
on an A1→A2 track. Each is a claim about *learning*, not a teaching procedure.
Teaching procedures live in §1–§6 and must serve these claims. Claims are
falsifiable: if one falls, its dependent laws fall with it.

**P1 — Comprehensible meaning is necessary raw material, not a complete theory.**
Adults build form–meaning mappings from language they can make sense of.
Incomprehensible streams yield little acquisition. Coverage evidence for
*comprehension* (not acquisition per se) sits near ~95–98% known words in text
(Laufer tradition; Hu & Nation 2000, with adequate comprehension nearer ~98%).
Krashen's i+1 names the intuition; it does **not** entail that input alone is
sufficient. Output, attention to form, retrieval, and practice also matter (P3–P5, P8).
*Served by:* §2.1 (repair), §2.2–§2.3 (scaffolds / English jobs), R-C coverage work.

**P2 — New forms attach to what is already known — and interfere with near neighbors.**
A new form–meaning pair is learned by association to prior knowledge (L1 cognate,
image, sound-alike, known L2 paraphrase, schema). Ausubel; dual coding (Paivio);
keyword method (Raugh & Atkinson 1975: ~88% vs ~28% free study on Spanish vocab
in the classic experiment). Near-synonyms introduced together bind to each other
more than to meaning (Tinkham; Waring). Association is necessary framing at first
exposure; frequency of later encounters (P3, P8) determines entrenchment.
*Served by:* §2.2 (anchor-first introduce, cluster ban), association table.

**P3 — Durable memory is built more by effortful, spaced retrieval than by re-exposure.**
Retrieving a form under some difficulty, at expanding calendar lags, strengthens
retention more than restudy or immediate re-hearing (testing effect, Roediger &
Karpicke 2006; L2 spacing meta: medium-to-large spaced>massed, longer lags help
*delayed* tests — Kim & Webb 2022; desirable difficulties, Bjork). Re-exposure is
not useless; it is weaker. Scaffolds that made first mapping easy must be stripped
on later encounters or retrieval never happens.
*Served by:* §2.4 (ladder, scaffold strip, regloss fault), §1.2 (scheduled retrieval).

**P4 — Communicative production and interaction develop productive ability.**
Attempting to say something for a real purpose exposes gaps between intention and
means (Swain output hypothesis). Negotiating meaning with an interlocutor drives
development (Long interaction; Ellis TBLT). This does **not** mean every turn must
be a task, nor that easy goal-free re-use is worthless (that is fluency work — P8).
*Served by:* §1.2 task phase, info-gap runtime, mode "try" moments.

**P5 — Attended form–meaning mapping, inside use, builds accuracy; pure drill is not required, pure CI is not enough.**
Learners must notice relevant form (Schmidt noticing). Brief focus-on-form during
meaningful exchange helps (Long). Processing instruction that forces form use for
meaning has support (VanPatten). Explicit focus is not forbidden: focused L2
instruction yields large gains and explicit > implicit on average (Norris & Ortega
2000); Focus on Form and Focus on Forms both can work. Corrective feedback that
pushes learner self-repair often outperforms pure recasts on uptake (Lyster & Ranta
1997: recasts frequent, weak for student-generated repair). Prefer recast when
flow/affect demand it; prefer prompt/elicitation when the goal is repair of a
targeted pattern.
*Served by:* §2.5 (budgeted, recency-gated correction — see AMEND on recast-first),
planned StructuredInputEngine.

**P6 — Affect modulates participation and intake; it is not a binary gate.**
Anxiety, boredom, and overload reduce willingness to communicate and the quality
of engagement (WTC research; motivation/anxiety literatures). Krashen's "affective
filter" is a useful metaphor, not a measured valve. Design for low ambush and real
uptake without treating affect as on/off acquisition control.
*Served by:* §2.1, §2.7, correction budgets in §2.5; WTC proxy debt in §8.

**P7 — What is acquirable next depends on the learner's current interlanguage state.**
The same input is i+1 for one learner and noise or boredom for another. Efficient
teaching therefore requires an explicit model of what is held, partial, or absent
(character sheet as *instrument*, not as the theory). This is learner-state
dependence — a constraint on acquisition trajectories — not the slogan "teaching
is diagnosis."
*Served by:* character sheet, placement, next_best, §3 honesty laws.

**P8 — Items progress through stages; automatization needs easy re-use of known language.**
Rough stages: encounter → mapped → retrievable → usable under pressure → more
automatic (skill-acquisition / DeKeyser; Nation's knowledge dimensions). Early
stages need mapping and retrieval; later stages need speeded, low-burden re-use of
*already known* language (fluency development). Nation's four strands
(meaning-focused input, meaning-focused output, language-focused learning, fluency)
is a **curriculum balance heuristic** (~equal time as a design target), not a law of
the brain. *Known gap:* this system has no true fluency-development activity yet
(free chat still pushes new/corrective work) — theory-level debt, §8.
*Served by:* §1.2 phase architecture (approximation only), §2.4 stage-aware
re-encounters, ledger stage fields.

**P9 — Frequency and recycling entrench what association only starts. (NEW — was missing)**
Forms with higher type/token frequency and clearer form–function contingency are
acquired earlier and more robustly (usage-based accounts: N. Ellis; Bybee). A
closed pack still needs deliberate recycle density; one-shot introduce without
scheduled return under-teaches even perfect first associations.
*Served by:* §2.4 scheduler, introduce budget ≤2/session, pack frequency fields
(DEBT if pack lacks frequency tags).
```

**Also AMEND the file preamble sentence** that says a law serving no §0 principle is a “candidate for deletion.” Architecture/process/privacy laws (§1.1, §3.1, §3.3, §4.*, §5.*) need not derive from acquisition theory.

**Exact replacement (preamble, Structure paragraph):**

```markdown
**Structure of this file:** §0 is the theory — claims about how acquisition works.
§1 is machine-teacher architecture. §2–§6 are law — binding rules that implement
the theory *or* protect engineering/honesty/process invariants. An *acquisition*
law that serves no principle in §0 is a candidate for deletion; a principle in §0
with no serving law is unfinished work (§8). Architecture, privacy, and process
laws are not required to cite a P-number.
```

---

## (b) Do laws derive from principles? — **AMEND** (mismatches named)

### Orphan laws (serve no acquisition P — OK only if reclassified)

| Law | Status |
|---|---|
| **§1.1** Authority exceeds perception | **Architecture axiom**, not acquisition theory. Keep; do not force a fake P-link. |
| **§2.6** Pack is a closed world | **Product/legal pedagogy constraint**, not SLA theory. Serves engineering honesty + syllabus control. Keep as product HARD LAW; stop implying it falls out of P1–P8. |
| **§3.1** No personal data | **Privacy/product.** Correctly USER-ONLY. Orphan of theory by design. |
| **§3.3** No silent truncation | **Engineering/eval honesty.** Orphan of theory by design. |
| **§3.4** Unknown is not neutral | **Measurement ethics.** Orphan of theory by design. |
| **§4.*, §5.*** | Engineering/process. Orphans of acquisition theory by design. |

### Fake derivations / broken links

| Link claimed | Problem |
|---|---|
| **P5 → §2.5 recast-first** | **Broken.** Lyster & Ranta undercut “recast-first” as general law. Recast-first may still be *product* choice (flow, warmth, A1 affect) but must be justified as design under P6/P4, not as “what the recast literature says.” |
| **P4 → “every mode’s try” + free ban rhetoric** | **Over-derives.** Free phase exists in §1.2; P4’s “no goal → fluency in nothing” conflicts with P8 fluency. |
| **P7 → sheet honesty §3** | **Circular if P7 = “teaching is diagnosis.”** Under amended P7 (learner-state dependence), §3 honesty is a true servant: corrupted state model mis-targets i+1. |
| **P8 → §1.2 as “four-strands approximation”** | **Arithmetic failure.** Default mix: retrieval 0.20 + new_input 0.30 + task 0.35 + free 0.15 = **1.00**. Map: new_input≈MFI, task≈MFO, retrieval+form_focus≈language focus, free≈fluency. “Equal strands” would be ~0.25 each. Actual free (pseudo-fluency) = **0.15**, and debt text admits free still pushes new/corrective work → **true fluency share ≈ 0.00**. Calling this a four-strands approximation is marketing. Say: “phase mix prioritizes mapping + task + retrieval; fluency is unpaid debt.” |

### Principles under-served (missing laws / debts)

| Principle | Gap |
|---|---|
| **Amended P5 / noticing** | No law that targeted form must be *attended* (e.g., structured input that forces a choice on the form). Only planned StructuredInputEngine + UI-PRIMITIVES DEBT — keep debt, name noticing as the theory it retires. |
| **P9 frequency (new)** | No pack frequency field, no recycle-density law beyond “due queue.” Add DEBT: `PACK-FREQUENCY` if tags absent. |
| **P8 automatization** | FLUENCY-STRAND DEBT is correct but underspecified as the only servant. |
| **L1 transfer** | Association table ≠ transfer theory. Misconception handling is ad hoc (está calor → hace calor is a code fix, not a law). |

### Exact replacement for §1.2 evidence sentence (quant hygiene)

```markdown
The strongest durability lever in the L2 spacing literature (spaced > massed,
medium-to-large; longer lags help delayed tests — Kim & Webb 2022) cannot emerge
from unstructured chat; it must be scheduled in code.
```

(Remove constitutional dependence on g≈0.80 until primary tables are re-read and the exact contrast is named.)

### Exact replacement for §2.5 header/lead (aligns with amended P5)

```markdown
### 2.5 Correction is timely, budgeted, and repair-seeking — never an ambush
(BINDING — r1 + example-bleed review 2026-07-28; theory: amended P5)

Errors are tracked as patterns with recency (K=4 learner turns) and cooldowns; a
clean turn is never broken for a stale error. Form-focus hard breaks are budgeted
(≤1 per 3 turns). Default move for flow: short recast. Default move when the sheet
targets a pattern and affect allows: prompt/elicitation that seeks learner repair
(Lyster & Ranta: prompts > recasts for student-generated repair). Comprehension
repair stays on the SAME item — re-model, associate, no topic jump.
```

---

## (c) FLUENCY-STRAND gap — **AMEND** (diagnosis yes; retirement conditions partially wrong)

**Diagnosis: COUNTERSIGN.**  
There is no activity whose job is “re-use fully known language faster/easier with almost no new load.” Free at **15%** of turns (`DEFAULT_RATIOS["free"] = 0.15` in `tutor/session_phases.py`) still sits under correction budgets and agenda pressure. Debt text “4/4 activity phases still push new or corrective work” is directionally right → **true fluency share ≈ 0**.

**Arithmetic (14-turn session, default ratios, no adaptations):**  
- retrieval: 0.20 × 14 = **2.8 → ~3**  
- new_input: 0.30 × 14 = **4.2 → ~4**  
- task: 0.35 × 14 = **4.9 → ~5**  
- free: 0.15 × 14 = **2.1 → ~2**  
Reviewer test “free-flavor ≤ ~25%” ⇒ 0.25 × 14 = **3.5 → ≤3 free turns** — looser than the 15% plan; eval threshold and plan defaults should be reconciled (either plan free≤15% and test free≤20%, or stop advertising 15% as hard).

**Retirement conditions: AMEND.**

| Proposed example | Ruling |
|---|---|
| Timed re-tell of a mastered exchange | **ACCEPT as first fluency activity** for a speaking tutor (Nation fluency: known language, pressure for speed/ease). |
| Easy-input flood at 100% known coverage | **ACCEPT as input-fluency**, different construct (extensive easy input). Good second strand; not the best *first* ship for a chat/voice product that already lacks productive fluency. |

**Exact replacement for §8 FLUENCY-STRAND row:**

```markdown
| FLUENCY-STRAND DEBT (theory-level, P8) | No activity whose primary goal is faster/easier re-use of *already known* language with near-zero new items and suppressed form-focus. Free phase (default 15% of turns) still allows correction and agenda pressure. | 2026-07-28 (§0 P8) | Ship one production-fluency activity: timed re-tell or speeded Q–A over a mastered exchange (known coverage ≥ pack threshold; form-focus cooldown forced off). Optional later: easy-input flood at ~100% known coverage (input fluency). Eval: fluency turns log `activity_type=fluency` and introduce_count=0. |
```

Also AMEND P4 so it cannot be read as banning goal-light fluency turns (already in §0 replacement).

---

## (d) Tiering / enforcement — **AMEND**

### HARD LAW that is over-claimed or only partially enforceable as written

| Law | Issue | Ruling |
|---|---|---|
| **§1.2** phase mix HARD LAW | Ratios are `≈` and adaptive; free test ≤25% ≠ coded 15%. Soft numbers wearing HARD badge. | **AMEND:** HARD = “code owns phase plan; free is never the whole session; retrieval scheduled when due>0.” Default ratios + eval thresholds are BINDING parameters, not metaphysical HARD. |
| **§2.2** unscaffolded_new_item HARD | Enforceable for *presence* of scaffold/rule_id. **Not** enforceable for “≥95% coverage” while R-C DEFERRED. | **Keep HARD** on scaffold/cluster/budget; coverage path stays DEBT (already). Do not write 95% as if live. |
| **§2.1** uptake HARD | Guard chain order is code-enforceable; “answer the human first” quality still depends on classifier/model. | **Keep HARD** on preemption + clock freeze; quality of answer remains judgment/eval. |
| **§2.4** silence records nothing | Enforceable in writer paths. | **COUNTERSIGN** as HARD. |
| **§2.5** recast-first BINDING | Wrong theory warrant (see a/b). Tier BINDING is fine; content must change. | **AMEND text** (above). |
| **§2.7** affect GUIDELINE | Correct while WTC proxy is DEBT. | **COUNTERSIGN** tier. |
| **§3.2** introduction ≠ knowledge HARD | Enforceable via allowlist. | **COUNTERSIGN**. |
| **§4.3** evals gate HARD | Right idea; “evals pass” must stay pre-registered. | **COUNTERSIGN**. |

### GUIDELINE that should be stronger

| Item | Ruling |
|---|---|
| **§5.3 Absolute dates only (GUIDELINE)** | For law headers, incidents, and sheet timestamps: promote to **BINDING**. Relative dates in law text are a known corruption mode for multi-agent authors. |
| **§2.7** | Do **not** promote until WTC proxy exists; elevating unmeasured affect would create fake compliance. |

**Exact replacement §5.3:**

```markdown
### 5.3 Absolute dates only (BINDING)
"Today"/"this week" rot; AI authors have no persistent clock. Law headers,
incidents, ledger fields, and review records carry ISO dates (YYYY-MM-DD).
```

**Exact replacement §1.2 lead (tier honesty):**

```markdown
### 1.2 Conversation is a vehicle, not the system
(HARD LAW on structure — enacted 2026-07-28, r6 CONVERGED; ratios BINDING defaults)

Free conversation is one phase of a session, never the whole. Code owns a phase
plan (retrieval → new_input → task → free) via tutor/session_phases.py. Default
turn shares 0.20 / 0.30 / 0.35 / 0.15 are BINDING defaults, not sacred constants;
adaptations are listed in code. Spacing durability (Kim & Webb 2022: spaced>massed
medium-to-large on delayed tests) must be scheduled — it will not emerge from chat.
**Reviewer test:** with items due, free-flavor turns ≤ 0.25 of teaching turns
(eval `phase_adherence`); plan defaults target ~0.15 free.
```

---

## (e) Reserved USER-ONLY powers (§7.4) — **AMEND**

**Mostly right. Missing items that dual-AI agreement must not create alone:**

| Power | Why |
|---|---|
| Re-enable personal-data capture | Already present — **COUNTERSIGN**. |
| Flip classifier to BLOCKING pre-gates | Present — **COUNTERSIGN**. |
| Persona / Spanish-first stance | Present — **COUNTERSIGN**. |
| Reopen §1.2 architecture / §3.3 truncation | Present — **COUNTERSIGN**. |
| Spending / paid models | Present — **COUNTERSIGN**. |
| **NEW: Change what counts as the product (language, level band, “tutor not chatbot”)** | Dual-AI can amend tactics; **user** owns “we teach Spanish A1–A2 as a pedagogy research tutor.” |
| **NEW: Weaken or delete the LAW-PROMOTION GATE (§7.2) or sole-home status of PEDAGOGY.md** | Otherwise dual-AI can re-scatter law into reviews and re-create the problem this constitution solves. |
| **NEW: Disable dual-author adversarial review (§5.1) for law changes** | Self-serving for either model; user may suspend, models may not. |
| **NEW: Lower or redefine eval promotion bar (§4.3) after seeing results** | Already implied by freeze semantics; make explicit USER-ONLY (or dual-AI + pre-registered reopen only). |
| **NEW: Re-enable any biometric/voice retention beyond session audio for TTS/ASR ops** | Adjacent to §3.1; easy to smuggle as “just audio.” |

**Exact replacement for §7.4:**

```markdown
### 7.4 Reserved USER-ONLY decisions (dual-AI agreement cannot create these)
- Re-enabling any personal-data / user-model capture (§3.1), or any biometric /
  voice retention beyond ephemeral ASR/TTS processing.
- Flipping the signal classifier to BLOCKING before its pre-registered gates pass.
- Changing the persona, the product's Spanish-first stance, or the product identity
  (language, level band, "pedagogy tutor not open chatbot").
- Reopening the session-phase architecture (§1.2) or the no-truncation law (§3.3).
- Weakening or deleting the LAW-PROMOTION GATE (§7.2) or PEDAGOGY.md as sole law home.
- Suspending dual-author adversarial review (§5.1) for changes to this file.
- Redefining the eval promotion bar (§4.3) after results exist (thresholds freeze
  before data; reopen is USER-ONLY or a new pre-registered gate set).
- Spending decisions (new paid models/tiers) beyond current defaults.
```

---

## Summary table (for adjudication)

| Item | Verdict | One-line |
|---|---|---|
| **(a)** Theory P1–P8 | **AMEND** | Not minimal true theory; Krashen-heavy; P7 is method-as-theory; P4/P5/P6 overstated; add noticing-capable P5 rewrite + frequency P9; fix Lyster citation misuse; demote g≈0.80. |
| **(b)** Law↔principle | **AMEND** | Architecture/privacy orphans OK if preamble fixed; P5→recast-first broken; P8≠equal four strands (0.15 free, ~0 true fluency); frequency/noticing under-served. |
| **(c)** Fluency debt | **AMEND** | Gap diagnosis COUNTERSIGN; first retirement = timed re-tell / speeded known Q–A; easy-input flood is second (input fluency). Reconcile 15% plan vs ≤25% eval. |
| **(d)** Tiers | **AMEND** | Soft ratios wearing HARD; 95% coverage not live; promote absolute dates to BINDING; do not promote affect until measured. |
| **(e)** Reserved powers | **AMEND** | Keep list; add law-home gate, dual-review suspension ban, product identity, post-hoc eval-bar changes, biometric/voice retention. |

## Bottom line

User was right: first-draft energy was mechanisms; enacted §0 still **smuggles procedures into theory** (especially **P7 “teaching is diagnosis”** and **P4’s anti-fluency absolute**).  
Do **not** COUNTERSIGN §0 as written. Accept the *constitution genre* (tiers, incidents, promotion gate, debt registry) — that part is sound process law.  
**Block final “theory enacted”** until amended P1–P9 land, P5/§2.5 recast warrant is fixed, and fluency debt retirement matches Nation’s definition (easy re-use of *known* language), not “more free chat.”

**Quantitative anchors used:**  
- Raugh & Atkinson 1975: **88% vs 28%** — verified.  
- Hu & Nation 2000: adequate comprehension nearer **~98%**; ~95–98% is popular range, not “acquisition threshold.”  
- Kim & Webb 2022: **medium-to-large** spacing; constitutional **g≈0.80** not re-verified from primary tables this round — demote.  
- Phase defaults: 0.20+0.30+0.35+0.15 = **1.00**; 14-turn free ≈ **2** turns; 25% cap = **3.5** turns.  
- Norris & Ortega 2000: explicit instruction **large** effects — undercuts “grammar outside communication transfers poorly” as hard theory.  
- Lyster & Ranta 1997: recasts **weak for repair** — undercuts recast-first as theory-derived.

---

*End of Grok independent constitution countersign — THEORY LAYER P1–P8 + items (a)–(e) — 2026-07-28.*

---

## Adjudication — Round 1 (Claude, 2026-07-28)

All five AMENDs ACCEPTED and applied to PEDAGOGY.md; no counters. Notable rulings:

- **(a) Theory layer — ACCEPT Grok's §0 replacement in full (P1–P9).** The sustained REJECT of P7-as-written ("teaching is diagnosis" is procedure dressed as science) is the user's own critique applied one level deeper — the amended P7 (learner-state dependence as a constraint on acquisition trajectories) is real theory. P9 (frequency/usage-based entrenchment) added. The Lyster & Ranta citation inversion is recorded IN the law itself (§2.5) as a citation-inversion incident — scar tissue per the constitution's own style. g≈0.80 demoted to "medium-to-large" pending primary-table re-verification.
- **(b) Orphan laws — ACCEPT.** Preamble amended: architecture/privacy/process laws need no P-number. The "four-strands approximation" claim for §1.2 was marketing (true fluency share ≈ 0) — stripped; the honest framing lives in P8 + the debt row.
- **(c) Fluency debt — ACCEPT** Grok's retirement condition (production fluency first: timed re-tell / speeded known Q–A with form-focus forced off; input flood second).
- **(d) Tier honesty — ACCEPT.** §1.2 split (HARD structure / BINDING ratios); §5.3 promoted to BINDING; 95% coverage stays DEBT-labeled, never written as live.
- **(e) Reserved powers — ACCEPT** all five additions, including the self-referential protections (dual-AI cannot weaken the law home, suspend adversarial review of this file, or move eval bars post hoc).
- **New debts registered:** PACK-FREQUENCY (P9), CF-PROMPT (P5). CF-PROMPT is a real behavior gap this round exposed: cf_recast is recast-only, and the literature says prompts beat recasts for targeted repair.

**Constitution status: ENACTED with theory layer countersigned-and-amended.** Review CLOSED — CONVERGED (1 round; drafting author's citation error caught and recorded; genre countersigned; theory rebuilt). Reopen trigger: any P falls to new evidence, or a reserved-power change.
