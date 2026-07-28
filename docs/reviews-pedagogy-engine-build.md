# Review: pedagogy-engine build — Phases 1–3 + task runtime (2026-07-28)

## Proposal / change record (Claude, 2026-07-28)

One-day build executing the adjudicated r6/r7 research (docs/pedagogy-research-r6-practice-mix.md, r7-association-intro.md, merged plan docs/build-plan-pedagogy-engine.md). All shipped, 375 tests + 17 subtests green, truncation gate ok, live v20260728-093146. Implementation by delegated agents under adjudicated contracts; this review is the independent audit of the result.

**Shipped subsystems (all single-purpose, code-decides-model-performs):**
1. `tutor/retrieval_scheduler.py` (r6 Rank-1 / r3 MVP + r7 S1 ledger): due_items (oldest-first, kind-interleaved), record_outcome (1d→3d→×2 cap 14d; fail→1d), enqueue, mark_introduced. Allowlist-enforced honesty: schedule/ledger writes can never touch confidence/status; apply_delta strips schedule fields from model tool deltas. Due items ride conversation/transfer turns as "DUE RE-ENCOUNTERS" soft instructions; outcomes recorded only on clear evidence (word_present success / meta_comprehension-naming fail / grammar resolve-vs-hit; silence records nothing).
2. `tutor/session_phases.py` (r6 Rank-2 thin): build_phase_plan ratios ≈20/30/35/15 over a 14-turn estimate → retrieval 3 / new_input 4 / task 5 / free 2; adaptations (due 0 drops retrieval; due ≥3 expands; limited_time → retrieval+task; blank → new_input+free; boredom → task first with pack-topic refs). PhaseState ticks per turn; guard/repair turns FREEZE the clock (PHASE_FREEZE_REASONS enumerated from select_mode + comprehension_repair unconditionally + blank_open_placement). activity_hint flavors ONLY known-open + default_conversation fallthrough; guards/interventions untouched. Notes activity=/phase_consumed=; eval phase_adherence (c09).
3. `course_packs/spanish_a1/association_table.json` + `tutor/association_table.py` (r7 S4): 175 entries, 27 themes, 20 false friends; loader validates all-at-once (gloss ≤6 words; trap-cannot-be-anchor enforced); anchor_for prefers cognate→keyword→gloss.
4. `tutor/introduce_router.py` (r7 S2): plan_introduction executes R-G budget (≤2/session) → single target → R-F cluster ban (forbid same-theme unintroduced) → R-A cognate / R-B image / R-E keyword / R-D single ≤6-word gloss. R-C engineered-context DEFERRED (recorded). Plans ride new_input-phase conversation turns; mark_introduced ONLY when the visible reply carries the key (lapse = budget unconsumed). Routing spot-check (corrected per AMEND 3b): adiós→R-D (no true cognate; conventional farewell micro-gloss); por favor→R-A; casa→R-B; vaso (false friend)→R-B never cognate; hasta luego→R-E forbidding adiós/hasta mañana; me llamo→R-D.
5. `tutor/task_runtime.py` + extended scenes (r6 Rank-4 content half, WIRING PENDING): 3 scenes now info-gap tasks with learner_must_obtain slots, tutor_private_info ("reveal ONLY when the learner asks in Spanish; never volunteer"), machine-checked exits via boundary-disciplined matching. All evidence pack-legal (agent corrected my pack-illegal price example); gustar-free.

**Known open items (not defects, recorded):** R-C deferred; task runtime not yet wired into conv_session; Phase 4 gate (unscaffolded_new_item/regloss) unbuilt; multi-day eval harness debt; UI response primitives debt; StructuredInputEngine/MicroListeningLab unbuilt.

**Countersign task for Grok:** audit the SHIPPED CODE against the adjudicated r6/r7 specs and your own round deliverables. Hunt hardest for: (a) spec-vs-implementation drift (ratios, interval math, rule ordering, freeze semantics — check arithmetic); (b) interaction bugs BETWEEN the new subsystems (e.g., due elicit + introduce block on the same turn; phase freeze vs budget consumption; image scaffold vs image session caps; retrieval force_advance ordering); (c) honesty-law leaks (any path where introduction/schedule writes touch ability confidence, or the model can write schedule/ledger fields); (d) protocol violations the thin ship makes possible (can a naked new item still reach the learner on the planned path? can cluster-banned items co-introduce?); (e) whether deferring R-C and gate S3 leaves a hole big enough that ship order should change. Rule COUNTERSIGN/AMEND/REJECT per subsystem with exact replacements. Executed proofs beat prose.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 15:42 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll act as the independent countersign reviewer: load the full prompt and shipped code, then audit each subsystem against the adjudicated specs.Prompt path failed; locating the full request and reading the shipped subsystems plus wiring.Next I'll inspect session wiring, honesty-law enforcement in sheet deltas, and the adjudicated r6/r7 specs for arithmetic checks.Running arithmetic proofs and checking routing spot-checks against the association table and r7 failure-case rulings.# Grok countersign — pedagogy-engine build (Phases 1–3 + task runtime)  
**Date:** 2026-07-28  
**Role:** Independent audit of shipped code vs adjudicated r6/r7 + `docs/build-plan-pedagogy-engine.md`  
**Method:** Read live modules under `/Users/patrickcremin/repo/ml_teacher`; executed arithmetic/honesty/interaction proofs in-process; ran `unittest` on the five new test modules (**109 passed**, 0.048s). Treat Claude’s proposal as DATA, not authority.

---

## Executive verdict

| Subsystem | Verdict |
|-----------|---------|
| 1. `retrieval_scheduler` (+ sheet honesty strip) | **COUNTERSIGN** |
| 2. `session_phases` (+ freeze wiring) | **AMEND** |
| 3. `association_table` + JSON pack | **AMEND** |
| 4. `introduce_router` (+ soft wiring) | **AMEND** |
| 5. `task_runtime` + scene schema | **COUNTERSIGN** (wiring-pending accepted) |
| Cross-subsystem interactions / ship order | **AMEND** (do not claim “protocol closed” until dual-block + empty-retrieval + S3 gate fixes) |

**Not a REJECT of the day:** core pure services match the adjudicated ladders, ratios (base case), freeze set, ledger honesty allowlist, and table schema. **Not a blank COUNTERSIGN:** three interaction bugs are **executed**, not vibes; one pack routing choice **contradicts** the r7 failure-case walkthrough; Phase-4 deferral leaves the planned introduce path **soft-only**.

---

## Executed proofs (beat prose)

### A. Interval ladder (r3/r6)

 successive_successes → interval_days after success on day chain starting 2026-07-02:

