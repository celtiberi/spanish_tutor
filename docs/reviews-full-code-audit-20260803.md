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
