# Full code audit — 2026-08-03 (USER: "we need a full review of our code")

Four parallel read-only auditors (prompt-path / machinery census /
stale+silent / gate+new-tech), synthesized here. Countersign round:
appended below by Grok. Execution tracked per item. Law: ENGINEERING
§4.6 (dead code is deleted, not archived), §1.1 (model is the teacher),
no-hide (2026-08-01/03).

## Verdict summary

The §1.1 strip HELD for the router: no mode/phase/instruction text
reaches any model prompt (verified exhaustively; the SESSION PHASE
strings terminate in the debug ring + rail chrome). But four things that
DO ship violate §1.1/§1.1a, the output gate still enforces the dead
code-owned-teaching contract (9/10 turns still_fail on a healthy
transcript), and the codebase carries ~1,500+ LOC of shadow/dead
machinery plus critical silent-failure sites.

## SLATE

### S1. §1.1 violations still shipping (fix the prompt, delete the source)
- S1a **scenes ship scripts**: open_scene_goals carries model_lines /
  elicit / transfer / tutor_private_info verbatim (scenes.py:217-227 →
  executor.py:263); boat_likes pushes GUSTAR while the stance bans it.
  §1.1a names this class forbidden. → strip scripted fields from the
  hint builder (goals/exit only) or delete scene shipping entirely.
- S1b **next_best ships** inside the sheet + "prefer next_best" note
  (character_sheet.py:784, executor.py:271-272). Code-owned agenda. →
  remove from prompt payload; keep as rail/telemetry if the UI wants it.
- S1c **teach_hint imperatives ship** (catalog "Recast X → Y" commands,
  character_sheet.py:785/1535, 2071-2074). → ship the misconception
  LABEL + example as facts; drop imperative phrasing from the payload.
- S1d **conversational_tutor.md**: 4 scripted <tutor> dialogue exemplars
  + dead pack law ("Unit 5 verb list", "course pack is inventory+…",
  lines 17/90/129-131/170-171). → rewrite: scope law points at the
  sheet's domain_scope; exemplars reduced to SHAPE without full scripted
  dialogues.
- S1e **tutor_persona.md** defers to "MODE instructions" + "pack
  palette" (line 53, 3-5). → fix authorities list.
- S1f **p2_structured FINAL_CONSTRAINTS** dormant script block +
  TEACHER_PROMPT_ORDER arms (executor.py:307-331, config.py:100-104) +
  run_referee.py stale ARMS (incl. B0_brief which now silently
  duplicates the plan arm — fabricated-comparison hazard). → DELETE the
  falsifier arms + referee arm list fixed.

### S2. Dead code — DELETE (§4.6; zero model-path behavior change)
- mode_executor_brief (modes.py:1186-1200, 0 callers)
- corpus.py load_pack + load_pack_planner_index + pack_topic_titles +
  the pack_topics parameter chain + modes._topic_suggestion_line
  (always [] / always raises; tests pin the corpses)
- pedagogy_contract.TEACH_MODALITIES (46 LOC, 0 readers)
- modes._phase_prefix + SESSION PHASE strings + ZERO_REGISTER_NOTE text
  (keep the blank_zero predicate — re-derived at turn_pipeline.py:1206)
- OUTPUT_GATE_REPAIRED event kind (emission site deleted; 3 tests pin)
- turn_pipeline realization_artifact field + dead B0 mirror block
  (:187-190, :1880-1889) + stale stage_prompt_build docstring
- executor dead params: personal_context/sheet_summary system args,
  mode_decision=/observations= task args; double build_ai_tutor_system
  on the round branch
- conv_session.py:394 "course_pack" debug labeller branch (+ its test)
- config: POLICY_PATH, CONTROLLER_PLANNER/EXECUTOR, stale
  LEARNER_PROFILE comment
- 8 orphan prompts/ files: teaching_policy, executor_*, planner_*,
  thin_runtime (git history is the archive)
- GATE_REPAIR_STAGES → rename (no repair exists); _INTEGRITY_HOLD /
  _DEGRADE_OK naming + stale ladder comment (:1161-1163)

### S3. Shadow machinery with ONE live wire — delete text, keep wire
- due_elicit_block text (keep DUE_ELICIT_OFFERED event → frames_seen)
- introduce render text (keep R-B→R-D downgrade + introduce ledger)
- self_flag_uptake text (UPTAKE_FLAGGED event is eval-pinned — keep)
- close_summary text (CLOSE_PHASE_OFFERED in notes projection)
- task_runtime.task_instructions text (keep task_state + ledger write)

### S4. The mode router + gate: coupled verdict
Gate rules keyed on shadow decision.mode (missing_recast,
form_focus_needs_model, comprehension_needs_check, english_wall's
placement arm) are STRUCTURALLY OBSOLETE — the mode is stripped from
the prompt, so the gate demands tags the model was never asked for.
Retiring them kills the router's last live consumer; modes.py then
reduces to whatever routing the image-attach path still needs
(image_concept) or dies entirely with image attach moved to
evidence-based triggers. Execution order: gate first, then router.
- gate:unscaffolded_new_item — structurally obsolete as CRITICAL:
  requires code IntroducePlan for its exempt slot; bare keys re-fault
  forever (bien fired 5×) because only code-planned introduces write
  first_seen. Fix: write first_seen for EVERY table key the tutor
  visibly used; same-turn teach_image counts as scaffold; soft unless
  the model's own <plan> promised an anchored introduce.
- gate:unscaffolded_flood — inverted incentive (≥3 bare → SOFT while
  1-2 bare → CRITICAL). Fold into the same soft advisory.
- gate:probe_loop — retune major: restrict scan to try/continue (model/
  acknowledge roleplay = false positives T2-T4), drop the shown-skill
  permanent ban + seed_from_sheet permanence, fix topic-key derivation
  ("what:te:bote", "location:y tu"). Keep the true-positive class
  (T8/T9 repeated identical try).
- gate:regloss — dead in practice (nothing reaches is_introduced);
  revive only on the first_seen ledger above.
- gate:sheet_leak — minor: tool-name marker needs JSON-ish context.
- KEEP: truncated, pedagogy_contract checks, english_wall (drop the
  placement-mode arm, keep blank_zero floor), cluster veto data.
- evals/student_checks: split still_fail by rule; fix probe_on_known
  mode-name pollution + " o " = quiz assumption; english_wall docstring.

