# PEDAGOGY.md — the law of ml_teacher

**Status:** ENACTED 2026-07-28 (⬛ Claude drafted; user-directed restructure same day — theory above mechanism; ⬛ Grok countersigned with AMEND ×5 on the theory layer, all accepted and applied 2026-07-28 — transcript in docs/reviews-pedagogy-constitution.md). This file is the ONLY home of law text for this project. A review, research round, or debate that changes how the teacher behaves is NOT closed, and its conclusion is NOT binding, until the signed law paragraph exists HERE with author tag and absolute date (LAW-PROMOTION GATE, §7.2). Everything else — research rounds, review docs, code comments — is transcript, evidence, or implementation.

**Tiers used below:** **HARD LAW** (violation is a bug; blocked by lint/gate where mechanizable) · **BINDING** (enforced through review; violations must be argued, not slipped) · **GUIDELINE** (default; deviation needs a stated reason) · **DEBT** (named, tracked non-compliance — §8; never silent).

**Reading order for a new session or agent:** this file → CLAUDE.md → docs/system-overview.md → the relevant docs/reviews-*.md.

**Structure of this file:** §0 is the theory — claims about how acquisition works. §1 is machine-teacher architecture. §2–§6 are law — binding rules that implement the theory *or* protect engineering/honesty/process invariants. An *acquisition* law that serves no principle in §0 is a candidate for deletion; a principle in §0 with no serving law is unfinished work (§8). Architecture, privacy, and process laws are not required to cite a P-number.

---

## §0. The theory of acquisition — why every law below exists

These are the project's claims about how an adult acquires a second language on an A1→A2 track. Each is a claim about *learning*, not a teaching procedure. Teaching procedures live in §1–§6 and must serve these claims. Claims are falsifiable: if one falls, its dependent laws fall with it.

**P1 — Comprehensible meaning is necessary raw material, not a complete theory.** Adults build form–meaning mappings from language they can make sense of. Incomprehensible streams yield little acquisition. Coverage evidence for *comprehension* (not acquisition per se) sits near ~95–98% known words in text (Laufer tradition; Hu & Nation 2000, with adequate comprehension nearer ~98%). Krashen's i+1 names the intuition; it does **not** entail that input alone is sufficient. Output, attention to form, retrieval, and practice also matter (P3–P5, P8).
*Served by:* §2.1 (repair), §2.2–§2.3 (scaffolds / English jobs), R-C coverage work.

**P2 — New forms attach to what is already known — and interfere with near neighbors.** A new form–meaning pair is learned by association to prior knowledge (L1 cognate, image, sound-alike, known L2 paraphrase, schema). Ausubel; dual coding (Paivio); keyword method (Raugh & Atkinson 1975: ~88% vs ~28% free study on Spanish vocab in the classic experiment). Near-synonyms introduced together bind to each other more than to meaning (Tinkham; Waring). Association is necessary framing at first exposure; frequency of later encounters (P3, P8, P9) determines entrenchment.
*Served by:* §2.2 (anchor-first introduce, cluster ban), association table.

**P3 — Durable memory is built more by effortful, spaced retrieval than by re-exposure.** Retrieving a form under some difficulty, at expanding calendar lags, strengthens retention more than restudy or immediate re-hearing (testing effect, Roediger & Karpicke 2006; L2 spacing meta: medium-to-large spaced>massed, longer lags help *delayed* tests — Kim & Webb 2022; desirable difficulties, Bjork). Re-exposure is not useless; it is weaker. Scaffolds that made first mapping easy must be stripped on later encounters or retrieval never happens.
*Served by:* §2.4 (ladder, scaffold strip, regloss fault), §1.2 (scheduled retrieval).

**P4 — Communicative production and interaction develop productive ability.** Attempting to say something for a real purpose exposes gaps between intention and means (Swain output hypothesis). Negotiating meaning with an interlocutor drives development (Long interaction; Ellis TBLT). This does **not** mean every turn must be a task, nor that easy goal-free re-use is worthless (that is fluency work — P8).
*Served by:* §1.2 task phase, info-gap runtime, mode "try" moments.

