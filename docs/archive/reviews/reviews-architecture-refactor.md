# Review: architecture refactor (2026-07-28, in progress)

## Mandate (USER, 2026-07-28)

1. "This is sounding like an architecture problem. Bugs and weird shit all over the place because maybe the code is getting hard to understand and manage. Lets do a architecture review and refactor once the current fix and review is complete."
2. "I want you to add to this review the idea that maybe its time for a state machine. I am not saying it is but we should think about it."

## Evidence context
Every defect in the whole-system audit (docs/reviews-system-audit-20260728.md) was a SEAM defect: subsystems blind to each other's state, two systems fighting over one behavior, ledgers not hearing events. Pure services keep countersigning clean; the wiring layer (conv_session.py as accidental god-object, four scattered session-state stores, ad-hoc snapshot passing) is where defects breed. Architecture map (read-only Explore agent) in progress; its eight-section output lands below verbatim as the evidence base.

## Standing question for the review: is it time for a state machine?

Recorded per user directive — an open question, not a conclusion. The review must evaluate explicit state machines at three distinct granularities, separately (they have different answers):

1. **Item lifecycle (strongest prima facie candidate).** P8 already declares the theory: encounter → mapped → retrievable → usable → automatic. Today that lifecycle is smeared across introduced_at, first_seen, scaffold, confidence bands, status strings, interval_days, successive_successes, and milestone events — written by four different modules. Most of today's honesty bugs (false planted, gloss-thrash, retraction, "known then needs-recheck") were arguably ILLEGAL-TRANSITION bugs that an explicit transition function (one place that says which state moves are legal on which evidence) would have rejected at write time. A per-item FSM would unify the ledgers and make the progression rail a pure projection of state history.
2. **Session flow.** PhaseState already IS a crude budgeted linear machine (retrieval → new_input → task → free → close, with freeze). Question is whether formalizing it buys anything beyond what exists — or whether the guard-preemption semantics (freeze vs consume vs force_advance) would be clearer as explicit transitions with an event vocabulary.
3. **Turn flow (weakest candidate — and a tension to weigh).** The turn is a priority ladder, not a stateful machine, and the converged framing design (docs/design-instruction-framing.md) points the OTHER way for performance: fewer scripted branches, more model judgment inside code-owned facts. A turn-level FSM risks re-introducing choreography with better syntax. The review must reconcile: state machines for STATE (item/session), framing for PERFORMANCE — or argue why not.

Evaluation criteria (pre-committed): does the machine make today's defect classes structurally impossible (illegal transitions rejected at write time) rather than caught-by-gate? Does it reduce the seam count or relocate it? What does migration cost against 543 green tests? Verdict per granularity, countersigned.

*Awaiting the architecture map; proposal follows in this doc.*

---

## Architecture map (Explore agent, 2026-07-28) — headline evidence

Full eight-section map in the session record; load-bearing numbers reproduced here:

- **tutor/ = 22,918 lines / 47 modules.** Orchestration 15%, pure services 38%, decision/prompt 9%, model adapters 5%, UI/transport 7%, **legacy-dead 24.5% (5,625 lines)** — including telemetry.py (574 lines, ZERO importers), ai_student/pedagogy_controller/planner/lesson_flow/cli/conversational (legacy stack), learner_profile (1 of 11 functions used).
- **conv_session.py = 2,861 lines**, fan-out to 27 tutor modules (57% of package), 62 lazy imports. `_execute_ai_tutor` = **862 lines / 38 inline stages** touching every subsystem; sheet written to disk 7 times per turn across 5 sites; SessionMemory.snapshot() called 5×/turn. Sibling `_execute_rules_planned` silently executes 12 of the 38 stages and uses UNCLIPPED history where the AI path clips. `user_turn` is ~110 lines dead legacy prose.
- **Test topology inversion:** 543 tests pin the leaves (output_gate 51, introduce_router 45, phases 35...); **the 862-line integrator has 0% automated coverage** — zero tests call _execute_ai_tutor/_execute_rules_planned/user_turn/open_session on a real session. One test literally asserts "branch verified present" (code shape, not behavior). No conftest.py, no fake model client, no session fixture.
- **State census:** 5 session stores + 8 loose attributes across **5 reset paths covering 5 DIFFERENT subsets**. `open_session` resets 1 of 5. **Live bug: web resume ("new chat") resets 0 of 5 stores while clearing chat history** — intro budget, asked_topics, cooldowns, phase clock, and task state all leak from the previous chat. Out-of-object: progress ledger has NO production reset/retraction caller (a fresh learner after reset_sheet is dedupe-suppressed by the prior learner's milestones); teach_assets generator/index/warm-inflight are process-global across all web sessions. The snapshot/from_snapshot serialization contract exists on ModeSessionState/PhaseState/TaskState with zero production callers.
- **Seams:** check_output_gate takes 18 args spanning 5 subsystems; select_mode 11; gate imports session_memory._deaccent (private) and calls retrieval_scheduler directly. decision.reason string-parsed by prefix; notes re-parsed 3× inside the module that emitted them; ~40 undeclared note prefixes are the de facto data bus (evals parse ~12 by prefix).
- **Duplication:** boundary regex ×3, Spanish letter class ×5, accent fold ×5 with 3 incompatible semantics, "already asked" ×4 representations, signal derivation 4×/turn, 6 instruction-block builders with 5 copies of the same mutation idiom and 3 inline spellings of one eligibility predicate. **Six parallel concept inventories** (175/21/16/10/9/6 entries); ASSOCIATION_NOUNS has zero readers; casa/ciudad can fire guard 6 with no image entry behind them. Counter-example that worked: gloss_after_key/anchor_in_reply extracted once, shared — never a defect site.

## Refactor proposal (⬛ Claude, 2026-07-28, round 1)

Constraints: behavior-neutral phases (no features mixed in); 543 tests + evals green after every phase; PEDAGOGY laws preserved (§1.1, §1.1a, §4.1); the converged framing design (docs/design-instruction-framing.md) must remain buildable on the result — its "content contributors" stage maps onto Phase 4's pipeline.

**Phase 0 — Characterization harness (PREREQUISITE, per the map).** conftest.py with a fake model client (canned <tutor> replies), a session fixture, and golden-turn characterization tests for _execute_ai_tutor (notes set, parts keys, sheet deltas, state mutations) plus the rules-path divergences AS THEY ARE (including the unclipped-history discrepancy — characterize, then decide). Nothing else moves until this exists.

**Phase 1 — SessionState aggregate (map move 2; lowest cost, highest bug-class kill).** One object owning SessionMemory/ModeSessionState/PhaseState/TaskState/CostTracker + the 8 loose attributes; ONE reset(kind) with an explicit coverage table (fresh/new-chat/sheet-reset); the unused snapshot contracts become its persistence surface. Fixes the resume-leak bug by construction. Progress-ledger reset semantics decided here (fresh learner → new ledger scope or production retraction path).

**Phase 2 — tutor/textnorm.py (map move 3).** Three NAMED policies (fold_lexical / fold_asset_key / fold_id), one boundary matcher, one letter class; 8 modules migrate; the private-import crossing dies. Policies are NOT merged (the three semantics differ deliberately — asset keys underscore, lexical keeps ñ).

**Phase 3 — Typed turn events (map move 5; additive).** Enum + dataclass event bus replacing note-string re-parsing; strings still rendered for logs/evals on day one; evals migrate off prefixes incrementally. Gate context consumes events, not re-split strings.

**Phase 4 — TurnContext + staged pipeline (map move 1; the big one, only after 0-3).** Explicit stages: observe → guards/select → phase → CONTRIBUTORS (due/introduce/task/close/zero-register as uniform InstructionContributor implementations with one eligibility predicate) → realize → gate/repair → RECORDERS (sheet/scheduler/first_seen/progress/memory as uniform TurnRecorder implementations) → capture/log. One sheet save per turn at a defined point. _execute_rules_planned becomes the same pipeline with a different stage list — divergences become visible configuration, not drift.

**Phase 5 — Inventory collapse (map move 4; retires part of SCRIPTED-CONTENT DEBT).** association_table gains the asset-sidecar schema slots (image prompt/visual score); CONCEPT_LEXICON becomes the sidecar keyed by table IDs; the four stray lists (TOPIC_CONCEPT_NOUNS, _noun_from_text pairs, _concepts_from_spanish, observe topic_vocab) derive from table queries; dead ASSOCIATION_NOUNS deleted. Table-coverage gate per §1.1a migration rules (fill before flip).

**Phase 6 — Dead-code quarantine (USER-visible decision, flagged).** 5,625 unreachable lines move to archive/ (git preserves history); 4 console scripts + evals/run_smoke.py + 57 legacy tests retire with them. Proposed, not assumed: it deletes a quarter of the package's grep surface but also its disambiguation tax.

**State-machine verdict (per the standing question; three granularities, three answers):**
1. **Item lifecycle — YES, adopt.** Formalize the P8 lifecycle as an explicit per-item machine: unseen → first_seen → introduced → scheduled(ladder) → durable, with recheck/regressed arcs. ONE transition function (retrieval_scheduler already half-owns it) validating legality at write time; the progress ledger becomes the transition log; the milestone rail a pure projection. Today's honesty-bug class (false planted, gloss-thrash, known-then-recheck) becomes structurally impossible — illegal transitions REJECTED, not gate-caught. This is Phase 1.5 (rides the SessionState work; the sheet schedule fields become the machine's persisted state).
2. **Session flow — NO new machine.** PhaseState already is the machine; Phase 4 gives its events (freeze/consume/advance) explicit names in the pipeline. Formalizing further is ceremony.
3. **Turn flow — NO.** A turn-level FSM would re-introduce choreography with better syntax, against the converged framing design. The pipeline is a sequence with contributor/recorder plug points, not a state machine. Machines for STATE, framing for PERFORMANCE.