### S5. No-hide gaps (silent failures → _oops/typed events; no behavior
hidden). CRITICAL first:
- executor.py:186 stance→"" and session_plan.py:98 pedagogy→"" (the
  teacher's entire instructions can vanish silently; docstring lies)
- character_sheet.py:574 corrupt sheet → silent blank + overwrite
  (data loss; quarantine the corrupt file + visible error instead)
- character_sheet.py:2286 grade-feed swallow; grade_log.py:34 CWD
  fallback forks the ledger; :110 unreadable→[]
- web_app.py:116/451/583 close() swallows (sheet persist can fail
  silently on every reload); conv_session.py:1817 missed _oops
- costs.py:45 ledger append swallow; progress_ledger.py:1069/1075
  crash→"0 due"/empty score (§3.4 violation)
- teach_assets.py:201 sidecar → permanently empty module global; :763
  generator failures = "declined"; :1024 import-time swallow
- conv_session.py:865 association table → None (add _oops)
- image_gen.py:125 logs "generate_on_miss=on" unconditionally after a
  swallow (lying telemetry)
- scenes.py:130 malformed scene JSON silently skipped; :152/:175
  predicate typo silently changes thresholds
- config.py:203 bad env cap → silent truncate-mode default

### S6. New-tech bugs (mine, this session — fix immediately, no
countersign needed)
- empty <plan></plan> leaks raw to the learner (extract_plan/1114:
  ctx.raw must always take _cleaned)
- replan_requested cleared at prompt-build; a failed model call
  swallows the replan → clear only after success
- plan-turn-without-<plan> silently re-runs full context forever →
  SESSION_PLAN key="missing" event
- the model's plan text is in NO audit trail → stash on ctx; surface in
  debug/traffic entries (parts.plan still says mode_runtime — stale)
- numbers_0_20→numbers_0_100 migration is DEAD (deep_merge seeds the
  new key first) and DESTROYS state → migrate on raw data pre-merge
- _untouched_targets reads the DEFAULT table, ignores session's; does
  not respect in_pack:false while the gate exempts those keys
- traffic log absent under evals (write into sim_log_dir)
- gloss_after_key accepts Spanish parenthetical as a gloss
- GateContext.asked/shown live set refs (copy like asked_topics)

### S7. Grades path
- run_student_smoke clamps SHEET_TOOLS=false + use_tools=False with a
  stale "rules-based sheet update" comment — the smoke structurally
  cannot exercise grading. Flip on + pin GRADE_LOG_PATH in _pin_ledgers
  (pollution hazard = 2026-07-28 incident class).
- conv_session tool_result claims {"ok": true} before validation;
  rejected deltas were told "ok" → report real outcome.
- grade feed silently requires non-empty reason → typed event.
- ai_student max_tokens=768 too small for growing learner_state JSON →
  parse fails from turn ~7, true_ability silently freezes, notes
  triple-counted.

### S8. Docs/briefings
- GROK.md: briefed the reviewer on the DEAD constitution (course packs,
  code-owned engine) — REWRITTEN FIRST, before this doc's countersign.
- README.md front door (course packs, sole-law-home, corpus seam,
  <session_state>) — rewrite.
- docs/system-overview.md: GATE_REPAIR-as-default, pack.md-as-live,
  boredom routing — fix sections 13/gate/affect.
- ~15 stale "PEDAGOGY §N" code citations → ENGINEERING §N (sweep);
  turn_morph.py:8 doubly wrong (cites reversed law as current).
- CLAUDE.md "PEDAGOGY.md wins" line → name both files.
- Log hygiene (USER: "way too many… couldn't tell what was going on"):
  no log files until the first learner turn; date subfolders.

### S9. Open policy questions (USER call, not auditor call)
- focus_enrich.py: 277 LOC + a real grok-3-mini call EVERY turn for
  right-rail chrome only. Keep paying, or delete the rail enrichment?
- scenes: after S1a strips scripts, is goal/exit scene data still
  wanted at all, or do scenes die entirely?
- session-phase machinery + task_runtime (shadow + one ledger write +
  eval pins): delete now or after the eval suite is retooled?
- forced periodic replan: model replanned 0× in 10 turns; plan went
  stale beyond the 12-message window. Nudge, force every N turns, or
  trust ROUND_NOTE?


---

## GROK (Grok Build CLI (1e1687c1cf6a)) - 2026-08-03 17:10 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the audit slate so I can rule each item independently against the code and evidence.The prompt path failed; I'll locate the full request and inlined audit materials in the workspace.I have the full slate and the gate/session_plan sources. Checking one quantitative claim and a couple of gate mechanics before issuing item-by-item verdicts.## Grok countersign — full-code-audit slate (2026-08-03)

Evidence checked: inlined `tutor/output_gate.py`, inlined `tutor/session_plan.py`, slate claims, 9/10 still_fail on evals/results/20260803-104618-student. Law frame: ENGINEERING §1.1 (model teaches; code facts/honesty/audit), §4.6 (dead code deleted), no-hide (2026-08-01/03). Verdicts: **COUNTERSIGN** / **AMEND** (exact text) / **REJECT**. S9 = recommendation only.

---

### S1 — §1.1 violations still shipping

| Item | Verdict | Notes |
|------|---------|--------|
| **S1a** scenes ship scripts | **COUNTERSIGN** | Scripted `model_lines` / elicit / transfer / tutor_private_info into the teacher prompt is exactly the forbidden class (§1.1a). boat_likes pushing GUSTAR against stance is not a side note — it proves code still steers moves. Fix: strip scripts from the prompt path immediately. Residual goals/exit = **S9**, not a soft alternative that delays the strip. |
| **S1b** next_best ships | **COUNTERSIGN** | “Prefer next_best” is a code agenda. Remove from prompt payload; rail/telemetry only. |
| **S1c** teach_hint imperatives | **COUNTERSIGN** | Ship misconception label + example as facts; drop “Recast X → Y” imperatives. |
| **S1d** conversational_tutor.md | **COUNTERSIGN** | Dead pack law + full scripted `<tutor>` dialogues must go. Scope → sheet `domain_scope`; exemplars = shape only. |
| **S1e** tutor_persona.md | **COUNTERSIGN** | Authorities list must not cite MODE instructions or pack palette. |
| **S1f** p2_structured / referee arms | **COUNTERSIGN** | Dormant script blocks + B0_brief silently aliasing plan arm is a fabricated-comparison hazard. DELETE falsifier arms; fix referee arm list. |

---

### S2 — Dead code DELETE (§4.6)

**COUNTERSIGN** the whole delete list and zero-model-path claim class.

**AMEND (execution hygiene, not scope cut):** before merge, run a reference-count / import-graph check so “0 callers” is machine-verified, not auditor memory — especially `modes._phase_prefix`, pack_topics chain, and the 8 orphan prompts. Git history is the archive; no `docs/archive/code/`.