**P5 — Attended form–meaning mapping, inside use, builds accuracy; pure drill is not required, pure CI is not enough.** Learners must notice relevant form (Schmidt noticing). Brief focus-on-form during meaningful exchange helps (Long). Processing instruction that forces form use for meaning has support (VanPatten). Explicit focus is not forbidden: focused L2 instruction yields large gains and explicit > implicit on average (Norris & Ortega 2000); Focus on Form and Focus on Forms both can work. Corrective feedback that pushes learner self-repair often outperforms pure recasts on uptake (Lyster & Ranta 1997: recasts frequent, weak for student-generated repair). Prefer recast when flow/affect demand it; prefer prompt/elicitation when the goal is repair of a targeted pattern.
*Served by:* §2.5 (budgeted, recency-gated correction), planned StructuredInputEngine (noticing — see NOTICING note in §8 UI-PRIMITIVES DEBT).

**P6 — Affect modulates participation and intake; it is not a binary gate.** Anxiety, boredom, and overload reduce willingness to communicate and the quality of engagement (WTC research; motivation/anxiety literatures). Krashen's "affective filter" is a useful metaphor, not a measured valve. Design for low ambush and real uptake without treating affect as on/off acquisition control.
*Served by:* §2.1, §2.7, correction budgets in §2.5; WTC proxy debt in §8.

**P7 — What is acquirable next depends on the learner's current interlanguage state.** The same input is i+1 for one learner and noise or boredom for another. Efficient teaching therefore requires an explicit model of what is held, partial, or absent (character sheet as *instrument*, not as the theory). This is learner-state dependence — a constraint on acquisition trajectories — not the slogan "teaching is diagnosis."
*Served by:* character sheet, placement, next_best, §3 honesty laws.