**Countersign task for Grok (round 1):** (a) attack the phase ordering and the behavior-neutral claim — where does Phase 1 or 4 secretly change behavior (e.g., single sheet-save point vs today's 7 writes: crash-consistency differences)? (b) The item-lifecycle machine: right states? where do confidence bands fit (in-machine or orthogonal)? does making the ledger the transition log break the append-only/retraction design? (c) Phase 0 harness: sufficient characterization strategy, or does golden-turn testing ossify today's accidental behavior (how do we mark characterized-but-wrong)? (d) Phase 6 quarantine: safe list correct? anything on it secretly load-bearing? (e) What's MISSING from the plan that the map evidence demands? (f) Sizing: which phases are one agent-batch each vs multi-batch? COUNTERSIGN/AMEND/REJECT per item with exact replacements.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 19:32 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll verify the architecture map claims against the codebase and attack the proposal item-by-item rather than accepting it at face value.Checking a few more Phase 6 and dual-path details before writing verdicts.## Grok countersign — architecture refactor round 1 (2026-07-28)

Independent verification against `/Users/patrickcremin/repo/ml_teacher` on 2026-07-28. Map claims treated as data; several are wrong enough that a plan which depends on them uncorrected will mis-sequence work.

---

### Map accuracy (must land before phases are treated as evidence-locked)

| Claim | Measured 2026-07-28 | Ruling |
|---|---|---|
| `tutor/` 22,918 lines / 47 modules | 22,918 lines; **48** `.py` modules | AMEND module count |
| legacy-dead 5,625 (24.5%) | Listed stack sum: telemetry 574 + ai_student 1490 + pedagogy_controller 1481 + planner 756 + lesson_flow 419 + cli 245 + conversational 212 + learner_profile 153 = **5,330** (5,330/22,918 ≈ **23.26%**) | AMEND arithmetic; do not use 24.5% without a published file list |
| `_execute_ai_tutor` 862 lines | L1480–L2340 = **861** | OK (off-by-one) |
| sheet written **7×/turn across 5 sites** | `save_sheet(` sites in file: 7 total; **inside `_execute_ai_tutor` only 3** (L2084, L2127, L2260); `_finish` adds 1 more (L1361) on paths that call it. Not “7 per turn” and not “5 sites” | **REJECT** quantitative claim; replace with: mid-turn AI path ≤3 conditional saves + finish/init/public paths elsewhere |
| `SessionMemory.snapshot()` 5×/turn | AI path **4** (L1598, L1653, L1748, L1883); rules path +1 (L2419) | AMEND |
| 543 tests | `def test_` count = **553** | AMEND |
| integrator 0% coverage | No test **calls** `_execute_ai_tutor` / `_execute_rules_planned`; only a **source-shape** comment in `tests/test_session_fixes.py` L824 (“branch verified present”). `user_turn`/`open_session` appear only via fakes or non-pipeline unit use | COUNTERSIGN direction; wording OK |
| no `conftest.py` | confirmed | COUNTERSIGN |
| `check_output_gate` 18 args | 2 pos + 16 kwonly = **18** | COUNTERSIGN |
| `select_mode` 11 | 1 pos + 10 kwonly = **11** | COUNTERSIGN |
| gate imports `session_memory._deaccent` | `output_gate.py` L662 | COUNTERSIGN |
| `ASSOCIATION_NOUNS` zero readers | defined `modes.py` L22 only; no other references | COUNTERSIGN |
| `user_turn` ~110 lines **dead** legacy prose | **REJECT.** `user_turn` is L2573–L2714 (**142** lines) and is the **production entry**: `web_app.py` L502, `evals/run_conv_smoke.py`, `tutor/conversational.py`. Planned branch is live; only the post-`_planned_enabled()` harness block is legacy | AMEND map before Phase 6/4 wording |
| web “new chat” resets **0 of 5** stores | **REJECT as stated.** Default `session_start` uses `want_fresh = body.fresh or not body.resume` and on fresh **pops the old session and constructs a new `ConversationalSession`** (`web_app.py` L441–L453, L157–L160), which re-inits memory/mode/phase/task/costs. Real residual: (1) `open_session` alone resets **costs only** (L2495) if called on a **live** object; (2) **progress ledger** is process/file-global with no production wipe; (3) **teach_assets** `_generator` / `_warm_inflight` are process-global | AMEND bug statement |
| fan-out 27 modules / 62 lazy | import set from `conv_session` = **25** tutor modules; indented `from .` ≈ **63** | AMEND |

---

### (a) Phase ordering and “behavior-neutral” claim

**Verdict: AMEND** (do not COUNTERSIGN as written).

**Attack:**

1. **Phase 0 → 1 → 2 → 3 → 4 order is mostly right**, but **Phase 1 is not behavior-neutral** if it “fixes the resume-leak by construction.” A deliberate product bugfix is a **behavior change**, not a refactor. Same for progress-ledger scope/retraction on sheet-reset.
2. **Phase 4 “one sheet save per turn” is not behavior-neutral under crash/partial-failure.** Today introduce success can `save_sheet` at L2084 **before** later stages; a crash mid-turn can leave introduce planted while later outcome/enqueue missing. Single end-of-turn save makes the turn **atomic** (usually better) but changes durability semantics under kill/OOM. That must be **named** as an intentional consistency change, not hidden under “neutral.”
3. **Phase 1.5 item FSM riding “free” on Phase 1 overloads the aggregate PR.** SessionState aggregation and a write-time transition function on ability/schedule fields are different risk classes; honesty law in `retrieval_scheduler.py` (schedule fields allowlist; confidence/status protected) will be touched.
4. **Phase 5 before full Phase 4 contributor unify is OK**, but flipping inventories without characterization of guard-6 / image paths will re-break `casa`/`ciudad`-class defects the map itself cites.
5. **Phase 6 last is correct** only after entrypoints and pyproject scripts are decided; quarantine is not free graph cleanup.

**Exact replacement — Constraints + ordering note (replace proposal Constraints paragraph and add after Phase 0):**

```text
Constraints:
- Refactor phases are *behavior-intent-declared*, not silently “neutral.”
  Allowed intentional deltas must be listed per phase in the PR description.
  Default bar: 553 tests + evals green; PEDAGOGY §1.1 / §1.1a / §4.1 preserved;
  converged framing design (docs/design-instruction-framing.md) remains buildable
  (content contributors map to Phase 4).
- Forbidden in refactor PRs: new teaching features, pack content edits, prompt
  stance rewrites, law text changes (LAW-PROMOTION GATE stays in PEDAGOGY.md).

Intentional behavior deltas (pre-declared, not “neutral”):
- Phase 1: unified reset(kind) including new-chat/sheet-reset coverage may
  change session-scoped counters vs today on any path that previously cleared
  history without reconstructing stores; progress-ledger scope decision is
  product-visible.
- Phase 4: at most one durable sheet persist per successful turn (atomic turn
  write). Mid-turn multi-save crash windows go away by design; document the
  new durability contract in the PR. Do not claim bit-identical disk traces.
- Phase 1.5 (item lifecycle machine): NOT part of Phase 1. Separate PR after
  Phase 1 + characterization of schedule/ability write sites.
```

**Exact replacement — Phase 4 save sentence:**

```text
One durable sheet save per successful turn at a single recorder-stage commit
point (atomic turn). Partial mid-turn saves are removed deliberately; crash
recovery semantics change from “last mid-turn save wins” to “turn commits or
it doesn’t.” Characterization harness must assert commit-point field sets, not
byte-identical intermediate files.
```

---

### (b) Item-lifecycle machine

**Verdict: AMEND** (YES to an explicit transition function; NO to the proposed state sketch and ledger conflation as written).

**Attack:**

1. **States as proposed (`unseen → first_seen → introduced → scheduled → durable`) do not match P8** (PEDAGOGY.md 2026-07-28: encounter → mapped → retrievable → usable under pressure → more automatic) **and do not match the code’s two-axis model:**
   - **Schedule axis** (scheduler-owned): `first_seen`, `introduced_at`, `scaffold`, `next_due`, `interval_days`, `successive_successes` — allowlisted in `SCHEDULE_FIELDS`.
   - **Ability axis** (sheet/process_turn-owned): `confidence`, `status`, `solid_uses` — **protected**; scheduler must not write them.
2. Folding confidence bands **into** the same FSM **reopens the honesty bug class** the scheduler was written to prevent (“introduction is not knowledge”).
3. **“Progress ledger becomes the transition log” breaks object-class law** already implemented in `progress_ledger.py` (header: history vs state are different classes; ledger never writes the sheet; append-only + `retracted` voids display/dedupe without rewriting history). Making the ledger the machine’s log either:
   - forces every legal micro-transition to mint rail events (spam + false celebrations), or
   - dilutes the rail into an audit dump (product regression).
4. **“Honesty bugs become structurally impossible” is overstated.** An FSM rejects illegal *writes*; it does not fix illegal *evidence classification* (false planted was “scaffold evidence wrong,” not “missing enum”). Gates on evidence remain necessary.
5. **`scheduled(ladder)` is not a single state** — ladder position is continuous (`interval_days` ∈ {1,3,…,14}, `successive_successes`). Encode as **data on a `retrievable` state**, not a free-text superstate.

**Exact replacement — state-machine verdict item 1:**

```text
1. Item lifecycle — YES, adopt a write-time transition API; NO single mega-FSM
   that merges ability + schedule + rail.

   Two orthogonal machines (or one API with two field classes):

   A) Encounter/schedule machine (extends retrieval_scheduler; sole writer of
      SCHEDULE_FIELDS):
        absent → first_seen → introduced → on_ladder(interval_days,
        successive_successes, next_due) → lapsed/re-queue on fail.
      Legal edges only; mark_introduced / mark_first_seen / record_outcome /
      enqueue become thin wrappers over transition(evidence).

   B) Ability machine (extends character_sheet process_turn / _bump_status):
        unknown/fragile/emerging/known with confidence + solid_uses gates.
      Introduction transitions MUST NOT write B (existing honesty law).

   Progress ledger stays a *projection* of selected crossings (planted,
   taking_root, rooted, regression, …) with append-only + retraction —
   NOT the transition log. Transition log = sheet fields (+ optional debug
   notes). Rail remains celebration/honesty UI, not source of truth.

   Confidence bands: orthogonal (machine B), never states of machine A.

   Phase placement: Phase 1.5 after SessionState (Phase 1) and after Phase 0
   characterization of every schedule/ability write site. Success criterion:
   illegal cross-axis writes raise; false-planted class still needs evidence
   predicates (FSM alone insufficient).
```

**Session / turn granularities (items 2–3):** **COUNTERSIGN** — PhaseState is enough; turn-level FSM rejected (agrees with framing design). Pipeline ≠ state machine.

---

### (c) Phase 0 characterization harness

**Verdict: AMEND.**

**Attack:** Golden turns without a **known-bug registry** will ossify seam defects (unclipped rules history, multi-save order, note-prefix bus) as sacred. “Characterize then decide” is right only if wrong behavior is explicitly labeled.

**Exact replacement — Phase 0:**

```text
Phase 0 — Characterization harness (PREREQUISITE).
- tests/conftest.py: session fixture; FakeModelClient returning canned <tutor>
  bodies; no silent truncation of sheet/pack/stance/history fed to the model
  (docs/teacher-context-no-truncate.md; scripts/check_teacher_truncation.py).
- Golden-turn tests that exercise ConversationalSession.user_turn /
  open_session → _execute_ai_tutor (and rules path) on a real session object
  with the fake client. Assert: notes set, parts keys, sheet deltas, store
  mutations, save_sheet call count/order (via monkeypatch), history clipping
  policy.
- Characterization classes:
    CHAR_PIN   — desired behavior; fail CI if changed.
    CHAR_BUG   — documented accidental behavior; test passes today; must not
                 silently flip without a bugfix PR that updates the pin.
    CHAR_DIVERGE — AI vs rules intentional/unintentional differences
                 (including rules path using unclipped history at
                 conv_session.py ~L2425 vs AI history_for_model ~L1895).
- Nothing in Phases 1–6 merges or deletes a CHAR_BUG without an explicit
  “bugfix” section and pin update. Golden files live under
  tests/characterizations/ with a one-line bug id referencing
  docs/reviews-system-audit-20260728.md or this review.
```

---

### (d) Phase 6 quarantine — safe list

**Verdict: AMEND** (list is **not** safe as written).

**Arithmetic on tests:** pure legacy test files `test_ai_student.py` (11) + `test_pedagogy_controller.py` (18) + `test_lesson_flow.py` (13) = **11+18+13 = 42**, not 57. Claim “57 legacy tests” is **unverified/rejected** until a file list is published (42 ≤ x ≤ 57 only with an explicit inventory).

**Load-bearing / do-not-archive without entrypoint rewrite:**

| Artifact | Why |
|---|---|
| `user_turn` / `open_session` | Production API — not quarantine candidates |
| `tutor/web_app.py`, `tutor-web` script | Live product |
| `evals/run_conv_smoke.py` | Live conversational evals — **not** `run_smoke.py` |
| `tutor/learner_profile.py` | Still imported for `profile_path_for_sheet` / reset cleanup from `conv_session.py` — quarantine only after path helper extracted |
| `tutor/planner.py` / pedagogy_controller / lesson_flow | Closed legacy cycle; OK to archive **if** console scripts and EXP harnesses updated |
| `pyproject` scripts `tutor`, `tutor-chat`, `tutor-ai-student` | Break installs if modules move without script edits |
| `tutor/rules_planner.py`, `plan_card.py`, `executor.py` | Optional TEACHER_MODE=rules + tests — **not** the same as `planner.py` |

**Telemetry:** zero production importers — **safe to archive**.

**Exact replacement — Phase 6:**

```text
Phase 6 — Dead-code quarantine (USER decision; not assumed).
Safe archive candidates (after import graph CI check = 0 production importers):
  tutor/telemetry.py;
  tutor/ai_student.py;
  tutor/pedagogy_controller.py;
  tutor/planner.py (EXP-002 pack planner — not rules_planner);
  tutor/lesson_flow.py;
  tutor/cli.py + tutor/conversational.py ONLY after pyproject.scripts retarget
  or removal is USER-approved;
  evals/run_smoke.py (pack/EXP path) — keep evals/run_conv_smoke.py.

Not archive:
  conv_session user_turn/open_session/_execute_ai_tutor;
  web_app; session_phases; modes; output_gate; retrieval_scheduler;
  progress_ledger; teach_assets; rules_planner/plan_card/executor;
  learner_profile until path helper extracted.

Process: move to archive/tutor_legacy/ in one PR with: updated pyproject
scripts, pytest ignore for archived tests, and a printed importer graph.
Publish the retired test file list and count (do not claim 57 without the list).
Line-count target re-measure post-move; do not advertise 24.5% until remeasured.
```

---

### (e) Missing items the map evidence demands

**Verdict: AMEND — add the following as Phase requirements (not optional niceties).**

**Exact replacement block — insert as “Phase gaps (Grok 2026-07-28)” after Phase 6:**

```text
Missing from Claude round-1 plan (required):

E1. teach_assets process-global isolation (_generator, _warm_inflight, index).
    Map correctly flags cross-session bleed; no phase owns it. Add Phase 1b
    or Phase 4 recorder precondition: per-app or per-session warm set;
    generator registration stays process-level but inflight/index mutation
    must not leak pedagogical state across learners.

E2. Production snapshot wiring. ModeSessionState/PhaseState snapshot APIs
    exist with ~zero production callers; SessionState (Phase 1) must either
    wire them for web resume OR delete the dead contract — not leave a third
    half-serialization.

E3. Gate/select context objects. Phase 3 events alone do not shrink
    check_output_gate’s 18-arg seam; Phase 4 must introduce GateContext /
    ModeContext (or TurnContext slices) and cut private _deaccent import.

E4. Dual-path policy after characterization. CHAR_DIVERGE must end in a
    written decision: delete rules path, or make it a stage-list config of
    the same pipeline (Phase 4 claim) with identical history clipping.

E5. Integrator coverage bar. Phase 0 is not done at “a few goldens exist”;
    done when open_session + N≥3 multi-turn user_turn paths hit
    _execute_ai_tutor under FakeModelClient (placement, repair, introduce,
    due elicit). Leaf 553 tests remain necessary but insufficient.

E6. Note-prefix bus inventory. Phase 3 needs a checked-in catalog of the
    ~40 prefixes (owners, consumers, eval parsers) before additive events;
    otherwise events+strings dual-write forever.

E7. Correct the resume/new-chat bug statement before Phase 1 implements the
    wrong fix (see map accuracy table).
```

---

### (f) Sizing (agent-batch vs multi-batch)

**Verdict: COUNTERSIGN with the following table (exact replacement for implicit one-phase-one-PR optimism).**

| Phase | Batches | Rationale |
|---|---|---|
| 0 Characterization | **2–3** | Fake client + fixture; then AI goldens; then rules diverge + CHAR_BUG tags |
| 1 SessionState aggregate | **2** | Aggregate + reset table without behavior fix; then intentional reset/ledger-scope fix + web_app call sites |
| 1.5 Item transition API | **2–3** | Schedule axis only first; ability axis; ledger projection pins |
| 2 textnorm | **1–2** | Mechanical if policies named; 8 modules + gate private import |
| 3 Typed events | **2** | Enum/dataclass + dual render; then gate/evals migrate off prefixes |
| 4 Turn pipeline | **4–6** | Highest risk: stage cuts of 861-line function; one stage family per batch; keep user_turn façade green |
| 5 Inventory collapse | **2–3** | Schema/sidecar fill; derive lists; delete ASSOCIATION_NOUNS after coverage gate |
| 6 Quarantine | **1** | After USER OK + importer CI; scripts/tests update same PR |

**Arithmetic:** minimum serial depth if no parallelization:  
\(3+2+3+2+2+6+3+1 = 22\) agent-batches worst case; optimistic critical path with parallel (2∥3 after 1): roughly \(3+2+3+\max(2,2)+6+3+1 = 20\) still multi-week human time, not a weekend. Do not schedule Phase 4 until Phase 0 goldens exist — **0 before 4 is HARD.**

---

### Three-granularity state-machine rollup

| Granularity | Claude | Grok |
|---|---|---|
| Item lifecycle | YES adopt | **AMEND** — yes transition API; two axes; ledger ≠ log; not free on Phase 1 |
| Session flow | NO new machine | **COUNTERSIGN** |
| Turn flow | NO | **COUNTERSIGN** |

---

### Round-1 overall

**NOT CONVERGED as written.**  

| Item | Verdict |
|---|---|
| (a) ordering / neutral | **AMEND** |
| (b) item machine | **AMEND** |
| (c) Phase 0 harness | **AMEND** |
| (d) Phase 6 list | **AMEND** |
| (e) missing | **AMEND** (E1–E7 required) |
| (f) sizing | **COUNTERSIGN** (table above) |

**BLOCKERS before this proposal can become final:**

1. Apply map accuracy corrections (especially **user_turn not dead**, **new-chat reset claim**, **save_sheet frequency**, **553 tests**).  
2. Accept AMEND text for (a)–(e).  
3. Split Phase 1.5 from Phase 1; declare atomic sheet save as intentional.  
4. User still owns Phase 6 go/no-go and console-script retirement.

No further dual-author round needed **if** Claude accepts these exact replacements without re-softening the honesty two-axis split or re-labeling bug fixes as “behavior-neutral.”

---

## Adjudication — Round 1 (⬛ Claude, 2026-07-28) — ACCEPT ALL, no re-softening; CONVERGED per Grok's stated condition

Grok's exact replacement blocks for (a)–(e), the sizing table (f), and ALL map-accuracy corrections are BINDING over my round-1 text. On-the-record corrections of my own claims:

1. **Map corrections accepted** — most materially: `user_turn` is the PRODUCTION ENTRY (only its post-guard harness block is legacy), and my relayed "web new-chat resets 0 of 5 stores" was wrong as stated — the default fresh path constructs a new session object; the REAL residuals are narrower (open_session on a live object resets costs only; the progress ledger has no production reset/retraction caller; teach_assets warm/index state is process-global across learners). Also: 553 tests not 543; save_sheet is ≤3 conditional mid-turn saves on the AI path, not 7/turn; dead-code arithmetic is 5,330/23.3% pending a published file list.
2. **(a) ACCEPT** — "behavior-neutral" was hiding bugfixes. The plan is now behavior-INTENT-DECLARED: Phase 1's reset unification and Phase 4's atomic-turn sheet save are pre-declared intentional deltas with documented durability semantics. Phase 1.5 is split out of Phase 1.
3. **(b) ACCEPT in full** — the two-axis design is strictly better than my single machine: an encounter/schedule machine (scheduler-owned, SCHEDULE_FIELDS) and an ability machine (sheet-owned, confidence/status) with cross-axis writes ILLEGAL — my merged FSM would have re-fused what the honesty allowlist deliberately separates. The progress ledger remains a PROJECTION of selected crossings, never the transition log (object-class law). And the overclaim is withdrawn: an FSM rejects illegal writes; evidence misclassification still needs gates.
4. **(c) ACCEPT** — CHAR_PIN / CHAR_BUG / CHAR_DIVERGE taxonomy adopted; no golden may ossify a bug unlabeled; the rules-path unclipped-history divergence is characterized then DECIDED (E4).
5. **(d) ACCEPT** — quarantine list corrected (telemetry/ai_student/pedagogy_controller/planner/lesson_flow/run_smoke safe; learner_profile only after the path-helper extraction; cli/conversational only with USER-approved script retirement; 42-test floor until the file list is published).
6. **(e) E1–E7 ACCEPT as phase requirements** — teach_assets cross-session isolation, snapshot wiring-or-deletion, GateContext/ModeContext to kill the 18-arg seam, dual-path decision, the integrator coverage bar (N≥3 multi-turn golden paths), the note-prefix catalog, and the corrected reset-bug statement.
7. **(f) COUNTERSIGN accepted** — ~20–22 agent batches; Phase 0 before Phase 4 is HARD.

**Review CLOSED — CONVERGED AS AMENDED (1 round; five AMENDs + map corrections, all accepted).** Execution: authorized by the user's standing refactor mandate; Phase 0 batch 1 dispatched 2026-07-28. USER-reserved: Phase 6 go/no-go + console-script retirement; Phase 1's declared behavior deltas ride the normal review trail.

---

## Phase 0 batch 1 landed (agent, 2026-07-28)

Harness only — zero production-code changes (no injection seam had to be touched: the client is injected by monkeypatching `config.make_client_for`, which `ConversationalSession.__init__` calls; anything else asking for a client also receives the fake, so nothing can reach the network).

**Files:** `tests/conftest.py` (FakeModelClient + `tutor_session_factory`/`tutor_session` fixtures + truncation-law guard + golden helpers), `tests/test_characterization_ai_path.py` (7 tests), `tests/characterizations/` (7 golden JSONs + `known_bugs.json` registry).

**Isolation per test:** tmp `sheet_path`; `PROGRESS_LEDGER_PATH` env (read at call time); `COST_LEDGER_PATH` env **plus** `tutor.costs.LEDGER_PATH` attr (bound at import — env alone is insufficient, note for E2/E1 work); teach-assets `ASSETS_DIR/CACHE_DIR/INDEX_PATH/MANIFEST_PATH` redirected to an empty tmp dir with `_generator=None` and `_index` reset (the process-global E1 state — with an empty cache no image ever attaches, so goldens are machine-independent of the gitignored local image cache); `log=False`; focus/classifier rails off via config attrs; association table loaded read-only from the real pack. `conv_session.save_sheet` is wrapped to record call sites.

**Truncation-law guard (auto-teardown on every factory session):** asserts all `*_PROMPT_CHARS`/`HISTORY_TURNS` caps are 0, the FULL `load_pack` text is a substring of every request's system blocks, the task's embedded sheet JSON parses completely (a `[:N]` slice breaks the parse) with all sections present, and the last request's messages carry the entire session history prefix (no `[-N:]` window).

**Pinned this batch (goldens through the PUBLIC API — open_session + user_turn → `_execute_ai_tutor`, per E5):**
1. *Blank open (placement) + zero-register turn* — `blank_open_placement` hard break, phase clock FROZEN on the open, post-open English turn = `default_conversation` carrying TRUE-ZERO REGISTER + NEW INPUT phase prefix + an R-E introduce plan for «hola»; un-realized plan lapses silently (budget unconsumed); glossed «bien» takes the AMEND-1c `first_seen` path (no `introduced_at`, no enqueue, confidence 0.0).
2. *Due elicit* (known sheet, `pan`+`agua` due) — DUE block on open lists both (oldest-first `agua,pan`); learner using `pan` records the outcome PRE-call (ladder 0→1 successes, due tomorrow; status/confidence untouched by the scheduler), the turn's DUE block then offers only `agua`; scene guard (`boat_likes`) outranks default flavor on a «gusta» turn while the DUE block still rides.
3. *Introduce mark path* (known sheet, no dues → new_input) — plan emitted on the flavorable OPEN too; realized turn («hola» + R-E anchor "hello") → `introduced:hola`, budget 2→1, `planted` rail milestone in the isolated ledger, schedule fields written with confidence 0.0/status unknown (honesty law), learner-used-key gate exemption («muy bien») pinned.
4. Per-turn `save_sheet` call-site lists, notes lists (volatile families normalized), parts key sets, phase/memory/mode_state mutations, request counts, usage/stop_reason for all of the above.

**CHAR_BUG tags created (registry: `tests/characterizations/known_bugs.json`):**
- **CHAR-BUG-001** — ≤3 conditional mid-turn `save_sheet` sites per AI turn (`__init__`/`_finish`/`_execute_ai_tutor`); turn is not atomic. Pinned by every golden's save-call list; Phase 4 atomic-turn is the declared fix.
- **CHAR-BUG-002** — `english_only_streak` double-counts the current turn (conv_session increments pre-select; modes guard 4 adds it again) → association hard break can fire on the FIRST English-only turn. Pinned by `golden_english_streak`.
- **CHAR-BUG-003** — `result.notes` non-chronological: pre-call scheduler/introduce notes render AFTER the post-call gate verdict (ordering pinned; Phase 3 events are the fix).
- **CHAR-BUG-004** — image-miss note duplicated per concept per turn (mode-attach site + fallback-decision site both note `image_gen_disabled:<concept>`); pinned inside three goldens.

**Golden regeneration protocol:** `CHAR_GOLDEN_UPDATE=1` rewrites goldens (never set in CI); a CHAR_BUG pin may only be regenerated by the bugfix PR that also updates the registry entry (Phase 0 law: no silent flips).

**Verification:** full suite green — **503 tests** (496 on the current working tree pre-batch + 7 new; the review's 553 figure predates the legacy-test removals now sitting uncommitted in the working tree) + 17 subtests; `scripts/check_teacher_truncation.py` ok (14 files); no server restart needed; nothing committed.

**Batch 2 must cover (per the amended Phase 0 spec + E4/E5):** rules-path goldens (`TEACHER_MODE=rules` through the same fixture) + the CHAR_DIVERGE set — most importantly the rules path's UNCLIPPED `self.history` vs the AI path's `config.history_for_model` (identical in testing mode, divergent the moment `HISTORY_TURNS>0` — characterize then DECIDE per E4); a gate-fault → repair golden (scripted critical fault, second fake call, usage accumulation, `output_gate_repaired`/`still_fail` notes); a comprehension-repair golden (meta turn against `last_tutor_try`); multi-turn budget arcs (intro budget exhaustion → R-G no-plan; hard-break spacing) and the close-phase summary block. Candidate CHAR_BUG for batch 2 scrutiny: the open turn marks EVERY open scene as `scene_modeled` (kills the scene-needs-model guard for the whole session).

---

## Phase 6 executed as deletion (agent, 2026-07-28)

USER directive 2026-07-28: "if there is dead code just delete it" — executed as outright deletion (git history is the archive), superseding the archive/-quarantine mechanics; console-script retirement thereby USER-approved. Grok's round-1 AMEND safe/not-safe lists treated as binding.

**Importer graph (computed before deletion; production scope = tutor/, evals/run_conv_smoke.py, scripts/):** every importer of every candidate is itself inside the deletion set — planner ↔ pedagogy_controller; planner → lesson_flow/student/directive_gate; pedagogy_controller → student/pack_lookup; cli → student/policy; evals/run_smoke.py → cli/planner/policy/student. telemetry, ai_student, conversational: ZERO importers anywhere. No module spared; nothing on the list had an outside production importer. Non-import references found and fixed: tutor/config.py help string (`python -m tutor.pedagogy_controller session` → `python -m tutor.web_app`). Kept-by-graph: evals/checks.py (imported by kept tests/test_ghostwrite.py), evals/trajectories.py (imported by kept evals/referee_bundle.py), tutor/corpus.py (imported by conv_session), tutor/rules_planner.py / plan_card.py / executor.py (live rules path — never candidates).

**Deleted production/eval files (12, 5,715 lines):**

| File | Lines |
|---|---|
| tutor/ai_student.py | 1,490 |
| tutor/pedagogy_controller.py | 1,481 |
| tutor/planner.py (EXP pack planner — rules_planner.py untouched) | 756 |
| tutor/telemetry.py | 574 |
| tutor/lesson_flow.py | 419 |
| tutor/cli.py | 245 |
| tutor/conversational.py | 212 |
| tutor/student.py | 129 |
| tutor/pack_lookup.py | 86 |
| tutor/directive_gate.py | 57 |
| tutor/policy.py | 23 |
| evals/run_smoke.py (run_conv_smoke.py kept) | 243 |

**Retired test files (4 files, 57 tests, 685 lines)** — exact list per Grok's demand (resolves 42-vs-57: Grok's floor missed test_harness.py):

| File | Tests | Lines |
|---|---|---|
| tests/test_pedagogy_controller.py | 18 | 200 |
| tests/test_harness.py (imports: tutor.cli, tutor.student) | 15 | 161 |
| tests/test_lesson_flow.py (imports: lesson_flow, pack_lookup, pedagogy_controller, student) | 13 | 146 |
| tests/test_ai_student.py | 11 | 178 |

**Console scripts:** removed `tutor` (tutor.cli:main), `tutor-chat` (tutor.conversational:main), `tutor-ai-student` (tutor.ai_student:main) from pyproject; `tutor-web` kept.

**Doc pointer fixes (minimal):** README.md (CLI section folded into Web; legacy pack-tutor run block replaced with deletion note), docs/web-and-audio.md (CLI surface row removed; AI-student section replaced with deletion note), docs/planner-executor-protocol.md + docs/conversational-spanish-and-learner-model.md status headers TABLED→RETIRED. Review docs untouched (append-only trail).

**Remeasured (no stale percentages):** tutor/ 22,918 lines / 48 modules → **17,446 lines / 37 modules** (−5,472 lines, −23.9% of package; −11 modules). Total deleted across repo: 6,400 lines / 16 files. Suite: 553 → **496 passed** (+17 subtests), fully green; delta −57 matches the retired list exactly. scripts/check_teacher_truncation.py ok (14 files). `import tutor.web_app` OK — no server restart required.

**Follow-ups (not this batch):** (1) tutor/learner_profile.py NOT deleted — conv_session.py imports `profile_path_for_sheet` and conv_session was file-scope-locked to a parallel agent this batch; delete after the path-helper extraction (per Grok's not-safe list). (2) Orphaned prompt assets now reader-less: prompts/ai_student.md, executor_controller.md, planner_controller.md, planner_controller_brief.md, planner_structured.md, planner_wrapper.md, thin_runtime.md (7 files; not code, left in place pending a call). (3) evals/trajectories.py + checks.py survive on real importers but mostly serve the retired referee/ghostwrite arms — candidates for the evals-port follow-through.

---

## Phase 0 batch 2 landed (agent, 2026-07-28)

Test-only batch per the amended Phase 0 spec + E4/E5: rules-path goldens + the CHAR_DIVERGE set, gate-fault→repair, comprehension-repair, budget arcs, close phase, and three new CHAR_BUG tags. Zero production changes (monkeypatch-only; TEACHER_MODE=rules set as a config attr through the batch-1 factory's own monkeypatch); nothing committed; no server restart.

**Files:** `tests/test_characterization_rules_path.py` (3 tests; CHAR_DIVERGE inventory in its module docstring is the canonical list), `tests/test_characterization_ai_arcs.py` (5 tests), 7 new goldens under `tests/characterizations/` (`golden_rules_blank_open`, `golden_rules_blank_turn`, `golden_rules_due_turn`, `golden_gate_repair_turn`, `golden_comprehension_repair`, `golden_budget_arc`, `golden_close_phase`), `known_bugs.json` +3 entries. Batch-1 fixtures/format reused verbatim (`tutor_session_factory`, `_observe`, `check_golden`, note families, date normalization) — extended, not forked.

**CHAR_DIVERGE set (rules vs AI path, characterized AS-IS — E4 evidence):**
- **H1 (the E4 divergence, pinned precisely):** the rules call site sends RAW `self.history` and **never calls `config.history_for_model`** (call-count 0 across rules turns, wrapper-counted; request messages == raw history prefix), while the AI path routes through `config.history_for_model(self.history)` (call-count 1/turn, full history at call). Identical bytes while `HISTORY_TURNS=0`; the clip point itself is pinned (`turns=2` → last 2 pairs) so the latent divergence is on record: the moment `HISTORY_TURNS>0`, the AI path clips and the rules path does not. E4's written decision (delete vs stage-list-config with identical history policy) still owed — this batch characterizes only.
- **S1** no output gate / no repair loop: a bare unintroduced table key («mucho gusto» in acknowledge) ships ungated in ONE model call (the same reply class forces a repair round on the AI path — see the gate-repair golden).
- **S2** no mode runtime: no select_mode/guard chain, no mode notes/parts, ModeSessionState never ticks (learner_turn_index 0, scene_modeled empty).
- **S3** no signal classifier/shadow; note_learner without extra_signals; no comprehension-hold clears.
- **S4** no retrieval scheduler: two items due yesterday are neither offered (no DUE block) nor recorded (learner uses due «pan», ladder fields byte-identical to seed).
- **S5** no introduce router/ledger/first_seen: a glossed «hola (hello)» in the reply earns NO first_seen bit; budget never consumed.
- **S6** no phase layer: PhaseState frozen at index 0 / 0 / 0 forever (the due-seed plan sits parked on "retrieval"); no activity note, no task/close blocks.
- **S7** no debug ring-buffer capture.
- **S8** prompt assembly: sheet rides in SYSTEM blocks (`build_executor_system`) instead of the per-turn task tail; PlanCard `pedagogy_constraints` payload with no student_character_sheet/session_facts/hard_observations/visual sections.
- **S9** notes vocabulary: `plan_source=rules`, `plan:<phase>/<move>`, `plan_reason=`, `plan_gate_ok`; oddity: `pedagogy:diagnostic_open` + `phase=diagnostic` emitted on NON-open turns whenever the card's phase is diagnostic (an open-copy note mid-session).
- **S10** sheet writes: only `__init__` + `_finish` sites (no mid-turn introduce/first_seen/enqueue saves).
- **S11** memory writes via `note_plan_try(card.reason, …)` (probe keys like ask_how from "comm_open"; reason strings land in `asked`) instead of the AI path's mode-name + asked-topic registry writes.
- **S12** (code-shape, noted not pinned) rules always passes `self.tools` to tutor_turn; AI path gates tools on `config.SHEET_TOOLS`.

**AI-path arc goldens (CHAR_PIN unless tagged):**
1. *Gate-fault → repair* (`golden_gate_repair_turn`): scripted critical `gate:unscaffolded_new_item` (bare «mucho gusto»), pinned: `output_gate_fail:` + `output_gate_repaired` notes, second model call (3 requests total; repair request = same task tail + assistant raw + `(harness) OUTPUT GATE FAILED…` message carrying the FULL previous attempt), usage accumulated across both calls (240/120), final parts from the repaired attempt with `scaffold_saved {mucho gusto: gloss}` → durable first_seen write at the `_execute_ai_tutor` save site; the planned «hola» lapsed silently in both attempts (budget unconsumed, no note when the key is absent entirely).
2. *Comprehension repair* (`golden_comprehension_repair`, 2 turns): "What does contento mean?" → `meta_comprehension_stay_on_topic` hard break; phase clock FROZEN (index/turns_in_phase unchanged, frozen_turns 1, `phase_consumed=False`); repair targets carry the remembered try/model with require_same_topic/forbid_new_topic; **no irrelevant image** (decision `no_image_worthy_concept`, nothing attached — the incident class); await hold armed with TTL 1, then cleared EAGERLY by the learner's own Spanish next turn (phase resumes consuming; routing falls to `scene_goal:boat_meet_captain`).
3. *Budget arcs* (`golden_budget_arc`, open + 4 turns, one golden with per-turn views): introduce budget 2→1→0 (`hola` R-E then `buenos días` R-D, both honesty-lawful: confidence 0.0/status unknown), third plan REFUSED by R-G (no `introduce_planned` note; phase prefix says "introduce budget EXHAUSTED (0 left)"); §2.1a self-flag uptake budget: fires on turn 1 (`uptake_flagged:pan`), consecutive flag on turn 2 silently blocked (gap 1 < 3), recovers on turn 4 (gap 3 → `uptake_flagged:leche`); turn 4 also pins the new_input→task phase advance + first task-capable scene binding (`task_goal_offered:boat_likes`, no slots filled).
4. *Close phase* (`golden_close_phase`): phase ticked to close per the runbook allowance; pinned: `SESSION PHASE: CLOSE` prefix + the exact summary line built ONLY from tracked state ("new items introduced: hola; errors resolved: weather_hace; skills shown: greet, spanish_ok." — no task line when no task bound); `close_phase_offered`; the glossed farewell «adiós» is a scaffolded first exposure (first_seen, NOT an introduction); the close turn consumes the 1-turn budget and the clock walks off the plan end into "free".

**New CHAR_BUG tags (registry updated):**
- **CHAR-BUG-005** (batch-1 candidate VERIFIED) — the open turn marks EVERY open scene `scene_modeled` (known-open/placement/default-conversation decisions carry scene_ids = all open scenes; the mark loop adds them although the reply modeled none), killing the `_scene_needs_model` guard for the whole session. Load-bearing: several goldens reach the flavorable default fallthrough (introduce turns) only BECAUSE this guard is dead — a fix re-routes them.
- **CHAR-BUG-006** — pre-call fallback image decision treats scene model_lines as "what the tutor actually said": on a scene turn it decided «hola» (from boat_meet_captain's suggested lines) while the actual reply taught «bote»; two different concepts' miss notes on one turn, and with a warm cache the irrelevant image would attach (incident class on the conversation path, where require_relevant_to is not threaded).
- **CHAR-BUG-007** — asked-topic registry records pronouns as topic concepts: `_topic_nouns` feeds every association-table key (pronouns/question words/copulas included) to the concept extractor, so "¿Dónde estás tú?" registers `location:tu`, splitting semantically identical asks across registry keys and leaking pronoun keys into do_not_re_ask.

**Verification:** full suite green — **511 passed** (503 pre-batch + 8 new) + 17 subtests; `scripts/check_teacher_truncation.py` ok (14 files); goldens regenerate only via `CHAR_GOLDEN_UPDATE=1` (batch-1 law unchanged); nothing committed.

**E5 verdict: Phase 0 is DONE per the adjudicated bar.** open_session is characterized on three sheet states (blank/placement, known, due); N≥3 multi-turn user_turn paths run through `_execute_ai_tutor` under the fake client — placement + zero register, due elicit, introduce mark, gate repair, comprehension repair (2-turn), budget arc (4-turn), close — and the rules path is characterized with the unclipped-history divergence pinned as E4 evidence. Leaf tests remain necessary-but-insufficient as stated. Not blocking under E5 but honestly open for a batch-3-if-wanted: cf_recast/form_focus hard-break arcs (only the english-streak association break is golden-pinned), SHEET_TOOLS=1 tool round-trips, speech input_mode, and the model-call exception branch. Next owed decisions before Phase 4 touches these paths: **E4** (rules path: delete vs stage-list config with identical history policy) and the CHAR-BUG-005 fix's golden re-routing plan.

---

## Phase 1 batch 1 landed (agent, 2026-07-28)

The SessionState aggregate WITHOUT behavior change, per Grok amendment (a) (batch 1 = aggregate + reset table; the intentional deltas are batch 2). Nothing committed.

**New module `tutor/session_state.py`** — `@dataclass SessionState`, 19 fields in the old `__init__` construction order: the 5 stores (`pedagogy_memory` SessionMemory, `mode_state` ModeSessionState, `phase_state` PhaseState, `task_state` TaskState|None, `costs` SessionCostTracker) + 14 loose attributes from the census (`history`, `messages_for_ui`, `focus_panel`/`focus_key`/`focus_meta`/`focus_version`/`focus_lock`/`focus_inflight`, `image_warm_lock`/`image_warm_inflight`, `last_plan`, `last_mode_decision`, `debug_requests` deque, `progress_session_id`). `SessionState.fresh(sheet, *, source_label, pack_topics, due_count, blank)` replays the old inline construction bit-for-bit (phase plan = `PhaseState(build_phase_plan(...))` — pinned equal to `build_session_phase_state` output by test); `reset("full")` replays construction from the remembered fresh() inputs; any other kind raises ValueError until batch 2. `DEBUG_RING_SIZE` moved here (conv_session re-exports for existing importers). E2 note honored: the unused snapshot APIs were NOT touched — wire-or-delete is a batch-2 decision.

**conv_session migration (mechanical):** `__init__` builds `self.state = SessionState.fresh(...)` at the point the old block sat; **19 thin @property delegates** (`_state_delegate` factory) keep every historical attribute name reading/writing through the aggregate — zero call-site changes in conv_session/web_app/evals/tests. Delegates carry a compatibility escape: partial sessions built via `ConversationalSession.__new__` (tests/test_debug_requests.py) fall back to plain instance attributes, exactly pre-aggregate behavior. `reset_sheet`/`open_session`/web handler bodies are byte-unchanged — their store writes now land in the aggregate via the delegates (the "purely mechanical" routing), their per-store COVERAGE is unchanged and now pinned.

**Reset coverage census as code** — `SessionState.RESET_COVERAGE` (current / churn / batch2-plan / pending decisions per kind), characterized by `tests/test_session_state.py` so batch 2's fix must be a visible table diff. Current-state snapshot (19 fields total):

| kind | path | resets today |
|---|---|---|
| fresh | `__init__` → `SessionState.fresh` | ALL 19 |
| new-chat | web session_start resume branch + open_session | history, messages_for_ui, focus_panel, focus_key, costs (5) — churn: focus_meta/focus_version via same-response sheet_public repaint; pedagogy_memory seeded not reconstructed; mode/phase/task/debug ring leak |
| sheet-reset | `reset_sheet` | pedagogy_memory, mode_state, phase_state, task_state, focus_panel, focus_key, focus_meta, last_mode_decision, last_plan, debug_requests (cleared in place), history, messages_for_ui (12) — misses costs, focus_version/inflight, image_warm_inflight, progress_session_id |
| open-session | `open_session` on a live object | costs, history, messages_for_ui (3) — the review's corrected residual, pinned including seed-not-reconstruct |

The new-chat characterization runs the REAL endpoint (TestClient on a live isolated session, turn executor stubbed to isolate reset actions from turn effects) and pins the leak class itself: sentinel asked_topics/mode-state/phase-state/task-state all survive the "new chat".

**Verification:** suite **523 passed** (511 pre-batch + 12 new in tests/test_session_state.py) + 17 subtests, fully green. **Goldens untouched** — all 15 characterization tests pass against the exact Phase 0 files; `git status tests/characterizations/` shows only the pre-existing untracked dir (Phase 0 was never committed), every golden's mtime predates this batch (13:54/14:15/14:18 vs batch work from ~14:30), combined md5 of the JSONs `357e9c018713ba2126cd21157388b300`, `CHAR_GOLDEN_UPDATE` never set. `scripts/check_teacher_truncation.py` ok (14 files). `import tutor.web_app` ok; server restarted — `/api/health` stale_code **false** (version 20260728-143246 = disk), `/api/progress` with no session → clean 404 refusal.

**Batch 2 scope (declared deltas, do not land silently):** unified `reset(kind)` for new-chat/sheet-reset/open-session with the coverage gaps fixed (RESET_COVERAGE batch2 column becomes current, table + characterization updated in the same commit); the new-chat leak fix (intro budget/asked_topics/cooldowns/phase clock/task state must not survive a new chat); progress-ledger scope decision (no production reset/retraction caller today — fresh learner dedupe-suppression is product-visible); **E2** snapshot APIs wired for web resume or deleted; web_app call sites routed through the aggregate reset kinds.

---

## Phase 1 batch 2 landed (agent, 2026-07-28)

The DECLARED behavior deltas (Grok amendment (a): behavior-intent-declared, never silently "neutral"). Every delta is visible as a RESET_COVERAGE table diff + characterization-test diff in `tutor/session_state.py` / `tests/test_session_state.py`. Nothing committed.

**Delta 1 — unified `SessionState.reset(kind)`** (`tutor/session_state.py`): kinds `"new_chat"`, `"sheet_reset"`, `"open_session"` (hyphen spellings accepted; `"full"` kept from batch 1). `new_chat` and `sheet_reset` share ONE field coverage — `UNIFIED_RESET` = all 19 aggregate fields EXCEPT the two runtime locks (never swapped while potentially held) and `progress_session_id` (same live session object; learner scope rotates via the ledger epoch, not the session id). The phase plan is REBUILT from the CURRENT sheet (`due_count`/`blank` recomputed — a new chat on a learned sheet no longer replays construction-time inputs); the remembered fresh() args update so later resets replay the newest sheet. The kinds differ only at the caller: `ConversationalSession.reset_sheet` additionally wipes/rebuilds the sheet file and appends the ledger epoch. **This closes the new-chat leak**: intro budget, asked_topics, covered_concepts, mode cooldowns, `content_uptake_last_turn`, phase clock, task state, debug ring and per-chat costs no longer bleed between chats.
Call-site routing: `open_session()` now runs `state.reset("new_chat", sheet=…)` after its sheet reload (replacing the lone `costs.reset()`); `web_app.session_start`'s resume branch dropped its 4 inline partial clears (routes through `open_session`); `web_app` reset's fresh path keeps constructing a new object. `reset_sheet` routes through `state.reset("sheet_reset")` — the batch-1 twelve stores + the four misses (costs, focus_version, focus_inflight, image_warm_inflight); the debug ring is now RECONSTRUCTED (batch 1 cleared it in place — pin flipped, declared).

**Delta 2 — costs continuity RULING**: the per-chat `SessionCostTracker` resets on `new_chat` AND `sheet_reset` (the header shows THIS chat's spend). The on-disk cost ledger is append-only forever — never touched by any reset kind. Recorded in `RESET_COVERAGE[*]["ruling"]`.

**Delta 3 — progress-ledger learner epoch** (`tutor/progress_ledger.py`): `record_retraction` is NOT the tool (nothing false to retract — the previous learner's milestones were genuinely earned). Instead `reset_sheet` appends an append-only `kind="epoch"` mark (`record_epoch`; `key="learner"`, `polarity="epoch"` — a dedicated marker value: never in `up_keys`, never a regression; `record_milestone` REJECTS the kind and `record_retraction` cannot target it). `has_milestone`/`up_keys` (the dedupe gate feeding `_progress_note`/`ladder_crossings`/`sheet_crossings` `seen` sets) now only consider events strictly AFTER the latest epoch mark — a fresh learner re-mints every crossing. Display is epoch-UNSCOPED: pre-epoch days stay (history is real), the epoch row rides the day clusters as a visible boundary (`display_state="boundary"`, display "Fresh start — progress reset"; app.js renders unknown kinds safely via its `JOURNEY_KINDS` fallback — no frontend edit). Retraction filtering unaffected (mask still spans the whole history; `has_milestone("retracted", …)` still reads raw lines). Web `/api/session/reset` emits exactly ONE epoch per learner reset: the old session's redundant `reset_sheet()` call was dropped (its disk wipe was already duplicated by the handler's nuclear-wipe block; `close(persist_sheet=False)` already prevented stale re-saves).

**Delta 4 — E2 RULING: WIRED, not deleted** (well under one batch). `SessionState.snapshot()`/`from_snapshot()` compose the per-store APIs: `ModeSessionState.snapshot` + NEW `from_snapshot`, `SessionMemory.snapshot` + NEW `from_snapshot`, `PhaseState.snapshot/from_snapshot`, `TaskState.as_dict/from_dict`. The per-store `snapshot()` SHAPES are untouched (prompt/debug consumers pin them); the fields they omit (SessionMemory: last_learner, last_tutor_ack, image counters/cooldown; ModeSessionState: learner_turn_index, last_error_hit_turn) ride the aggregate as sibling keys and are restored by the stores' `from_snapshot`. Excluded BY DESIGN and documented: locks + inflight flags (runtime-only), debug ring (in-memory-only law), costs (per-chat header; the durable record is the cost ledger). No production caller yet BY DESIGN — this is the documented persistence surface for future server-restart resume, pinned by round-trip tests so it cannot rot into a third half-state.

**Delta 5 — `open_session` kind RULING**: DEPRECATED alias → `new_chat` semantics (`reset("open_session")` routes to `"new_chat"`); its old 3-store partial reset (costs/history/messages_for_ui — the review's corrected residual) is preserved in the table as `pre_batch2`.

**RESET_COVERAGE before → after** (19 fields; before = batch-1 census, now the table's `pre_batch2` audit column):

| kind | before (batch 1) | after (batch 2) |
|---|---|---|
| fresh | ALL 19 | ALL 19 (unchanged) |
| new-chat | history, messages_for_ui, focus_panel, focus_key, costs (5) — memory seeded-not-reconstructed; mode/phase/task/debug leaked | UNIFIED_RESET (16 = ALL − locks − progress_session_id); churn: focus_meta/focus_version repainted by the same response AFTER the reset |
| sheet-reset | 12 (missed costs, focus_version, focus_inflight, image_warm_inflight) + debug ring cleared in place | UNIFIED_RESET (16) + ledger epoch; debug ring reconstructed |
| open-session | costs, history, messages_for_ui (3) — the residual bug | UNIFIED_RESET (16) via the new_chat alias |

**Goldens regenerated: NONE.** All 15 characterization tests pass against the exact Phase 0 files (`CHAR_GOLDEN_UPDATE` never set; every file mtime predates this batch; `find tests/characterizations -newermt 2026-07-28T14:20 | wc -l` → 0). Why no pinned path changed: every golden calls `open_session` on a FRESHLY constructed session, where the unified reset reconstructs stores to the identical fresh values and rebuilds the phase plan from the same sheet content (deterministic) — bit-identical turns; goldens that mutate phase/memory state do so AFTER the open; epoch scoping with zero epoch events is the identity function; per-store `snapshot()` shapes untouched. CHAR-BUG-001…007 pins all stand.

**Leak-closure / delta test names** (`tests/test_session_state.py` unless noted): `TestUnifiedResetKinds::test_unified_kinds_reset_everything_except_kept` (6 param spellings), `::test_leak_class_closed_at_unit_level`, `::test_phase_plan_rebuilt_from_current_sheet`, `::test_kept_fields_are_locks_and_progress_id_only`; endpoint-level `TestCoverageCharacterization::test_new_chat_web_resume_path` (REAL `/api/session/start` resume on a live session, turn executor stubbed — seeds sentinel asked_topics/mode/phase/task + intro budget + cooldowns, asserts ALL fresh) plus `::test_sheet_reset_path` (full coverage + epoch row + reconstructed ring) and `::test_open_session_path` (alias semantics; memory reconstructed THEN seeded); epoch: `TestLearnerEpochThroughSession::test_plant_reset_replant_reminits` (plant → sheet_reset → same key plants again), `::test_display_keeps_both_sides_with_boundary`, and unit-level `tests/test_progress_ledger.py::TestLearnerEpoch` (4 tests: scope rotation/re-mint incl. latest-epoch-wins, display boundary, retraction-filtering unaffected, epoch not a milestone kind); E2: `TestSnapshotRoundTrip` (4 tests: round-trip equality, JSON-serializable, lossy-store fields via aggregate, excluded runtime fields rebuilt fresh).

**Verification**: suite **543 passed** + 17 subtests, fully green (523 pre-batch + 20 new: 16 in test_session_state.py, 4 in test_progress_ledger.py). `scripts/check_teacher_truncation.py` ok (14 files). Server restarted; `/api/health` stale_code **false** (version 20260728-145121 = disk); `/api/debug/requests` with no session → clean empty JSON; `/api/progress` with no session → clean 404. Live curl kept to health/read probes only — the start→reset→resume flow (including the no-leak assertion) runs through TestClient in the suite, so no model calls were made. Nothing committed.

---

## Phase 1.5 batch 1 landed (agent, 2026-07-28)

The encounter/schedule transition machine — SCHEDULE AXIS ONLY, per Grok's sizing row ("Schedule axis only first; ability axis; ledger projection pins") and the round-1 (b) replacement text as adjudicated. Write-path formalization, behavior-identical on every reachable production/test path; goldens byte-unchanged. Files: `tutor/retrieval_scheduler.py` (state model + `transition()` + wrapper refits), `tests/test_retrieval_scheduler.py` (+11 tests, new `TestScheduleStateMachine`). Nothing committed.

**The REAL state graph as derived from the code** (`item_state(entry)`, precedence order): `on_ladder` if `next_due` parses to a date; else `introduced` if `introduced_at` truthy; else `first_seen` if `first_seen` truthy; else `absent` (covers missing entries AND ability-only entries — the schedule axis is simply unstarted for them). Divergences from Grok's round-1 sketch (`absent → first_seen → introduced → on_ladder(...) → lapsed/re-queue on fail`), each with code evidence:

1. **`introduced` as a standalone state is NOT producible by this module's writers.** `mark_introduced` = enqueue + scaffold write, and `enqueue` writes `introduced_at` and `next_due` in the SAME `_write` — an introduction lands directly on_ladder (the task brief's "introduced+next_due = on_ladder immediately", verified). The state is kept in the model only for external/degenerate data — hand-edited sheets, or `normalize_sheet` coercing a garbage `next_due` to None while `introduced_at` survives (`character_sheet._normalize_schedule_entry`) — so such entries still have legal repair edges (`enqueue`/`outcome` → on_ladder, `retract` → back).
2. **"lapsed" is not a distinct state.** A failed outcome is the `on_ladder → on_ladder` self-loop with data reset (interval 1d, next_due tomorrow, successes 0) — Grok's "re-queue on fail" is an edge + data, not a state. Ladder position (interval_days, successive_successes, next_due) is DATA on `on_ladder`, per the binding text.
3. **`on_ladder` WITHOUT `introduced_at` is reachable:** `record_outcome_ex` on an absent key creates the honest-zero entry and writes only ladder fields (`_entry(create=True)`; no introduced_at). Production never does this (`_record_due_outcomes` only records for already-due items) but the API permits it — characterized and encoded as a legal edge, per the brief.
4. **`first_seen` is not strictly a stage passed through:** the FIELD is orthogonal durable evidence that persists into on_ladder (introduce keeps it) and through retraction (retract deliberately does not pop it); the STATE means the bit is the item's furthest schedule progress. Also `absent → on_ladder` direct edges exist (the grammar transfer-resolve `enqueue` path skips first_seen/introduced staging entirely — and note `enqueue` itself writes `introduced_at` when absent).

**Legal-edge table** (`_VIA_EDGES`, per-operation; `LEGAL_TRANSITIONS: dict[state, set[state]]` is the union view, kept in sync by an import-time check + `test_legal_transitions_union_matches_via_edges`):

| via (writer) | legal edges |
|---|---|
| `first_seen` (mark_first_seen) | absent→first_seen; first_seen→first_seen (no-op); introduced→introduced, on_ladder→on_ladder (data-add of the missing bit — see guard ruling below) |
| `introduce` (mark_introduced) | absent→on_ladder; first_seen→on_ladder — ONLY these; introduced/on_ladder source = double-introduce = **IllegalTransition** |
| `enqueue` | absent→on_ladder; first_seen→on_ladder; introduced→on_ladder; on_ladder→on_ladder (the legal re-queue) |
| `outcome` (record_outcome_ex) | any state →on_ladder (absent creates honest-zero entry, no introduced_at — characterized) |
| `retract` (retract_introduction) | on_ladder/introduced→first_seen (bit kept) or →absent (shell removed / ability-only entry kept); first_seen→first_seen; absent→absent (no-op) |

**`transition(sheet, key, kind, *, to_state, via, evidence, today, scaffold, success) -> (sheet, crossing)`** — validates the edge (IllegalTransition names via, from→to, kind:key, and the opaque evidence), performs ALL field writes through the existing allowlisted `_write` (retract is the one edge whose mutation is field REMOVAL, exactly the five fields the introduce wrote — first_seen kept, ability untouched, shell-deletion semantics verbatim), post-checks that the landed `item_state` equals the declared `to_state`, and returns the crossing info (from/to states + evidence; for via="outcome" also the exact interval-ladder telemetry). One declared divergence from the sketched signature: a `via` discriminator was added because `to_state` alone under-determines the write set (introduce/enqueue/outcome all land on_ladder with different field writes). Evidence is OPAQUE — quality validation stays with the gates, per the adjudication ("FSM rejects illegal writes, evidence gates stay"). The ledger stays a PROJECTION: `record_outcome_ex` still returns the identical 7-key telemetry dict (`key/kind/success/interval_before/interval_after/successes_before/successes_after` — shape pinned by test) consumed by `progress_ledger.ladder_crossings`; the transition log is the sheet fields.

**Wrapper refits (same external signatures, same field outcomes):** `mark_first_seen`, `mark_introduced`, `enqueue`, `record_outcome_ex` (and `record_outcome` via it), `retract_introduction` — all now thin wrappers over `transition()`. Unknown-kind ValueError messages unchanged. **Guard ruling (characterized first, per the brief):** the `is_introduced`/`has_first_seen` skip before `mark_first_seen` STAYS at the conv_session call site (L2160–2163); the writer itself has ALWAYS allowed the self-loop (it has no introduced-guard) and only adds the missing bit / no-ops on an existing one — moving the guard in would have changed function-level behavior, so it did not move. **The one new function-level rejection:** double-introduce now raises IllegalTransition where the bare function would previously have silently re-queued (next_due reset to tomorrow, interval 1). No production path can reach it (introduce_router filters `is_introduced` keys at plan time; `mark_introduced_if_visible` only fires on a planned key) and no test exercised it — suite + goldens confirm zero behavioral delta. Retraction encoded per its actual semantics: pops exactly the five introduce-written fields, keeps `first_seen`, deletes the honest-zero shell (status unknown/empty + confidence 0.0 + nothing else) — i.e. `introduced/on_ladder → first_seen | absent`, not always "absent-shell".

**Illegal-transition tests added** (`tests/test_retrieval_scheduler.py::TestScheduleStateMachine`, 11): `test_item_state_classification`, `test_double_introduce_raises`, `test_introduce_from_first_seen_is_legal`, `test_first_seen_after_introduced_no_raise_callsite_guard_stays`, `test_outcome_on_absent_key_creates_entry_without_introduced_at`, `test_retract_edges_back`, `test_enqueue_requeue_self_loop_is_legal`, `test_cross_axis_write_still_raises_via_allowlist`, `test_transition_rejects_unknown_via_state_kind`, `test_illegal_transition_message_carries_evidence`, `test_legal_transitions_union_matches_via_edges`. All pre-existing honesty-law tests (allowlist, tool-delta rejection, ability-fields-restored) pass untouched.

**Verification:** suite **554 passed** + 17 subtests, fully green (543 pre-batch + 11 new). Goldens byte-unchanged: combined md5 of `tests/characterizations/*.json` = `357e9c018713ba2126cd21157388b300` before AND after (the exact Phase 1 batch 1 figure); `CHAR_GOLDEN_UPDATE` never set. `scripts/check_teacher_truncation.py` ok (14 files). `import tutor.web_app` ok; pure refactor with byte-identical goldens — no server restart needed (nothing to prove live). Only `tutor/retrieval_scheduler.py` + `tests/test_retrieval_scheduler.py` touched. Nothing committed.

**Batch 2 scope (ability axis, machine B):** formalize `character_sheet` `_bump_status` + the KNOWN gate as explicit transitions `unknown → fragile → emerging → known` (confidence bands + solid_uses gates as edge conditions), same pattern — central transition function, illegal cross-axis writes from the scheduler side already rejected here, sheet-side writer refits behavior-identical, KNOWN-gate evidence stays a gate not an enum. Then the ledger projection pins: `ladder_crossings`/`sheet_crossings`/`_progress_note` consume machine crossings (projection law — append-only + retraction untouched), with the crossing shapes pinned by test before any consumer migrates.

---

## Phase 1.5 batch 2 landed (agent, 2026-07-28)

The ability-axis machine (machine B) + the ledger projection pins, per the adjudicated round-1 (b) replacement and the batch-1 derive-from-code discipline. Write-path formalization, behavior-identical on every reachable path; goldens byte-unchanged. Files: `tutor/character_sheet.py` (machine B + writer refits), `tests/test_character_sheet.py` (+15, `TestAbilityStateMachine`), `tests/test_progress_ledger.py` (+8, `TestProjectionContract`). Nothing committed.

**The REAL band graph as derived from the code** (`ability_band(entry)`: strict `STATUSES` vocabulary; missing entry / missing status / out-of-vocabulary string → `unknown` — the ability axis has no "absent"; machine A's honest-zero shells land here). Divergences from Grok's round-1 sketch (`unknown/fragile/emerging/known with confidence + solid_uses gates`), each with code evidence:

1. **The vocabulary is FIVE bands, not four: `blocked` exists** (`STATUSES`, tool schema enum) but is **not producible by any code writer** — only a tool/model delta can enter it; `_bump_status` ESCAPES it (success → emerging, fail → fragile/unknown). Encoded: no `(*, blocked)` edge on the `bump` via.
2. **`fragile` is real** (not sketch-only) — but the sub-known bands are **evidence-direction SIBLINGS, not ordered rungs**: `_bump_status` on success goes `unknown → emerging` DIRECTLY (never through fragile); `fragile` is entered only on FAILED evidence at conf ≥ 0.25 (below that a failure lands on `unknown`), or by tool claim. The sketch's linear ladder does not exist in code.
3. **DOWN edges are everywhere**: `known → emerging` (`_cap_turn_confidence` re-gate demotion — including on legacy known-with-0-uses entries any time they pass through `process_turn`), `known → fragile` / `known → unknown` (`_bump_status` failure), and `known → known` survives failure while conf/uses hold the gate (conf 1.0 − 0.105 fail ≥ 0.80 stays known).
4. **The UNION graph is COMPLETE** — every band reaches every band (`ABILITY_TRANSITIONS`, import-time-synced to `_ABILITY_VIA_EDGES` like batch 1). Documented finding, not an oversight: today's ability axis has no illegal band edge at the union level; the protections are **gate arithmetic** (per-turn caps + known gate), exactly as the adjudication predicted ("an FSM rejects illegal writes; evidence gates stay"). The per-via tables are where the machine has teeth: `cap` = self-loops + the ONE demotion edge `known → emerging`; `normalize` = self-loops only; `bump` cannot mint `blocked`; `tool_merge`/`delta_lexicon` are edge-complete BY CHARACTERIZATION (see CHAR-BUGs).
5. **The known gate stays in the writers, not the machine** (per the batch brief): a machine-level `known ⇒ solid_uses ≥ 2` guard would be WRONG — legacy/seeded sheets legally hold known with `solid_uses` 0 and `_clamp_skill_entry` preserves that claim (prev-known + conf ≥ gate keeps known without uses; pinned by `test_clamp_keeps_legacy_known_without_uses`).
6. **Signature divergence** (mirror of batch 1's added `via`): the sketched `ability_transition(entry, *, evidence, via)` under-determines the edge — the pre-write entry is needed for the from-band, so the call is `ability_transition(pre, staged, *, via, evidence)`; it validates and returns `staged` UNCHANGED (byte-identical outputs; the writers stay the places that compute field values).

**Legal-edge table** (`_ABILITY_VIA_EDGES`, per-operation; `ABILITY_TRANSITIONS` union kept in sync by import-time check + test):

| via (writer) | legal edges |
|---|---|
| `bump` (_bump_status: apply_rule_updates sites + note_error_pattern grammar mirror) | any band → {unknown, emerging, fragile, known}; blocked escapable, never enterable |
| `tool_merge` (_clamp_skill_entry: tool/model skills+grammar merge) | edge-complete (any → any of 5); known gate in-writer; CHAR-BUG-008 |
| `delta_lexicon` (apply_delta lexicon dict merge + bare-string status) | edge-complete; NO conf cap / known gate at this site; CHAR-BUG-009 |
| `cap` (_cap_turn_confidence: per-turn ceiling + re-gate) | self-loops + `known → emerging` (the only genuinely narrow via) |
| `normalize` (normalize_sheet coercion of AI full rewrites) | self-loops only (an invalid status already IS band unknown) |

**Cross-axis guard (BUILD 4 mirror, both directions now enforced):** `ability_transition` REJECTS any move of a `SCHEDULE_FIELDS` member — added, removed, or changed vs the pre-write entry (`ValueError` "honesty law"), the mirror image of machine A's `_write` allowlist restoring ability fields. **Single source:** `character_sheet` now imports `SCHEDULE_FIELDS` from `retrieval_scheduler` (stdlib-only, so the import can never cycle) and derives `SCHEDULE_ENTRY_FIELDS` from it; `ABILITY_FIELDS` mirrors `retrieval_scheduler._PROTECTED_FIELDS` and is pinned equal by TEST, not import (the scheduler stays stdlib-pure). Symmetry test: `test_cross_axis_symmetry_both_directions` shows both guards raising in one place.

**Writer refits (same signatures, same outcomes; all six status-band write sites route through the machine):** `_bump_status` (return path → via="bump"), `_clamp_skill_entry` (return path → via="tool_merge"), `apply_delta` lexicon dict branch + lexicon bare-string branch (via="delta_lexicon"), `_cap_turn_confidence` (per-entry pre-snapshot + validate, in-place mutation retained; via="cap"), `normalize_sheet` skills + grammar coercion loops (via="normalize"). Out-of-machine and documented: `can_dos.migrate_skills` (load-time legacy migration — routing it would cycle the import graph; bands land as data and `normalize`/`load` coercion covers invalid statuses), the honest-zero initializations (`retrieval_scheduler._entry`, `apply_rule_updates`' default lexicon entry — band-unknown initializations, not transitions), and `process_turn`'s revised_sheet WHOLESALE replacement (the AI full-rewrite has no per-entry merge to route; its missing +0.25 clamp was already documented in `_cap_turn_confidence`'s docstring and docs/reviews-system-overview.md — unchanged this batch). New function-level rejections, all production-unreachable (mirror of batch 1's double-introduce ruling): a schedule-field move through `_clamp_skill_entry`/the lexicon merge now raises where it would have silently merged — `apply_delta` strips `SCHEDULE_ENTRY_FIELDS` before both calls, so no reachable path changes; suite + byte-identical goldens confirm.

**Tool band-jump verdict (characterized FIRST, per the brief): the tool CAN jump bands today — PARTIALLY guarded.** `_cap_turn_confidence` is NOT a complete guard:
- What holds: skills/grammar `unknown` at conf 0 cannot reach known in one call (the +0.25 conf cap in `_clamp_skill_entry` is the real transition guard: claim `known 0.9` lands `emerging 0.25`); a lexicon known-claim WITHOUT a solid_uses claim is demoted by the cap re-gate (to emerging — though its conf 1.0 survives, ceiling = staged).
- **CHAR-BUG-008** — skills/grammar: the `solid_uses` claim is TRUSTED (`_clamp_skill_entry`: `uses = max(uses, incoming["solid_uses"])`) and `_cap_turn_confidence`'s ceilings use the post-delta STAGED values, so ONE tool call at prev conf ≥ 0.55 crosses `emerging → known` with zero code-observed uses (verified: prev emerging 0.6 + claim `{known, 0.85, solid_uses: 2}` → known 0.85).
- **CHAR-BUG-009** — lexicon: `apply_delta`'s lexicon branch skips `_clamp_skill_entry` entirely (no per-turn conf cap, no known gate — only a [0,1] clamp), so ONE tool call mints `absent → known at conf 1.0` when solid_uses is claimed (verified end-to-end through `process_turn`).
- Ruling per the brief: **legal-but-logged this batch** — the edges are encoded as legal (edge-complete vias), the behavior is pinned by `test_tool_band_jump_characterized_char_bug_008_009`, and a future fix PR (gate the solid_uses claim / route lexicon through `_clamp_skill_entry`) must update those pins + this entry together. **Registry note:** `tests/characterizations/known_bugs.json` was NOT updated — it sits inside this batch's byte-unchanged golden pin (md5 gate covers `*.json`); this runbook entry is the canonical CHAR-BUG record until the fix PR (or a batch allowed to touch the registry) lands.

**Milestone ↔ transition/crossing mapping table** (pinned by `TestProjectionContract`; the ledger PROJECTS these, never writes machine fields):

| milestone kind | named source | pin |
|---|---|---|
| `planted` | machine A `via="introduce"` (absent/first_seen → on_ladder), emitted at conv_session's `introduced:` site | `test_planted_maps_to_introduce_transition` (+ ability axis untouched: introduce mints NO sheet_crossing) |
| `taking_root` | machine A `via="outcome"` data: interval crosses `TAKING_ROOT_DAYS` (3) | `test_ladder_kinds_map_to_outcome_crossings` |
| `rooted` | machine A `via="outcome"` data: interval reaches `ROOTED_DAYS` = `INTERVAL_CAP_DAYS` (14, import-pinned) | same |
| `regression` | machine A `via="outcome"` fail from interval ≥ 3 (polarity=down) | same |
| `error_recovered` | character_sheet healthy gate: `count == 0 AND resolved_streak >= ERROR_PATTERN_HEALTHY_STREAK` (its own gate, neither band machine) | `test_error_recovered_maps_to_healthy_gate` |
| `can_do_emerging` | machine B confidence crossing: `EMERGING_CONF == character_sheet.EMERGING_MIN_CONF` (0.55, now a NAMED band boundary in `_bump_status`) with a positive band | `test_kind_vocabulary_matches_mapping_table` |
| `can_do_known` | machine B band edge `* → known` — proven EQUIVALENT to `ability_band` crossing over an 8×8 status matrix incl. out-of-vocabulary strings | `test_can_do_known_is_the_band_edge` |
| `task_complete` | task_runtime machine verdict (neither A nor B) | vocabulary pin |
| `retracted` | honesty correction; pairs with machine A `via="retract"` at the incident-repair path | existing `TestRetraction` + vocabulary pin |
| `epoch` (marker, not in KINDS) | session `sheet_reset` boundary (Phase 1 batch 2 delta 3) — not a machine transition | existing `TestLearnerEpoch` |

**Projection-contract pins (grep proof + tests):** `record_milestone`/`record_epoch`/`record_retraction` take no sheet parameter (signature-pinned) and a full record cycle leaves a live sheet deep-equal; `sheet_crossings`/`ladder_crossings`/`live_state_supports`/`build_progress_payload` never mutate their inputs; `progress_ledger` holds NO reference to any machine writer (namespace + import-line pin over `save_sheet`/`mark_introduced`/`enqueue`/`record_outcome*`/`retract_introduction`/`transition`/`ability_transition`/`apply_*`/`_bump_status`/`_write` — grep confirms its only cross-module imports are read-only: `INTERVAL_CAP_DAYS`, `due_items`, `ERROR_PATTERN_HEALTHY_STREAK`, `compute_progress_score`, `CAN_DOS`, `load_scenes`, `config`).

**Verification:** suite **577 passed** + 17 subtests, fully green (554 pre-batch + 15 machine-B + 8 projection). Goldens byte-unchanged: `md5 -q tests/characterizations/*.json | md5` = `357e9c018713ba2126cd21157388b300` before AND after (the exact Phase 1 batch 1 figure; `CHAR_GOLDEN_UPDATE` never set; `known_bugs.json` untouched — see registry note). `scripts/check_teacher_truncation.py` ok (14 files). `import tutor.web_app` ok; pure refactor + tests with byte-identical goldens — no server restart needed. Only `tutor/character_sheet.py`, `tests/test_character_sheet.py`, `tests/test_progress_ledger.py` touched. Nothing committed.

**Phase 1.5 verdict: DONE at batch 2** — Grok's sizing row allotted 2–3 batches for "schedule axis; ability axis; ledger projection pins"; batch 1 delivered the schedule axis, batch 2 the ability axis + projection pins. No batch 3 needed. Remaining follow-ups are FIX PRs, not Phase 1.5 batches: (1) the CHAR-BUG-008/009 tool band-jump fix (+ registry entries + pin updates in one PR), (2) the AI full-rewrite +0.25 clamp gap (pre-existing, documented in `_cap_turn_confidence`), (3) optional: `migrate_skills` machine routing if can_dos/character_sheet ever untangle. Phase 4's recorder stage should consume `ability_transition`/machine-A `transition` crossings directly when the pipeline lands.

---

## Phase 2 landed (agent, 2026-07-28)

`tutor/textnorm.py` — the one home for Spanish text normalization (map move 3), per the adjudicated round-1 plan and Grok's Phase 2 amendment (three NAMED policies, one module, never a merged function). Pure refactor, behavior-identical on every probe and every test; goldens byte-unchanged. Files: `tutor/textnorm.py` (new, stdlib only), 8 caller migrations, `tests/test_textnorm_contract.py` (new, the permanent contract). Nothing committed.

**Policy inventory shipped (docstrings state semantics + users; the module docstring carries the merge-refusal law):**

| policy | semantics (verbatim from the historical implementation) | replaces | users |
|---|---|---|---|
| `fold_lexical` | lower; SIX vowels á é í ó ú ü → plain; KEEPS ñ; keeps spaces/punctuation | `session_memory._deaccent` | session_memory (asked-topic registry keys), output_gate (probe-loop due-exemption — the private-import kill) |
| `fold_asset_key` | strip+lower; FIVE vowels (NOT ü) + ñ→n; space→_; drops …/.; strips leading el_/la_ (el_ first) | `teach_assets._norm_key` | teach_assets only (image cache keys — change = orphaned cache) |
| `fold_id` | lower; space AND hyphen → _; FIVE vowels (NOT ü) + ñ→n; no strip | the fold step inside `character_sheet.normalize_error_pattern_id` | character_sheet only (error-pattern ids in on-disk sheets) |
| `fold_prose` | lower+strip; NFD; drop ALL combining marks (ñ→n, ü→u, ç→c) + ¿¡?.!,;:"'; collapse whitespace | `character_sheet.fold` + `_SURFACE_NOISE` | character_sheet only (error-pattern detect/resolve + affect/receptive regex scans) |

**fold_prose DECISION: shipped as the FOURTH named policy in textnorm**, not kept local. Its semantics are unique to one caller, but "one home for every fold" wins: leaving it in character_sheet preserves a fifth fold site for future drift, and textnorm's module docstring is where the incompatible-semantics warning lives. character_sheet imports it as the historical local name (`from .textnorm import fold_id, fold_prose as fold`) — zero call-site churn, and the contract test pins `character_sheet.fold IS textnorm.fold_prose`.

**Boundary-matcher family: TWO named variants, not one** (characterization first, per the brief). `phrase_present` proved EXACTLY equivalent to `bool(_key_match)` on all 57 probe pairs (single-word paths compile the identical regex; both split/rejoin the needle) — so the family is `word_present` (observe's semantics verbatim: whole-needle escape) + `phrase_match` (gate's semantics verbatim: Match object for the overlap filter) + `phrase_present` (= bool(phrase_match), task_runtime's name) + `phrase_body` (exposed so `gloss_after_key` composes its key+gloss regex from the same escaped body). One letter class `SPANISH_LETTERS = "a-záéíóúüñ"` replaces all five copies (observe/task_runtime/output_gate/turn_morph + tutor_response's inline `_CONCEPT_TOKEN` class; session_memory's inline `_WHAT_VERB_RE` class migrated too, same bytes).

**Divergences found between the three matchers (pinned as named-variant contract, NOT fixed — CHAR_BUG candidates):**
- **CHAR_BUG candidate (MWU whitespace)**: `word_present` escapes the needle WHOLE, so a multiword needle only matches its own literal spacing — «cómo estás» misses «cómo  estás» / a newline between the words — while `phrase_match`/`phrase_present` join words with `\s+`. Latent cross-caller inconsistency: conv_session.mark_introduced_if_visible and introduce_router scan MWU table keys through `word_present` while output_gate's unscaffolded-new-item scan matches THE SAME keys through `phrase_match` — a reply wrapping «buenos días» across a line break is VISIBLE to the gate but NOT introduce-marked (silent-lapse vector, the exact "two callers that should share semantics but don't" class the brief predicted). 4 probe pairs pin it.
- **CHAR_BUG candidate (empty needle)**: `word_present("", text)` degenerates to a bare boundary pattern that CAN match (`word_present("", "hola !")` → True, `word_present("", "")` → True); the phrase family returns falsy. No production caller passes an empty needle today (keys are non-empty), but the trap is real and now documented in the docstring. 4+1 probe pairs pin it (incl. whitespace-only needle).
- Both divergences are pinned by `test_named_variant_divergences` with the Phase 0 law attached: a unification is a bugfix PR that updates the pins, never a silent flip. `tests/characterizations/known_bugs.json` NOT touched (it sits inside the golden md5 pin — same registry ruling as Phase 1.5 batch 2); this entry is the canonical record.

**Differential characterization (BUILD 3):** probe corpus of **401 probes across 9 families** — 61 fold strings (accents/ñ/ü/case/MWU/el-la/punctuation/whitespace/ellipsis/NFD-only diacritics ç ô ö ï), 27 error-pattern ids end-to-end through `normalize_error_pattern_id` (catalog hits, aliases, fuzzy, tool-invented names), 57 (needle,text) boundary pairs (plural tolerance, accent non-folding, ñ/ü boundaries, digit/underscore adjacency, MWU whitespace, empty needles) × 3 matcher families (word/phrase bool + phrase SPANS — the gate's overlap filter consumes .start()/.end()), 14 gloss_after_key pairs (regex recomposition insurance), 27+61 fold_id inputs (old fold lines replicated verbatim as the source). Captured from the PRE-migration implementations, then the migrated tree re-probed: **401/401 byte-identical**. The corpus + expected outputs are frozen INLINE in `tests/test_textnorm_contract.py` (16 tests) — deliberately not under `tests/characterizations/*.json`, which the golden md5 gate covers. Caller-binding tests assert IDENTITY (`observe.word_present IS textnorm.word_present` etc.), so a re-added local copy fails the contract even if byte-equal.

**Per-caller migrations (all 8; behavior-identical, suite-verified):**

| module | change |
|---|---|
| observe | def word_present + `_ES_LETTERS` die; re-export façade (`from .textnorm import SPANISH_LETTERS as _ES_LETTERS, word_present`) — conv_session/introduce_router/modes/tests keep importing from observe; `_ES_TOKEN` composes the shared class |
| task_runtime | def phrase_present + `_ES_LETTERS` + `import re` + the observe import die; re-export façade (tests import from task_runtime) |
| output_gate | `_ES_BOUND`/`_key_body`/`_key_match` die; 3 call sites → `phrase_match`; `gloss_after_key` recomposes over `phrase_body` + `SPANISH_LETTERS` (byte-identical pattern); **the private `session_memory._deaccent` import (L662) is DEAD** — due-exemption compares through public `fold_lexical` |
| turn_morph | `_ES` literal dies → `from .textnorm import SPANISH_LETTERS as _ES` |
| tutor_response | `_CONCEPT_TOKEN` inline class → composed from `SPANISH_LETTERS` (same bytes) |
| session_memory | def `_deaccent` dies → `fold_lexical` at all 4 sites; `_WHAT_VERB_RE` class shared; lazy word_present imports → textnorm |
| teach_assets | def `_norm_key` dies → `from .textnorm import fold_asset_key as _norm_key` (~15 call sites unchanged); lazy word_present import → textnorm |
| character_sheet | def `fold` + `_SURFACE_NOISE` + `import unicodedata` die → `fold_prose as fold`; normalize_error_pattern_id's fold lines → `fold_id(pid)` (catalog/alias/fuzzy logic untouched, pinned end-to-end) |

**Verification:** suite **593 passed** + 17 subtests, fully green (577 pre-batch + 16 contract). Goldens byte-unchanged: `md5 -q tests/characterizations/*.json | md5` = **`357e9c018713ba2126cd21157388b300`** before AND after (the exact Phase 1 figure; `CHAR_GOLDEN_UPDATE` never set). `scripts/check_teacher_truncation.py` ok (14 files). `import tutor.web_app` ok; pure refactor with byte-identical goldens — no server restart needed. Touched: `tutor/textnorm.py` (new) + the 8 modules above + `tests/test_textnorm_contract.py` (new). Nothing committed.

**Follow-ups (not this batch):** (1) the two CHAR_BUG candidates above — the MWU-whitespace introduce/gate split is the load-bearing one (silent-lapse vector); a fix PR unifies the scan semantics AND updates the named-variant pins + this entry. (2) `output_gate._ALPHA_TOKEN_RE` and observe's `_ES_TOKEN` are the same uppercase-inclusive token class spelled twice — outside the adjudicated ×5 inventory, left in place; fold into textnorm (e.g. `SPANISH_ALPHA`) opportunistically when Phase 4 touches those files. (3) Phase 3 (typed turn events) unblocked; nothing in this batch changes the note-string bus.

---

## Phase 3 batch 1 landed (agent, 2026-07-28)

The note-prefix catalog (E6, BINDING) + typed turn events with dual-emit, per the adjudicated Phase 3 sizing row ("Enum/dataclass + dual render; then gate/evals migrate off prefixes"). Pure refactor, behavior-identical; goldens byte-unchanged. Files: `tutor/turn_events.py` (new, stdlib-only: catalog + enum + dataclass + render/classify + `TurnEventLog`), `tutor/conv_session.py` (dual-emit wiring + the re-parse kills), `tests/test_turn_events.py` (new, 78 contract tests), `tests/test_session_fixes.py` (one source-shape assertion updated to the event-kind marker — the rendered legacy string is now pinned in the render table instead of as an f-string literal). Nothing committed.

**The real prefix count: 62 catalogued families, not ~40** (68 distinct note constants once the seven fixed `pedagogy:*` values are counted individually — the map's "~40" undercounted by ~22). Every family is a `TurnEventKind` member with a `NoteSpec` row in `NOTE_CATALOG`: match string (exact vs prefix), payload shape, emitter site(s), consumers, stability class, golden coverage. Emitter split: 51 families minted structured at the conv_session sites (AI + rules + legacy paths), 11 minted in leaf modules (`character_sheet.process_turn`/`summarize_sheet_changes` change notes ×10, `pedagogy_contract` `pedagogy:*` ×1 family) and ABSORBED into typed events at the conv_session bus boundary (`TurnEventLog.absorb`, catalog-driven classification, byte-preserving — batch 2 pushes typing into those emitters when their signatures next open).

**Stability classes (measured, published):**
- **eval-pinned (14):** `mode=`, `activity=`, `uptake_flagged:`, `due_elicit_offered:`, `progress_milestone:`, `introduce_planned:`, `task_goal_offered:`, `task_slot_filled:`, and the six `output_gate*` kinds — parsed by 8 checker functions in evals/conv_checks.py over 10 note prefixes plus the joined-notes substring scans ("output_gate", "missing_recast" — the latter matches fault PAYLOADS, catalogued as such).
- **ui-pinned (2, a class the brief did not predict):** `rules_backup` / `tool_update` — web_static/app.js `setNotes` styles the notes line WARN on rules_backup-without-tool_update membership.
- **log-only (46):** session .jsonl (`state.notes` + `extra.sheet_notes`), web notes line, debug ring.
- **debug-only: NONE exist** — the ring carries the same list the logs get; no kind is minted for the ring alone.
- Golden coverage flag per row: 37 of 62 families are byte-pinned inside the Phase 0 goldens today.
- Off-bus vocabularies documented (not catalogued): the gate's internal `gate:*`/`tl_ratio=` notes travel in `parts["output_gate"]` (and as payload inside `output_gate_*` bus notes); app.js mints `fresh_learner`/`reset_may_have_failed` client-side.

**Seam decision: TurnResult gains the `events` field (not SessionState).** Checked the pins first, per the brief: the goldens pin `parts_keys` (sorted parts keys), note families, and named observation fields — NOT the TurnResult dataclass field census — and `to_dict()` is an explicit key list, so the new field is invisible to every JSON surface (web `**turn.to_dict()`, logs, debug ring, goldens). The SessionState alternative would have broken the aggregate's own pins (the 19-field RESET_COVERAGE census tests). During the turn the log lives as a session-side transient (`session.__dict__["_turn_events"]`, reset by `begin_turn_log` at the top of each executor incl. both legacy paths; `session_event_log` accessor is `__dict__`-based so partial-session tests and SimpleNamespace fakes keep working); `_finish` aliases `result.events = log.events`, so post-`_finish` emitters (introduce ledger, asked-topic, tail) land in the same list. `to_dict()` deliberately unchanged — the timeline gets an exposure surface in batch 2.

**Dual-emit contract as shipped:** every note string in `result.notes` is the `render()` projection of exactly one typed event (multiset equality contract-tested per turn on live golden scenarios). Event `seq` is monotonic in EMISSION order = true chronology; the legacy list keeps its historical ASSEMBLY order — **CHAR-BUG-003 (non-chronological notes) is deliberately preserved this batch** (`mode=`/`mode_reason=` are minted at stage "select" but their strings still render in the tail block at the legacy position; pre-call scheduler notes still assemble after the gate verdict). Stages: schedule/select/instruct/image/gate/sheet/contract/record/tail/plan.

**Re-parse sites killed (3 — the map's "decision.reason string-parsed by prefix; notes re-parsed" cluster in conv_session):**
1. **Guard-6 covered-concept** (`decision.reason.startswith("new_noun:")` + split mid-pipeline) → reads `MODE_REASON.payload["guard6_concept"]`, parsed ONCE at the event boundary (`turn_events._guard6_concept`); exact-equivalence (empty-tail included) contract-tested.
2. **Gate-context `retrieval_failed_keys`** (`n.split(":",1)[1] for n in sched_notes if n.startswith("due_outcome_fail:")`) → `{e.key for e in ev.find(DUE_OUTCOME_FAIL)}`; equivalence against the old string-split asserted on every live-scenario turn.
3. **Introduce-ledger branch** (`intro_note.startswith("introduced:")`) → new structured `introduce_outcome(sheet, plan, reply, teach_images) -> (sheet, status, key)` with status in ("introduced","lapsed",None); `mark_introduced_if_visible` kept as a thin string-rendering wrapper (its many direct tests untouched, strings now single-sourced from the render table).

**Contract tests** (`tests/test_turn_events.py`, 78): `test_catalog_covers_every_kind_and_only_kinds`, `test_render_table_covers_every_kind`, `test_catalog_count_published_number` (=62), `test_stability_classes_are_the_measured_vocabulary`, `test_no_catalog_match_shadows_another` (longest-prefix-first law), `test_round_trip_every_kind_classify_then_render` (70 representative REAL legacy strings; every kind covered), `test_emit_renders_the_legacy_string`, `test_absorb_preserves_bytes_and_classifies` (+ LEGACY_UNCATALOGUED sentinel behavior), `test_mode_reason_guard6_payload_is_the_boundary_parse`, `test_seq_monotonic_and_stage_tagged`, live-integrator scenarios `test_blank_session_dual_emit` / `test_due_session_success_and_fail_paths` (due success AND deterministic meta-comprehension fail) / `test_introduce_session_typed_status_matches_strings` / `test_rules_path_dual_emit` — each asserting the three per-turn laws (seq monotone, catalog completeness incl. "no uncatalogued note reached the bus", notes == rendered-event multiset) plus old-vs-new re-parse equivalence — `test_turn_result_json_surface_unchanged`, `test_wrapper_keeps_string_contract`, and 62 parametrized `test_catalog_rows_have_all_e6_columns`.

**Verification:** suite **671 passed** + 17 subtests, fully green (593 pre-batch + 78 new). Goldens byte-unchanged: `md5 -q tests/characterizations/*.json | md5` = **`357e9c018713ba2126cd21157388b300`** before AND after (the exact Phase 1 figure; `CHAR_GOLDEN_UPDATE` never set). `scripts/check_teacher_truncation.py` ok (14 files). `import tutor.web_app` ok; pure refactor with byte-identical goldens — no server restart needed. Touched: `tutor/turn_events.py` (new), `tutor/conv_session.py`, `tests/test_turn_events.py` (new), `tests/test_session_fixes.py` (one assertion). Nothing committed.

**Batch 2 scope (owed):** (1) evals/conv_checks.py migrates off the 10 parsed prefixes — checkers consume the typed event list (exposed via a serialized `events` surface: `to_dict()` gains the timeline, run_conv_smoke records it); (2) gate context consumes events directly (GateContext slice per E3 rides Phase 4, but the `retrieval_failed_keys`/asked-topic inputs can take typed events now); (3) **the CHAR-BUG-003 chronology fix PR rides batch 2**: `result.notes` becomes the seq-ordered projection (`[render(e) for e in events]`), with golden regeneration JUSTIFIED and the known_bugs.json entry updated in the same PR (the registry sits inside the golden md5 pin — untouched this batch by the standing registry ruling); (4) push typed emission into the leaf emitters (character_sheet/pedagogy_contract/self_flag_uptake_block return events, absorb boundary retires); (5) candidates while there: CHAR-BUG-004's duplicate image-miss notes become one event with two projections — fix rides the chronology PR.

---

## Phase 3 batch 2 landed (agent, 2026-07-28)

The adjudicated batch-2 scope in full: eval checkers onto typed events, gate context event-sourced and pinned, the **CHAR-BUG-003 chronology fix** (declared bugfix riding this batch) with justified golden regeneration, the leaf-emitter typing push-down with an absorb-zero proof, and the ui-pinned note guard. Files: `evals/conv_checks.py`, `evals/run_conv_smoke.py`, `tutor/conv_session.py`, `tutor/character_sheet.py`, `tutor/pedagogy_contract.py`, `tutor/turn_events.py` (docs/catalog columns only), `tests/test_turn_events.py`, `tests/test_conv_checks_events.py` (new), `tests/test_characterization_ai_path.py`, `tests/test_uptake_flag.py`, `tests/characterizations/` (14 goldens regenerated + `known_bugs.json`). Nothing committed.

**(1) Eval checkers migrated onto events.** `run_conv_smoke._push` now records the serialized TurnEvent timeline per turn (`turn["events"]`, kind/key/payload/seq/stage), and `TurnResult.to_dict()` gains the `events` key (the batch-1 "timeline exposure surface" owed to batch 2 — web `/api` responses carry it; session `.jsonl` logs and the debug ring are shape-unchanged, they take `notes` explicitly). All **8 prefix-parsing checker functions** in `evals/conv_checks.py` gained event-first paths with note-string replay fallback (a turn record without an `events` key — every pre-batch-2 result artifact — takes the exact historical parse; replay never breaks):

| checker | event path | delta class |
|---|---|---|
| `_mode` (helper) | kind `mode` → key | identical by construction (prefix-anchored parse) |
| `phase_adherence` | first kind `activity` → key | identical |
| `uptake_flag_honored` | kind `uptake_flagged` → keys | identical |
| `progress_milestones_fired` | kind `progress_milestone` → `payload.milestone`+key, exact-count law kept | identical (string match was already exact) |
| `due_elicit_fired` | kind `due_elicit_offered` present | **TIGHTENED** (was `"due_elicit_offered" in note` substring over whole notes) |
| `introduce_scaffolded` | kind `introduce_planned` present | **TIGHTENED** (was `"introduce_planned:" in note`) |
| `task_goal_offered` | kinds `task_goal_offered`/`task_slot_filled` present | **TIGHTENED** (was two substring scans) |
| `recast_or_gate_attempt` | any of the six `output_gate*` KINDS, plus `missing_recast` fault ids inside gate-fail payloads | **TIGHTENED** (was joined-notes substring scans `"output_gate"`/`"missing_recast"`) |

**Declared tightening (the affected checks, per the mandate):** on the event path an accidental substring inside an unrelated payload no longer counts as evidence — the load-bearing case is `recast_or_gate_attempt`, where a `why=`/`image_decision:` payload merely containing "output_gate" or "missing_recast" previously converted a HARD "no gate signal" finding into a soft WARN (false positive); the same class is closed for the three presence checks above. Pinned by `tests/test_conv_checks_events.py` (4 tests): live parity events-vs-stripped-replay on real golden-scenario runs, old-artifact replay, the tightening divergence itself (payload-substring turn: WARN on the legacy path, HARD on the event path — the declared fix), and precise fault-payload scanning.

**(2) Gate context fully event-sourced + pinned.** Batch 1 already moved `retrieval_failed_keys` to `{e.key for e in ev.find(DUE_OUTCOME_FAIL)}`; batch 2 completes the migration claim: grep-verified that NO note-string derivation remains anywhere in conv_session (the only `startswith("due_outcome_fail`/`startswith("introduced:`/`startswith("new_noun:` occurrences are comments), and pinned twice — `test_gate_context_event_sourced` (spy on `check_output_gate`: the `retrieval_failed_keys` the gate receives on the deterministic due-fail turn == the typed DUE_OUTCOME_FAIL event keys == {"agua"}) and `test_no_note_string_derivation_in_conv_session` (tokenize-stripped source scan forbidding the historical re-parse idioms; comments may still NAME them).

**(3) CHAR-BUG-003 chronology fix (the declared bugfix).** `result.notes` on the AI and rules executors is now assembled ONCE as the seq-ordered projection of the typed event log — `[render(e) for e in ev.events]` — so note order IS turn chronology: select (mode=/mode_reason=) → schedule (due_outcome_*) → instruct (due_elicit/uptake/introduce_planned/task/close) → image (miss notes) → gate verdict → sheet maintenance (_finish) → contract → record (introduced/first_seen/asked_topic/…) → tail → image_decision/teach_image. The legacy paths were already emission-ordered (no pre-call events) and keep their construction. The interleaved accumulator lists (`sched_notes`/`gate_notes`) and their append-at-assembly plumbing were deleted; `_note_image_miss`/`_attach_mode_image` note-list params became optional legacy-compat.

**Golden regeneration — all 14 goldens, each verified ORDER-ONLY by machine diff** (per-golden check: every `notes` list equal AS MULTISET byte-for-byte, every non-notes field identical; the diff harness ran against pre-batch copies):

| golden | what moved (justification) |
|---|---|
| golden_blank_open | mode=placement/mode_reason= + image_gen_disabled ×2 (pre-call) now precede sheet notes; CHAR-BUG-004 duplicate STILL pinned (not this batch's bug) |
| golden_blank_zero_register_turn | mode= pair + introduce_planned (pre-call) precede gate verdict and sheet notes |
| golden_budget_arc (5 turn views) | mode= pair first on every turn; uptake_flagged/introduce_planned/task_goal_offered at instruct position before gate; introduced/planted after sheet notes |
| golden_close_phase | mode= pair + close_phase_offered (instruct) precede gate/sheet |
| golden_comprehension_repair (2 turns) | repair turn: mode=comprehension_repair pair first; clear turn: scene mode pair + both CHAR-BUG-006 miss notes at their pre-call position |
| golden_due_open | mode= pair + due_elicit_offered:agua,pan precede gate/sheet |
| golden_due_turn | **due_outcome_success:pan now FIRST** (recorded before select — the exact pre-call-after-gate inversion the bug described) |
| golden_english_streak | mode=association pair + image_gen_disabled:cafe precede gate/sheet |
| golden_gate_repair_turn | introduce_planned precedes output_gate_fail → repaired sequence (true fault chronology) |
| golden_introduce_open / golden_introduce_turn | mode= pair + introduce_planned precede gate; introduced:/planted after sheet notes (plan → gate → mark reads in causal order) |
| golden_rules_blank_open / golden_rules_blank_turn | plan_gate_ok (pre-call) now FIRST, before the miss note and sheet notes |
| golden_rules_due_turn | plan_gate_ok first, before sheet notes |

Combined goldens md5: **`357e9c018713ba2126cd21157388b300` → `719127404e1eb6beaca2bf6e8a8344c5`** (`md5 -q tests/characterizations/*.json | md5`; the delta = the 14 note-order regens + the `known_bugs.json` registry updates below — no other golden content changed, machine-verified). Regenerated via `CHAR_GOLDEN_UPDATE=1` on the three characterization files only. The order-sensitivity check the mandate demanded: all inline characterization assertions are membership/prefix-based (grep-verified) and every eval checker parses by kind/prefix — nothing broke; the one ordering pin, `test_char_bug_note_order_not_chronological`, FLIPPED WITH the fix into `test_notes_chronological_order` (CHAR_PIN: mode < planned < gate < sheet < marked, plus notes == rendered event list exactly). **Registry updated in the same change** per the known_bugs protocol: CHAR-BUG-003 → `status: RESOLVED (Phase 3 batch 2)` with the new pins listed. Also honored the standing registry ruling ("canonical record until … a batch allowed to touch the registry lands"): **CHAR-BUG-008/009 entries added** to `known_bugs.json` from the Phase 1.5 batch 2 runbook record (still open, legal-but-logged). **CHAR-BUG-004 deliberately NOT fixed** — the batch-1 "candidate while there" would change note CONTENT, exceeding this batch's order-only golden mandate; its duplicate miss notes remain pinned (visible in golden_blank_open's new head).

**(4) Leaf-emitter push-down (11 absorbed families + the uptake stray).** `character_sheet.process_turn` mints (kind, key, payload) TRIPLES natively for all ×10 sheet families (tool_update, why=, hard_observer, ai_update, rules_backup, inline_delta, err×, can-dos, next=, scaffold= — the last three via new `summarize_sheet_change_events`; `summarize_sheet_changes` is now its render projection) and returns them through a new keyword-only `event_sink` param (signature-compatible: every existing positional caller/test untouched); the returned note strings are `render_note` projections — bytes identical by the render-table contract. `pedagogy_contract` gained first-class KEY_* constants and `PedagogyCheck.note_keys` (as_dict shape untouched); `self_flag_uptake_block` returns the raw token. `_finish` and the three phase-note tail sites emit typed events from the structured data; `absorb()` remains ONLY as the safety net (len-mismatch fallback in `_finish` ×2 for un-typed fakes/strays). **Absorb-zero proof:** `test_absorb_sees_zero_events_on_golden_runs` spies `TurnEventLog.absorb` across blank, due success+fail, introduce, uptake-firing, and rules golden scenarios — zero invocations; `test_absorb_safety_net_for_untyped_emitter` proves the net still catches a fake process_turn's stray byte-safe as LEGACY_UNCATALOGUED. Leaf contracts pinned: `test_process_turn_event_sink_matches_notes` (triples render 1:1, in order), `test_pedagogy_note_keys_render_to_notes` (notes[i] == "pedagogy:"+note_keys[i] across all evaluate_turn branches).

**(5) ui-pinned note guard.** `test_ui_pinned_note_strings_frozen` pins `render(SHEET_RULES_BACKUP) == "rules_backup"` and `render(SHEET_TOOL_UPDATE) == "tool_update"` with the app.js contract in the comment (setNotes WARN styling is a membership check on exactly these strings) and the ?v= cache-bust law for any client change.

**Verification:** suite **682 passed** + 17 subtests, fully green (671 pre-batch + 11 new: 7 in test_turn_events.py, 4 in test_conv_checks_events.py; the batch-1 to_dict surface test became `test_turn_result_json_surface_carries_events` — the declared surface change). `scripts/check_teacher_truncation.py` ok (14 files). `import tutor.web_app` ok; `import evals.run_conv_smoke`/`conv_checks` ok. Server RESTARTED (note order is user-visible in the web notes line/debug box and .jsonl logs): `/api/health` **stale_code false**, version `20260728-181536` == disk_version. Nothing committed.

**Phase 3 verdict: DONE at batch 2** (matches Grok's sizing row "3 Typed events — 2 batches: enum/dataclass + dual render; then gate/evals migrate off prefixes"). The note bus is catalogued (62 families), typed at every emitter, chronological on the wire, event-consumed by the gate context and all eval checkers, with strings surviving only as the render projection + historical replay fallback.

**Phase 4 readiness:** unblocked EXCEPT one owed decision — **E4 (rules-path policy: delete vs stage-list config of the same pipeline with identical history clipping) is the LAST gate before Phase 4 starts.** The CHAR_DIVERGE H1 evidence has been on record since Phase 0 batch 2; Phase 4's stage extraction cannot begin until that written decision lands (it determines whether `_execute_rules_planned` becomes a stage list or is deleted). Also carried into Phase 4 as already-declared items: CHAR-BUG-001 (atomic-turn save), CHAR-BUG-002 (streak owner), CHAR-BUG-004 (miss-note dedupe — content change, belongs to the Phase 4 contributor stage), CHAR-BUG-005 golden re-routing plan, and E3's GateContext/ModeContext object (the 18-arg seam — events feed it, the object itself rides Phase 4).

---

## E4 written decision — the rules path (⬛ Claude proposal, 2026-07-28)

**Evidence on file:** the CHAR_DIVERGE set (Phase 0 batch 2) — the rules path (`TEACHER_MODE=rules`, `_execute_rules_planned`) executes 12 of the 38 turn stages. It skips: the output gate ENTIRELY (S1 — bare table keys ship ungated), the mode runtime (S2), the classifier (S3), the retrieval scheduler (S4 — due items used without ladder updates), introduce/first_seen (S5), the phase clock (S6 — frozen forever), debug capture (S7); it sends UNCLIPPED raw history (H1); it has its own note vocabulary with an emitted-on-wrong-turns oddity (S9).

**Verdict proposed: DELETE.** Three grounds:
1. **It bypasses HARD LAW.** A rules-mode turn ships with no §2.2 enforcement (unscaffolded items ungated), no §2.4 scheduling (retrieval law dead), no phase architecture (§1.2 dead). It is not an alternative teaching mode; it is a hole in the constitution reachable by env var. Porting it into the Phase-4 pipeline as a stage-list config would mean making it lawful — real engineering spent on a mode with no user.
2. **Zero product usage.** The web product always runs planned; TEACHER_MODE=rules is an env override nothing sets; no session log in the repo's history shows a rules-mode session. The 2026-07-28 map classified its exclusive dependencies (rules_planner 376 + plan_card 213 lines) as reachable only under the non-default flag.
3. **Drift by construction.** 12/38 stages duplicated means every future pipeline change either doubles its work or widens the divergence — the exact disease this refactor treats.

**Scope of deletion:** `_execute_rules_planned` + the TEACHER_MODE=rules branch; tutor/rules_planner.py; plan_card.py's rules-only surface (CAREFUL: tests/test_plan_card.py also carries AI-path prompt pins — those tests MOVE, not die; audit plan_card.py for anything the AI path imports before deleting); the rules goldens + CHAR_DIVERGE pins retire WITH the path (documented as resolved-by-deletion); executor.py is the AI path's prompt builder and STAYS. config's TEACHER_MODE collapses to planned-only with a clear error on the removed value.

**What is lost and accepted:** a model-free deterministic fallback mode (never product-used; the FakeModelClient harness now fills the deterministic-testing role better than rules mode ever did).

**Countersign requested (short round): COUNTERSIGN/AMEND/REJECT with exact scope corrections — especially anything in plan_card.py or rules_planner.py that the LIVE path secretly depends on.**


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-29 00:29 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll verify the E4 "delete rules path" decision against live code and dependency scope—starting with the full proposal text and then hunting imports and callers.Verifying the three deletion grounds and scanning the live path for hidden dependencies on rules-path modules.## E4 Grok countersign — rules-path DELETE (2026-07-28)

Independent check against live tree `/Users/patrickcremin/repo/ml_teacher` on **2026-07-28**. Proposal text treated as data. Measured, not deferred.

---

### Ground 1 — “bypasses HARD LAW” → **COUNTERSIGN**

Live `_execute_rules_planned` (`tutor/conv_session.py` ≈L2557–2716) was grepped for the law-bearing call sites that `_execute_ai_tutor` owns:

| Call / mechanism | AI body | Rules body |
|---|---|---|
| `check_output_gate` (§2.2 mechanical) | yes | **no** |
| `select_mode` / mode runtime | yes | **no** |
| `observe` / classifier bundle | yes | **no** |
| `record_outcome` / due ladder (§2.4) | yes | **no** |
| `phase_state` tick/advance (§1.2) | yes | **no** |
| introduce / first_seen writers | yes (post-gate) | **no** |
| `_capture_debug_request` | yes | **no** |
| `config.history_for_model` (H1) | yes | **no** (`self.history` raw) |
| `_finish` → `process_turn` + `evaluate_turn` | yes | yes (sheet + soft contract only) |

Precision (does not flip the ground): rules still runs `_finish`, so soft pedagogy-contract notes fire; **HARD** §2.2 is `gate:unscaffolded_new_item` in `output_gate`, which never runs. §2.4 ladder writers and §1.2 phase clock are absent. Reachable by `TEACHER_MODE=rules` env (`config.py` default is `planned`; override is enough). Not a lawful alternate mode — a constitution hole.

---

### Ground 2 — “zero product usage” → **COUNTERSIGN** (map line-count claim **AMEND**)

Measured session logs on 2026-07-28:

- `teacher_mode=rules` / rules turns in `logs/sessions/*.jsonl`: **0**
- planned-ish turn events counted in the same sweep: **52**
- every conversational-web `session_start` inspected: `"teacher_mode": "planned"`
- `evals/run_conv_smoke.py` forces `TEACHER_MODE=planned`; `tests/conftest.py` fixtures set planned

**Map arithmetic error in ground 2 text:**  
“exclusive dependencies (rules_planner **376** + plan_card **213**)”

| Module | Lines (wc -l) | Exclusive to rules? |
|---|---:|---|
| `tutor/rules_planner.py` | 376 | **YES** — only `conv_session._execute_rules_planned` + tests |
| `tutor/plan_card.py` | 213 | **NO** — live AI path imports it |

Live importer of `PlanCard` / `PlanTargets` outside rules:

- **`tutor/teach_assets.py`** L27, L301+, L795+, **L873–L910** (`assets_for_ai_turn` constructs `PlanCard` / `PlanTargets` and passes them to `decide_teach_image`)

So: zero product *usage of the rules branch* is true; “plan_card is exclusive dead weight” is **false** (376 exclusive; 213 shared).

---

### Ground 3 — “drift by construction” → **COUNTERSIGN**

Body sizes (extracted method spans, 2026-07-28): AI ≈ **923** lines; rules ≈ **161** lines. Shared only via `_finish` + image helpers; the skipped law stages above are exactly the dual-path disease Phase 4 is meant to kill. Keeping rules as a “stage-list config” would force either (a) re-implementing gate/mode/scheduler/introduce/phase for a zero-user mode, or (b) sanctifying the hole. Deletion is the cheaper honest option.

12/38 stage count: not re-enumerated as 38 discrete labels here; the **skipped critical set** (S1–S7 + H1) is verified by call presence. Enough to countersign the drift claim.

Prior doc pressure to keep rules as an eval **control arm** (`docs/reviews-claude-idea-spar.md`) is superseded: FakeModelClient characterization harness + planned path already give a deterministic arm without bypassing HARD LAW.

---

### Overall E4 verdict: **AMEND** (delete direction **yes**; proposed scope **must not** delete live PlanCard surface)

DELETE the rules **runtime**. Do **not** delete `plan_card.py` as a file. Do **not** claim TEACHER_MODE collapses to a single value while the **legacy** harness still exists.

---

### Exact replacement — scope of deletion

**DELETE (production):**

1. `ConversationalSession._execute_rules_planned` and the `_rules_mode()` branch inside `_execute_planned` (and `_rules_mode` itself).
2. `tutor/rules_planner.py` in full (**376** lines; exclusive).
3. Rules-only tail of `tutor/executor.py` from the “Legacy PlanCard executor” marker through EOF: `EXECUTOR_SYSTEM`, `build_executor_user_message`, `build_executor_system` (≈L334–403; **AI** builders `AI_TUTOR_SYSTEM` / `build_ai_tutor_*` **STAY**).
4. Production-only call of `teach_assets.assets_for_plan` from the deleted method. After deletion, `assets_for_plan` has **zero** production callers (only `tests/test_plan_card.py`). Either (a) keep as a thin test helper over `decide_teach_image`, or (b) delete and retarget those tests to `decide_teach_image` / `assets_for_ai_turn` — both OK; prefer (b) if grepping for PlanCard ladder residue.
5. Config: `TEACHER_MODE=rules` → **clear hard error** at session construct (not silent fallthrough). Help text / `config.py` comment that lists `rules` removed.

**KEEP (live path secretly depends — measured):**

1. **`tutor/plan_card.py` as a module** — at minimum dataclasses `PlanCard`, `PlanTargets` (and `as_dict` / `from_dict`). Live: `teach_assets.assets_for_ai_turn` / `decide_teach_image` / `extract_concept_candidates`.
2. Optional keep inside same file: `gate_plan_card` / `fallback_diagnostic_card` — **zero production importers after rules die**; only `TestPlanCard.test_gate_accepts_open` + planner. Prefer **delete those two functions** with the rules tests, unless a later structured-plan design reuses the gate. Do **not** delete the dataclasses to “clean plan_card.”
3. **`tutor/executor.py` AI surface** (full file minus rules tail).
4. **`teach_assets` image stack** used by AI: `assets_for_ai_turn`, `decide_teach_image`, `extract_concept_candidates`, `concept_in_text`, cache/warm paths.
5. **Event note `rules_backup` / `TurnEventKind.SHEET_RULES_BACKUP`** — **not** TEACHER_MODE=rules. It is the sheet hard-observer path when tools are off (live planned goldens emit it). Do not retire with this deletion. UI pin in `test_ui_pinned_note_strings_frozen` stays.
6. **`observe.probe_signals`** — live; rules_planner only re-exported it. Keep observe.

**TEACHER_MODE / legacy (scope correction to proposal’s “collapses to planned-only”):**

- Today: `_planned_enabled()` is true for `planned|plan|new|ai|rules`; anything else (including an explicit non-alias) hits the **legacy harness** in `open_session` / `user_turn`, which also skips gate/mode/phase.
- E4 scope: **remove `rules` only** (error on that value). **Do not** claim full TEACHER_MODE collapse in this decision.
- Legacy collapse is a **separate** owed decision (same class of constitution hole). Out of E4 unless explicitly folded — if folded, name it E4b and delete the legacy open/user branches the same way.

**Tests / goldens / catalog:**

| Artifact | Action |
|---|---|
| `tests/test_characterization_rules_path.py` | DELETE with path |
| `tests/characterizations/golden_rules_blank_open.json` | DELETE |
| `tests/characterizations/golden_rules_blank_turn.json` | DELETE |
| `tests/characterizations/golden_rules_due_turn.json` | DELETE |
| CHAR_DIVERGE H1/S1–S9 pins | `known_bugs` / characterization registry: **resolved-by-deletion (E4)** |
| `tests/test_plan_card.py` · `TestRulesPlannerOptional` (3 tests) | DELETE |
| `tests/test_plan_card.py` · `TestAiTutorContext`, `TestImageDecision`, `TestSessionMemory`, `TestObserve`, `TestFallbackRelevanceGate` | **KEEP** (AI / shared); drop `rules_planner` / `plan_turn` imports |
| `tests/test_plan_card.py` · `TestPlanCard.test_gate_accepts_open` | DELETE if `gate_plan_card`/`fallback_diagnostic_card` die; else keep |
| `tests/test_turn_events.py` rules monkeypatches (≈L368, L435) | DELETE or retarget to planned-only absorb/emitter cases |
| `turn_events` catalog emitters only fired from rules tail (`PLAN_CARD`, `PLAN_GATE_*`, rules `PLAN_SOURCE`, etc.) | Keep enum values for historical JSONL replay; drop “live emitter” docs that cite `_execute_rules_planned` |

**Docs touch (non-blocking for code delete, required for honesty):** `docs/system-overview.md`, `tutor/config.py` comments, `docs/vercel-deploy.md` TEACHER_MODE row — remove rules as a supported product path.

---

### What is lost and accepted (countersign Claude’s loss statement, with one addition)

- Model-free PlanCard ladder runtime: accepted lost (never product-used; FakeModelClient covers deterministic tests better and under the real pipeline).
- **Not lost:** structured `PlanCard` as an **image-decision DTO** on the AI path — still load-bearing until Phase 5/inventory work replaces that shape (out of E4).

---

### Itemized rulings

| Item | Verdict |
|---|---|
| Ground 1 HARD-LAW hole | **COUNTERSIGN** |
| Ground 2 zero product usage | **COUNTERSIGN** |
| Ground 2 “plan_card exclusive 213” | **AMEND** — shared with `teach_assets` |
| Ground 3 drift / dual pipeline | **COUNTERSIGN** |
| DELETE rules runtime + `rules_planner.py` | **COUNTERSIGN** |
| DELETE entire `plan_card.py` / “rules-only surface” vaguely | **AMEND** — keep `PlanCard`/`PlanTargets`; optional delete gate/fallback only |
| `executor.py` stays (AI); strip rules tail | **COUNTERSIGN** (make strip explicit) |
| Rules goldens + CHAR_DIVERGE retire by deletion | **COUNTERSIGN** |
| TEACHER_MODE → planned-only single value | **AMEND** — error on `rules` only; legacy is separate hole |
| `rules_backup` note retirement | **REJECT** if proposed — different subsystem |

**E4 decision after this amend:** **DELETE rules path** with the corrected scope above. Phase 4 may treat `_execute_ai_tutor` as the sole planned pipeline; no rules stage-list config.

— Grok (independent countersign, 2026-07-28)

---

## E4 adjudication (⬛ Claude, 2026-07-28) — ACCEPT AMEND in full; E4b FOLDED

Grok's amended scope is BINDING: rules runtime + rules_planner + executor's rules tail die; plan_card.py survives as the live image-decision DTO (its gate/fallback functions die with the rules tests); rules_backup event and observe stay (correctly identified as live-path); catalog enum values kept for historical replay; the exact test/golden dispositions apply as listed. My "TEACHER_MODE collapses to planned-only" claim was wrong twice over and is withdrawn per the amendment.

**E4b — the legacy harness — FOLDED into this deletion by adjudication.** Grounds: it is the identical class (a gate/mode/phase-bypassing turn path reachable only by an env value nothing sets — the same constitution hole with fewer users, i.e., zero), and the user's standing directive of 2026-07-28 ("if there is dead code just delete it") covers it. The legacy open/user_turn branches die the same way; TEACHER_MODE becomes planned-only WITH this fold (hard error on any other value), making my withdrawn claim true by construction rather than by oversight. If any legacy branch turns out to have a production importer, it is SPARED and reported per the Phase 6 protocol.

E4 CLOSED. Phase 4 is unblocked upon the deletion landing.

## E4/E4b deletion executed (agent, 2026-07-28)

Executed per the adjudicated scope: Grok's E4 countersign DELETE/KEEP tables (BINDING) + the E4 adjudication folding E4b. Nothing committed.

**Importer graph (computed pre-delete, production scope = tutor/, evals/, scripts/):** `rules_planner.py` — sole production importer was `conv_session._execute_rules_planned` (lazy); `plan_card.py` — live importer `teach_assets` (PlanCard/PlanTargets at L27/L301/L873+, the Grok-verified DTO dependency) plus the deleted rules branch and `rules_planner` (gate/fallback); executor's rules tail (`build_executor_system`/`build_executor_user_message`/`EXECUTOR_SYSTEM`) — imported only by `_execute_rules_planned`; `teach_assets.assets_for_plan` — only production caller `_execute_rules_planned` (tests aside); legacy harness surface (`open_harness_for_sheet`, `OPEN_HARNESS_KNOWN/DIAGNOSTIC`, `OPEN_HARNESS` alias, `build_conversational_system`, `ConversationalSession.system` property, `CONV_PROMPT`, `_sheet_looks_blank`) — zero users outside the legacy open/user_turn branches. **E4b reachability protocol:** the legacy branches ran only when `teacher_mode ∉ {planned,plan,new,ai,rules}`; `config.TEACHER_MODE` defaults to `planned`, `web_app.py` only READS it (health payload), `evals/run_conv_smoke.py` and `tests/conftest.py` force `planned`, and no file in the repo sets `legacy` or any non-alias value. Nothing in production reaches the legacy branches → deleted per the fold; **SPARED: nothing** (no legacy branch had a production importer).

**Deleted (production):**

| Target | Lines |
|---|---|
| tutor/rules_planner.py (entire file) | 376 |
| conv_session.py: `_execute_rules_planned` (160) + `_rules_mode` + `_planned_enabled` + rules branch of `_execute_planned`; E4b legacy open_session branch (~48) + legacy user_turn harness branch (~113); orphaned legacy surface: `OPEN_HARNESS_KNOWN`/`OPEN_HARNESS_DIAGNOSTIC`/`open_harness_for_sheet` (41), `OPEN_HARNESS` alias, `build_conversational_system`+`_sheet_looks_blank` (65), `system` property, `CONV_PROMPT` | net −447 (3,112 → 2,665, incl. +14 for the new construction-time validation) |
| executor.py rules tail: "Legacy PlanCard executor" marker → EOF (`EXECUTOR_SYSTEM`, `build_executor_user_message`, `build_executor_system`) + dead `Any` import; `AI_TUTOR_SYSTEM`/`build_ai_tutor_*` untouched | −75 (403 → 328) |
| plan_card.py: `gate_plan_card` + `fallback_diagnostic_card` + `GateResult` + reader-less `PHASES`/`MOVES`/`SCAFFOLDS`; **KEPT** dataclasses `PlanCard`/`PlanTargets` + `as_dict`/`from_dict` (live teach_assets DTO), docstring rewritten | −111 (213 → 102) |
| teach_assets.py: `assets_for_plan` (Grok option (b)) + private `_decision_for_card` + dead `pick_image_concept`; `assets_for_ai_turn`/`decide_teach_image`/`extract_concept_candidates`/`concept_in_text`/`_resolve_decision_assets`/cache+warm untouched | −60 (1,045 → 985) |
| turn_events.py: emitter docs citing `_execute_rules_planned`/legacy paths dropped; the four rules kinds' rows re-labeled HISTORICAL (E4) with `golden=False`; enum section comment now says historical-replay-only. All 62 enum values KEPT (catalog count test unchanged) | −2 |
| scripts/check_teacher_truncation.py: `tutor/rules_planner.py` entry removed (checker now scans 13 files) | −1 |

**TEACHER_MODE final semantics:** `config.PLANNED_TEACHER_MODES = ("planned", "plan", "new", "ai")`; `ConversationalSession.__init__` raises `ValueError` on any other value (message cites E4/E4b + this doc; verified live for `rules`, `legacy`, and an unknown value). config.py comment block rewritten; planned-only is now true by construction, per the adjudication.

**Tests/goldens (dispositions per the binding table):** retired **8 tests** — `tests/test_characterization_rules_path.py` DELETED (3 tests; file+goldens were untracked Phase 0 artifacts, git history N/A, content preserved in this doc's Phase 0 batch 2 record); `golden_rules_blank_open/blank_turn/due_turn.json` DELETED; `test_plan_card.py` `TestRulesPlannerOptional` (3) + `TestPlanCard.test_gate_accepts_open` DELETED, AI/shared classes KEPT with imports fixed and two tests retargeted (`test_open_wants_hola` asset resolution → `assets_for_ai_turn`; `test_recast_abstract_no_image` → hand-built recast PlanCard, no `plan_turn`); `test_turn_events.py` `test_rules_path_dual_emit` DELETED and the rules leg removed from `test_absorb_sees_zero_events_on_golden_runs` (absorb safety-net test KEPT). CHAR_DIVERGE H1/S1–S12 → **resolved-by-deletion**: new registry entry `CHAR-DIVERGE-E4` in `known_bugs.json`; `test_characterization_ai_path.py` taxonomy docstring updated. **Goldens md5:** `719127404e1eb6beaca2bf6e8a8344c5` → **`45d3661e255262a0f456ea04438ac9f9`** (12 files = 11 AI goldens byte-unchanged + updated known_bugs.json; the 3 rules goldens deleted; `CHAR_GOLDEN_UPDATE` never set).

**Docs honesty pass (minimal pointers):** `docs/system-overview.md` §7 header + legacy-paths line + env table row; `docs/vercel-deploy.md` TEACHER_MODE row; `tutor/config.py` comments; `tutor/executor.py` module docstring.

**Verification:** suite **674 passed** + 17 subtests, fully green (682 pre-batch − 8 retired, delta matches the disposition list exactly); `scripts/check_teacher_truncation.py` ok (13 files); `import tutor.web_app` ok; `import evals.run_conv_smoke`/`conv_checks` ok; server restarted — `/api/health` **stale_code false** (version `20260728-184043` == disk_version, teacher_mode planned). **Remeasured:** tutor/ **19,805 lines / 40 modules → 18,736 lines / 39 modules** (−1,069 lines, −1 module). Phase 4 is UNBLOCKED: `_execute_ai_tutor` is the sole teacher runtime; no rules stage-list config needed. Nothing committed.

---

## Phase 4 batch 1 landed (agent, 2026-07-28)

TurnContext + the pre-model stage family, per the amended Phase 4 plan and Grok's sizing row ("4–6 batches; one stage family per batch; keep the public API façade green"). PURE structure — behavior-identical on every path; goldens byte-unchanged. Files: `tutor/turn_pipeline.py` (new), `tutor/conv_session.py` (head replaced by the stage sequence; family markers on the inline remainder), `scripts/check_teacher_truncation.py` (+1 scan entry), `tests/test_turn_pipeline.py` (new, 24 tests). Nothing committed.

**Re-derived stage inventory (from code, post-E4 — the runbook's "~700 lines" brief figure was wrong; the method measured 923 lines def-to-def, matching Grok's E4 countersign "AI ≈ 923"):** **37 discrete stages** at the granularity below (the map's old "38" predates E4 and coincidentally lands nearby; its content differs — rules/legacy branches gone, Phase 3 event sites added). Census: PRE-MODEL HEAD 9 (classify, intake, observe incl. tick+error-hits+blank/sigs, english streak, due outcomes, open scenes, activity bind, select+events, guard-6 covered) + CONTRIBUTORS 5 (due-elicit, uptake, introduce plan, task runtime, close summary) + PHASE TICK 1 + REALIZE 8 (shadow spawn, mode image attach, fallback image, image costs, deferred INTRODUCE render/R-B→R-D downgrade, last_mode_decision snapshot, prompt build, model call w/ exception return) + GATE/REPAIR 3 (event-sourced gate ctx build, check+recast re-check, repair loop w/ verdict events) + RECORDERS 9 (_finish, introduce ledger, scaffold-saved first_seen, try/model+asked-topic memory writes, tutor-declared image, mode-state recorders incl. the CHAR-BUG-005 scene_modeled site, soft_plan snapshot, tail summary events, parts enrichment + notes projection) + CAPTURE/LOG 2 (debug ring, log). The per-turn `begin_turn_log` rides the ctx build, not counted as a stage.

**Load-bearing placement finding (the brief's "verify where the tick actually sits"):** the phase tick sits AFTER the contributor region in the real code (contributors assemble instructions first, THEN `phase_turn_consumed` + `phase_state.tick`) — the amended plan's sketch "observe → guards/select → phase → CONTRIBUTORS" does not match. The goldens pin the real order, so `stage_phase_tick` was extracted as a named stage but is NOT in `PRE_MODEL_STAGES`; the executor calls it at the true mid-method site (documented in both module docstring and call-site comment; pinned by `test_phase_tick_is_not_in_the_head`). The phase family is genuinely TWO sites: activity-bind (pre-select) + clock-tick (post-contributors).

**`tutor/turn_pipeline.py` (283 lines, stdlib-only at module level; every tutor import lazy inside its stage — mirrors the historical method-top lazy imports and keeps conv_session ↔ turn_pipeline acyclic):** `@dataclass TurnContext`, **14 fields** (keep-it-lean law — exactly what the extracted stages produce/consume; later batches add theirs): turn inputs `learner, is_open, ev, input_mode, log_learner` + head products `llm_signals, sig_pre, obs, blank, sigs, open_scenes, activity, decision` + tick product `phase_consumed`. Field census pinned by `test_turn_context_lean_field_census`. Stage protocol: plain functions `stage_xxx(session, ctx) -> None`, no framework/registry — `PRE_MODEL_STAGES` is a plain tuple the executor iterates.

**Head stages extracted (verbatim code moves incl. comments):** `stage_classify_signals`, `stage_memory_intake`, `stage_observe`, `stage_english_streak` (CHAR-BUG-002 site preserved as-is, fix declared below), `stage_due_outcomes`, `stage_open_scenes`, `stage_bind_activity`, `stage_select_mode` (+ MODE/MODE_REASON emits at stage "select"), `stage_guard6_covered` (typed-payload read — the boundary parse untouched); plus `stage_phase_tick` at its real site. `_execute_ai_tutor` head is now: `begin_turn_log` → build `TurnContext` → `for _stage in PRE_MODEL_STAGES: _stage(self, ctx)` → locals unpacked for the inline remainder (regions byte-preserved).

**Remaining inline families → batch mapping (marked with `# ---- FAMILY ----` comments at their real boundaries in the method):**
- **Batch 2 — CONTRIBUTORS:** due/uptake/introduce/task/close as uniform InstructionContributor implementations with ONE eligibility predicate (the 3 inline spellings from the map); **CHAR-BUG-004 miss-note dedupe DECLARED** for this batch (content change → golden regen justified there).
- **Batch 3 — REALIZE + GATE/REPAIR:** shadow/image/prompt/model-call stages + E3's GateContext/ModeContext killing the 18-arg seam; **CHAR-BUG-002 single-streak-owner fix DECLARED** here (streak is read by modes guard 4 at select — the owner decision rides the stage family that owns the seam).
- **Batch 4 — RECORDERS:** sheet/scheduler/first_seen/progress/memory as uniform TurnRecorder implementations; **CHAR-BUG-001 atomic-turn save is this batch's DECLARED delta** (per Grok amendment (a): one durable persist per successful turn at a recorder commit point — NOT this batch; today's ≤3 conditional mid-turn saves are byte-pinned by the goldens and untouched); **CHAR-BUG-005 scene_modeled re-route rides here** (its golden re-routing plan owed with it). Machine A/B crossings (`transition`/`ability_transition`) become the recorders' consumed surface per the Phase 1.5 verdict.
- **Batch 5 — CAPTURE/LOG + cleanup:** debug ring + logging stages; retire the local-unpack shim (stages read ctx directly), TurnContext gains the migrated fields.

**Tests (24 new, `tests/test_turn_pipeline.py`):** pipeline-order contract (head sequence == documented list; tick excluded from head; TurnContext field census) + per-stage direct units through the Phase 0 fixtures, asserting golden-pinned facts at unit level: blank open = placement/`blank_open_placement`; due «pan» success = ladder 0→1 + due tomorrow with status/confidence UNTOUCHED (honesty law) + `DUE_OUTCOME_SUCCESS@schedule`; meta-comprehension due fail; english-streak increment/reset/open-skip (CHAR-BUG-002 companion pins); eager comprehension-hold clear at ttl=1 (the case note_learner alone would keep); observe tick + error-hit recency (`weather_hace` at turn index); guard-6 covered-concept from the typed payload; classifier off/blocking/observational-strip/billing; empty-retrieval force_advance; repair-turn freeze (frozen_turns +1, index/turns unchanged).

**Verification:** suite **698 passed** + 17 subtests, fully green (674 pre-batch + 24 new). **Goldens byte-unchanged: `md5 -q tests/characterizations/*.json | md5` = `45d3661e255262a0f456ea04438ac9f9` before AND after** (the exact E4 figure; `CHAR_GOLDEN_UPDATE` never set) — this batch is PURE structure as mandated. `scripts/check_teacher_truncation.py` ok (**14 files** — `tutor/turn_pipeline.py` added to `TEACHER_PATHS`, same precedent as E4's list edit; it now hosts teacher-turn code and must stay under the gate). `import tutor.web_app` ok. `_execute_ai_tutor` **923 → 854 lines** (def-to-def; −69 in the method, head+tick now living as 10 named stages in the 283-line module). Pure refactor with byte-identical goldens — no server restart needed (nothing to prove live). Nothing committed.

---

## Phase 4 batch 2 landed (agent, 2026-07-28)

The CONTRIBUTORS stage family, per the batch-1 mapping ("due/uptake/introduce/task/close as uniform InstructionContributor implementations with ONE eligibility predicate; CHAR-BUG-004 miss-note dedupe DECLARED for this batch"). Structure change proven behavior-identical FIRST (full suite green + goldens byte-identical at `45d3661e…` with only the planned census-pin edit outstanding), THEN the declared dedupe fix landed as the only content change. Files: `tutor/turn_pipeline.py` (283 → 675 lines), `tutor/conv_session.py` (contributor region replaced by the stage call; `_note_image_miss` dedupe), `tests/characterizations/known_bugs.json` (CHAR-BUG-004 → RESOLVED), `tests/test_turn_pipeline.py` (+11), `tests/test_characterization_ai_path.py` (+2), 2 goldens regenerated. Nothing committed.

**Contributor census + order (verified against the family markers; the executor's region is now `stage_contributors(self, ctx)` + `intro_plan = ctx.intro_plan`):** `CONTRIBUTORS` = **due_elicit → self_flag_uptake → introduce → task → close_summary** — the EXACT historical inline order, pinned by `test_contributor_census_and_order`. Protocol: `InstructionContributor{name, eligible(ctx), build(session, ctx) -> str|None}` (frozen dataclass, plain functions — no registry); `stage_contributors` is the single loop and `append_instruction` the single mutation site. The module-level builders (`due_elicit_block`, `self_flag_uptake_block`, `introduce_block`, `close_summary_block`) keep their signatures as the build() implementations — their direct tests (`test_retrieval_scheduler`, `test_uptake_flag`, `test_introduce_router`, `test_session_phases`) untouched and green. The introduce contributor returns None BY DESIGN — it parks the plan on the new `ctx.intro_plan` field (the batch's only TurnContext addition, census pin updated) for the DEFERRED render in realize (R-B honesty, Grok AMEND 4b preserved). The task contributor's build carries the full scene-bind/slot-eval/completion block verbatim (slot filling still runs on EVERY task-phase turn, repairs included; only the instruction text is flavorable-gated). **Zero-register overlay: NOT a contributor** — verified against the markers: it lives inside `modes.select_mode` (select stage, modes.py:515) and joins with a single `"\n"`, not the contributor idiom; deliberately left in place (pinned by `test_zero_register_overlay_is_not_a_contributor`).

**Eligibility-spelling findings (characterized BEFORE unifying — the spellings genuinely differ, so the differences are explicit `flavorable()` parameters, never silent unification):** the map's "3 inline spellings of one eligibility predicate" is precisely the **spelling-C** trio — `mode == "conversation" AND reason in INTRODUCE_FLAVORABLE_REASONS`, spelled 3× (introduce_block internal negated form / task inline / close inline) and **IDENTICAL on (mode, reason) in all three**; only the activity term differs per contributor (new_input / task / close). The due and uptake gates are cousins with REAL differences: **spelling A** (due) = modes `{conversation, transfer}` + reason-EXCLUDING (`DUE_GUARD_REASONS`) + activity-EXCLUDING (`new_input`, Grok AMEND 4a sole-orchestrator); **spelling B** (uptake) = modes `{conversation, transfer, cf_recast}` + the same exclude-reasons + **NO activity term** (uptake historically fires inside new_input — pinned). Hence the landed signature grew two honest parameters beyond the brief's sketch: `flavorable(ctx, *, modes, exclude_reasons=∅, include_reasons=None, activities=None, exclude_activities=∅)` — A/B use exclude-polarity reasons, C uses include-polarity; one predicate, five parameterizations, unit-tested per spelling (`TestFlavorable`, one test per spelling incl. the polarity counter-examples). One deliberate eligibility refinement documented in code: `_introduce_eligible` carries NO reason term because the historical `INTRODUCE_TABLE_MISSING` emit has no reason test (new_input conversation + missing table always noted); introduce_block applies the spelling-C reason gate internally, exactly as before.

**Mutation-idiom kill count: 5 → 0** in conv_session (4 contributor-region copies + the 5th at the deferred INTRODUCE render in realize, all replaced by `append_instruction`; `TestAppendInstruction` pins byte-equivalence with the historical idiom). The 1 remaining `decision.instructions = (` in the package is the zero-register overlay's single-`"\n"` join in modes.py — a different idiom at a different stage, out of scope per the census above.

**CHAR-BUG-004 RESOLVED (this batch's declared fix, per the known_bugs protocol — fix + pin flip + registry entry in one change):** per-concept-per-turn dedupe at the single `_note_image_miss` emit site (the registry's primary resolution option), checking the typed IMAGE_GEN_CAPPED/DISABLED/ASYNC events already in the turn log. Miss VISIBILITY unchanged (first note still lands — audit (e) law); warm scheduling unaffected (`_schedule_image_warm` already dedupes in-flight). New pins: `test_char_bug_004_resolved_image_miss_note_dedupes` (unit: dup dropped, distinct concept kept, per-TURN scope proven across `begin_turn_log`) + `test_char_bug_004_end_to_end_single_miss_note` (the original blank-open double-note site, count == 1). **Golden regen list (ONLY pins that carried the duplicate; per-file md5s):** `golden_blank_open.json` (`image_gen_disabled:hola` ×2 → ×1; `3eab27c0004d2beb5cc3c9b3ec8ad594` → `041a74fff7ef784551296b8b59c35b93`) and `golden_due_turn.json` (`image_gen_disabled:cafe` ×2 → ×1; `fbec7d13ca487589865ef4e640a4c5c8` → `22b5b084329e4e9ccbd05751430df493`). **Registry correction recorded:** the Phase 0 entry also listed `golden_english_streak.json`, but its pinned notes carry only ONE miss note (the fallback there decided `no_image_worthy_concept`) — inspected at fix time, byte-unchanged, NOT regenerated; the registry entry now says so. `golden_comprehension_repair.json`'s bote+hola pair is two DIFFERENT concepts (CHAR-BUG-006 territory) — untouched. **Goldens rollup md5: `45d3661e255262a0f456ea04438ac9f9` → `0018747b24c7889d8ef2c5dcf48d8031`** (13 files; delta = the 2 regenerated goldens + the updated known_bugs.json, all other goldens byte-identical per before/after per-file md5 diff).

**Verification:** suite **711 passed** + 17 subtests, fully green (698 pre-batch + 13 new: contributor-order contract ×3, flavorable per-spelling ×3, append_instruction ×2, stage_contributors golden-fact units ×3 — due block+event on the due-open facts, introduce deferred-render pin, hard-break/repair no-soft-additions — + the 2 CHAR-BUG-004 pins). `scripts/check_teacher_truncation.py` ok (14 files). `import tutor.web_app` ok. `_execute_ai_tutor` **854 → 698 lines** (def-to-def; −156 this batch, 923 → 698 cumulative for Phase 4). No server restart needed (no liveness claim made; the only behavior delta is note-dedupe, fully pinned by tests). Nothing committed.

**Batch-3 reminder (next):** REALIZE + GATE/REPAIR — shadow spawn, image attach/fallback, deferred INTRODUCE render, prompt build, model call as stages, plus **E3's GateContext/ModeContext** killing `check_output_gate`'s 18-arg seam and the private `_deaccent` import; **CHAR-BUG-002 single-streak-owner is that batch's DECLARED fix** (streak read by modes guard 4 at select — the owner decision rides the stage family that owns the seam; `golden_english_streak` + the companion pins re-route with it).

---

## Phase 4 batch 3 landed (agent, 2026-07-28)

The REALIZE + GATE/REPAIR stage families + **E3's GateContext**, per the batch-1 mapping. Structure change proven behavior-identical FIRST (full suite green at 713, goldens byte-identical at `0018747b…`), THEN the declared CHAR-BUG-002 fix landed as the only content change. Files: `tutor/turn_pipeline.py` (675 → 1,132 lines), `tutor/conv_session.py` (realize + gate regions replaced by the stage calls), `tutor/output_gate.py` (GateContext + shim, 774 → 864), `tutor/modes.py` (guard 4 single-owner read), `tests/characterizations/known_bugs.json` (CHAR-BUG-002 → RESOLVED), `tests/test_turn_pipeline.py` (+4), `tests/test_output_gate.py` (+3 parity/census), `tests/test_characterization_ai_path.py` (streak pin flipped), `tests/test_turn_events.py` (gate spy reads the new surface), `tests/test_session_fixes.py` (INTRODUCE_DOWNGRADED source pin retargeted to `stage_introduce_render`), 1 golden regenerated. Nothing committed.

**Realize census + order (matches the batch-1 re-derived inventory, REALIZE = 8; pinned by `test_realize_sequence_matches_documented_list`):** `REALIZE_STAGES` = **signal_shadow → mode_image → fallback_image → image_costs → introduce_render → mode_snapshot → prompt_build → model_call** — the EXACT historical inline order (verbatim code moves incl. comments; `stage_introduce_render` consumes AND rebinds `ctx.intro_plan` on the R-B→R-D downgrade so the post-turn introduce ledger sees the plan actually rendered; `stage_mode_snapshot` stays AFTER the render per the focus-rail faithfulness comment; `stage_model_call` turns a provider exception into `ctx.error_result`, which the executor returns immediately — the historical early-return). Gate/repair census = **3** (`GATE_REPAIR_STAGES`, pinned): `stage_gate_context` (outside the try, as inline) → `stage_gate_check` (parse + check + recast re-check) → `stage_gate_repair` (verdict events + the single bounded repair round + re-gate); the executor wraps check+repair in the historical try/except (`OUTPUT_GATE_ERROR` on any gate exception, turn proceeds ungated). The inline `critical` set literal is now module-level `turn_pipeline.GATE_CRITICAL_FAULTS` (frozenset, same 8 members).

**E3 — GateContext (the 18-arg seam is dead at both ends):** `output_gate.GateContext`, **18 fields** — exactly the historical signature (2 positionals + 16 keyword-only), census-pinned by `test_context_field_census_covers_the_18_arg_seam`: per-attempt `parts, visible, raw, require_recast, truncated`; turn-constant `is_open, already_asked, already_shown, mode, image_present, association_table, sheet, introduce_key, retrieval_failed_keys, learner_text, blank_zero, asked_topics, topic_nouns`. `check_output_gate(ctx: GateContext)` is the new surface; the legacy kwarg signature is a thin shim building the context — both funnel into `_check_output_gate(gctx)`, so **shim == context by construction**, additionally proven black-box by `TestGateContextParity` (fault-rich case: truncated + missing_recast + unscaffolded_new_item + probe_loop; plus a defaults case). All 51+ legacy-shape gate tests (test_output_gate/test_introduce_router/test_tutor_response/test_session_fixes) stayed green through the shim, unmodified in call shape. The conv_session call site builds ONE turn-constant GateContext from the TurnContext (`stage_gate_context`; retrieval_failed_keys still event-sourced from the typed DUE_OUTCOME_FAIL events) and the three per-attempt calls ride `dataclasses.replace` (parts/visible per parse; raw/truncated re-derived from the repair response; require_recast sticky) — no kwarg splat remains. The `_deaccent` half of E3 was already satisfied in Phase 2 (fold_lexical), verified still true. ModeContext was NOT needed: the mode-side inputs already travel as TurnContext fields + the ModeDecision object; recorded here so batch 4 doesn't hunt for it.

**TurnContext additions (census pin updated):** batch 3 added 13 fields — realize products `teach_images, image_decision, system, task, messages, final, raw, tool_delta, usage, error_result` + gate products `gate_ctx, gate_result, need_recast`. The post-family local unpack for the inline recorders/capture regions remains (batch-5 cleanup retires it); `intro_plan` now unpacks AFTER realize (downgrade-faithful).

**CHAR-BUG-002 RESOLVED (this batch's declared fix, per the known_bugs protocol — fix + pin flip + registry entry in one change):** single streak owner is `stage_english_streak` (counts the CURRENT turn before select — unchanged); modes guard 4 dropped its `eng_streak + 1` and reads `state.english_only_streak` only. **Behavior change:** the association hard break now requires a GENUINE ≥2 streak — the SECOND consecutive English-only turn — instead of firing on the first (no_entiendo path unchanged; stored streak values unchanged; non-english_only turns read identically). New pins: `test_char_bug_002_resolved_single_streak_owner` (end-to-end: turn 1 no break/streak 1, turn 2 association hard break/streak 2, golden on turn 2) + `TestEnglishStreak::test_char_bug_002_first_english_turn_no_hard_break`/`…second_english_turn_hard_breaks` (head-level). **Golden regen list (ONLY pins that carried the bug):** `golden_english_streak.json` (`977a64a5a4174f8e01cb3a5faf687fb5` → `8fe1c04ea629d0ae1d603651c7524397`) — the pinned break observation moved a turn later, exactly as declared. **Every other pin checked and byte-unchanged, with justification:** `golden_blank_zero_register_turn` (its English turn is guarded by the hard-break BUDGET — placement break < 3 turns — not the streak count; pinned mode was already conversation), `golden_budget_arc` (all breaks there are guard-6 noun associations, no english_only turns), `golden_comprehension_repair` (meta guard fires before guard 4 both before and after), remaining goldens have no english_only learner turns; `tests/test_modes.py` untouched (its guard-4 test seeds streak=2 explicitly — fires under both counts; the `esta calor` test carries spanish_ok); **evals checked per the brief:** `evals/conv_trajectories.py` pins NONE of the old behavior — c04 is the guard-6 noun association (`bote`, Spanish turn), c05 is the no_entiendo path, no trajectory sends an English-only turn expecting `english_stuck_association` — zero eval expectation edits. One companion adjust: `test_hard_break_and_repair_turns_get_no_soft_additions` now seeds streak=1 so its single English turn is a genuine second-consecutive break (was riding the double count, as its old comment admitted). **Goldens rollup md5: `0018747b24c7889d8ef2c5dcf48d8031` → `2c3d45bf74e33f873e6625f847496d51`** (12 files; delta = the 1 regenerated golden + known_bugs.json `f7e39708…` → `6a009ed2…`, all 10 other goldens byte-identical per before/after per-file md5 diff).

**Verification:** suite **718 passed** + 17 subtests, fully green (711 pre-batch + 7 new: realize/gate order contracts ×2, streak regression ×2, GateContext parity/defaults/census ×3; the streak char test and the INTRODUCE_DOWNGRADED source pin retargeted 1:1). `scripts/check_teacher_truncation.py` ok (14 files — full-history assembly now lives in `stage_prompt_build` under the same gate, no slices introduced). `import tutor.web_app` ok; evals import ok. `_execute_ai_tutor` **698 → 432 lines** (def-to-def; −266 this batch, 923 → 432 cumulative for Phase 4). **Server restarted this batch** (gate call surface + streak behavior changed): `/api/health` **stale_code false** (version `20260728-193216` == disk_version, teacher_mode planned). Nothing committed.

**Batch-4 reminder (next):** RECORDERS — sheet/_finish, introduce ledger, scaffold-saved first_seen, try/model + asked-topic memory writes, tutor-declared image, mode-state recorders, soft_plan snapshot, tail summary events, parts enrichment + notes projection as uniform TurnRecorder implementations; **CHAR-BUG-001 atomic-turn save is that batch's DECLARED delta** (one durable persist per successful turn at a recorder commit point — today's ≤3 conditional mid-turn saves are golden-pinned until then); **CHAR-BUG-005 scene_modeled re-route rides it** (golden re-routing plan owed with it); Machine A/B crossings become the recorders' consumed surface per the Phase 1.5 verdict.

---
## Phase 4 batch 4 landed (agent, 2026-07-29)

The RECORDERS stage family + the **atomic-turn save (CHAR-BUG-001 RESOLVED — this batch's declared delta, Grok round-1 (a) amendment BINDING)**. Structure change and the declared fix landed together at the family that owns the seam, per the batch-1 mapping; the **CHAR-BUG-005 declared fix was ATTEMPTED and STOPPED with evidence** per the batch brief's stop condition (details below — 001 landed alone, exactly as the brief prescribes for that outcome). Files: `tutor/turn_pipeline.py` (1,132 → 1,567 lines), `tutor/conv_session.py` (recorder region replaced by the stage loop; `_finish` save removed; new `_commit_sheet`), `tests/characterizations/known_bugs.json` (001 → RESOLVED; 005 stopped-note), `tests/test_turn_pipeline.py` (+4: recorder order contract + TestAtomicSheetCommit ×3; TurnContext census pin +4 fields), `tests/test_characterization_ai_path.py` / `tests/test_characterization_ai_arcs.py` (save pins flipped WITH the fix), 10 goldens regenerated. Nothing committed.

**Recorder census + order (verified against the family markers; matches the batch-1 re-derived inventory RECORDERS = 9; pinned by `test_recorder_sequence_matches_documented_list`):** `RECORDER_STAGES` = **finish → introduce_ledger → first_seen → memory_notes → declared_image → mode_record → soft_plan → tail_events → parts_notes** — the EXACT historical inline order (verbatim code moves incl. comments) — **plus `stage_sheet_commit` as the family's FINAL member** (the atomic commit point; 10 tuple entries = 9 census stages + the commit). Census note: the brief's sketch split "error-resolve + enqueue" from the mode-state recorder, but in the real code they are ONE contiguous region sharing the `resolved` local and the `elif Mode.TRANSFER` arm — extracted as one honest stage (`stage_mode_record`: hard-break note, form/recast cooldowns, the CHAR-BUG-005 scene_modeled site preserved as-is, error-resolve + first-time retrieval enqueue, last_mode); the brief's "progress emits" are not a standalone region either — the only in-family progress emit is the introduce ledger's `planted` milestone (inside `stage_introduce_ledger`; the sheet-crossing emits live inside `_finish`). `stage_finish` wraps `session._finish` (single caller verified: the turn pipeline). TurnContext grew exactly the recorder products: `result, phase_label, phase_note_key, soft_plan` (census pin updated).

**CHAR-BUG-001 RESOLVED — the atomic-turn save (per the binding declaration):** all mid-turn `save_sheet` sites collapsed to ONE commit point — `stage_sheet_commit` → `ConversationalSession._commit_sheet` (kept as a session method calling the module `save_sheet` binding so the Phase 0 harness's save-call recorder keeps its caller-name seam). Removed saves: `_finish`'s unconditional post-process_turn save + the three conditional `_execute_ai_tutor` saves (introduce-marked, wrote-first_seen, resolve-enqueue). The in-memory sheet still mutates through every stage; disk persists once per successful turn. **Crash-semantics note (declared, not hidden):** recovery changes from "last mid-turn save wins" to **"the turn commits or it doesn't"** — a crash mid-turn leaves the PREVIOUS turn's sheet on disk, never a half-written turn (an introduce can no longer be planted durably without the later writes); a model-call error returns BEFORE the recorder family, so failed turns persist nothing (unchanged); the `__init__`/`reset_sheet`/`close` saves outside the turn stay. New pins per the declaration's harness clause (commit-point FIELD SETS, not byte-identical intermediates): `TestAtomicSheetCommit` — exactly one `_commit_sheet` per successful turn; the single committed snapshot carries BOTH write families on the introduce turn (process_turn `updated_at` + the introduce schedule fields) and the first_seen bit without introduce fields on the scaffold-save turn (honesty law); disk == snapshot; a failed model call commits nothing.

**Golden regen list (ALL 10 goldens that pin save lists; per-file md5 old → new; structural before/after diff verified the save list is the ONLY delta in every file; `golden_budget_arc` pins no save list — byte-identical `8fde4b67f468a70d7f5d831120afe275`):**
- `golden_blank_open` `041a74fff7ef784551296b8b59c35b93` → `ba2815a1d2482ec804f0764f8e1747ea` (`['__init__','_finish']` → `['__init__','_commit_sheet']`)
- `golden_blank_zero_register_turn` `55aabbf63eb5cd3ef9aa7eae8ea26d23` → `ba2ce027a6241f97d7c3476c59b0d1f2` (`['_finish','_execute_ai_tutor']` → `['_commit_sheet']` — the first_seen «bien» save rides the commit)
- `golden_close_phase` `810269d2012878f4e917512a3aa9be89` → `94b97709d30b4ddc430a8812d1867109` (first_seen «adiós» save → commit)
- `golden_comprehension_repair` `9fa47325eb45aa39767d5d28756014e4` → `965ba50274ca4c0057c99b9748051afe` (both turns `['_finish']` → `['_commit_sheet']`)
- `golden_due_open` `c34d1fc83397ef4dd6219c01b28a4880` → `107caf9aa9d21d55a71db4b3f5ff0d0d` / `golden_due_turn` `22b5b084329e4e9ccbd05751430df493` → `0fddd60a3d0192a067094007eaaab43f`
- `golden_english_streak` `8fe1c04ea629d0ae1d603651c7524397` → `409025a7eb8318308c737c24de3c77dc` / `golden_gate_repair_turn` `29b51cbfb9c001ef65b21d0670c1db25` → `b215480d89f8fa11bf936f1090d5b9d9` (first_seen «mucho gusto» save → commit)
- `golden_introduce_open` `749f49b066a237ee742f9d28d57aec57` → `5ae4c9283c9bac5139595a53b32e3cba` / `golden_introduce_turn` `16b493cbaf29d6cc3250b993b77b7fcd` → `9811374aea0547c9d2d8030d2ce325dd` (the CHAR-BUG-001 two-site pin `['_finish','_execute_ai_tutor']` → `['_commit_sheet']`, inline assert flipped WITH the fix)

**Goldens rollup md5: `2c3d45bf74e33f873e6625f847496d51` → `ef5f731c7268107a16013de775557a95`** (12 files; delta = the 10 regenerated goldens + `known_bugs.json` `6a009ed2…` → `f0169d84bfcf621d4d5dcba6266f5162` (001 RESOLVED entry + 005 stopped-note)).

**CHAR-BUG-005 — STOPPED WITH REASON (the brief's stop condition met on the LAW branch).** The honest check was built and provisionally wired (mark `scene_modeled` only for scenes whose content appeared in the visible reply: word/phrase-boundary token-sequence match on `input.model_lines` (punctuation-tolerant) + multi-word `primary_exit` slot-evidence phrases; single common words (`hola`, `bebes`) deliberately insufficient; a scene_goal turn that realized the scene counts — verified: the comprehension-repair clear turn's «Estoy en el bote» honestly marks `boat_meet_captain`). The guard DID revive — and the measured re-routes are **unlawful per PEDAGOGY.md §6.4**: guard-7's prefer-unmodeled `+1` captures every zero-score turn, and the introduce/task/close content blocks are reason-gated to `INTRODUCE_FLAVORABLE_REASONS` (`known_open_from_sheet`, `default_conversation`) — spellings calibrated AGAINST the dead guard. Measured re-routes (char suite under the prototype, 7 failures): `golden_blank_zero_register_turn` (true-zero turn → `scene_goal:boat_likes`; TRUE-ZERO INTRODUCE + `SESSION PHASE: NEW INPUT` prefix gone), `golden_budget_arc` (ALL new_input turns → `scene_goal:boat_likes` on repeat — the introduce budget arc NEVER exercises: no plan on any learner turn, budget stuck at 2, R-G unreachable — §6.4 "introduce plan (new_input — owns the phase exclusively)" starved), `golden_close_phase` (`close_phase_offered` gone while `activity=close` — the close phase's content block starved), `golden_introduce_turn` + `test_notes_chronological_order` + `golden_gate_fault_repair` (introduce plan/mark pins gone), and the pick LOOPS (a bonus-picked scene stays unmodeled unless the model utters its lines — which the SCRIPTED-CONTENT DEBT migration will make rarer, so the loop worsens by design direction). **Fake-client trajectory evals: no NEW mechanical failures** (9/11 identical pre/post; c02 `<recast>` and c11 task-block fail identically both sides as canned-reply artifacts; c03's post-break turns `default_conversation`×3 → `scene_goal:boat_likes`×3, c07–c10 scene picks re-rank `boat_meet_captain` → `boat_where_boat` — all inside the allowed mode sets). So evals alone would not have stopped it; the §6.4 content-block starvation did. Prototype REVERTED; the pin (`test_char_bug_open_marks_all_scenes_modeled`) still passes on today's behavior (mark site now `turn_pipeline.stage_mode_record`, behavior unchanged); registry entry updated with the full stopped-note. **Owed before a retry: a select-mode/contributor policy countersign round** — make `scene_goal:*` introduce/task/close-flavorable, or subordinate the scene-needs-model bonus to the phase plan (frozen guard-chain change → PEDAGOGY §7.3 reopen-by-countersign, USER-visible).

**Verification:** suite **722 passed** + 17 subtests, fully green (718 pre-batch + 4 new). `scripts/check_teacher_truncation.py` ok (14 files). `import tutor.web_app` ok; evals import ok; fake-client trajectory run on the final code == the pre-batch baseline exactly. `_execute_ai_tutor` **432 → 138 lines** (def-to-def; −294 this batch, **923 → 138 cumulative for Phase 4**). **Server restarted this batch** (persistence behavior changed): `/api/health` **stale_code false** (version `20260729-115840` == disk_version, teacher_mode planned). Nothing committed.

**Batch-5 reminder (next, Phase 4 close):** CAPTURE/LOG — debug-ring + log stages; retire the local-unpack shim (stages/capture read ctx directly; the executor's remaining locals: `activity, decision, system, task, messages, final, usage, gate_result`); TurnContext gains the capture fields; then the **Phase 4 close verdict** — stage-list census complete (head 9 + contributors 5 + tick 1 + realize 8 + gate 3 + recorders 9 + commit + capture/log 2), `_execute_ai_tutor` reduced to the stage sequence, and the two owed policy rounds recorded as NOT Phase 4's: the CHAR-BUG-005 select-mode round (above) and CHAR-BUG-006's `require_relevant_to` threading.

---

## Phase 4 batch 5 landed — PHASE 4 CLOSED (agent, 2026-07-29)

The CAPTURE/LOG stage family + the cleanup sweep + this close verdict. PURE structure — behavior-identical on every path; **goldens byte-unchanged: rollup md5 `ef5f731c7268107a16013de775557a95` before AND after** (the exact batch-4 figure; `CHAR_GOLDEN_UPDATE` never set; known_bugs.json untouched — the CHAR-BUG-006 verdict below is queue-with-assessment, so no registry/golden delta). Files: `tutor/turn_pipeline.py` (1,567 → 1,619), `tutor/conv_session.py` (1,913 → 1,834), `tests/test_turn_pipeline.py` (+7). Nothing committed.

**Capture/log extraction (the final 2 census stages):** `CAPTURE_LOG_STAGES` = **stage_debug_capture → stage_log_turn** — the exact historical inline order (verbatim moves: the `_capture_debug_request` kwarg set and the `_log_turn_result` log_learner defaulting are byte-preserved, pinned by `TestCaptureLogStages`). **TurnContext gained ZERO fields** — the batch-1 reminder's "TurnContext gains the capture fields" turned out already satisfied: batches 3/4 carry every capture input (`system/task/messages/final/usage/gate_result/result`); the keep-it-lean census pin is unchanged at 32 fields. `_execute_ai_tutor` is now exactly: `begin_turn_log` → lazy stage imports → build ctx → head loop → `stage_contributors` → `stage_phase_tick` → realize loop → error-result early return → `stage_gate_context` + try(check, repair) → recorder loop → capture/log loop → `return ctx.result`. **Final measure: 138 → 63 lines def-to-def** (13 of them the docstring; ~50 executable).

**Cleanup sweep kill list (all behavior-identical, verified per item):**

| Class | Killed | Detail |
|---|---|---|
| (a) Family markers | **7 banner blocks** | the `# ---- PRE-MODEL HEAD/CONTRIBUTORS/PHASE TICK/REALIZE/GATE-REPAIR/RECORDERS/CAPTURE-LOG ----` banners in `_execute_ai_tutor` (~60 comment lines); the method docstring now carries the one-paragraph executor order and the stage tuples ARE the documentation. Zero `# ----` markers remain in conv_session. |
| (b) Locals-unpack bridge | **9 locals** | `activity, decision, result` (batch-1/4 shim) + `system, task, messages, final, usage, gate_result` (batch-3 shim) — all consumers now read ctx (the two capture/log stages were the last); verified per variable, and `test_locals_unpack_shim_is_retired` lints the bridge cannot creep back. |
| (b′) Dead imports | **5** | conv_session module head: `SimpleNamespace` (types), `Any` (typing), `load_pack` (corpus), `format_sheet_for_prompt` (character_sheet), `render` (turn_events) — each verified zero uses in-file AND zero re-export importers repo-wide (the stages carry their own lazy imports). `TurnEventLog`/`DEBUG_RING_SIZE` re-exports KEPT (live signature use / test importers). |
| (c) Delegates | **0 killed / 19 KEPT** | table below — NO delegate met the kill criterion (zero production readers). |
| (d) Orphans | **0 deleted / 2 spared** | importer-graph run over every function in conv_session + turn_pipeline: post-extraction, every stage/builder/helper has a production caller. The only zero-production-caller functions are `mark_introduced_if_visible` (Phase 3's deliberate historical-string contract — 14+ call sites in test_introduce_router/test_turn_events; not Phase-4 dead skin) and `build_session_phase_state` (the Phase 1 equivalence ORACLE — test_session_state proves `SessionState.fresh` builds the same plan against it; deleting it deletes the proof). Both SPARED with reasons, per the churn-discipline rule. |

**Delegate decision point (Phase 1 batch 1 layer — adjudicated NOW, per the batch-1 plan):** production reads (tutor/ + evals/ + scripts/, excluding session_state's own aggregate fields) vs test reads, attribute-name census: `pedagogy_memory` 34/62, `mode_state` 21/50, `task_state` 17/16, `costs` 12/22, `phase_state` 8/52, `_focus_meta` 7/0, `messages_for_ui` 6/7, `last_mode_decision` 6/5, `progress_session_id` 6/8 (+1 getattr in web_app), `_focus_panel` 5/1, `_focus_lock` 4/1, `history` 3/12, `_focus_key` 3/1, `_focus_inflight` 3/0 (+1 getattr), `_image_warm_inflight` 3/1, `_focus_version` 2/1 (+1 getattr), `_image_warm_lock` 2/1, `debug_requests` 1/21 (+1 getattr in web_app), `last_plan` 1/7. **Verdict: ALL 19 KEPT, ZERO killed** — the layer is not dead compatibility skin; it IS the production access idiom (turn_pipeline itself reads `session.pedagogy_memory`/`session.mode_state`/… through it). `test_delegate_census_is_the_adjudicated_kept_list` pins the 19-name census as the no-new-delegates lint.

**Re-measured:** `tutor/conv_session.py` **1,913 → 1,834** (−79: the marker banners, the bridge, the imports, the executor collapse); `tutor/turn_pipeline.py` **1,567 → 1,619** (+52: the two stages + family docs); 34 stage functions total in the module.

### Phase 4 close verdict

**Final stage census (complete — matches the batch-1 re-derived inventory exactly):** PRE-MODEL HEAD **9** + CONTRIBUTORS **5** (InstructionContributor instances under the `stage_contributors` loop, ONE `flavorable()` predicate, ONE `append_instruction()` mutation site) + PHASE TICK **1** (at its verified real site AFTER the contributors) + REALIZE **8** + GATE/REPAIR **3** + RECORDERS **9** + the atomic commit (`stage_sheet_commit`, batch 4's added stage) + CAPTURE/LOG **2** = the 37 census stages + the commit, realized as **34 named stage functions + 5 contributor instances** in `tutor/turn_pipeline.py`. `test_final_stage_inventory_complete_order` pins the full executor-order inventory (uniqueness + arithmetic included).

**Cumulative method shrink:** `_execute_ai_tutor` **923 → 63 lines** def-to-def (batch 1: 923→854; batch 2: →698; batch 3: →432; batch 4: →138; batch 5: →63 — **−93%**).

**What remains inline in the executor, and why:** (1) the `TurnContext` build (the executor owns its inputs); (2) the `ctx.error_result` early return (control flow — a family cannot return from its caller); (3) the gate try/except with the `OUTPUT_GATE_ERROR` emit (the historical semantics put the family BOUNDARY around check+repair but not context-build — the executor owns that boundary; encoding it inside a stage would change what an exception in context-build does); (4) the `begin_turn_log` call (rides the ctx build, never counted as a stage). Nothing else — no locals, no markers.

**E3 verdict:** **GateContext DONE** (batch 3 — the 18-arg seam dead at both ends, shim == context by construction, parity-tested; `_deaccent` half satisfied since Phase 2). **ModeContext NOT NEEDED** — recorded in batch 3, re-confirmed at close: `stage_select_mode` still passes mode-side inputs from TurnContext fields + session aggregates and the decision travels as the ModeDecision object; batches 4–5 added no mode-arg seam. E3 CLOSED with one context object instead of two, by evidence.

**CHAR-BUG-006 verdict — QUEUED with assessment (not this batch's fix):** the extraction did NOT make the fix trivial, and the one-paragraph assessment is: the seam is now obvious (`stage_fallback_image`'s `relevant_to` is an explicit named parameter at a single site — the mechanical edit is ~5 lines) but no ≤20-line change is behavior-safe, because (i) threading the repair-path recipe (`learner + targets.model_lines`) cannot fix the bug — the incident concept («hola») comes FROM the scene's suggested `model_lines`, which is exactly the dishonest text base the registry describes; (ii) an honest pre-call base (learner text only) would also veto legitimate scene-image picks («bote») — a select/image policy narrowing, not a refactor; (iii) a post-call re-check can't ride the extraction either: `stage_prompt_build` threads `ctx.teach_images` INTO the prompt, so the model is told about the image pre-call — post-hoc dropping creates prompt/reply incoherence, and the miss-note + async warm fire pre-call in the same stage. The registry's prescribed fix point ("Phase 4's contributor stage") also proved wrong — the site landed in REALIZE. Verdict: 006 stays in the fix-PR queue as a **policy round** (which relevance base is lawful on scene/conversation turns), to be run WITH or alongside the 005 select-mode round below. Goldens untouched.

**Carried forward out of Phase 4:** (1) the **CHAR-BUG-005 select-mode countersign round** (owed per the batch-4 stopped-note: make `scene_goal:*` phase-flavorable or subordinate the scene-needs-model bonus — frozen guard-chain change, PEDAGOGY §7.3 reopen-by-countersign, USER-visible); (2) **CHAR-BUG-006** as queued above (same policy neighborhood — run the two rounds together); (3) **Phase 5 inventory collapse** as planned (association_table sidecar schema; the four stray concept lists derive from table queries; the `PlanCard` image-decision DTO shape the E4 countersign kept load-bearing gets replaced there); (4) Phase 6-class leftovers: none new — this batch's orphan scan found zero deletable dead skin beyond the two SPARED oracles.

**Verification:** suite **729 passed** + 17 subtests, fully green (722 pre-batch + 7 new: capture/log order contract, final-inventory contract, capture/log units ×3, delegate-census lint, locals-bridge lint). **Goldens rollup md5 `ef5f731c7268107a16013de775557a95` unchanged** (12 files, per-file identical). `scripts/check_teacher_truncation.py` ok (14 files — the capture/log stages moved WITHIN gated files). `import tutor.web_app` ok; evals imports ok. **No server restart — nothing to prove live:** zero behavior change (006 queued, not landed; pure structure + dead-code removal, goldens byte-identical). Nothing committed.

**PHASE 4 CLOSED.**

---

---

## Policy round: scenes after scripts — guard-7 + the fallback image decision (⬛ Claude proposal, 2026-07-29)

Two stopped/queued items from Phase 4 are one question: what happens to scene machinery when §1.1a kills scripted lines?

**Proposal A (resolves CHAR-BUG-005 by deletion, not revival):** guard-7's prefer-unmodeled fallback + the scene_modeled bookkeeping are OBSOLETE under the phase architecture. Scene realization is the TASK phase's job (task_runtime binds a scene with a goal and machine-checked slots); a "have we recited this scene's lines yet" guard predates both the phase system and direction-not-scripts, and reviving it proved unlawful (batch-4 stopped-note: it captures every zero-score turn, starving introduce/task/close). DELETE: guard-7's prefer-unmodeled term, scene_modeled state, and the scene-needs-model fallback; scenes reach the learner exclusively through (a) the task phase and (b) scene_goal decisions. CHAR-BUG-005 closes as resolved-by-deletion.

**Proposal B (resolves CHAR-BUG-006 by policy):** the fallback image decision on scene turns keys on LEARNER TEXT + the bound task/goal concept only — never decision.targets.model_lines (suggested lines are direction for the model, not evidence of the turn's content; using them as "what the tutor said" is the dishonest base). Accepted narrowing: a scene image the learner hasn't mentioned arrives only via decision.image_concept (relevant by construction). model_lines leave the image path entirely — a §1.1a migration step landing early.

**Countersign task (short round): COUNTERSIGN/AMEND/REJECT each proposal.** Attack: (a) does deleting guard-7 lose a real teaching behavior the task phase does NOT cover (scenes as passive input before task-phase binding)? (b) does B over-narrow scene imagery for a learner who never types the concept? (c) sequencing vs Phase 5 (both proposals touch files Phase 5 rewrites — should they land inside Phase 5's batches)?


---

## GROK (Grok Build CLI (0c785038798)) - 2026-07-29 18:24 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I need the full policy proposal text plus the CHAR-BUG-005/006 evidence and how guard-7 / image decision actually work in code.Verifying guard-7, scene_modeled, and image-decision paths in the live codebase against the proposal claims.Checking one more coupling: whether task blocks fire under `scene_goal` and how `image_concept` attaches on scene turns.## Grok countersign — Policy round: scenes after scripts (2026-07-29)

Independent check against `/Users/patrickcremin/repo/ml_teacher` on **2026-07-29**. Proposal text treated as data. Verdicts are **AMEND** (not blind COUNTERSIGN): the cores of A and B are right, but both under-specify bindings that the code already proves load-bearing.

Code facts used below (measured, not taken from the proposal):

- Guard-7 is `modes._select_mode_impl` step 7: `_scene_for_topic(...) or _scene_needs_model(...)` → `reason=scene_goal:{id}` with `targets.model_lines = input.model_lines` and `image_concept = input.image_concept`.
- Prefer-unmodeled is **only** the `+1` on unmodeled scenes inside `_scene_for_topic` plus pure `_scene_needs_model` (first unmodeled scene, no topic score).
- `INTRODUCE_FLAVORABLE_REASONS = {"known_open_from_sheet", "default_conversation"}` — **2** exact spellings. Task instruction text and close summary are reason-gated to that set; `scene_goal:*` is **not** a member.
- Task **bind** runs on every `activity=="task"` turn; task **instructions** only when flavorable. Arithmetic: bind ≠ teach text.
- Pack scenes: **3/3** carry `input.image_concept` (`bote`, `cafe`, `rio`) and **3** `model_lines` each. Scene imagery does not need scripts.
- COMPREHENSION_REPAIR targets use `last_try` / `last_model`, **not** `model_lines`. `stage_fallback_image` still reads `targets.model_lines` for both `tutor_models` and repair `relevant_to`.
- Phase 4 batch-4 revival: needs_model alive → introduce budget stuck at **2**, **0** introduce plans on `golden_budget_arc` new_input turns (starvation of §6.4 exclusive introduce ownership). That is the unlawful behavior class.

---

### Attack (a) — Does deleting guard-7 lose teaching the task phase does not cover?

**Partial yes if “guard-7” means the whole step; no if it means only prefer-unmodeled / needs_model.**

| Path | What it does | Covered by task phase? |
|---|---|---|
| `_scene_needs_model` (no topic score) | Force any unmodeled scene → `scene_goal` | **No useful teaching.** Captures zero-score turns; starves introduce/task/close. Unlawful when alive (batch-4). |
| Prefer-unmodeled `+1` | Tie-break / nudge toward unmodeled when topic already scores | Cosmetic ranking only; load-bearing only if marks are honest. |
| `_scene_for_topic` keyword match | Passive scene pursuit when learner mentions boat/likes/location | **Not covered by task bind alone.** Task contributor only runs at `activity=="task"` and binds first task-capable open scene by pack order, not by live topic. Topic match is the pre-task / free-chat passive CI path. |
| Task contributor | Bind scene + slot eval + (if flavorable) task block | Machine-checked info-gap only in **task** activity. |

**Today CHAR-BUG-005 already kills needs_model for the whole session** (open marks all open scenes → `_scene_needs_model` returns `None`). Deleting needs_model + `scene_modeled` + the `+1` is mostly **documenting de facto behavior** and preventing a lawful-looking revival. It does **not** remove topic-matched `scene_goal`.

**Hole in Proposal A as written:** “scenes reach exclusively through (a) task phase and (b) scene_goal decisions” keeps `scene_goal`, but **task/close/introduce instruction blocks refuse `scene_goal:*`**. So a live topic match during task phase **binds** a scene and **withholds** the task block — the opposite of “task phase owns scenes.” Deletion of needs_model alone does not fix that seam.

---

### Attack (b) — Does B over-narrow scene imagery?

**No, not for the current pack — if `decision.image_concept` remains the scene-image channel.**

- Mode attach (`stage_mode_image` → `_attach_mode_image`) keys on `decision.image_concept`.
- Guard-7 already sets `image_concept` from `input.image_concept` on all **3/3** scenes.
- Learner never types «bote»: image still arrives via `image_concept=bote`, not via parsing `model_lines`.
- Dishonest path is exactly CHAR-BUG-006: cache miss on `bote` + fallback `tutor_models=model_lines` → e.g. «hola» from boat_meet_captain scripts → second miss note / wrong warm.

B’s accepted narrowing is the right contract. Over-narrowing would only appear if someone later drops `input.image_concept` without another code-owned concept (table key / goal form). That is a Phase 5 inventory risk, not a reason to keep scripts on the image path.

**Nuance:** ban **scene** `model_lines` from the image path, not “any prior Spanish forever.” Repair’s real prior performance lives in `last_model`/`last_try`, not `targets.model_lines`. B’s wording must not accidentally forbid a future repair relevance base of **actual** prior tutor Spanish.

---

### Attack (c) — Sequencing vs Phase 5

| Item | Touches Phase 5 rewrite surface? | Land where? |
|---|---|---|
| **A** (`scene_modeled`, modes guard-7 subset, mark site in `stage_mode_record`) | **No** (select/mode_state; not association_table / CONCEPT_LEXICON / PlanCard DTO) | **Own micro-batch now**, before Phase 5. Prevents accidental needs_model revival while scenes are migrated. |
| **B** (`stage_fallback_image` / `assets_for_ai_turn` contract) | **Yes** (Phase 5 rewrites image inventory + PlanCard image DTO) | **Pin-first policy PR (or Phase 5 batch-0 contract)** with a regression test: `model_lines` never supplied as `tutor_models` / relevance text. **Do not** wait for full inventory collapse; **do not** land mid-batch after table rewrites without the pin. |

---

## Proposal A — **AMEND** (core COUNTERSIGN; do not ship as written)

### Verdict
**AMEND.** Resolve CHAR-BUG-005 by **deletion of prefer-unmodeled bookkeeping**, not by reviving honest marks. Keep topic-matched scene pursuit. Fix the flavorable/phase seam the proposal leaves open.

### Exact replacement text (drop-in for the proposal paragraph)

```markdown
**Proposal A (resolves CHAR-BUG-005 by deletion + phase host rules, not revival)
— AMENDED 2026-07-29:**

Guard-7's *prefer-unmodeled* machinery is obsolete and unlawful when alive.
Scene realization for info-gaps is the TASK phase's job (task_runtime binds a
scene with machine-checked slots). A "have we recited this scene's lines yet"
ledger predates phases and §1.1a; reviving honest `scene_modeled` marks
re-enabled `_scene_needs_model` and starved introduce/task/close (Phase 4
batch-4 stop: introduce budget stuck at 2, 0 introduce plans on budget-arc
new_input turns).

DELETE (only these):
1. `ModeSessionState.scene_modeled` (field + snapshot/from_snapshot).
2. Prefer-unmodeled `+1` inside `_scene_for_topic`.
3. `_scene_needs_model` and every `or _scene_needs_model(...)` call site.
4. The mark loop in `stage_mode_record` that adds `decision.scene_ids` to
   `scene_modeled`.

KEEP:
5. `_scene_for_topic` keyword scoring → `reason=scene_goal:{id}` (passive /
   live-topic scene pursuit is NOT provided by task bind order alone).

PHASE HOST (required; otherwise scene_goal still starves §6.4 blocks):
6. Do **not** run topic scene pick when `activity_hint ∈ {"new_input", "close"}`
   (introduce owns new_input; close owns close). Fall through to
   `default_conversation` so flavorable content blocks fire.
7. Expand task (and only task) instruction gating so reasons matching
   `scene_goal:` are flavorable **when** `activity == "task"`, e.g. reason in
   INTRODUCE_FLAVORABLE_REASONS OR reason.startswith("scene_goal:") under
   task activity. Close remains exact-set only. Introduce remains
   new_input + existing exact set (scene pick already suppressed there).

Scenes reach the learner through:
- (a) task phase bind + task block (slot goals, private values, never scripts);
- (b) topic-matched `scene_goal` on activities that may host it (task / free /
  retrieval after higher guards; never new_input/close).

CHAR-BUG-005 closes as **RESOLVED-BY-DELETION** of the mark/needs_model
machine. Registry: flip pin
`test_char_bug_open_marks_all_scenes_modeled` to assert the field/mark site
are gone (or that open no longer writes scene_modeled). Goldens that already
ride the dead-guard fallthrough stay green if (6) holds; any golden that
depended on forced unmodeled capture must not be reintroduced.
```

### Rejected alternatives (explicit)
- **REJECT** deleting all of guard-7 including `_scene_for_topic` — loses live-topic passive scene input; task bind is pack-order first scene, not topic-aware.
- **REJECT** revival of honest `scene_modeled` + needs_model without phase subordination — already measured unlawful (§6.4).
- **REJECT** “only delete needs_model, leave flavorable set unchanged” — leaves task-phase `scene_goal` silent on task text (bind without teach block).

---

## Proposal B — **AMEND** (core COUNTERSIGN; tighten wording)

### Verdict
**AMEND.** Ban scene `model_lines` from the image decision path. Keep code-owned `decision.image_concept` (and learner text) as the lawful base. Does not over-narrow current pack (3/3 scenes have `image_concept`).

### Exact replacement text

```markdown
**Proposal B (resolves CHAR-BUG-006 by policy) — AMENDED 2026-07-29:**

Pre-call image decision must never treat scene `input.model_lines` (or
`decision.targets.model_lines` copied from them) as "what the tutor said."
Those strings are §1.1a-forbidden performance scripts / direction residue, not
evidence of this turn's content. CHAR-BUG-006 class: scene wants «bote»,
fallback extracts «hola» from boat_meet_captain's suggested lines → dual miss
notes / wrong warm.

Image relevance base (conversation / scene / association / placement):
1. **Primary:** `decision.image_concept` when set (scene input.image_concept,
   association noun, placement open key) — relevant by construction; mode
   attach owns cache hit/miss + single miss note for that concept.
2. **Secondary (fallback only):** learner text (+ signals already used).
3. **Forbidden on the image path:** `targets.model_lines`, scene
   `input.model_lines`, or any other authored script list passed as
   `tutor_models` / `require_relevant_to`.
4. **Repair exception (actual performance, not scripts):** if a relevance
   string is needed for COMPREHENSION_REPAIR, use learner text and/or
   `targets.last_model` / `targets.last_try` (session memory of prior tutor
   Spanish) — never scene model_lines. Today's repair targets do not set
   model_lines; do not reintroduce that key for scripts.

Accepted narrowing (intentional): a scene image the learner has not typed
arrives **only** via `decision.image_concept` (or a future table-derived
equivalent). No image from parsing suggested lines. When image_concept is
unset and learner text has no imageable concept → no image (async warm only
for concepts the code already decided).

`model_lines` leave the **image path** entirely. Removing them from
realization prompts remains the separate §1.1a / SCRIPTED-CONTENT migration
(do not claim B finishes that debt).

Pin (same PR): unit or golden assertion that
`stage_fallback_image` / `assets_for_ai_turn` is not called with scene
model_lines as tutor_models on a scene_goal turn; dual miss-note
(hola+bote) incident class does not recur.
```

### Rejected alternatives
- **REJECT** “thread `require_relevant_to=learner+model_lines`” as the 006 fix — that **is** the dishonest base (registry + batch-5 assessment).
- **REJECT** post-call drop of a pre-call attached image — prompt already told the model about the image (`stage_prompt_build`); creates prompt/reply incoherence.
- **REJECT** deferring B until full Phase 5 inventory collapse without a pin — live incident class; Phase 5 must inherit the ban, not rediscover it.

---

## Sequencing — **AMEND** (answer to attack c)

```markdown
**Sequencing (binding):**
1. **Proposal A micro-batch first** (modes.py + mode_state snapshot + 
   stage_mode_record mark deletion + flavorable/phase-host rules + registry
   flip). Not a Phase 5 batch. Independent of association_table/PlanCard.
2. **Proposal B pin-first next** (or Phase 5 batch-0 "image relevance
   contract"): stage_fallback_image + call-site contract + regression pin.
   Then Phase 5 inventory batches may rewrite teach_assets/PlanCard only if
   the pin stays green.
3. **Do not** fold A into Phase 5. **Do not** ship B only as a side effect
   of table fill. **Do not** reorder so Phase 5 concept-list migration runs
   before the model_lines image ban pin.
```

---

## Item-by-item scorecard

| Item | Verdict | One-line reason |
|---|---|---|
| **A — delete needs_model / scene_modeled / prefer-unmodeled** | **COUNTERSIGN** (as subset) | Dead or unlawful; task bind + topic match cover real teaching |
| **A — as written (“guard-7 obsolete”, no phase-host/flavorable fix)** | **AMEND** | Must keep `_scene_for_topic`; must host `scene_goal` under task without starving blocks; suppress pick on new_input/close |
| **B — ban model_lines from image decision** | **COUNTERSIGN** core | §1.1a + CHAR-BUG-006; 3/3 scenes have `image_concept` |
| **B — wording / repair nuance / pin** | **AMEND** | Exact bases + repair uses last_model/last_try not scripts + same-PR pin |
| **(a) teaching loss** | **Answered** | Needs_model: no loss. Whole guard-7: yes loss. Topic match: keep. |
| **(b) over-narrow** | **Answered** | No for current pack if image_concept channel kept |
| **(c) vs Phase 5** | **AMEND** | A now; B pin-first / Phase 5 batch-0; not buried mid-inventory |

---

## Close conditions (for the proposal to become final)

1. Replacement paragraphs for A and B above replace the 2026-07-29 Claude proposal text in `docs/reviews-architecture-refactor.md` (append this countersign; do not rewrite prior authors).
2. A implementation checklist matches DELETE 1–4 + KEEP 5 + PHASE HOST 6–7.
3. B implementation never passes scene `model_lines` into `assets_for_ai_turn`; pin lands same PR.
4. CHAR-BUG-005 → RESOLVED-BY-DELETION; CHAR-BUG-006 → RESOLVED with pin; no PEDAGOGY law text duplicated here — point at §1.1a / §6.4 only.

**Round status:** ready to implement under the AMENDED text; **not** ready under the unamended Claude paragraphs alone.

---

## Policy round adjudication (⬛ Claude, 2026-07-29) — ACCEPT BOTH AMENDMENTS; sequencing binding

Grok's amended texts are BINDING over my proposals. Accepted in full, with the catches recorded:

1. **A:** my "delete guard-7" over-deleted — topic-matched scene pursuit (`_scene_for_topic` keyword scoring) is real passive-CI teaching the task bind order does NOT cover, and stays. What dies is exactly the prefer-unmodeled machine (scene_modeled field, the +1, _scene_needs_model, the mark loop). And my proposal missed the flavorable/phase-host seam entirely: scene picks are now suppressed on new_input/close activities (introduce and close own those), and the task block becomes flavorable for scene_goal reasons under task activity — "task phase owns scenes" made true by gating, not slogan. CHAR-BUG-005 closes as resolved-by-deletion WITH host rules.
2. **B:** the model_lines image ban adopted with Grok's nuance — repair relevance may use actual prior performance (last_model/last_try), never authored scripts; post-call image dropping correctly rejected (prompt incoherence); the pin lands BEFORE Phase 5's inventory batches so the rewrite inherits the ban.
3. **Sequencing accepted as binding:** A = own micro-batch now (no Phase 5 surface); B = pin-first, after Phase 5 batch 1 lands (teach_assets collision) and before batch 2 flips lists.

A micro-batch dispatched 2026-07-29.

---

## Proposal A micro-batch landed (agent, 2026-07-29)

Executed per Grok's BINDING amended text (DELETE 1–4, KEEP 5, PHASE HOST 6–7). Files: `tutor/modes.py`, `tutor/turn_pipeline.py`, `evals/run_conv_smoke.py`, `tests/test_modes.py`, `tests/test_turn_pipeline.py`, `tests/test_session_state.py`, `tests/test_characterization_ai_arcs.py`, `tests/characterizations/known_bugs.json`, `tests/characterizations/golden_comprehension_repair.json`. (Parallel-agent surface untouched: `teach_assets.py` / `association_table.py` / `course_packs/`; Proposal B not started.)

**Deletions (items 1–4), all executed:**
1. `ModeSessionState.scene_modeled` — field, `snapshot()` key, `from_snapshot()` restore (legacy snapshots with the key are ignored). The SessionState aggregate surface composes `**ms.snapshot()`, so it lost the key with no separate edit.
2. The prefer-unmodeled `+1` inside `_scene_for_topic` (plus the vestigial modeled-scene `pass` block); the now-unused `state` parameter dropped from its signature.
3. `_scene_needs_model` (whole function) and its only call site, guard 7's `or _scene_needs_model(...)` fallback.
4. The `decision.scene_ids` → `scene_modeled` mark loop in `stage_mode_record` (the CHAR-BUG-005 site). Also: `evals/run_conv_smoke.py::_apply_mode_state` lost its `scene_modeled` seeding branch (no trajectory seeds it).

**KEEP (item 5):** `_scene_for_topic` keyword scoring → `reason=scene_goal:{id}` intact — pure topic match now; no match, no scene (the deleted fallback can no longer force a zero-score capture even with fresh, unmarked state — pinned).

**PHASE HOST rules, implementation sites:**
- **Rule 6** — `modes._select_mode_impl` guard 7: the topic pick runs only when `activity_hint not in ("new_input", "close")`; otherwise fallthrough to `default_conversation` so the flavorable content blocks fire. `_select_mode_impl`'s docstring now records this as the ONE adjudicated exception to "guards ignore the hint".
- **Rule 7** — `turn_pipeline._task_build` (the contributor census confirmed this is where the task text gate lives; `flavorable()` itself and `INTRODUCE_FLAVORABLE_REASONS` unchanged): the task-block condition is now spelling-C `flavorable(...)` OR (`ctx.activity == "task"` AND mode conversation AND `reason.startswith("scene_goal:")`) — the activity term asserted explicitly per the binding text even though `_task_eligible` already guarantees it. Close (`_close_summary_eligible`) exact-set only, unchanged; introduce unchanged (rule 6 suppresses the pick on new_input anyway).

**Golden outcomes (old rollup md5 `ef5f731c7268107a16013de775557a95` → new `08aff507ee84bcb073ed7166cf446207`, delta = 2 of 12 files):**
- **Byte-identical (10):** blank_open, blank_zero_register_turn, budget_arc, close_phase, due_open, due_turn, english_streak, gate_repair_turn, introduce_open, introduce_turn — exactly the binding text's prediction: every golden riding the dead-guard fallthrough stayed green under rule 6 (the `+1`/needs_model deletions are behavior-neutral where CHAR-BUG-005 had already marked everything at open, and pure keyword scoring reproduces the historical picks). `golden_due_turn` keeps its lawful `scene_goal:boat_likes` (retrieval activity hosts the pick).
- **Regenerated (1): `golden_comprehension_repair.json`** (`965ba50274ca4c0057c99b9748051afe` → `08d07b66c92c53535f5aec440ba7f176`). Justification: its clear turn («Estoy contento.») rides the NEW_INPUT activity and topic-matched `scene_goal:boat_meet_captain` under the old guard 7; rule 6 now lawfully re-routes it to `default_conversation` + `introduce_planned:hola:R-E`. Lawfulness check vs PEDAGOGY §6 / the batch-4 stopped-note: this is the exact INVERSE of the unlawful class — an introduce plan now FIRES on a new_input turn that previously carried none (no introduce starvation, budget consumable, R-G reachable); close_phase_offered intact (golden byte-identical); true-zero SESSION PHASE prefix intact (golden byte-identical); no pick loops (the pick needs a live topic match and never runs on new_input/close). No STOP condition met. Side effect recorded in the registry: the re-route displaces CHAR-BUG-006's dual-miss-note host turn from this golden (bote/hola miss pair now asserted ABSENT there); 006 stays OPEN — `stage_fallback_image` still reads `targets.model_lines`, and scene_goal turns still occur on task/free/retrieval — the Proposal B pin-first batch owns it.
- **known_bugs.json** `f0169d84bfcf621d4d5dcba6266f5162` → `b72533641507e0168828eae005234f13` (005 flip + 006 displacement note).

**Registry:** CHAR-BUG-005 → **RESOLVED-BY-DELETION** (+ host rules), WAS/NOW behavior text, pinned_by updated to the flipped pin + the two new host-rule test classes. CHAR-BUG-006: pinned_by records the displacement; resolution now points at the adjudicated Proposal B text (pin-first, after Phase 5 batch 1, before batch 2).

**Tests added/flipped:**
- `test_char_bug_open_marks_all_scenes_modeled` FLIPPED: asserts field + snapshot keys + `_scene_needs_model` are GONE, plus an ast-level deletion lint (no Name/Attribute/def/exact-string reference to `scene_modeled` / `_scene_needs_model` in `tutor.modes` or `tutor.turn_pipeline`; prose mentions allowed).
- `tests/test_modes.py::TestSceneHostRules`: pick suppressed on new_input (NEW INPUT prefix present) and close (CLOSE prefix present); `scene_goal:*` reachable on task/free/retrieval/None; zero-score turn falls through (needs_model deletion pinned behaviorally).
- `tests/test_turn_pipeline.py::TestSceneGoalTaskSeam`: task block ("TASK (single convergent exit") + TASK_GOAL_OFFERED fire on `scene_goal:boat_likes` under task activity (the bind-without-teach seam Grok caught, closed); the scene_goal clause is task-activity-only; close gate refuses scene_goal.

**Verification:** suite **752 passed + 17 subtests, fully green** (`.venv/bin/python -m pytest tests/ -q`). `scripts/check_teacher_truncation.py` ok (14 files). `import tutor.web_app` ok. Server restarted (behavior changed); `/api/health`: `stale_code: false`, version `20260729-123544`. Nothing committed.

---

## Phase 5 batch 1 landed (agent, 2026-07-29)

Inventory-collapse prerequisite per Grok's round-1 (b) amendment (BINDING, docs/reviews-direction-not-scripts.md §(b)): **table fill + asset sidecar — DATA + LOADER only; the list-derivation flip is batch 2.** Files: `course_packs/spanish_a1/association_table.json` (+15 entries, appended — existing entries byte-untouched, order preserved because table order is behavior-bearing for `candidate_keys` buckets and the `_topic_nouns` palette), **NEW** `course_packs/spanish_a1/asset_sidecar.json` (10 entries), **NEW** `course_packs/spanish_a1/migration_deprecations.json` (1 entry), `tutor/teach_assets.py` (sidecar loader + effective-lexicon overlay), `tutor/modes.py` + `tutor/session_memory.py` (function-local concept lists hoisted to module constants `NOUN_TEXT_PAIRS` / `NEW_CONCRETE_NOUNS` / `SPANISH_CONCEPT_PAIRS` — pure code motion so the coverage gate can enumerate them), **NEW** `tests/test_inventory_coverage.py` (16 tests). Ran CONCURRENTLY with the Proposal A micro-batch above — zero file collisions (their surface: modes scene machinery / turn_pipeline / goldens; ours: pack data / teach_assets / list hoists; both edit sets verified coexisting, suite green on the merged tree).

**Coverage audit (the 80% gap was the floor, not the ceiling).** Union of every concept in the six lists (+ `_new_concrete_noun`, observe's `topic_vocab` class, scene `image_concept`s), folded via `fold_asset_key` against the 175-key table: **16 concepts missing**, not 4 — `bote`, `barco`, `música`, `comida`, `río`, `playa`, `sol`, `edificio`, `perro`, `gato`, `desayuno`, `calor`, `frío`, `estoy_bien`, `soy_de`, `me_gusta`. (Already covered: ciudad, casa, café, agua, pan, trabajo, familia, hola, me llamo.) The **reverse gap** confirmed too: casa/ciudad — and every other imageable table key — have no sidecar asset entry; guard-6 can still fire with no image metadata behind them (today `_default_prompt` synthesizes; batch 2's selection flip must decide sidecar-less-key handling explicitly).

**Table fill: 15 entries added** (r7 rules: gloss ≤6 words, anchors judged honestly — cognates bote/boat, música/music, sol/solar, edificio/edifice, calor/calorie, frío/frigid; curated keywords barco/embark, comida/comestible, desayuno/break-the-ayuno, río/Rio Grande, me gusta/gusto; comida gets NO cognate per the adjudicated judgment; playa/perro/gato/soy de plain gloss). **14 are `in_pack: false`** — honest per pack.md (bote/barco/río/playa/sol/edificio/perro/gato are persona-world/off-inventory nouns; música/comida/desayuno fall under "food/drink noun sets beyond Unit 5's closed production set" + unlisted vocab; calor/frío weather is out of scope, tener-idioms explicitly deferred in U6; **me gusta** is out of pack scope — boat_likes' own primary_exit says "NO gustar"). NOTE per the brief: these keys stay valid for observation/asked-topics/asset lookups but are introduce-router-ineligible and gate-scan-inert (`_eligible` and `scan_unscaffolded_new_items` both skip `in_pack:false`) — and at the batch-2 flip they deliberately drop OUT of association selection (imageable ∧ pack-legal), which IS the setting-palette de-privileging of the boat world, not a loss. **1 in-pack entry: `soy de`** (introductions, U3 ser+origin — honest). All 15 pass loader validation; loader untouched.

**Declared live-surface deltas (data-driven, none golden-pinned — per amendment (a) these are declared, not hidden):** (1) `soy de` joins the gate's unscaffolded-scan inventory (a bare un-glossed "soy de" first exposure now faults/records like any in-pack formula; no golden or test fixture contains the phrase — verified). (2) The `_topic_nouns` palette gains 4 strings ("me gusta", "soy de", "calor", "frío" — the other 11 were already present via TOPIC_CONCEPT_NOUNS); asked-topic keys can now bind them when a question frame co-occurs. (3) `forbid_cluster_with` (R-F, no in_pack filter) grows for introductions-theme plans (+ soy de) and food-theme plans (+ comida, desayuno) — R-F-lawful widening. (4) Progress-rail display names resolve the new keys' glosses (display only).

**Asset sidecar:** `asset_sidecar.json`, **10 entries = CONCEPT_LEXICON migrated verbatim**, keyed by TABLE keys (hola, me llamo, soy de, café, bote, música, comida, me gusta, río + the one deferred key below); `prompt`→`image_prompt` rename per the amendment's schema language; aliases preserved exactly (including legacy free-text lookups); `file` present only where the lexicon had it (hola, estoy bien, me llamo — cache filenames unchanged because `fold_asset_key(table_key)` = the legacy asset id, pinned by test). Loader `teach_assets.load_asset_sidecar` validates schema AND the key law: **every sidecar key must be an association-table key or on the deprecation list — a sidecar can never mint concepts** (ValueError lists all offenders; `_`-prefixed comment keys skipped). `sidecar_lexicon()` returns the CONCEPT_LEXICON shape; `_lexicon()` = `{**CONCEPT_LEXICON, **sidecar}` wired at all 13 internal read sites — **CONCEPT_LEXICON stays this batch as the fallback (batch 2 deletes it)**; a missing/invalid sidecar degrades to the in-code lexicon, never a crash (association-table posture). `image_gen.py` still imports CONCEPT_LEXICON directly — parity makes it moot; batch 2 migrates it. **Parity proof (pinned):** `sidecar_lexicon(pack) == CONCEPT_LEXICON` exact dict equality on all 10 legacy keys AND `_lexicon() == CONCEPT_LEXICON` — the overlay is behavior-neutral by construction.

**Deprecation list: 1 entry — `estoy bien` (status `deferred_table_entry`), the batch's one honest impossibility.** Adding it as an in-pack table key is measurably a behavior flip: the gate's longest-match overlap filter would keep "estoy bien" over "bien" in golden_blank_zero_register_turn's pinned reply — `scaffold_saved {bien: gloss}` → `{estoy bien: gloss}`, `first_seen:bien` → `first_seen:estoy bien`. Forbidden in a data+loader batch; marking it `in_pack:false` instead would be dishonest data (the wellbeing exchange IS pack content). Recorded with reason + owed action: batch 2 (or a fix PR) adds the entry WITH the declared gate delta and golden re-pin, or countersigns a formula-asset carve-out. No eval references `estoy_bien` (verified) — no eval update owed. The sidecar carries its asset under the deferred key, sanctioned by the record.

**Coverage gate as a test (§1.1a migration rule, executable):** `tests/test_inventory_coverage.py::CoverageGate` — every concept in TOPIC_CONCEPT_NOUNS, NOUN_TEXT_PAIRS (concept side; needles are §1.1a class-iv detection text), NEW_CONCRETE_NOUNS, ASSOCIATION_NOUNS, SPANISH_CONCEPT_PAIRS (concept side), CONCEPT_LEXICON keys, observe's topic_vocab class (hand-listed + a drift guard asserting each surface still fires the signal), and scene image_concepts must fold into table keys ∪ deprecation keys; plus the deprecation list stays ≤3, documented, and disjoint from the table. Green at 100% coverage with the single recorded deferral.

**Verification:** suite **752 passed + 17 subtests, fully green** (= 729 pre-batch + 16 this batch + 7 Proposal A micro-batch). **Goldens: ZERO drift from this batch** — every suite run was green with no `CHAR_GOLDEN_UPDATE` (byte-match proof); the rollup md5 moved `ef5f731c7268107a16013de775557a95` → **`08aff507ee84bcb073ed7166cf446207`** solely via the CONCURRENT Proposal A micro-batch's documented 2-file re-pin (its section above; the other 10 goldens byte-identical, mtime-verified). `scripts/check_teacher_truncation.py` ok (14 files). `import tutor.web_app` ok. No restart (data + loader; runtime behavior parity-pinned). Nothing committed.

**Batch-2 scope (the flip):** derive the four live lists from table queries — TOPIC_CONCEPT_NOUNS, `_noun_from_text`/NOUN_TEXT_PAIRS + NEW_CONCRETE_NOUNS, `_concepts_from_spanish`/SPANISH_CONCEPT_PAIRS, observe topic_vocab — selection keyed on imageable ∧ pack-legal (optionally theme-filtered); DELETE ASSOCIATION_NOUNS (dead) + CONCEPT_LEXICON (sidecar becomes sole asset source; migrate image_gen.py); guard-6 pairs and observe vocab become table queries; replace the PlanCard image-decision DTO shape (E4 leftover). **Policy-round outcome checked per the brief:** Proposal A landed in parallel (scene_modeled/needs_model machinery already deleted — batch 2 need NOT defer scene-adjacent lists to a batch 3), but **Proposal B is sequenced pin-first BETWEEN this batch and batch 2** (adjudication item 3, binding): batch 2 must not start until B's model_lines-image-ban pin lands, and inherits the ban. Also owed batch 2: the `estoy bien` deferred entry decision; the **imageable-vs-sidecar selection question** — hola is `imageable:false` in the table yet is the open-turn image asset, so the flip must decide whether image selection keys on `imageable`, on sidecar presence, or both (a wrong choice silently kills the open-turn image); `barco` kept as its own table key (real distinct word, TOPIC-list member) while remaining an alias of bote in the pairs — the flip collapses or keeps that deliberately.

---

## Proposal B pin landed (agent, 2026-07-29)

Executed per Grok's BINDING "Exact replacement text" for Proposal B (this doc, policy round) at the adjudicated sequence point: **after Phase 5 batch 1, before Phase 5 batch 2**. Files: `tutor/turn_pipeline.py`, `tutor/teach_assets.py` (docstring contract only), `tests/test_characterization_ai_path.py`, `tests/test_characterization_ai_arcs.py` (comment truth only), `tests/characterizations/golden_due_turn.json`, `tests/characterizations/known_bugs.json`. Phase 5 batch 1's sidecar overlay surface (`teach_assets` loader/lexicon code, pack data) untouched — coexistence verified by the green merged suite.

**Ban sites (the complete model_lines image chain, from the grep):**
1. `turn_pipeline.stage_fallback_image` — the `tutor_models=list((ctx.decision.targets or {}).get("model_lines") or [])` argument is GONE (parameter omitted entirely, not emptied). Scene turns' image relevance base is now exactly the binding text: `decision.image_concept` primary (mode attach owns its cache hit/miss + single miss note — unchanged) + learner text secondary (already threaded via `learner=`). Docstring records the ban + the accepted narrowing.
2. `turn_pipeline.stage_fallback_image` repair branch — **verdict: CUT, not clean.** The comprehension_repair `require_relevant_to` join read `targets.model_lines` (dead at runtime — repair targets never set the key — but a live script re-entry seam). Replaced with the binding item-4 base: learner text + `targets.last_model` + `targets.last_try` (actual prior tutor performance from session memory). Behaviorally inert today (repair candidates are extracted from learner text only, so the gate outcome cannot flip; golden_comprehension_repair/golden_gate_repair_turn byte-identical, suite-proven), and the scripts key can no longer return.
3. Those two lines were the ENTIRE image chain: `grep model_lines` across `tutor/` now hits only `modes.py:1018` (scene_goal decision targets — realization-prompt direction, §1.1a's separate migration per the binding's last paragraph) and `scenes.py` (pack loading). `teach_assets.assets_for_ai_turn` keeps the `tutor_models` parameter for true post-hoc callers but its docstring now carries the contract: actual tutor output only, authored scene scripts banned, the reply-path caller passes none.

**CHAR-BUG-006: RESOLVED** (registry flipped, WAS/NOW recorded). With scripts off the path the dual-miss-note class is impossible by construction: the fallback can only decide concepts surface-present in the learner's own words, so a scene turn can never note/warm a script-derived phantom (`bote`+`hola`). A learner-typed second concept remains lawful (honest secondary base). Incident-class probe at fix time: learner «Estoy contento hoy.» on the `scene_goal:boat_meet_captain` host — OLD fallback decided `hola`/new_concrete_model (want=True, dual note); NEW decides `no_image_worthy_concept` (want=False, single honest `bote` note).

**The pin (binding requirement — Phase 5 batch 2 must inherit this GREEN):** `tests/test_characterization_ai_path.py` —
- `test_char_bug_006_resolved_no_scene_scripts_as_tutor_models` — spy on `assets_for_ai_turn` through a real end-to-end `scene_goal` turn: no call carries `tutor_models`, and no authored scene line appears in ANY argument (relevance text included).
- `test_char_bug_006_resolved_dual_miss_note_class_gone` — the bote host turn end-to-end: exactly one `image_gen_disabled:bote`, zero script-derived `hola` note/attach of any kind.
- `test_char_bug_006_ban_lint_image_chain_free_of_model_lines` — ast-level ban lint (the CHAR-BUG-005 lint idiom): no Name/Attribute/string-Constant/keyword `model_lines` reference anywhere in `tutor.turn_pipeline`.

**Golden regeneration (ONLY pins that change; old rollup md5 `08aff507ee84bcb073ed7166cf446207` → new `365eb6412725245ce1e852fc54844fcc`, formula `md5 -q *.json | md5` in tests/characterizations):**
- **Regenerated (1): `golden_due_turn.json`** — its retrieval `scene_goal:boat_likes` turn was the one remaining golden riding the fallback's script base (registry: fallback decided `cafe` from boat_likes' model_lines; note deduped only because mode attach picked the same concept). Delta is exactly one notes line: `image_decision:new_concrete_model` → `image_decision:no_pedagogy_trigger` (learner «Me gusta mucho el pan.» yields no imageable fallback concept; the honest `image_gen_disabled:cafe` mode-attach note is unchanged). Everything else byte-identical.
- **Byte-identical (10):** all other goldens — proven by the full suite running green with NO `CHAR_GOLDEN_UPDATE` (any drift would fail check_golden). `known_bugs.json` also moved (006 flip), which the rollup includes.

**Behavior honesty (declared delta, accepted narrowing — adjudicated):** image selection on scene turns is NARROWER: a scene image the learner has not typed arrives only via `decision.image_concept`; the fallback can no longer want/warm a script-derived concept on scene turns (due_turn's `cafe` fallback want → none). Runbook: this section is the declared-delta record. **Evals:** no eval trajectory pins the old fallback pick — `evals/` greps clean for image-decision reasons; `conv_checks.py`'s bote association check keys on the mode decision's `image_concept`/mode (mode-attach path, unaffected). No eval adjustment owed.

**Verification:** suite **755 passed + 17 subtests, fully green** (= 752 pre-batch + 3 pin tests) via `.venv/bin/python -m pytest tests/ -q`. `scripts/check_teacher_truncation.py` ok (14 files). `import tutor.web_app` ok. Server restarted (behavior changed); `/api/health`: `stale_code: false`, version `20260729-125137`. Nothing committed.

**Phase 5 batch 2 clearance:** the binding sequence step 2 is COMPLETE — batch 2 (list-derivation flip) may now start and MUST keep the three 006 pin tests green while rewriting teach_assets/PlanCard; the ban travels with the rewrite (no scene/authored script list may ever feed `tutor_models`/`require_relevant_to`, per the pinned contract).

---

## Phase 5 batch 2 landed — PHASE 5 CLOSED (agent, 2026-07-29)

The inventory flip, per Grok's round-1 (b) amendment (BINDING: selection derives from table `imageable` + pack-legal; sidecar is metadata by the same IDs, never a second concept list; batch 1 met the migration prerequisite). Files: `tutor/association_table.py` (structural sets moved here + `cached_default_table` + `content_topic_keys`), `tutor/session_memory.py`, `tutor/modes.py`, `tutor/observe.py`, `tutor/output_gate.py` (structural-set re-export only), `tutor/conv_session.py` (`_topic_nouns`), `tutor/teach_assets.py`, `tutor/image_gen.py`, `scripts/prewarm_teach_images.py`, `course_packs/spanish_a1/association_table.json` (+1 entry: `estoy bien`, appended — order preserved), `course_packs/spanish_a1/migration_deprecations.json` (now EMPTY), `tests/test_inventory_coverage.py` (rewritten: derivation-law gate + sidecar sole-source), `tests/test_asked_topics.py`, `tests/test_characterization_ai_arcs.py`, `tests/test_characterization_ai_path.py`, `tests/test_turn_pipeline.py`, 2 goldens regenerated + `known_bugs.json` (CHAR-BUG-007 → RESOLVED). The three Proposal B 006 pins inherited GREEN, untouched.

**Table load posture (all four modules):** ONE module-level cache, `association_table.cached_default_table()` — the validating loader over `config.DEFAULT_PACK_DIR`, loaded once per process; a broken/missing default pack raises LOUDLY at first import instead of silently emptying routing lists (the loader's validation is respected; the per-session degrade posture in `conv_session` is unchanged for custom pack dirs).

### Per-list flip decisions

1. **`session_memory.TOPIC_CONCEPT_NOUNS` + `conv_session._topic_nouns` — BROADENED** (topic-key extraction, registry richness — per the brief's preference). ONE derivation, `session_memory.topic_palette(table)`: recorded priority tier first (`_TOPIC_PRIORITY_KEYS`, the 18 legacy incident-noun keys in legacy ORDER — order is behavior-bearing, first-present wins; surfaces = key + `fold_lexical` accent variant, reproducing the old 21 strings exactly) then `content_topic_keys(table)` — every table key EXCEPT `STRUCTURAL_THEMES`/`STRUCTURAL_KEYS` (canonical home moved to `association_table.py`; `output_gate` re-exports). Declared deltas, both golden/eval-justified: (a) **CHAR-BUG-007 RESOLVED** — the registry's prescribed resolution executed verbatim ("exclude STRUCTURAL_THEMES/STRUCTURAL_KEYS … in Phase 5's inventory collapse; update pin in the same PR"): pronouns/question words/copulas/numbers/`hay` no longer bind as topic concepts; `¿Dónde estás tú?` registers bare `location`, semantically identical asks dedupe onto one key (probe_loop now catches the re-ask class the split hid). (b) The module default now EQUALS the production palette (the old 21-noun constant was a narrower divergent default used only when callers passed no `nouns`); two `test_asked_topics` unit pins updated with justification — a wellbeing/name try whose text contains the frame phrase itself (`cómo estás`, `cómo te llamas` — real table keys) binds it as concept, exactly as the production gate/registry path already behaved pre-flip. No in_pack filter (off-pack keys stay observation-valid per the batch-1 record); no imageable filter (topics need not be imageable — `trabajo`).
2. **`session_memory.SPANISH_CONCEPT_PAIRS` (repair `last_concepts`) — CONSERVATIVE** (feeds comprehension-repair image concepts = routing). `_REPAIR_CONCEPT_SPEC`: recorded legacy membership (río, bote, barco→bote, café, música, comida, hola, estoy bien), every key validated against the table at import; concept ids = `fold_asset_key(table key)`; needles = key + accent-fold variant + recorded authored extras (`estoy` → the `estoy bien` formula — §1.1a class-iv detection text). Byte-equal behavior (the added literal `estoy bien` needle is subsumed by `estoy`). **barco kept deliberately** (batch-1 flag adjudicated): its OWN table key (real word, topic-palette member) but the `bote` asset id in the pairs — the sidecar alias collapse, one referent one image.
3. **`modes.NOUN_TEXT_PAIRS` (guard-6 `_noun_from_text`) — CONSERVATIVE** (routing, per the brief's preference). `_GUARD6_NEEDLE_SPEC`: the recorded legacy needle sequence — ORDER preserved exactly including the deliberate split («río dulce» outranks everything; plain «río» ranks below the other nouns) — with concept ids derived `fold_asset_key(table key)` and the **imageable law enforced at import**: every member must be an `imageable: true` table entry or the module fails to import (`_imageable_concept_id` raises; negative-tested).
4. **`modes.NEW_CONCRETE_NOUNS` (guard-6 fallback candidates) — CONSERVATIVE.** Same derivation + imageable enforcement over the recorded legacy membership/order (café, bote, música, comida, río).
5. **`observe` topic_vocab regex — CONSERVATIVE** (the signal gates guard-6 routing). `_TOPIC_VOCAB_TABLE_KEYS` (café, bote, barco, río, comida, música, calor, frío) validated imageable table keys; the compiled alternation is built from key + accent-fold variant — provably equivalent to the historical `caf[eé]|…` classes (drift guard fires each surface).

### Deletions

- **`modes.ASSOCIATION_NOUNS`** — deleted (zero readers; the coverage gate was its last importer).
- **`teach_assets.CONCEPT_LEXICON`** — deleted (~115 lines). The pack asset sidecar (batch-1 parity-proven byte-identical) is the SOLE metadata source: `_lexicon()` = cached `sidecar_lexicon(DEFAULT_PACK_DIR)`, degrade `{}` on a missing/invalid sidecar (association-table posture — images lose curated metadata, cached files keep resolving via manifest/index, never a crash). `image_gen.py` migrated off the direct import (reads `_lexicon()`); `scripts/prewarm_teach_images.py` migrated AND its stray hand-copied `EXTRA_CONCEPTS` list now derives from the guard-6 lists (dry-run verified: 19 concepts, all cached). The batch-1 parity test class became `SidecarSoleSource`: `_lexicon() == sidecar_lexicon(pack)`, folded keys == the 10 legacy asset ids, the three bundled cache filenames pinned byte-exact (hola.jpg/estoy_bien.jpg/me_llamo.jpg), per-entry schema shape, and the degrade path. The coverage gate reshaped: it now pins DERIVATION LAWS (membership folds into table keys; guard-6/topic_vocab members imageable-true; palette excludes structural; module default == production palette; deprecation hatch EMPTY) instead of chasing hand lists.

### The imageable-vs-sidecar ruling (batch-1 flag — LANDED, no stop)

Implemented as adjudicated: the table's `imageable` answers "can THIS concept be dual-coded for MEANING" and governs image **SELECTION** — guard-6/association/R-B lists derive from `imageable: true` entries only, enforced at import. The sidecar answers "do we have an ASSET" and never widens selection. The placement-open «hola» image is the ONE exemption: a `decision.image_concept` channel with its own justification — SCENE-SETTING for a true-zero opening (a greeting illustration orienting the learner), not R-B meaning-binding — so it is exempt from the imageable filter (`hola` stays `imageable: false`; its asset lives in the sidecar). Documented in `modes.py` (guard-6 spec block + the `blank_open_placement` decision site) and `teach_assets.py` (sidecar section). Verified against laws and goldens: `golden_blank_open` byte-identical (image_gen_disabled:hola + image_decision:diagnostic_open intact); no law conflict — the exemption is the status quo made explicit, and scene `input.image_concept`s (bote/cafe/rio) are all imageable:true anyway.

### estoy-bien deferral — RESOLVED (real table entry, declared delta exactly as predicted)

`estoy bien` appended to the table (END — order is behavior-bearing for candidate buckets/palette): `{gloss_en: "I am fine", imageable: false, theme: "how_are_you"}`, in_pack (it IS pack content — the U2 estar wellbeing exchange); imageable:false per the theme's own judgment class (bien/mal/muy bien are all false) — its asset rides the sidecar under the ruling above. `migration_deprecations.json` is now EMPTY (comment records the graduation). **The golden delta was EXACTLY the predicted scaffold_saved span change, nothing else** — `golden_blank_zero_register_turn`: `scaffold_saved {bien: gloss}` → `{estoy bien: gloss}`, `first_seen:bien` → `first_seen:estoy bien`, sheet write `lexicon:bien` → `lexicon:estoy bien` (the golden now also pins `lexicon:bien: null` — the MWU won the span, bare «bien» untouched; CORRECT per the longest-match law). Inline pins updated with the regen (`test_characterization_ai_path`, `test_turn_pipeline::test_first_seen_rides_the_same_single_commit`). No other golden was touched by the entry (`golden_blank_open` is placement — scan-exempt — and byte-identical; no other pinned reply contains the phrase; introduce candidate order unaffected — appended last, greetings priority bucket still leads with `hola`). Side effects declared: `estoy bien` joins the unscaffolded-scan inventory, the introduce-eligible pool (R-D gloss — no cognate/keyword/image), the how_are_you R-F forbid lists, and the topic palette tail. No STOP condition met.

### Golden regeneration list

Old rollup md5 `365eb6412725245ce1e852fc54844fcc` → **new `9e662c5fd4eeec2534b4afd0e734f7ca`** (formula `md5 -q *.json | md5` in tests/characterizations). Content deltas = **2 goldens + the registry**: `golden_blank_zero_register_turn.json` (estoy-bien span family, above), `golden_comprehension_repair.json` (clear_turn `asked_topics: [location:tu]` → `[location]`, note `asked_topic:location:tu` → `asked_topic:location` — the 007 fix), `known_bugs.json` (007 → RESOLVED). All other goldens byte-identical — proven by the full suite running green with no `CHAR_GOLDEN_UPDATE` (`golden_blank_open` re-written by the shared regen run but content-identical).

### Remaining SCRIPTED-CONTENT DEBT residue

**`model_lines` in realization prompts — the §1.1a migration's last leg, NOT this batch.** The single production read is `modes.py` guard 7 (`scene_goal` decision `targets.model_lines` = scene `input.model_lines`, injected into realization direction), plus `scenes.py` pack loading of the field. The image path is clean (Proposal B pins, inherited green); this batch's flip removed every parallel concept LIST — what remains of the debt is scene-authored performance text reaching the model's direction, owed to the §1.1a scene-spec migration (goals/slots/exit predicates replace suggested lines). Also recorded, NOT debt: `modes._form_for_concept` / `_good_models` are class-E form-exemplar inventory (lawful per §1.1a(i)); `_scene_for_topic`'s keyword lists and all needle strings are class-iv detection text; `modes._fallback_association_concept`'s inline 5-tuple (guard-4 fallback, same membership as NEW_CONCRETE_NOUNS) survives as a function-local ordering detail outside the four-list mandate — fold it into the derived constants whenever guard 4 is next touched; `teach_assets.PlanCard/ImageDecision` DTO shape (E4 surviving surface) carries no authored content and its retirement is orthogonal cleanup, not scripted-content debt.

### Phase 5 close verdict

**PHASE 5 CLOSED.** Map move 4 is done: the six parallel concept inventories are ONE — the association table (191 keys) is the sole concept inventory; the sidecar is asset metadata by the same IDs (never mints, pinned); the four live lists are table-derived queries with recorded conservative/broadened decisions per list; the dead list and the in-code lexicon are deleted; the migration deprecation hatch is EMPTY; the coverage gate now enforces derivation laws rather than chasing hand lists. Two registry bugs closed on the way (007 here; 005/006 by the adjudicated policy round + B pin, sequenced exactly as bound). Casa/ciudad-class guard-6 concepts now provably imageable-backed at import (the map's original defect class structurally excluded).

**Verification:** suite **761 passed + 17 subtests, fully green** (= 755 pre-batch + 6 net new derivation-law tests) via `.venv/bin/python -m pytest tests/ -q`, including the three Proposal B 006 pins (run by name, green) and the reshaped coverage gate. `scripts/check_teacher_truncation.py` ok (14 files). `import tutor.web_app` ok. Server restarted (behavior shifted: 007 topic keys, estoy-bien scan, sidecar sole-source); `/api/health`: `stale_code: false`, version `20260729-131929` == disk_version, `lexicon_size: 10` (sidecar), teach-image catalog 20/20 hits. Nothing committed.

---

## CHAR-BUG-008/009 fix landed — REGISTRY CLEAR (agent, 2026-07-29)

The final open registry entries executed as a declared **behavior-change** PR (not refactor-neutral): the model's `update_character_sheet` tool loses the power to inflate the diagnosis (PEDAGOGY §3.2 introduction ≠ knowledge / P7 the sheet is the targeting instrument; §4.5 capability removal + instruction). Files: `tutor/character_sheet.py`, `tests/test_character_sheet.py`, `tests/characterizations/known_bugs.json`, this runbook. Nothing committed.

**Clamp rules chosen (the honesty law, exact):**
- **008 (`solid_uses` claims are not evidence).** `_clamp_skill_entry` now starts from the sheet's own recorded (observed) count; an incoming `solid_uses` claim may **LOWER** it (honest demotion, floored at 0 — `uses = min(observed, max(0, claim))`), never raise it, and the merge mints no uses of its own — the old `max(uses, claim)` trust AND the rose/promoted **+1-per-merge heuristic are both gone** (the heuristic let pure claims climb the gate over N calls, so gating only the claim field would have left "uncrossable by claim alone" false). Code-observed evidence (`_bump_status` on real learner text, via `apply_rule_updates`/`note_error_pattern`) is the ONLY source that increments `solid_uses`.
- **008 (known gate keyed to prev band + observed uses).** Promotion to `known` through a tool merge requires prior known (legacy/seeded claims stay honored — `test_clamp_keeps_legacy_known_without_uses` unchanged) OR a sub-known EVIDENCE band (`emerging`/`fragile`) with observed uses ≥ `KNOWN_MIN_SOLID_USES` and conf ≥ `KNOWN_MIN_CONF`. Everything else claiming known is **silently clamped to emerging** (conf capped 0.75) — the `_cap_turn_confidence` philosophy for routine inflation, per the fix brief's per-case rule. The old one-call crossing (prev emerging 0.6 + claim `{known, 0.85, solid_uses: 2}`) now lands `emerging 0.75, uses 0`.
- **009 (no branch merges unclamped).** BOTH `apply_delta` lexicon branches (dict merge AND bare-string status) route through `_clamp_skill_entry` (which gained a `via` parameter, default `"tool_merge"`, passed `"delta_lexicon"` there — the machine still discriminates the write site). Characterized clamped landing: absent + claim `{known, 1.0, solid_uses: 2}` through `process_turn` lands **`emerging` at conf 0.25 (the +0.25 first-appearance ceiling), uses 0**; the known-claim-without-uses case lands the same (pre-fix its conf 1.0 survived the cap re-gate demotion). Accepted narrowings recorded: lexicon entries touched by a dict claim now carry an explicit `solid_uses` honest zero; an out-of-vocabulary bare-string claims nothing (absent entry stays band unknown — the old branch minted `emerging`).

**Edge-table changes (machine B):** `tool_merge` and `delta_lexicon` are no longer edge-complete — both now equal `_TOOL_CLAIM_EDGES`: any band → {unknown, emerging, fragile, blocked} plus {emerging, fragile, known} → known. **Removed edges: `unknown → known` and `blocked → known`** on both vias (not writer-producible after the fix; the machine raising `IllegalAbilityTransition` on them is the production-unreachable regression backstop, mirror of the batch-1 double-introduce ruling — raise reserved for impossible states, clamp for routine inflation, per the brief). The UNION graph `ABILITY_TRANSITIONS` is unchanged (still complete via `bump` evidence edges), so `_check_ability_graph_sync` and the union pin hold. `blocked` stays tool-enterable; `cap`/`normalize`/`bump` untouched.

**Pins flipped + added (Phase 0 law: fix + pin + registry in one change):** `test_tool_band_jump_characterized_char_bug_008_009` inverted → `test_char_bug_008_009_resolved_tool_cannot_jump_bands` (clamped landings end-to-end through `process_turn`, the lawful observed-evidence promotion, claim-may-lower-never-raise); NEW `test_tool_vias_tightened_char_bug_008_009` (edge-set equality + the two backstop raises); `test_confidence_cap_and_known_gate` re-pinned (its old "climb over several solid updates" 4-call claim ladder to known WAS the 008 heuristic in miniature — now pins the stall at emerging/0.75/0 uses and the promotion once observed uses reach the gate). Tool schema updated per §4.5's instruction half: description now carries "Do not claim solid_uses; observation records it (claimed counts are capped at the code-observed count, and 'known' requires observed uses — it cannot be granted by claim)", echoed in the skills/lexicon property descriptions.

**Golden outcome: zero regenerations, verified.** The characterization fake model issues no sheet tool calls (grep over `tests/conftest.py`: no `tool_use`/`tool_delta`; no golden JSON contains a tool-claimed `solid_uses`) — the goldens ride the rules observer path, which this fix does not touch. All `golden_*.json` byte-identical (mtimes predate the fix session; golden suite green with `CHAR_GOLDEN_UPDATE` never set; golden-only md5 `98070c04cb04ece961443a7d4594e007`). The combined `md5 -q tests/characterizations/*.json | md5` moved **`9e662c5fd4eeec2534b4afd0e734f7ca` → `b5a56c61c592773c657cf92f405f46eb`** solely because `known_bugs.json` (inside the glob) carries the two registry flips.

**REGISTRY CLEAR.** `tests/characterizations/known_bugs.json`: **10/10 entries resolved or explicitly closed** — CHAR-BUG-001/002/003/004/006/007/008/009 RESOLVED, CHAR-BUG-005 RESOLVED-BY-DELETION, CHAR-DIVERGE-E4 RESOLVED BY DELETION. (The fix brief said "12/12"; the registry has always held 10 keys — 9 CHAR-BUGs + the E4 divergence set — reported faithfully per §5.4.) No characterized-not-fixed behavior remains; the only recorded ability-axis follow-up left OPEN is the pre-existing, documented AI full-rewrite +0.25 clamp gap (`_cap_turn_confidence` docstring / Phase 1.5 batch 2 follow-up (2)), which is not a registry entry.

**Verification:** suite **762 passed + 17 subtests, fully green** (761 pre-fix + 1 net new edge-table test) via `.venv/bin/python -m pytest tests/ -q`; the two flipped pins were the ONLY failures mid-change (blast radius exactly the characterized surface). `scripts/check_teacher_truncation.py` ok (14 files). `import tutor.web_app` ok. Server restarted (behavior changed); `/api/health`: `stale_code: false`, version `20260729-133702` == disk_version. Nothing committed.

---

## CAMPAIGN CLOSED — capstone (⬛ Claude, 2026-07-29)

**Mandate (USER, 2026-07-28):** "Bugs and weird shit all over the place because maybe the code is getting hard to understand and manage. Lets do a architecture review and refactor." Plus the standing question ("maybe its time for a state machine") and the deletion directive ("if there is dead code just delete it").

**Executed:** ~19 agent batches + 5 countersign rounds (map corrections, E4, scenes-after-scripts, plus the framing round-2 verify), every batch green before the next launched, over ~24 hours.

**Before → after (measured):**
- `_execute_ai_tutor`: 923 lines / 38 inline stages / 0% test coverage → **63 lines** running 37 named, individually-tested stages in five families (head, contributors, realize, gate/repair, recorders) + capture/log.
- `tutor/`: 22,918 lines / 48 modules → **19,987 / 40** (E4+E4b and Phase 6 deletions net of new modules: session_state, turn_pipeline, turn_events, textnorm).
- Execution paths: 3 (AI / rules / legacy harness) → **1**, all HARD LAWS enforced on it; TEACHER_MODE errors on anything else.
- Session state: 5 stores + 8 loose attrs, 5 reset paths covering 5 different subsets → **one SessionState aggregate, unified reset kinds, leak class closed, learner epochs**.
- Item state: 7 fields written by 4 modules → **two orthogonal legality-checking machines** (schedule axis / ability axis), cross-axis writes illegal both directions, ledger a proven projection.
- Text handling: 5 fold functions (3 semantics), 3 boundary matchers, 5 letter-class copies → **one module, 4 named policies**, 401-probe differential contract, identity-pinned bindings.
- Turn data bus: ~40 undeclared note prefixes, 3 self-re-parses → **62-family typed event catalog**, dual-emit render contract, chronological ordering, zero absorb fallbacks on golden runs.
- Concept inventories: 6 parallel lists → **one 191-key association table + asset sidecar**, imageable enforced at import, coverage gate executable, deprecation list empty.
- Gate seam: 18 args across 5 subsystems → **GateContext** with shim parity.
- Bug registry: **10/10 resolved or closed** — including two lawful STOPs where fixes were built, found unlawful, and reverted with reasons (the 005 revival; later resolved by countersigned deletion+host-rules).
- Tests: 553 pre-campaign → 496 after legacy retirement → **762**, fully green; the truncation gate never went red; golden regenerations: 5 events, every one with per-golden justification.
- Durability: atomic turn commit (declared); diagnosis integrity: the model tool can no longer inflate bands or solid_uses (declared).

**State-machine question answered:** yes for item lifecycle (two axes, not one — the countersign's correction), no for session flow (PhaseState suffices), no for turn flow (pipeline ≠ FSM; framing owns performance).

**Residue (tracked, not hidden):** SCRIPTED-CONTENT DEBT's last leg (model_lines in realization prompts — scene schema v2); the AI full-rewrite clamp gap (pre-existing, documented); PEDAGOGY §8's product debts (fluency strand, structured input, etc.) — those are product work, not architecture.

Campaign CLOSED. Reopen trigger: any new subsystem wired outside the pipeline's contributor/recorder contracts.