Exact replacement for the S2 header line:

> **S2. Dead code — DELETE (§4.6; zero model-path behavior change).** Delete the listed corpses in one PR after an automated zero-reference check fails closed on any still-live symbol. Tests that pin corpses are deleted or rewritten to assert absence, not behavior of dead APIs. `GATE_REPAIR_STAGES` rename lands in the same PR as doc sweep S8.

---

### S3 — Shadow machinery: delete text, keep wire

**COUNTERSIGN.** Text that only exists to script teaching must die; ledger/event wires that still record facts may stay until S9 retires the subsystem.

**AMEND:** each “keep wire” item must name the single consumer (event → frames_seen / ledger / eval pin). If the only consumer is an eval pin, schedule deletion with the eval retool (S9), not indefinite shadow life.

---

### S4 — Mode router + gate (highest stakes)

**Overall direction: COUNTERSIGN with AMENDs.** Execution order gate-first, then router: **COUNTERSIGN.**

#### Arithmetic (why the gate is structurally obsolete)

1. **Mode-contract rules demand tags the model was never asked for.** Inlined `_check_output_gate`:
   - `gate:missing_recast` if `mode_l in ("cf_recast", "form_focus")` (or `require_recast`)
   - `gate:form_focus_needs_model` if `mode_l == "form_focus"`
   - `gate:comprehension_needs_check` if `mode_l == "comprehension_check"`
   - english_wall / unscaffolded placement exemption if `mode_l == "placement"`

   If mode is shadow-only (stripped from prompts — slate claims this held under audit), these are code-owned contracts against a decision the teacher never received. **Retire mode-keyed contracts.** Keep `require_recast` only if it is derived from learner-evidence (error this turn), not from shadow mode name.

2. **Flood severity is inverted.**  
   `FLOOD_MIN_DISTINCT = 3` (inlined):  
   - bare count \(n \in \{1,2\}\) → **CRITICAL** `gate:unscaffolded_new_item`  
   - bare count \(n \ge 3\) → **SOFT** `gate:unscaffolded_flood`  
   Severity \(S(1)=\text{CRITICAL} > S(3)=\text{SOFT}\). Non-monotonic: dumping more bare keys is rewarded. **Fold bare keys into one soft advisory.**

3. **9/10 still_fail on a “healthy” sibling-check run.**  
   still_fail rate \(= 9/10 = 0.90\). Under no-hide, a gate that still encodes the dead code-owned-teaching contract will fail nearly every turn that (a) hits 1–2 bare table keys without code `introduce_key`, or (b) sits in a shadow mode with a tag contract. That is not a model quality signal; it is gate/constitution drift. **Split still_fail by rule** before trusting student_checks.

#### Per-rule

| Rule | Verdict |
|------|---------|
| Retire missing_recast / form_focus_needs_model / comprehension_needs_check (mode-keyed) | **COUNTERSIGN** |
| english_wall: drop placement-mode arm, keep blank_zero floor + truncated + pedagogy_contract + cluster veto | **COUNTERSIGN** — only if `blank_zero` remains independently computed (slate: turn_pipeline re-derive). Placement must not be the sole true-zero path. |
| unscaffolded_new_item CRITICAL + IntroducePlan exempt | **AMEND** (below) |
| unscaffolded_flood fold into soft | **COUNTERSIGN** |
| probe_loop retune | **COUNTERSIGN** (restrict to try/continue; drop shown-skill permanent ban + seed_from_sheet permanence; fix topic-key derivation). Keep true-positive class (identical try re-ask). |
| regloss revive on first_seen ledger | **COUNTERSIGN** |
| sheet_leak JSON-ish context | **COUNTERSIGN** |
| student_checks split + probe_on_known / “ o ” / english_wall docstring | **COUNTERSIGN** |
| Then delete/shrink modes.py | **AMEND** (below) |

**AMEND — replace the slate’s unscaffolded_new_item fix paragraph with:**

> **gate:unscaffolded_new_item / flood:** Structurally obsolete as CRITICAL under §1.1 — the exempt slot requires a code `IntroducePlan` (`introduce_key`), and only code-planned introduces reliably write `first_seen`, so bare keys re-fault forever (e.g. «bien» 5×). **Fix:** (1) Write `first_seen` for every association-table key the tutor visibly used this turn (scaffold optional for the ledger write; same-turn teach_image counts as scaffold). (2) Bare unscaffolded keys → **SOFT advisory only** (merge flood into the same soft path; delete the inverted ≥3 soften). (3) **KEEP CRITICAL only for same-theme cluster extras** (near-synonym interference — real constraint, not mode theater). (4) **Do not parse free-text `<plan>` for “promised an anchored introduce.”** That re-implements code-owned teaching judgment over unstructured prose and will thrash. If a hard introduce contract is needed later, require a structured tag the model emits (e.g. `<introduce key="…"/>`), not NLP over the plan.

**AMEND — router teardown sequencing:**

> After mode-keyed gate rules are retired, delete shadow mode text and the mode router’s teaching decisions. **Do not delete the image-attach path until a replacement is wired** (evidence-based trigger: tutor-declared image / table key with asset / explicit teach_image). Until then, keep the minimum image_concept wire or document images as off. No silent loss of image attach.

---

### S5 — No-hide gaps

**COUNTERSIGN** the CRITICAL-first list.

Call-out on inlined `load_pedagogy`: OSError → `""` is **not** no-hide-compliant if nothing surfaces a typed note. Docstring’s “visible because the guide is simply missing” fails ENGINEERING no-hide — absence without `_oops`/typed event is silent degradation of the teacher’s entire rule set. Same class: stance → `""` at executor.

---

### S6 — New-tech bugs (sanity-check)

| Bug | Verdict |
|-----|---------|
| empty `<plan></plan>` / always use cleaned raw | **COUNTERSIGN** — `extract_plan` strips tags even when plan body is empty (`strip() or None`); leak is at the call site if `ctx.raw` keeps pre-clean text. Always assign cleaned. |
| replan flag clear only after successful model call | **COUNTERSIGN** |
| plan-turn without `<plan>` → SESSION_PLAN missing event | **COUNTERSIGN** — **AMEND add:** after 2 consecutive plan turns with no `<plan>`, surface a visible internal note; do not silently burn full-context forever without telemetry. |
| plan text in audit trail | **COUNTERSIGN** |
| numbers_0_20→0_100 migrate pre-merge on raw | **COUNTERSIGN** — deep_merge seeding the new key first makes migration dead and can destroy state; pre-merge on raw is the correct direction. |
| `_untouched_targets` default table / `in_pack:false` | **COUNTERSIGN** |
| traffic log under evals | **COUNTERSIGN** |
| gloss_after_key Spanish parenthetical | **COUNTERSIGN** — inlined detector accepts any ≤6-token parenthetical; needs non-ES / gloss-language check. |
| GateContext asked/shown live refs | **AMEND** — inlined `_check_output_gate` already does `asked = set(already_asked or [])` / `shown = set(...)` (copies). Confirm a real mutation bug at construction or a different field before “fixing” a non-bug. If the defect is elsewhere (e.g. session mutates the same set mid-repair loop before the copy), state that site. Defensive copy at `GateContext` build remains cheap hygiene. |