**P8 — Items progress through stages; automatization needs easy re-use of known language.** Rough stages: encounter → mapped → retrievable → usable under pressure → more automatic (skill-acquisition / DeKeyser; Nation's knowledge dimensions). Early stages need mapping and retrieval; later stages need speeded, low-burden re-use of *already known* language (fluency development). Nation's four strands (meaning-focused input, meaning-focused output, language-focused learning, fluency) is a **curriculum balance heuristic** (~equal time as a design target), not a law of the brain. *Known gap:* this system has no true fluency-development activity yet (free chat still pushes new/corrective work) — theory-level debt, §8.
*Served by:* §1.2 phase architecture (approximation only), §2.4 stage-aware re-encounters, ledger stage fields.

**P9 — Frequency and recycling entrench what association only starts.** Forms with higher type/token frequency and clearer form–function contingency are acquired earlier and more robustly (usage-based accounts: N. Ellis; Bybee). A closed pack still needs deliberate recycle density; one-shot introduce without scheduled return under-teaches even perfect first associations.
*Served by:* §2.4 scheduler, introduce budget ≤2/session, pack frequency fields (PACK-FREQUENCY DEBT, §8).

---

## §1. The two axioms

### 1.1 Authority exceeds perception (HARD LAW — frozen 2026-07-28, docs/reviews-adaptivity-architecture.md, 3 countersign rounds)
Code owns every teaching **decision**: when to correct, what is due, what is new, what the goal is, what counts as done, what the session's phases are. The model owns only the **performance**: natural Spanish, warmth, persona, role-play. The model is never the syllabus.
**Incident:** topic railroading and an ignored "I didn't understand" (session 20260726-155600) — a model left to govern its own pedagogy optimizes for conversational momentum, not learning.
**Reviewer test:** find the decision in code. If a teaching decision exists only as prompt text the model may ignore, it is advice, not architecture — file it as a gap or build the gate.

### 1.1a Direction, not scripts (HARD LAW — ⬛ Claude proposed, ⬛ Grok amended ×5 and countersigned, promoted 2026-07-28; user directive "provide direction to the AI — not hard code what is supposed to happen")
Corollary to §1.1: code and authored pack content own **decisions and inventory**; the model owns **spoken performance**. Authored pack/scene/task content states communicative **goals**, **constraints** (pack law, exit predicates, budgets), and **inventory** (forms, slots as values, association keys, setting *direction*). It does **not** supply the tutor's dialogue lines.
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
Free conversation is one phase of a session, never the whole. Code owns a phase plan (retrieval → new_input → task → free → **close**) via tutor/session_phases.py. Default turn shares 0.20 / 0.30 / 0.35 / 0.15 are BINDING defaults, not sacred constants; adaptations are listed in code. The **Close phase** (~1 turn, USER-ratified 2026-07-28 after the blind grade's "no arc, no close" defect; restores r6's original design) ends the session with a one-line "you practiced X" summary and a real Spanish farewell exchange — which also exercises introduced farewell vocabulary. (shipped 2026-07-28, server version 20260728-114151) Spacing durability (Kim & Webb 2022: spaced>massed medium-to-large on delayed tests) must be scheduled — it will not emerge from chat.
**Reviewer test:** with items due, free-flavor turns ≤ 0.25 of teaching turns (eval `phase_adherence`); plan defaults target ~0.15 free; session logs end with a close-phase turn once shipped.

---

## §2. Teaching laws

### 2.1 Learner uptake outranks everything (HARD LAW — frozen 2026-07-28, adaptivity review; standing order in the tutor system prompt AND the guard chain)
Answer the human first, teach second. Help requests, topic requests, and comprehension failure preempt every mode, phase, and agenda — and FREEZE the session phase clock (confusion never burns budget). The guard chain order in tutor/modes.py select_mode is frozen; no phase or engine may reorder or weaken it.
**Incident:** learner said "I didn't understand" and was railroaded onward (2026-07-28, the review's founding transcript — now a permanent CI fixture).

### 2.1a Learner-initiated content earns one turn of uptake (BINDING — ⬛ Claude proposed, ⬛ Grok amended ×4 and countersigned, promoted 2026-07-28; subordinate to §2.1; reopened §2.1 per §7.3 without weakening it)
**Scope.** When the learner volunteers meaning that is **not** a direct answer to the tutor's outstanding try/choice prompt and is **not** itself a §2.1 guard signal — including an attempted description, an off-script topic, or a self-flagged form (quotes, "?", "I don't know the word") — the tutor's **same turn** must take it up before any agenda pivot.
**Uptake move (same turn, in order):** (1) model the offered meaning in correct **pack-legal** Spanish (one short model); (2) set the try **on that meaning**. Agenda pivots (next_best, scenes, due items, introductions) wait **one** turn. Content-uptake does **not** freeze the session phase clock (unlike §2.1 guards).
**Self-flagged forms.** Corrected same turn with one clear target model when the target is pack-legal. If off-catalog: one brief L1 gloss or nearest pack-legal paraphrase only — **no** ledger/sheet introduce, **no** multi-turn open-world side quest, **no** denylist breach (§2.6 still HARD LAW). Same-turn self-flag repair does not consume the §2.5 form-focus hard-break budget unless escalated to multi-step form drill.
**Budget (anti-starvation).** At most **1 consecutive** content-uptake deferral turn, and **≤1 content-uptake deferral per 3 teaching turns** (same rate unit as §2.5 hard-break). When budget is exhausted: ≤1-clause acknowledge, then agenda may proceed.
**Architecture.** Code owns the agenda-yield decision once a detector exists (suppress same-turn next_best/introduce/scene pivot blocks). The model **performs** the short model + try only. Detection starts shadow/instruction+eval; a blocking gate requires pre-registered precision metrics frozen before results (§4.3). Regex-only meaning classification remains a smell (§4.2).
**Incident:** weather and breakfast abandoned mid-attempt; self-flagged «uvia»/«circa» unrepaired — session 20260728-103617 (blind-graded #1/#4 defects).
**Reviewer test:** find a turn where the learner's message contains an **off-script** attempted description (not an answer to the outstanding try) and the tutor's try targets an unrelated agenda item while the content-uptake budget still had room — that turn violates this law unless a §2.1 guard fired.

### 2.2 Nothing new arrives naked (HARD LAW — enacted 2026-07-28, r7 CONVERGED; enforced by gate:unscaffolded_new_item) — serves P1, P2, P3
The principle (P2): a new item must be *attached* to something the learner already holds at the moment it first appears — an association is built, or nothing is. The mechanism: first exposure routes by item class, in evidence order: true-cognate anchor → image dual-code → engineered ≥95%-coverage context (DEFERRED, §8) → one ≤6-word L1 micro-gloss. One new item per introduce move; ≤2 introductions per session; near-synonyms of the same theme never co-introduce (cluster ban — Tinkham/Waring interference; CODE VETO at any count, not advice). The scaffold exists to be stripped (P3): it appears at first exposure and never again unless retrieval fails. **Attachment clause (2026-07-29, floating-anchor incident; ⬛ Claude shipped, ⬛ Grok AMEND 2026-07-29):** Cognate/keyword **anchor** text counts as clothing only when the **item form and the anchor co-occur on the same line** of learner-facing text (enforced: `anchor_in_reply(..., key=)` line adjacency — presence-anywhere is not scaffold evidence). Introduce direction must require that co-occurrence in the anchor-bearing line (never a floating anchor the learner re-attaches by guessing). A why with no referent builds no association (P2). **Display order (serves the same principle, not a substitute for co-occurrence):** the item is met before its why — model before explain in every assembly (`compose_visible` + UI part blocks).
**Incident:** «hasta luego» and «adiós» introduced together, bare, 2026-07-28 — the founding failure of r7.
**Reviewer test:** grep a session log for a table key's first appearance; it must carry a rule_id (introduce plan) or a scaffold, or the gate must have fired.

**Where the clothing goes (rider — enacted 2026-07-29; ⬛ Claude proposed, ⬛ Grok AMEND accepted verbatim; docs/reviews-morph-card-introductions.md):** First exposure still follows this section's association path (cognate → image → engineered context when available → ≤6-word L1 micro-gloss). For structural items, chat may add a short explain beat — normally 1–2 lines; the first introduction of a new structure this session earns 2–3 lines of meaning and use — and must never dump a conjugation table or full paradigm in chat. When the introduced item maps to pack verb morphology, the Morphology card MUST show that paradigm on the same turn, selected in CODE from the turn's typed INTRODUCED / FIRST_SEEN events (§1.1 — never by prompt request or by re-scanning the tutor reply). If the learner also engages a verb form the same turn (error, attempted conjugation, grammar meta-question, how-say), learner engagement outranks the introduction fill. Chat brevity is not under-teaching when the depth has a designed home; depth with no home is the fault.
**Incident:** estar introduced 2026-07-29 with a one-line explain while the Morphology card — built for that paradigm — stayed blank; every card trigger read only the learner's turns.
**Reopen bound (Grok Q2):** if multi-verb-bearing introduce turns appear in logs at ≥1/50 introduce turns, reopen the first-hit picker (prefer sole INTRODUCED key, else an explicit priority table) — never silently merge paradigms.

### 2.3 English is scaffold, not wallpaper (BINDING — amended policy, r7 §6)
Three defined jobs: (1) lifeline when the learner is stuck (once, short, then back to Spanish); (2) first-exposure micro-gloss per §2.2; (3) cognate/keyword anchors. Dual-subtitle walls (X = Y on every line) remain banned (gate:english_wall). Re-glossing an already-introduced item without a same-turn retrieval failure is a fault (gate:regloss) — the retrieval effect requires the crutch gone.

### 2.4 Memory is retrieval, not re-exposure (HARD LAW — enacted 2026-07-28, r3/r6; tutor/retrieval_scheduler.py)
Introduced items ride the ladder 1d → 3d → ×2 capped at 14d; failure resets to 1d. Due items are woven into conversation as natural elicits — no flashcard chrome. The scaffold is stripped on re-encounter. Outcomes are recorded only on clear evidence; **silence records nothing** (a guess recorded as data is worse than no data).

**Varied retrieval (rider — enacted 2026-07-29; ⬛ Claude proposed, ⬛ Grok AMEND accepted verbatim; docs/design-encounter-variety.md):** The system records, in code, the frames in which an item has been elicited (`frames_seen` on the sheet entry, scheduler-owned, exposure history — never ability evidence) and directs each due elicit toward a frame not yet on that list. Soft direction only (§1.1a); the model chooses the new context. Replaying one frame on a spaced ladder is re-exposure wearing retrieval's clothes (P3). A multi-frame bar for ability promotion is out of scope of this rider and may ship only after the pre-registered revisit bound in docs/design-encounter-variety.md fires and a separate §3.2 countersign.
**Incident:** estar's every exercise through 2026-07-29 was the wellbeing frame; nothing remembered that across sessions. Same round, introduce-order corollary (tutor/introduce_router.py): greeting/farewell/courtesy openers lead the introduce queue ONLY for a true-zero sheet (both axes); mid-stream they sort last — and the related-bucket matcher reads only next_best targeting fields, never `avoid`/`reason` (the avoid-string "greetings" had promoted greetings themselves — the hola-on-known-open incident).

### 2.5 Correction is timely, budgeted, and repair-seeking — never an ambush (BINDING — r1 + example-bleed review 2026-07-28; theory: amended P5; Grok-amended 2026-07-28)
Errors are tracked as patterns with recency (K=4 learner turns) and cooldowns; a clean turn is never broken for a stale error. Form-focus hard breaks are budgeted (≤1 per 3 turns). Default move for flow: short recast. Default move when the sheet targets a pattern and affect allows: prompt/elicitation that seeks learner repair (Lyster & Ranta: prompts > recasts for student-generated repair — the elicitation path is CF-PROMPT DEBT, §8, until built). Comprehension repair stays on the SAME item — re-model, associate, no topic jump.
**Incident:** «llama» re-corrected on a clean turn from stale sheet counts (2026-07-28). **Citation-inversion incident:** the first draft of this law cited Lyster & Ranta FOR recast-first; their finding is the opposite (Grok countersign, 2026-07-28).

### 2.6 The pack is a closed world (HARD LAW — standing; course_packs/spanish_a1/pack.md)
The tutor teaches only pack inventory. Denylisted forms (gustar, hacer, open-world nouns) do not appear in models, examples, scenes, or scaffolds. All shipped content (scenes, examples, association anchors) must be pack-legal.
**Incident:** my own "pack-legal" replacement examples were 50% illegal (Grok REJECT, example-bleed review); the fix agent later had to rewrite my pack-illegal café-price info-gap. The pack law binds the authors, not just the model.

### 2.7 Affect is a signal, not decoration (GUIDELINE — r4; partially built)
Boredom reshapes topics and phase order; limited time compresses the session; anxiety (WTC proxy — DEBT, §8) shifts toward input over forced production. Time pressure is never mistaken for boredom.

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
**Enactment conditions:** (i) USER ratification — GRANTED 2026-07-30; (ii) pre-registered referee results attached (arms A/P1/P2/B0/B1, N≥20/session-clustered) — PENDING; (iii) completeness lint green — PENDING; (iv) non-default dual path until promotion — STANDING.
**Incident preserved:** premature token savings truncated a teaching reply at 60 visible tokens — that class of cut remains a bug under the dual-role regime.

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

1. **Safety guards** (uptake §2.1): time → topic_request → help_request → boredom → comprehension_repair — always preempt, always freeze the phase clock.
2. **Phase plan** (§1.2): what kind of turn this is (retrieval / new_input / task / free).
3. **Mode runtime**: which intervention, if any (cf_recast, form_focus, association, transfer) — budgeted, recency-gated.
4. **Content blocks**: due re-encounters (retrieval), introduce plan (new_input — owns the phase exclusively, §2.2), task goal + private info (task).
5. **The model performs** — Spanish, warmth, Marisol. Persona is skin, never authority.
6. **The output gate audits AND enforces**: critical faults (truncation, sheet leak, english_wall, unscaffolded_new_item, **probe_loop** — promoted 2026-07-30, repeated-probe incident 20260729-210545) force one repair rewrite; soft faults (regloss, unscaffolded_flood) are logged telemetry. **The still_fail floor (2026-07-30, system review, Grok-amended R1):** a reply whose repair leaves a critical/ship-ban fault may NEVER ship — the ladder is (a) part surgery (drop the probing try/continue, re-gate the remainder) then (b′) hold (the payload is not delivered; the client renders a non-teaching system notice, never code-owned Spanish, §1.1a). "Fail open" was policy and is repealed: a critic that cannot refuse is telemetry. Checker budget direction: ≤1 comprehension check per 3 turns; never a meaning quiz on sheet-known material (an A/B English quiz is worksheet chrome at ANY frequency in conversation mode); due items return as §2.4 natural elicits only.

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
| §6 still_fail floor | GATE_SHIP_BAN_FAULTS + _gate_floor (tests/test_gate_floor.py: strip + hold pins); output_gate_stripped/held events; session still-fail counter | system-review-20260730 countersign trail |
| §3.3 dual-role (amended) | check_teacher_truncation + completeness_v1 lint (B0 build) + logged brief/slice artifacts | USER-ratified 2026-07-30; referee results pending (arms A/P1/P2/B0/B1) |
| §2.3 walls/regloss | gate:english_wall, gate:regloss | — |
| §3.1 no personal data | identity stripped at load/normalize/process_turn; tool schema lacks identity; writers raise | eval sheet_evolution leak check (all trajectories) |
| §3.2 ledger honesty | scheduler allowlist + apply_delta strip | — |
| §1.2/§6 phase mix | eval phase_adherence, due_elicit_fired, introduce_scaffolded, task_goal_offered | transcript review |
| §4.3 promotion bar | evals/run_conv_smoke.py trajectories c01–c11 | pre-registered gate referee |
| §4.4 cache/version | /api/health stale_code; buildStamp in UI | — |

A law with an empty mechanical column and no named DEBT is under-enforced — that state is itself reportable in review.

---

*Enacted 2026-07-28. Amendment history lives in docs/reviews-pedagogy-constitution.md.*
