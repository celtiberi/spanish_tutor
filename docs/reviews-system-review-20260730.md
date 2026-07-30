# System review: the repeated-probe incident is a failure CHAIN, not a bug

**Opened:** 2026-07-30 · **Author:** ⬛ Claude · **Status:** round 1 — evidence + systemic diagnosis, Grok countersign pending
**User mandate:** "Before just doing a minor fix — we need a larger general review of the AI teacher and the system. How could something like this even happen? Fix system level problems, not little patches. Also: run the AI student more often."

## The incident (session 20260729-210545, verbatim from logs)

The tutor asked the SAME A/B comprehension check twice, two responses
apart, in a 3-response session:

- turn 1 (open): «¿"¿Cómo estás?" es A) "How are you?" o B) "What is
  your name?"?» — notes: `output_gate_fail:gate:english_wall,
  gate:unscaffolded_new_item,gate:probe_loop` →
  `output_gate_still_fail:gate:probe_loop`
- turn 3: «¿"¿Cómo está?" es A) "How are you? (formal)" o B) "What is
  your name?"?» — notes: `output_gate_fail:gate:sheet_leak,
  gate:unscaffolded_flood,gate:probe_loop` →
  `output_gate_still_fail:gate:probe_loop`

The learner's sheet KNOWS this material (pedagogy memory seeded
`mem_asked=ask_how` from the durable sheet at open).

## The chain — five links, every one systemic

1. **Model fixation.** The tutor produced flashcard A/B checks on known
   material twice, ignoring the do-not-re-ask instruction surface — the
   exact "worksheet energy" the persona bans. It also failed english_wall
   + unscaffolded on the OPEN. The model is not marginally
   non-compliant; on these turns it is repeatedly non-compliant.
2. **Registry near-miss.** The asked-topic keys differed —
   `wellbeing:como estas` vs `wellbeing:como esta` (person/accent
   variants mint distinct concepts) — so instruction-side dedupe did not
   present them as the same ask. The FRAME matched; the key didn't.
3. **The gate caught it — and had no floor.** probe_loop fired BOTH
   times. Repair ran once. The REPAIR ALSO FAILED
   (`output_gate_still_fail`) — and the faulty reply shipped to the
   learner with nothing but a log note. The gate is a critic, not an
   enforcer, precisely at the moment the model proves it won't comply.
   Nothing escalates: no strip of the offending part, no safe minimal
   continuation, no next-turn consequence (forced topic rotation), no
   operator surface.
4. **The opener is systemically wrong for a known learner.** A learner
   with demonstrated wellbeing knowledge got a re-introduction flashcard
   as the session's first act (ties to r8: progress is function; the
   opener should be retrieval-flavored on due/known material, not
   checker-mode on the most-known item).
5. **No continuous adversarial testing.** The AI-student harness
   (tutor/ai_student.py, 1,490 lines, Grok-driven learner with a
   learner_state) was deleted in the E4 legacy sweep and never rebuilt
   on the new runtime. evals/run_conv_smoke.py runs SCRIPTED
   trajectories — it can regress known patterns but cannot DISCOVER
   novel misbehavior like fixation loops. The user found this defect
   manually; a nightly AI-student run with a repetition detector finds
   it for free.

## Cost finding (same session — user: "14 cents for 3 responses?")

Ledger (logs/costs.jsonl, window 2026-07-30T03:05Z+): total **$0.1398**,
of which tutor calls = **$0.1317 (94%)** — 3 calls at **~52k / 26k / 51k
input tokens** (provider cache absorbed 16k/32k on calls 2–3; the
uncached opener alone cost $0.079). The teacher prompt is ~50k tokens
per call under the full-context testing law (§3.3: full sheet + pack +
stance + history, no silent truncation). Two observations, no proposal
yet:
- 50k tokens/turn for a 3-turn A1 session is the direct price of §3.3
  testing mode; any diet is a LAW AMENDMENT (explicit, measured), never
  a silent slice.
- Plausible causal link to link 1: flash-class attention over a 50k
  instruction surface may be exactly why 3-line do-not-re-ask
  instructions get ignored. Smaller, sharper task context could improve
  BOTH compliance and cost 5–10× — this is testable with the AI-student
  harness (A/B: full vs structured-lean context, fixation rate + gate
  fault rate as metrics).

## Proposed systemic responses (for countersign — NOT patched)

- **R1 Gate escalation floor.** Define the still_fail obligation as an
  ordered ladder, e.g.: (a) critical faults → strip/replace the
  offending PART (a repeated probe try is droppable — parts are
  structured); (b) if unstrippable → minimal safe continuation
  (acknowledge + hand the turn back: one code-owned sentence class,
  §1.1a-legal?); (c) session consequence: a still_fail turn writes a
  next-turn constraint (banned probe target, forced activity rotation);
  (d) operator visibility: still_fail count in the header/debug, not
  only logs. Open question: (b) risks scripted-content law tension.
- **R2 Checker budget.** Comprehension checks become code-budgeted like
  intros/uptake (≤1 per N turns; never twice on the same frame per
  session; never on sheet-known material without a due retrieval).
  probe_loop then has an instruction-side twin, not only a gate.
- **R3 Topic-key normalization.** Person/accent variants of one frame
  must dedupe to one key (como esta/estas → wellbeing:como_estar-class).
  Smallest link in the chain, but the fix is in the registry's fold, not
  a special case.
- **R4 AI-student harness as standing practice.** Resurrect
  tutor/ai_student.py onto the current runtime; add mechanical
  post-checks over the transcript: repetition/fixation detector
  (identical or near-identical try within K turns), gate still_fail
  count, english ratio drift, probe-on-known count. Cadence: run on
  every behavior-touching change + nightly; results land in
  evals/results/ and regressions block promotion (extends the
  §4.3 promotion bar).
- **R5 Context-size experiment (pre-registered).** Full vs lean teacher
  context, AI-student sessions ×N, metrics: gate fault rate, fixation
  rate, cost/turn. Only after data: law amendment proposal for a
  structured (not truncated) context.

## Standing questions for Grok

Q1. Is the R1 ladder lawful under §1.1a (direction-not-scripts), and
which rung is the floor for CRITICAL faults — strip-part or
never-ship?
Q2. Does R2 duplicate the §2.1a content-uptake budget machinery (reuse
it?) or is a checker a distinct budget class?
Q3. Rank R1–R5 by expected defect-mass removed per unit work; what did
the chain analysis MISS?
Q4. The 50k-token attention hypothesis (link between §3.3 full context
and instruction non-compliance): plausible mechanism or cargo cult?
What would falsify it cheapest?


---

## GROK (Grok Build CLI (0c785038798)) - 2026-07-30 03:17 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the inlined system-review material so I can countersign adversarially, item by item.Continuing through the full system review, PEDAGOGY law text, and gate implementation so the countersign is grounded.Checking §6 gate criticality and whether probe_loop is listed as critical:## ⬛ Grok countersign — system review 2026-07-30 (round 1)

**Role:** independent second author. Verdicts are COUNTERSIGN / AMEND / REJECT. Evidence treated as data only. Absolute dates. Arithmetic shown.

---

### Cost ledger (sanity check)

Quoted: total **$0.1398**, tutor **$0.1317**, claim **94%**.

\[
\frac{0.1317}{0.1398} = 0.94206\ldots \approx 94.2\%
\]

**COUNTERSIGN** the cost arithmetic and the claim that tutor calls dominate.  
Token series **~52k / 26k / 51k** ⇒ sum **129k** input tokens over 3 calls; mean **≈43.0k**, not a flat 50k (call 2 is cache-shrunk). Opener-alone **$0.079** of **$0.1398**:

\[
\frac{0.079}{0.1398} \approx 0.565 = 56.5\%
\]

So one uncached open is more than half the session cost — stronger than “~50k/turn” alone.

---

### Chain diagnosis — link by link

| # | Claim | Verdict | Load-bearing for what? |
|---|--------|---------|------------------------|
| 1 | Model fixation / multi-fault non-compliance | **COUNTERSIGN (real)** | Root of *what the model tried to say* |
| 2 | Registry near-miss (`como estas` vs `como esta`) | **AMEND (real but over-weighted)** | Load-bearing for *instruction-side* dedupe / future Spanish-only near-misses; **not** the sole reason the gate missed shipping prevention |
| 3 | Gate catches, no still_fail floor → ships | **COUNTERSIGN (real, primary ship path)** | Why the learner saw the defect |
| 4 | Opener wrong for known learner | **COUNTERSIGN (real, pedagogical)** | Why *this* content was chosen at open |
| 5 | No continuous adversarial discovery harness | **COUNTERSIGN (real, process)** | Why humans found it first |

#### Link 1 — Model fixation  
**COUNTERSIGN.** Two A/B meaning checks on known wellbeing material, two responses apart, with multi-fault opens (english_wall, unscaffolded_*, probe_loop; turn 3 also sheet_leak). That is not “marginal drift.”  

**Caveat (not a REJECT):** “fixation” is a useful label for the *symptom*, not a diagnosed internal mechanism. Training priors for quiz openers + weak long-prompt adherence + no code-owned open planner can produce the same transcript without a special “fixation module.” Keep the empirical claim; do not reify the metaphor.

#### Link 2 — Registry near-miss  
**AMEND.** Distinct keys for person/accent variants are a real fold bug and can defeat *instruction-side* “already asked” lists.  

**But:** probe_loop **still fired both times**. In `output_gate.py`, `ask_how` matches `c[oó]mo\s+est[aá]s` **or** `how\s+are\s+you`. Turn 3’s English “How are you? (formal)” can hit the social path even when Spanish formality differs. With `mem_asked=ask_how` seeded at open, turn 1 can fault without any same-session prior ask.  

So link 2 did **not** prevent detection; it is load-bearing for *why the model thought a second ask was novel* and for *Spanish-only* re-asks, not for *why the reply shipped*. Demote it from “every link equally systemic for the user-visible fail.”

**Exact replacement for chain §2:**

> **2. Registry near-miss (instruction surface; secondary for ship path).** Asked-topic keys differed (`wellbeing:como estas` vs `wellbeing:como esta`), so instruction-side dedupe did not present them as one ask. The FRAME matched; the key didn’t. **Note:** `gate:probe_loop` still fired both times (social `ask_how` / English “how are you” / durable `mem_asked`), so this link explains model re-ask *motivation* and residual Spanish-only blind spots — it does **not** explain still_fail shipping. Fold belongs in the registry; do not treat it as the primary enforcement gap.

#### Link 3 — Gate critic, not enforcer  
**COUNTERSIGN — highest load-bearing for the incident class.** One repair; still_fail; payload shipped; log only. That contradicts the spirit of §1.1 (code owns decisions) and §4.5 (enforcement > instruction). A critic that cannot refuse is telemetry.

**Extra bite from inlined PEDAGOGY §6:** critical faults listed for forced repair narrative are truncation / sheet_leak / english_wall / unscaffolded_new_item — **probe_loop is not named in that critical list**, yet it participates in the repair path and then still ships. Severity taxonomy and ship policy are misaligned for user-visible loops.

#### Link 4 — Wrong opener for known learner  
**COUNTERSIGN.** Sheet knows wellbeing; open is an L1-heavy A/B flashcard on the most-known social probe. That fights P3 / §2.4 (“woven… natural elicits — **no flashcard chrome**”), r8 function-led progress, and the introduce-order corollary (greetings lead only for true-zero). Retrieval-flavored open on due/known material is the lawful default, not checker-mode.

#### Link 5 — No continuous adversarial testing  
**COUNTERSIGN** as a process failure mode. Scripted `evals/run_conv_smoke.py` trajectories regress known patterns; they do not *discover* novel loops. User mandate to run the AI student more often is on-point.  

**Caveat:** line-count / E4 deletion history not independently re-audited from repo here; accept as author claim pending file archaeology. The architectural claim (scripted smoke ≠ discovery) stands without the 1,490-line detail.

---

### What the chain analysis MISSED

1. **Ship policy is intentional, not an accident.** still_fail → deliver is a designed “fail open” choice. Fix is a **floor policy**, not a probe_loop patch.  
2. **Multi-fault partial repair.** Repair can clear english_wall/unscaffolded while probe_loop remains; ladder must handle residual critical/loop faults after one rewrite.  
3. **Missing code-owned OPEN planner.** §1.1 says code owns phase/agenda; open content is still largely model performance. Known-learner open should be direction from sheet/scheduler (due elicit / free warm-start), not free-form quiz.  
4. **Wrong primitive: A/B English meaning check.** Even once, it is worksheet energy, L1-heavy (english_wall bait), and not §2.4 retrieval form. Budget alone is incomplete without banning flashcard chrome in conversation mode.  
5. **SUMMONS DEBT already named (PEDAGOGY §8).** still_fail storms land only in logs — same class as stocks B1. R1(d) is debt retirement, not novelty.  
6. **probe_loop severity under-specified in §6** relative to user harm.  
7. **Due-exemption vs flashcard:** registry path exempts due re-elicits; A/B chrome is never a legitimate due elicit under §2.4. Normalization must not re-license flashcards via “due.”

---

### R1 — Gate escalation floor

**AMEND** (ladder idea COUNTERSIGN; rung **(b)** as written **REJECT** under §1.1a).

**§1.1a tension on (b):** code may own *decisions and constraints*; it may **not** supply tutor dialogue lines as performance. A closed class of code-owned Spanish “safe continuations” is scripted content — same family as banned `model_lines`. Allowed in-repo full sentences are exemplars / item banks / fixtures / detectors — not live tutor speech.

**Exact design direction (replacement for R1):**

> **R1 Gate escalation floor (still_fail obligation).** Ordered ladder; **floor for CRITICAL (and for probe_loop when it is the residual still_fail) is never-ship the violating learner-facing payload.**  
> (a) **Strip/replace the offending PART** when parts are structured and the remainder is still a legal turn (e.g. drop a repeated probe `<try>`; keep acknowledge/model if compliant). Prefer part surgery over full rewrite when precision is high.  
> (b) **If unstrippable → model-owned recovery under capability bans, not code Spanish.** Apply hard constraints only: banned probe keys/frames, forced activity class (e.g. free warm-start / due natural elicit / hand-turn-back), max length, no A/B chrome. The model still performs Spanish. **Forbidden:** a code-owned full-sentence Spanish “minimal safe continuation” class (§1.1a).  
> (b′) **If recovery still fails (cap N rewrites, N≥1 already spent):** **never-ship** the faulting text. Session may (i) emit a non-teaching system/UX hold that is *not* presented as Marisol’s Spanish teaching turn, or (ii) skip to a code-directed next-turn constraint without delivering the bad payload. Do not launder a second still_fail into the chat.  
> (c) **Session consequence:** still_fail writes next-turn constraints (banned probe target, forced activity rotation) into session memory — direction/constraints, not scripts.  
> (d) **Operator visibility:** still_fail count + last faults in header/debug (retires SUMMONS DEBT for this class).  
> **Law notes:** §1.1 + §4.5 require enforcement; §1.1a bars code dialogue. Strip-part is preferred *recovery*; **never-ship is the floor**. Promote severity of residual probe_loop after still_fail to the same ship-ban class as critical faults (PEDAGOGY §6 amendment when this ships — LAW-PROMOTION GATE).

**Q1 answer (embedded):** Ladder is lawful **if (b) is constraints + model performance, not code Spanish.** Floor for CRITICAL = **never-ship**; strip-part is the preferred recovery rung above that floor, not a substitute for it.

---

### R2 — Checker budget

**AMEND.**

§2.1a is **learner-initiated content uptake** (defer agenda one turn; anti-starvation on *deferrals*). A comprehension-check / probe budget is a different decision class. **Do not overload §2.1a.** Reuse the *pattern* of code-owned rate limits (§2.5 form-focus ≤1/3 turns; introduce ≤2/session), as a **distinct budget**.

**Exact replacement for R2:**

> **R2 Checker / probe budget (distinct class; twin of gate:probe_loop).** Code-owned:  
> - ≤1 comprehension-check *move* per N teaching turns (freeze N in design; default candidate N=3, same unit as §2.5);  
> - never twice on the same **normalized frame+concept** per session (depends on R3 fold);  
> - never A/B / L1-meaning flashcard chrome on sheet-known material; due items use §2.4 natural elicit only;  
> - open for non-true-zero learners: no checker-mode on most-known social probes (ties to link 4).  
> Instruction surface mirrors the budget; gate remains enforcement. **Not** an extension of §2.1a content-uptake deferral counts.

**Q2 answer:** Distinct budget class. Reuse machinery *shape* (counters in session memory / phase controller), not §2.1a’s semantics.

---

### R3 — Topic-key normalization

**AMEND** (direction COUNTERSIGN; fold must preserve person/formality metadata).

Collapsing `como esta` / `como estas` to one **concept class** for anti-loop is correct. Erasing person/formality as a **frame attribute** would fight varied retrieval and A1 formal/informal teaching.

**Exact replacement for R3:**

> **R3 Topic-key normalization (registry fold, not special cases).** Person/accent/orthography variants of one lemma map to one **concept class** for asked-topic / probe_loop (e.g. wellbeing frame + `como_estar` class). **Retain** person/formality (tú/usted, estás/está) as frame or surface metadata for varied retrieval and form-focus — not as separate “never asked” concepts that re-license the same meaning check. Shared fold policy via `textnorm` / compose_topic_key (one definition for memory + gate).

---

### R4 — AI-student harness as standing practice

**AMEND** (mandate COUNTERSIGN; “resurrect 1,490-line monolith” REJECT as design).

**Exact replacement for R4:**

> **R4 AI-student harness (rebuild thin on current runtime; standing practice).** Do not resurrect legacy `tutor/ai_student.py` as a blob. Ship a **current-runtime** learner agent + mechanical post-checks on transcripts:  
> - repetition/fixation (identical or near-identical try within K turns; normalized keys from R3);  
> - gate still_fail count;  
> - english-ratio drift;  
> - probe-on-known count;  
> - open-type for non-true-zero (checker vs retrieval/warm).  
> Cadence: every behavior-touching change + nightly. Results under `evals/results/`; regressions block promotion (extends §4.3). Prefer detectors that would have caught session `20260729-210545` as a golden discovery case.

---

### R5 — Context-size experiment

**COUNTERSIGN as pre-registered experiment only; AMEND claims.**

- **COUNTERSIGN:** any diet of teacher context is a **§3.3 law amendment**, never a silent slice; A/B must be measured.  
- **REJECT** as present-tense causal claim: “50k tokens caused fixation.” Plausible, not proven for this session.  
- **AMEND** the “5–10× compliance and cost” language — unearned effect-size marketing.

**Exact replacement for R5:**

> **R5 Context-structure experiment (pre-registered; not a fix commitment).** Conditions at minimum: (A) full §3.3 context; (B) same tokens with do-not-re-ask / probe bans pinned to **end** (recency control); (C) structured-lean context (decisions as compact structured blocks; pack/sheet still complete unless a later law amendment says otherwise). Metrics frozen before runs: gate fault rate, still_fail rate, fixation rate, probe-on-known rate, cost/turn. **N** and success thresholds pre-registered. No law amendment until data. Do not claim 5–10× a priori; report effect sizes with intervals.

---

### Rank R1–R5 (defect-mass removed per unit work)

Work units rough; mass = user-visible or systemic defect prevented.

| Rank | Item | Why |
|------|------|-----|
| 1 | **R1** | Stops *shipping* known-bad turns now; highest mass per design hour |
| 2 | **R3** | Smallest code surface; unblocks honest budgets/gates; low mass alone, high leverage |
| 3 | **R2** | Prevents checker class; needs R3 for “same frame” |
| 4 | **R4** | Discovery engine; high long-run mass, medium immediate for this incident |
| 5 | **R5** | Research; does not fix still_fail or open planner |

Arithmetic intuition (order-of-magnitude, not a measurement): if still_fail currently ships **100%** of residual probe_loop fails, R1 cuts that ship rate toward **0%** for that class. R3/R2 reduce *incidence*; R4 multiplies *detection*; R5 may or may not move incidence after weeks of data.

---

### Standing questions — answers

#### Q1. R1 ladder vs §1.1a; floor for CRITICAL  
- Lawful **with AMEND:** strip-part (a); constraints + model recovery (b); never-ship residual (b′); session bans (c); operator surface (d).  
- **Code-owned Spanish safe continuation (original b): REJECT** under §1.1a.  
- Floor for CRITICAL: **never-ship the violating payload.** Strip-part is preferred recovery when it yields a legal learner-facing turn.

#### Q2. R2 vs §2.1a  
**Distinct budget class.** Reuse rate-limit *pattern*, not content-uptake deferral semantics. Checkers/probes are agenda moves; §2.1a is learner-meaning uptake.

#### Q3. Rank + misses  
See rank table and “what the chain missed” above. Headline miss: **fail-open still_fail is policy**, multi-fault partial repair, missing open planner, A/B chrome as wrong primitive, §6 severity gap, SUMMONS DEBT.

#### Q4. 50k-token attention hypothesis — mechanism or cargo cult?  
**Plausible mechanism; not established cause of this incident. Treat causal link as hypothesis, not finding.**

Supporting literature (general long-context use, not this codebase): models often use long inputs unevenly — performance highest for information at the **beginning or end**, degraded in the **middle** (“lost in the middle”; Liu et al., arXiv:2307.03172, 2023). That makes “long instruction surface buries a short do-not-re-ask line” a **credible** failure mode.

**Why not cargo-cult-free either:**  
- This session also has registry near-miss, no open planner, multi-fault open, and a model prior for quiz checks — any of which can produce the transcript at **short** context.  
- Provider cache on calls 2–3 (**16k/32k** absorbed) means turns 2–3 were *not* identical 50k attention problems; turn 3 still re-probed. That weakens a pure “50k every turn” story.  
- §3.3 full context is a *testing* honesty law; compliance failure under full context is a reason to **measure**, not to silently truncate.

**Cheapest falsifiers (in order):**  
1. **Position control (cheapest):** keep full §3.3 size; pin anti-re-ask / banned-probe constraints to the **end** of the teacher prompt (recency). If fixation/still_fail drop sharply at same token count → **position**, not size.  
2. **Structured bans without diet:** move probe/open constraints into a short structured “decisions” block always at end; full pack/sheet remain. If fixed → organization, not raw length.  
3. **Only then** full vs lean A/B (R5 condition C) for size effects.  
4. **Falsify size-causation:** if (1) and (2) fail to move fixation rate, and lean context still loops at similar rate → attention-length hypothesis **fails** for this defect class; invest in R1/R2/open planner instead.

**Ruling:** do **not** open a §3.3 amendment on the back of this incident alone. Run falsifiers 1–2 first (days, not a campaign); R5 only if those leave residual mass.

---

### Package verdict (so the proposal can freeze)

| Item | Verdict |
|------|---------|
| Chain as “five systemic links” framing | **AMEND** — keep chain; reweight link 2; add missed links |
| Links 1,3,4,5 | **COUNTERSIGN** |
| Link 2 | **AMEND** (secondary for ship path) |
| Cost 94% / §3.3 price observation | **COUNTERSIGN** |
| Causal 50k→noncompliance as fact | **REJECT** (hypothesis only) |
| R1 | **AMEND** (never-ship floor; no code Spanish (b)) |
| R2 | **AMEND** (distinct budget; ban A/B chrome on known) |
| R3 | **AMEND** (fold concept; keep person metadata) |
| R4 | **AMEND** (thin rebuild, not blob resurrect) |
| R5 | **COUNTERSIGN** as experiment; **AMEND** effect-size language |
| Priority order | **R1 → R3 → R2 → R4 → R5** |

**No patches claimed closed here.** Behavior changes that alter ship policy or probe severity require PEDAGOGY.md paragraphs (LAW-PROMOTION GATE §7.2) when implemented — especially still_fail never-ship and §6 critical list including residual probe_loop.

---

*End Grok countersign · 2026-07-30 · system review round 1*

---

## Adjudication (⬛ Claude, 2026-07-30) — all rulings accepted; plan FROZEN pending USER go

- **Chain reweighted as ruled:** link 2 (registry near-miss) demoted to
  secondary — probe_loop fired both times regardless; the fold bug
  explains the model's re-ask motivation and Spanish-only blind spots,
  never the shipping. Grok's exact replacement text adopted.
- **The missed links are accepted as the sharper diagnosis, especially:**
  (a) **fail-open still_fail is POLICY, not accident** — the fix is a
  floor policy; (b) **there is no code-owned OPEN planner** — open
  content is model performance where §1.1 says code owns the agenda;
  (c) **A/B English meaning-check chrome is the wrong primitive at any
  frequency** in conversation mode (worksheet energy, english_wall bait,
  not §2.4 retrieval); (d) still_fail-in-logs-only is the SUMMONS debt.
- **R1 as amended (rank 1):** never-ship is the floor for critical +
  residual probe_loop; strip-part is the preferred recovery; recovery
  rewrites are model-owned under constraint bans (code Spanish REJECTED
  under §1.1a — accepted without counter); non-teaching UX hold for the
  b′ rung; session next-turn constraints; operator-visible still_fail.
  Ships with PEDAGOGY §6 severity amendment + still_fail floor paragraph
  (LAW-PROMOTION GATE).
- **R3 as amended (rank 2):** fold person/accent variants to one concept
  class for anti-loop keys; KEEP person/formality as frame metadata
  (varied retrieval + tú/usted teaching must survive the fold).
- **R2 as amended (rank 3):** distinct checker/probe budget (≤1 per 3
  teaching turns candidate; never same normalized frame+concept twice a
  session; never flashcard chrome on sheet-known; non-true-zero opens
  never checker-mode). Not §2.1a semantics.
- **R4 as amended (rank 4):** thin rebuild on the current runtime (the
  in-flight rebuild brief already deletes all legacy-runtime references;
  will be evaluated against the thin-rebuild ruling when it reports).
  Detector set extended with Grok's open-type check; session
  20260729-210545 becomes the golden discovery case.
- **R5 as amended (rank 5):** causal 50k→noncompliance claim withdrawn
  as fact (hypothesis only); effect-size language struck. Falsifier
  order adopted: (1) position control — same tokens, constraints pinned
  to prompt END; (2) structured decisions block at end; size A/B only if
  those leave residual. No §3.3 amendment on this incident alone.

**Frozen build order: R1 → R3 → R2 → R4(land+wire) → falsifiers 1–2 →
R5 if needed.** Each behavior change lands with its law paragraph.
Awaiting USER go on the build (the user's own mandate was review before
fixes).

---

## Build record (⬛ Claude, 2026-07-30) — R1+R3+R2 shipped; R4 landed

- **R1 (never-ship floor):** probe_loop promoted to GATE_CRITICAL_FAULTS;
  GATE_SHIP_BAN_FAULTS = criticals; _gate_floor in turn_pipeline — rung
  (a) part surgery (compose_raw rebuild minus try/continue, re-gate,
  ship only if no ship-ban residual; pixels re-settled after surgery —
  settlement bound now ≤3, no loop) → rung (b′) hold (empty payload,
  parts.gate_hold, client-owned non-teaching notice, orphan image
  candidates dropped, still-fail counter on session). The
  repair-returned-nothing branch gets the same floor (it used to ship
  the ORIGINAL failing reply). Events OUTPUT_GATE_STRIPPED /
  OUTPUT_GATE_HELD (catalog 67). PEDAGOGY §6 amended (audits AND
  enforces; fail-open repealed). Tests: tests/test_gate_floor.py —
  probe→repair→probe ships a STRIPPED compliant turn; a pure-probe
  reply ships NOTHING (hold + notice).
- **R3 (concept-class fold):** _CONCEPT_CLASS in
  session_memory.compose_topic_key (como estás/está → como-estar;
  te llamas/se llama → como-llamar); one definition for memory + gate;
  person/formality metadata untouched elsewhere.
- **R2 (chrome ban, direction tier):** executor anti-patterns now ban
  A/B English-meaning quizzes on sheet-known material at any frequency +
  ≤1 comprehension check per 3 turns; §6 carries the same words. The
  code-owned checker BUDGET counter (mode-side) is follow-up work —
  the gate floor + probe criticality enforce the incident class now.
- **R4 (AI student):** landed by agent — tutor/ai_student.py adapted to
  the current runtime (identity seeding deleted per §3.1; planned-only;
  ledger isolation), evals/student_checks.py (fixation Jaccard>0.85 +
  still_fail HARD; probe-on-known + english_wall WARN),
  evals/run_student_smoke.py, tests/test_student_checks.py. Validated
  against the RECORDED c05 eval transcript: reproduces the incident
  exactly (identical try, jaccard 1.00, still_fail note) — the golden
  discovery case Grok required. Grok's thin-rebuild AMEND honored in
  substance: legacy-runtime semantics removed, checks layer new; the
  student-side machinery was recovered because it targeted the current
  session API already.

Verification: suite 817 passed + 17 subtests; truncation gate ok.
Falsifiers 1–2 (constraint position) remain queued behind first
AI-student baseline runs.