---

### S7 — Grades path

**COUNTERSIGN** all four: smoke must exercise grading (SHEET_TOOLS on + pinned GRADE_LOG_PATH); tool_result must not claim `ok: true` pre-validation; empty grade reason → typed event; ai_student `max_tokens=768` too small (parse fail ~turn 7 freezes true_ability) — raise ceiling and pin.

---

### S8 — Docs/briefings

**COUNTERSIGN.** GROK.md rewrite-first was correct (commit e3a4fc4). README / system-overview / PEDAGOGY§→ENGINEERING§ sweep / CLAUDE.md dual law homes / log hygiene (no logs until first learner turn; date subfolders): all **COUNTERSIGN**.

---

### S9 — Open policy (recommendation only, not rulings)

| Question | Recommendation |
|----------|----------------|
| **focus_enrich.py** (277 LOC + grok-3-mini every turn for right-rail chrome) | **Delete or make on-demand.** Paying a model call every turn for non-teaching chrome adds cost, latency, and silent-failure surface for zero learner-facing pedagogy. Default: delete; if UI wants enrichment, trigger on rail open, not every turn. |
| **scenes after S1a** | **Delete scenes entirely** until an eval shows goal/exit data improves outcomes without reintroducing scripts. Goal/exit without scripts is still code-selected steering (which scene fires). Thin residual data is not worth the machinery. |
| **session-phase + task_runtime** | **Delete in the same milestone as eval retool**, not “after someday.” Shadow + one ledger write + eval pins is exactly the class that drifts forever. One PR: update pins → delete. |
| **forced periodic replan** | **Soft nudge, not blind trust, not full-pedagogy force every N.** Evidence: 0/10 model-initiated `<replan/>` in the 10-turn run. `ROUND_HISTORY_MESSAGES = 12` ⇒ 6 exchanges of window; a 10-exchange session drops \(20-12=8\) messages. Plan can reference world that left the window. Recommend: every 6 ROUND turns append a short note “history window advanced; revise plan or emit `<replan/>` if needed” — do **not** auto-inject full PEDAGOGY every N (cost + trains the model to ignore ROUND_NOTE). Force full replan only on `<replan/>`, missing plan, or explicit out-of-plan learner steer detected by the model. |

---

### Blockers before “slate is final”

1. **S4 AMEND** on unscaffolded (no plan-NLP; soft bare; CRITICAL cluster only; first_seen for every visible key).  
2. **S4 AMEND** on image-attach sequencing before router death.  
3. **S6** GateContext copy — verify real bug site.  
4. **S9** USER picks on scenes / focus_enrich / phase machinery / replan policy.

### Ready to execute without further debate (if AMENDs accepted)

S1a–S1f, S2 (with refcheck), S3, S5, S7, S8, S6 (except GateContext pending verify), and S4 mode-contract retirement + flood fold + probe_loop retune + regloss-on-first_seen + student_checks split.

---

**Summary scorecard:** COUNTERSIGN dominant on S1–S3, S5, S7–S8; S4 COUNTERSIGN direction with two binding AMENDs; S6 mostly COUNTERSIGN + one hygiene AMEND; S9 four recommendations (delete focus_enrich; delete scenes; delete phase/task with eval retool; soft replan nudge every 6 rounds). No full-item REJECT. Highest-stakes failure mode confirmed in source: mode-keyed gate contracts + inverted flood + IntroducePlan-gated first_seen explain a ~90% still_fail rate on an otherwise healthy transcript — fix the gate constitution before trusting tutor grades.

---

## CLAUDE — adjudication of the countersign (2026-08-03)

Zero REJECTs. All four binding AMENDs ACCEPTED:

1. **S4 unscaffolded rework** — accepted verbatim: first_seen for every
   visibly-used table key; bare keys = SOFT advisory (flood folded in);
   CRITICAL retained ONLY for same-theme cluster extras; NO free-text
   plan parsing (a structured <introduce key=""/> tag if a hard contract
   is ever needed). Grok's plan-NLP warning is right — parsing prose for
   promises re-creates code-owned judgment.
2. **S4 image-attach sequencing** — accepted: router teaching decisions
   die first; the image_concept wire survives until an evidence-based
   trigger replaces it. No silent loss of image attach.
3. **S6 GateContext** — Grok's challenge VERIFIED CORRECT: the gate
   copies at output_gate.py:600-601 (`asked = set(already_asked or [])`)
   before any use; audit D's finding is a NON-BUG. No change shipped
   (a second copy would be redundancy, §4.6 spirit).
4. **S2 refcheck** — accepted: deletions land only after an automated
   zero-reference check (grep-based import/symbol scan) fails closed.
   Plus S6 plan-missing addendum accepted: 2 consecutive plan-less plan
   turns escalate to a visible internal note.

S9 goes to the USER (4 recommendations relayed: delete focus_enrich or
on-demand; delete scenes entirely; delete phase+task in the same PR as
the eval retool; soft replan nudge every 6 round turns).

Execution begins with the ready-to-execute set (S1, S2+refcheck, S3,
S5, S6 remainder, S7, S8, S4 per AMENDs), each phase suite-green.
Shipped pre-countersign (already green): S6 empty-plan leak, replan
preserve-on-failure, session_plan:missing event, numbers-migration
state carry, _untouched_targets session-table threading, profile-unlink
_oops, stance/pedagogy load failures now shout on stderr.

---

## S10 (added post-countersign — USER-flagged smell, 2026-08-03)

**"The sheet is being built at runtime instead of being the source of
truth?"** Confirmed: only vocabulary targets live as data
(association_table.json); grammar forms + paradigms (can_dos.py
FORM_INVENTORY/MORPHOLOGY_BY_FORM), can-dos (CAN_DOS), scope
(DOMAIN_SCOPE), and the misconception catalog (ERROR_PATTERN_CATALOG)
are code literals. Content-as-code = the §1.1 category error one layer
down.

