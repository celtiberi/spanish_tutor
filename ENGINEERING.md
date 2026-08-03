# ENGINEERING.md — the engineering, honesty, and process law of ml_teacher

**Origin:** split out of PEDAGOGY.md 2026-08-03 (USER: "Pedagogy is how
to teach. That is a coding decision. How confused are we?"). Sections
keep their historical numbers — citations reading "PEDAGOGY §1/§3–§9"
resolve here unchanged. PEDAGOGY.md now holds ONLY the theory of
acquisition (§0) and the teaching principles (§2).

**Status:** ENACTED 2026-07-28 (⬛ Claude drafted; user-directed restructure same day — theory above mechanism; ⬛ Grok countersigned with AMEND ×5 on the theory layer, all accepted and applied 2026-07-28 — transcript in docs/reviews-pedagogy-constitution.md). This file is the ONLY home of law text for this project. A review, research round, or debate that changes how the teacher behaves is NOT closed, and its conclusion is NOT binding, until the signed law paragraph exists HERE with author tag and absolute date (LAW-PROMOTION GATE, §7.2). Everything else — research rounds, review docs, code comments — is transcript, evidence, or implementation.

**Tiers used below:** **HARD LAW** (violation is a bug; blocked by lint/gate where mechanizable) · **BINDING** (enforced through review; violations must be argued, not slipped) · **GUIDELINE** (default; deviation needs a stated reason) · **DEBT** (named, tracked non-compliance — §8; never silent).

**Reading order for a new session or agent:** PEDAGOGY.md → this file → CLAUDE.md → docs/system-overview.md → the relevant docs/reviews-*.md.

**Structure of this file:** §1 machine-teacher architecture axioms · §3 honesty laws · §4 engineering laws · §5 process laws · §6 the gate/audit behavior contract · §7 change protocol (incl. §7.4 USER-ONLY powers) · §8 debt registry · §9 enforcement map. The theory (§0) and teaching principles (§2) live in PEDAGOGY.md; engineering law here may cite them but never impersonate them.

---

## §1. The two axioms

### 1.1 The model is the teacher; code is the record-keeper and auditor (HARD LAW — REWRITTEN 2026-08-03, USER-ratified §7.4: "We have a smart AI model that knows language and teaching. Why are we hard coding a plan that can't adapt to the student… fix the constitution")
The MODEL owns every teaching **decision**: what to teach next, when to correct, when to review, what the session's arc is. It decides from **facts code supplies**: the character sheet, session memory (what was asked/answered/shown — the anti-repetition record), what is due for review as *data*, the pack scope, and the live conversation. CODE owns three things and only three: **facts** (honest, complete, never scripted opinions), **honesty** (sheet writes only by deliberate graded tool calls with evidence; privacy by construction), and **audit** (the no-hide gate labels failures on the model's output and never rewrites, strips, or hides them — §6).
**Supersession clause:** the previous §1.1 ("code owns every teaching decision… the model is never the syllabus," frozen 2026-07-28) is REVERSED by USER authority. Every law below that assigns a lesson decision to code (mode selection, phase plans, introduce routing, per-turn instruction blocks) is superseded to this reading: the machinery may run as **shadow telemetry** (visible in notes/debug for comparison, useful to the audit) but its instructions may NOT enter the model's prompt, and it may not constrain the model's teaching. Deletions vs. shadow demotions are tracked in evals/omission_ledger.jsonl.
**Why the reversal:** the 2026-07-28 axiom answered a real incident (topic railroading, ignored confusion) with the wrong tool — a hard-coded curriculum that produced flashcard ladders, repeated probes, and a tutor that could not adapt ("always the same text… it was just stupid" — USER). The incidents are now answered by the no-hide audit + visible failures, not by scripting the teacher.
**Reviewer test:** find any instruction paragraph in the model's prompt that tells it WHAT move to make this turn. If one exists outside standing direction (persona, honesty rules, output shape, pack scope), it is a violation — file it.

