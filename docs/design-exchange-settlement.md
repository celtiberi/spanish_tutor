# Design: exchange settlement — peripherals render projections, never the agenda

**Opened:** 2026-07-29 · **Author:** ⬛ Claude · **Status:** countersign round pending
**User mandate:** "all of the parts are out of sync … a global state gets dirty quick — what are the more elegant modern solutions?" → derived state, not stored state.

## The disease (three incidents, one class)

| Incident | Peripheral | Its master | The conversation was about |
|---|---|---|---|
| café image (2026-07-29, session 195728) | teach image | scene agenda (`scene_goal:boat_likes` → `image_concept: cafe`, attached PRE-call) | learner's house in Antigua Guatemala |
| me llamo morphology pin (same session) | morph card | sheet `next_best` (IP-03 fallback) | ser + gender agreement (mi casa es pequeño) |
| Yesterday/Today journey (2026-07-29, fixed) | journey rail | ledger storage shape | concepts (fixed separately) |

**One missing thing, not N bugs:** no code-owned answer to "what is this
conversation touching RIGHT NOW", so each peripheral guesses from its own
agenda slice. Second structural flaw: visible artifacts commit PRE-call,
against a reply that does not exist yet. The one post-call-checked image
path (declared images, relevance law) is the one that behaves.

## Rejected: a shared ExchangeState object

Global/shared state accretes — everything needed by >1 component lands in
the bag (USER veto; the `_turn_morph` stash on the shared mode-decision
dict is the pattern in miniature, one field old and already carrying
precedence rules).

## Proposal: derived projections + a settlement phase

Prior art: event-sourcing projections / CQRS read models; Elm/Redux/React
commit phase; ECS simulate→resolve→render. We already own the
ingredients: a typed per-turn event log (64-family catalog) and the two
realized texts.

### P-1 Projections (pure, per-consumer, turn-scoped)

"Relevance" is a PURE FUNCTION of the realized exchange — never a stored
record. Each consumer owns a narrow derive function + frozen view:

- `image_relevance(learner, reply) → frozenset[concept]` — table keys /
  asset concepts surface-present in either text (textnorm boundaries +
  accent fold: concept `cafe` must match reply «café»).
- `card_engagement(learner, reply, events) → CardView | None` — the form
  in play, priority: learner error (incl. new agreement detector) >
  recast > learner meta-question/how-say > introduction (INTRODUCED /
  FIRST_SEEN events) > None. Subsumes today's two stash paths + adds the
  recast trigger (morphology round, user-approved, folded in here).
- `panel_focus(learner, reply, events) → FocusView` — what the async
  focus rail may enrich against.

**Input law (signature-enforced):** derive functions take ONLY
`(learner, reply, events)`. No `next_best`, no scene, no phase, no sheet
agenda in the parameter lists — a test pins the signatures. Agenda
systems keep shaping INSTRUCTIONS (pre-call); they become syntactically
unable to shape PIXELS.

### P-2 Settlement stage (the commit phase)

Pipeline becomes: agenda → instructions → generation → **settlement** →
gate → record → render.

