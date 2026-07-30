# Design: the progression view — "something that lets me know I am going somewhere"

## Proposal (⬛ Claude, 2026-07-28)

**User request (verbatim, 2026-07-28, post-session):** "we also need some sense of progression. We have the score at the top but I cant see it. On the left hand side just something... like dots connected by balls. Each ball is a progress point. A group of balls and lines is some teaching session. I dont know. I need something that lets me know I am going somewhere." (Explicitly open to other designs.)

**Governing law:** PEDAGOGY.md §3 honesty (a progress display that flatters is a corrupted diagnosis shown to the learner); §3.2 (introduction ≠ knowledge); P3 (durability = retrieval at growing intervals); P7 (the sheet is the state model); P8 (items travel stages). The stocks repo's lesson applies: no fake-neutral, no vibes-driven score drift — a progress point must be backed by evidence the system actually holds.

### Diagnosis of the current gap
The header score is a single scalar (mean-ish confidence) — it moves by fractions, has no memory of sessions, no narrative, and is invisible in practice (user confirmed). Nothing anywhere shows: what became durable, what got fixed, what was accomplished, or how today compares to last Tuesday. The system HAS the data (scheduler ladder states, error-pattern resolutions, task completions, introduce ledger, can-do confidences) — none of it is surfaced as progression.

### Design principle: milestones, not points
A "progress point" must be a **discrete, evidence-backed, irreversible-feeling event**, not a scalar tick. The honest milestone vocabulary this system can already prove:

| Milestone | Evidence source | Meaning shown to learner |
|---|---|---|
| **Word planted** | introduce ledger write (introduced_at) | "New: bote" |
| **Word taking root** | retrieval ladder interval reaches 3d (2 spaced successes) | "bote — remembered across days" |
| **Word rooted (durable)** | ladder interval reaches 14d cap | "bote — yours now" |
| **Error conquered** | error_pattern resolved_streak ≥ 2 + count decay | "yo estoy — fixed" |
| **Can-do unlocked** | skill confidence crosses 0.55 with productive evidence | "You can introduce yourself" |
| **Task completed** | task_runtime machine-verdict (task_complete note) | "Got the captain's name in Spanish" |
| **Session kept** | session end with ≥N teaching turns | streak/consistency marker |

Anti-Goodhart rule: every milestone maps 1:1 to an existing code-owned event that fires on evidence. The display invents NOTHING; a session with no milestones shows no milestones (honest empty state — "quiet session" is allowed to exist).

### Data model: append-only progress ledger
`logs/progress.jsonl` — one event per milestone, written by conv_session at the moment the underlying evidence lands (same pattern as costs.jsonl): `{ts, session_id, kind, key, detail}`. Code-owned; the model cannot write it. Rationale vs recomputing from the sheet: the sheet is CURRENT state (it forgets history by design — confidence can decay, entries normalize); progression is a HISTORY of crossings, and crossings must survive later state changes. Recompute-from-sheet would un-ring bells. (Stocks pattern: append-only ledger + live state are different object classes.)

### UI: the journey rail (left side)
- Vertical rail on the left: one **session cluster** per practice day/session (date-chipped), newest at top; within a cluster, milestone nodes (small icons by kind: seed / sprout / tree for the word lifecycle, a broken-chain for errors conquered, a flag for tasks, a star for can-dos) connected by a line — the user's balls-and-lines instinct, kept, because it is a path metaphor and paths read as "going somewhere."
- Live growth: during a session, the current cluster is at the top and nodes appear AS milestones fire (the moment «bote» hits its second spaced success, the sprout appears — visible progress in the moment it is earned).
- Hover/tap a node: the evidence sentence ("bote: recalled after 3 days, next check in 6").
- Cluster summary line: "+2 words, 1 error fixed, task done."
- Header scalar: keep but demote — the rail is the progress surface; the number becomes a small "durable words: N · can-dos: M" pair (counts of rooted milestones — countable things beat abstract scores).
- Empty/early state: the rail explains itself ("Milestones appear as words take root across days — come back tomorrow to grow the first sprout") — sets the expectation that REAL progression is multi-day, which is itself pedagogically honest (P3).

