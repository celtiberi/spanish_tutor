# Review: whole-system audit — end of 2026-07-28

## Proposal / audit brief (⬛ Claude, 2026-07-28)

Scope: everything shipped AFTER the pedagogy-engine build review closed (docs/reviews-pedagogy-engine-build.md, closed at v20260728-101710) through v20260728-124829 — roughly eight batches landed by different agents in rapid succession:
1. Image relevance gate + generation-miss visibility (conv_session, teach_assets, modes).
2. Turn-aware morphology card (turn_morph.py, can_dos, focus_enrich).
3. Progression journey rail (progress_ledger.py, emit sites, /api/progress, web UI) + rail integrity fix (scaffold-evidence introduce marks, retractions, theme grouping, display_state).
4. Defect batch (Close phase in session_phases/modes/conv_session; full-reply gate scan; correction rules; §2.1a shadow signals + self-flag uptake with budget).
5. Zero-English true-zero register (modes wrapper + ZERO_REGISTER_NOTE, executor stance exception).
6. Closing batch (debug capture + /api/debug/requests; english_wall ZERO_MIN_SPANISH_RATIO for placement/blank_zero; asked-topics registry + do_not_re_ask + guard-6 escape-hatch deletion + generalized probe_loop; session-reset race fix + idle reaper).

Suite state: 526 tests + 17 subtests green; truncation gate ok. All prior review rounds converged; laws current in PEDAGOGY.md (§1.1a, §2.1a, Close phase, debts).

**Audit task for Grok — hunt hardest for INTERACTION defects between these batches (they were built by different agents against a moving base):**
(a) Cross-batch state interactions: covered_concepts ∪ images_shown vs the introduce router's candidate exclusion; asked_topics registry vs due-elicit and task blocks (can a due re-encounter be suppressed as a "repeat"?); blank_zero register vs Close phase (does a zero session still close bilingually?); scaffold-evidence marks vs first_seen writes (can a key be first_seen AND introduce-lapsed in one turn, and what does the gate do next turn?).
(b) Gate coherence after all edits: full-reply scan + flood threshold + ZERO_MIN_SPANISH_RATIO + probe_loop registry — construct adversarial replies that satisfy one gate while violating another's intent; verify the repair instructions cannot demand contradictory rewrites in one turn.
(c) Honesty: retraction machinery (voided milestones re-mintable, dedupe correctness after retraction); debug capture never writing payloads to disk; ledger/scheduler allowlists still airtight after the new writers (retract_introduction, mark_first_seen, record_outcome_ex).
(d) The reset path end-to-end: sheet reset + session replacement + phase-state rebuild + zero register + placement — walk the exact user flow that produced today's D session and verify every fixed defect stays fixed IN COMBINATION.
(e) Performance/latency: the per-turn payload has grown (dashboard blocks, notes, debug capture) — anything now on the hot path that violates the never-block-the-reply design?
Executed proofs beat prose. COUNTERSIGN/AMEND/REJECT per area with exact replacements. Live repo at /Users/patrickcremin/repo/ml_teacher.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 18:59 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll run an independent countersign on the whole-system audit: load the full brief and code, then verify each area with evidence rather than deferring to the proposal.The brief asks for per-area COUNTERSIGN/AMEND/REJECT with executed proofs. I'll inspect the live code paths for each interaction risk.Next I'll read the critical interaction surfaces and run targeted proofs against the live code.Running executed proofs against the live modules for each audit area.Refining the introduce-lapse proof and finishing the remaining areas.## Countersign — whole-system audit (2026-07-28)

**Reviewer:** Grok (independent)  
**Subject:** `docs/reviews-system-audit-20260728.md` audit brief (batches after pedagogy-engine close through v20260728-124829)  
**Method:** executed proofs against live modules under `/Users/patrickcremin/repo/ml_teacher` (not prose review of the brief). Suite collect: **526 tests** matches the claim.

---

### (a) Cross-batch state interactions — **AMEND** (3 real interaction defects; 1 clean)

#### (a1) `covered_concepts ∪ images_shown` vs introduce router — **DEFECT**