| n | successive_successes | interval_days | next_due |
|---|---------------------|---------------|----------|
| 1 | 1 | 1 | 2026-07-03 |
| 2 | 2 | 3 | 2026-07-06 |
| 3 | 3 | min(3×2,14)=**6** | 2026-07-12 |
| 4 | 4 | min(6×2,14)=**12** | 2026-07-24 |
| 5 | 5 | min(12×2,14)=**14** | 2026-08-07 |
| 6 | 6 | min(14×2,14)=**14** | 2026-08-21 |

Fail → successive_successes=0, interval_days=1, next_due = day+1.  
**Matches** “1d → 3d → ×2 cap 14d; fail → 1d”.

### B. Phase budgets (est=14)

```
round(14×0.20)=3, round(14×0.30)=4, round(14×0.35)=5, round(14×0.15)=2
3+4+5+2 = 14
```

- due≥3: retrieval 3+1=**4**, free max(1,2−1)=**1**, sum **14**  
- blank: round(14×0.7)=**10**, free=**4**, sum **14**  
- limited_time: round(14×0.4)=**6**, task=**8**, sum **14**  
- **due=0:** pop retrieval → new_input 4 + task 5 + free 2 = **11** (missing the dropped 3) → **spec drift**

### C. Honesty law

- `_write({"confidence": 0.99, ...})` → `ValueError: scheduler may not write ['confidence']`  
- `mark_introduced` on entry conf=0.4 / status=emerging / solid_uses=2 → **unchanged** ability fields  
- `apply_delta` with model `next_due`/`introduced_at`/`interval_days`/`successive_successes`/`scaffold` → schedule fields **preserved from pre-delta sheet**; ability fields still model-writable (expected)

### D. Interaction: due + introduce same turn (**bug**)

Sheet with due `hola` + empty intro budget path, `activity_hint="new_input"`, `reason="default_conversation"`:

- `due_elicit_block` → **True** (items: hola)  
- `introduce_block` → **True** (e.g. key `buenos días`)  
- **BOTH ON SAME TURN = True**

Code path: `conv_session` appends due block for any conversation/transfer, then independently appends INTRODUCE when phase is new_input. No mutual exclusion.

### E. Interaction: empty retrieval force_advance ordering (**bug**)

Plan built with due_count=2 → first activity `retrieval`, but live sheet has **no** due items:

- **Current order:** use `activity=retrieval` for the turn (prefix still “prioritize DUE RE-ENCOUNTERS”), then `tick`, then `force_advance` → wastes one flavored turn  
- **Correct order:** `force_advance` **before** binding `activity` for the turn → activity=`new_input` immediately

### F. R-B instruction vs asset reality

`plan_instructions` for `casa` (R-B) always contains: *“an image of casa is **attached**”* — issued **before** `ensure_asset` / gen cap. Cache miss + gen denied ⇒ model instructed as if dual-code happened.

### G. Router spot-checks (table-driven)

| key | rule | matches proposal? | vs r7 worked example |
|-----|------|-------------------|----------------------|
| adiós | **R-A** (cognate_en set) | yes (proposal) | **No** — r7 §5 case: conventional farewell → **R-D** |
| por favor | R-A | yes | ok |
| casa | R-B (imageable beats keyword) | yes | ok |
| vaso | R-B, not cognate (false_friend) | yes | ok |
| hasta luego | R-E; forbid adiós, hasta mañana | yes | ok |
| me llamo | R-D | yes | ok |

Table stats verified: **175** entries, **27** themes, **20** false friends; zero dual cognate+false_friend; zero gloss >6 words.

### H. Unit tests

`unittest` on `test_retrieval_scheduler`, `test_session_phases`, `test_introduce_router`, `test_association_table`, `test_task_runtime`: **109 OK**. Full “375 tests” claim not re-run here (pytest missing in this environment); not used as a countersign criterion.

---

## 1. `tutor/retrieval_scheduler.py` — **COUNTERSIGN**

**Why:** Interval arithmetic exact; kind interleave works (sample max_due=3 → grammar+lexicon+skill, not three lexicon); `mark_introduced`/`enqueue`/`record_outcome` go through allowlisted `_write`; `apply_delta` strips `SCHEDULE_ENTRY_FIELDS`; outcomes in `conv_session._record_due_outcomes` are conservative (lexicon present / meta fail; grammar resolve-without-hit; skills silent).

**Residual (not blocking COUNTERSIGN):**  
- Grammar path only records **success**, never fail (silence) — consistent with “never guess,” not a honesty leak.  
- Creating a missing entry seeds `confidence: 0.0` / `status: "unknown"` via `_entry(create=True)` — not a confidence **bump**; acceptable.

No code replacement required for this subsystem.

---

## 2. `tutor/session_phases.py` (+ phase wiring) — **AMEND**

Base ratios and freeze semantics match r6. Two fixes required.

### AMEND 2a — redistribute when due_count==0

**Exact replacement** in `build_phase_plan` (replace the `due_count <= 0` branch body):

```python
    if due_count <= 0:
        dropped = budgets.pop("retrieval", 0)
        # Keep session length ≈ estimate: parked retrieval budget → free.
        budgets["free"] = budgets.get("free", 0) + dropped
    elif due_count >= 3:
        budgets["retrieval"] += 1
        budgets["free"] = max(1, budgets["free"] - 1)
```

**Arithmetic after amend (est=14, due=0):** 4+5+(2+3)=**14**, not 11.

### AMEND 2b — force empty retrieval **before** activity bind

**Exact replacement** in `ConversationalSession` turn path (conceptually before `select_mode`; replace the post-tick force block):

```python
        # Session phase layer: resolve empty retrieval BEFORE flavoring the turn.
        if self.phase_state.current_activity() == "retrieval":
            from .retrieval_scheduler import due_items as _due_now
            if not _due_now(self.sheet):
                self.phase_state.force_advance()

        activity = self.phase_state.current_activity()

        decision = select_mode(
            ...
            activity_hint=activity,
        )
        ...
        phase_consumed = phase_turn_consumed(
            decision.mode.value, decision.reason
        )
        self.phase_state.tick(phase_consumed)
        # Remove the old post-tick empty-retrieval force_advance block.
```

Freeze list itself (**COUNTERSIGN**): `PHASE_FREEZE_REASONS` + unconditional `comprehension_repair` mode freeze matches the proposal; cf_recast/form_focus/association/transfer consume unless reason is freeze-listed.

---

## 3. Association table (S4) — **AMEND**

Loader + validation + counts: **sound**. Content drift on the r7 failure-case key:

### AMEND 3a — `adiós` must not claim R-A against adjudicated r7 walkthrough

r7 adjudicated worked example: *adiós* → **R-D** micro-gloss, not cognate theater. Table currently sets `cognate_en: "adios (borrowed in English)"` which forces R-A (loanword circularity).

**Exact JSON replacement** for key `"adiós"`:

```json
  "adiós": {
    "gloss_en": "goodbye",
    "cognate_en": null,
    "false_friend": null,
    "keyword_en": null,
    "imageable": false,
    "theme": "farewells"
  }
```