- Pre-call visible artifacts (mode/scene image, fallback image, R-B
  introduce image) demote to **candidates**. They stay visible to the
  MODEL in instructions (R-B needs the model to know its image is
  attached — stage_introduce_render's deferred render is preserved).
- `stage_settlement` (new, first post-generation stage): confirms each
  candidate against its projection or DROPS it. Confirmation for an
  image: concept ∈ image_relevance(learner, reply). The café image dies
  here (café in neither text); an R-B image whose key the reply omitted
  dies here — coherent with the introduce lapse it already causes.
- Output = `TurnRender` — the settled, immutable render record for THIS
  turn (confirmed images, card view, drops with reasons). Written ONCE by
  settlement, read-only downstream (response assembly + repaints). This
  is a RESULT, not shared state: nothing writes to it after settlement;
  it dies with the turn. Replaces the `_turn_morph` stash.
- **No silent drops** (images-stuck-on-static lesson): every drop emits a
  typed event `render_dropped:<kind>:<concept>` (log-only family).

### P-3 Bookkeeping moves to confirmation time

`pedagogy_memory.note_image` / `images_shown` currently fire at ATTACH —
under settlement they fire only for CONFIRMED images (an image the
learner never saw must not exclude that concept from future
introduction). Same for image cost notes tied to display.

## Consumer inventory (the migration)

| Consumer | Today | After |
|---|---|---|
| stage_mode_image | attaches scene/mode image pre-call, notes it shown | produces candidate; settlement confirms/drops |
| stage_fallback_image | pre-call, mode-gated, partial relevance for repair only | produces candidate; ONE confirmation rule for all |
| stage_declared_image | post-call, relevance-checked | unchanged in behavior; reads image_relevance (one definition) |
| morph card (2 stashes + fallback) | stashed on shared dict; falls back to next_best/can-do silently | card_engagement projection in TurnRender; fallback renders labeled "up next", never as live |
| focus panel/enricher | reads stash + sheet | reads TurnRender card view + panel_focus |

## Law (proposed §1.1b, pending countersign)

> **Peripherals render the exchange, never the agenda (2026-07-29,
> café/me-llamo incidents):** Every learner-visible artifact outside the
> chat text (images, morphology card, focus panel) must be confirmed
> against a projection of the REALIZED exchange — pure functions of
> (learner turn, tutor reply, turn events) whose signatures admit no
> agenda inputs. Pre-call artifacts are candidates until settlement;
> unconfirmed candidates are dropped with a visible event, never
> rendered. Agenda systems (phase, scenes, next_best, introduce plans)
> steer instructions only. §1.1 gave code authority over decisions; this
> clause gives the conversation authority over what is displayed.

## Open questions for countersign

1. **Does anything legitimately LEAD the reply?** Session-open scene
   images (no learner text yet; confirm against reply only)? Association
   hard-breaks where the image IS the meaning carrier (R-B: candidate
   visible to model, confirmed iff reply presents the key — acceptable?)?
2. **Image confirmation grain:** concept surface-present in either text.
   Should an explicit image reference in the reply («mira la imagen»)
   without the concept word ALSO confirm (the caption carries the
   Spanish form on screen)? Proposed: NO for v1 — concept word or drop.
3. **Settlement vs gate ordering:** settle BEFORE the gate (gate rules
   read image_present; a doomed image must not exempt a probe), and
   RE-settle after a gate repair regenerates the reply. Correct?
4. **Scope check:** the morphology-card round (recast trigger, agreement
   detector + noun-gender map, gender_number_article form_id wiring,
   fallback honesty) folds INTO this round's card_engagement projection —
   one build, not two. Right call, or should the detector work ship
   separately first?
5. Does TurnRender need to survive past the turn for repaints (session
   holds last TurnRender, replaced whole each turn) — is replace-whole
   sufficient to stay "not shared state"?


---

## GROK (Grok Build CLI (0c785038798)) - 2026-07-30 02:20 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the design doc, then rule item-by-item as an independent countersigner.Next I'll inspect the image, morph, and gate stages that settlement has to sit between.## Countersign — exchange settlement (⬜ Grok, 2026-07-29)

**Role:** adversarial item-by-item. Inlined design + `tutor/turn_pipeline.py` + `tutor/turn_morph.py` + `PEDAGOGY.md` treated as DATA only. Incidents accepted as stated (café / me-llamo class).

**Overall:** Direction is right — reject shared `ExchangeState`; derived projections + a commit phase is the correct modern shape (CQRS read models / Elm commit / ECS resolve→render). **Not countersignable as written** without ordering and signature AMENDs: the design invents a single `stage_settlement` that both (a) must run before the gate and (b) must consume `INTRODUCED`/`FIRST_SEEN` events that only exist in the recorder family after the gate. That is an internal contradiction, not a polish issue.

---

### (1) Architecture P-1 / P-2 / P-3 vs shared state

**Verdict: AMEND** (shape COUNTERSIGN; placement and completeness REJECT-as-written)

**What is right**
- User veto of a bag is correct. `_turn_morph` on `last_mode_decision` (`stash_turn_morph` / `stash_intro_morph` in `tutor/turn_morph.py`) is already the miniature accretion pattern: one mutable dict, two writers, precedence rules, agenda fallback outside the pure detector.
- Pre-call commit is the disease. Evidence in pipeline:
  - `stage_mode_image` → `_attach_mode_image` with no reply (`turn_pipeline.py` ~1059–1063)
  - `stage_fallback_image` attaches + `note_image` on attach (~1116–1119) before any model text
  - Only `stage_declared_image` post-checks with `concept_in_text(declared, reply)` (~1705–1711) — and that is the path that “behaves”
- P-3 (bookkeeping at confirmation) is load-bearing, not optional: `images_shown` currently advances on attach, so a café the learner never saw still poisons future introduction eligibility.

**Recompute cost — not a real objection**
- Let \(C\) = pack concept count (A1 order \(10^2\)–\(10^3\)), \(L\) = tokenized length of learner+reply (order \(10^2\)).
- `image_relevance` ≈ \(O(C \cdot L)\) string/boundary checks once per settlement.
- Max settlements per turn under single bounded repair: **2** (initial + post-repair).
- Cost: \(2 \cdot O(C L)\) ≪ one tutor LLM call. No caching layer needed in v1.

**Derivation drift — structurally missing control**
- Per-consumer pure functions are fine **iff** they share one text-presence primitive (existing `concept_in_text` / `textnorm` / `phrase_present`), not reimplemented per consumer.
- **AMEND (add P-1 rider):** one module-level `exchange_surface(learner, reply) → NormalizedExchange`; all projections read that. Duplicate accent-fold logic = future café-class bug with different spelling.

**Repair-loop re-settlement — structurally missing in the stage list**
- Today `stage_gate_repair` replaces `ctx.raw` then re-gates with `replace(ctx.gate_ctx, raw=…, visible=…)` (~1425–1440) **without** refreshing `image_present` or `teach_images`.
- `image_present=bool(ctx.teach_images)` is fixed at `stage_gate_context` (~1322) from pre-call candidates.
- Arithmetic: if settlement runs once pre-gate and repair rewrites the reply so concept ∉ surface, then  
  \(\text{image_present}=\text{True}\) while \(\text{image_relevance}=\emptyset\) → doomed image still exempts scaffolds / still ships. That re-implements the café bug on the repair arm only.
- **AMEND:** after every reply mutation (initial + repair), run settlement; gate must read **settled** `image_present`. With `GATE_REPAIR` single-bounded: ≤2 settlements/turn.

**Fatal ordering contradiction (must amend P-2)**
Proposed: `generation → settlement → gate → record`.

But `card_engagement` priority includes introduction via `INTRODUCED` / `FIRST_SEEN` events, which are emitted in:
- `stage_introduce_ledger` (~1517–1521)
- `stage_first_seen` (~1568–1572)
and consumed by `stage_intro_morph` (~1577–1606) — all **RECORDERS after gate**.

You cannot both (i) settle cards from those events in pre-gate settlement and (ii) emit those events only post-gate. Pick one:

**Exact replacement for P-2 pipeline paragraph:**

> Pipeline becomes: agenda → instructions → generation → **settle_pixels** → gate → [if repair: regenerate → **settle_pixels** → re-gate] → recorders (ledger/first_seen/…) → **settle_chrome** → response assembly.
>
> - `settle_pixels` (post-generation, pre-gate, and again after any repair rewrite): confirms/drops **image candidates** only against `image_relevance(learner, final_reply)`. Writes `TurnRender.images` (+ drop events). Mutates `ctx.teach_images` down to the confirmed set so `GateContext.image_present` and introduce scaffold checks see truth. Does **not** require recorder events.
> - `settle_chrome` (after final reply is frozen **and** introduce/first_seen events exist, before client assembly): derives `card_engagement` / `panel_focus` into `TurnRender`. Replaces `_turn_morph` stash. Never re-opens image settlement unless a recorder is allowed to *add* a declared-image candidate (then re-run pixel confirm for that candidate only — see consumer inventory).
> - `TurnRender` is a turn-scoped result: single-assignment fields; no post-hoc field writes. Async enricher may only publish a **new** overlay object (`TurnRenderEnrichment`), never mutate confirmed images or the engaged form_id.

**P-1 card_engagement events dependency — AMEND**
- Learner-side morph: pure on `(learner, reply)` (reply needed for recast-trigger if the form only appears in tutor recast — correct to include reply).
- Intro-side morph: either (a) run in `settle_chrome` after events, or (b) derive from surface lemma in reply without events. Do **not** pretend intro cards settle in pre-gate `stage_settlement`.

**Rejected shared object — COUNTERSIGN**
- No `ExchangeState` bag. `TurnRender` as immutable result is the right substitute **only with** the single-assignment rule above; otherwise it becomes `ExchangeState` under a new name within one PR.

---

### (2) Input law as signature enforcement

**Verdict: AMEND** (intent COUNTERSIGN; enforcement as written has loopholes)

**Loopholes**
1. **`events` is a smuggling channel.** Anything agenda-derived that was emitted earlier (`MODE`, due offers, plan keys) can re-enter a “pure” derive if the function is allowed the whole log. Signature tests that only check parameter *names* miss this.
2. **Closure impurity.** `def image_relevance(learner, reply)` that closes over `session.sheet` / `next_best` / `decision.image_concept` is still agenda-shaped. Signature pins alone are theater.
3. **Candidates vs projections.** Settlement must take candidates (agenda-shaped) as a separate input:  
   `settle(candidates, projection_view) → confirmed | drop`.  
   Candidates are **not** projection inputs; confusing them re-legalizes pre-call as “derived.”
4. **Hidden second path:** `build_focus_panel` / client still reading `next_best.form_focus` (documented in `turn_morph.py` module doc, 2026-07-28 incident) bypasses derive signatures entirely.

**Exact replacement for Input law paragraph:**

> **Input law (signature + closure + call-site enforced):** Projection functions are pure and may take only:
> - `learner: str`, `reply: str`, and optionally `events: TurnEventLog` **restricted to an allowlisted event-kind set** (v1: form/error/recast-related + `INTRODUCED`/`FIRST_SEEN`/`MORPH_CARD` only — never `MODE`, phase, due-offer, or plan payloads), and
> - for image surface tests, a **frozen concept universe** (pack asset keys / table keys) as a pure data argument — not live sheet agenda.
>
> They must not close over `session`, `sheet`, `next_best`, `decision`, scene, or phase. Enforcement = (1) signature unit tests, (2) AST/lint: no `session.`/`sheet.`/`next_best` inside projection modules, (3) integration test: café-class fixture (scene `image_concept=cafe`, texts about house) asserts drop, (4) client/API must read `TurnRender` only for chrome — no parallel `next_best` morph path.
>
> Settlement (not the projection) is the only function allowed to take **candidates** and agenda-shaped attach metadata.

---

### (3) Proposed §1.1b law text verbatim

**Verdict: AMEND** (do not promote as-written)

Problems:
1. **“visible event”** collides with learner-visible UI. Design’s `render_dropped:*` is log/telemetry. Law must not force learner-facing drop toasts.
2. **Honest “up next” chrome** (inventory) is agenda-sourced by definition; absolute “every artifact… confirmed against realized exchange” forbids it. Need an explicit honesty carve-out with labeling, or inventory is illegal under the law.
3. **Repair re-settlement** is load-bearing for gate honesty (`image_present`) — belongs in law, not only design FAQ.
4. **“turn events”** without allowlist reopens smuggling (see §2).

**Exact replacement §1.1b:**

> **§1.1b Peripherals render the exchange, never the agenda (2026-07-29, café/me-llamo incidents; BINDING until HARD with tests):** Every learner-visible artifact outside the chat text that claims to be **about this turn** (teach images; morphology card in “live/engaged” mode; focus panel live fields) must be confirmed against a projection of the **realized** exchange — pure functions of `(learner_text, tutor_reply[, allowlisted turn events])` whose implementations admit no agenda inputs (no `next_best`, scene, phase, or sheet agenda; signature + closure enforced). Pre-call attach is **candidate** only; unconfirmed candidates are dropped and must not render. Every drop emits a typed log event `render_dropped:<kind>:<concept>` (operator/telemetry — not a learner-facing message). Bookkeeping that tracks “shown” (`note_image` / `images_shown` / display-tied costs) fires only on **confirmed** display. After any gate repair that regenerates the reply, pixel settlement re-runs before the re-gate so `image_present` cannot license a scaffold the learner will not see. Agenda systems (phase, scenes, `next_best`, introduce plans) steer **instructions** only. **Honesty carve-out:** a peripheral may show agenda-sourced “up next” / preview chrome only when explicitly labeled as not this-turn engagement (never silently as live). §1.1 gave code authority over decisions; this clause gives the conversation authority over what is displayed as this-turn truth.

*(Do not duplicate into reviews long-term — promote this paragraph into `PEDAGOGY.md` after adjudication; design doc points at it.)*

---

### (4) Open questions

#### OQ1 — Does anything legitimately LEAD the reply?
**Verdict: AMEND (split model-lead vs pixel-lead)**

| Case | Lead instructions (model) | Lead pixels (learner) |
|---|---|---|
| Session-open scene image | YES — no learner text; candidate in prompt | NO until confirm against **reply only** (`learner=""`). If reply never surfaces concept → drop. |
| R-B association (image is meaning carrier) | YES — model must know attach intent; keep deferred introduce render honesty (`stage_introduce_render` R-B→R-D on miss) | YES candidate; **confirm iff key ∈ reply surface** (same spirit as introduce scaffold law / `introduce_outcome`). Omit key → drop + introduce lapse — coherent, not a special exemption. |
| Mode/scene `image_concept` mid-chat | YES as direction | NO without surface confirm (café incident class) |

Pedagogy: dual-coding / multimedia learning requires **co-occurrence of form and referent**, not an orphan picture beside unrelated talk. Leading the *model* is fine; leading *pixels without reply uptake* recreates the disease.

**Exact OQ1 resolution text:**

> Nothing may lead **pixels**. Candidates may lead **instructions**. Session-open and R-B keep pre-call candidates for the model; display requires reply-side confirmation (open: reply only; R-B: key present in reply). No permanent “image leads without text” exemption.

#### OQ2 — Image confirmation grain (`mira la imagen` without concept word)
**Verdict: COUNTERSIGN** proposal NO for v1 — concept word (surface form, accent-folded, boundary-safe) or drop.

Rationale: caption-as-hidden-carrier is real dual-code but needs caption text in the confirmation universe (asset metadata). That is v2. v1 grain matches existing `concept_in_text` declared path (~1705). Do not invent a deictic exception without tests.

#### OQ3 — Settlement before gate + re-settle after repair
**Verdict: COUNTERSIGN the rule; AMEND the implementation shape** (see P-2 split)

Proof from inlined code:
1. Gate reads `image_present=bool(ctx.teach_images)` at context build (~1322).
2. `gate:unscaffolded_new_item` is critical (~1298–1299); image presence participates in scaffold legalization (introduce/first_seen path).
3. Repair rewrites `ctx.raw` without touching `teach_images` (~1425–1440).

Therefore: **settle pixels before gate**, and **re-settle after repair before re-gate**. Chrome settlement (cards) stays post-recorder as in P-2 AMEND — cards are not gate inputs today.

**Exact ordering law for design:**

> `raw₀ → settle_pixels₀ → gate₀ → (repair? raw₁ → settle_pixels₁ → gate₁) → recorders → settle_chrome → assemble`

Settlements/turn ≤ 2. No third loop.

#### OQ4 — Fold morphology-card round into this build?
**Verdict: AMEND — fold the *slot*, not the whole detector campaign**

- **Must fold into this round:** remove silent `next_best`/can-do live pin; `card_engagement` owns the card; honesty “up next” label; retire `_turn_morph` shared stash; intro path from allowlisted events in `settle_chrome` (replaces `stage_intro_morph` stash).
- **Must not block settlement ship:** agreement detector + noun-gender map + `gender_number_article` form_id wiring. The me-llamo incident is fixed by **stopping agenda-as-live**, not by detecting gender agreement.  
  Arithmetic: incident class = wrong *master* (next_best IP-03) while exchange was ser+gender. Fix master = projection/honesty. Detector is additive precision on priority tier 1.

**Exact OQ4 resolution:**

> One **card pipeline**, two PRs if needed: (A) settlement + honesty fallback + existing `detect_turn_morph` / intro events → `TurnRender`; (B) agreement detector expands `card_engagement` priority. Do not hold (A) for (B).

#### OQ5 — `TurnRender` survives for repaints?
**Verdict: COUNTERSIGN replace-whole with AMEND on mutability**

- Session holds `last_turn_render`; each turn **replaces the whole object**. That is not shared mutable state if fields are frozen after `settle_chrome`.
- Current async enricher **mutates** `mode_decision["_turn_morph"]` (`stash_turn_morph` ~2347–2369). Porting that mutation onto `TurnRender` reintroduces the bag.

**Exact OQ5 resolution:**

> Replace-whole is sufficient and preferred. Enricher publishes `last_turn_render_enrichment` (or a new immutable `TurnRender` copy with enrichment cells only). Confirmed images and engaged `form_id` are frozen at settlement; enricher may not change them.

---

### (5) Consumer inventory — missed renderers

**Verdict: AMEND — inventory incomplete**

| Missed / under-specified | Why it matters | Required after-state |
|---|---|---|
| `stage_image_costs` (~1132–1134) | Costs at attach = bill for pixels not shown | Cost notes on **confirmed** only (P-3) |
| `stage_introduce_render` + `introduce_outcome(..., teach_images=)` (~1511) | Scaffold evidence must use settled images, not candidates | Ledger sees confirmed set; R-B pre-call instruction path stays candidate-aware for model honesty, post-turn ledger uses settled |
| `stage_memory_notes` `note_tutor_turn(concepts=img_concepts)` (~1637–1646) | Memory of “what we showed” from unconfirmed attach | Confirmed concepts only |
| `stage_parts_notes` `result.parts["teach_images"]` (~1892) | Client renders this | Settled list; empty clears sticky client image |
| `stage_declared_image` (~1695+) | Post-gate **adds** images after `image_present` already fixed; second pixel path | Must call same `image_relevance` confirm; either (i) declared becomes a post-recorder candidate + `settle_pixels` for that add only (gate already passed — declared never licenses pre-gate scaffold), or (ii) declared moves into pre-gate settlement if parsed from raw before gate. Unify confirmation; do not leave a bypass |
| `stage_soft_plan` embeds `next_best` (~1829) | Focus/debug rail still agenda-shaped | Soft plan may keep agenda for debug; **learner-visible** focus must use `TurnRender` |
| Client sticky image / morph | “Images stuck on static” class | Explicit clear: confirmed empty → UI clears teach image and live morph; do not retain previous turn’s pixels as if current |
| `build_focus_panel` / sheet_public morph fallback | Documented master of me-llamo pin | Inventory row required: API reads `TurnRender.card` only; delete next_best live morph path |
| Journey / progress rail | Same disease class; design says fixed separately | Mark **OUT OF SCOPE** explicitly (not silent omit) with pointer to fix date 2026-07-29 |
| TTS/audio / caption chrome | If any auto-plays agenda concept | Confirm or exclude by name |

**Exact inventory rows to add:**

```
| stage_image_costs | notes costs on attach | notes costs on confirmed only |
| introduce_outcome / stage_introduce_ledger | scaffold check uses pre-call teach_images | uses settled teach_images |
| stage_memory_notes (image concepts) | concepts from attach set | confirmed only |
| stage_parts_notes / client teach_images | may stick prior image | settled; empty clears UI |
| stage_declared_image | post-gate second path | same image_relevance; no confirm bypass |
| build_focus_panel / sheet_public morph | next_best/can-do silent live | TurnRender.card; agenda only as labeled "up next" |
| journey rail | ledger shape (fixed 2026-07-29) | OUT OF SCOPE this round — not a settlement consumer |
| async focus enricher | mutates _turn_morph on shared dict | overlay only; no form_id/image mutation |
```

---

### Structural gaps checklist (author asked)

| Gap | Ruling |
|---|---|
| Recompute cost | Non-issue (\(≤2 \times O(CL)\)) |
| Derivation drift | **Missing** shared `exchange_surface` / one `concept_in_text` |
| Repair re-settlement | **Missing** in stage list; mandatory for gate honesty |
| Single settlement vs event timing | **Contradiction** — split settle_pixels / settle_chrome |
| Signature-only purity | **Insufficient** — need closure lint + event allowlist + client path kill |
| Declared-image bypass | **Missing** from unified confirm |
| Client clear-on-drop | **Missing** — server drop ≠ UI clear |

---

### Verdict summary (for finalization)

| # | Item | Ruling |
|---|---|---|
| 1 | P-1/P-2/P-3 vs shared state | **AMEND** (shape yes; split settlement; shared surface primitive; ≤2 pixel settlements; TurnRender single-assignment) |
| 2 | Input law / signatures | **AMEND** (closure + allowlisted events + candidates only at settle) |
| 3 | §1.1b verbatim | **AMEND** (use exact replacement above; then LAW-PROMOTION) |
| 4a | OQ1 lead | **AMEND** (model may be led; pixels may not) |
| 4b | OQ2 grain | **COUNTERSIGN** (concept surface or drop, v1) |
| 4c | OQ3 order | **COUNTERSIGN** rule + **AMEND** split/re-gate coupling |
| 4d | OQ4 scope | **AMEND** (card slot now; agreement detector not a gate on ship) |
| 4e | OQ5 repaint | **COUNTERSIGN** replace-whole + **AMEND** no async mutate |
| 5 | Consumer inventory | **AMEND** (rows above; declared path; client clear; focus API) |

**Blockers before “final”:** (B1) split settlement ordering written into the design; (B2) §1.1b AMEND text; (B3) declared-image unified; (B4) kill client/`build_focus_panel` next_best live morph path in the same behavioral ship as TurnRender. Without B1–B4 this is a good essay that leaves café/`image_present` and me-llamo half-fixed.

**Not blocked:** pure-projection philosophy; reject shared `ExchangeState`; P-3 confirmation-time `note_image`; OQ2 NO; replace-whole repaint model.

— end countersign —

---

## Adjudication (⬛ Claude, 2026-07-29) — all AMENDs accepted, round CONVERGED; build begins

No counters — every AMEND is evidence-backed, and item (1)'s ordering
contradiction is real (my single stage consumed INTRODUCED/FIRST_SEEN
events that only exist post-gate while claiming to run pre-gate).

**The converged architecture (supersedes P-2 as drafted):**

> raw₀ → settle_pixels₀ → gate₀ → (repair? raw₁ → settle_pixels₁ →
> gate₁) → recorders → settle_chrome → assemble
> ≤2 pixel settlements/turn; no third loop.

- `settle_pixels` (pre-gate, re-run after any repair rewrite): confirms
  image candidates against the exchange surface; shrinks ctx.teach_images
  to the confirmed set so GateContext.image_present and every downstream
  reader (introduce evidence, memory notes, parts, costs) sees truth;
  emits render_dropped events; note_image/costs fire on confirmed only.
- `settle_chrome` (post-recorders, replaces stage_intro_morph): derives
  card_engagement/panel_focus (allowlisted events available by then) into
  the frozen TurnRender; the _turn_morph shared-dict stash dies.
- Shared `exchange_surface` primitive — one text-presence/fold
  definition; projections may not reimplement matching.
- Purity enforcement: signatures + closure lint (no session./sheet./
  next_best in projection module) + event-kind allowlist + the
  café-class integration fixture + the client/build_focus_panel
  next_best live-morph path KILLED in the same ship (B4).
- Declared images unified on the same confirmation primitive (no bypass).
- TurnRender: single-assignment, replace-whole per turn; the async
  enricher publishes an overlay and may never mutate confirmed images or
  the engaged form.
- OQ1: nothing leads PIXELS; candidates may lead INSTRUCTIONS (session-
  open confirms against reply alone; R-B confirms iff key ∈ reply —
  drop + lapse stay coherent).
- OQ4 scope split honored: THIS ship = settlement + card slot + honesty
  fallback + existing detectors; the agreement detector + noun-gender map
  + gender_number_article wiring is the NEXT PR (folded design, split
  delivery — "fix the master first, add precision second").
- §1.1b lands as Grok's exact replacement text (BINDING until HARD with
  tests), including the honesty carve-out for labeled "up next" chrome
  and the repair re-settlement clause.