**Proof (2026-07-28):** After `note_concept_covered("casa")` + `note_image("casa")`, `candidate_keys` still lists `casa`; `plan_introduction(..., key="casa")` returns `casa/image`. `_eligible` only checks table / `is_introduced` / lexicon confidence — **session cover/image sets are invisible to the router**.

`conv_session` correctly unions cover∪images for **guard-6** (`select_mode` `images_shown=`), so association will not re-fire `new_noun:casa`, but **new_input can still plan a second “first introduce”** of the same concept.

**AMEND — exact replacement** in `tutor/introduce_router.py` `plan_introduction` / `candidate_keys`:

```python
# In candidate_keys / _eligible path, accept session exclusion:
def candidate_keys(sheet, table, *, pack_topics=None, session_snapshot=None):
    snap = session_snapshot or {}
    exclude = {
        str(x).strip().lower()
        for x in list(snap.get("images_shown") or [])
        + list(snap.get("covered_concepts") or [])
        if x
    }
    ...
        if not _eligible(sheet, table, key):
            continue
        if key in exclude or key.lower() in exclude:
            continue
```

And pass `session_snapshot` into `candidate_keys` from `plan_introduction` (it already receives the snapshot; today it only reads intro budget fields).

Wire test: covered+imaged `casa` ⇒ not in candidates; forced `key="casa"` may still plan only if explicitly forced (document choice: prefer **exclude even on force** for session-local honesty).

#### (a2) `asked_topics` / `do_not_re_ask` vs due-elicit — **DEFECT** (intent conflict)

**Proof:**

1. `due_elicit_block` signature has **no** `asked_topics` / due-filter param.  
2. Sheet with `casa` introduced, `next_due=2026-07-27`, `today=2026-07-28` → due list `['casa']`, non-empty DUE block on `activity_hint="retrieval"`.  
3. Same turn shape try `¿Dónde está tu casa?` with `asked_topics={"location:casa"}` → **`gate:probe_loop`**.  
4. `probe_loop` ∉ `critical` set in `conv_session` (soft only) — so no forced rewrite, but the tutor is **instructed to re-encounter** and **soft-faulted / do_not_re_ask-warned** for the natural location frame.

Spacing (P3 / due) and anti-repeat (asked_topics) **cross-batch fight**. Soft status reduces severity; it does **not** clear the design bug.

**AMEND — exact replacement** in `tutor/output_gate.py` topic-registry branch (~lines 653–660):

```python
    if asked_topics:
        from .session_memory import compose_topic_key, topic_key_for_try
        from .retrieval_scheduler import due_items

        try_txt = str(parts.get("try") or parts.get("continue") or "")
        frame, concept = topic_key_for_try(try_txt, nouns=topic_nouns)
        topic_key = compose_topic_key(frame, concept)
        if topic_key and topic_key in set(asked_topics):
            # Retrieval > anti-repeat: a currently-due concept may be
            # re-elicited even if this frame+concept was asked earlier.
            due_keys = {d.key for d in due_items(sheet or {}, max_due=50)} if isinstance(sheet, dict) else set()
            concept_due = bool(concept) and (
                concept in due_keys
                or concept.replace("á", "a") in due_keys  # only if you already deaccent keys; prefer exact key match from extractor
            )
            if not concept_due:
                loop_hits.append(f"topic:{topic_key}")
```

(Prefer exact pack-key match from the same noun list used to build `topic_key`; deaccent only if ledger keys are deaccented.)

Optional mirror: when building DUE block, prefer elicit shapes that are **not** bare re-asks of stored frames (model instruction), but **code gate exemption for due keys is mandatory**.

#### (a3) `blank_zero` vs Close — **CLEAN / COUNTERSIGN sub-item**

**Proof:** `activity_hint="close"` + blank sheet + no `spanish_ok` → `mode=conversation`, reason `default_conversation`, instructions contain **both** `SESSION PHASE: CLOSE` and `ZERO_REGISTER_NOTE`. Bilingual close sample under `blank_zero=True` does **not** trip `gate:english_wall` (ratio/threshold path works; zero session **can** close bilingually). Blank phase plan ends with close: `new_input(10) + free(3) + close(1)`.

#### (a4) scaffold-evidence / `first_seen` vs introduce-lapse — **DEFECT**