### 1.1a Direction, not scripts (HARD LAW — ⬛ Claude proposed, ⬛ Grok amended ×5 and countersigned, promoted 2026-07-28; user directive "provide direction to the AI — not hard code what is supposed to happen")
Corollary to §1.1 (as rewritten 2026-08-03): code and authored pack content own **facts and inventory** — never decisions, never dialogue; the model owns teaching decisions AND spoken performance. Authored pack/scene/task content states communicative **goals**, **constraints** (pack law, exit predicates, budgets), and **inventory** (forms, slots as values, association keys, setting *direction*). It does **not** supply the tutor's dialogue lines.
**Allowed full-sentence Spanish in-repo (closed classes only):** (i) short form exemplars and contrast pairs for CF/form-focus; (ii) dictation / processing-instruction / listening item banks; (iii) eval, TTS, and ASR fixtures; (iv) learner-surface detection lists (`evidence_any`, pattern catalogs).
**Forbidden as tutor-facing content:** scene `model_lines`, recitable `elicit` scripts, and private-info fields stored as full answers the model must read aloud — store slot **values** and constraints; the model realizes Spanish under pack law.
**Concept lists** used for association/image selection derive from the association table (imageable + pack-legal); asset sidecars may attach metadata by the same key and must not invent a second concept set.
**Setting:** stable for one open task; rotate across tasks/sessions from a pack palette; no privileged personal-world setting in code.
**Enforcement path:** schema/lint — scene JSON must not require full-sentence tutor dialogue fields; optional deprecated fields must not be injected into realization prompts; evals assert direction shape, not fixed boat lines.
**Incident:** tutor produced "Yo estoy muy bien aquí en el bote" from authored `model_lines` / boat world (2026-07-28) — performance scripted by content, not by session goals.
**Migration status:** ordered steps + blockers in docs/reviews-direction-not-scripts.md (association-table 80% coverage gap is the flip blocker); until migration completes this law binds NEW content immediately and existing content via the tracked migration (SCRIPTED-CONTENT DEBT, §8).

### 1.1b Peripherals render the exchange, never the agenda (2026-07-29, café/me-llamo incidents; BINDING until HARD with tests; ⬛ Claude proposed, ⬛ Grok AMENDed — landed verbatim; docs/design-exchange-settlement.md)
Every learner-visible artifact outside the chat text that claims to be **about this turn** (teach images; morphology card in "live/engaged" mode; focus panel live fields) must be confirmed against a projection of the **realized** exchange — pure functions of `(learner_text, tutor_reply[, allowlisted turn events])` whose implementations admit no agenda inputs (no `next_best`, scene, phase, or sheet agenda; signature + closure enforced). Pre-call attach is **candidate** only; unconfirmed candidates are dropped and must not render. Every drop emits a typed log event `render_dropped:<kind>:<concept>` (operator/telemetry — not a learner-facing message). Bookkeeping that tracks "shown" (`note_image` / `images_shown` / display-tied costs) fires only on **confirmed** display. After any gate repair that regenerates the reply, pixel settlement re-runs before the re-gate so `image_present` cannot license a scaffold the learner will not see. Agenda systems (phase, scenes, `next_best`, introduce plans) steer **instructions** only. **Honesty carve-out:** a peripheral may show agenda-sourced "up next" / preview chrome only when explicitly labeled as not this-turn engagement (never silently as live). §1.1 gave code authority over decisions; this clause gives the conversation authority over what is displayed as this-turn truth.
**Incidents:** a `boat_likes` scene attached a café image while the learner discussed their house in Antigua (2026-07-29, session 195728); the morphology card sat pinned to `next_best` IP-03 ("me llamo") through a ser+gender-agreement exchange. Same class as the journey day-clustering (fixed 2026-07-29).