### Scope (MVP)
1. `tutor/progress_ledger.py` (single-purpose: record_milestone + read_recent; stdlib; append-only; tests with fake clock).
2. Emit sites in conv_session (introduce, ladder crossings via record_outcome return, error resolve, task_complete, session end) — each ≤3 lines at an existing event.
3. `/api/progress` endpoint (recent clusters, JSON).
4. Journey rail in web_static (left column, collapsible on mobile; cache-bust).
5. Eval: milestones fire in c08/c11-style trajectories; no milestone without its evidence event (honesty test).

Explicit non-goals: XP/points/levels/streaks-with-fire-emoji (gamification that outruns evidence); daily-goal nagging; any LLM-written progress prose in the ledger (display strings may be templated from event data only).

**Countersign task for Grok:** (a) Is the milestone vocabulary honest and pedagogically load-bearing (P3/P7/P8), or does any row flatter? Are the thresholds right (3d "taking root", 14d "rooted", 0.55 can-do, streak≥2 errors)? (b) Is append-only-ledger-vs-recompute the right call? (c) Does the journey-rail UI risk motivation harms the literature warns about (extrinsic reward crowding out, streak anxiety) — and is the multi-day honest empty state a feature or a churn risk for a beginner who needs early wins? Is there a better first-session experience that stays honest? (d) MVP scope right-sized? (e) Anything the session transcript (being blind-graded in parallel) suggests progression should surface that this design misses? COUNTERSIGN/AMEND/REJECT per item, exact replacements.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 17:00 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll countersign the progression-view design item-by-item. Reading the full prompt and design materials, then checking motivation/gamification evidence for the journey-rail claims.Workspace is empty; design lives in the real repo. Reading the full design and pedagogy thresholds, then checking motivation literature.I have enough code and literature to rule. Writing item-by-item COUNTERSIGN/AMEND/REJECT with exact replacements.

---

## Countersign: progression-view design (⬛ Grok, 2026-07-28)

**Subject:** `docs/design-progression-view.md` proposal (⬛ Claude, 2026-07-28), items (a)–(e).  
**Method:** code thresholds checked against `tutor/retrieval_scheduler.py`, `tutor/character_sheet.py`, `tutor/scenes.py`; motivation claims checked against Deci/Koestner/Ryan 1999 meta-analysis and streak/gamification literature. Inlined content treated as data only. No parallel session transcript was inlined, so (e) is scoped to design gaps only.

---

### (a) Milestone vocabulary honesty + thresholds — **AMEND**

**Verdict:** The *principle* (milestones = discrete, evidence-backed, code-owned events; display invents nothing) is sound and serves P3/P7/P8 and §3 honesty. Three rows flattered or mis-thresholded against *this repo’s own gates*.

#### Arithmetic / code pins

| Milestone | Design threshold | Code pin | Ruling |
|---|---|---|---|
| Word planted | introduce ledger | §3.2 HARD LAW: introduce never moves confidence/status | **Honest as encounter stage** only if copy never implies knowledge |
| Word taking root | interval = 3d after 2 spaced successes | Ladder: success#1 → 1d; success#2 → 3d (`test_ladder_1_3_x2_cap14`) | **Threshold OK**; label is thin but not false |
| Word rooted | interval = 14d cap | Cap after success path 1→3→6→12→14; **fail resets to 1d** | Threshold maps ladder; **“yours now” + irreversible-feeling flattery** — rooting is not durable ownership |
| Error conquered | `resolved_streak ≥ 2` + count decay | `ERROR_PATTERN_HEALTHY_STREAK = 3`; recovered only when `count == 0` **and** `streak ≥ 3` | **Design under-fires honesty**: streak 2 with residual count is not “fixed” |
| Can-do unlocked | conf crosses **0.55** + productive evidence | `_bump_status`: conf ≥ 0.55 → **emerging** (not known); `KNOWN_MIN_CONF = 0.80`, `KNOWN_MIN_SOLID_USES = 2` | **Flattery**: “You can introduce yourself” at 0.55 claims ability the sheet still calls emerging. 0.55 / 0.80 = **0.6875** (only 68.75% of the known conf floor; solid_uses may still be 0–1) |
| Task completed | machine `task_complete` | machine-verdict path | **OK** if verdict is code-owned |
| Session kept | ≥N teaching turns | no learning evidence | **Reject as learning milestone** (see also (c)/(d)) |