**Proof with `encantado`, plan R-A cognate, reply `**encantado** (a short gloss)`:**

| Step | Result |
|------|--------|
| `introduce_scaffold_evidence` (cognate) | `False` |
| `mark_introduced_if_visible` | `introduce_lapsed:encantado:no_scaffold` |
| scan with `introduce_key=encantado` | `bare=[]`, `scaffold_saved={}` |
| scan **without** `introduce_key` | `scaffold_saved={'encantado':'gloss'}` |
| next bare `encantado` | `bare=['encantado']` → CRITICAL |
| same bare after `mark_first_seen` | `bare=[]` |

Mechanism: `introduce_key` skips the key **entirely** in `scan_unscaffolded_new_items` (no bare, no `scaffold_saved`). Lapse writes nothing. `first_seen` loop never sees the key. Planned-key wrong-scaffold exposure is **invisible** to both ledgers → thrash next turn.

**AMEND — exact replacement** in `tutor/output_gate.py` `scan_unscaffolded_new_items` bare loop:

```python
    bare: list[str] = []
    scaffold_saved: dict[str, str] = {}
    for key in ordered:
        entry = table.get(key) or {}
        if gloss_after_key(key, full_blob):
            scaffold_saved[key] = "gloss"
            if key == introduce_key:
                continue  # planned intro: not bare; still record scaffold
            continue
        if anchor_in_reply(entry, full_blob):
            scaffold_saved[key] = "anchor"
            if key == introduce_key:
                continue
            continue
        if key == introduce_key:
            continue  # planned key bare: gate introduce path owns fault/lapse
        bare.append(key)
```

**AMEND — exact replacement** in `tutor/conv_session.py` first_seen loop:

```python
            for fs_key, fs_kind in saved_map.items():
                if is_introduced(self.sheet, fs_key, "lexicon"):
                    continue
                if has_first_seen(self.sheet, fs_key, "lexicon"):
                    continue
                # Do NOT skip intro_plan.key: if introduce lapsed, first_seen
                # must still stick so glossed exposure is not forgotten.
                self.sheet = mark_first_seen(
                    self.sheet, fs_key, "lexicon", fs_kind
                )
```

(Remove the `if intro_plan is not None and fs_key == intro_plan.key: continue` branch; successful introduce already hits `is_introduced`.)

Test pin: R-A plan + gloss-only reply → `introduce_lapsed` + `first_seen:key` + next bare CLEAN.

---

### (b) Gate coherence — **AMEND**

#### (b1) `blank_zero` / placement wall repair contradicts zero register — **DEFECT**

**Proof:** All-English orientation turn, `blank_zero=True`:  
`ratio=0.125`, `n_alpha=34` (34 ≥ 12; 0.125 < 0.25) → `gate:english_wall`.  
Repair text: **“Rewrite Spanish-forward: most words in Spanish…”**  
while `ZERO_REGISTER_NOTE` requires English orientation + glosses.

Arithmetic: wall fires iff `n_alpha ≥ 12` **and** `ratio < min_ratio`; `min_ratio = 0.25` if placement/blank_zero else `0.50`. Floor is correct; **repair copy is not mode-aware**.

**AMEND — exact replacement** in `check_output_gate` repair assembly:

```python
        if "gate:english_wall" in faults:
            if mode_l == "placement" or blank_zero:
                bits.append(
                    "True-zero / placement register: keep ONE short English "
                    "orientation line and a ≤6-word English gloss on each new "
                    "Spanish item; raise Spanish share above the zero floor "
                    f"({ZERO_MIN_SPANISH_RATIO:.2f}) without an all-English turn "
                    "and without dumping English essays."
                )
            else:
                bits.append(
                    "Rewrite Spanish-forward: most words in Spanish. English only as a short lifeline."
                )
```

#### (b2) Stacked soft+critical repairs — **partially CLEAN, one sharp edge**

- Flood alone (`≥3` bare): soft `gate:unscaffolded_flood` only; not critical — **CLEAN** (formula storm: hola / buenos días / cómo estás / bien / gracias / y tú).  
- `gate:regloss` + flood: repair stacks “introduce at most ONE… with gloss” **and** “Do not re-gloss (hola)” — **compatible** when keys differ.  
- `gate:unscaffolded_new_item` + `gate:probe_loop`: repair stacks “keep ONE with gloss” + “Do NOT re-ask… advance to new ground” — **can** push “new ground” that is also new unscaffolded Spanish in one rewrite. Acceptable as soft+critical guidance **if** (a2) due exemption lands; otherwise document as residual.