### 1.2 Conversation is a vehicle, not the system (HARD LAW on structure — enacted 2026-07-28, r6 CONVERGED; ratios BINDING defaults; Grok-amended 2026-07-28; Close phase USER-ratified 2026-07-28 per §7.4)
Free conversation is one phase of a session, never the whole — as THEORY (P3/P4/P8: retrieval, tasks, and fluency work all matter; chat alone under-teaches). **Code-owned phase plans are SUPERSEDED (2026-08-03, §1.1 rewrite):** tutor/session_phases.py may run as shadow telemetry only; the model shapes the session arc from the due/data facts and its own judgment. Default turn shares 0.20 / 0.30 / 0.35 / 0.15 are BINDING defaults, not sacred constants; adaptations are listed in code. The **Close phase** (~1 turn, USER-ratified 2026-07-28 after the blind grade's "no arc, no close" defect; restores r6's original design) ends the session with a one-line "you practiced X" summary and a real Spanish farewell exchange — which also exercises introduced farewell vocabulary. (shipped 2026-07-28, server version 20260728-114151) Spacing durability (Kim & Webb 2022: spaced>massed medium-to-large on delayed tests) must be scheduled — it will not emerge from chat.
**Reviewer test:** with items due, free-flavor turns ≤ 0.25 of teaching turns (eval `phase_adherence`); plan defaults target ~0.15 free; session logs end with a close-phase turn once shipped.

---

## §3. Honesty laws (the sheet)

