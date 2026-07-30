# Design: lesson planner + small rounds with dynamic context (r9)

**Opened:** 2026-07-30 · **Author:** ⬛ Claude (round 1 analysis) · **Status:** analysis rounds in progress — NO build authorized
**User mandate:** "We are sending 50k tokens… the teacher asks a question answerable in 3 words… We probably need a planning phase and then a smaller agent phase. The planning phase gets the full context… smaller rounds with much reduced context just on specific ideas. Look at ~/repo/elfric — we really broke this down from a larger planning phase to smaller rounds with dynamic context. It worked very well. Do a few rounds analyzing and thinking about this."

## Evidence already in hand

1. **Prompt anatomy (measured tonight):** system ≈72k chars — course-pack
   palette 50.7k (70%), base teaching prompt 17.5k, persona 4k; task adds
   ~12k chars (sheet render 9.8k) + full history. Ledger: ~50k input
   tokens/call, 94% of session cost; one uncached open = 56% of a
   session's spend.
2. **Full context ≠ compliance (first AI-student baseline, 2026-07-30):**
   6-turn run under FULL context → 4/6 turns still_fail (english_wall ×1,
   unscaffolded ×3). The new floor amputates; it cannot make the
   generator good. Fix generators, not instances.
3. **elfric prior art (agent survey, cited by file):** one ~2.5k-token
   planner call (typed todos: declared inputs, operation, tool_hints,
   output_shape) + deterministic input resolution + per-round compressed
   prompts (~150 tokens median) + fresh two-message context per round +
   cache-shaped payloads. Headline measured result (commit b55af00):
   **170 LLM calls/$0.17/339s → 10 calls/$0.004/57s** on the same
   question. Full survey: appendix below.

## The mapping (ml_teacher translation)

| elfric | ml_teacher today | proposed |
|---|---|---|
| steer planner (2.5k tokens, full-ish view, typed todos) | code-side mode/phase/introduce routers (already §1.1) + NO LLM planning | **LessonPlanner call** at session open + phase transitions: receives sheet PROJECTION + pack SLICE (code-selected: due items, introduce candidates, active can-dos, their table entries) + curated history brief; emits a typed **LessonBrief** |
| TypedTodo (inputs declared; code resolves) | due block / introduce plan already DECLARE exact keys — then we ship the whole pack anyway | brief carries target items WITH their anchors/glosses inline; executor never sees the 191-key pack |
| dispatch rounds (~150-token compressed prompt + declared inputs only) | every turn gets 17.5k-char contract + 50.7k-char pack + 9.8k-char sheet + full history | **turn executor**: stable compact core contract (~4k chars, hand-written) + persona + brief + curated exchange window + this-turn instructions + DYNAMIC table entries (see below) ≈ **4–6k tokens/turn** |
| fresh 2-message context; findings compacted, last-3 full | full history resent (§3.3) | last K=3 exchanges verbatim + ≤300-word curated session brief; full history stays on disk, auditable |
| provenance citations make narrow context safe | output gate + §1.1b settlement (STRONGER: machine-checked behavior, not citations) | unchanged — the gate is the safety net that makes the diet safe (§4.5 enforcement > instruction; pack scope is ALREADY gate-enforced: unscaffolded/cluster/denylist checks are code) |
| no mid-turn re-planning; local retry-once | gate repair (retry-once) ✓ | keep; re-plan only at phase boundaries / task completion / still_fail streak ≥2 (session consequence) |
| cache-shaped: byte-stable system + volatility at tail | system already stable/cached (32k cache hits observed) | keep; smaller stable prefix caches better and opens stop costing 8¢ |

**Dynamic context (the user's phrase, made concrete):** the executor's
table slice is assembled per turn by CODE: brief targets ∪ due keys ∪
introduce plan ∪ **table keys detected in the learner's turn** (we
already scan learner text against the table for uptake/observation) ∪
keys in the last exchange. A learner question about ANY pack word pulls
that entry into the next round automatically — declared, resolved,
logged. elfric trap #13 (planner naming unknowable fields) is closed by
validating every brief key against table+sheet in code before the round.

## The §3.3 collision, faced head-on

