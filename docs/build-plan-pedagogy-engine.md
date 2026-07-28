# Build plan — the pedagogy engine (merged r6 + r7, adjudicated 2026-07-28)

User mandate (2026-07-28): "We are still very shallow in pedagogy… Conversation is just one element… stop being shy about writing code. It is ok to have many systems and services as long as they are engineered and single purpose."

Sources: docs/pedagogy-research-r6-practice-mix.md and r7-association-intro.md (both CONVERGED, adjudications appended). Standing laws: authority exceeds perception (code decides, model performs); SessionPhaseController is the SOLE orchestrator once built; evals gate is the promotion bar; no personal data anywhere (docs/reviews-personal-data-removal.md).

## Phase 1 — Foundation (additive; no turn-loop restructure) — BUILD NOW
1. **Sheet schema v2 additions** (one migration, both rounds share it): per lexicon/grammar/skill item — `introduced_at`, `scaffold` (r7 S1 first-seen ledger; keys are lemma OR multiword unit like "hasta luego"); `next_due`, `interval_days`, `successive_successes` (r6 scheduler). Introduction NEVER bumps confidence/known (honesty law).
2. **`tutor/retrieval_scheduler.py`** (r6 rank 1 / r3 finally built): pure code service. Intervals: success 1d → 3d → ×2 cap 14d; fail → 1d. `due_items(sheet, today, max_due=3)`; `record_outcome(...)`; injectable `today` for fake-clock tests. Enqueue on transfer success.
3. **Soft wiring**: due items ride mode instructions as "re-encounter elicits" inside the current topic (no new hard mode, no flashcard chrome); session counters cap introductions at 2/session (stopgap until Phase 2 owns budgets).
4. **Tests/evals**: interval math + fake-clock units; ledger honesty (introduce ≠ ability bump); eval check `due_elicit_fired` on a two-day simulated trajectory.

## Phase 2 — SessionPhaseController (thin)
Turn-count-based phase plan above select_mode: retrieval ~20% / structured input ~30% / task ~35% / free ~15% with r6 §4.3 adaptations (minus struck profile hooks — pack topics + sheet lexicon only). Repair and critical gate faults preempt. `activity_type` becomes a first-class logged field; eval `phase_adherence ≥ 0.80`. Sole-orchestrator law enforced here.

## Phase 3 — Introduction machinery (r7 S4 + S2)
`course_packs/spanish_a1/association_table.json` (cognates, false friends ≥15, imageable flags, curated keywords, thematic_group_id for the cluster ban) → `IntroducePlan` router executing R-A…R-G (cognate → image → engineered ≥95%-coverage context → single ≤6-word L1 micro-gloss; one target per move; budget-aware). Prompt policy text amended per r7 §6 ONLY after the machinery exists.

## Phase 4 — Enforcement
Output gate: `gate:unscaffolded_new_item` (critical) + `gate:regloss` (soft). Must not fight `gate:english_wall`.

Phase 4 status: SHIPPED 20260728-095944 (r7 S3 in tutor/output_gate.py: scan_unscaffolded_new_items over the pack association table — model/try detection, gloss/anchor scaffold signals anywhere in-reply, ≤6-word gloss law, R-F cluster veto on same-theme extras even when glossed; regloss soft fault unless the item failed retrieval this turn; conv_session plumbs table/sheet/plan-key/failed-due/learner-text into all three gate calls and adds unscaffolded_new_item to the critical set. Pragmatic exemptions, recorded: introduced keys; any sheet-lexicon evidence (conf > 0); keys in the learner's own current utterance; in_pack:false; structural paradigm themes pronouns/question_words/copulas/numbers/function; placement mode. 14 gate unit tests in tests/test_output_gate.py.)

## Phase 5 — Activity engines
`StructuredInputEngine` MVP (ser/estar A/B image choice; receptive-evidence bump path; UI choice buttons — client work), `ConvergentTaskRuntime` (scenes get single primary exit + private info slots), `MicroListeningLab` (dictation edit-distance scorer on pack sentences; shadowing block).

Phase 5 status: ConvergentTaskRuntime: scenes+runtime SHIPPED — 3 boat scenes extended with primary_exit/tutor_private_info/learner_must_obtain (pack-legal, gustar-free task content), tutor/task_runtime.py pure runtime + tutor/scenes.py schema validation + tests/test_task_runtime.py. Task WIRING SHIPPED 20260728-095944: conv_session binds the first task-capable open scene on task-phase turns (session-scoped TaskState, persists until done), evaluate_turn runs on the learner's own text BEFORE the tutor call (notes task_slot_filled:<id> / task_complete:<scene_id>), and task_instructions (goal + remaining slots + tutor_private_info with the never-volunteer directive) ride only flavorable turns (same set as INTRODUCE; guards/repairs preempt; after done, task turns fall back to normal flavor). Eval c11_task_infogap + task_goal_offered check (evals/conv_trajectories.py, conv_checks.py; run_conv_smoke gains seed_phase_state).

## Cross-cutting debts (from both rounds)
- Multi-day eval harness with fakeable clock (spacing is untestable without it).
- Item banks are the real content debt for Phases 3/5 (pack is prose + 3 scenes today).
- Behavioral WTC/anxiety proxy (latency, reply length, English-escape rate) — later, feeds phase adaptation; NOT personal data.
- UI response primitives (choice buttons/image hotspots) required before StructuredInputEngine.

Status: Phase 1 SHIPPED 20260728-085537 (tutor/retrieval_scheduler.py + sheet schedule fields + soft DUE RE-ENCOUNTERS wiring + intro budget counters + tests/test_retrieval_scheduler.py + eval c08_due_reencounter/due_elicit_fired; 285 tests green, truncation gate ok). Phase 2 SHIPPED 20260728-091255 (tutor/session_phases.py thin SessionPhaseController: turn-wise PhasePlan 3/4/5/2 of 14 with r6 §4.3 adaptations minus struck profile hooks; PhaseState clock frozen on guard/repair turns; select_mode activity_hint flavors known-open + default fallthrough only; activity= logged per turn; eval phase_adherence + c09_phase_mix; 314 tests green, truncation gate ok). Phase 3 S4+S2 SHIPPED 20260728-093146 (R-C engineered-context deferred): S4 table+loader (course_packs/spanish_a1/association_table.json 175 entries incl. 20 false friends + tutor/association_table.py loader with R-A/R-E anchor preference and R-F theme helpers + tests/test_association_table.py) + S2 IntroducePlan router (tutor/introduce_router.py — R-G budget → one target → R-F cluster ban → cognate/image/keyword/gloss routing; conv_session introduce_block rides new_input flavorable turns only, mark_introduced_if_visible writes the S1 ledger ONLY when the visible reply carries the key; tests/test_introduce_router.py + eval c10_introduce_scaffolded/introduce_scaffolded; 375 tests green, truncation gate ok). Grok-countersign fix batch + Phase 4 gate + Phase 5 task wiring SHIPPED 20260728-095944 (P0 AMENDs 2a/2b/3a/4a/4b per docs/reviews-pedagogy-engine-build.md adjudication; 391 tests + 17 subtests green, truncation gate ok, health stale_code false).
