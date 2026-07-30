# Research r8 — what IS progress in Spanish teaching? (progress measurement)

**Opened:** 2026-07-29 · **Author:** ⬛ Claude (round 1) · **Status:** awaiting Grok verify/refute
**User hypothesis under test:** *"tracking what words a student learned is not progress and not modern thinking in Spanish teaching."*
**System context:** the tutor's sheet tracks item ability + a spaced-retrieval schedule (lexicon/grammar), ACTFL-style can-dos (skills), error patterns, and task completions; the learner-facing journey rail and header currently LEAD with items (words planted/rooted, counts of known/emerging).

## Claims (⬛ Claude, sources dated 2026-07-29)

**C1 — The field's unit of progress is functional ability, not inventory.**
ACTFL Proficiency Guidelines (2024 revision) and the NCSSFL-ACTFL Can-Do
Statements define growth as movement along proficiency bands
(Novice-Low → … → Distinguished) across three communication modes
(interpersonal, interpretive, presentational), evidenced by what the
learner **can do** in authentic situations. CEFR is likewise
action-oriented ("can-do" descriptors). US classroom practice
operationalizes progress as rubric-rated performance on integrated tasks
mapped to those descriptors — not as vocabulary counts.
(actfl.org proficiency-guidelines-overview; NCSSFL-ACTFL Can-Do
Statements; ACTFL Performance Descriptors.)

**C2 — Assessment evidence is task performance, rated on two pillars.**
Task-based language assessment (TBLA) rates (a) the linguistic dimension —
complexity, accuracy, fluency (CAF) — and (b) the communicative
dimension — functional adequacy (did the message succeed) — the CAFFA
framework (Kuiken & Vedder). CAF indices (clause complexity, error-free
clause ratio, speech rate/pauses, lexical sophistication) rise
monotonically with rated proficiency and are standard developmental
measures in instructed SLA. Functional adequacy must be included because
tasks are goal-oriented. (Benjamins rmal.3.14; Hasnain & Halder 2024
review; Language Testing in Asia 2022; ScienceDirect CAF/FA prediction
studies.)

**C3 — Vocabulary size is a REAL but PARTIAL proxy — the carve-out.**
Size correlates strongly with all four skills (Milton; Miralpeix &
Meara), and coverage thresholds are hard evidence: ~2–3k word families
for basic conversation, first 3k ≈ 95% spoken-text coverage, 6–7k ≈ 98%
(Nation 2006). So item tracking is a legitimate *diagnostic substrate*
and scheduler input. But size tests miss depth (collocation, association,
constraints of use) and miss deployment — whether the learner can USE the
word under real-time pressure. Vocabulary knowledge is necessary, not
sufficient; it is an input to progress, not the definition of it.

**C4 — Word-count-as-progress is the canonical modern FAILURE mode.**
The gamified-app literature and practitioner critique (Duolingo streaks/
XP) converge: rewarding item counts and attendance produces an "illusion
of progress" — recognition without production, translation without
thinking in the language, streak-preservation behavior over challenge.
This is precisely the user's critique, and the field agrees.

**C5 — Dynamic assessment: progress = shrinking mediation.**
The Vygotskian line (Lantolf & Poehner) measures development as the
DECREASE in help needed for the same function — the same can-do performed
with less scaffolding is progress even when the "items" involved are
unchanged. Our scaffold-strip law (§2.2/P3) already encodes the mechanism;
we do not yet DISPLAY it as progress.

**C6 — Self-assessed can-do portfolios (LinguaFolio) are the
learner-facing standard.** Progress indicators framed as "I can…"
statements with collected evidence sustain motivation and align with
ACTFL; the learner sees function growth, not item counts.

## Verify/refute — the user's hypothesis

| Verdict | Reasoning |
|---|---|
| **VERIFIED with one carve-out** | Modern Spanish pedagogy defines and displays progress as proficiency-band movement on can-do functions, evidenced by task performance (functional adequacy + CAF) and shrinking scaffold need. A words-learned ledger as the HEADLINE is the field's named anti-pattern (C1, C2, C4, C5, C6). Carve-out (C3): item tracking remains evidence-based as an internal substrate — coverage thresholds are real, and the scheduler needs items — so the sheet keeps tracking words; the learner-facing *definition* of progress should not be words. |

## Implications for ml_teacher (proposed, ranked by evidence strength)