§3.3 bans silent truncation of the teacher path. This design does not
truncate — it RE-ROLES: the planner is the teacher-of-record and sees
everything; the executor performs one move against a complete-for-its-
role, validated, LOGGED brief. Everything omitted is omitted by declared
design, auditable per turn (the brief is an artifact in the debug ring,
like elfric's run manifest). Ship gate: §3.3 amendment text +
pre-registered A/B (below) — never a quiet flag flip.

## Pre-registered referee (extends R5; supersedes its conditions)

Arms: (A) full context (today); (B) planner+rounds. Instrument: AI-student
harness, N≥6 sessions/arm, same personas/seeds; metrics frozen: gate
fault rate, still_fail rate, fixation rate, probe-on-known, cost/turn,
latency/turn, plus BLIND transcript grades (grok blind-score, rubric
frozen first). Promotion: B must be ≼A on faults and ≥A−0.5 band on blind
grade at ≤0.35× cost. Kill: any honesty-law regression (sheet writes,
scope escapes reaching the learner past the gate).

## Standing questions for the Grok rounds

Q1. Planner cadence: session-open + phase transitions (+ still_fail
streak) vs every-turn cheap planner. elfric plans once per request;
our "request" analogue is arguably the PHASE, not the turn.
Q2. Executor's guaranteed-context floor: what must ALWAYS be present for
lawful teaching (uptake law §2.1 — learner asks about out-of-slice
words; repair targets; register rules)? Is the dynamic-slice union
above sufficient or does it need a fallback lane?
Q3. Does gate-side scope enforcement fully replace the pack-in-prompt
(§2.6 closed world) or does the model need SOME palette signal (topic
titles? a 1k-token index) to stay generative within scope?
Q4. The LessonBrief schema: what are OUR TypedTodo axes? Proposal:
targets[{key, gloss, anchor, move}], allowed_new[], banned_asks[],
due[], scene_goal, register, exit_criteria. What's missing/wrong?
Q5. Migration: arm B behind TEACHER_CONTEXT=brief env + dual-path sunset
date; is the two-arm A/B sufficient or is elfric falsifier-1
(position control) still worth running FIRST as the cheap test?

---

## Appendix — elfric survey (agent, 2026-07-30, cited by file)

(Direct quotes and measurements from /Users/patrickcremin/repo/elfric;
2,435 real llm_call_done records analyzed.)

- Planner: `steering.py` (426 L) — reasoning call, no tools, JSON out;
  receives curated brief + memory + tool NAMES only; "Remove steering
  research phase… Trim tool list to names only (was 8K YAML)" → "$0.19 →
  $0.02" (commit 7b97ebc). Median 2,477 input tokens (p90 2,505, n=108).
- Plan artifact: TypedTodo{type, title, description, inputs[InputSpec],
  operation, output_shape, must_mutate, tool_hints, success_criteria} —
  validated by parse_typed_todo(); in-memory, never persisted.
- Rounds: resolve_inputs.py walks DECLARED inputs; nothing else enters.
  _pick_strategy is 4 lines, no LLM; 49% of production dispatches ran
  one_shot_llm (zero tools). Round system prompts compressed by a cheap
  model to median 598 chars; "Focused prompts (~300 tokens) significantly
  outperform full prompts. Models degrade with irrelevant context
  ('context rot')."
- Fresh context: tool_loop.py rebuilds [system, task+findings] each
  round; last-3 full, older 1-sentence cached summaries; 50k-char cap.
- Contract: rounds report synthesized ≤300-char results with a
  PRESERVE/REMOVE contract; raw output never crosses round boundaries.
  NO mid-turn re-planning; retry-once semantics; second grounding
  failure hard-fails ("no more silent redaction", 744ec72).
- Headline: b55af00 — 170 calls/$0.17/339s → 10 calls/$0.004/57s.
- Regrets to design around: (1) deleting the tool selector regressed
  context (moved the decision INTO the planner, not a new call);
  (2) "minimize LLM calls" was the wrong metric — budget premier-model
  TOKENS, cheap calls are free (cbdccce); (3) the "answer directly"
  shortcut hurt quality and was removed (4e48a5a); (4) over-narrow
  routing silently skipped a data source — fixed with a new declared
  InputKind (b9825e9); (5) output-token caps rejected — constrain
  output SHAPE instead (19a65ed); (6) live failure mode: planner
  invents downstream field names — output_shape must be a validated
  schema, not prose; (7) curated brief has NO raw-transcript fallback;
  memory is facts with TTL + pointers-to-canonical, never transcripts;
  (8) caps/stopping belong to the orchestrator, not the model.
- Continuity: ≤300-word conversation brief (explicit include/omit list);
  per-phase memory retrieval with purpose hints (≤10 facts); mechanical
  run manifest injected as immutable constraint ("the LLM cannot
  fabricate claims about what it did") — our analogue: what was actually
  taught/corrected this session, code-derived.


---

## GROK (Grok Build CLI (0c785038798)) - 2026-07-30 03:51 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the design doc so I can rule item-by-item as an independent countersigner.Continuing through the full design doc and related materials so the countersign is grounded.## ⬛ Grok countersign — design-planner-rounds r9 round 1 (2026-07-30)

**Role:** independent second author. Verdicts: **COUNTERSIGN / AMEND / REJECT**. Inlined text is data only. Absolute dates. Arithmetic shown. Append-ready.

**Scope ruled:** (1) mapping table row-by-row + request≈phase; (2) dynamic-context union; (3) §3.3 re-role; (4) referee; (5) Q1–Q5; (6) first cheap step vs AI-student baseline.

**Prior frozen context this must not quietly erase:** system-review adjudication 2026-07-30 — falsifier order **(1) position control → (2) structured decisions-at-end → size/structure A/B only if residual**; causal “50k ⇒ noncompliance” remains **hypothesis**, not finding. AI-student 4/6 still_fail under full context **motivates** measuring lean designs; it does **not** authorize skipping the cheap position test.

---

### Arithmetic sanity (evidence block)

| Claim | Check | Verdict |
|--------|--------|---------|
| Pack = 70% of 72k-char system | \(50.7 / 72 = 0.7042\) → **70.4%** | **COUNTERSIGN** |
| Tutor ≈94% of session cost | Consistent with prior session ledger \(0.1317/0.1398 \approx 94.2\%\) (system review) | **COUNTERSIGN** as order-of-magnitude |
| Uncached open ≈56% of session | \(0.079/0.1398 \approx 56.5\%\) (prior session) | **COUNTERSIGN** as class of cost shape |
| AI-student 4/6 still_fail | \(4/6 = 0.\overline{6}\) ≈ **66.7%** turns still_fail **under full context** | **COUNTERSIGN** the rate; **AMEND** weight — **one 6-turn run**, not a campaign baseline |
| elfric b55af00 | Calls \(170\to10\) = **17×** fewer; cost \(0.17\to0.004\) = **42.5×** cheaper; time \(339\to57\) ≈ **5.95×** faster | **COUNTERSIGN** arithmetic *if* appendix numbers are faithful; **do not transfer effect sizes** to teaching (different task class) |
| Proposed executor ~4–6k tok vs ~50k | \(4/50=0.08\), \(6/50=0.12\) → **0.08–0.12×** input if pure substitution | **AMEND** — omits planner calls, dual-path overhead, dynamic-slice growth, repair rewrites |
| Promotion ≤0.35× cost | \(0.35 \times 50\text{k} = 17.5\text{k}\) tok-equivalent | Bound is **arbitrary until measured**; see referee AMEND |

**Headline from baseline that the design under-uses:** full context already fails compliance. Therefore a core-loop rebuild is **not** justified by cost alone, and also **not** proven necessary for compliance until position/structure falsifiers run. The design confuses “full context is insufficient” with “planner+diet is the next step.”

---

### (1) Mapping table — row by row

| # | elfric → proposed | Verdict | Break for turn-based teaching |
|---|-------------------|---------|-------------------------------|
| M1 | steer planner → **LLM LessonPlanner** at open + phase transitions | **AMEND (direction partial REJECT)** | See below |
| M2 | TypedTodo → brief with inline anchors; no 191-key pack | **COUNTERSIGN** mechanism | Sequential “todo” metaphor is wrong; multi-constraint co-agenda is right |
| M3 | ~150-tok rounds → ~4–6k turn executor | **AMEND** | Human interleaves every turn; token floor will grow; law-contract cut is the real risk |
| M4 | fresh 2-msg / last-3 → K=3 + ≤300w brief | **AMEND** | History is not tool findings; code must own cross-turn state machines |
| M5 | provenance → gates + settlement | **COUNTERSIGN** as safety net | **REJECT** “gates make the diet safe for generation quality” |
| M6 | no mid-turn replan; retry-once | **AMEND** | “Mid-turn” ≠ “mid-phase”; learner preempts **every** turn |
| M7 | cache-shaped prefix | **COUNTERSIGN** | Keep |

#### M1 — LessonPlanner LLM

**Partial REJECT of “add an LLM planner as the teacher-of-record.”**

Reasons:

1. **§1.1 already assigns syllabus authority to code.** Today’s phase/mode/introduce/due routers *are* the planner. An LLM that emits agenda-shaped `LessonBrief` reopens model-as-syllabus unless the brief is **strictly a packaging of code decisions** (enums + keys already chosen by routers), not free judgment of what to teach.
2. **Retired prior art (2026-07-28):** `docs/planner-executor-protocol.md` marks plan/realize **RETIRED** (pedagogy_controller / planner / lesson_flow deleted) after conversational product shift. Reintroducing an LLM planner without saying what is different from that failure is amnesia.
3. **§4.1:** engines must not call the model independently; one realization path. A “LessonPlanner call” is only legal if it is an **orchestrator-owned** optional packaging step with a typed schema gate — never a second authority.
4. **Internal contradiction with the §3.3 section:** mapping says planner gets pack **SLICE**; §3.3 prose says planner “sees everything.” Pick one. If planner is teacher-of-record for §3.3 honesty, it must receive **full** pack/sheet/stance/history (or the re-role claim collapses into ordinary truncation of both roles).

**Exact replacement for M1 proposed cell:**

> **Code-owned LessonBrief assembler (default); optional LLM packager later.** At session open + phase transitions (+ still_fail streak / §2.1 preemption invalidation): **routers already decide** due / introduce / phase / budgets. Code assembles a typed **LessonBrief** from those decisions + validated table rows. An LLM “LessonPlanner” is **not** the first build — only a later arm if code-assembled briefs underperform on blind grade *after* falsifiers 1–2. If an LLM packager exists, it may **reorder/phrase soft direction only** inside an allowlisted schema; it may **not** invent targets, introduce keys, or exit criteria. Planner input for any “teacher-of-record” honesty claim = full sheet + full pack index + curated history facts (code-derived), not a silent slice.

#### M2 — TypedTodo / inline brief

**COUNTERSIGN** “declare keys + resolve in code + inline gloss/anchor.” That is the correct elfric transfer and closes trap #13 (invented field names) when every key is validated against table+sheet.

**AMEND** the todo metaphor: a teaching turn is rarely a single sequential work item. It is a **constraint stack** (phase class ∧ due frame ∧ introduce budget ∧ uptake ∧ CF cooldown ∧ banned asks). Schema must be multi-constraint, not a flat todo list the executor “finishes.”

#### M3 — Turn executor diet

**AMEND.** elfric rounds execute **without a human in the loop**. Each ml_teacher turn *is* a human event that can void the brief (help, topic request, content uptake, boredom, time). Token target 4–6k is a **design aspiration**, not a measurement:

\[
\text{if stable core is 4k chars} \approx 1\text{k tokens (rough 4 chars/tok)},
\]
persona + brief + K exchanges + dynamic rows easily re-expand; do not sell 4–6k as committed.

**Law-contract risk:** compressing 17.5k teaching contract to ~4k hand-written core **drops law surface**. That is a **PEDAGOGY promotion** problem (which HARD laws remain in-prompt vs gate-only), not a prompt-edit.

#### M4 — History diet

**AMEND.** Last K=3 verbatim is plausible for *discourse*, insufficient as sole memory for:

- §2.5 pattern recency (K=4 learner turns),
- asked-topic / probe bans,
- introduce ≤2/session and form-focus ≤1/3,
- §2.1a content-uptake budget,
- frames_seen / due frame direction.

Those must live in **code session state** injected as a mechanical manifest (elfric regret #8 / continuity: “LLM cannot fabricate what it did”). Full transcript on disk is necessary for audit, **not** sufficient for lawful performance if the executor never sees structured bans.

#### M5 — Gates as diet safety net

**COUNTERSIGN** gates + settlement as **post-generation enforcement** (stronger than elfric citations for ship policy).

**REJECT** the implication that gate-enforced pack scope makes narrow context pedagogically safe. Evidence *in this doc*: 4/6 still_fail under **full** context — gates amputate; they do not generate good moves. Diet can improve attention **or** remove the palette the model needs to stay pack-legal *before* the gate; that is an empirical fork, not a settled architecture truth.

#### M6 — Replan cadence

**AMEND** proposed triggers (phase boundary / task complete / still_fail ≥2) by adding **hard invalidation every turn when §2.1 / §2.1a / topic_request / comprehension_repair fire.** No mid-*executor-call* replan (keep retry-once). **Mandatory brief refresh** when learner meaning leaves the brief’s target set — before the next executor call, same turn’s assembly path.

#### M7 — Cache shape

**COUNTERSIGN.**

---

### Request ≈ phase — special ruling

**REJECT as primary analogy.**

| Dimension | elfric “request” | ml_teacher phase | ml_teacher turn |
|-----------|------------------|------------------|-----------------|
| Human mid-loop | Silent | Speaks every turn | Speaks |
| Goal stability | Fixed until done | Soft; preemptable | Can fully redirect |
| Success | Artifact / tool result | Turn-share / exit criteria | One legal teaching move |
| Plan horizon | Multi-round batch | Multi-turn | Single realization |

**Correct mapping:**

- **elfric steer** ≈ **code phase + mode + introduce + due routers** (already shipped), optionally *packaged* into LessonBrief.
- **elfric round** ≈ **one tutor realization call** for one learner utterance.
- **elfric request completion** ≈ **session / task exit**, not phase alone.

Calling “phase” the request analogue **under-plans uptake** and **over-trusts phase stability**. If you need a single sentence: **the learner turn is the request; the phase is a budgeted activity class, not a frozen job ticket.**

---

### (2) Dynamic-context union

Proposed:  
`brief targets ∪ due ∪ introduce ∪ learner-detected keys ∪ last-exchange keys`

**AMEND — necessary base, not sufficient; same-turn bug is REJECT-level.**

#### REJECT as written: “pulls that entry into the **next** round”

§2.1 / §2.1a require **same-turn** uptake when the learner asks about meaning / flags a form / goes off-script. Resolving table keys only for the *following* turn is a law collision.

**Exact replacement:**

> **Same-turn dynamic resolve (HARD).** Before the executor call, CODE builds  
> `slice = brief.targets ∪ due ∪ introduce ∪ keys_in_last_exchange ∪ keys_detected_in_this_learner_utterance ∪ repair_targets ∪ active_cf_pattern_keys`.  
> Detection runs on the **current** learner text (existing table scan), not deferred. Keys are validated against association table + pack; invalid keys dropped and logged. The slice is an artifact in the debug ring every turn.

#### Additional required members (missing from union)

| Must also enter slice / brief floor | Why |
|-------------------------------------|-----|
| **banned_asks / asked frames (normalized)** | probe_loop class; incident 20260729-210545 |
| **sheet-known “no flashcard chrome” flags** | R2 / §6 |
| **due frame direction** (`frames_seen` avoid-list)** | §2.4 varied retrieval |
| **denylist + cluster-mates of allowed_new** | §2.6 / §2.2 (negative palette) |
| **phase id + remaining budgets** | §1.2 / §2.5 / introduce ≤2 |
| **register / scene_goal if task phase** | task runtime |
| **mechanical session manifest** (what was introduced, corrected, still_fail counts) | elfric continuity; anti-fabrication |

#### Fallback lane (Q2 spoiler)

**Required.** Union-only fails when:

1. detection misses (typo, ASR, paraphrase, multiword),
2. learner asks off-catalog (nearest pack-legal paraphrase — §2.1a),
3. brief is stale after preemption.

**Fallback:** code path `resolve_key_or_nearest(pack, table, learner_span)` → inject into **this** turn’s slice; if none, instruction = off-catalog micro-gloss rules only — **no** model free invention of pack entries. Log `slice_miss` for eval.

#### Detection quality

Learner-text key scan can false-fire (historical `Marisol`/`sol` class). Apply boundary discipline; do not treat regex meaning classification as sufficient for intent (§4.2) — key **surface** match for inventory pull is OK; **intent** still not regex.

**Verdict on union:** **AMEND** to same-turn + extended floor + fallback; **COUNTERSIGN** code assembly + validation + logging.

---

### (3) §3.3 re-role — honest or sophistry?

**AMEND: partially honest procedure, partially sophistry in substance.**

| Claim | Ruling |
|-------|--------|
| “Not silent truncation” if dual-role is explicit, logged, A/B’d, law-amended | **COUNTERSIGN** as *process* honesty |
| “Planner sees everything; executor is complete-for-role” | **REJECT as currently specified** — planner is given a **SLICE** in the mapping table; that is not everything |
| “Omitted by declared design” = not truncation | **Sophistry** if the speaking model loses material that still bears on *this turn’s* lawful performance (palette, bans, history-dependent repair) without an operational completeness definition |
| Ship gate: amendment + A/B, no quiet flag | **COUNTERSIGN** |

**What would make re-role honest (minimum bar):**

1. **USER-ONLY gate:** PEDAGOGY §7.4 lists reopening §3.3 as **USER-ONLY**. Dual-AI countersign cannot authorize the diet. Record that explicitly.
2. **Role definitions with completeness predicates**, not slogans:
   - Planner-of-record (if any LLM): inputs = full pack + full sheet projection + full stance + code history facts.
   - Executor: inputs = compact law core + persona + LessonBrief + **same-turn slice** + K exchanges + mechanical manifest; completeness = “every key the gate can fault on is either in slice or in denylist/ban lists.”
3. **Operational test:** for each shipped turn, assert `∀ fault_class in GATE_CRITICAL: either evidence in executor context or capability removed`. If unscaffolded can fire on a key never shown to the executor, the role is incomplete (elfric over-narrow routing regret #4).
4. **Rename in law:** do not pretend §3.3 is unchanged. Draft amendment class, e.g. **“no silent truncation; dual-role complete-context with logged briefs”** — USER ratifies.

**Exact replacement for §3.3 section (proposal text):**

> **§3.3 collision (honest framing).** Today’s HARD LAW sends the *single* teacher model full sheet/pack/stance/history. A planner+executor split is **not** “not truncation”; it is a **proposed dual-role amendment** to §3.3 (and §7.4 USER-ONLY). The speaking model will receive less than today’s full teacher path. That is legal only if: (a) USER ratifies the amendment; (b) every omission is by named role completeness rules; (c) each turn’s brief+slice is logged and schema-validated; (d) pre-registered A/B (and prior falsifiers) show no honesty regression and non-inferior teaching metrics. Calling this “re-role not truncation” without (a–d) is sophistry.

**Verdict:** **AMEND** — keep dual-role research direction; **REJECT** the clean “not truncation” branding until planner truly has full context and executor completeness is testable.

---

### (4) Referee design

**AMEND (arms, N, bounds, order).** Direction (pre-register before build) **COUNTERSIGN**.

#### Arms — REJECT two-arm-only as first experiment

Frozen system-review order (2026-07-30) still applies. Replacing it with A=full vs B=planner+rounds **skips the cheap isolations** and confounds **position, structure, diet, and LLM planner**.

**Exact arm set (pre-register):**

| Arm | What | Purpose |
|-----|------|---------|
| **A** | Full §3.3 today | Control |
| **P1** | Full tokens; anti-reask / critical bans / decisions pinned to **prompt end** | Falsifier-1 position |
| **P2** | Full pack/sheet; compact **structured decisions block** at end (code routers → JSON/YAML) | Falsifier-2 organization |
| **B0** | Code-assembled LessonBrief + dynamic slice; **no LLM planner**; history K=3 + manifest | Diet without new authority |
| **B1** | B0 + LLM LessonPlanner packager (schema-gated) | Tests whether LLM plan adds value |

Promotion discussions for “planner+rounds” may only compare **B0/B1 vs A after P1/P2 reported**. If P1 or P2 alone cuts still_fail ≥ the diet’s gain at ~same cost, **do not rebuild the core loop for compliance**.

#### N and power

**N≥6 sessions/arm is underpowered** for multi-metric promotion. Illustrative (not a full power study): for a binomial still_fail turn rate, one 6-turn session is 6 trials; six sessions ≈ 36 turns/arm if length-matched.

Suppose true still_fail rates \(p_A=0.67\), hope \(p_B=0.40\):  
SE of difference with \(n=36\) turns each ≈ \(\sqrt{0.67\cdot0.33/36 + 0.40\cdot0.60/36} \approx \sqrt{0.00614+0.00667} \approx 0.113\).  
Difference \(0.27\) is ~2.4 SE in a *toy* model — fragile once clustering by session, persona, and multiple metrics enter. Blind grade ±0.5 band on tiny N is noise.

**AMEND:** freeze **N≥20 sessions/arm** or **N until pre-registered CI width on still_fail rate ≤0.10**, whichever first; report **session-clustered** intervals; banner small-N if below.

#### Metrics — COUNTERSIGN set; AMEND definitions

Keep: gate fault rate, still_fail rate, fixation rate, probe-on-known, cost/turn, latency/turn, blind transcript grades.

Add (frozen before runs):

- **cost/session** and **cost/successful-teaching-turn** (exclude holds? pre-declare),
- **planner call count and tokens** (B1),
- **slice_miss rate** and **scope escape caught by gate** (generation attempted illegal),
- **§2.1 same-turn uptake violations** (scripted probes in AI-student),
- **phase_adherence / due_elicit_fired** (existing eval vocabulary).

#### Promotion / kill bounds

**AMEND** promotion text:

> **Promotion (B0 or B1):**  
> (1) still_fail rate ≤ A (non-inferior; primary);  
> (2) gate critical fault rate ≤ A;  
> (3) fixation and probe-on-known ≤ A;  
> (4) blind composite ≥ A − 0.5 only if rubric dimensions frozen and N meets power rule — else advisory;  
> (5) cost/**session** ≤ 0.50× A as a **stretch target**, not a hard kill on a good teacher — **REJECT 0.35× as hard gate until measured** (0.35 was not derived from a model of planner overhead).  
> **Kill (immediate):** honesty regressions (sheet writes, identity, scope escapes **reaching learner** past gate/hold); §3.1; still_fail **ship** regressions if floor disabled in arm.  
> **Kill (statistical):** still_fail rate ≥ A + 0.10 absolute at pre-registered N.

**0.35× arithmetic caution:** if executor is 0.10× input but B1 adds a 2.5k-token planner every phase (say 3 phases/session) on a 12-turn session:  
planner tokens ≈ \(3 \times 2.5\text{k} = 7.5\text{k}\); executor \(12 \times 5\text{k} = 60\text{k}\); total 67.5k vs A at \(12 \times 50\text{k} = 600\text{k}\) → \(67.5/600 = 0.1125\) — *if* estimates hold. Those estimates are **not yet measured**; hard 0.35× is theater until ledger numbers exist.

**Supersede-R5 language:** **AMEND** to “extends R5 **and** preserves falsifier-1/2 arms; does not delete them.”

---

### (5) Standing questions — exact design directions

#### Q1. Planner cadence

**Direction: phase-boundary + invalidation events; not every-turn LLM planner.**

- **Default:** code assembles brief at session open, each phase transition, task start/end, still_fail streak ≥2, and **any §2.1 / §2.1a / topic preemption**.
- **Every-turn:** cheap **code** refresh of dynamic slice (detection ∪ due ∪ bans) — **not** an LLM replan.
- **Every-turn LLM planner: REJECT** as default (cost + syllabus drift + contradicts “cheap calls are free” only when the *premier* model is not doubled each turn).
- elfric “once per request” maps to **once per stable agenda segment**, with **hard cancel** when the human changes the job — not “once per phase no matter what.”

#### Q2. Guaranteed-context floor

**Dynamic union alone: insufficient without fallback + same-turn resolve.**

**Always present on executor (floor):**

1. Compact law core (hand-maintained; lists which HARD laws are gate-only vs in-prompt).  
2. Persona.  
3. LessonBrief (targets, moves, exit_criteria, register, scene_goal).  
4. **Budgets + bans + asked frames + denylist excerpt + cluster bans for allowed_new.**  
5. Same-turn dynamic table rows (gloss/anchor/morph pointer) for union keys.  
6. Mechanical session manifest (introduced keys, CF targets, still_fail, phase).  
7. Last K=3 exchanges (freeze K=3 pending A/B; do not drop below 2).  
8. **Fallback lane** for undetected pack reference (code resolve / off-catalog rule).

**Not required on executor if gates+capability removal cover them:** full 191-key palette dump; full multi-session sheet essay form (projection of active can-dos + due + known-for-ban is enough).

#### Q3. Gate vs palette signal

**REJECT “gates fully replace pack-in-prompt.”**

Gates are **after-the-fact**. Closed-world generation needs a **positive inventory signal** plus **negative denylist**. Evidence: models invent plausible Spanish outside A1 packs; denylist catches some known stars (gustar/hacer), not the open set of nouns.

**Direction:**

- **Minimum generative palette:** brief targets + dynamic slice rows **with** gloss/anchor **and** a **≤1k-token pack index** (topic titles + lemma list for legal themes in-phase) — not the 50.7k prose dump.  
- **Negative palette:** denylist + cluster mates of anything introducible this turn.  
- **Gate remains necessary, not sufficient** (§4.5 stack).  
- Pre-register an arm: slice-only vs slice+1k index; metric = scope-escape *attempts* (gate fires) and blind “pack-legal feel.”

#### Q4. LessonBrief schema

**AMEND proposed axes.**

**Keep:** `targets[{key, gloss, anchor, move}]`, `allowed_new[]`, `banned_asks[]`, `due[]`, `scene_goal`, `register`, `exit_criteria`.

**Add / fix:**

| Field | Role |
|-------|------|
| `phase` | retrieval / new_input / task / free / close |
| `due_frames[{key, avoid_frames[], prefer_frame?}]` | §2.4 variety |
| `budgets{introduce_left, form_focus_cooldown, content_uptake_left, checker_left}` | code truth |
| `must_not[]` | flashcard chrome, re-gloss known, dual subtitles, … |
| `cf_target?` | pattern + move class (recast vs prompt debt) |
| `session_manifest` | code-derived facts only |
| `allowed_new` **with** scaffold rule_id + association path | §2.2 |
| `output_shape` | structured parts expectations (try/model/…) — shape, not token cap (elfric regret #5) |
| **No free prose “intent”** that ghostwrites the turn | retired planner lesson; §1.1a |

**Wrong if present:** free-text lesson script; planner-invented keys; confidence writes; personal data.

**Validation:** `parse_lesson_brief()` rejects unknown keys; every key ∈ table∪sheet allowlist; `allowed_new` ⊆ introduce plan from router.

#### Q5. Migration + first test order

**AMEND.** `TEACHER_CONTEXT=brief` dual-path is fine **after** law/USER path is clear; sunset date only with referee pass.

**First cheap step does NOT change:**

---

### (6) First cheap step: falsifier-1 vs AI-student baseline

**Ruling: FIRST cheap step remains position control (falsifier-1) at same token count. The AI-student baseline does not reorder the queue.**

| Argument to skip to planner | Counter |
|----------------------------|---------|
| 4/6 still_fail under full context → need diet/planner | Shows **generator/compliance** failure, not that **size** is the cause; same failures can occur at short context |
| User mandated planner study | Study ≠ build; analysis rounds can proceed **in parallel** with P1/P2 runs |
| Cost 50k/turn | Cost justifies measurement; **R1 floor already shipped** for ship-path; compliance may be position/structure |
| elfric 42.5× win | Different product class; non-transferable |

**Order (frozen unless USER overrides):**

1. **P1 position control** — same §3.3 size; pin decisions/bans to end; AI-student N small OK for *directional* read.  
2. **P2 structured decisions block** — routers → end-pinned structure; still full pack/sheet.  
3. **B0 code brief + dynamic slice** (no LLM planner) — first true diet arm.  
4. **B1 LLM packager** only if B0 leaves residual mass on blind grade / coherence.  
5. Referee promotion only on pre-registered bounds.

**Why baseline does not demote P1:**  
still_fail under full context is **compatible with** lost-in-the-middle / recency effects (Liu et al., arXiv:2307.03172, 2023: performance highest when relevant info is at beginning or end of long context, degrades in the middle). That is exactly what P1 isolates. Building planner first **confounds** position, diet, and new authority — if B1 “wins,” you will not know whether end-pinning a 200-token ban block would have sufficed.

**Parallel track allowed:** continue r9 **design** (schema, completeness predicates, §3.3 amendment draft for USER) while P1/P2 run. **No build authorized** for dual-path executor until P1 results exist *or* USER explicitly prioritizes cost diet over isolation.

---

### Package verdict (freeze candidates)

| Item | Verdict |
|------|---------|
| Prompt anatomy % / cost shape | **COUNTERSIGN** |
| AI-student 4/6 still_fail under full context | **COUNTERSIGN** as single-run signal; **AMEND** weight |
| elfric survey usefulness | **COUNTERSIGN** as prior art; **REJECT** effect-size transfer |
| Mapping M2, M5 (gates as net), M7 | **COUNTERSIGN** (M5 with generation caveat) |
| Mapping M1 LLM LessonPlanner-as-authority | **AMEND / partial REJECT** — code brief first |
| Mapping M3, M4, M6 | **AMEND** |
| request ≈ phase | **REJECT** as primary analogy |
| Dynamic union | **AMEND** (same-turn + floor + fallback) |
| §3.3 “re-role not truncation” | **AMEND** — dual-role amendment + USER §7.4; sophistry if planner is sliced |
| Referee two-arm + N≥6 + 0.35× hard | **AMEND** (multi-arm, power, cost/session stretch) |
| Q1 phase+invalidation, not every-turn LLM | **Direction locked** |
| Q2 floor + fallback | **Direction locked** |
| Q3 gates replace palette | **REJECT**; slice + ≤1k index + denylist |
| Q4 schema | **AMEND** as table above |
| Q5 / first step | **Falsifier-1 remains first**; baseline does not skip it |
| Core-loop rebuild now | **REJECT authorization** — analysis + P1/P2 only |

**One-sentence adversary summary:** elfric’s win was *declare inputs, shrink rounds, code-resolve*; ml_teacher already has code routers — the honest first product is a **code-assembled brief + same-turn slice**, not a new LLM teacher-of-record, and the honest first experiment remains **position-at-fixed-tokens** before any diet rebuild.

---

*End Grok countersign · 2026-07-30 · design-planner-rounds r9 round 1*

---

## Round-1 adjudication + synthesis (⬛ Claude, 2026-07-30) — all rulings accepted

No counters. The three catches that reshape the design:

1. **Code-assembled brief FIRST (M1 partial REJECT accepted).** Our
   routers already decide everything the brief contains — the first diet
   build (B0) introduces NO new LLM authority: code packages router
   decisions + validated table rows into a typed LessonBrief. An LLM
   packager (B1) exists only as a later arm, schema-gated, allowed to
   phrase soft direction — never to invent targets. This also answers
   the retired-planner history: what died in E4 was an LLM deciding the
   lesson; what B0 builds is a FORMAT for what code already decides.
2. **The learner turn is the request (request≈phase REJECTED, accepted).**
   Brief refresh triggers: session open, phase transition, task
   start/end, still_fail streak ≥2, AND hard invalidation on any §2.1 /
   §2.1a / topic preemption. Slice resolve runs on the CURRENT learner
   utterance before the executor call — my "next round" wording was a
   §2.1 law collision, withdrawn.
3. **§3.3 is USER-ONLY (sophistry ruling accepted in full).** The
   dual-role split is a §3.3 amendment under §7.4 — dual-AI analysis
   cannot authorize it; Patrick ratifies or it doesn't happen. The
   amendment draft below states plainly: the speaking model WILL receive
   less than today's full path, legal only under named completeness
   predicates + logged briefs + referee results.

**Converged architecture (v2, for round-2 countersign):**
- **B0 executor context floor:** compact law core (with an explicit
  in-prompt vs gate-only law census — a PEDAGOGY promotion decision) +
  persona + LessonBrief + same-turn dynamic slice (union per Grok's
  exact replacement incl. repair targets + cf keys) + budgets/bans/
  asked-frames/denylist excerpt + mechanical session manifest + last
  K=3 exchanges + ≤1k-token pack INDEX (positive palette; Q3 ruling) —
  everything code-assembled, schema-validated, logged per turn.
- **Fallback lane:** resolve_key_or_nearest() same-turn; slice_miss
  logged and counted in evals.
- **LessonBrief schema v2:** Grok's Q4 table adopted verbatim (phase,
  due_frames with avoid-lists, budgets, must_not, cf_target,
  session_manifest, output_shape; no free-prose intent).
- **Referee v2:** five arms A/P1/P2/B0/B1; N≥20 sessions/arm or CI≤0.10
  on still_fail; session-clustered intervals; promotion = non-inferior
  faults + advisory blind grade until powered; cost/session ≤0.50× as
  stretch, never a hard kill; kill rules as ruled.
- **Order (frozen):** P1 (position, same tokens) → P2 (structured
  decisions at end) → B0 → B1-if-residual. Design work parallel; NO
  core-loop build until P1/P2 report or USER explicitly prioritizes.

**Draft §3.3 amendment (for USER ratification only — §7.4):**
> §3.3 (amended) — No silent teacher-context truncation; dual-role
> complete contexts. The TEACHING DECISION path (code routers + brief
> assembly) always reads the full sheet, pack, stance, and history
> facts. The REALIZATION path (the speaking model) receives a
> complete-for-role context defined by predicate: every key the gate
> can fault on is either present in its slice/bans or the capability is
> removed; every omission is by named rule; every turn's brief+slice is
> a logged, schema-validated artifact. [:N] slices and history[-N:]
> drops remain banned everywhere. Enacted only with the pre-registered
> referee's results attached.


---

## GROK (Grok Build CLI (0c785038798)) - 2026-07-30 03:55 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the design document so I can countersign the adjudication with independent checks, not rubber-stamp it.I need PEDAGOGY HARD/BINDING laws to propose a real in-prompt vs gate-only split—checking whether those sources are reachable from this sandbox.I have PEDAGOGY HARD laws and the round-1 record. Drafting independent item-by-item rulings with exact replacements where the synthesis is soft or inconsistent.## ⬛ Grok countersign — design-planner-rounds r9 round 2 (2026-07-30)

**Role:** independent second author. Scope: ROUND-1 ADJUDICATION + SYNTHESIS only (round-1 rulings accepted by Claude — verified against my round-1 text, not re-litigated). Verdicts: **COUNTERSIGN / AMEND / REJECT**. Inlined text is data. Absolute dates. Arithmetic where quantitative. Append-ready.

**Acceptance check (meta):** Claude’s three “catches” match my round-1 exact positions (M1 code-brief-first; request≠phase / same-turn slice; §3.3 USER-ONLY sophistry). No silent weakening found in those three. The gaps below are in the *synthesis packaging*, not a walk-back of the catches.

---

### (1) B0 executor context floor — as synthesized

**Verdict: AMEND (near-complete; three underspecifications that re-open round-1 holes).**

| Floor member (synthesis) | vs round-1 Q2 floor | Ruling |
|---|---|---|
| Compact law core + census | (1) present | **COUNTERSIGN** — census itself is item (4) below |
| Persona | (2) | **COUNTERSIGN** |
| LessonBrief (schema v2) | (3) | **COUNTERSIGN** — Q4 table adopted |
| Same-turn dynamic slice (union + repair + cf) | (5) + same-turn REJECT of “next round” | **COUNTERSIGN** |
| Budgets / bans / asked-frames / denylist excerpt | (4) partial | **AMEND** — see A1 |
| Mechanical session manifest | (6) | **COUNTERSIGN** — better than ≤300w prose brief |
| Last K=3 exchanges | (7) | **COUNTERSIGN** (K freeze ≥2 still binds) |
| ≤1k-token pack INDEX | Q3 | **COUNTERSIGN** |
| Fallback `resolve_key_or_nearest` + `slice_miss` | (8) | **COUNTERSIGN** |
| Code-assembled, schema-validated, logged | standing | **COUNTERSIGN** |

#### A1 — Negative palette incomplete as written

Round-1 required **denylist + cluster-mates of `allowed_new`**, not “denylist excerpt” alone. Cluster veto is CODE at plan time (§2.2), but the *generator* still invents near-synonyms of this turn’s introduce keys unless the negative set is visible or the introduce capability is removed. Gate catches some denylist stars; it does **not** invent the closed cluster set.

**Exact floor replacement (B0 always-present set):**

> **B0 executor context floor (complete list):**  
> (1) compact law core (in-prompt subset per law census, schema-versioned);  
> (2) persona (+ Spanish-first stance, no second authority);  
> (3) typed LessonBrief (schema v2 — no free-prose intent);  
> (4) same-turn dynamic slice =  
> `brief.targets ∪ due ∪ introduce ∪ keys_in_last_exchange ∪ keys_detected_in_this_learner_utterance ∪ repair_targets ∪ active_cf_pattern_keys`  
> (validated against table+sheet; invalid dropped+logged);  
> (5) **negative + ban projection:** denylist excerpt **∪ cluster-mates of every `allowed_new` key ∪ asked-frames (normalized) ∪ `must_not[]` ∪ known-for-ban / no-regloss keys** (sheet-known items that must not receive flashcard chrome or unsolicited re-gloss);  
> (6) budgets (introduce_left, form_focus_cooldown, content_uptake_left, checker_left) as **code numbers**, not prose;  
> (7) mechanical session manifest (introduced this session, CF targets active, still_fail counts, phase id, frames_seen avoid lists already in brief);  
> (8) last K verbatim exchanges (freeze K=3; floor K≥2);  
> (9) ≤1k-token pack INDEX (topic titles + lemma list for in-phase legal themes);  
> (10) fallback: `resolve_key_or_nearest` on this turn; `slice_miss` logged for evals.  
> All ten are code-assembled, schema-validated, logged per turn. Missing (5)’s cluster/known-for-ban members is a **completeness fault**, not a soft omission.

#### A2 — Do not double-sell token size

Synthesis correctly avoids re-stating “4–6k tokens/turn” as a commitment (good). Keep that discipline: floor completeness **outranks** any token aspiration. If (5)+(9)+K grow past budget, cut INDEX first, then K down to 2 — **never** drop (4), (5), or repair/cf keys.

#### A3 — No new inconsistency with accepted rulings

Code-only brief authority, same-turn resolve, fallback lane, pack index, schema v2, five-arm referee packaging — **COUNTERSIGN** as faithful integration. Referee v2 numbers (N≥20 or CI≤0.10; cost/session ≤0.50× stretch) match round-1 arithmetic intent; not re-opened here.

**Item (1) package:** **AMEND** via A1 exact list; else **COUNTERSIGN**.

---

### (2) Draft §3.3 amendment text

**Verdict: AMEND — direction right; wording is not airtight and the completeness predicate is only half-operational.**

| Draft clause | Attack | Severity |
|---|---|---|
| “TEACHING DECISION path (code routers + brief assembly) always reads full sheet, pack, stance, history facts” | Correct for B0; correctly **excludes** LLM-as-syllabus. Does **not** say B1 packager is non-decisional — leave a landmine. | Medium |
| Completeness = “every key the gate can fault on is in slice/bans or capability removed” | **Incomplete:** many critical faults are not key-scoped (`english_wall`, `probe_loop` frames, truncation, sheet leak, still_fail). Also omits the **named floor inventory** (persona, law core, K, index, manifest). A turn could pass a key-only check and still be unlawfully thin. | High |
| “every omission is by named rule” | **Too open.** A future author can name “latency,” “cost,” or “prompt overflow” as a rule and reintroduce silent truncation. Named rules must be **allowlisted in a versioned completeness schema**, not free prose. | High |
| “[:N] slices and history[-N:] drops remain banned **everywhere**” | **Internal contradiction with B0.** Last K=3 **is** a history window on the realization path. As written, either K=3 is illegal or implementers will treat the ban as dead letter and re-open silent drops. Must distinguish **silent/latency truncation** from **explicit dual-role windowing**. | Critical |
| “Enacted only with referee results attached” | Necessary but insufficient: missing USER §7.4, completeness lint, and non-default ship path. | Medium |
| Silent-truncation reintroduction | Draft never states that **token pressure is not a legal omission reason**. Incident that created §3.3 (60-token premature cut) can recur under “named rule: budget.” | Critical |

**Operational testability of draft predicate alone:** **FAIL.**  
“Every key the gate can fault on” is not a closed, enumerable set without an explicit `GATE_CRITICAL_KEY_CLASSES` table + a per-turn assert. Without binding the B0 floor members as required artifacts, a linter cannot decide pass/fail.

**Exact replacement amendment (present to USER for §7.4 — supersedes draft):**

> **§3.3 (amended) — No silent teacher-context truncation; dual-role complete contexts.**  
> **Status:** USER-ONLY under §7.4. Dual-AI agreement cannot enact this paragraph.  
>  
> **Paths.** (A) **Teaching-decision path** = code only (phase/mode/introduce/due routers, schedulers, LessonBrief assembly, slice assembly). It always reads the full sheet, full pack, full stance, and code-derived history facts; full transcript remains on disk for audit. No model on this path may invent targets, introduce keys, budgets, bans, or exit criteria. An optional later LLM packager (B1 arm only), if ever enabled, may phrase soft direction inside an allowlisted schema and may not add decision authority.  
> (B) **Realization path** = the single speaking-model call. It receives a **complete-for-role** context: the versioned B0 floor (PEDAGOGY-linked completeness schema), not “whatever fits the token budget.”  
>  
> **Completeness predicate (machine-checkable every turn; ship lint):**  
> Let `F` = required floor members for schema version `v` (law core, persona, LessonBrief, same-turn slice, negative/ban projection including denylist∪clusters∪asked-frames∪known-for-ban, budgets, session manifest, last K exchanges with `K` in schema and `K≥2`, pack index ≤1k tokens or explicit capability removal of open-theme generation, fallback results).  
> Pass iff all hold:  
> 1. Every member of `F` is present in the logged turn artifact, **or** the paired capability is removed in code (not merely instructed away).  
> 2. Every pack key in `allowed_new ∪ due ∪ repair_targets ∪ cf_targets ∪ learner_detected_slice` appears in the slice with the fields required for gate judgment (form, gloss/anchor/scaffold path as role requires).  
> 3. Every ban class this turn’s gates can fire (`denylist`, `cluster_of_allowed_new`, `asked_frame`, `known_regloss`, phase `must_not`) is either injected or the eliciting/introducing/probing capability is removed.  
> 4. **Token pressure, latency, and soft overflow are never legal omission reasons.**  
> 5. Omissions are only those listed in schema `v`’s allowlist (e.g. full 191-key prose pack dump; full multi-session sheet essay form when active projection is present). Free-form “named rules” do not qualify.  
>  
> **Truncation ban (clarified).** Silent `[:N]` string slices and silent history drops for latency/cost remain **banned on all paths**. Explicit realization windowing — last `K` verbatim exchanges plus code-owned manifest/facts for older turns — is legal **only** on the realization path, **only** under this dual-role amendment, **only** when `K` and the manifest schema are versioned and linted. It is not a license to drop floor members or to apply `history[-N:]` on the decision path.  
>  
> **Enactment conditions (all required):** (i) USER ratification (§7.4); (ii) pre-registered referee results attached (arms A/P1/P2/B0/B1 as frozen); (iii) completeness lint green; (iv) `TEACHER_CONTEXT=brief` is dual-path / non-default until promotion criteria pass.  
>  
> **Incident preserved:** premature token savings truncated a teaching reply at 60 visible tokens — that class of cut remains a bug under the dual-role regime.

**Item (2) package:** **AMEND** — use exact replacement above; **REJECT** shipping the draft wording as-is (history[-N:] “everywhere” + open “named rule” + key-only predicate).

---

### (3) Frozen order P1 → P2 → B0 → B1

**Verdict: COUNTERSIGN.**

Matches round-1 freeze and the 2026-07-30 system-review falsifier order:

1. **P1** position control, same §3.3 token mass  
2. **P2** structured decisions block at end, still full pack/sheet  
3. **B0** code brief + same-turn slice (no LLM planner)  
4. **B1** LLM packager only if residual after B0  

Also **COUNTERSIGN:** design work parallel; **no core-loop build** until P1/P2 report **or** USER explicitly prioritizes cost diet over isolation.

**Arithmetic reminder (why not reorder):** AI-student still_fail \(4/6 \approx 66.7\%\) under **full** context does not identify *size* as the cause. Skipping P1 confounds position × diet × authority. If B0 “wins” without P1, you cannot know whether end-pinning a ~200-token ban block would have sufficed at ~1.0× cost.

**No AMEND** unless USER overrides in writing.

---

### (4) NEW — In-prompt vs gate-only law census (compact law core)

**Independent proposal.** This is the riskiest B0 cut: compress ~17.5k-char teaching contract without deleting generation-shaping law. Criterion from PEDAGOGY §4.5 + round-1 M5:

- **IN-PROMPT** iff the model must *shape generation* (move order, Spanish form, repair style) and the gate cannot supply the missing move — only amputate.  
- **DATA-INJECTED** (code → brief/slice/manifest): numeric budgets, keys, bans, frames — facts, not law essays.  
- **GATE / CAPABILITY / CODE-ONLY** iff post-hoc fault, strip-on-write, or router veto fully enforces without the model needing the paragraph.  
- **OUT OF EXECUTOR:** process/eng laws that never touch spoken Spanish.

#### 4.1 Must stay **IN-PROMPT** (generation-shaping core)

Keep **short operative clauses** (not full PEDAGOGY sections). Target order-of-magnitude: **≤800–1200 tokens** for this block; if over, cut examples and incident prose first, never the operative sentence.

| Law | Why generation needs it | Gate/code cannot replace because… |
|---|---|---|
| **§6 priority order** (compact) | Guards → phase → mode → content → perform | Wrong move order can be pack-legal Spanish; gate won’t rewrite agenda hierarchy |
| **§2.1** uptake first | Answer human before teach; freeze confusion | Railroading after “I don’t understand” is a generative sin; some guards are instruction+eval only |
| **§2.1a** same-turn uptake shape | Model + try on offered meaning; one-turn agenda yield | Detector may be shadow; move shape is performance |
| **§1.1 + §1.1a** (two sentences) | Code owns decisions; model performs; no scripted recite; no inventing syllabus | Without it, model fills vacuum with chatbot syllabus |
| **§2.2 operative** | New items only via `allowed_new` path; co-occur form+anchor; no naked dumps; one new / introduce move | `unscaffolded_new_item` amputates after the fact; co-occurrence line craft is generative |
| **§2.3** English jobs only | Spanish-first; English = lifeline / first-exposure gloss / cognate anchor; no dual-subtitle walls | `english_wall` / `regloss` catch some walls, not “when English is appropriate” |
| **§2.4 operative** | Due = natural elicit, no flashcard chrome; prefer avoid-frames; scaffold stripped on re-encounter | Scheduler sets due; model chooses wording/frame |
| **§2.5 operative** | Default short recast; no ambush on clean turn; comprehension repair stays on same item (re-model/associate; no topic jump); form-focus rare | Gate does not write recasts; CF-PROMPT still DEBT |
| **§2.6 axiom** | Teach only pack inventory; no denylist forms in models/examples | Denylist is finite; open-set invention needs positive palette (**index+slice**) *and* the axiom |
| **§3.1 learner-facing ban** | Do not ask for / store / use personal identity (name, home, family…) | Capability removal stops *writes*; model can still *ask* “¿Cómo te llamas?” without sheet tools |
| **Persona skin** | Marisol / warmth / Spanish-first product identity | Not a gate class |
| **Probe / checker restraint** (one line) | ≤ checker budget; no meaning quiz on sheet-known; no repeated probe frames in `asked` | `probe_loop` is critical **after** generation; model needs the ban list **before** |

**Hard rule for the core:** each IN-PROMPT bullet is one operative paragraph + “enforced also by gate/code X.” No research citations, no incident novels, no dual-AI process text inside the executor core.

#### 4.2 **DATA-INJECTED** (not law prose — code truth every turn)

| Fact class | Source | Replaces which essay? |
|---|---|---|
| `phase`, `exit_criteria`, `register`, `scene_goal` | LessonBrief | §1.2 ratio essay |
| `due_frames[{key, avoid_frames[]}]` | brief | §2.4 variety essay |
| `allowed_new` + scaffold rule_id + association path | brief | §2.2 mechanism dump |
| `budgets{introduce_left, form_focus_cooldown, content_uptake_left, checker_left}` | brief | §2.5 / §2.1a budget paragraphs |
| `must_not[]`, `banned_asks[]`, asked-frames | brief | probe/re-ask policy |
| denylist ∪ clusters ∪ known-for-ban | floor (5) | full pack closed-world dump |
| slice rows (gloss/anchor/morph pointer) | same-turn assemble | 50.7k pack prose |
| session manifest | code | “what we already did” memory essay |
| `cf_target` + move class | brief | CF theory |

If a budget is **0**, inject the number; do **not** rely on the model remembering “≤1 per 3 turns” from a long law dump.

#### 4.3 **GATE / CAPABILITY / CODE-ONLY** (omit from executor law core)

| Law | Primary enforcement | Leave out of executor prompt? |
|---|---|---|
| **§1.1b** exchange settlement | Pure render functions; `render_dropped`; no agenda in pixels | **YES** — model does not settle peripherals |
| **§3.2** intro ≠ knowledge; ledger allowlist | Scheduler allowlist + `apply_delta` strip | **YES** |
| **§3.2 rider** progress-is-function display | `progress_ledger` code | **YES** (not tutor speech law) |
| **§3.3** / completeness lint | `check_teacher_truncation` + new completeness lint | **YES** as law essay; realization *obeys floor*, doesn’t cite §3.3 |
| **§4.1** one orchestrator | Architecture / import lint | **YES** |
| **§4.3** eval promotion bar | Process | **YES** |
| **§4.4** cache/version | Web ops | **YES** |
| **§2.2 cluster veto at plan** | CODE veto before brief | **YES** as essay; clusters still **data-injected** |
| **§2.4 ladder intervals** | `retrieval_scheduler` | **YES** |
| **§4.5** enforcement stack | Meta for authors | **YES** |
| **§5.x** dual-author / dates / reporting | Process | **YES** |
| **§7.x** change protocol / USER-ONLY list | Process | **YES** |
| Critical gates: `unscaffolded_new_item`, `english_wall`, `probe_loop`, sheet leak, truncation; still_fail floor (surgery → hold) | Output gate + hold | **YES** as long prose — one line “gate may rewrite or hold; do not assume fail-open” is enough |
| Identity strip / tool schema without personal fields | Capability removal | **YES** beyond the short §3.1 ask-ban |

#### 4.4 **BINDING in core only if generative**

| BINDING | Placement |
|---|---|
| §2.3 English jobs | IN-PROMPT (above) |
| §2.5 CF budgets/moves | IN-PROMPT operative + DATA budgets |
| §2.1a (already) | IN-PROMPT |
| §3.4 unpriced/unknown | OUT (ops) |
| §4.2 regex smell | OUT (eng) |

#### 4.5 Census arithmetic (budget sanity)

Assume rough 4 chars/token:

| Block | Chars (design target) | Tokens ≈ |
|---|---|---|
| IN-PROMPT law core (operative only) | 3 200–4 800 | **800–1 200** |
| Persona | 1 500–4 000 | 375–1 000 |
| Brief + bans + budgets + manifest | 2 000–6 000 | 500–1 500 |
| Slice rows (variable) | 500–4 000 | 125–1 000 |
| K=3 exchanges | 1 500–6 000 | 375–1 500 |
| Pack index ≤1k tok | ≤4 000 | **≤1 000** |
| **Sum (typical)** | | **≈3.2k–7.2k tok** |

Round-1 rejected selling **4–6k as committed**; this census predicts **overlap with that band only when slice and history are moderate**. Floor completeness still wins.

**Promotion note (LAW-PROMOTION GATE):** adopting this census into the compact core is a **behavior-facing prompt change**. It does not amend PEDAGOGY text by itself, but the dual-role §3.3 amendment (item 2) **must** land before B0 ships; the census should be frozen as a versioned artifact (e.g. `prompts/executor_law_core.md` + schema `completeness_v1`) and named from the §3.3 completeness schema — not edited ad hoc per experiment arm.

**Item (4) package:** this census is the **proposed split**. Riskiest cut: moving §2.1 / §2.1a / §2.5 repair shape to gate-only — **REJECT that cut** if anyone proposes it later; those three are generation-critical and under-gated today.

---

### Package verdict (round 2)

| # | Item | Verdict |
|---|---|---|
| 1 | B0 executor context floor (synthesis) | **AMEND** — exact floor list A1 (add cluster mates + known-for-ban / no-regloss); else countersigned |
| 2 | Draft §3.3 amendment | **AMEND** — exact replacement above; **REJECT** draft-as-written (history ban vs K=3 contradiction; open “named rule”; key-only predicate) |
| 3 | Order P1→P2→B0→B1 | **COUNTERSIGN** (frozen) |
| 4 | In-prompt vs gate-only census | **PROPOSED** — §6/§2.1/§2.1a/§1.1–1.1a/§2.2op/§2.3/§2.4op/§2.5op/§2.6/§3.1-ask/persona/probe line = IN-PROMPT; budgets/keys/bans/frames = DATA; §1.1b/§3.2/§4.x/§5/§7/settlement/ledger/ladder = GATE/CODE/OUT |

**One-sentence adversary summary:** Claude integrated round 1 cleanly on architecture and order; the remaining failure modes are **specification holes** — a floor that under-names the negative palette, a §3.3 draft that both bans and requires history windowing, and a law-core cut that will silently delete §2.1/§2.5 generative shape if someone treats “gate-enforced” as “prompt-optional.”

**Freeze candidates after this round:** order (3); B0 floor once A1 list lands; §3.3 only after USER sees the **replacement** text, not the draft; law census (4) as `completeness_v1` attachment to that amendment.

---

*End Grok countersign · 2026-07-30 · design-planner-rounds r9 round 2*

---

## Round-2 adjudication (⬛ Claude, 2026-07-30) — ANALYSIS PHASE CONVERGED

All round-2 rulings accepted, no counters:
- **B0 floor:** Grok's A1 exact ten-member list adopted (negative palette
  now names cluster-mates of allowed_new + known-for-ban/no-regloss keys
  as completeness FAULTS if missing); cut-priority under token pressure:
  pack index first, then K→2 — floor members never.
- **§3.3 amendment:** my draft is WITHDRAWN (it both banned and required
  history windowing, left a "named rule" loophole, and had a key-only
  predicate). Grok's replacement text is the one that goes to the USER:
  versioned completeness schema (completeness_v1), machine-checkable
  per-turn lint, token pressure NEVER a legal omission reason, explicit
  distinction between silent truncation (banned everywhere, forever) and
  versioned realization windowing (legal only under this amendment).
- **Order:** P1 → P2 → B0 → B1 FROZEN; design parallel; no core-loop
  build until P1/P2 report or the USER explicitly prioritizes.
- **Law census:** Grok's split adopted as the completeness_v1 attachment
  (in-prompt operative core ≤800–1,200 tokens: §6 priority order, §2.1,
  §2.1a, §1.1/§1.1a two-liners, §2.2/§2.3/§2.4/§2.5 operative clauses,
  §2.6 axiom, §3.1 ask-ban, persona, probe restraint; budgets/keys/bans/
  frames as DATA; settlement/ledger/process laws GATE/CODE-only). The
  standing REJECT is recorded: §2.1/§2.1a/§2.5 may never be demoted to
  gate-only — they are generation-critical and under-gated.
- Census arithmetic accepted: realistic executor context ≈3.2k–7.2k
  tokens (floor completeness outranks any token aspiration).

**USER decision points (nothing below proceeds without them):**
1. §3.3 dual-role amendment (Grok replacement text above) — §7.4
   USER-ONLY ratification, with referee results to be attached.
2. Authorize P1/P2 falsifier runs (cheap: prompt reorder + AI-student
   batches at current context size).
3. B0 build timing: after P1/P2 data (frozen default) or in parallel
   (explicit USER override).

**Status: analysis CONVERGED 2026-07-30 (2 rounds + adjudications).**