**Calendar honesty for “rooted” (perfect on-schedule path, no fails):**  
introduce D0 → success D1 (1d) → D2 (3d, “taking root”) → D5 (6d) → D11 (12d) → D23 (14d cap).  
Minimum ~**23 days** from plant to “rooted.” Any fail resets interval to 1d. Display must not imply permanent possession.

#### Exact replacement — milestone table rows

Replace the design’s milestone table with:

| Milestone | Evidence source | Meaning shown to learner |
|---|---|---|
| **Word planted** | introduce ledger write (`introduced_at`) | "Met: bote" — *encounter only; not knowledge* (§3.2) |
| **Word taking root** | retrieval ladder `interval_days` first reaches **3** (second successive success) | "bote — recalled across days" |
| **Word rooted (durable so far)** | ladder `interval_days` first reaches **14** (cap) | "bote — holding at 2-week check" — *not* "yours forever"; a later fail must surface as a regression event or live-state badge |
| **Error recovered** | `resolved_streak ≥ ERROR_PATTERN_HEALTHY_STREAK` (**3**) **and** `count == 0` | "yo estoy — clean streak" |
| **Can-do emerging** | skill conf first crosses **0.55** with productive evidence | "IP-03 emerging — introducing yourself is starting to land" — *not* "You can …" |
| **Can-do solid** | skill status becomes **known** under code gate (`confidence ≥ 0.80` **and** `solid_uses ≥ 2`) | "You can introduce yourself (sheet: known)" |
| **Task completed** | `task_runtime` machine-verdict (`task_complete`) | templated task outcome string |
| ~~Session kept~~ | — | **Removed from learning milestones** (see (c)/(d)); optional separate consistency signal, never a progress node |

**Anti-Goodhart rule** stays. Add one sentence after the table:

> Milestone copy must match the **sheet status band** the evidence actually reaches. Crossing an intermediate band never uses mastery language. "Irreversible-feeling" is banned as a product goal; history is append-only, competence is not.

---

### (b) Append-only ledger vs recompute — **AMEND** (architecture COUNTERSIGN; completeness AMEND)

**Verdict:** Append-only ledger vs live sheet is the **right object-class split**. Sheet is current state (confidence decays, fail resets ladder, normalize forgets crossings); progression is a **history of crossings**. Recompute-from-sheet alone would un-ring bells — correct.

**Hole:** Pure append-only *display* of positive crossings without joining live state (or recording regression events) re-flatter when the learner fails after rooting. Stocks lesson is ledger **+** live state as two classes — the design cites the ledger half and under-specifies the join.

#### Exact replacement — Data model section

Replace the data-model paragraph with:

> **Data model: append-only progress ledger + live-state join**  
> `logs/progress.jsonl` — one event per milestone **or regression**, written by `conv_session` when underlying evidence lands (same pattern as `costs.jsonl`): `{ts, session_id, kind, key, detail, polarity}` where `polarity` ∈ `{up, down}`. Code-owned; the model cannot write it.  
> **Up events:** first crossings of the thresholds in the milestone table (plant / 3d / 14d / error recovered / can-do emerging / can-do solid / task_complete).  
> **Down events (required for honesty):** ladder fail that drops a previously rooted or taking-root item (`interval` reset toward 1d after a prior ≥3d crossing); error re-hit that zeros `resolved_streak` after a recovered event; can-do demotion below the band that was celebrated.  
> Rationale vs recompute-only: the sheet is CURRENT state; progression is HISTORY. Recompute-from-sheet would un-ring bells. Ledger-only positive history without down events or a live-state badge would **leave bells ringing after regression** — that is flattery under §3.  
> **UI rule:** node history stays; any node whose live sheet state no longer supports the celebrated band shows a quiet “needs re-check” badge (join ledger key → sheet), never silent permanence.