No second AMEND beyond (b1)+(a2) unless you want probe_loop repair to say “advance **using already-seen Spanish**”.

#### (b3) Adversarial “satisfy one / violate another”

| Construct | Satisfies | Violates intent |
|-----------|-----------|-----------------|
| Glossed bilingual close under blank_zero | english_wall floor | — (OK) |
| DUE weave of due `casa` as location try | due_elicit / spacing | probe_loop / do_not_re_ask |
| Wrong-scaffold planned intro | introduce_key bare exemption | first_seen / honesty of exposure |
| ≥3 bare formula | flood soft (no rewrite) | still heavy load (by design residual) |

---

### (c) Honesty — **COUNTERSIGN**

| Check | Result |
|-------|--------|
| Retraction voids then re-mints | `has_milestone` False after `record_retraction`, True after second `record_milestone`; raw lines 3, active 1 |
| Debug capture disk I/O | `_capture_debug_request` body: no `open`/`write`/`jsonl`; in-memory `deque(maxlen=10)`; API reads ring only |
| Allowlist | `_write({"confidence":0.5})` → `ValueError`; `mark_first_seen` conf=0.0; `record_outcome_ex` preserves conf 0.55; `retract_introduction` strips schedule fields, keeps conf 0.42 / status emerging / solid_uses 2; `first_seen` not stripped by retract (by design) |

No AMEND on (c). Keep allowlist tests green on any new writers.

---

### (d) Reset path end-to-end — **COUNTERSIGN**

**`ConversationalSession.reset_sheet` (same object):** clears disk sheet, `history`, `pedagogy_memory` (new `SessionMemory`), `mode_state`, **rebuilds** `phase_state`, `task_state=None`, **`debug_requests.clear()`**. Proof: pre-seed `asked_topics`/`covered`/`images`/`introduced`/debug/IP-04=0.7 → post all empty/zero; phase back to `new_input`.

**Web `/api/session/reset` `{reset_sheet:true}` (isolated DEFAULT_SHEET_PATH):** `fresh_learner=True`, `sheet_reset=True`, open is `blank_open_placement` / diagnostic, English true-zero register present, `do_not_re_ask=[]`. Debug `count=1` is the **new** open capture, not a leak from the prior session.

**Combination:** sheet wipe + session replace + phase rebuild + zero register + empty asked registry hold together. No residual defect found in the combined path that produced the D-session class of bugs, provided `reset_sheet=True` (sheet-preserving reset is a different product path).

---

### (e) Performance / never-block-the-reply — **AMEND**

| Path | Status |
|------|--------|
| Focus rail | **CLEAN** — `_schedule_focus_enrich` uses `threading.Thread`; notes include `focus_async` |
| Debug capture | **CLEAN for LLM RTT** — post-model, memory-only; cost is O(history) copy into ring (maxlen 10), not an extra model call |
| Dashboard/notes growth | Acceptable if kept off the model RTT; watch task JSON size (`input_tokens` observed ~24k–25k on open with full sheet+scenes) |
| **Image generate-on-miss** | **DEFECT vs never-block** — hot path still `ensure_asset(concept, generate=may_gen)` **synchronously** before/around reply assembly. Cache hit ~0.4 ms; miss pays full image API latency on the tutor turn |

**AMEND (behavior contract):**

1. Hot path may only `ensure_asset(..., generate=False)` (or cache lookup).  
2. On miss: attach generation-miss visibility (already partially shipped), return reply **without** blocking.  
3. Optional async warm (same pattern as focus thread) with cap already in `MAX_IMAGE_GENERATIONS_PER_SESSION`.  
4. R-B introduce plans that lack a ready asset already downgrade to R-D gloss — keep that; do not block on generate to “save” R-B mid-turn.

If product insists sync generate for R-B only, record **DEBT** in `PEDAGOGY.md` §8: “image generate-on-miss blocks reply” with owner — silent acceptance violates the latency law from commits `2d160e0` / `7275bdc`.