1. **Lead the journey with can-dos, not items (C1/C6).** The rail's
   headline unit becomes the FUNCTION ("Say how I am", "Introduce
   myself", "Order food and drink") with its proficiency state; items
   (estar, me llamo) become supporting substrate under each function.
   We already have the data: skills (can-dos with statements), the
   association table's themes, task completions.
2. **Progress evidence joins function to performance (C2).** A can-do
   advances on demonstrated task outcomes (task_complete already
   ledgered) and unscaffolded production (scaffold-strip events),
   never on introduction/exposure (§3.2 already forbids that).
3. **CAF-lite telemetry in code (C2, FLUENCY-STRAND debt).** Cheap
   per-turn indices we can already compute: Spanish ratio (exists),
   mean length of Spanish utterance, error-free turn ratio (gate +
   error patterns), self-initiated (unprompted) production rate. A
   session-over-session trend of these IS the modern progress curve.
4. **Display shrinking scaffold as progress (C5).** "Said it without
   help — first time" is a milestone the ledger can already derive
   (first unscaffolded due-success of an item/function).
5. **Header counts become function counts (C1).** "3 things you can do,
   2 emerging" + one band statement, instead of item known/emerging
   counts. Items stay one click deeper.

## Standing questions for Grok

Q1. Is the VERIFIED-with-carve-out verdict right, or does the vocabulary
evidence (C3) deserve more weight at A1 specifically — where item
acquisition is arguably the bulk of what Novice progress IS?
Q2. Are the four CAF-lite indices in implication 3 the right minimal
set for typed+spoken A1 conversation, or is any of them noise at this
level? What is the strongest cheap index we omitted?
Q3. Implication 1 re-headlines the rail by can-do function. Our can-do
inventory is small (IP-01…); themes currently stand in as pseudo-
functions. Is mapping table themes → functions defensible, or does it
need a real function inventory first (ITEM-BANK debt adjacency)?
Q4. What did we MISS — a measurement family with strong evidence not
covered by C1–C6?

---

## Process record: first invocation ABORTED (2026-07-29)

The first Grok call for this round passed the brief with the wrong flag,
so Grok received an empty subject and correctly REJECTED the invocation
("no verify/refute table is epistemically valid" on a null subject)
rather than inventing a round — the isolation guarantee holding. Full
abort text in the session transcript; re-invoked with the author claims
above inlined per its checklist.


---

## GROK (Grok Build CLI (0c785038798)) - 2026-07-30 00:15 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll act as the independent second author for research r8. First I'll load the full brief, the r8 claims, and PEDAGOGY.md so I can verify/refute without deferring.The prompt path failed; I'll load the inlined research doc and PEDAGOGY.md from the project and verify the load-bearing claims with sources.Next I'll verify Claude's C1–C6 and related sources on the open web, and pull the system's can-do / journey-rail details so implications can be ruled against law.I have enough independent evidence to rule. Append-ready research-round output follows.

---

## Research r8 — independent picture + verify/refute (⬛ Grok, 2026-07-29)

**Role:** independent second author · **Subject:** `docs/pedagogy-research-r8-progress-measurement.md` (⬛ Claude, 2026-07-29) + `PEDAGOGY.md` (enacted 2026-07-28) as law constraint · **Method:** claims treated as data only; web verification with absolute dates; arithmetic shown where quantitative; adversarial (agreement without check discarded).

---

### (1) Independent picture (dated pins)

**What “progress” is in modern instructed Spanish / L2, 2024–2026 framing**

1. **Rating unit = proficiency performance, not inventory.** ACTFL Proficiency Guidelines **2024** (released **2024-04-02**) define ability by **FACT**: Functions/tasks, Accuracy, Context/content, Text type — what the learner can *do* spontaneously across listening/speaking/reading/writing. NCSSFL–ACTFL Can-Do Statements (aligned to those Guidelines; **2026** revision of Can-Dos publicly rolled out by **2026-02-23**) are for goal-setting and charting growth, explicitly **not** letter-grade instruments. CEFR remains action-oriented can-do descriptors.

2. **Novice is not “functions without words.”** At ACTFL Novice / CEFR A1, functions are *carried by* highly formulaic, memorized phrases and high-frequency lexical frames. The field still rates the **function** (greet, identify self, answer practiced personal Qs), but the developmental *stuff* of Novice growth is largely phrase/item deployment inside those functions. Treating “item acquisition is bulk of Novice progress” as a *definition of progress* is wrong; treating it as *the main substrate of Novice evidence* is right.

3. **Assessment evidence is multi-pillar.** Standard developmental measures in instructed SLA: **CAF** (complexity, accuracy, fluency) plus **functional adequacy (FA)** — Kuiken & Vedder’s FA scales / CAFFA line (rating scale work from **2017**; FA measurement papers into the **2020s**). CAF does **not** rise strictly monotonically with proficiency (Skehan trade-off: accuracy/complexity/fluency compete under attentional load). FA is required because tasks are goal-oriented.

4. **Vocabulary size is a strong partial predictor, not the construct.** Milton-line work: vocabulary size (measured appropriately aural vs written) explains on the order of **~40–60%** of variance across four skills (broadly ~½). Nation (**2006**): for unscripted English spoken text, **~3,000 word families + proper nouns ≈ >95% coverage**; **6,000–7,000 ≈ 98%**. Size misses depth (collocation, constraints of use) and online deployment. Arithmetic: if size ≈ 0.50 of skill variance, then **≥ half of proficiency variance is non-size** → size cannot *define* progress.

5. **Word-count / XP as the *headline* is a documented misalignment, not a fringe vibe.** Gamified apps reward streaks/XP/item recognition; practitioner and product critiques (Duolingo-class) show engagement without transferable production — the “illusion of progress.” Academic CAF/FA and ACTFL/CEFR frameworks do not treat word-ledger as the proficiency unit. Calling this “the field’s named anti-pattern” overstates institutional naming; the *substance* of the critique is sound.

6. **Development ≠ static test score.** Dynamic assessment (Lantolf & Poehner line): development is visible as reduced need for mediation and movement toward self-regulation on the same function. Scaffold-strip is a partial mechanical cousin. LinguaFolio / ELP-style can-do portfolios with *evidence* are the learner-facing standard in proficiency-oriented US programs; pure self-check without evidence inflates.

**Pins for this product (ml_teacher, 2026-07-29):** sheet already has skills (IP-01…), lexicon/grammar ladder, error patterns, task_complete, scaffold state. Journey rail currently **leads** with word planted/taking-root/rooted (design 2026-07-28). That is honest durability telemetry (P3) but **wrong primary public definition of progress** relative to the field’s unit. Internal item tracking remains mandatory for §2.4 scheduler and §3.2 honesty.

---

### (2) Verify/refute table — C1–C6 + hypothesis verdict

| ID | Claim (Claude) | Ruling | Evidence / arithmetic |
|---|---|---|---|
| **C1** | Field’s unit of progress is functional ability, not inventory; ACTFL 2024 + Can-Dos + CEFR; US practice = task rubrics not vocab counts | **AMEND** | Core direction **confirmed**: ACTFL 2024 proficiency = what individuals can do; FACT organizes levels; Can-Dos chart growth; CEFR is can-do. **Amend:** (i) FACT is **four** criteria — Accuracy and Text type are co-equal with Functions, so “functional only” under-describes the rating model; (ii) “US classroom practice” is not uniform — standards-aligned programs use performance tasks; many still run vocab quizzes as local grades; Can-Dos are explicitly **not** grading instruments. |
| **C2** | TBLA rates CAF + FA (CAFFA); CAF rises **monotonically** with proficiency; FA required | **AMEND** | CAFFA / Kuiken–Vedder FA **confirmed** as serious assessment pillar. Hasnain & Halder **2024** review of oral CAF measures exists. **Refute monotonicity:** Skehan trade-off literature — complexity, accuracy, fluency compete; joint max is not expected; CAF is standard *dimensional* developmental evidence, not a single monotonic curve. |
| **C3** | Vocab size real partial proxy; ~2–3k basic conversation; 3k≈95% spoken, 6–7k≈98% (Nation 2006); necessary not sufficient | **CONFIRM** (citation polish) | Nation **2006** spoken coverage pins match: **3k + proper nouns >95%**; **6–7k for 98%** (English corpora). Milton-line ~**40–60%** variance → size is strong substrate. **Polish:** “~2–3k basic conversation” is softer practitioner shorthand; cite 3k/95% as the hard pin. Miralpeix & Meara is a looser citation cluster (size–skill work more cleanly Milton; Miralpeix & Muñoz **2018** for size–skills). Depth/deployment gap **confirmed**. |
| **C4** | Word-count-as-progress is the canonical modern failure mode; field agrees with Duolingo critique | **AMEND** | Direction **confirmed**: XP/streak/item-count as *headline* produces engagement–ability mismatch (“illusion of progress”). **Amend:** “canonical” / “field agrees” is rhetorical. Stronger wording: **widely documented product failure mode**; **not** how ACTFL/CEFR define proficiency. |
| **C5** | DA: progress = shrinking mediation; scaffold-strip encodes mechanism; not yet displayed as progress | **CONFIRM** | Lantolf & Poehner DA: mediation sensitivity + reduced help / self-regulation = developmental signal. First unscaffolded success is a **valid but thin** operationalization (full DA also tracks reciprocity, transcendence to new tasks). Product claim that strip is law but not learner-facing progress signal is fair against PEDAGOGY §2.2/P3. |
| **C6** | Self-assessed can-do portfolios (LinguaFolio) are learner-facing standard | **AMEND** | **Confirm** for proficiency-oriented US K–12 / LinguaFolio–ELP line: goal-setting + evidence + self-assessment linked to motivation, self-regulation, some achievement gains (ACTFL’s own research summary on Can-Dos). **Amend:** not global universal; **self-rating without performance evidence is noisy**; system should prefer **code-evidenced** can-do crossings over pure self-check. |
| **Verdict** | User hypothesis VERIFIED with one carve-out (items internal; functions public) | **AMEND** | **Substantively right** for *definition and learner-facing headline*. **Carve-out undersells A1:** at Novice, item/phrase acquisition is a **large share of what progress looks like empirically**, because functions *are* formulaic deployments. Correct product stance: **headline = can-do / task / mediation**; **secondary visible substrate = item durability under those functions**; never orphan item counts as the meaning of “I’m going somewhere.” |

---

### (3) What Claude MISSED (Q4 — measurement families with strong evidence outside C1–C6)

Ranked by evidence weight for an A1 conversational Spanish tutor:

| # | Missed family | Why it matters | Cheap signal in this system? |
|---|---|---|---|
| **M1** | **Automatization / fluency development** (DeKeyser skill acquisition; Nation four-strands fluency; mean length of run, phonation-time ratio, reduced mid-clause pause) | Distinct from “accuracy up.” P8 + FLUENCY-STRAND DEBT already name the theory gap. C2’s CAF names fluency then implication-3 under-instruments it. | Partial: Spanish ratio, MLU; full needs ASR timing. |
| **M2** | **Interactional competence** (turn contingency, repair initiation, response relevance, keeping exchange alive) | Interpersonal mode is half the product; CAF on monologue under-captures chat. | Partial: self-initiated production; adjacency to outstanding try; L1-escape. |
| **M3** | **Transcendence / transfer across frames** (DA + varied retrieval) | Same form in wellbeing-only frame ≠ durable can-do. §2.4 varied-retrieval rider (enacted **2026-07-29**) is the law hook; r8 never ties progress display to multi-frame success. | Yes: `frames_seen` + first success in a new frame. |
| **M4** | **Vocabulary depth / collocation constraints** (not size) | Uchihara-line: collocation knowledge associates with oral proficiency beyond mere size. C3 mentions depth then drops it. | Harder; pack collocation pairs / error patterns are a thin start. |
| **M5** | **Interpretive / comprehension coverage** (P1) | Progress is half reception at A1; C1–C6 are production-heavy. IT-01/IT-02 exist in `can_dos.py` but r8 implications ignore them. | Meaning-check success rate; re-model vs topic-jump on confusion (already law). |
| **M6** | **Global speaking probes (elicited imitation, short OPIc-like tasks)** | EI has validation literature as efficient oral-proficiency proxy — orthogonal to ledger confidences. | Future eval/placement; not free per turn. |
| **M7** | **Processability / developmental sequences** (Pienemann-style: which *form stages* emerge) | Item “known” ≠ next processable structure; pack order risk. | Research-level; don’t fake in UI. |
| **M8** | **Affect / WTC participation quality** | P6 + WTC DEBT: progress requires continued willing production; silence after ambush is regression of opportunity. | Latency, length collapse, English-escape (debt already). |

**Biggest miss vs C1–C6:** r8 equates “modern progress” almost entirely with **can-do + CAF + DA mediation**, and underweights **fluency/automatization**, **interactional competence**, and **cross-frame transcendence** — three families that are both evidence-rich and already adjacent to this codebase’s debts/riders.

---

### (4) Answers to Q1–Q3

#### Q1 — Is VERIFIED-with-carve-out right, or does C3 deserve more weight at A1?

**Ruling: AMEND the verdict — keep the carve-out, raise A1 weight of items as *evidence*, not as *definition*.**

- **Definition of progress (field):** can-do / proficiency performance (C1, C6) + task FA (C2) + reduced mediation (C5). User hypothesis on *headline* word-tracking: **holds**.
- **A1/Novice substance:** ACTFL Novice language is lists, phrases, formulaic turns. Arithmetic from Milton-class results: size ≈ **½** of skill variance ⇒ at low levels, **growing a closed pack’s deployed inventory is high-signal**, because pack size ≪ Nation’s 3k/95% world (A1 active estimates often cited ~**300–1000** lemmas depending on source — pack is a thin slice of that). So:
  - **Item acquisition is a large *share of Novice evidence*** (often the bulk of *what changes week-to-week* on a closed A1 pack).
  - **Item acquisition is not what Novice progress *is*** — progress is “I can greet / introduce / answer how-are-you with less help,” which *uses* those items.
- **Product implication:** do **not** make words the rail headline; **do** show item durability *nested under* the function they serve (“Under *Say how I am*: estar taking root”). That is the honest A1 synthesis Claude’s binary “functions good / items bad for display” slightly oversimplifies.

#### Q2 — CAF-lite indices: right set? Noise? Strongest omission?

| Index (impl. 3) | A1 typed+spoken ruling | Why |
|---|---|---|
| **Spanish ratio** | **KEEP** | Already exists; tracks L2 use vs L1 escape; aligns P1/P4 and English-as-scaffold law. |
| **Mean length of Spanish utterance** | **SOFT / often noise at NL** | Novice success is often **2–5 word formulaic** turns (`Me llamo X`, `Estoy bien`). MLU rises late; early “progress” can be longer *English* or scaffolded echo. Use only session-trend with task-type control. |
| **Error-free turn ratio** | **SOFT** | Confounded by: (i) tutor prompt difficulty, (ii) recast uptake turns, (iii) one-word answers that are “error-free” but non-progress. Prefer **targeted-pattern clean streak** (error_patterns) over global EFT. |
| **Self-initiated (unprompted) production rate** | **KEEP** | Strong WTC / ownership signal; maps to interactional competence (M2). |

**Strongest cheap indices omitted (ranked):**

1. **Unscaffolded due-success rate** (due elicit success with scaffold stripped) — purest P3/DA hybrid; ledger already almost has it.  
2. **L1-escape / help-lifeline rate** (English dependence declining) — inverse of independence.  
3. **First success in a new frame** (`frames_seen` growth) — transcendence; ties §2.4 rider.  
4. **If ASR on:** silent-pause ratio or speech rate on *known* material only (fluency strand; don’t mix with new-item turns).  
5. **Type-token ratio of learner Spanish** within session (lexical diversity) — weak alone, useful trend with Spanish ratio.

**Minimal A1 set I would ship:** (a) Spanish ratio, (b) unscaffolded due-success rate, (c) self-initiated production rate, (d) L1-escape rate. Demote raw MLU and global error-free ratio to research telemetry until task-normalized.

#### Q3 — Themes as pseudo-functions vs real function inventory?

**Ruling: theme→function mapping is not defensible as the progress unit. Use (and grow) the real can-do inventory first.**

- **Category error:** association-table **themes** are content domains (food, greetings, boat…). **Functions** are communicative acts (“I can greet a peer,” “I can say how I am”). Mapping theme → function collapses *about what* into *what I can do*.
- **Inventory already exists and is small but real:** `tutor/can_dos.py` lists **IP-01…IP-08, IT-01, IT-02, PR-01** (11 can-dos) with ACTFL-ish statements and form_hooks — not “IP-01 only.” Thin, not absent.
- **ITEM-BANK DEBT** is about PI/dictation/task banks, not a blocker for *displaying* existing can-dos. Do not wait on item-bank to re-headline the rail.
- **Defensible use of themes:** group supporting items under a can-do (“IP-04 · estar cluster”); never promote a theme to a can-do substitute.
- **AMEND path:** expand function inventory toward fuller Novice interpersonal set (request help, accept/refuse, location, age with *tener*, etc.) with pack-legal form_hooks — still **functions first**.

---

### (5) Implications vs PEDAGOGY.md — COUNTERSIGN / AMEND / REJECT

Law pins used: P3, P4, P7, P8; §1.1; §2.2 scaffold strip; §2.4 retrieval + frames rider; §3.1 no personal data; §3.2 introduction ≠ knowledge; §4.3 eval gate; FLUENCY-STRAND DEBT; prior progression-view countersign **2026-07-28** (0.55 = emerging only; known = conf ≥ 0.80 **and** solid_uses ≥ 2).

| # | Implication | Ruling | Conflict with enacted law? | Exact design direction |
|---|---|---|---|---|
| **1** | Lead journey with can-dos; items substrate under functions | **AMEND** then COUNTERSIGN | **No HARD LAW conflict.** Aligns P4, P7, §3.2 (if advances never on introduce). Tension only with *current shipped rail emphasis* on word plant/root — product, not law. | Headline unit = can-do **statement** + band (emerging/solid). Items nest under supporting can-dos. **Do not** use association themes as functions (Q3). Copy must not say “You can X” at conf **0.55** (prior amend: emerging only; solid at **0.80 + solid_uses ≥ 2**). 0.55/0.80 = **0.6875** → mastery language at 0.55 is **false**. |
| **2** | Can-do advances on task outcomes + unscaffolded production, never exposure | **COUNTERSIGN** | **Reinforces** §3.2 HARD LAW; §2.4 evidence discipline. | Wire can-do progression to: `task_complete` for task-linked can-dos; productive elicit success; scaffold-strip success. Gate: introduce/plant events **never** emit can-do unlock. |
| **3** | CAF-lite: Spanish ratio, MLU, error-free ratio, self-initiated | **AMEND** | No law conflict; partially serves P8 / FLUENCY-STRAND DEBT if fluency strand actually appears. Claiming the trend “**IS** the modern progress curve” overclaims (C2 monotonicity fail). | Ship **Spanish ratio + self-initiated + unscaffolded due-success + L1-escape**. Demote MLU & global error-free to shadow. No learner-facing CAF numbers until eval gate freezes definitions (§4.3). |
| **4** | Display shrinking scaffold as progress | **COUNTERSIGN** | Aligns P3, §2.2 (scaffold exists to be stripped). | Milestone: “Said it without help — first time” only on **code-proven** first unscaffolded due-success (or first unscaffolded can-do performance). Not on free chat vibes. Optional later: mediation step-count if DA ladder is instrumented. |
| **5** | Header = function counts + band statement; items one click deeper | **AMEND** | No conflict if counts are **evidence-true**. Conflict risk with §3 honesty if “3 things you can do” uses emerging threshold. | Header: **“N solid · M emerging”** + one band line (e.g. Novice-Low interpersonal). Solid uses known-gate; emerging uses 0.55-cross. Item counts demoted, not deleted (scheduler/user curiosity). |

**Special answer — does implication 1 conflict with any enacted law?**  
**No.** Nothing in PEDAGOGY.md requires item-led learner progress UI. §3.2 forbids treating introduction as knowledge — a can-do-led rail is *more* compliant than a plant-count headline if plant events stay labeled encounter-only. The live constraint is **honesty of thresholds and evidence**, not a ban on can-do headlining. Prior progression design already admitted can-do milestones; r8 correctly **reorders priority**, not invents can-dos from nothing.

---

### Bottom line (adversarial)

- Claude’s center of mass is **right**: modern progress ≠ words-learned ledger as definition or headline.  
- Overclaims to correct: CAF **monotonicity**; “field’s named anti-pattern”; themes as ready-made functions; CAF-lite four-pack as *the* curve.  
- Undersells: **A1 formulaic reality** (items as bulk *evidence*), **fluency/automatization**, **interactional competence**, **cross-frame transcendence**, **interpretive can-dos**.  
- **User hypothesis:** **VERIFIED for definition and display priority**; **AMEND** so A1 does not pretend functions float free of item/phrase acquisition — nest items under functions rather than exile them.

**Recommended adjudication next step (not law yet):** one design amend doc that (i) re-prioritizes journey rail can-do > item, (ii) freezes solid/emerging thresholds to sheet gates, (iii) adds unscaffolded-success + frame-transcendence milestones, (iv) leaves item ledger intact for §2.4 — then LAW-PROMOTION only if any teaching *decision* changes (display alone may not need a PEDAGOGY paragraph; decision rules for can-do promotion do).

---

*End of independent r8 round · ⬛ Grok · 2026-07-29*

---

## Adjudication (⬛ Claude, 2026-07-29) — round CONVERGED

All Grok rulings accepted; no counters. The corrections are real:

- **C2 monotonicity REFUTED, accepted.** The Skehan trade-off literature
  is the mainstream position — complexity/accuracy/fluency compete under
  attentional load; my "rise monotonically" leaned on one study. CAF is
  dimensional evidence, not a single curve; no learner-facing CAF numbers
  until eval-gate-frozen definitions (§4.3).
- **C1/C4 rhetoric trimmed, accepted** (FACT is four co-equal criteria;
  "widely documented product failure mode", not "the field's named
  anti-pattern").
- **Verdict AMEND accepted — the A1 correction is the round's key
  insight:** at Novice, functions ARE largely formulaic item deployment,
  so item acquisition is the bulk of week-to-week *evidence* while never
  being the *definition*. Product form: items NEST under the function
  they serve ("Under *Say how I am*: estar taking root") — not exiled,
  not headlined.
- **Q3 category error accepted:** association-table themes are content
  domains, not communicative functions; the rail's headline unit must be
  the real can-do inventory (11 exist in can_dos.py), grown toward a
  fuller Novice interpersonal set later. The 2026-07-29 concept-rail
  regroup (themes) was a correct step OFF the calendar but themes are the
  wrong final unit.
- **Missed families accepted** — the three that matter here and are
  already code-adjacent: fluency/automatization (FLUENCY-STRAND debt),
  interactional competence (self-initiated production), and cross-frame
  transcendence (§2.4 frames_seen rider → "first success in a NEW frame"
  milestone).
- **Ship-set for progress telemetry (Q2, accepted):** Spanish ratio +
  unscaffolded due-success rate + self-initiated production rate +
  L1-escape rate; MLU and global error-free ratio demoted to shadow.
- **Threshold honesty pins re-affirmed:** "solid" copy requires the known
  gate (conf ≥ 0.80 AND solid_uses ≥ 2); 0.55 is emerging only, never
  mastery language.

**Converged design direction (build awaits USER go):**
1. Journey rail headline = can-do statements with band state; supporting
   items nested beneath the can-do they serve; item ledger untouched
   internally (§2.4 scheduler substrate).
2. Can-do advancement wired ONLY to evidence: task_complete, unscaffolded
   productive success, scaffold-strip success — never exposure (§3.2).
3. New ledger milestones: "said it without help — first time"
   (unscaffolded due-success) and "used it in a new context"
   (frames_seen first-success-in-new-frame).
4. Header: "N solid · M emerging" functions + one band line; item counts
   demoted one level, not deleted.
5. Telemetry (shadow first): the four-index ship-set, session-over-
   session.
Law note (Grok, accepted): display reordering alone needs no PEDAGOGY
paragraph; can-do PROMOTION decision rules do — a §3.2 rider lands with
the build if/when authorized.

**Status: CONVERGED 2026-07-29 (1 aborted invocation + 1 full round).**

---

## Build record (⬛ Claude, 2026-07-29) — converged design SHIPPED, countersign pending on specifics

Implements the adjudicated direction (all five items minus telemetry,
which stays a named follow-up):
1. `can_dos.CAN_DO_THEMES` (+ reverse `THEME_TO_CAN_DO`, one-can-do-per-
   theme validated): greetings→IP-01, introductions→IP-03,
   how_are_you/states/copulas→IP-04, farewells/courtesy→IP-05,
   food/drinks/preferences→IP-06, family/people/numbers/places/
   question_words→IP-07. All other themes stay ordinary theme groups.
2. `progress_ledger.concept_groups` now emits can-do FUNCTION sections
   first (kind="can_do": id, statement, band via `_can_do_band` honesty
   gates — solid ONLY at status known; emerging at emerging/fragile/conf
   ≥ 0.55; mastery "Can …" label only at solid), each with its supporting
   item nodes (lexicon via theme route, grammar via FORM_INVENTORY
   supports) and its own ledger crossing as `evidence`; then theme/tasks
   groups for unrouted nodes. Recency-ordered throughout.
3. New ledger kinds `first_solo` + `new_context` minted at the due-
   success site (`_progress_production`), ledger-deduped, no ability
   writes, live_state_supports → None (event-facts, no recheck badge).
   new_context v1 approximation as adjudicated (fires once per item at
   its first success with ≥2 recorded frames).
4. Client: can-do section headers (band icon + phrasing; statement +
   evidence on hover), new milestone chips, header copy "can-dos solid N ·
   emerging M". app.js ?v=20260729b.
5. PEDAGOGY §3.2 rider landed + §9 row.
Verification: suite 790 passed + 17 subtests; truncation gate ok; one
golden regenerated (due arc: +first_solo:pan note + progress event — the
only delta, pinned in-test).


---

## GROK (Grok Build CLI (0c785038798)) - 2026-07-30 00:37 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the inlined research/law files so I can countersign the r8 build items against PEDAGOGY.md and prior rulings.Next I'll pull the Build record, the landed §3.2 rider, and the prior Grok r8 ruling so the countersign can be item-by-item.I have enough to rule: checking one more honesty edge on whether `status=="known"` can lag the gate, then issuing item-by-item verdicts.---

## r8 BUILD specifics — independent countersign (⬛ Grok, 2026-07-29)

**Role:** contrarian second author · **Subject:** Build record in `docs/pedagogy-research-r8-progress-measurement.md` (⬛ Claude, 2026-07-29) vs prior Grok r8 round + landed `PEDAGOGY.md` §3.2 rider · **Method:** code + law treated as DATA; ACTFL Can-Do Novice (2026) consulted for theme→function stretch calls; arithmetic shown; no deference.

**Pins used:** r8 Grok round (implication 1/4/5 AMENDs; Q3 themes≠functions; M3 frame-transcendence); prior progression countersign **2026-07-28** (solid = conf ≥ **0.80** AND solid_uses ≥ **2**; 0.55 = emerging only); `KNOWN_MIN_CONF=0.80`, `KNOWN_MIN_SOLID_USES=2`, `EMERGING_CONF=0.55`; §2.4 soft scaffold-strip; `tutor/can_dos.py` CAN_DO_THEMES; `progress_ledger._can_do_band`; `conv_session._progress_production`.

---

### Item (1) — §3.2 rider text as landed

**Verdict: AMEND** (direction COUNTERSIGN; two honesty overclaims must land in the rider)

**Match vs prior round:** Function-led public definition; items nested substrate; themes never stand in for functions; evidence-only band moves; mastery only at known gate; 0.55 emerging; event-fact milestones move no ability fields; A1 “items = bulk of evidence, not meaning” — all **match** the converged r8 adjudication.

**Fails prior constraints:**

1. **first_solo as “unscaffolded by construction”** — §2.4 strip is a **soft instruction** (`due_elicit_block`: “no re-gloss unless they fail”), not a gate-proven absence of help. Prior implication 4 required **code-proven** first unscaffolded due-success. Soft direction ≠ proof.
2. **new_context wording** encodes the v1 multi-frame **history** approximation, not Grok M3 “first success **in a new frame**.” That is acceptable only if the law names the approximation (item 5).

**Arithmetic (mastery gate in rider is correct):**  
solid gate = conf ≥ **0.80** AND uses ≥ **2**.  
0.55 / 0.80 = **0.6875** → mastery language at 0.55 is **false** (rider already forbids this).

**Exact replacement** for the production-milestones sentence in the §3.2 rider (rest of rider COUNTERSIGN as-is):

> The production-evidence milestones are code-derived event-facts that move no ability fields: **first_solo** (first **spaced due-success** under §2.4 re-encounter direction — scaffold strip is soft law, not gate-proven absence of help; copy may say “spaced recall,” not “proved without help”) and **new_context** (v1: due-success while `frames_seen` ≥ 2 — multi-frame **exposure history**, not yet frame-of-success attribution; see r8 build countersign 2026-07-29).

Also strike or soften “unscaffolded by construction” everywhere it appears as a closed proof (rider, `progress_ledger` KIND comment, `_progress_production` docstring, tests’ prose).

---

### Item (2) — `CAN_DO_THEMES` routing map

**Rule:** themes are content domains nesting **items under** can-dos — never pseudo-functions (prior Q3). One-can-do-per-theme is fine for *routing*, not for *truth* of every pairing.

| Theme → can-do | Can-do statement (machine) | Ruling | Reason |
|---|---|---|---|
| greetings → IP-01 | greet a peer | **COUNTERSIGN** | Direct. |
| introductions → IP-03 | name self/other | **COUNTERSIGN** | Direct. |
| how_are_you → IP-04 | say how I am | **COUNTERSIGN** | Direct. |
| states → IP-04 | wellbeing states | **COUNTERSIGN** | estar-predicate cluster. |
| **copulas → IP-04** | ser, estar under wellbeing | **AMEND (category error for ser)** | `estar` supports IP-04; **`ser` is identity/description** (FORM_INVENTORY already: `present_ser` → IP-07, PR-01). Theme-level dump of both into IP-04 is a stretch that falsifies nesting. |
| farewells → IP-05 | end exchange | **COUNTERSIGN** | Direct. |
| **courtesy → IP-05** | por favor, gracias, perdón under leave-taking | **AMEND (stretch / mismatch)** | IP-05 statement is leave-taking only. Sheet observer maps `gracias` → **IP-01**, not IP-05 (`character_sheet._LEXICON_PATTERNS`). ACTFL Novice groups polite social formulas with greet/leave *as practices*, but this product’s **IP-05 text does not cover mid-exchange politeness**. |
| food/drinks/preferences → IP-06 | simple preferences | **COUNTERSIGN** | Direct. |
| family/people → IP-07 | personal Qs | **COUNTERSIGN** | Direct. |
| **numbers → IP-07** | 29 number lemmas under personal Qs | **AMEND (stretch, keep with bound)** | ACTFL Novice personal Qs include **age** (numbers via *tener*); full 0–20 inventory is broader (count, price, time). Defensible only as **substrate**, not as “numbers *are* the can-do.” Prefer form-route `numbers_0_20` / `tener_age_possession` → IP-07; lexicon theme optional. |
| places → IP-07 | personal Qs | **COUNTERSIGN** | ¿de dónde / dónde? in personal scope. |
| question_words → IP-07 | ask simple personal Qs | **COUNTERSIGN** | Direct. |

**Unmapped can-dos (IP-02 formal, IP-08 task, IT-*, PR-01):** acceptable for v1; do not force-fill with theme fakes.

**Exact replacement** for `CAN_DO_THEMES` (ship this map):

```python
CAN_DO_THEMES: dict[str, tuple[str, ...]] = {
    "IP-01": ("greetings",),
    "IP-03": ("introductions",),
    "IP-04": ("how_are_you", "states"),  # copulas REMOVED — ser/estar via FORM_INVENTORY
    "IP-05": ("farewells",),             # courtesy REMOVED — ordinary theme until politeness can-do
    "IP-06": ("food", "drinks", "preferences"),
    "IP-07": ("family", "people", "places", "question_words"),
    # numbers: leave unmapped as theme; keep FORM_INVENTORY numbers_0_20 / tener_age_possession → IP-07
}
```

**If Claude insists on keeping numbers and/or courtesy in v1 without a new can-do:** COUNTERSIGN **numbers→IP-07** only with a code comment + test note “age/quantity substrate for personal Qs — not a function claim”; **REJECT courtesy→IP-05** (wrong statement). **REJECT copulas→IP-04** either way (ser is not wellbeing).

**Arithmetic (coverage):** mapped themes in shipped map = greetings, introductions, how_are_you, states, copulas, farewells, courtesy, food, drinks, preferences, family, people, numbers, places, question_words = **15**.  
After AMEND remove 3 (copulas, courtesy, numbers) → **12**.  
3/15 = **0.20** of pairings rejected/amended = not a rubber stamp on the full table.

---

### Item (3) — `_can_do_band` display gates

**Verdict: AMEND** (solid/emerging intent COUNTERSIGN; implementation under-enforces prior arithmetic)

**Shipped:** solid = `status == "known"` only; emerging = status in {emerging, fragile} OR conf ≥ 0.55; mastery “Can …” only when band solid.

**Probe (executed 2026-07-29):**

| entry | band | label |
|---|---|---|
| status=known, conf=0.5, solid_uses=0 | **solid** | **“Can greet a peer”** |
| status=known, conf=0.9, solid_uses=2 | solid | “Can greet a peer” |
| status=fragile, conf=0.3, solid_uses=1 | **emerging** | “Greet a peer” |

**Arithmetic failures vs prior pin:**

- Known gate requires conf ≥ **0.80** AND uses ≥ **2**.  
  conf **0.50** / 0.80 = **0.625** → mastery at half-confidence is **false**.  
  uses **0** < **2** → solid display without observed uses is **false**.
- Emerging was pinned to **0.55-cross**. fragile conf **0.30** < **0.55** still paints as emerging solely by status string.

**Fragile-as-emerging:** acceptable **only when conf ≥ 0.55** (non-solid but still “showing signal”). Below 0.55, band must be **quiet** (or a future “wobbly” band — not invented here). Collapsing all fragile into emerging hides DA-style regression.

**Exact replacement** for `_can_do_band`:

```python
def _can_do_band(entry: dict | None) -> str:
    """Display band: solid ONLY when known-gate arithmetic holds
    (conf >= 0.80 AND solid_uses >= 2); never trust status string alone.
    emerging ONLY when conf >= EMERGING_CONF (0.55) and not solid;
    status labels do not override the conf floor. Else quiet."""
    if not isinstance(entry, dict):
        return "quiet"
    try:
        conf = float(entry.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    try:
        uses = int(entry.get("solid_uses") or 0)
    except (TypeError, ValueError):
        uses = 0
    if conf >= 0.80 and uses >= 2:
        return "solid"
    if conf >= EMERGING_CONF:  # 0.55
        return "emerging"
    return "quiet"
```

(Wire constants from `character_sheet.KNOWN_MIN_*` / `EMERGING_MIN_CONF` rather than magic numbers.)

Header “can-dos solid N · emerging M” then inherits honest counts.

---

### Item (4) — `first_solo` definition

**Verdict: AMEND** (milestone COUNTERSIGN; “without help” inference **not airtight**)

**What code actually does:** `_progress_production` runs only after **due** lexicon/grammar **success** (`_record_due_outcomes`). Ledger-deduped. No ability write. That much is sound.

**Why “without help” is not airtight:**

1. Scaffold strip is **soft** (“no re-gloss unless they fail”) — no turn-level check that English/gloss/model-echo help was absent.  
2. Lexicon success = `word_present(due_key, learner)` — surface presence, not free unprompted production (echo of tutor try/model can still count).  
3. Prior implication 4: milestone only on **code-proven** first unscaffolded due-success — this is **code-proven due-success**, not code-proven unscaffolded.

**Acceptable product stance:** keep the event; **honest copy**.

**Exact replacements:**

- **Milestone semantics (code comment / KIND doc):**  
  `first_solo` = first **spaced due-success** for this item (re-encounter path), ledger-once.  
- **Learner copy** (`detail_for`):  
  replace  
  `«{key}» — recalled without help at a spaced re-encounter (first time)`  
  with  
  `«{key}» — first successful spaced recall (due re-encounter)`.  
- **Do not** claim DA “shrinking mediation” as proved until a help/scaffold-absent bit is instrumented (named debt: `FIRST_SOLO_HELP_BIT` optional later).

**COUNTERSIGN** shipping the milestone under the amended definition. **REJECT** closed-law language that equates due-success with proved unscaffolded production.

---

### Item (5) — `new_context` v1 approximation

**Verdict: AMEND** — **acceptable to ship v1** with honest labeling; **must not wait** on full frame-of-success attribution to ship *a* multi-frame signal; **must not claim** transcendence.

**Shipped:** once per item, on due success when `len(frames_seen) ≥ 2`. Success may be in an **old** frame. `frames_seen` is **exposure** (elicit history from tutor try/model engagement), not learner production frames.

**Vs prior M3:** Grok asked for “first success **in a NEW frame**.” v1 is weaker: “success after multi-frame exposure.” Adjudication already recorded imprecision — correct to escalate it here rather than paper over.

**Arithmetic of false-positive class:**  
If frames_seen = [wellbeing, location] purely from **tutor** elicits, and learner’s first success is still in wellbeing, v1 still mints `new_context`. That is **1 false transcendence claim per item** under the strong reading. Rate depends on frame variety before first success; not zero.

**Ruling:**

| Option | Decision |
|---|---|
| Ship v1 now? | **Yes** (event-fact, no ability write) |
| Wait for frame-of-success? | **No** as a ship blocker; **Yes** as named follow-up debt before any promotion bar uses multi-frame ability |
| Copy / law claim “new context success”? | **No** until attribution exists |

**Exact replacements:**

- **KIND / detail copy:**  
  replace  
  `«{key}» — recalled after meeting it in new contexts{ftxt}`  
  with  
  `«{key}» — spaced recall after multi-frame practice{ftxt}`  
  (or: `… after seeing it in ≥2 frames{ftxt}`).  
- **§3.2 rider:** use the amended sentence from item (1).  
- **Debt name (record in r8 doc or §8):** `NEW_CONTEXT_FRAME_OF_SUCCESS` — mint only when success frame ∉ prior production-success frames (or at least success frame is newly added this turn and was the directed “not on that list” frame). Pre-register: no ability-axis use of multi-frame until this lands (aligns §2.4 rider: multi-frame bar for promotion out of scope until revisit bound).

**COUNTERSIGN** v1 as multi-frame **exposure-at-success** telemetry. **REJECT** equating v1 with “first success in a new frame” or using it for can-do promotion.

---

### Cross-check: Build record claims vs verification suite

Build claims 790 tests + golden delta for `first_solo:pan` — not re-run in this sandboxed countersign. **Do not** treat pass-count as pedagogical countersign. Enforcement map §9 row for this rider is directionally right **after** items (1)(3)(4)(5) AMENDs land in code + law text.

---

### Bottom line (explicit)

| # | Build specific | Verdict |
|---|---|---|
| **1** | §3.2 rider as landed | **AMEND** (two honesty phrases) |
| **2** | CAN_DO_THEMES map | **AMEND** map: drop **copulas→IP-04**, **courtesy→IP-05**; **numbers→IP-07** only as optional stretch or prefer form-only; rest **COUNTERSIGN** |
| **3** | `_can_do_band` gates | **AMEND** — re-apply conf/uses arithmetic; fragile below 0.55 ≠ emerging |
| **4** | first_solo = without help | **AMEND** — keep milestone; drop airtight unscaffolded claim |
| **5** | new_context v1 | **AMEND** — ship with honest copy; transcendence waits on frame-of-success debt |

**Overall:** build is **not final as written**. Converged **design direction** remains COUNTERSIGN; **implementation specifics** need the exact replacements above before this round is closed and the §3.2 rider can honestly say “Grok-verified” on the build, not only on the research verdict.

**No full REJECT** of the ship — the five AMENDs are local and testable; none require redesign of the can-do-led rail.

---

*End of r8 BUILD countersign · ⬛ Grok · 2026-07-29*

---

## Build adjudication (⬛ Claude, 2026-07-29) — all five AMENDs accepted, round CLOSED

- **(1) §3.2 rider** — Grok's replacement sentence landed verbatim
  ("spaced recall", never "proved without help"; new_context named as the
  v1 exposure approximation). "Never trust the status string" clause
  added to the mastery-gate sentence.
- **(2) CAN_DO_THEMES** — Grok's shipped map landed exactly: copulas
  REMOVED from IP-04 (ser is identity, not wellbeing — category error;
  ser/estar route per-form via FORM_INVENTORY), courtesy REMOVED from
  IP-05 (statement is leave-taking only; the observer maps gracias to
  IP-01 — proven inconsistency), numbers REMOVED (age/quantity reaches
  IP-07 via the form routes, not a 29-lemma dump). 12 pairings remain.
- **(3) _can_do_band** — replacement landed: solid requires the gate
  ARITHMETIC (KNOWN_MIN_CONF 0.80 + KNOWN_MIN_SOLID_USES 2, constants
  imported, never the status string); emerging requires conf ≥ 0.55
  (fragile below the floor is quiet, not emerging); header counts now
  ride the same gates. Grok's executed probe (status=known, conf 0.5,
  uses 0 → wore mastery copy) was a real honesty hole in my build.
- **(4) first_solo** — kept under the amended definition; copy is now
  "first successful spaced recall (due re-encounter)"; every
  "unscaffolded by construction" claim softened in rider, KIND comment,
  docstring, and tests. Optional FIRST_SOLO_HELP_BIT noted, not opened.
- **(5) new_context** — v1 ships with honest copy ("spaced recall after
  multi-frame practice"); NEW_CONTEXT_FRAME_OF_SUCCESS DEBT registered in
  PEDAGOGY §8 with the pre-registration (no ability-axis use of
  multi-frame data until attribution lands).
- **Ordering note (adjudicated here):** can-do sections lead the rail AS
  A BLOCK before theme groups (the r8 headline principle), each block
  recency-ordered internally — pinned in tests.

Verification after AMENDs: suite 790 passed + 17 subtests; truncation
gate ok; app.js ?v=20260729c.

**r8 round + build: CLOSED 2026-07-29.** Follow-ups on record: telemetry
shadow set (Spanish ratio / unscaffolded due-success / self-initiated /
L1-escape), NEW_CONTEXT_FRAME_OF_SUCCESS debt, FIRST_SOLO_HELP_BIT
(optional), can-do inventory growth toward the fuller Novice
interpersonal set.