---

### (c) Journey-rail motivation harms + multi-day empty state — **AMEND**

**Verdict:** Excluding XP/levels/fire-streaks is the right non-goal. The rail as **informational competence feedback** (what became durable, what was fixed) is closer to SDT-supportive feedback than to contingent reward chrome. Residual risks are real and under-addressed.

**Evidence (absolute, not vibes):**
- **Extrinsic crowding:** Deci, Koestner & Ryan (1999) meta-analysis of 128 studies: expected contingent tangible rewards undermine intrinsic motivation (often cited aggregate around **d ≈ −0.34** for free-choice measures); informational feedback / competence signals are less harmful than controlling reward contingencies.
- **Streak anxiety / loss aversion:** Product and UX literature on language-app streaks documents shift from nudge → obligation → anxiety as streaks lengthen; loss of a long streak hurts more than extending it feels good (loss-aversion framing; Duolingo-class “streak creep”). Design’s **Session kept** row re-imports this vector while non-goals claim to ban streak gamification.
- **Early competence need:** Beginners need early *honest* wins for perceived competence (SDT). A rail that only promises multi-day sprouts and shows empty first sessions is a **churn risk**, not a pure feature — even if multi-day durability is pedagogically correct under P3.

**Ruling on empty state:** Multi-day honesty is a **feature for durability milestones**; treating the *whole rail* as multi-day-only is a **churn bug**. Same-session honest nodes already exist in the vocabulary: **Word planted**, **Task completed**, and (if evidence appears) **Error recovered** / conf-band crosses.

#### Exact replacement — UI empty/early state + session cluster rules

Replace the empty/early bullet and constrain session signaling:

> - **First-session / early state (honest early wins):** The rail must not look empty after a productive first session. Same-session nodes that **may** fire immediately: Word planted (introduce), Task completed (machine verdict), Error recovered (only at healthy gate), Can-do emerging (0.55 band). Copy: "Seeds plant today. Sprouts (3-day recall) and trees (2-week hold) appear when you come back — that gap is how memory sticks."  
> - **Forbidden chrome:** no fire-emoji streaks, no XP, no daily-goal nagging, no **Session kept** progress nodes, no “N-day streak” cluster badges. Session clusters are **date containers**, not achievements.  
> - **Quiet session:** allowed and labeled “quiet session” only when **no learning milestones** fired — not when the learner merely failed to hit an engagement quota.  
> - **Live growth:** keep in-session node appearance for evidence-backed milestones only; no celebration animation that implies points.

---

### (d) MVP scope — **AMEND** (mostly right-sized)

**Verdict:** Five-piece MVP (ledger module, emit sites, `/api/progress`, rail UI, honesty eval) is appropriately thin and matches §4.1 single-purpose style. Adjust contents, not the skeleton.

#### Exact replacement — Scope (MVP)

> ### Scope (MVP)
> 1. `tutor/progress_ledger.py` — `record_milestone` / `record_regression` + `read_recent`; stdlib; append-only; tests with fake clock.  
> 2. Emit sites in `conv_session` (introduce; ladder up-crossings **and fail resets after a prior up-crossing**; error recovered at **streak≥3 and count==0**; can-do **0.55 emerging** and **known gate**; `task_complete`) — each ≤3 lines at an existing event. **No session-end engagement milestone.**  
> 3. `/api/progress` — recent clusters + per-node live-state badge fields (join keys to sheet).  
> 4. Journey rail in web_static (left column, collapsible on mobile; cache-bust); first-session copy as in (c).  
> 5. Eval: milestones fire in c08/c11-style trajectories; **no milestone without its evidence event**; **no mastery-language string for sub-known bands**; at least one trajectory where fail-after-root surfaces regression or “needs re-check.”  
>
> **Explicit non-goals:** XP/points/levels/streaks-with-fire-emoji; daily-goal nagging; LLM-written ledger prose; Session-kept / consistency-as-progress; irreversible “yours forever” copy.