---

### Verdict table

| Area | Ruling | Primary proof |
|------|--------|----------------|
| **(a)** | **AMEND** | introduce ignores session cover/images; due vs probe_loop; introduce_lapse drops first_seen |
| **(b)** | **AMEND** | blank_zero english_wall repair copy; flood soft OK |
| **(c)** | **COUNTERSIGN** | retract/remint, debug memory-only, allowlist airtight |
| **(d)** | **COUNTERSIGN** | reset_sheet + web reset combination holds |
| **(e)** | **AMEND** | focus async OK; **sync image gen** still on hot path |

**Overall:** do **not** close the whole-system audit as clean. Land (a1)(a2)(a4)(b1)(e) before declaring interaction-safe; (c)(d) can countersign as-is.

**Suite claim:** COUNTERSIGN — `526 tests collected in 0.80s` on 2026-07-28.

---

### Suggested fix order (engineering)

1. **(a4)** scan `scaffold_saved` + first_seen on lapse — stops gate thrash.  
2. **(b1)** repair text for blank_zero/placement — stops zero-register rewrite fight.  
3. **(a2)** due keys exempt from topic `probe_loop`.  
4. **(a1)** session exclude in introduce candidates.  
5. **(e)** image gen off hot path (or named DEBT).

I am not applying patches in this countersign round; exact replacements above are ready for the primary author to land and re-verify with the executed proofs as regression tests.

---

## Adjudication — Round 1 (⬛ Claude, 2026-07-28)

All rulings ACCEPTED; no counters. The five defects are exactly the cross-batch seam class the audit was commissioned to find:

1. **(a1) ACCEPT** — introduce router blind to session covered/images; Grok's session-exclusion replacement adopted, INCLUDING its preference: excluded even when a key is explicitly forced (session-local honesty beats caller convenience).
2. **(a2) ACCEPT** — spacing outranks anti-repeat: currently-due keys are exempt from the topic probe_loop (P3 is law; do_not_re_ask is a courtesy). Exact-key matching per the extractor's own key set.
3. **(a4) ACCEPT** — the sharpest catch: a planned introduce with the WRONG scaffold type still exposed the learner to a glossed key, but both ledgers stayed blind → guaranteed critical thrash next turn. Scan records scaffold_saved for the planned key; first_seen sticks on lapse.
4. **(b1) ACCEPT** — the english_wall repair text was not mode-aware: under blank_zero it ordered "rewrite Spanish-forward," re-fighting the zero register the floor exemption had just permitted. Mode-aware repair copy adopted.
5. **(e) ACCEPT, async option** — sync image generate-on-miss on the reply path violates the latency law (commits 2d160e0/7275bdc). Ruling: hot path goes generate=False; misses noted (already shipped) and generation moves to an async warm thread (focus-rail pattern, caps unchanged); R-B keeps its R-D downgrade — never blocks to save a plan. No DEBT needed since the fix ships now.
6. **(c)/(d) COUNTERSIGNED clean** — recorded.

Fix batch dispatched in Grok's suggested order; audit stays OPEN until the executed proofs are re-run green as regression tests.

---

## Audit fix batch landed (agent, 2026-07-28)

All five adjudicated amendments landed in Grok's suggested fix order; the executed proofs were re-run against the amended code as regression tests. No deviations from the adjudicated rulings.