### 3.1 The sheet is ability only — no personal data, anywhere, by construction (HARD LAW — enacted 2026-07-28, docs/reviews-personal-data-removal.md, countersigned)
No name, family, location, interests, or sensitive facts are captured, stored, or emitted — from ANY path: rules observer, model tool calls, prompts, score, UI, focus rail. Identity is stripped (not preserved) at load, normalize, every process_turn, and session open. tutor/learner_profile.py is disconnected reference code with hard-disabled writers.
**Incident:** the case-insensitive I-am regex made "I am searching for eggs" the learner's name; the tutor greeted "¡Hola, Searching!" (2026-07-28).
**Reviewer test (Grok's, executed):** process_turn with a tool_delta carrying identity → nothing stored, nothing in score/prompt/human view.
**Reserved:** re-enabling any user model is a USER-ONLY decision (§7.4) and a new design, not a re-enable.

### 3.2 Introduction ≠ knowledge (HARD LAW — enacted 2026-07-28, r7 S1)
Ledger writes (introduced_at, scaffold, first_seen, next_due, interval, streak) NEVER move confidence/status — enforced by allowlist in tutor/retrieval_scheduler.py, which also restores ability fields on any attempted write. The model's sheet tool cannot write schedule or ledger fields (stripped in apply_delta).
**Reviewer test:** run the interval ladder end to end; confidence must be byte-identical before and after.

**Progress is function, evidenced by production (rider — enacted 2026-07-29; ⬛ Claude proposed from research r8, ⬛ Grok research-round verified + build countersign AMENDs applied same day; docs/pedagogy-research-r8-progress-measurement.md):** The learner-facing definition of progress is the can-do FUNCTION, never the item ledger; items display only nested under the function they serve (routed in code: can_dos.CAN_DO_THEMES for lexicon themes, FORM_INVENTORY supports for forms — themes are content domains and may never stand in for a function). A can-do's display band moves on evidence only — observed production, task outcomes, spaced-retrieval success — never exposure or introduction. Mastery phrasing ("Can …") is legal ONLY when the known-gate ARITHMETIC holds (observed uses ≥ 2 AND confidence ≥ 0.80 — the status string alone is never trusted); 0.55 is emerging, always; below the emerging floor a can-do is quiet, whatever its status label says. The production-evidence milestones are code-derived event-facts that move no ability fields: first_solo (first spaced due-success under §2.4 re-encounter direction — scaffold strip is soft law, not gate-proven absence of help; copy may say "spaced recall," not "proved without help") and new_context (v1: due-success while frames_seen ≥ 2 — multi-frame exposure history, not yet frame-of-success attribution; see r8 build countersign 2026-07-29). Item tracking itself stays mandatory as the scheduler's substrate — words are inputs to progress, not its definition (r8 A1 finding: at Novice, items are the bulk of the *evidence* while never being the *meaning*).

### 3.3 No silent teacher-context truncation; dual-role complete contexts (HARD LAW — AMENDED 2026-07-30, USER-ratified per §7.4 ("ratify, run P1/P2, build B0 in parallel"); ⬛ Grok replacement text adopted verbatim after Claude's draft was REJECTED for a windowing contradiction + "named rule" loophole; docs/design-planner-rounds.md; lint: scripts/check_teacher_truncation.py + the completeness lint below; pre-commit gate)
**Paths.** (A) **Teaching-decision path** = code only (phase/mode/introduce/due routers, schedulers, LessonBrief assembly, slice assembly). It always reads the full sheet, full pack, full stance, and code-derived history facts; the full transcript remains on disk for audit. No model on this path may invent targets, introduce keys, budgets, bans, or exit criteria. An optional later LLM packager (B1 arm only), if ever enabled, may phrase soft direction inside an allowlisted schema and may not add decision authority. (B) **Realization path** = the single speaking-model call. It receives a **complete-for-role** context: the versioned B0 floor (completeness schema `completeness_v1` — ten members incl. law core, LessonBrief, same-turn slice, negative/ban projection with denylist∪clusters∪asked-frames∪known-for-ban, budgets, session manifest, last K≥2 exchanges, ≤1k-token pack index, fallback results) — never "whatever fits the token budget."
**Completeness predicate (machine-checkable every turn; ship lint):** every floor member present in the logged turn artifact OR its paired capability removed in code; every pack key in allowed_new ∪ due ∪ repair_targets ∪ cf_targets ∪ learner-detected slice present with the fields the gate judges; every ban class the turn's gates can fire either injected or the capability removed; **token pressure, latency, and soft overflow are never legal omission reasons**; omissions only from the schema's versioned allowlist — free-form "named rules" never qualify.
**Truncation ban (clarified).** Silent [:N] slices and silent history drops for latency/cost remain **banned on all paths**. Explicit realization windowing (last K verbatim exchanges + code-owned manifest for older turns) is legal ONLY on the realization path, ONLY under this amendment, ONLY when K and the manifest schema are versioned and linted. Until the referee passes, TEACHER_CONTEXT=brief is dual-path and non-default; the full-context path remains the default teacher.
**Enactment conditions:** (i) USER ratification — GRANTED 2026-07-30; (ii) pre-registered referee results attached (arms A/P1/P2/B0/B1, N≥20/session-clustered) — RUN 2026-08-02: B0 won compliance (0.210 vs 0.321 sf/turn, z=−2.09) at 0.47× cost but N=19 failed the frozen power rule, and the frozen-rubric blind grade found responsiveness −0.93 (the code brief carried the curriculum but lost the learner's world) — **promotion HALTED, B0 dormant**; (iii)–(iv) moot, see amendment below.
**Incident preserved:** premature token savings truncated a teaching reply at 60 visible tokens — that class of cut remains a bug under the dual-role regime.
**AMENDMENT 2026-08-03 (USER-directed per §7.4; supersedes the dual-role B0 design above).** Under rewritten §1.1 (the model is the teacher) the code-assembled LessonBrief is dead as a concept — the completeness_v1 schema and B1-packager clauses apply only to the retired B0 arm. The shipped default is **TEACHER_CONTEXT=plan**, the USER's two-phase architecture: "The pedagogy is handed to the teacher. The teacher gets the character sheet so it knows where the student is. The teacher creates a plan for this session. Now we have a smaller context that is fed for the future rounds unless something changes and we need a new plan."
- **PLAN turns** (session open, or after `<replan/>`) carry the FULL context: PEDAGOGY.md verbatim, the full character sheet, full history; the model writes its own private `<plan>` block. **Same-day addendum:** the prose course pack was DELETED — the sheet is the single planning artifact: a DOMAIN MODEL (`domain_targets_not_yet_touched` from the association table, `domain_scope` deferred/out-of-scope/recognition-only law, frozen form inventories as grammar targets, misconception diagnosis vocabulary with empty detect — the model diagnoses, code records) co-located with the LEARNER MODEL (per-item state). **Vocabulary ruling (Grok-countersigned, docs/reviews-sheet-vocabulary.md):** the sheet is never called a curriculum/syllabus/course — it carries content SELECTION; sequence belongs solely to the model's session plan, which is never called a "course." Domain DATA (association table, teach-asset sidecar, scenes as domain-situated materials — never path law) lives in `domain/spanish_a1/`. The B0 "brief" arm was deleted with the pack it fed on.
- **ROUND turns** carry the model's OWN plan + full sheet + session facts + due data + the last `ROUND_HISTORY_MESSAGES` (=12, versioned in `tutor/session_plan.py`) messages; no pedagogy file. The model may revise its plan any turn and escapes to full context with `<replan/>`.
- **The truncation ban stands.** The round window is explicit, versioned, and `truncation-ok`-annotated — the lint gained a named-constant-window pattern so it cannot recur silently, and the characterization guard (`tests/conftest.py::assert_full_teacher_context`) enforces the round contract (no pack, plan present, tail-aligned window of exactly K) rather than exempting it. Silent slices remain banned on all paths.
This addresses the blind-grade failure directly: the plan is the teacher's own words, not a code brief — the learner's world survives because its author is the one who taught it.

### 3.4 Unknown is not neutral (BINDING — cost review 2026-07-28)
Unpriced models are tracked and FLAGGED, never silently $0. Missing evidence is a gap, never a fake-neutral score. A crashed check reports UNCHECKED, not clean.

---

## §4. Engineering laws

### 4.1 Single-purpose subsystems; one orchestrator (HARD LAW — enacted 2026-07-28, r6 adjudication)
Every engine (scheduler, phases, router, task runtime, gate) is a single-purpose module with a data contract, stdlib-first, unit-tested with fake clocks where time matters. The SessionPhaseController is the sole orchestrator; engines emit plans/trials and NEVER call the model independently. Exactly one realization path.
**Reviewer test:** grep an engine for a model client import. Any hit is a violation.

### 4.2 Regex for judgment is a smell (BINDING — user directive 2026-07-28: "if you see regex it is smell for 'we could be doing this better'")
Classifying INTENT or MEANING by regex is presumptively wrong — use a cheap LLM classifier (shadow-first, promotion-gated). Pattern-matching is legitimate only for surface forms (did the learner literally write «estoy»), with word/MWU boundary discipline.
**Incidents:** "Searching" (§3.1); the sol image firing inside "Marisol" and "solo"; help requests missed by pattern gaps. Three incidents, one smell.

### 4.3 The evals gate is the promotion bar (HARD LAW — standing convention, memory + adaptivity review)
Doc review, countersign, or agreement NEVER equals validation. Behavior ships when the behavioral gate in evals/ passes; authority changes (e.g., classifier shadow → blocking) ship only through pre-registered gates FROZEN before results exist. Criteria written after seeing results are rationalizations.

### 4.4 Web assets bust their caches; servers prove their version (HARD LAW — standing, memory + stale-code incidents)
Editing web_static/app.js or styles.css REQUIRES bumping their ?v= in index.html. Every restart is verified against /api/health (version + stale_code:false). A change that isn't running is a change that didn't happen.
**Incidents:** two separate debugging sessions burned on stale JS / a stale July-26 process.

### 4.5 Enforcement over instruction (BINDING — pattern law)
When a rule matters, prefer, in order: capability removal (the tool cannot express the violation — e.g., identity stripped from the tool schema) → mechanical gate/lint (output gate faults, commit hooks) → review-prompt check (judgment half, fixed output schema) → prompt text (weakest; never the only layer for a HARD LAW).

---

## §5. Process laws

### 5.1 Dual-author adversarial review (BINDING — standing, ~30 rounds of case law in docs/reviews-*.md)
Design, law, research, and grading run propose → countersign (Grok) → adjudicate with reasons → converge (2–4 rounds), appended to a rolling docs/reviews-*.md file. Verdicts are per-item ACCEPT/AMEND/REJECT. **Never average** — accept with reasons or counter with equal evidence. Executed proofs beat prose. All-countersign rounds are suspicious; a zero rejection rate means the prompts are steering.
**Case law:** Grok caught a shipped PII write path, a 3× pricing error, loanword circularity, two wiring defects by execution, and a gate storm — each would have shipped otherwise.

### 5.2 Delegation: workhorses execute, the director checks (BINDING — user directive, stated three times)
Grok and Agent-tool subagents carry token-heavy work (sweeps, investigations, mechanical fix batches, reviews). The main session keeps adjudication, small surgical edits, law-writing, and final verification. Inline grunt work is a rule violation, not a style choice.

### 5.3 Absolute dates only (BINDING — promoted from GUIDELINE by Grok countersign 2026-07-28)
"Today"/"this week" rot; AI authors have no persistent clock. Law headers, incidents, ledger fields, and review records carry ISO dates (YYYY-MM-DD).

### 5.4 Report outcomes faithfully (BINDING)
Failing tests are reported with output; skipped steps are named; agents return raw data, not reassurance. A validation claim without the command that produced it is prose.

---

## §6. Behavior contract (the tutor's runtime constitution, priority order)

1. **Safety guards** (uptake §2.1): time → topic_request → help_request → comprehension_repair — always preempt, always freeze the phase clock. (boredom guard DELETED 2026-07-30, junk audit — never fired in 207 turns.)
2. **Phase plan** (§1.2): what kind of turn this is (retrieval / new_input / task / free).
3. **Mode runtime**: which intervention, if any (cf_recast, form_focus, association, transfer) — budgeted, recency-gated.
4. **Content blocks**: due re-encounters (retrieval), introduce plan (new_input — owns the phase exclusively, §2.2), task goal + private info (task).
5. **The model performs** — Spanish, warmth, Marisol. Persona is skin, never authority.
6. **The output gate audits and SURFACES — it never hides (NO-HIDE, USER-enacted 2026-08-01, commit 898af6e):** the gate checks every reply (truncation, sheet leak, english_wall, unscaffolded_new_item, probe_loop, regloss, flood, no_teach_move) and on failure the RAW reply ships with `gate_fail` + a visible diagnosis — no repair rewrites, no part stripping, no blank holds, no content scrub. Rationale: rewrite/strip/hold machinery papered over model/prompt failures so the generator never got fixed (fix generators, not instances); a visible GATE FAIL is the audit that drives the fix. This supersedes the 2026-07-30 repair-ladder / never-ship / harm-partition text (that ladder is retired; its countersign trail remains in docs/archive/reviews/). Fault classes remain as audit labels. Checker budget direction unchanged: ≤1 comprehension check per 3 turns; never a meaning quiz on sheet-known material; due items return as §2.4 natural elicits only.

---

## §7. Change protocol

### 7.1 How a law is born
Incident or user directive → draft here (author tag + date) → Grok countersign (append to a docs/reviews-*.md) → adjudication with reasons → header updated with amendment count. The debate transcript is never summarized away.

### 7.2 LAW-PROMOTION GATE (HARD LAW)
A review that changes teacher behavior cannot close until its law paragraph lands in THIS file. The review doc keeps the transcript plus a pointer ("Law live at PEDAGOGY §x.y as of DATE").

### 7.3 Freeze semantics
Frozen items (guard chain; classifier promotion gates; adaptivity rulings) change only through a new countersign round that names the frozen ruling it reopens. Pre-registered thresholds never move after data exists.

### 7.4 Reserved USER-ONLY decisions (dual-AI agreement cannot create these) — Grok-amended 2026-07-28
- Re-enabling any personal-data / user-model capture (§3.1), or any biometric / voice retention beyond ephemeral ASR/TTS processing.
- Flipping the signal classifier to BLOCKING before its pre-registered gates pass.
- Changing the persona, the product's Spanish-first stance, or the product identity (language, level band, "pedagogy tutor not open chatbot").
- Reopening the session-phase architecture (§1.2) or the no-truncation law (§3.3).
- Weakening or deleting the LAW-PROMOTION GATE (§7.2) or PEDAGOGY.md as sole law home.
- Suspending dual-author adversarial review (§5.1) for changes to this file.
- Redefining the eval promotion bar (§4.3) after results exist (thresholds freeze before data; reopen is USER-ONLY or a new pre-registered gate set).
- Spending decisions (new paid models/tiers) beyond current defaults.

### 7.5 Precedence
If any other doc, prompt, memory, or code comment conflicts with this file, THIS FILE WINS until amended here. CLAUDE.md points here; it does not duplicate law.

---

## §8. Debt registry (named non-compliance — first-class, never silent)

| Debt | What it is | Created | Retired when |
|---|---|---|---|
| R-C DEFERRED | Engineered ≥95%-coverage context rule unbuilt; introduce falls through to gloss/keyword | 2026-07-28 (thin ship, adjudicated) | Coverage estimator built + router rule enabled |
| STORM RESIDUAL | ≥3-key formulaic turns degrade to soft flood fault, not critical | 2026-07-28 (Grok r2, adjudicated) | first_seen coverage makes floods rare in logs |
| MULTIDAY-HARNESS DEBT | Spacing claims untestable beyond fake-clock units; no cross-session eval trajectories | 2026-07-28 (r6) | Multi-day simulated eval harness ships |
| UI-PRIMITIVES DEBT | No choice buttons/image hotspots; StructuredInputEngine blocked | 2026-07-28 (r6) | Client response primitives ship |
| ITEM-BANK DEBT | Pack is prose + 3 scenes; PI/dictation banks don't exist | 2026-07-28 (r6) | Pack item-bank JSON ships |
| WTC/ANXIETY DEBT | Affect adaptation references signals not yet computed | 2026-07-26 (r4) | Behavioral proxy (latency, length, English-escape) ships |
| E-CLASSIFIER SHADOW | Intent classifier runs shadow-only pending frozen promotion gates (n≥100 shadow, n≥80 labeled, P/R≥0.90) | 2026-07-28 (adaptivity review) | Gates pass → blocking, or misses redirect the design |
| FLUENCY-STRAND DEBT (theory-level, P8) | No activity whose primary goal is faster/easier re-use of *already known* language with near-zero new items and suppressed form-focus. Free phase (default 15% of turns) still allows correction and agenda pressure. | 2026-07-28 (§0 P8) | Ship one production-fluency activity: timed re-tell or speeded Q–A over a mastered exchange (known coverage ≥ pack threshold; form-focus cooldown forced off). Optional later: easy-input flood at ~100% known coverage (input fluency). Eval: fluency turns log `activity_type=fluency` and introduce_count=0. |
| PACK-FREQUENCY DEBT (P9) | Pack items carry no frequency/recycle-density tags; introduce order and recycling are theme-ordered, not frequency-informed | 2026-07-28 (Grok countersign, P9) | Pack gains frequency tags; candidate_keys and recycle density consume them |
| CF-PROMPT DEBT (P5) | Elicitation/prompt-based corrective feedback unbuilt; cf_recast is recast-only despite Lyster & Ranta favoring prompts for targeted repair | 2026-07-28 (Grok countersign) | A prompt/elicitation move ships for sheet-targeted patterns (affect-gated), with eval coverage |
| SHEET-CHALLENGE DEBT (§7 P7) | The character sheet is the canonical model everything trusts, but no consumer (eval, blind grader, gate) can formally DISPUTE a sheet claim; contradictory evidence waits for a human to notice | 2026-07-28 (cross-repo note, stocks §2o challenge-lane pattern) | A structured challenge protocol ships: claim key + dated evidence → claim marked disputed wherever the sheet is consumed, quality-bar validated, append-only |
| NEW_CONTEXT_FRAME_OF_SUCCESS DEBT (§3.2 rider, P3) | new_context v1 fires on due-success while frames_seen ≥ 2 — multi-frame EXPOSURE, not proof the success happened in a new frame (the success may be in the old frame) | 2026-07-29 (r8 build countersign, item 5) | Mint only when the success frame is itself new (frame-of-success attribution); pre-registered: no ability-axis use of multi-frame data until this lands (pairs with the §2.4 revisit bound) |
| ARM-RECONCILE DEBT (§4.3) | Teaching-policy changes ship against the eval gate but nothing PRE-REGISTERS what each change should improve in live transcripts, or reconciles HIT/MISS on a cadence — plausible pedagogy can survive on plausibility | 2026-07-28 (cross-repo note, blind-arm/reconcile pattern) | Policy changes arm an append-only expected-improvement record (rubric dimensions / misconception IDs); transcript reconcile reports HIT/MISS with small-N banner, no post-hoc rewrites |
| SUMMONS DEBT | Eval regressions, gate-fault storms, and sheet corruption land only in logs/ — a summons no one receives is not a summons (stocks B1 v2 incident class) | 2026-07-28 (cross-repo note) | Failure paths audited and classed: what pages the user, what triggers an automated diagnosis round, what may stay a log line — with the decision recorded here |
| WATCHDOG DEBT (§4.4) | Nothing auto-restarts tutor.web_app on source change; stale-process incidents (the July-26 ghost server) are detected by health stamp but repaired by hand | 2026-07-28 (cross-repo note; our own 2026-07-28 stale-process incident) | A watchdog re-execs the server when disk version ≠ running version; manual-restart ritual retired |
| SCRIPTED-CONTENT DEBT (§1.1a) | Existing scenes carry model_lines/recitable elicits/private-info sentences; modes/teach_assets carry parallel frozen concept lists; association table missing 4 of 5 legacy association nouns (80% gap = flip blocker) | 2026-07-28 (direction-not-scripts countersign) | Migration steps 1–7 in docs/reviews-direction-not-scripts.md complete: table filled, selection table-derived, model_lines out of realization prompts, scene schema v2, scenes regenerated under setting palette, evals assert direction shape, prewarm refreshed |
| ZERO-FLOOD SEVERITY (§2.2/P1) | unscaffolded_flood is soft for all learners; a blank-sheet learner still SEES multi-item floods (blind grade 20260728b: comprehensibility 4, vocab support 3) | 2026-07-28 (D-grade session review) | Blank/zero learners get a hard one-new-item-per-turn cap (gate severity or instruction+gate pair), countersigned before flip |

Adding a debt requires: name, date, what full compliance would be, retirement condition. Retiring one requires the condition met and a dated note.

---

## §9. Enforcement map (what makes each HARD LAW real)

| Law | Mechanical check | Judgment check |
|---|---|---|
| §3.3 no truncation | scripts/check_teacher_truncation.py + .githooks/pre-commit | — |
| §2.2 naked items | gate:unscaffolded_new_item (critical) + cluster veto | countersign rounds on router/table |
| §2.2 rider: card carries the paradigm | morph_card:<lemma> note + tests/test_turn_morph.py::TestIntroMorph + golden arc pin (morph_card:estar) | reopen bound: multi-verb introduces ≥1/50 → picker review |
| §2.4 rider: varied retrieval | frame_recorded:<key>:<frame> note + tests/test_encounter_variety.py + due-block direction line | pre-registered revisit 2026-08-12 / 30 writes / >50% single-frame rule (design doc) |
| §3.2 rider: progress is function | can-do sections + band gates in progress_ledger (tests/test_progress_ledger.py TestCanDoThemeRouting/TestR8ProductionMilestones); first_solo/new_context ledger-deduped | r8 doc countersign trail; mastery copy audit (no "Can …" below known gate) |
| §1.1b exchange settlement | exchange_render purity lint + signature pins + café-class fixture (tests/test_exchange_render.py); render_dropped events; settle_pixels ≤2/turn | design-exchange-settlement.md countersign trail |
| §6 no-hide gate | gate_fail surface + visible diagnosis (tests/test_gate_floor.py TestGateNoHide: no repair/strip/hold events, raw ships); session still-fail counter | USER-enacted 2026-08-01 (commit 898af6e); prior ladder trail archived |
| §3.3 two-phase plan context (2026-08-03 amendment) | check_teacher_truncation (incl. named-constant-window pattern) + conftest guard round contract + tests/test_session_plan.py (plan/round/replan/strip pins) | USER-directed 2026-08-03; B0 dormant (referee run 2026-08-02: N=19 power FAIL, blind responsiveness −0.93) |
| §2.3 walls/regloss | gate:english_wall, gate:regloss | — |
| §3.1 no personal data | identity stripped at load/normalize/process_turn; tool schema lacks identity; writers raise | eval sheet_evolution leak check (all trajectories) |
| §3.2 ledger honesty | scheduler allowlist + apply_delta strip | — |
| §1.2/§6 phase mix | eval phase_adherence, due_elicit_fired, introduce_scaffolded, task_goal_offered | transcript review |
| §4.3 promotion bar | evals/run_conv_smoke.py trajectories c01–c11 | pre-registered gate referee |
| §4.4 cache/version | /api/health stale_code; buildStamp in UI | — |

A law with an empty mechanical column and no named DEBT is under-enforced — that state is itself reportable in review.

---

*Enacted 2026-07-28. Amendment history lives in docs/reviews-pedagogy-constitution.md.*