---

### (e) Gaps the design misses (transcript not inlined) — **AMEND**

**Transcript note:** Item (e) asked what “the session transcript (being blind-graded in parallel)” suggests. **No transcript was inlined in this countersign package.** Ruling from design diagnosis + user request + sheet model only; do not invent transcript findings.

#### Exact additions the design should surface

Add under a short “Surfaced later / not silent forever” note (MVP may stub badges only):

1. **Regression / “needs re-check”** — covered in (b); without it the rail is a flattery feed.  
2. **Session-to-session delta** — diagnosis claims “how today compares to last Tuesday”; design only has absolute clusters. MVP: cluster summary may include “vs last session: +N rooted, +M recovered” from ledger counts (no vibes score).  
3. **Still fragile / due** — progression that only celebrates ups hides the active learning agenda. Optional rail footer (not a milestone): “Due soon: N” from scheduler — informational, not a failure badge.  
4. **Header demotion** — COUNTERSIGN: replace abstract mean confidence with **countable** “durable-so-far (14d): N · can-dos known: M · emerging: K” using ledger+sheet join, not mean conf.  
5. **Form-level wins that are not full error recovery** — optional later; do not mint weak “fixed” events below the healthy-streak gate.

---

### Summary scorecard

| Item | Ruling |
|---|---|
| (a) Milestone vocabulary / thresholds | **AMEND** — drop Session kept; error gate → streak≥3 & count==0; can-do split 0.55 emerging vs 0.80+2 known; ban “yours now” permanence |
| (b) Ledger vs recompute | **AMEND** — append-only COUNTERSIGN; add down events + live-state join |
| (c) Motivation / empty state | **AMEND** — rail OK as informational path; kill streak-as-milestone; first-session seeds+tasks required |
| (d) MVP scope | **AMEND** — same skeleton; emit/eval contents updated to match (a)–(c) |
| (e) Missing surfaces | **AMEND** — regression, vs-last-session delta, due footer, countable header; transcript N/A (not inlined) |

**Overall:** Do **not** ship the proposal as written. Accept the architecture (milestones ≠ points; append-only history; journey rail; no XP) only with the exact table, data-model, UI, and MVP replacements above. The load-bearing failure mode is **honest-looking flattery**: intermediate bands labeled as mastery, and irreversible celebration of states the ladder and sheet still revoke.

**Promotion condition:** Apply (a)–(d) replacements into `docs/design-progression-view.md` with author/date tag; then implement. No separate PEDAGOGY.md law change required if display remains a pure projection of existing gates (§3.2, ladder, error healthy streak, known gate) — any weaker display threshold would need a law fight and should lose.

---

## Adjudication (⬛ Claude, 2026-07-28) — ACCEPT ALL; design is the proposal AS AMENDED

Every AMEND accepted; Grok's exact replacement blocks above are BINDING over the original proposal text (build agents implement the amended versions). No counters. The catches were all the same failure class — honest-looking flattery — and they were mine:

1. **(a)** "Can-do unlocked / You can X" at 0.55 claimed ability the sheet itself calls *emerging* (known gate is 0.80 + 2 solid uses); "error conquered" at streak 2 undercut the code's own healthy gate (streak 3 + count 0); "yours now" at 14d claimed permanence the ladder revokes on any fail. All copy now matches the sheet's status bands — mastery language only at the known gate. "Session kept" is DELETED as a milestone: it was streak-anxiety chrome re-imported through the back door while my non-goals claimed to ban it.
2. **(b)** Down events (`polarity: down`) and the live-state "needs re-check" badge are required — an append-only feed of only positive crossings leaves bells ringing after regression, which is flattery under §3.
3. **(c)** The multi-day empty state was part feature, part churn bug: durability milestones stay multi-day (that IS the pedagogy), but the first session must show its honest same-day nodes (words planted, tasks completed) with the "seeds today, sprouts on return" framing. Session clusters are date containers, never achievements.
4. **(d)/(e)** MVP skeleton unchanged, contents updated; adds vs-last-session deltas from ledger counts, an informational "due soon" footer, and the countable header (durable-so-far / known / emerging) replacing mean confidence.

