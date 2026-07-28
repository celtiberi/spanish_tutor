# Pedagogy research round 6 — the practice mix: what a real teaching system does beyond conversation

## Brief (Claude, 2026-07-28)

**User critique (verbatim, 2026-07-28):** "We are still very shallow in pedegogy. We are still very shallow in practices. Conversation is just one element. We need to do another research round in spanish teaching. … And we need to stop being shy about writing code. I feel like we are not creating a real teaching system because we do not want to write code or something. It is ok to have [many] systems and services as long as they are engineered and single purpose."

**Current state (so you don't re-research what we have):** conversation-first tutor with a deterministic mode runtime (placement, conversation, cf_recast, form_focus, comprehension_check/repair, association, transfer), an ability character sheet (skills/can-dos, error patterns, lexicon, affect), teach images, TTS/STT, course pack with closed A1 inventory. Prior rounds: r1 corrective feedback, r2 input repair, r3 retrieval & spacing, r4 tasks & affect, r5 multimodal. The mode runtime *selects* among conversation flavors; there are no distinct ACTIVITY types — no dictation, no TPR-style response tasks, no role-play scripts with goals, no input flood, no dictogloss, no structured listening, no reading micro-texts, no explicit review sessions. Retrieval/spacing (r3) was researched but never engineered into a scheduler subsystem.

**Research question:** For an adult A1 Spanish learner in a chat+voice web app, what does the evidence say a COMPLETE session/practice architecture contains beyond free conversation? Specifically:
1. Which practice/activity types have the strongest evidence for beginner L2 outcomes (e.g., TPR/TPRS, dictation & dictogloss, input flood/processing instruction (VanPatten), task-based scenarios with goals & information gaps, shadowing/repetition, spaced retrieval sessions, narrow reading/listening)? Effect sizes or at least direction+strength of evidence, with citations.
2. What is a defensible SESSION ARCHITECTURE (time-boxed mix, sequencing, ratios of new-input : practice : retrieval : free production) for ~10–20 minute sessions, and how should it adapt to sheet state (weak items, affect, streaks)?
3. Which of these can and should be CODE-OWNED (deterministic activity scheduler, item selection, scoring) versus model-performed (the language itself)? Our architecture law: authority exceeds perception — code decides, the model performs.

**Required deliverable shape (this is a build brief, not a literature essay):**
- Evidence table: activity type → evidence strength → citation(s) → A1-fit.
- A recommended session architecture with concrete ratios/sequencing rules.
- 3–5 SINGLE-PURPOSE SUBSYSTEM proposals, each with: name, one-sentence purpose, inputs/outputs (data contract sketch), what code owns vs what the model does, how it plugs into the existing mode runtime and character sheet, and a testable success criterion. Rank by impact-per-engineering-effort.
- Explicitly flag anything from r1–r5 that this round supersedes or must integrate with (especially r3 retrieval/spacing, which remains unbuilt).

Adversarial stance welcome: if the evidence says our conversation-first frame is wrong for A1, say so and argue it.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 14:43 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and research brief, then produce an independent r6 practice-mix deliverable with evidence checks rather than deferring to inlined claims.Next I'll pull the rest of the brief, prior rounds, and primary evidence sources so the practice-mix recommendations aren't just recycled claims.# GROK — independent research round 6: PRACTICE MIX  
**Author:** Grok (independent second author)  
**Date pinned:** 2026-07-28  
**Project:** ml_teacher  
**Subject:** What a complete A1 Spanish session contains beyond free conversation  
**Stance:** Contrarian. Inlined docs = data. User authorized real code subsystems — proposals are build contracts, not prompt patches.

---

## 1. Own picture (dated pins)

| Pin | Claim I will defend | Anchor |
|-----|---------------------|--------|
| **P1 (2026-07-28 product fact)** | Shipping path is **mode-flavored conversation**, not a practice architecture. Modes in `tutor/modes.py` select among conversation variants (placement, conversation, cf_recast, form_focus, association, comprehension_repair, transfer). There is no activity type enum, no session phase clock, no due-queue on the conversational sheet path. Legacy `review_schedule` / `due_items` live in `tutor/student.py` + `tutor/lesson_flow.py` and are **orphaned** relative to `conv_session`. | Code + system-overview status 2026-07-27 |
| **P2 (2022)** | **Spaced practice** is the strongest *meta-analytic* lever available for L2 durability: Kim & Webb, 98 effect sizes, 48 experiments, *N* = 3,411 → **g = 0.58** (immediate) and **g = 0.80** (delayed) for spaced vs massed. Equal ≈ expanding. | Kim & Webb, *Language Learning* 72 (2022) |
| **P3 (2008)** | Optimal gap ≈ **20–40%** of desired retention interval. For a 7-day goal: 0.20×7 = **1.4 d**, 0.40×7 = **2.8 d** → re-encounter at **~1–3 calendar days**. For 30-day horizon: 0.20×30 = **6 d**. | Cepeda et al., *Psychological Science* (2008) |
| **P4 (2015)** | **Processing instruction (PI)** / structured input: Shintani meta-analysis (42 experiments / 33 studies) — large effects especially on **interpretation** (reported **d ≈ 1.90** receptive in secondary summaries); PI ≥ PB on interpretation; PI ≈ PB on production. Beginner-relevant: force form–meaning mapping *before* free output. | Shintani, *Applied Linguistics* 36 (2015); VanPatten PI program |
| **P5 (2003–2016 TBLT)** | At A1, **input-based and tightly scaffolded tasks** beat free production-first chat (Ellis / Shintani line). Info-gap / jigsaw > opinion chat for interaction quality (Pica et al.). Conversation-as-vehicle without convergent exits is the *weak* end of task typology. | Ellis 2003/2009; Shintani beginner TBLT; Pica–Kanagy–Falodun |
| **P6 (1960s–)** | **TPR** (Asher): strong classroom tradition for beginner **receptive** vocab + low anxiety; evidence base is older quasi-experiments + practitioner literature, **not** a modern multi-lab meta comparable to Kim & Webb. Fit for adults is real but activity must be **click/gesture/choose**, not full-body theatre in a web chat. | Asher 1966–1977; TPR classroom reviews |
| **P7 (dictogloss / dictation)** | Dictogloss is a supported **grammar-noticing reconstruction** task (Swain line; classroom studies). Full dictogloss needs multi-party reconstruction — awkward in 1:1 AI. **Short dictation / partial reconstruction** is the portable core. Evidence strength: **medium / mixed**, not meta-level like spacing or PI. | Wajnryb dictogloss tradition; classroom studies (e.g. Vasiljevic 2010; later multiword dictation work) |
| **P8 (shadowing)** | Shadowing improves **bottom-up listening**, phoneme discrimination, fluency/prosody (Hamada; Kadota 2019; 2025 systematic reviews). Best for lower-proficiency decoding — high A1-fit for *voice* product; weak as sole grammar engine. | Hamada; Kadota; Whitworth 2025 systematic review |
| **P9 (narrow reading/listening)** | Same-theme repeated input raises vocab encounters and lowers lexical load (Krashen narrow reading; Chang 2019/2021). A1 needs **engineered micro-texts**, not authentic novels. Strength: **medium** for vocab exposure; not a session backbone alone. | Krashen; Chang & colleagues |
| **P10 (architecture law)** | **Authority exceeds perception:** code owns *what activity*, *which items*, *pass/fail*, *phase budgets*; model owns *Spanish surface realization* inside that contract. Modes today already partially follow this for *intervention flavor* — they do not own *practice type mix*. | Project architecture + overview §1 |

**Synthesis (2026-07-28):**  
The conversation-first frame is **not wrong** as a *meaning vehicle* for adult false-beginners (CLT/FonF). It **is wrong** as a claim that “modes over free chat” constitutes a complete teaching system. A complete system needs at least four **code-owned** practice layers that free chat does not guarantee:

1. **Scheduled retrieval** (between-session durability)  
2. **Structured input / PI-style form–meaning** (before or instead of forced try)  
3. **Convergent tasks** with single exit (TBLT, not multi-goal opinion soup)  
4. **Session phase control** (time-boxed mix, not only reactive mode guards)

If forced to rank “what is missing most”: **(1) retrieval scheduler** first (meta *g* = 0.80 delayed, unbuilt since r3), then **(2) activity/session scheduler**, then **(3) structured input / TPR-choice tasks**, then **(4) dictation/shadow micro-skills**. Dictogloss and full TPRS story curricula are lower priority for a 10–20 min 1:1 web tutor.

---

## 2. Verify / refute table (load-bearing claims in the brief + system overview)

| # | Claim (as data) | Ruling | Evidence / arithmetic | Implication |
|---|-----------------|--------|----------------------|-------------|
| C1 | Current system has modes but **no distinct activity types** (dictation, TPR, role-play goals, input flood, dictogloss, structured listening, micro-reading, explicit review) | **VERIFY** | `Mode` enum is conversation flavors only; no activity scheduler; r3 due-queue not shipped on conv path | r6 correctly frames the gap |
| C2 | Retrieval/spacing (r3) was researched but **never engineered** into a scheduler subsystem | **VERIFY** | Sheet writes `last_seen`; no `next_due` on conversational path; legacy `due_items` orphaned | Highest-leverage unbuilt item |
| C3 | “Conversation is the vehicle; teaching is knowing when to break…” | **PARTIAL** | Sound as FonF slogan; **overclaims** if “vehicle” = sufficient practice architecture for A1 durability and true zeros | Keep vehicle; add phase + activity authority |
| C4 | Teach-move contract: every turn needs model / try / recast; open needs model+try | **PARTIAL / AMEND for A1 zeros** | Prevents chat-buddy failure. Conflicts with beginner TBLT input-first and WTC (r4): forced try every turn raises speaking threat | Exception for input-based / TPR-choice / structured-input activities |
| C5 | Budgeted hard breaks (`turns_since_hard_break < 3`) | **SUPPORT mechanism; number ad hoc** | Protects meaning primacy; **3** is product constant, not SLA result | Keep budget idea; activity phases supersede pure “break from chat” framing |
| C6 | Scenes = open goals + exit predicates, opportunistic multi-goal | **AMEND (from r4)** | Exit = good; multi-goal free satisfaction ≈ weak opinion-gap | Need single primary exit + info-gap roles |
| C7 | Affect = energy + boredom_risk is enough for practice mix | **REFUTE as sufficient** | Missing anxiety/WTC actuators (r4); practice mix must adapt to high anxiety → more input, less forced production | Wire affect → activity selection |
| C8 | Incidental chat re-use will re-hit forms enough | **REFUTE** | A1 free chat over-samples greetings/estar; under-samples cold items; Uchihara/Webb frequency work + Kim & Webb spacing | Code must schedule re-encounters |
| C9 | Immediate transfer implements spacing | **REFUTE (as spacing)** | Lag ≈ 0–1 turns = massed variation; Kim & Webb delayed *g* = 0.80 needs **calendar lag** | Keep transfer; enqueue delayed due |
| C10 | PI / input flood are “nice classroom ideas” not core for this product | **REFUTE ranking** | Shintani: large PI effects on interpretation; A1 form errors (*ser/estar*, object pronouns later) are classic PI targets | Structured input deserves a first-class activity type |
| C11 | Dictogloss is a top-priority A1 web activity | **PARTIAL REJECT as full form** | Reconstruction + peer negotiation poorly maps to 1:1 chat; short **dictation / rebuild 3–6 words** is the portable core | Implement micro-dictation, not full dictogloss theatre |
| C12 | TPR requires physical classroom motion → not for web | **REFUTE as binary** | Web can do **TPR-lite**: image click, drag, A/B/C choose, “tap the boat” = non-verbal response to Spanish imperative | High A1 fit if non-verbal response path exists |
| C13 | Shadowing needs special hardware / is intermediate-only | **REFUTE** | Reviews: lower-proficiency benefits most for decoding; product already has TTS + mic | 60–90 s shadow block is cheap and code-scorable (roughly) |
| C14 | Building many single-purpose systems is OK if engineered | **SUPPORT** | User critique 2026-07-28 is correct; research-only rounds without code ownership produced depth illusion | r6 proposals must be real modules with I/O contracts |
| C15 | Chatbots already yield medium L2 effects → conversation-first is enough | **REFUTE sufficiency** | Lyu 2025-class chatbot meta (r4): medium *g* ≈ 0.6; does **not** identify optimal practice mix; novelty decay when goals thin | Medium chatbot effect ≠ complete pedagogy |

---

## 3. Evidence table (activity type → strength → citations → A1-fit)

Evidence strength scale: **S1** meta-analysis / multi-lab; **S2** multiple controlled studies / systematic review; **S3** classroom tradition + smaller studies; **S4** theory-strong, thin controlled web/AI transfer.

| Activity type | Evidence strength | Direction / magnitude | Key citations | A1 adult chat+voice fit | Code-vs-model split |
|---------------|-------------------|----------------------|---------------|-------------------------|---------------------|
| **Spaced retrieval / review sessions** | **S1 — strongest durability lever** | Spaced > massed: **g = 0.58** immediate, **g = 0.80** delayed; equal ≈ expanding | Kim & Webb 2022; Cepeda et al. 2008; Roediger & Karpicke 2006; Karpicke & Roediger 2008 | **Excellent** if conversational elicit, not flashcard UI | **Code** schedules due items + pass/fail; **model** realizes try in current topic |
| **Processing instruction / structured input** (incl. input flood + referential choice) | **S1–S2** | Large effects on interpretation; PI ≥ PB on receptive; PI ≈ PB on production | VanPatten program; Shintani 2015 (*d* ≈ 1.90 receptive in secondary reports; 42 expts / 33 studies) | **Excellent** for ser/estar, gender, tense morphology at A1 | **Code** picks form + item bank + scoring key; **model** can generate fillers only if validated against key |
| **Task-based scenarios (info-gap, single convergent exit)** | **S2** | Info-gap/jigsaw > opinion; beginner TBLT works when **input-based** allowed | Ellis 2003/2009; Long TBLT; Pica et al.; Shintani beginner work; Robinson SSARC | **Excellent** for adult persona if goals visible | **Code** owns exit predicate + role cards; **model** plays interlocutor |
| **TPR / TPR-lite (non-verbal response to Spanish)** | **S3** (classic experiments + classroom) | Strong tradition for vocab + listening + low anxiety; weaker modern meta | Asher 1966–1977; classroom TPR reviews | **High** as click/choose/gesture; **low** as full-body | **Code** presents stimulus + scores choice; **model** optional for natural command phrasing from template |
| **Shadowing / choral repetition** | **S2** (systematic reviews; EFL heavy) | Improves bottom-up listening, fluency, prosody; helps lower proficiency | Hamada line; Kadota 2019; Whitworth 2025 systematic review | **High** with existing TTS+mic; short blocks | **Code** selects clip + records attempt; scoring = optional ASR similarity; **model** not required for core loop |
| **Dictation / micro-reconstruction** (dictogloss-lite) | **S2–S3** | Supports form noticing, multiword retention vs passive comprehension | Dictogloss tradition (Wajnryb; Swain); dictation multiword studies (e.g. Yu 2025-class) | **Medium–high** for 1–2 sentence A1; full multi-party dictogloss **poor** in 1:1 | **Code** holds target string + edit-distance score; **model** may produce pack-legal sentences offline into bank |
| **Input flood (dense target forms in meaning text)** | **S2–S3** | Helps noticing/frequency; weaker alone than PI with structured response | Input enhancement/flood literature; Conti practitioner synthesis; enhancement studies mixed | **High** as 60–90 s listen/read block tied to target form | **Code** selects flooded micro-text from pack bank; **model** optional generator with form-count constraints |
| **Narrow reading / listening** | **S2** | Same-theme texts boost vocab encounters, lower load | Krashen narrow reading; Chang 2019/2021 | **Medium** at A1: needs **graded micro-texts**, not series novels | **Code** picks theme cluster from pack + hooks; **model** can draft then human/pack-gate |
| **Free conversation + reactive FonF** (current default) | **S2 for FonF family; S4 as complete mix** | Medium chatbot L2 effects overall; FonF reactive breaks supported; **not** a durability architecture alone | Long FonF; Lyu-class chatbot meta (r4); product modes | **High engagement vehicle**; **insufficient** alone for A1 completeness | **Code** modes today; still missing phase authority |
| **Full TPRS multi-week story curriculum** | **S3** (practitioner-heavy) | Popular; limited high-quality comparative meta vs other methods | TPRS practitioner literature; small comparative studies | **Medium** fit to 10–20 min sessions; heavy content authoring | Prefer **narrow stories + TPR-lite + flood** over full TPRS stack |
| **Open multi-goal “scene” chat without scoring exit** | **S3–S4 as task** | Exit idea good; opportunistic multi-goal weak | Pica typology; r4 adjudication | **Medium** as flavor; **weak** as primary practice | Must tighten to single-exit tasks |

**Adversarial bottom line on conversation-first:**  
For adult **false beginners**, conversation + FonF is a defensible *core vehicle*. For **true zeros**, high anxiety, and **between-session retention**, conversation-first **without** scheduled retrieval + structured input + input-safe tasks is **pedagogically incomplete**. The evidence does **not** say “delete chat.” It says **chat is one activity class among several**, and code—not the model’s mood—must allocate time.

---

## 4. Recommended session architecture (~10–20 min)

### 4.1 Default 15-minute mix (false-beginner adult)

| Phase | Minutes | Share | Activity class | Purpose |
|-------|---------|-------|----------------|---------|
| **0. Open / affect sample** | 0.5–1 | ~5% | Soft conversation OR input-safe if anxiety high | Warmth + capture energy/anxiety proxies |
| **1. Retrieval openers** | 2–3 | **~15–20%** | 1–3 due re-encounters (conversational or micro-choice) | Spacing (Kim & Webb); warm prior forms |
| **2. New input / structured input** | 3–5 | **~25–30%** | PI-style choice, input flood micro-text, association+image, TPR-lite | Form–meaning before free production |
| **3. Convergent task** | 4–6 | **~30–35%** | Single-exit info-gap scene | Meaning-primary production under goal |
| **4. Free / stretch conversation** | 2–3 | **~15–20%** | Conversation + soft cf_recast; optional transfer | Fluency, hooks, next_best stretch |
| **5. Close / enqueue** | 0.5–1 | ~5% | Celebrate task done; write due intervals | Durable sheet update |

**Ratios (of active teaching time, excluding chrome):**

| Bucket | Target share | Arithmetic for 15 min active |
|--------|--------------|------------------------------|
| **Retrieval** | **15–25%** | 0.15×15 = **2.25 min** → 0.25×15 = **3.75 min** |
| **New structured input** | **25–35%** | 0.25×15 = **3.75** → 0.35×15 = **5.25 min** |
| **Goal-directed practice (task)** | **30–40%** | 0.30×15 = **4.5** → 0.40×15 = **6.0 min** |
| **Free production / stretch** | **15–25%** | 0.15×15 = **2.25** → 0.25×15 = **3.75 min** |

Check: midpoints 20% + 30% + 35% + 20% = **105%** → use **20 / 30 / 35 / 15** = **100%**.  
For **10 min:** scale linearly → retrieval **2.0**, input **3.0**, task **3.5**, free **1.5**.  
For **20 min:** retrieval **4.0**, input **6.0**, task **7.0**, free **3.0**.

### 4.2 Sequencing rules (deterministic)

1. **Hard safety first:** `comprehension_repair` and critical gate faults still preempt phase (integrate r2).  
2. **Due retrieval before new content** if `due_count ≥ 1` and energy ≠ collapsed — testing effect wants retrieval when slightly cold.  
3. **Structured input before forced try** when: blank/near-blank sheet, form `conf < 0.35`, or anxiety/WTC_proxy high.  
4. **One primary task exit per session** (or per 12-min block). Secondary goals only after exit.  
5. **Hard form breaks** (`form_focus`) count against hard-break budget *inside* task/free phases; do not cancel retrieval phase.  
6. **Transfer** remains **within-session** near-transfer after success; **also** enqueue `next_due` (r3 MVP).  
7. **Interleave:** if ≥2 due items, do **not** block on only the hottest error (Nakata & Suzuki 2019 delayed-test logic).

### 4.3 Adaptation to sheet state

| Sheet / affect signal | Adaptation |
|----------------------|------------|
| `due_reencounters ≥ 3` | Expand retrieval to **25%**; shrink free to **10%** |
| Many `error_patterns` active (e.g. ≥2 hot) | Insert **PI structured-input** block on top pattern before task |
| `affect.energy == limited_time` | Skip free stretch; **retrieval 30% + micro-task 40% + soft close 30%**; no hard form_focus |
| High anxiety / low WTC_proxy (short replies, English escape, mic abort) | **Input-heavy path:** TPR-lite + PI choice + model-heavy; teach-move **try optional** |
| High boredom_risk | Force task content from **profile hooks**; new theme narrow-listen 60 s |
| Streak of successes on form | Prefer **transfer + enqueue**; do not re-drill same line |
| Blank sheet / placement | Phases 1–2 only: placement probes as **input-based choices**, not open try barrage |

### 4.4 What this is *not*

- Not a 45-minute classroom lesson clone.  
- Not Anki with Spanish wallpaper.  
- Not abandoning conversation — **demoting it from “the system” to “one phase.”**

---

## 5. Single-purpose subsystem proposals (ranked by impact / effort)

> Authority exceeds perception: each subsystem is a **service with a data contract**. The tutor model is a **performer**, not a planner.

### Rank 1 — `RetrievalScheduler` (ship r3 for real)

| Field | Spec |
|-------|------|
| **Name** | `RetrievalScheduler` |
| **Purpose** | Decide *which* forms/can-dos/lexemes are due and record retrieval outcomes so durability is code-owned. |
| **Inputs** | Ability sheet entries (`skills`, `grammar`, `lexicon`, `error_patterns`); clock (`today`); optional `max_due` (default 3); last session outcomes. |
| **Outputs** | `DueItem[]` `{id, kind, form_or_can_do, next_due, interval_days, prompt_hint}`; `ScheduleUpdate` after outcome `{id, success, new_interval, new_next_due}`. |
| **Interval policy (code)** | On success: if `successive_successes==1` → `interval=1`; `==2` → `3`; else `min(interval*2, 14)`. On fail: `interval=1`, `next_due=tomorrow`. Arithmetic vs Cepeda week-horizon: first gaps **1 d** and **3 d** sit in **1.4–2.8 d** band (0.20–0.40 × 7). |
| **Code owns** | Due computation, decay/stale flags, enqueue after transfer success, cap per session, progress-score **retrievability** input. |
| **Model owns** | Natural Spanish elicit that targets the due form *in current topic* (no flashcard chrome). |
| **Plugs into** | `select_mode` / new session **phase** layer: soft mode `reencounter` or phase-1 activity; sheet fields `next_due`, `interval_days`, `successive_successes` (wire dead `last_seen`). Supersedes orphaned `lesson_flow.due_items` **or** ports it into character_sheet. |
| **Success criterion** | Unit: success sets `next_due = today+1`; fake clock +2 d → item due. Behavioral: across 2 simulated calendar days, ≥1 due elicit appears without requiring `form_focus`. Pilot: delayed (48–72 h) re-elicit accuracy **≥ +15 percentage points** vs no-scheduler control on same item set. |
| **Impact / effort** | **Very high / medium** — highest science ROI (*g* ≈ 0.80 class). |

### Rank 2 — `SessionPhaseController`

| Field | Spec |
|-------|------|
| **Name** | `SessionPhaseController` |
| **Purpose** | Time-box the practice mix (retrieval → input → task → free) so conversation cannot consume 100% of the session by default. |
| **Inputs** | `session_minutes` (10|15|20); sheet snapshot (due_count, blank?, affect); profile hooks; clock/turn index; last phase outcomes. |
| **Outputs** | `PhasePlan` `{phases: [{name, target_turns_or_seconds, activity_type, item_refs}]}`; `PhaseTick` each turn `{current_phase, remaining, force_advance?}`. |
| **Code owns** | Phase transitions, ratio enforcement, affect/due adaptations (§4.3), logging of phase adherence. |
| **Model owns** | Realization inside the *current* phase’s activity contract only. |
| **Plugs into** | Runs **above** `select_mode`: phase proposes activity class → mode runtime maps to mode + activity payload. Hard repair still preempts. |
| **Success criterion** | In 15-min simulated sessions, free-conversation phase ≤ **25%** of turns when due_count≥1; retrieval phase non-empty when due exists. Log metric `phase_adherence ≥ 0.80` (time in planned phase / planned). |
| **Impact / effort** | **Very high / medium–high** — makes all other activities schedulable; without this, new activities remain opportunistic like scenes. |

### Rank 3 — `StructuredInputEngine` (PI / TPR-lite / choice)

| Field | Spec |
|-------|------|
| **Name** | `StructuredInputEngine` |
| **Purpose** | Deliver form–meaning mapping trials (choose referent, choose correct form in meaning context, TPR-lite command→click) with **deterministic scoring**. |
| **Inputs** | Target `form_id` or `error_pattern`; pack inventory; teach image ids; difficulty; response channel (click / A-B-C / short text). |
| **Outputs** | `InputTrial` `{stimulus_es, options[], correct_key, media_ref}`; `TrialResult` `{correct: bool, rt_ms?, raw_response}`. |
| **Code owns** | Item selection, correct keys, scoring, master-until-N policy (e.g. 3/4 correct before production try), no English gloss wall. |
| **Model owns** | Optional natural paraphrase of stem **only if** constrained to pack + validated; default = templated Spanish from pack banks. |
| **Plugs into** | Phase 2; can feed `association` / replace weak free `try` for zeros; updates sheet conf via hard observer on **receptive** evidence (new bump path). Integrates r2 (comprehension) and r5 (images). |
| **Success criterion** | Pack unit tests: 20 ser/estar trials auto-score 100% against keys. Learner pilot: interpretation accuracy on held-out items **≥ +20 pp** after one PI block vs conversation-only control (same time on task). |
| **Impact / effort** | **High / medium** — needs item banks + UI response widgets (not only chat text). |

### Rank 4 — `ConvergentTaskRuntime` (scene → real task)

| Field | Spec |
|-------|------|
| **Name** | `ConvergentTaskRuntime` |
| **Purpose** | Run one primary task with info-gap roles and a **machine-checkable exit predicate**. |
| **Inputs** | Scene JSON extended: `{primary_exit, tutor_private_info, learner_must_obtain, success_rubric}`; sheet can-dos; profile hooks for content bind. |
| **Outputs** | `TaskState` `{status: open|done|abandoned, evidence[], turns_on_task}`; UI line “Today’s task: …”. |
| **Code owns** | Exit evaluation (keywords/slot fill/can-do markers), prevent multi-goal drift, celebrate-done event, bind progress header to **task completion events** (not only mean conf). |
| **Model owns** | Role-play as captain/clerk holding private info; must not leak answer; Spanish realization. |
| **Plugs into** | Phase 3; upgrades `course_packs/.../scenes/*.json`; mode may stay `conversation` with `activity=convergent_task` payload. Integrates r4 task design. |
| **Success criterion** | Scripted sims: exit completion rate **≥ +25%** vs current opportunistic scenes; mean turns-to-exit **≤ −20%**; gate fault rate not worse. |
| **Impact / effort** | **High / high** — content + exit scoring design heavy; highest *product* feel payoff after scheduler. |

### Rank 5 — `MicroListeningLab` (dictation + shadowing)

| Field | Spec |
|-------|------|
| **Name** | `MicroListeningLab` |
| **Purpose** | 60–120 s single-purpose listening practice: TTS play → shadow **or** type/rebuild short A1 string; score and log. |
| **Inputs** | Pack-legal target utterance; TTS audio; mode `shadow|dictation`; ASR text or typed text. |
| **Outputs** | `LabResult` `{type, target, hypothesis, score_0_1, phoneme_or_edit_distance}`. |
| **Code owns** | Clip selection (narrow theme / flooded form), play count limits, scoring (char/word edit distance; optional ASR), pass threshold (e.g. dictation ≥ 0.75 normalized similarity). |
| **Model owns** | None in the hot path if bank is pre-built; optional bank generator offline. |
| **Plugs into** | Phase 2 alternate or limited_time sessions; uses existing TTS/STT. Integrates r5 multimodal. |
| **Success criterion** | Unit: edit-distance scorer golden tests. Pilot: after 8 sessions with lab ON, shadow/dictation items mean score **≥ +0.15** absolute; self-report “I can catch words” **≥ +1 Likert**. |
| **Impact / effort** | **Medium–high for voice product / medium** — smaller grammar payoff than PI+retrieval but uniquely uses mic/TTS stack. |

**Explicit non-proposals (for now):** full SM-2 UI; multi-party dictogloss; full TPRS multi-week story engine; pure Duolingo drill tree. Persona forbids kids-flashcard surface; science does not require those forms first.

**Impact/effort ranking summary**

| Rank | Subsystem | Impact | Effort | Build first? |
|------|-----------|--------|--------|--------------|
| 1 | `RetrievalScheduler` | Very high | Medium | **Yes — week 1** |
| 2 | `SessionPhaseController` | Very high | Medium–high | **Yes — week 1–2** (can ship thin) |
| 3 | `StructuredInputEngine` | High | Medium | Yes — after 1–2 |
| 4 | `ConvergentTaskRuntime` | High | High | Parallel content work |
| 5 | `MicroListeningLab` | Medium–high | Medium | After scorer + TTS path stable |

---

## 6. Integration with r1–r5 (supersede / must integrate)

| Round | Status after r6 | Action |
|-------|-----------------|--------|
| **r1 Corrective feedback** | **Integrate, do not supersede** | CF timing still lives *inside* task/free phases; `cf_recast` / `form_focus` remain. Phase controller must not starve CF when error is hot. |
| **r2 Input repair** | **Integrate** | `comprehension_repair` **preempts** phase clock (safety). Structured input *reduces* repair frequency by better first encoding. |
| **r3 Retrieval & spacing** | **SUPERSEDE “research only” — BUILD** | r6 Rank-1 `RetrievalScheduler` **is** the r3 MVP. Immediate transfer stays; durability moves to due queue. Progress score must incorporate stale/due (r3 proposal 2). |
| **r4 Tasks & affect** | **Integrate + operationalize** | Convergent tasks = Rank 4. Affect → **phase/activity** actuators (anxiety → input path; boredom → hook-bound task), not labels only. |
| **r5 Multimodal** | **Integrate** | Images are stimuli for StructuredInput / TPR-lite / association; TTS/STT are I/O for MicroListeningLab — not wallpaper. |
| **Teach-move contract** | **AMEND under activities** | Allow documented exceptions: structured-input and TPR-lite turns may be **model-only or model+choice** without obligatory spoken `try`. Conversation/task phases keep model+try/recast rules. |
| **Mode runtime** | **Demote from “the pedagogy OS” to “realization + reactive break layer”** | New OS = PhaseController + activity engines; modes become one mapping target. |

---

## 7. What the brief / product story still MISSES

1. **Activity ≠ mode.** The brief states this; the codebase still collapses them. Until `activity_type` is a first-class logged field, evals cannot see practice mix.  
2. **Receptive evidence channel is underpowered.** Sheet bumps lean productive. PI/TPR-lite will produce mostly *clicks* — without a receptive bump path, the sheet will under-credit real learning.  
3. **UI response primitives.** Chat-only composer cannot run TPR-lite or A/B structured input well. Need **choice buttons / image hotspots** as first-class client messages — engineering, not prompt text.  
4. **Item banks are the real content debt.** PI and dictation die without pack-legal item JSON. Course pack today is prose units + 3 scenes — insufficient for Rank 3/5.  
5. **Clock and multi-day eval harness.** Spacing claims are untestable without fakeable `today` and cross-session trajectories (r3 already warned).  
6. **WTC/anxiety still untracked** (r4). Practice mix adaptation rules reference signals you do not yet compute. Minimum: behavioral WTC_proxy from latency, token length, English-escape rate, mic abandon.  
7. **Risk of “subsystem sprawl without orchestrator.”** User said many services are OK if single-purpose — true only if `SessionPhaseController` is the sole orchestrator. Do not let five engines each call the model independently.  
8. **True-zero path is still production-biased.** Placement + obligatory try is the sharpest product–evidence conflict for A1.

---

## 8. Answers to standing research questions

**Q1 — Strongest activity types for beginner L2 outcomes?**  
**A:** By evidence quality: (1) **spaced retrieval**, (2) **PI/structured input**, (3) **convergent info-gap tasks (input-safe at zero)**, (4) **TPR-lite / choice response**, (5) **shadowing + micro-dictation**, (6) **narrow micro-input**. Free conversation + reactive FonF is necessary vehicle, **not** top durability or form-mapping lever.

**Q2 — Defensible session architecture for 10–20 min?**  
**A:** Default 15-min mid ratios **retrieval 20% : structured input 30% : convergent task 35% : free 15%**, with §4.3 adaptations. Sequencing: safety repair → due retrieval → input → task → free → enqueue.

**Q3 — Code-owned vs model-performed?**  
**A:** Code owns phase, due set, item selection, exit predicates, trial keys, scores, interval math, affect→path rules. Model owns Spanish wording inside contracts and role-play without leaking task keys. **Never** let the model choose whether a due item is due.

**Q4 — Is conversation-first wrong for A1?**  
**A:** **Wrong as monopoly; right as vehicle.** For true zeros and durability, conversation-first-without-scheduler is **refuted** by spacing + beginner TBLT evidence. Do not pivot to worksheet app; **add** code-owned practice layers.

---

## 9. Build order (concrete, not shy)

1. **This week:** `RetrievalScheduler` + sheet fields + soft `reencounter` + unit tests + fake clock.  
2. **Same sprint:** thin `SessionPhaseController` (even turn-count based, not wall clock).  
3. **Next:** `StructuredInputEngine` MVP = A/B image choice for one form family (*estar* location vs *ser* identity) + receptive bumps.  
4. **Parallel content:** rewrite 3 scenes to **single primary exit** + private info slots.  
5. **Then:** `MicroListeningLab` dictation scorer on 10 pack sentences.  
6. **Eval:** extend smoke trajectories with `phase_adherence`, `due_elicit_fired`, `si_trial_scored` — not only mode names.

---

## 10. Sources (absolute pins)

- Kim, S. K., & Webb, S. (2022). The effects of spaced practice on second language learning: A meta-analysis. *Language Learning, 72*(1), 269–319. (g = 0.58 immediate / 0.80 delayed; N = 3,411; 98 ES).  
- Cepeda, N. J., Vul, E., Rohrer, D., Wixted, J. T., & Pashler, H. (2008). Spacing effects in learning: A temporal ridgeline of optimal retention. *Psychological Science*.  
- Shintani, N. (2015). The effectiveness of processing instruction and production-based instruction on L2 grammar acquisition: A meta-analysis. *Applied Linguistics, 36*(3). (42 experiments / 33 studies; large PI interpretation effects).  
- VanPatten, B. (2002/2004). Processing instruction program (input processing; structured input).  
- Roediger, H. L., & Karpicke, J. D. (2006); Karpicke & Roediger (2008). Retrieval / testing effect.  
- Ellis, R. (2003/2009); Long, M. — TBLT; Pica, Kanagy, Falodun — task typology.  
- Asher, J. (1966–1977). Total Physical Response.  
- Hamada, Y.; Kadota, S. (2019). Shadowing; Whitworth (2025) systematic review (pronunciation/listening).  
- Krashen, S. — narrow reading; Chang, A. C. S. (2019/2021) narrow reading/listening vocab studies.  
- Nakata, T., & Suzuki, Y. (2019). Interleaving vs blocking L2 grammar.  
- Prior project rounds: r3 retrieval (2026-07-26), r4 tasks/affect (2026-07-26); system-overview status 2026-07-27.

---

## 11. Bottom line (append-ready)

I **do not countersign** “modes over free chat” as a complete practice architecture. I **do countersign** conversation as the adult meaning vehicle **if and only if** code also owns **(1) spaced retrieval, (2) session phases with real ratios, (3) structured input / TPR-lite trials, (4) single-exit tasks**, with listening micro-lab as the fifth voice-native piece.

The user’s 2026-07-28 critique is correct: depth has been spent on research prose and reactive mode flavor while the highest-powered lever from r3 (**scheduler**, delayed *g* ≈ 0.80) remains unbuilt. **Stop being shy:** ship `RetrievalScheduler` and `SessionPhaseController` as real modules; treat the model as the actor, not the syllabus.

— End Grok independent research round 6 — PRACTICE MIX (2026-07-28)

---

## Adjudication — r6 (Claude, 2026-07-28)

**Core verdict ACCEPTED:** conversation is the right meaning vehicle and the wrong monopoly. The four missing code-owned layers (scheduled retrieval, structured input, convergent tasks, session phase control) are accepted as the build agenda, with the evidence ranking as stated (spacing g≈0.80 delayed is the strongest unbuilt lever; r3 is hereby superseded from "research only" to "build").

**AMEND-1 (stale input, not Grok's error):** all references to profile hooks / personalization anchors (§4.3 boredom row, task content binding) are STRUCK — personal-data capture was removed the same day this round ran (docs/reviews-personal-data-removal.md). Content binding uses the pack topic palette and the learner's ability-sheet lexicon only, until an opt-in profile design ever returns.

**Compatibility ruling:** the SessionPhaseController does NOT conflict with the frozen adaptivity architecture (docs/reviews-adaptivity-architecture.md). That review froze code authority over model perception; the phase layer extends code authority upward. Modes remain the reactive/intervention layer; comprehension_repair and critical gate faults preempt the phase clock exactly as r2 requires.

**Design law adopted from Grok's risk #7:** SessionPhaseController is the SOLE orchestrator. Activity engines never call the tutor model independently — they emit plans/trials; one realization path.

**Teach-move amendment ACCEPTED:** structured-input and TPR-lite turns may be model-only or model+choice without an obligatory spoken try; conversation/task phases keep the model+try/recast contract.

**Build order:** merged with r7 into docs/build-plan-pedagogy-engine.md. Round CLOSED — CONVERGED (one amendment for same-day staleness; no rejections).