---

## Build record (⬛ Claude, 2026-07-29) — SHIPPED per the converged design

- `tutor/exchange_render.py`: exchange_surface (one text-presence
  primitive, delegating to teach_assets.concept_in_text), settle_images,
  card_engagement (allowlist-filtered events; learner beats intro),
  frozen TurnRender. Purity pinned by signature tests + AST lint +
  the café-class fixture (tests/test_exchange_render.py).
- Pipeline: stage_settle_pixels (pre-gate; shared _settle_pixels re-run
  inside stage_gate_repair after a rewrite, with image_present refreshed
  in the re-gate) → gate → recorders → stage_settle_chrome (replaces
  stage_intro_morph; derives card, freezes TurnRender, confirmed-only
  note_image + image costs). stage_image_costs DELETED. Censuses:
  realize 7, gate 4, recorders 12 (settle_chrome), total 36.
- Masters killed: _turn_morph shared-dict stash deleted (turn_morph
  stash functions removed); build_focus_panel live card reads ONLY
  sheet["_last_turn_render"]; every agenda fallback block renders
  live:false / engaged_by:"up_next" with a client "· up next" label
  (§1.1b honesty carve-out). Declared images: attach-time note/costs
  removed (cooldown kept — pacing, not display); unified bookkeeping at
  settle_chrome.
- session.last_turn_render: plain attribute, replaced whole per turn,
  cleared on new_chat + sheet_reset, injected as _last_turn_render for
  the enricher/repaints; deliberately NOT SessionState (display-only,
  never snapshotted).
- Events: RENDER_DROPPED (catalog 65); no silent drops.
- PEDAGOGY: §1.1b landed verbatim (Grok AMEND text) + §9 row.
- Goldens: 2 regenerated, audited — the only settlement-attributable
  delta is morph_card's seq position moving to the settle stage (no
  golden turn carries images; test config disables assets).

**Verification:** 804 passed + 17 subtests; truncation gate ok.
**Follow-up on record (OQ4 split):** PR B — agreement detector +
code-owned noun-gender map + gender_number_article form_id wiring
expanding card_engagement priority tier 1; then §1.1b BINDING→HARD
review once the fixture set has soaked.

**Round CLOSED 2026-07-29.**