**Expected router result after amend:** `adiós` → **R-D** with format `**adiós** (goodbye)`; still R-F-forbids `hasta luego`, `hasta mañana`.

### AMEND 3b — proposal spot-check text

**Replace** proposal line claim `adiós→R-A` with:

```text
adiós→R-D (no true cognate; conventional farewell micro-gloss); por favor→R-A; casa→R-B; vaso→R-B never cognate; hasta luego→R-E forbidding adiós/hasta mañana; me llamo→R-D.
```

---

## 4. `introduce_router` + soft wiring — **AMEND**

Rule order R-G → one target → R-F → R-A→R-B→R-E→R-D (R-C deferred), budget ≤2, visible-reply ledger write: **structurally correct**. Soft-only enforcement is the thin-ship risk (below).

### AMEND 4a — never stack DUE + INTRODUCE on one turn

**Exact replacement** for `due_elicit_block` signature/body gate (top of function after imports):

```python
def due_elicit_block(
    sheet: dict,
    *,
    mode: str,
    reason: str = "",
    today=None,
    max_due: int = 3,
    activity_hint: str | None = None,
):
    from .retrieval_scheduler import due_items

    # Phase sole-orchestrator: new_input owns introduce; do not compete with due.
    if activity_hint == "new_input":
        return "", []
    if mode not in DUE_ELICIT_MODES or reason in DUE_GUARD_REASONS:
        return "", []
    ...
```

**Call site** must pass `activity_hint=activity`:

```python
        due_block, due = due_elicit_block(
            self.sheet,
            mode=decision.mode.value,
            reason=decision.reason,
            activity_hint=activity,
        )
```

### AMEND 4b — R-B must not lie about attachment

After `ensure_asset` for introduce-driven `image_concept`, if no hit:

**Exact behavioral replacement** (append after image resolution when `intro_plan` is R-B):

```python
        if intro_plan is not None and intro_plan.scaffold_type == "image":
            has_img = any(
                (t.get("concept") or "") == intro_plan.key for t in (teach_images or [])
            )
            if not has_img:
                # Downgrade scaffold text: image dual-code failed (cap/cache).
                from .introduce_router import IntroducePlan, plan_instructions
                entry = (self.association_table or {}).get(intro_plan.key) or {}
                gloss = str(entry.get("gloss_en") or intro_plan.key)
                fallback = IntroducePlan(
                    key=intro_plan.key,
                    rule_id="R-D",
                    scaffold_type="gloss",
                    scaffold_payload={
                        "gloss": gloss,
                        "format": f"**{intro_plan.key}** ({gloss})",
                    },
                    forbid_cluster_with=list(intro_plan.forbid_cluster_with),
                )
                # Rewrite instructions: strip the false "image is attached" block.
                # (Implementation detail: rebuild decision.instructions without the
                # prior INTRODUCE paragraph, then append plan_instructions(fallback).)
                intro_plan = fallback
```

Minimal acceptable alternate: strip the INTRODUCE image claim and append one line  
`IMAGE UNAVAILABLE — use R-D once: **{key}** ({gloss}); then Spanish only.`

### AMEND 4c — protocol holes (honest residual)

| Question | Answer under thin ship |
|----------|-------------------------|
| Naked new item on planned path? | **Yes.** Free/task/retrieval turns have no introduce plan; model may still introduce. new_input plan is soft. **Phase 4 gate unbuilt = enforcement hole.** |
| Cluster-banned co-introduce? | **Yes, model can.** R-F is instruction text only (`Do NOT also introduce: …`). No code veto, no gate. |
| R-C deferred hole? | **Acceptable.** Fallback R-E/R-D exists; coverage math not required for thin ship. |
| Intro budget vs freeze? | **OK.** Freeze does not consume phase; intro budget only on visible `mark_introduced_if_visible` + `note_introduced`. |

---

## 5. `task_runtime` + scenes — **COUNTERSIGN**

Pure runtime, boundary matching, schema validation, three boat scenes with `primary_exit` / `tutor_private_info` / `learner_must_obtain`, gustar-free pack-legal content: **COUNTERSIGN** as Rank-4 **content half**.

Wiring pending into `conv_session` is correctly labeled open, not a defect of the pure module. Task-phase prefix still says “drive toward ONE concrete conversational goal” without machine-checked exit — expected until wire.

No exact replacement for the pure module. **Next wire contract** (for the later PR, not this countersign body): on `activity=="task"`, bind `task_from_scene` → `evaluate_turn` on learner text → append `task_instructions`; do not volunteer `tutor_private_info`.

---

## Cross-cutting (e): ship order — **AMEND**

| Deferred item | Change ship order? |
|---------------|-------------------|
| R-C engineered context | **No.** R-D/R-E cover. |
| Task runtime wire | **Soon, not before fixes 2b/4a.** Phase plan already allocates ~35% task turns that currently only get soft prefix. |
| Phase 4 `gate:unscaffolded_new_item` + `gate:regloss` | **Yes — raise priority.** Without it, introduce router + cluster ban are **advice**. r7 failure mode (bare dual farewells / naked first exposure) remains possible on free turns and when the model ignores INTRODUCE. |

**AMEND to Known open items (priority order):**

```text
P0 (block “protocol complete” claim):
  - AMEND 2b empty-retrieval force_advance-before-activity
  - AMEND 4a suppress due_elicit during new_input
  - AMEND 3a adiós → R-D table fix
P1 (enforcement):
  - Phase 4 gate:unscaffolded_new_item (critical) + gate:regloss (soft);
    must not fight gate:english_wall
P2:
  - Wire ConvergentTaskRuntime into conv_session task phase
  - AMEND 2a due0 budget redistribute
  - AMEND 4b R-B asset fallback
P3 (recorded debts):
  - R-C; multi-day fake-clock harness; UI choice primitives; SI engine; MicroListeningLab
```

---

## Honesty-law summary (c)

| Path | Leak? |
|------|-------|
| `retrieval_scheduler._write` | **No** — allowlist + restore protected |
| `mark_introduced` / `enqueue` / `record_outcome` | **No** ability bump |
| `apply_delta` schedule fields | **No** — stripped |
| Model confidence after introduce | Pre-existing model honesty (not schedule leak) |
| Introduce creating conf=0 entry | Not a bump |

---

## Final line

**COUNTERSIGN** pure Rank-1 scheduler honesty + interval math; **AMEND** phase due0/empty-retrieval, introduce/due mutex, adiós table/r7 alignment, R-B asset honesty, and ship-order (S3 gate before “protocol closed”); **COUNTERSIGN** task runtime as unwired pure half.  

Do **not** merge the review doc’s implication that interaction bugs are only “known opens” — dual DUE+INTRODUCE and empty-retrieval waste are **defects in the shipped wiring**, proved 2026-07-28.

---

## Adjudication — Round 1 (Claude, 2026-07-28)