**Ruling:** consolidate the ENTIRE domain model into
`domain/spanish_a1/` as one reviewable dataset; `default_sheet()` loads
it and attaches zeroed learner state; code keeps mechanics only
(transitions, thresholds, grading, formatting). A new level = a new
data dir, zero code edits.

**Sequencing:** executes AFTER S1/S2/S4 deletions — scenes die, the
mode router and its detect regexes die; consolidate only what survives.
The generated preview (logs/base_character_sheet.json) is a stopgap;
the dataset itself becomes the inspectable artifact.

**S9 replan ruling (USER-adjudicated same session):** build NOTHING —
no nudge, no forced replan. No observed failure; the sheet + window +
session_facts re-feed the learner's world every turn and <replan/> is
documented in every round note. Revive condition: a live transcript
showing the tutor contradicting its own plan or losing post-window
context (the traffic log now captures the evidence needed to prove it).

---

## EXECUTION — S4 gate retune + mode-router teardown (chunk 2, 2026-08-03)

Per the accepted AMENDs, both parts landed in one working set (suite
691 passed; truncation gate ok):

**Gate retune (tutor/output_gate.py):** mode-keyed contracts DELETED
(gate:missing_recast + require_recast, gate:form_focus_needs_model,
gate:comprehension_needs_check, mode:association_no_image_cache,
english_wall placement arm — blank_zero floor kept, re-derived in
stage_gate_context).  unscaffolded rework per AMEND verbatim:
scaffold_saved is now the EXPOSURE map — every visibly-used
not-yet-introduced key → first_seen (kinds gloss/anchor/image/bare;
same-turn teach image = scaffold); bare keys = ONE SOFT
gate:unscaffolded_new_item; gate:unscaffolded_flood + FLOOD_MIN_DISTINCT
DELETED; CRITICAL survives only as gate:cluster_veto (new fault id — the
old shared name could not carry two severities).  probe_loop: scan = try
+ continue ONLY; shown-skill ban + seed_from_sheet asked-permanence
DELETED; asked-registry + topic-registry true-positive classes kept.
topic-key fixes: qué-clitic skip (what:te→what:gusta) +
SOCIAL_FORMULA_THEMES excluded from the topic palette (location:y tu).
sheet_leak: update_character_sheet counts only in JSON-/call-ish context.
No plan-NLP anywhere.  evals/student_checks: still_fail split by rule
(HARD = cluster_veto/truncated/pedagogy), mem-key mode-name filter, \bo\b
quiz assumption deleted, english_wall docstring fixed.

**Router teardown:** tutor/modes.py DELETED (git is the archive).  Died
with it: ModeSessionState (+ SessionState field/persistence/reset rows),
last_mode_decision, stage_select_mode/guard6/english_streak/mode_image/
mode_snapshot/mode_record, the contributor family (flavorable/
append_instruction/InstructionContributor), MODE/MODE_REASON/HARD_BREAK
event kinds, parts.mode/mode_decision, the UI mode badge + mode labels
(app.js; ?v= bumped), debug-entry shadow fields + the traffic-log
router_shadow_NOT_SENT pop-list, focus-rail live-mode overlay
(build_focus_panel is a sheet projection), classifier-shadow
routed_mode/disagree fields, conv-smoke seed_mode_state/mode_sets/
mode-keyed checkers.  SURVIVING WIRES (Grok AMEND — no silent loss):
introduce planner runs every turn as pure shadow (stage_introduce_plan;
mode/reason flavor gate gone), R-B image attach via stage_intro_image →
_attach_concept_image, R-B→R-D downgrade (stage_introduce_render, no
instruction render), declared-image path, blank-open fallback image
(known opens ship none, as before), error-resolve→enqueue
(stage_resolve_enqueue), UPTAKE_FLAGGED re-keyed to
turn_pipeline.stage_uptake_flag over observe.detect_self_flagged_token
(instruction path + ModeSessionState budget deleted — observation needs
no pacing; uptake_flag_honored eval pin intact).  ERROR_PATTERN_CATALOG
detect/resolve lists STAY (live consumers: _record_due_outcomes +
resolve-enqueue).  Goldens regenerated (CHAR_GOLDEN_UPDATE=1);
golden_english_streak deleted with its class; declared behavior deltas:
introduce may now plan/mark on ANY turn incl. blank opens, uptake budget
gone, gate scan runs on open turns (no placement exemption).

---

## S11 (USER-ruled 2026-08-03, post-chunk-2): the gate shrinks to plumbing

USER: "We create a really awesome character sheet. That with prompts
creates a good AI teacher… [the cluster rule] goes into the pedagogy.
It is something we can have test cases for to see if our pedagogy +
prompts seems to be working. Why are you making gates for this?"

**Ruling:** runtime teaching-judgment is a relic of the code-is-teacher
era — deleted, not demoted (§4.6). The output gate keeps ONLY plumbing
checks code can actually judge: gate:truncated (provider cut the reply)
and gate:sheet_leak (internal JSON/tool talk in learner text). Every
teaching-opinion check — cluster_veto, probe_loop, english_wall,
pedagogy:no_teach_move / open_needs_model_try, unscaffolded_new_item,
regloss — leaves the runtime entirely and lives ONLY as eval test
cases over AI-student transcripts (student_checks + blind rubric),
judging whether pedagogy + prompts are working. The teaching rules
themselves stay in PEDAGOGY §2 unchanged (the model still receives
them). first_seen exposure bookkeeping survives (it is record-keeping,
not judgment). ENGINEERING §6 gate contract + §9 rows amended with the
execution chunk. Supersedes the S4 retune's remaining teaching-opinion
criticals (the retune was the right direction; this is the destination).


## EXECUTION — prompt purge + dead-code sweep + S3 remainder (chunk 3, 2026-08-03)

Suite 689 passed; `scripts/check_teacher_truncation.py` ok. Goldens
byte-stable (no regeneration needed — they pin notes/sheet state, never
the prompt payload). Zero-ref grep before every cut; every deleted API's
tests deleted or turned into absence pins. NOT COMMITTED (this chunk).