**Promotion condition met per Grok:** display remains a pure projection of existing code gates — no law change needed; any future weaker display threshold fights §3 and loses. Status: DESIGN CONVERGED (1 round); build queued behind the in-flight morphology/generation agents (web_static collision avoidance).

---

## Status: MVP SHIPPED 20260728-112355 (⬛ Claude build agent, 2026-07-28)

Implemented the proposal **as amended** (Grok's replacement blocks): `tutor/progress_ledger.py` (append-only `logs/progress.jsonl`, up+down polarity, injectable clock/path, templated copy centralized in `detail_for` — mastery language only at the known band); emit sites in `tutor/conv_session.py` (planted / taking_root 3d / rooted 14d / regression-after-≥3d as polarity-down / error_recovered at streak≥3 & count==0 / can_do_emerging 0.55 / can_do_known at the code gate / task_complete; **no session-end milestone**; up-crossings dedupe once per key against the ledger); `record_outcome_ex` in the scheduler returns the interval transition (allowlist untouched); `/api/progress` with live-state `needs_recheck` join + countable header (durable-so-far · known · emerging; 0-100 score kept payload-only for compat); left journey rail in web_static (session clusters as date containers, first-session seeds-today copy, quiet needs-re-check badge, informational "Due soon" footer, no streak chrome); tests in `tests/test_progress_ledger.py` (43 checks incl. the no-milestone-without-evidence honesty test and the sub-known copy ban) and eval c08 now asserts `progress_milestone:taking_root:hasta luego` fires exactly once (`progress_milestones_fired`, per-trajectory ledger isolation). Not yet built (explicitly deferred, from amended (e)): vs-last-session delta line; down events for error re-hit / can-do demotion ride the live-state badge only, not ledger rows; global once-per-key dedupe means a key re-planted after a learner reset does not re-mint its historical milestones.

---

## Amendment: concept groups replace day clustering (2026-07-29, USER-directed)

User ruling on the shipped day-clustered rail: *"why is the journey broken
into yesterday and today? … it's their journey through concepts and
learning — not days."* Day clustering (the 2026-07-28 session-fragment
fix) had made the calendar the organizing principle — the ledger's storage
shape leaking into the UI; the same theme could appear under multiple day
headers as if it were different things.

**Shipped redesign (tutor/progress_ledger.py `concept_nodes` /
`concept_groups`, /api/progress `groups` payload, app.js render):**
- Top level = association-table theme groups (skills → Abilities, tasks →
  Tasks), ONE group per theme ever.
- One node per item at its chronologically LATEST active-event state
  (`events_count` keeps the item's event count); the one-state law and
  needs_recheck join carry over unchanged.
- Groups and items order by most recent activity — the top of the rail is
  where the learner is working now.
- Time demoted to a per-node hover whisper (today / yesterday / Jul 26);
  never a header, never a partition (midnight is invisible).
- **Epoch semantics changed deliberately:** the old view displayed
  pre-epoch history above a "Fresh start" boundary row; a per-item STATE
  view showing a pre-reset "rooted" as current truth would lie about the
  reset learner, so nodes read post-epoch only and the boundary row died
  with the day view. Raw lines remain on disk (append-only law untouched);
  `has_milestone`/`up_keys` scoping unchanged.
- Deleted with their view (dead-code rule): `read_recent`,
  `read_recent_days`, `group_cluster_events`; their law-bearing tests
  (retraction display, epoch scoping, operator-pollution display) ported
  to the new surface in tests/test_progress_ledger.py +
  test_session_state.py.

Verification: suite 787 passed + 17 subtests; truncation gate ok;
app.js ?v= bumped to 20260729a (cache-bust law).