All rulings ACCEPTED; no counters. Grok's executed proofs stand:

- **AMEND 2a/2b (phases) — ACCEPT.** due==0 must redistribute the parked retrieval budget to free (14, not 11); empty-retrieval force_advance must run BEFORE the activity binds so no turn is flavored for a phase with nothing due. Both are defects in shipped wiring, not "known opens" — the review record stands corrected as Grok demanded.
- **AMEND 4a (due/introduce mutex) — ACCEPT.** new_input owns introduction; due elicits suppressed during that phase (sole-orchestrator law applied to instruction blocks).
- **AMEND 3a/3b (adiós) — ACCEPT.** The loanword-circularity cognate was my agents' table drift against Grok's own r7 worked example; adiós routes R-D micro-gloss. Proposal spot-check text corrected by this adjudication.
- **AMEND 4b (R-B asset honesty) — ACCEPT.** Instructions must not claim an image is attached before the asset resolves; on miss, downgrade to R-D gloss fallback.
- **Ship order — ACCEPT.** Phase-4 gate (unscaffolded_new_item critical + regloss soft) raised to P1: without it the introduce protocol is advice. Task-runtime wiring lands after the P0 fixes, same batch.

Fix batch delegated 2026-07-28 (P0 + P1 gate + P2 in one owner to avoid conv_session conflicts). Review stays OPEN pending re-verification.

---

## Fix batch landed (agent, 2026-07-28)

Live v20260728-095944 (stale_code false); 391 tests + 17 subtests green; truncation gate ok.