**S1b** next_best OUT of the model payload: format_sheet_for_prompt drops
the key (sheet FILE keeps it — UI rail/telemetry); executor sheet notes
lose "prefer next_best"; AI_TUTOR_SYSTEM rule 8 (next_best guide)
deleted, list renumbered.  conftest assert_full_teacher_context now
asserts next_best ABSENT + teach_hint ABSENT from every shipped sheet
block (flipped from asserting present).
**S1c** teach_hint imperatives stripped from the model projection
(active_error_focus + error_patterns entries); catalog "source" (pack
M-ID provenance) added to active_error_focus as a FACT; the catalog +
sheet file keep teach_hint for UI/telemetry.
**S1d** prompts/conversational_tutor.md rewritten: the 4 scripted <tutor>
dialogue exemplars DELETED (the required-shape block with "…"
placeholders is the one skeleton, now marked SHAPE-only); "Curriculum
palette" section + pack law DELETED → new "Scope" section (authority =
the sheet's domain_scope); every pack/next_best reference replaced with
sheet facts (active_error_focus, domain_targets_not_yet_touched);
teaching-method prose kept.
**S1e** prompts/tutor_persona.md authorities fixed (header + hard rules:
teaching guide, sheet domain scope, output gate; "MODE"/"pack palette"
gone); variety rule now cites the course default, not "pack law".
**S1f** TEACHER_PROMPT_ORDER falsifier arms DELETED: config selector +
executor p1_reorder/p2_structured branches incl.
FINAL_CONSTRAINTS_check_before_replying (no tests pinned them).
evals/run_referee.py: ARMS reduced to the single live plan arm; module
docstring marked RETIRED pending a new pre-registration (the old arm list
would have run four copies of one config — fabricated-comparison hazard);
manifest preregistration=None; driver mechanics kept.

**S2** tutor/corpus.py DELETED (load_pack/planner_index/pack_topic_titles,
zero refs; truncation script's TEACHER_PATHS row + load_pack pattern
removed, named-constant history pattern intact; TestPackTopics deleted).
pedagogy_contract.TEACH_MODALITIES DELETED (+ absence pin).
OUTPUT_GATE_REPAIRED kind + catalog row + render row DELETED; catalog
59 (docstring counts corrected to measured: eval-pinned 9, ui-pinned 2,
log-only 48); conv_checks._GATE_EVENT_KINDS now five; tests replaced
with kind-absence pins (test_turn_events, test_gate_floor).
turn_pipeline: realization_artifact field + dead B0 debug-mirror block
DELETED; stage_prompt_build docstring B0 paragraph rewritten;
GATE_REPAIR_STAGES → GATE_AUDIT_STAGES + stage_gate_repair alias DELETED
(conv_session calls stage_gate_verdict directly; absence pins added);
duplicate build_ai_tutor_system on the ROUND branch removed (build once,
reuse).  executor dead params DELETED: build_ai_tutor_system
sheet_summary/personal_context (system = static stance+persona only),
build_ai_tutor_user_message observations= + personal_context/
learner_personal_context row (test_persona/test_asked_topics/
test_plan_card updated).  conv_session "course pack palette"→course_pack
debug labeller branch DELETED (+ test fixture now stance/persona(cached)/
plan-extra).  config: POLICY_PATH, CONTROLLER_PLANNER/EXECUTOR,
GATE_REPAIR stub DELETED (incl. conftest monkeypatch); LEARNER_PROFILE
comment fixed (capture disabled; path exists solely for legacy-file
deletion).  9 orphan prompts/ files DELETED (teaching_policy,
executor_controller/law_core/reply_protocol, planner_controller/_brief/
structured/wrapper, thin_runtime) — prompts/ = conversational_tutor +
tutor_persona + ai_student, exactly the three with loaders.

**S3 remainder** introduce_router.plan_instructions DELETED (zero
production callers; plan/downgrade/ledger wires untouched; tests →
absence pin).  The S2 "stale ladder comment" (:1161-1163) was already
rewritten by chunk 2's gate retune (the still_fail-floor text now states
the no-hide reality) — verified, nothing to do.

## EXECUTION — S11: the gate shrinks to plumbing (chunk 4, 2026-08-03)

Suite 682 passed; `scripts/check_teacher_truncation.py` ok.  Zero-ref grep
before every cut, fails closed.  NOT COMMITTED (this chunk).