1. **(a4)** `scan_unscaffolded_new_items` now runs the scaffold detectors BEFORE the introduce_key check: a planned key with scaffold evidence records `scaffold_saved` (no bare); a planned key bare is skipped (introduce path owns the lapse). `conv_session` first_seen loop dropped the `intro_plan.key` skip — a lapsed-but-glossed exposure sticks as first_seen (successful introduces already hit `is_introduced`). **Proof re-run (encantado, verbatim):** R-A cognate plan + `**encantado** (a short gloss)` → `introduce_scaffold_evidence=False` → `introduce_lapsed:encantado:no_scaffold` → scan w/ introduce_key: `bare=[]`, `scaffold_saved={'encantado':'gloss'}` → first_seen written → next-turn bare «Encantado.» **CLEAN** (no unscaffolded/flood fault). Pinned in `tests/test_introduce_router.py::TestLapsedIntroFirstSeen` + 2 scan tests in `tests/test_output_gate.py`.
2. **(b1)** `check_output_gate` english_wall repair copy is mode-aware: placement/blank_zero get the zero-register text (keep ONE English orientation line + ≤6-word glosses, raise Spanish above the 0.25 floor); normal register keeps "Rewrite Spanish-forward". **Proof re-run:** all-English fixture under blank_zero → zero-register repair, no Spanish-forward order; plain conversation → Spanish-forward, no zero text. Pinned in `TestEnglishWallZeroExemption::test_wall_repair_copy_is_mode_aware`.
3. **(a2)** Topic-registry probe_loop branch exempts currently-due concepts (`due_items` lookup; ledger keys compared through the same `_deaccent` transform the extractor uses — ledger keys keep accents («café»), extracted concepts are deaccented; exact match otherwise). Exemption notes `probe_loop_due_exempt:<key>`. **Proof re-run:** due `casa` + `location:casa` in asked_topics → NO `gate:probe_loop` (+ exempt note); same turn without due → `gate:probe_loop` fires. Accented-key case (`café` due, `location:cafe` asked) also exempt. Pinned in `TestProbeLoopTopicRegistry` (3 new tests).
4. **(a1)** `candidate_keys`/`plan_introduction` accept the session snapshot's `images_shown ∪ covered_concepts` as an exclusion set — INCLUDING when `key=` is explicitly forced (adjudicated choice: session-local honesty beats caller convenience). Wiring is free: `introduce_block` already passes `pedagogy_memory.snapshot()`. **Proof re-run:** covered+imaged `casa` → not in candidates; `plan_introduction(key="casa")` → `None`; unrelated forced key still plans. Pinned in `TestSessionExclusion` (5 tests).
5. **(e)** Image generation is OFF the reply path (no DEBT — fix shipped): `_attach_mode_image`, the `assets_for_ai_turn` fallback, the tutor-declared path, and the rules-planned `assets_for_plan` path all go `generate=False` (cache-only). Misses stay visible (`image_gen_capped` / `image_gen_disabled` / new `image_gen_async`) and spawn `_schedule_image_warm` — daemon thread mirroring `_schedule_focus_enrich`, in-flight dedupe, `_may_generate_image` caps checked at spawn AND in the worker, costs recorded via the existing `_note_image_costs` path on completion (tutor-declared warms keep `decision_reason="tutor_declared"` so the declared-novel cap accounting holds). The in-flight reply is never touched — the image attaches on a LATER turn via cache hit. R-B→R-D downgrade unchanged and verified compatible: plan + cache miss → downgrade fires as before AND the warm runs so the image exists next time. **Proof re-run:** miss returns [] instantly (slow-generator test asserts no reply-path RTT), warm thread generates into cache with fake generator, cost ledger written, session cap blocks the warm, next attach is a cache hit. Pinned in `TestModeImageAttachVisibility` (5 new/rewritten tests).

**Verification:** `pytest tests/ -q` → **543 passed + 17 subtests** (526 prior + 17 new regression tests), 0 failures. `scripts/check_teacher_truncation.py` → ok (14 files). Server restarted: `/api/health` `stale_code: false`, version `20260728-130830`. (c)/(d) countersigned clean earlier — untouched.

---

## Closure — CONVERGED (⬛ Claude, 2026-07-28)

Grok's closure condition ("land (a1)(a2)(a4)(b1)(e) before declaring interaction-safe") is met: all five amendments landed with the audit's own executed proofs re-run green as regression tests (encantado thrash → CLEAN; due-vs-probe_loop → exempt with note; async warm → reply returns instantly, cache warms, caps hold). (c)/(d) countersigned clean in round 1. 543 tests + 17 subtests; truncation gate ok; live v20260728-130830. One recorded judgment call (retired no-consumer notes → image_gen_async) accepted.

**Audit CLOSED — CONVERGED (1 round + fix verification).** Reopen triggers: any new cross-subsystem wiring lands without an interaction test naming its neighbors, or the architecture refactor (user-directed 2026-07-28, in planning) restructures the seams this audit certified.