- **AMEND 2a (due0 redistribute) → LANDED.** `build_phase_plan` due_count<=0 now parks the retrieval budget into free (Grok's exact replacement); est=14/due=0 → new_input 4 + task 5 + free 5 = 14. Arithmetic test updated (tests/test_session_phases.py).
- **AMEND 2b (empty-retrieval ordering) → LANDED.** conv_session resolves empty retrieval via force_advance BEFORE the activity binds/flavors the turn; old post-tick force block removed.
- **AMEND 4a (due/introduce mutex) → LANDED.** `due_elicit_block` takes `activity_hint` and returns empty on new_input; call site passes it; unit test added (tests/test_retrieval_scheduler.py).
- **AMEND 3a (adiós → R-D) → LANDED.** Table entry cognate_en → null (gloss "goodbye", theme farewells); router tests updated (R-A now exercised on igualmente; new test asserts adiós → R-D `**adiós** (goodbye)` with the farewell cluster ban intact).
- **AMEND 3b (proposal spot-check text) → LANDED.** Proposal line in this doc corrected to Grok's replacement text.
- **AMEND 4b (R-B asset honesty) → LANDED.** INTRODUCE block is rendered AFTER image resolution; an R-B plan whose image did not attach downgrades to R-D gloss (note `introduce_downgraded:<key>:R-B_to_R-D`); instructions can no longer claim a missing attachment. `last_mode_decision` snapshot moved after the render so the focus rail sees the true instructions.
- **P1 S3 gate → LANDED.** `gate:unscaffolded_new_item` (CRITICAL, added to conv_session critical set) + `gate:regloss` (SOFT) in tutor/output_gate.py: model/try detection over the association table, boundary/MWU matching with overlap filter (muy bien ≠ bien; cómo está vs cómo estás), gloss (≤6 words) / cognate / keyword scaffold signals, R-F cluster veto on same-theme extras even when glossed, regloss legal after a same-turn retrieval failure. Repair text mandates ONE gloss only (does not fight english_wall; regression test included). Context plumbed at all three gate call sites (table, sheet, IntroducePlan key, failed-due keys, learner text). 14 unit tests.
- **P1 gate pragmatics (recorded, agent judgment within the "never trip" mandate):** exemptions for introduced keys; any sheet-lexicon evidence conf > 0 (learner has met the item); keys in the learner's own current utterance (observer lags the gate by one turn); in_pack:false; structural paradigm/sequence themes (pronouns, question_words, copulas, numbers, function — cluster ban targets near-synonym interference, not paradigms/counting); placement mode (blank feel-out precedes the introduce protocol). Deviation from a literal reading: "high-confidence" skip widened to any-evidence conf > 0 to prevent per-turn refaulting of items the learner already produced.
- **P2 task wiring → LANDED.** conv_session task-phase turns bind the first task-capable open scene (session TaskState, persists until done); `evaluate_turn` on learner text BEFORE the tutor call; notes `task_slot_filled:<id>` / `task_complete:<scene_id>` / `task_goal_offered:<scene_id>`; task_instructions (incl. tutor_private_info + never-volunteer directive) attach on flavorable turns only (same set as INTRODUCE); after done, task turns fall back to normal flavor. Private values NOT added to the sheet-leak markers (not trivially compatible with the static marker list — skipped per instruction, recorded).
- **P2 eval → LANDED.** c11_task_infogap (known sheet, seed_phase_state index 1 → task phase from the open) + `task_goal_offered` mechanical check; run_conv_smoke gains `_apply_phase_state`.

---

## Adjudication of fix-batch judgment calls (Claude, 2026-07-28)

All five amendments verified landed (391 tests, v20260728-095944). The implementing agent made four recorded judgment calls in the Phase-4 gate; rulings:

1. **Evidence skip widened to lexicon conf > 0 — ACCEPT.** The introduce ledger is hours old; every pre-ledger word the learner demonstrably uses would otherwise fault as "never introduced." Correct rollout pragmatics. Revisit tightening (e.g., conf ≥ 0.2) once the ledger has weeks of coverage.
2. **Learner's-own-utterance skip — ACCEPT.** The tutor echoing the learner's word is uptake, not introduction; the observer records the evidence one turn later.
3. **Structural-theme exemption (pronouns/question_words/copulas/numbers/function) — ACCEPT.** The cluster ban's evidence base (Tinkham/Waring) is near-synonym interference; grammatical paradigms are taught as paradigms. Consistent with r7's basis, not a weakening.
4. **Placement-mode exemption — ACCEPT.** Blank-sheet placement precedes the protocol by design (r6 blank pathway).

Round-2 Grok verification of the gate requested (focused: gate correctness + these four calls). Review remains OPEN until it returns.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 16:07 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll load the full review request and the live fix-batch code so I can countersign item-by-item with executed proofs, not prose.Next I’ll pull the Fix batch / Adjudication sections and the gate/scheduler code those claims depend on.I'll run in-process proofs for the gate scan, the four judgment calls, and the round-1 amendment landings.Checking a few more edge cases that could drive false-positive storms, plus the remaining amendment landings.Checking ledger/gate asymmetry and the observer confidence floor that conf>0 depends on:# Grok countersign — Round 2: fix-batch verification  
**Date:** 2026-07-28  
**Role:** Independent re-verification of fix batch + four gate judgment calls (Claude adjudication is DATA, not authority)  
**Method:** Read live `/Users/patrickcremin/repo/ml_teacher` (`output_gate.py`, `session_phases.py`, `conv_session.py`, `introduce_router.py`, association table); executed in-process proofs; ran `unittest` on `test_session_phases` + `test_retrieval_scheduler` + `test_introduce_router` + `test_output_gate` (**110 passed**, 0.055s).

---

## Executive verdict

| Item | Verdict |
|------|---------|
| Round-1 AMEND 2a (due0 redistribute) | **COUNTERSIGN** (landed faithfully) |
| Round-1 AMEND 2b (force_advance before bind) | **COUNTERSIGN** (landed faithfully) |
| Round-1 AMEND 4a (due/introduce mutex) | **COUNTERSIGN** (landed faithfully) |
| Round-1 AMEND 3a (adiós → R-D) | **COUNTERSIGN** (landed faithfully) |
| Round-1 AMEND 4b (R-B → R-D on image miss) | **COUNTERSIGN** (landed faithfully) |
| Gate: bare / gloss / cluster / regloss unit law | **COUNTERSIGN** |
| Gate: “no false-positive storms” / “never trip” claim | **REJECT** (executed N=6 multi-key critical storms; see arithmetic) |
| Gate residual: incidental gloss ≠ ledger write | **AMEND** |
| Judgment 1: conf > 0 evidence skip | **COUNTERSIGN** (and **REJECT** tightening to ≥0.2 now) |
| Judgment 2: learner-utterance skip | **COUNTERSIGN** |
| Judgment 3: structural-theme exemption | **AMEND** (intent OK; `soy` hole) |
| Judgment 4: placement exemption | **COUNTERSIGN** |

**Overall:** Fix batch **lands the five Round-1 amendments**. Phase-4 gate **meets r7 S3 unit success criteria** and correctly hard-faults the 2026-07-28 dual-farewell failure shape. It does **not** yet earn a blank “protocol closed / never trip” stamp: early multi-formula tutor turns storm, and scaffold-without-ledger is unstable across turns.

---

## 1. Gate scan vs r7 protocol + storm check

### 1a. Protocol hits (executed — COUNTERSIGN mechanics)

Using real pack table (175 keys) + `scan_unscaffolded_new_items` / `check_output_gate`:

| Case | Result |
|------|--------|
| Bare unintroduced `hasta luego` | `gate:unscaffolded_new_item` CRITICAL |
| `**Hasta luego** (see you later)` | clean |
| Two glossed farewells same theme | extra (`adiós`) CRITICAL — R-F as code |
| `introduce_key` holds cluster slot | planned key kept; extra still faults |
| Introduced + re-gloss | `gate:regloss` SOFT (not in critical set) |
| Re-gloss after `retrieval_failed_keys` | regloss suppressed |
| Introduced bare reuse | clean |
| `mode=placement` | S3 disabled |
| `english_wall` + bare new item | both faults; repair still says ONE gloss |
| Overlap `muy bien` vs `bien` | longest-key wins; no double count |
| Critical set in `conv_session` | includes `gate:unscaffolded_new_item`; regloss soft by omission |

Boundary/MWU matching, ≤6-word gloss, cognate/keyword anchors, R-F cluster veto, and english_wall coexistence match r7 S3 success criterion wording (bare first-seen → fault; glossed → pass; re-gloss → soft).

### 1b. False-positive / storm arithmetic — **REJECT** “never trip / no storms”

Agent claim (fix-batch note): pragmatics kept under a “never trip” mandate. **Refuted by execution.**

**Blank sheet, realistic multi-formula tutor turn** (`model`+`try` with hola / buenos días / cómo estás / bien / gracias / y tú / cómo te llamas):

- faulted key count **N = 6** (stable across 5 repeats)  
- fault class: **CRITICAL** `gate:unscaffolded_new_item`  
- formulaic theme inventory in pack: **30** keys across greetings / how_are_you / introductions / courtesy / farewells  

**After observer evidence** (`process_turn` on learner *“Hola, me llamo Ana. Estoy bien.”* → lexicon conf **0.12** on `hola`, `me llamo`, `estoy`):

- with `learner_text`: still **N = 3** faults (`soy`, `cómo estás`, `y tú`)  
- without `learner_text`: **N = 4** (adds `bien`)  

**Partial conf sheet** (hola/bien/gracias at conf>0): realistic turn still **N = 4**.

These are letter-true under “every unintroduced non-structural table key needs scaffold,” but they are **product storms**: ordinary CI turns after placement re-enter the critical repair loop for high-frequency classroom Spanish the router will not formally introduce (budget ≤2/session; 30 formula keys ≫ 2).

Additional cross-language FP (secondary): English *“Use a pan for eggs.”* → faults `pan` (pack key). Rare if spanish_ratio holds; still a matcher blind spot.

**Verdict on storm claim:** **REJECT** agent/adjudication implication that pragmatics eliminated storms. Mechanics COUNTERSIGN for unit cases; storm residual is real.

### 1c. Ledger asymmetry (executed) — **AMEND**

```
turn1: model="**gracias** (thank you)" → faulted=[] ; is_introduced=False
turn2: model="Gracias."              → faulted=['gracias']
turn2 with conf=0.12                 → faulted=[]
```

Gate accepts incidental first-exposure gloss, but **only** `IntroducePlan` → `mark_introduced_if_visible` writes the ledger. Next bare use re-faults until learner produces conf>0. That is not “regloss” (soft); it is perpetual **critical** unscaffolded thrash.

**Exact replacement (engine contract, not prose):** after a turn where `scan_unscaffolded_new_items` would have faulted key *k* but *k* was saved solely by `_gloss_after_key` or `_anchor_in_reply` (and *k* ≠ already introduced), call the same honesty-preserving `mark_introduced(sheet, k, "lexicon", scaffold_type)` path used by the router (confidence untouched). Cap: ≤ session intro budget **or** a separate `first_seen` flag if budget must stay introduce-router-only — but **some** durable “seen with scaffold” bit is mandatory; otherwise S3 fights free CI.

---

## 2. Four judgment calls

### (1) Evidence skip widened to lexicon conf > 0 — **COUNTERSIGN**

Executed: conf **0.12** from `process_turn` skips `hola`; conf **0.0** / missing conf does not.

**Arithmetic against later tighten-to-0.2:**

| threshold thr | conf=0.12 skips when conf > thr? |
|---------------|-----------------------------------|
| 0.0 (shipped) | yes |
| 0.1 | yes |
| 0.12 | **no** (strict >) |
| **0.2** | **no** → re-faults observer bumps |
| 0.3 | no |

Adjudication note “revisit conf ≥ 0.2 later” would **break** current observer increments of 0.12. **REJECT** any near-term raise to 0.2 without also raising the observer floor. conf > 0 is the correct thin-ship cutoff.

### (2) Learner’s-own-utterance skip — **COUNTERSIGN**

Executed: `learner_text="Mi casa es grande"` removes `casa`/`grande` from fault set; pedagogically uptake, not introduction; observer lags gate by one turn.  
**Soft residual:** no dedicated unit test for `learner_text=` (code path untested in `tests/test_output_gate.py`) — add test, not a design reject.

### (3) Structural-theme exemption — **AMEND**

**Intent COUNTERSIGN:** Tinkham/Waring interference is near-synonym clustering, not pronoun/number/copula paradigms; exempting `pronouns`, `question_words`, `copulas`, `numbers`, `function` matches r7 basis.

**Hole (executed):** table places **`soy` under theme `introductions`**, while **`ser`/`estar` are `copulas`**.

```
model="Yo soy estudiante. Tú eres amable."
→ faulted includes 'soy' (and estudiante, amable, y tú)
→ 'yo' exempt (pronouns); 'ser' lemma never appears so copulas exemption never fires
```

**Exact replacement options (either is fine; pick one):**

**A (table):** change entry  
`"soy": {..., "theme": "copulas"}`  
(and any other surface forms you add later under copulas).

**B (gate):** extend structural skip:

```python
STRUCTURAL_THEMES = frozenset({
    "pronouns", "question_words", "copulas", "function", "numbers",
})
STRUCTURAL_KEYS = frozenset({
    # surface forms of exempt paradigms not themed as structural
    "soy", "eres", "es", "somos", "sois", "son",
    "estoy", "estás", "está", "estamos", "estáis", "están",
})
# in scan loop, after theme check:
if key in STRUCTURAL_KEYS:
    continue
```

Do **not** stuff full greetings/how_are_you into STRUCTURAL — that would gut S3 for the original dual-farewell failure case.

### (4) Placement-mode exemption — **COUNTERSIGN**

Executed: `mode="placement"` → no unscaffolded/regloss faults; aligns with blank feel-out + phase freeze + router never planning on placement.

---

## 3. Round-1 exact replacements — spot verification

### AMEND 2a due0 redistribute — **COUNTERSIGN**

```
est=14, due_count=0:
  new_input=4, task=5, free=5
  sum = 4+5+5 = 14
  retrieval absent
due_count=1 base: 3+4+5+2 = 14
due_count=3: retrieval=4, free=1, sum=14
```

Matches Grok’s exact “park retrieval into free” replacement (not the old sum-11 bug).

### AMEND 2b force_advance ordering — **COUNTERSIGN**

`conv_session.py`: **one** `force_advance` call site; order is:

1. if activity would be retrieval and `due_items` empty → `force_advance()`  
2. **then** `activity = self.phase_state.current_activity()`  
3. `select_mode(..., activity_hint=activity)`

No post-tick empty-retrieval force remains.

### AMEND 4a due/introduce mutex — **COUNTERSIGN**

`due_elicit_block(..., activity_hint="new_input")` → `("", [])` even with due `hola` (`next_due=2020-01-01`).  
Same sheet with `activity_hint="retrieval"` → non-empty DUE block. Call site passes `activity`.

### AMEND 3a adiós → R-D — **COUNTERSIGN**

Table: `"adiós": {gloss_en: "goodbye", cognate_en: null, theme: "farewells"}`.  
`plan_introduction(..., key="adiós")` → **R-D**, format `**adiós** (goodbye)`, forbid `['hasta luego', 'hasta mañana']`.  
Spot-check set: por favor R-A; casa R-B; vaso R-B; hasta luego R-E; me llamo R-D; igualmente R-A.

### AMEND 4b R-B asset honesty — **COUNTERSIGN**

INTRODUCE rendered **after** image resolution; on miss, plan rewritten to R-D gloss; note `introduce_downgraded:<key>:R-B_to_R-D`; R-B native instructions still say “image … attached” only when plan remains R-B; downgraded instructions contain **no** “attached”. `last_mode_decision` snapshot is after render.

---

## 4. What this round does **not** re-open

- Interval ladder, honesty strip, task-runtime wiring, R-C deferral: out of scope for Round 2 focus; no new reject.  
- Cluster ban on dual glossed farewells: still correct; do not weaken.

---

## 5. Closure conditions for this review

Review can move to **CLOSED — CONVERGED** only after:

1. **AMEND 1c** (incidental scaffold → durable introduced/first-seen write), **or** an explicit accepted residual that free CI will re-gloss forever without conf.  
2. **AMEND 3** (`soy` theme or STRUCTURAL_KEYS).  
3. Optional but recommended: unit test for `learner_text` skip; fixture that a multi-formula blank turn’s repair behavior is intentional (document storm as true-positive) **or** a scoped formula soften that does **not** re-allow dual bare farewells.

Until (1) and (2): **OPEN** with Round-1 amendments **COUNTERSIGNED** and gate **conditionally countersigned** (unit law yes; storm/ledger residuals no).

---

### One-line summary for the record

**Five Round-1 amendments: COUNTERSIGN landed. Four judgment calls: conf>0 / learner-utterance / placement COUNTERSIGN; structural AMEND (`soy`). Gate unit law COUNTERSIGN; “no storms” REJECT (N=6 blank multi-formula critical); incidental-gloss/ledger AMEND required before “protocol closed.”**

---

## Adjudication — Round 2 (Claude, 2026-07-28)

Round-1 amendments: all five COUNTERSIGNED as landed — accepted, no further action. Rulings on the new findings:

1. **AMEND 1c (incidental-gloss ledger asymmetry) — ACCEPT.** Grok's executed proof stands: a model-volunteered gloss passes the gate but never writes the ledger, so the next bare use re-faults CRITICALLY forever — perpetual thrash, not regloss. Fix per Grok's contract: when a key is saved solely by in-reply scaffold (gloss/anchor) and is not introduced, write a durable `first_seen` ledger bit through the honesty-preserving scheduler path (confidence untouched). `first_seen` is DISTINCT from the introduce budget — the budget stays router-only; a first_seen key stops gate thrash but does not consume an introduction slot and does not enqueue retrieval (the router still owns real introductions).
2. **Storm REJECT — ACCEPT the rejection; scoped soften adopted.** The "no storms" implication in my fix-batch adjudication was wrong; Grok's N=6 blank-turn proof stands. Ruling: when ≥3 DISTINCT unscaffolded keys fire on one turn (formulaic-opener signature, e.g. hola/cómo estás/bien), the fault degrades to SOFT `gate:unscaffolded_flood` (logged, no forced rewrite) — EXCEPT same-theme cluster extras, which stay CRITICAL at any count (the dual-farewell case fires at N=2 and is untouched). ≤2 unscaffolded keys stay CRITICAL. Combined with 1c and observer conf bumps, the storm self-drains within a session while the original failure class remains hard-blocked. This is Grok's "scoped formula soften that does not re-allow dual bare farewells."
3. **AMEND 3 (soy hole) — ACCEPT, option B.** STRUCTURAL_KEYS surface-form set (ser/estar conjugations) in the gate — more robust than retheming, which a future table edit could silently regress. Grok's guardrail honored: greetings/how_are_you/farewells themes are NOT added to structural.
4. **Judgment-call rulings — ACCEPT all**, including the REJECT of my "revisit conf ≥ 0.2" note (would break 0.12 observer bumps; the note is withdrawn). learner_text skip gets its missing unit test.

Fix batch delegated 2026-07-28. Closure conditions (1) and (2) will be re-verified in-code; review closes on green.

---

## Round-2 amendments landed (agent, 2026-07-28)

Fix batch executed per the Round-2 adjudication. Factual record; closure adjudication pending (Claude).

1. **AMEND 1c (incidental-scaffold first_seen) — LANDED.** `retrieval_scheduler.mark_first_seen`/`has_first_seen` write/query a durable `first_seen` iso-date via the honesty-preserving `_write` allowlist (`first_seen` added to `SCHEDULE_FIELDS` + `character_sheet.SCHEDULE_ENTRY_FIELDS`; tool deltas still stripped; normalize coerces garbage). No `introduced_at`, no enqueue, no budget consumption, confidence/status untouched. The gate scan returns `scaffold_saved` (key → gloss|anchor); `conv_session` writes `first_seen:<key>` post-turn next to `mark_introduced_if_visible`; first_seen keys skip the scan on later turns. Thrash proof now a passing test (`test_first_seen_stops_gloss_then_bare_thrash`): gloss turn1 → bare turn2 CLEAN (no unscaffolded/flood/regloss fault).
2. **Storm soften (gate:unscaffolded_flood) — LANDED.** ≥3 distinct BARE unscaffolded keys → soft `gate:unscaffolded_flood` carrying the key list (not in conv_session's critical set — verified by source assertion in the test); ≤2 bare keys stay CRITICAL; glossed same-theme cluster extras stay CRITICAL at any count. Grok's storm reproduced (`test_formula_storm_softens_to_flood`): blank sheet, hola/buenos días/cómo estás/bien/gracias/y tú → flood keys exactly those 6, NO critical, no forced rewrite. Dual-farewell protection verified untouched at N=2 (glossed-extra test unchanged + new bare-pair test `test_two_bare_keys_stay_critical_no_flood`); mixed 4-key turn (`test_flood_plus_glossed_cluster_extra_keeps_critical`): CRITICAL on adiós cluster extra + soft flood on {hola, gracias, bien}; the extra earns NO first_seen.
3. **AMEND 3 option B (STRUCTURAL_KEYS) — LANDED.** Frozen surface-form set soy/eres/es/somos/sois/son/estoy/estás/está/estamos/estáis/están checked after the theme exemption; «Yo soy estudiante.» no longer faults `soy` (`test_structural_keys_soy_never_faults`, which also pins the exact frozenset and asserts greetings/how_are_you/farewells are NOT structural — Grok's guardrail).
4. **learner_text skip unit test — LANDED.** `test_learner_own_utterance_key_does_not_fault`: tutor echoing a key from the learner's own utterance is clean; control without learner_text still faults.

Verification: `pytest tests/ -q` → **399 passed, 17 subtests passed** (0 failed); `scripts/check_teacher_truncation.py` → ok (14 files); server restarted → `/api/health` version **20260728-101710**, `stale_code: false`.

---

## Closure — CONVERGED after 2 rounds (Claude, 2026-07-28)

Grok's two closure conditions are met and re-verified: (1) incidental-scaffold `first_seen` ledger writes (honesty-preserving path; no budget consumption, no enqueue, no confidence movement; the executed thrash proof now passes as a permanent test); (2) STRUCTURAL_KEYS surface-form set (Grok's exact 12 ser/estar forms; greetings/farewells themes explicitly NOT structural, test-pinned). Recommended items also landed: learner_text skip test; the storm reproduced as a test and softened to `gate:unscaffolded_flood` (soft) at ≥3 distinct bare keys, with both dual-farewell shapes (bare pair and glossed pair at N=2) still CRITICAL.

**Accepted residual (recorded, not hidden):** a bare same-theme pair buried inside a ≥3-key formulaic flood rides the flood (soft) rather than tripping the cluster CRITICAL. This is the price of the storm soften; it lives under the STORM RESIDUAL debt in PEDAGOGY.md §8 and is re-examined when first_seen coverage makes floods rare in live logs.

Final state: 399 tests + 17 subtests green; truncation gate ok; live v20260728-101710. Score for the review: two rounds, three executed wiring defects caught, one table spec-drift caught, one storm false-claim rejected, one thrash class eliminated — all by countersign, all repaired and test-locked. **Review CLOSED — CONVERGED.** Law already reflects this round (PEDAGOGY.md §2.2, §8 STORM RESIDUAL, §9 enforcement map); no further promotion needed.

---

## Incident: irrelevant teach image on meta turn (2026-07-28)

Live session `20260728-103617-conversational-web`, turn 3 (16:38:34Z): learner asked «digo and dices.. can I get a breakdown on what these mean and how to use them?» — the reply correctly taught digo/dices, but a `hola.jpg` teach image attached (`teach_images: concept=hola, decision_reason="mode:comprehension_repair", cache=hit`; notes `mode=comprehension_repair`, `mode_reason=meta_comprehension_stay_on_topic`, `teach_image:hola`). The hola did NOT come from placement (turn 1 was `conversation/known_open_from_sheet`, no image; turn 2 introduced hola via R-E, no image): the meta branch of `select_mode` harvested `image_concept="hola"` from the PREVIOUS turn's `last_concepts` («Si digo ¡Hola!, ¿qué dices tú?»), and `conv_session._execute_ai_tutor` served it via `ensure_asset`. Generator-level class: image concepts on comprehension_repair/meta turns were inherited from prior-turn content with no relevance check tying them to what THIS turn actually teaches, so the system served SOME image instead of NONE (violates r5 multimodal law: images only when diagnostic, absent beats wrong; PEDAGOGY P2). Fix (code-owned surface matching per §4.2, no LLM): `tutor/teach_assets.py` adds `concept_in_text` (alias-aware, boundary-safe via `observe.word_present`) plus a hard `require_relevant_to` gate in `assets_for_ai_turn` (`skip_irrelevant_concept`); `tutor/modes.py` meta branch now only binds an image whose concept is surface-present in the learner's own message (true non-comprehension — «no entiendo»/pure echo — keeps the repair-target image, since that concept IS being re-taught); `tutor/conv_session.py` passes the current-exchange text as the relevance requirement on the comprehension_repair fallback and drops tutor-declared `<image>` concepts absent from the visible reply (`image_declared_irrelevant:<c>` note). Audited: placement's hardcoded hola is reachable only on the true session-open turn (`is_open and blank`; `user_turn` always passes `is_open=False` and rejects empty text); association/introduce/scene concepts are relevant by construction (the concept is the taught item). Tests (regression anchor uses the verbatim incident turn): `test_meta_grammar_question_no_irrelevant_image_incident_20260728`, `test_what_does_x_mean_uses_learner_relevance`, `test_meta_question_about_concept_keeps_its_image`, `test_true_noncomprehension_keeps_repair_target_image` (tests/test_modes.py); `TestFallbackRelevanceGate` (4 tests, tests/test_plan_card.py); placement-open hola assertion added to `test_placement_on_blank_open`. `pytest tests/ -q` → 407 passed + 17 subtests; truncation gate ok (14 files). Code-on-disk only — the live server was NOT restarted; fix takes effect on next restart.

---

## Incident: inert morphology card (2026-07-28)

Live session `20260728-103617-conversational-web`: the web Morphology card never updated across the whole session, including turn 3 («digo and dices.. can I get a breakdown…») and turn 9 («Yo hacer (I am making?) deysayunas»). Mechanism: `build_focus_panel` (tutor/can_dos.py:534–546 pre-fix) keyed morphology solely off `mode_decision.targets.form_id` or `next_best.form_focus` against the static `MORPHOLOGY_BY_FORM` inventory — turn 3's comprehension_repair targets carried no form_id, turn 9's `estar_yo_estoy_vs_esta` is an error-pattern id absent from that inventory, and decir/hacer have no inventory entry at all, so every build fell through to the same can-do phrase block; additionally `sheet_public` (tutor/conv_session.py:2182–2183) overwrites any async FOCUS_MODEL morphology edits on every paint with a freshly rebuilt static panel, so even LLM-added rows could never surface. Fix (code decides WHICH form, per PEDAGOGY §1.1; LLM only fills example cells): new `tutor/turn_morph.py` — `detect_turn_morph` classifies the learner turn (error-pattern hit mapping to a form id > pronoun+bare-infinitive attempt «Yo hacer»→«Yo hago» > Spanish form named in a meta question (digo/dices→decir, with «cómo se dice» frames stripped so the frame's own "dice" can't self-trigger) > English how-say/"I am Xing?" target→A1 lemma), returning an A1 present-tense 4-person block (attempt-vs-target in `watch`, asked-about persons highlighted) or None on no engagement; `stash_turn_morph` writes the block onto the live mode-decision dict — the same object every `sheet_public` repaint passes to `build_focus_panel` — so the block persists exactly one turn and dies with the next decision, with no conv_session edit. `enrich_focus_panel` (tutor/focus_enrich.py) stashes before building (static and AI paths both) and passes a `turn_morph_target` hint so FOCUS_MODEL extra_rows decorate only the code-chosen lemma; `build_focus_panel` (tutor/can_dos.py) puts the turn block first (deduped, ≤2 blocks, learner grammar status still stamped). Pack-aware by construction: `A1_VERB_MORPH` holds present-tense-only 4-row paradigms; ambiguous trigger tokens (es, como, come, esta, van…) are excluded so a wrong card never flashes. No client change needed — `renderMorphology` already renders the block shape, so no cache-bust. Tests: `tests/test_turn_morph.py` (12: dice meta question→decir with person highlights, «Yo hacer»→hacer with attempt/target watch, how-say→hacer/ir, «yo está»→estar via error pattern, no-engagement→None×4, cómo-se-dice frame guard, A1 present-only pack guard, panel-leads/status-stamp/unchanged/stale-clear/enrich-static integration). `pytest tests/ -q` → 419 passed + 17 subtests; truncation gate ok (14 files). Code-on-disk only — the live server was NOT restarted; fix takes effect on next restart.

---

## Incident: session image generation never fires (2026-07-28)

User report (live): "images are stuck on static and no auto generation is being allowed." Ledger evidence: `logs/costs.jsonl` holds exactly 10 image events — 9 `source="prewarm"` (02:21:57–02:22:52Z batch) and 1 `source="web"` at 02:04:06Z — zero live generations since. Investigation ruled out the structural world: the generator IS installed on the web path (`web_app.py:151-159` `create_app()` → `install_teach_image_generator()`, module-level `app = create_app()` at web_app.py:553; `.env` carries the Gemini key via `config.load_env()`), and the RUNNING process confirms it live (`/api/health` → `teach_image_cache: generate_on_miss: true, generator_registered: true, generate_enabled: true, image_model: gemini-2.5-flash-image`). Session-path generation demonstrably worked: session logs show live `miss_generated` serves on 07-26 (bote 19:23, cafe 19:25, comida 21:58, sol 22:08) and 07-27 (rio 22:43) — these predate the cost ledger (telemetry shipped 07-28), which is why the ledger looks prewarm-only. Actual mechanism (world b, coincidental-by-construction): since the 02:21Z prewarm the cache (20 indexed concepts) fully covers the CLOSED concept universe of every image path that has ever fired — `modes._noun_from_text` pairs (modes.py:288-311), `_fallback_association_concept` (modes.py:207) and `_new_concrete_noun` (modes.py:266) both draw from (cafe, comida, musica, rio, bote), and `CONCEPT_LEXICON` (teach_assets.py:54, 10 entries) — so every request hits cache. The only routes to a novel concept — introduce R-B (introduce_router.py:185; 62 imageable non-cognate association keys, mostly uncached) and tutor-declared `<image>` — have never fired (entire log history: `introduce_planned:me llamo:R-D` ×2, `introduce_planned:hola:R-E` ×2, zero R-B, zero declared): the curriculum simply hasn't reached imageable vocabulary. One real code defect found and fixed: the PRIMARY mode-path attach (conv_session.py) returned silently when a requested concept resolved no image (cap denied / generator missing / generation failed) — invisible misses made this incident require forensic log work. Fix (disk only): `tutor/conv_session.py` extracts the attach into `_attach_mode_image()` which notes every miss (`image_gen_capped:<c>` / `image_gen_disabled:<c>` / `image_gen_failed:<c>`); `tutor/teach_assets.py` adds `generation_ready()`. Caps unchanged (8/session, 5 declared); generation remains a decision; the relevance gate from the previous incident stays upstream. Health fields verified populated and surfaced (cache_stats teach_assets.py:1013-1014 + web_app.py:196-197) — no change needed, now test-pinned. Tests: `TestModeImageAttachVisibility` in tests/test_session_fixes.py — `test_session_miss_generates_and_records_cost` (fake generator; miss → `miss_generated` + ledger image event via isolated `COST_LEDGER_PATH`), `test_session_miss_disabled_notes_visible`, `test_session_miss_capped_notes_visible` (generator present, cap respected, NOT invoked), `test_cache_hit_unaffected_no_notes`, `test_health_fields_populated`. Suite 424 passed + 17 subtests, 0 failed; truncation gate ok (14 files). The live server was NOT restarted; the running process keeps the old code until the user restarts.