**tutor/output_gate.py** reduced to plumbing: gate:truncated +
gate:sheet_leak (with chunk 2's JSON-context tool-name rule) are the
ENTIRE fault vocabulary.  The first-exposure scan survives as bookkeeping
only — `scan_first_exposures` (renamed from scan_unscaffolded_new_items)
returns the scaffold_saved exposure map and nothing else; gloss_after_key /
anchor_in_reply stay (shared with conv_session.introduce_scaffold_evidence);
stage_first_seen verified working end-to-end.  DELETED: cluster veto,
probe_loop machinery (_PROBE_PATTERNS, detect_tutor_probe_keys, asked/
asked_topics/topic_nouns reads, due-exemption incl. the gate's fold_lexical
binding), english_wall (lexicons, ratios, sandwich exempt, blank_zero
floor), the evaluate_turn call, regloss, all unscaffolded fault emission
(clean removal — no residual note; the exposure flow never needed one).
OutputGateResult loses spanish_ratio; GateContext is 8 fields (is_open /
already_asked / introduce_key / retrieval_failed_keys / blank_zero /
asked_topics / topic_nouns GONE — zero-ref'd each: asked_topics still feeds
executor do_not_re_ask; the registries themselves are untouched).

**tutor/pedagogy_contract.py**: the judgment half DELETED — evaluate_turn,
check_tutor_parts, check_visible_fallback, PedagogyCheck, CONTRACT_VERSION,
the KEY_/VIOLATION_/NOTE_ judgment constants.  KEPT: is_blank_learner /
open_phase (turn_pipeline blank detection + observe), has_teach_move
(ai_student transcript stats), KEY_DIAGNOSTIC_OPEN / KEY_KNOWN_LEARNER_OPEN
(tail phase note).  ZERO-REF CORRECTION (recorded, not guessed): the chunk
brief said "evaluate_turn's only consumer was the gate" — FALSE; a second
consumer lived in conv_session._finish ("Durable pedagogy contract
(code-enforced)": PEDAGOGY event emission + parts["pedagogy"]).  The S11
ruling text ("pedagogy:no_teach_move / open_needs_model_try … leaves the
runtime ENTIRELY") covers that site unambiguously — both consumers deleted,
along with the _log_turn_result pedagogy rows.  The PEDAGOGY event kind
SURVIVES (the tail phase note is bookkeeping); its historical judgment
payloads still classify for replay.

**turn_pipeline**: GATE_CRITICAL_FAULTS = GATE_SHIP_BAN_FAULTS =
{gate:truncated, gate:sheet_leak}.  stage_gate_verdict loses the soft
branch (every remaining fault is critical) — OUTPUT_GATE_SOFT_FAIL kind
DELETED (member, catalog row, render, parse; catalog 59→58, eval-pinned
9→8; absence pins in test_turn_events + test_gate_floor).  The no-hide
surface is UNCHANGED for the two plumbing faults (OUTPUT_GATE_FAIL +
STILL_FAIL + gate_fail banner + raw ships — re-pinned live in
test_gate_floor via a sheet-leak reply and a max_tokens stop).

**evals/student_checks.py** is the teaching-opinion home now (severity
ledger in the file header): check_cluster_intro (HARD; per PEDAGOGY §2.2;
exempt_qa_pairs=False default — the Q&A-formula-pair question is UNRESOLVED
policy, flagged in-code against this stamp), check_probe_repeat (WARN;
chunk-2 retune preserved: try/continue parts only, social regexes + the
session_memory topic-key extractor; due-exemption impossible transcript-side
→ advisory), check_english_wall (WARN; lexicons + ratio + sandwich exempt
MOVED here from the gate; row 0 uses the true-zero floor),
check_teach_shape (no_teach_move + open-model/try HARD on structured rows,
recast_without_try WARN), check_exposure_advisories (WARN bare/regloss).
HARD_STILL_FAIL_FAULTS = {gate:truncated} (chunk-2's HARD set minus the
deleted runtime faults).  Harness verified sufficient: ai_student transcript
rows already carry parts per turn — no capture extension needed.
run_student_checks gains table= (tests inject a synthetic table; smoke uses
the real domain table).  conv_checks: zero-ref _GATE_EVENT_KINDS/
_GATE_FAIL_EVENT_KINDS DELETED; open_english_orientation imports the ratio
from student_checks.

**ENGINEERING.md**: §6 item 6 amended in place (plumbing auditor; teaching
checks live in evals; supersession noted, history kept); §9 rows for §2.2
naked items, §2.3 walls/regloss, §6 no-hide gate re-pointed at the eval
checks with dated amendment markers.

**web UI**: NO changes — the GATE FAIL banner (app.js) is fault-id-agnostic
(joins whatever fault list arrives); no deleted-fault-specific UI text
existed; no ?v= bump needed (§4.4 not triggered).

**Goldens** regenerated (CHAR_GOLDEN_UPDATE=1), deltas: every golden loses
`pedagogy:ok` (note + "pedagogy" parts_key); golden_gate_repair_turn (file
name kept, scenario re-pinned as "bare exposure is bookkeeping, not a
fault") flips gate.ok true / faults [] / gate_fail false and loses
output_gate_fail:/soft_fail:gate:unscaffolded_new_item + the gate_fail/
gate_faults parts_keys; first_seen:hola + first_seen:mucho gusto UNCHANGED
(exposure bookkeeping intact).  No other note families moved.

**Tests**: test_output_gate rewritten (plumbing surface + exposure-scan
suite + absence pins for every deleted fault id/helper + field censuses);
test_gate_floor re-pinned (2-fault critical set, leak/truncation no-hide,
soft-fail-kind absence); test_pedagogy_contract reduced to the surviving
half + judgment absence pins (+ conv_session source pin, comment-stripped);
test_turn_events counts/sets/round-trip updated, gate-context spy test
replaced by a no-teaching-fields pin; test_student_checks extended for the
five migrated checks; test_introduce_router lapse test moved to
scan_first_exposures; test_debug_requests fixture vocabulary modernized;
test_textnorm_contract gate-binding row updated (fold_lexical left the gate
with its last consumer).  CLOSE_REPLY orphan fixture deleted.

Out of scope, noted: evals/run_referee.py (RETIRED, chunk 3) still counts
"english_wall" note substrings — reads 0 on new transcripts; §8 debt rows
ZERO-FLOOD SEVERITY / STORM RESIDUAL cite gate-severity remedies that S11
makes unconstitutional — flagged for the next debt-registry pass, not
edited here (chunk brief scoped ENGINEERING changes to §6 + §9).

## EXECUTION — S5 no-hide + S7 grades path/harness (chunk 5, 2026-08-03)

Suite 701 passed; `scripts/check_teacher_truncation.py` ok.  NOT COMMITTED.
Visibility only — no behavior hidden, no teaching turn made killable.

**S5.1** load_sheet corrupt branch: QUARANTINE (rename to
`<name>.corrupt-<stamp>` before the next save can overwrite the evidence)
+ `[no-hide]` stderr + default_sheet(); regression tests incl.
save-after-quarantine leaves the evidence untouched.
**S5.2** grade-feed swallow: never-break kept, `[no-hide] grade_log write
failed` stderr; ability-move-without-reason now mints typed note
`why=grade_unrecorded:no_reason` (SHEET_WHY kind — no new event kind;
tripwire, unreachable via well-formed deltas today).
**S5.3** grade_log CWD fallback + unreadable-ledger→[] shout on stderr.
GRADE_LOG_PATH env honor pre-existed (line 26) — verified + test-pinned,
not re-added.
**S5.4** web_app three close swallows (_close_meta / session_start fresh
branch / reset path): `[no-hide] session close failed (sheet may be
unpersisted)` + traceback.  (The session_start sheet-re-read swallow is
NOT in the slate — untouched.)
**S5.5** costs record_event append swallow shouts (spend UNTRACKED);
COST_PRICING_JSON parse failure shouts ONCE per process (_pricing runs
per priced call — a once-flag, still never silent).
**S5.6** progress_ledger crash sites report UNCHECKED per §3.4: due_soon
→ None (not 0), score → None (not {}), + stderr.  Verified consumer-safe:
/api/progress serves grade_log.build_grades_payload; app.js reads only
counts/grades/empty — build_progress_payload has zero production readers
(tests only), so None renders as absent, no "unchecked" sibling needed.
**S5.7** teach_assets: sidecar load failure no longer caches the
permanent module-global empty — degrade-to-{} per call, retry next call,
stderr each failed attempt (test updated to pin overlay stays None);
generator crash no longer reads as "declined" (stderr with exception);
import-time seed swallow + cache-index corrupt/save swallows shout.
**S5.8** conv_session association-table load → _oops("association_
table.load", e), None fallback kept.
**S5.9** image_gen: "generate_on_miss=on" logged ONLY when the flag set
succeeded; failure path prints `[no-hide]` and returns False.
**S5.10** config._prompt_cap ValueError shouts (names env var + which
fallback engaged).  providers tool-call args dropping to {} shout via
_warn_tool_args_dropped (both tool_calls + legacy function_call arms,
JSON-fail and non-object cases — a malformed grade is now visible).
scenes.py sites confirmed GONE; session_log._jsonable left (accepted).

**S7.11** run_student_smoke: SHEET_TOOLS→"true" (setdefault — operator
override preserved), use_tools=True (stale "rules-based" comment
corrected; that path died 2026-07-31 — the smoke can now actually
grade); _pin_ledgers pins GRADE_LOG_PATH to `<stamp>/sheet_grades.jsonl`
(honored by default_grade_log_path env read — zero ConvSession
plumbing); isolation doc/summary rows updated.
**S7.12** tutor_turn tool_result: `{"ok": true, "applied": …}` →
`{"received": true, "tool": …}` + harness text "received for review"
(grade_why_ok validation runs later in process_turn; a to-be-rejected
delta is no longer told ok).  Break-out-of-loop kept, test-pinned.
**S7.13** _finish double gate: session.use_tools stays the discard
authority, but a non-None delta discarded by mismatch now raises→_oops
("tool_delta_gate_mismatch") → INTERNAL_ERROR event + turn note, and
TurnResult.tool_delta reports the DISCARD (None), not the phantom delta.
**S7.14** ai_student max_tokens 768→2048 (state JSON stopped fitting
~turn 7 → silent true_ability freeze); parse-failure notes de-triple-
counted (merge_learner_state mints the single `state_parse_failed`;
respond() duplicate + sim-loop `parse_miss` alias deleted);
`true_ability_frozen` minted once per freeze episode (reset on the next
successful parse); run_simulation docstring un-stale'd ("use_tools=False
FREEZES ability"); conv_session logger meta "rules"→"frozen".

**Tests** (+19): tests/test_ai_student.py NEW (single-note pins, freeze
episodes, max_tokens=2048 behavioral pin, smoke-clamp source pins);
test_character_sheet quarantine ×3 + grade-feed visibility ×3;
test_grade_log GRADE_LOG_PATH env ×3; test_progress_ledger UNCHECKED ×3;
test_providers_tools honest-tool_result; test_inventory_coverage sidecar
test extended to pin no-cache-failure + [no-hide].

## EXECUTION — S10: the domain model becomes DATA (chunk 7, FINAL, 2026-08-03)

Suite 732 passed; `scripts/check_teacher_truncation.py` ok.  Goldens
byte-stable (content-identical migration — nothing regenerated).  NOT
COMMITTED (this chunk).

**domain/spanish_a1/ is now the complete single source of truth** for the
level slice.  Four new data files, GENERATED from the live literals (the
byte-identical guarantee — no hand transcription), then verified equal:
`can_dos.json` (sections: can_dos / can_do_themes / morphology_by_can_do /
stretch_activities), `grammar_forms.json` (FORM_INVENTORY flat-merged with
each form's MORPHOLOGY_BY_FORM entry — one record per form id, field names
never collide; the loader splits them back), `domain_scope.json`
(verbatim), `misconceptions.json` (ERROR_PATTERN_CATALOG with detect
(pattern, note) tuples as 2-element arrays; entries without pack "source"
keep no key).  Plus `domain/spanish_a1/README.md` (this dir IS the domain
model; edits change teaching, no code edit).

**tutor/domain_data.py** NEW — the one validating loader (association_table
pattern): reads + validates all four files, raises ONE ValueError listing
ALL problems (schema, cross-refs: misconception form_id→grammar_forms,
supports/can_dos refs/form_hooks→can_dos, theme routed to at most one
can-do, duplicate source, partial morphology, required stretch fallback),
compiles every detect/resolve regex at load (re.I; a non-compiling pattern
is malformed data).  `cached_default_domain()` module-level cache;
consuming modules bind at import, so a missing/corrupt domain file is a
STARTUP error (import fails loudly), never a silent default.  `load_domain
(pack_dir)` is the session-capable entry exactly like
load_association_table — recorded: NO production caller passes a custom
pack_dir today (smokes/conftest pass DEFAULT_PACK_DIR), so no dead
per-session domain plumbing was added (§4.6).

**tutor/can_dos.py** literals DELETED (CAN_DOS, CAN_DO_THEMES,
FORM_INVENTORY, MORPHOLOGY_BY_FORM, MORPHOLOGY_BY_CANDO,
STRETCH_ACTIVITIES); public names re-bound from the loader (zero consumer
churn); THEME_TO_CAN_DO stays the derived inversion.  KEPT IN CODE (calls
recorded): LEGACY_SKILL_TO_CANDO — it maps this codebase's own pre-can-do
key names (migration machinery, not domain content); mechanics
(default_*_entry/blocks, morphology_blocks_*, build_focus_panel,
migrate_skills) unchanged.

**tutor/character_sheet.py** DOMAIN_SCOPE + ERROR_PATTERN_CATALOG literals
(+ the _mined helper) DELETED → loader binds; detect_error_pattern_hits /
detect_error_pattern_resolves now iterate the load-compiled patterns (same
catalog order, same folded-then-raw case-insensitive match — behavior
pinned identical).  KEPT IN CODE: ERROR_PATTERN_ALIASES +
normalize_error_pattern_id fuzz rules (tool-id normalization machinery);
_GRAMMAR_COVERAGE / DEFAULT_COVERAGE noted as adjacent content-in-code
OUTSIDE the S10 ruling — flagged here, not moved.

**logs/base_character_sheet.json** (stopgap preview) deleted, not
regenerated — the datasets are the inspectable artifacts.

**Migration discipline:** generator dumped the JSON FROM the literals and a
reference snapshot; post-rewire verification diffed every loaded symbol
against the snapshot (all equal, order preserved, tuples restored) before
the literals were considered gone.  The equality check survives as
tests/test_domain_data.py TestLoadedSymbolsEqualJson — loaded symbols ==
JSON content per the documented mapping, forever.

**tests/test_domain_data.py** NEW (18 tests): files parse; loaded symbols
equal JSON (incl. detect-tuple + themes-tuple shape and catalog order);
compiled-at-load census; cross-refs (form_id/can_do/form_hooks/source
unique/CAN_DO_THEMES themes exist in the association table/scope lists
disjoint+deduped); malformed-data-raises suite over a mutated pack copy
(missing file, bad JSON names the file, bad regex, dangling form_id,
duplicate source, double-routed theme, unknown supports, partial
morphology, missing stretch fallback, multi-problem error lists all);
mechanics-read-the-data pins.  Existing inventory/catalog tests
(test_error_patterns, test_progress_ledger routing invariant,
test_inventory_coverage) pass unchanged — they now validate data through
the same names.

**Docs:** system-overview §13 rewritten (7 data files + loader), §14
can_dos.py row, §19 watch-out 6 → DONE with a don't-regress note; README
directory map row.  ENGINEERING.md untouched (its CAN_DO_THEMES/
FORM_INVENTORY citations name symbols that still exist and still route in
code — accurate as written).
