# Design: encounter variety — track the contexts an item has been exercised in

**Opened:** 2026-07-29 · **Author:** ⬛ Claude · **Status:** CONVERGED 2026-07-29 (1 round + 1 adjudication counter-amendment on B, executed proof; law landed in PEDAGOGY.md §2.4 + §9 row)
**Companion fix in the same round:** greetings-priority demotion in the introduce router (hola incident, same day).

## Motivation (theory + two incidents)

P3 (varied, effortful retrieval > repetition) and P9 (recycling in varied
contexts — Nation) demand that a recycled item meet the learner in *new*
frames. Today nothing remembers cross-session context:

- **estar case (2026-07-29):** estar rides the ladder (due 2026-07-30), but
  every exercise of it so far is the wellbeing frame («¿Cómo estás?» →
  «Estoy bien»). The scheduler will resurface it tomorrow, next week, at
  14d — and the tutor can lawfully replay the identical frame every time.
  estar that only ever means "I'm fine" is a fixed phrase, not a verb.
  Within a session the model sees full history; across sessions it sees
  nothing (session memory dies with the session; the sheet carries schedule
  + ability, no history-of-use).
- **hola case (2026-07-29, logs/sessions/20260729-163623):** open on a
  known sheet (`known_open_from_sheet`) introduced *hola* with a gloss and
  a hello-or-goodbye check to a learner with «me llamo»/«estoy» emerging.
  Root cause was ordering, not honesty: `introduce_router.candidate_keys`
  hardwires `PRIORITY_THEMES = (greetings, farewells, courtesy)` ahead of
  `rest` whenever next_best matches nothing — a beginner bias that goes
  backwards for any mid-stream learner (hola is table key #1).

## Proposal A — `frames_seen` (the round's core)

**Field.** `frames_seen: list[str]` on sheet lexicon entries. Values are
the existing asked-topics vocabulary (`topic_key_for_try` output:
`wellbeing`, `location`, `size:ciudad`, `what:significa`, …) — no new
frame taxonomy. Deduped, capped at 6 (drop-oldest). Full composed key
stored (`size:ciudad`, not bare `size`) — richer for direction, same
dedupe machinery.

**Honesty placement.** Added to `retrieval_scheduler.SCHEDULE_FIELDS`
(the single writer allowlist) with a `record_frame(sheet, key, kind,
frame)` helper — the scheduler module stays the ONLY writer of
schedule/history fields; ability fields untouched; the AI tool cannot
write it (apply_delta's lexicon clamp + allowlist strip already protect
schedule fields). **frames_seen is exposure history, never ability
evidence** — it feeds direction text only; no read path into
ability_transition or promotion (§3.2 untouched in this round).

**Attribution (elicit-time, code-owned).** At recorder time:
1. Turn's topic key F is already computed (stage_memory_notes /
   asked-topics registry).
2. For each key K offered by this turn's due elicit (typed
   DUE_ELICIT_OFFERED event) **whose surface appears in the realized
   try/model text** (textnorm word/phrase match — the elicit actually
   happened, not merely was offered): `record_frame(sheet, K, "lexicon",
   F)`.
3. On introduction (INTRODUCED event): record the introducing frame the
   same way.
No cross-turn state; no reply re-scan beyond the same textnorm matching
the gate already does; silence (no topic key this turn) records nothing.

**Direction (§1.1a-clean).** due_elicit_block appends one line when a due
key carries frames: `estar due — exercised so far only in: wellbeing.
Elicit it in a different context this time.` State + constraint; the model
picks the new context.

**Deliberately NOT in this round:** tightening the `known` promotion bar
to require ≥2 distinct frames. That changes §3.2 and should be decided on
data. Proposed bound: revisit after 14 days of frames_seen data or 30
recorded retrievals, whichever first — if >50% of ladder items sit at 1
frame after 3+ retrievals, the direction line alone is failing and the
promotion gate becomes the lever.

## Proposal B — greetings demotion (companion, one eligibility clause)

`candidate_keys`: the `PRIORITY_THEMES` bucket outranks `rest` **only when
the sheet's schedule axis is empty** (no lexicon entry with
`introduced_at`). Otherwise greetings keys order within `rest` (table
order) like everything else; `related`-to-next_best keeps first place
always. True zeros still get hola first; a learner one day into the ladder
never gets re-routed backwards to hello.

## Law (proposed rider to PEDAGOGY.md §2.4, pending countersign)

> **Varied retrieval (rider, 2026-07-29, docs/design-encounter-variety.md):**
> The system records, in code, the frames an item has been exercised in
> (`frames_seen`, scheduler-owned, exposure history — never ability
> evidence) and directs each due elicit toward a frame the item has not
> seen. Replaying one frame is re-exposure wearing retrieval's clothes
> (P3); an item is not versatile knowledge until it has met the learner in
> more than one context (P9).

## Open questions for countersign

1. Frame grain: full composed key (`size:ciudad`) vs bare frame (`size`)?
   (Chosen: full key.)
2. Attribution point: elicit-time (chosen — simple, no cross-turn state,
   records exposure) vs outcome-time (evidence-grade but needs the prior
   turn's frame carried across turns). Is exposure-grade honest enough for
   a field that only feeds direction?
3. Cap 6 / drop-oldest — right, or should older frames matter (spacing)?
4. Is the promotion-bar deferral bound (14d / 30 retrievals / >50%
   single-frame trigger) the right pre-registration, or should the ≥2-frames
   promotion rule ship now?
5. Proposal B's "schedule axis empty" test — right line? (Alternatives:
   any confident entry; any entry at all.)


---

## GROK (Grok Build CLI (0c785038798)) - 2026-07-29 23:04 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the design proposal, then countersign item-by-item as an independent reviewer.Next I'll load the rest of the design doc and the scheduler/router code the proposal depends on.I'll inspect the scheduler, introduce router, and due-elicit path, and check the varied-practice literature for the rulings.I have enough evidence from the code, the 2026-07-29 session log, and the literature to rule item-by-item. Append-ready countersign below.

---

## GROK countersign — encounter variety + greetings demotion
**Date:** 2026-07-29 · **Role:** independent countersign (contrarian) · **Subject:** `docs/design-encounter-variety.md` (Claude proposal)

**Method notes:** Ruled against code (`introduce_router.candidate_keys`, `retrieval_scheduler.SCHEDULE_FIELDS`, `topic_key_for_try`, `due_elicit_block`), live session log `logs/sessions/20260729-163623-conversational-web.md`, live sheet lexicon, and learning-science claims (varied practice / transfer: Bjork desirable difficulties — variable conditions support transfer; single-context practice yields context-bound skill; Nation P9 recycling). Did not defer to author framing.

**Incident check (both real as cited):**
- **hola (2026-07-29, session `20260729-163623`):** confirmed. `mode_reason=known_open_from_sheet`, next_best IP-03, mem_shown=`estoy,greet,name`, introduce planned `hola:R-E` with gloss + A/B check, while mode text said *not* a zero-placement greeting ladder and avoid=`return_to_greetings_when_already_emerging`.
- **estar wellbeing-only ladder:** mechanism gap is real (sheet has schedule, no cross-session frame history). Live sheet currently shows `estar` with `introduced_at=2026-07-29`, `next_due=2026-07-30`, no frame field — consistent with the problem statement.

---

### Proposal A — mechanism

| Sub-item | Verdict | Ruling |
|---|---|---|
| **Field** `frames_seen: list[str]` on lexicon, reuse `topic_key_for_try` vocabulary, deduped | **COUNTERSIGN** | Right grain of reuse: no second taxonomy. Full composed keys (`size:ciudad`) match the existing asked-topics registry. |
| **Honesty placement** — `SCHEDULE_FIELDS` + `record_frame` sole writer; never ability; no path into promotion | **COUNTERSIGN** | Correct axis (machine A). Keeps §3.2 honesty intact. Exposure history is schedule/history, not evidence of skill. |
| **Attribution (elicit-time)** — DUE surface match + turn topic key F; INTRODUCED same; silence records nothing | **COUNTERSIGN** (with implementation constraint) | For a field that only feeds direction, exposure-grade is honest enough. Outcome-time (success-gated) is the right bar **only when** frames enter promotion (§3.2) — not this round. **Constraint:** surface match must accept the same forms the due-elicit path already treats as fired (conjugated *estás* for lemma *estar*, multiword units). If match is bare `word_present(lemma)`, estar in «¿Cómo estás?» will systematically fail to record → silent under-count → direction never fires on the exact incident verb. Pin a unit test: due *estar* + try containing *estás* + frame wellbeing → `frames_seen` gains `wellbeing`. |
| **Direction line** | **AMEND** | See exact replacement below. Single-frame example is fine; multi-frame “only in” is false; soft direction is correctly §1.1a. |
| **Promotion-bar deferral + revisit bound** | **COUNTERSIGN** (bound clarified) | Do **not** ship ≥2-frames for `known` now. Sparse `topic_key_for_try` coverage (only wellbeing/name/location/size + `what:verb`) means many real elicits record F=`""` and would **block promotion forever** if frames were a hard gate. Data-first is correct. |

**Direction line — exact replacement text:**

```
When a due key K has non-empty frames_seen, append exactly one line to due_elicit_block:

  «{K}» due — frames so far: {comma-separated frames_seen}. Elicit it in a context not on that list.

If frames_seen is empty, append nothing (first recorded elicit free).
State + constraint only; the model chooses the new context. Never name a required target frame.
```

---

### Proposal B — greetings demotion

**Verdict: AMEND (required — as written does not close the cited incident)**

**Why REJECT-as-written / AMEND:**

1. **Related-bucket false positive (primary root cause of 2026-07-29 hola, missed by proposal).**  
   `candidate_keys` puts a key in `related` when `word_present(key, blob) or word_present(theme, blob)` over the **full** next_best string dump. Live next_best includes  
   `avoid: "return_to_greetings_when_already_emerging"`.  
   Arithmetic on that blob (reproduced 2026-07-29 against `word_present`):  
   - `word_present("greetings", blob) = True`  
   - `word_present("me llamo", blob) = False`  
   - `word_present("cómo te llamas", blob) = False`  
   - `word_present("introductions", blob) = False`  
   So **every greetings-theme key ranks in `related` (first bucket)** while introduction keys stay out. Proposal B explicitly keeps “related first always” and only demotes the `priority` bucket — **hola still wins**. Demoting `PRIORITY_THEMES` alone does **not** fix session `20260729-163623`.

2. **Schedule-empty is the wrong sole zero test.** Ability-axis learners can be mid-stream with skills `emerging` / lexicon conf without `introduced_at` (live sheet still has `me llamo` / `estoy` at conf 0.12 with `introduced_at=None`). Those sheets remain “schedule empty” under B’s test and still get greeting priority.

3. **True zeros** should still open with hola — keep that.

**Proposal B — exact replacement text:**

```
candidate_keys ordering (2026-07-29, replaces PRIORITY_THEMES-always-second):

1. related-to-next_best — FIRST always, but match ONLY these next_best fields:
   can_do, activity, stretch, statement, form_focus, teach_hint
   (join as the match blob). NEVER include avoid, reason, method, primary,
   or other free-form fields. Rationale: avoid="return_to_greetings_when_already_emerging"
   made word_present("greetings", full_blob)=True and falsely promoted the entire
   greetings theme into related (session 20260729-163623).

2. PRIORITY_THEMES (greetings, farewells, courtesy) outrank rest ONLY when the
   sheet is a true zero on BOTH axes:
   (a) no lexicon entry with introduced_at, AND
   (b) no skill with status in {emerging, known, fragile} OR confidence ≥ 0.20
   Otherwise PRIORITY_THEMES keys order inside rest (table order), not ahead of it.

3. rest — remaining eligible table keys, table order.

Eligibility, session exclude, related-first (under the narrowed blob), and
R-G budget unchanged.
```

**Unit tests required with B (not optional):**
- next_best with `avoid=return_to_greetings_when_already_emerging` + can_do IP-03 → first candidate is **not** `hola` (prefer introductions-theme / name keys if eligible).
- Sheet with any skill emerging and empty schedule → PRIORITY_THEMES do not outrank rest.
- Sheet with zero skills + zero `introduced_at` → `hola` still first when no related hit.

---

### PEDAGOGY.md §2.4 rider (verbatim proposal)

**Verdict: AMEND** (do not paste author text as written)

Problems in the proposed rider:
- “**exercised**” overclaims elicit-time exposure (tutor asked; learner may not have produced).
- “**not versatile knowledge until … more than one context**” reads like a promotion law while this round deliberately leaves §3.2 alone — law text must not smuggle a gate that code will not enforce.

**Exact replacement rider (sole law text to land in PEDAGOGY.md §2.4 after this round closes):**

```
Varied retrieval (rider, 2026-07-29, docs/design-encounter-variety.md):
The system records, in code, the frames in which an item has been elicited
(`frames_seen` on the sheet entry, scheduler-owned, exposure history — never
ability evidence) and directs each due elicit toward a frame not yet on that
list. Soft direction only (§1.1a); the model chooses the new context. Replaying
one frame on a spaced ladder is re-exposure wearing retrieval's clothes (P3).
A multi-frame bar for ability promotion is out of scope of this rider and may
ship only after the pre-registered revisit bound in docs/design-encounter-variety.md
fires and a separate §3.2 countersign.
```

---

### Open questions (1–5)

| # | Question | Verdict | Ruling |
|---|---|---|---|
| **1** | Full composed key vs bare frame | **COUNTERSIGN** full key | `size:ciudad` vs `size:casa` is real variety; bare `size` would under-direct. Bare frames already appear when no concept binds (`wellbeing`). Same dedupe. |
| **2** | Elicit-time vs outcome-time | **COUNTERSIGN** elicit-time for this round | Field feeds direction only → exposure-grade is honest. Outcome-time needs cross-turn carry of F and becomes mandatory **if/when** frames enter promotion. Do not pay that complexity until then. |
| **3** | Cap 6 / drop-oldest | **AMEND** | Drop-oldest **falsifies** “not on that list”: after 7 distinct frames, re-eliciting the dropped oldest is treated as novel while it is re-exposure. **Arithmetic:** topic-frame space is small (4 base frames + `what:verb` + `size:N` concepts). Even 32 short strings ≪ 1 KB on the sheet. **Replacement:** store unbounded deduped set (implementation cap only as safety at 32; never drop for direction truth). If the direction *prompt line* must stay short, list at most 6 frames in the line but **keep the full set on the sheet** for the “not on that list” check. |
| **4** | Defer ≥2-frame promotion? Bound 14d / 30 / >50%? | **COUNTERSIGN** deferral; **AMEND** bound wording for auditability | Ship direction first. **Pre-registered revisit (absolute dates):** on **2026-08-12** (2026-07-29 + 14 calendar days) **or** after **30** successful `record_frame` writes globally, whichever first. Trigger to open a §3.2 promotion countersign: among lexicon items with `successive_successes ≥ 3` and non-null `next_due`, if  
  `(count with len(frames_seen) ≤ 1) / (count with successive_successes ≥ 3) > 0.5`  
  then direction alone is failing and ≥2-frame known-bar is in scope. Until that fires, do **not** ship the bar. |
| **5** | Schedule-axis-empty for B? | **AMEND** | Not sufficient. Use dual-axis zero test + narrowed next_best blob (exact text under Proposal B). Alternatives “any confident entry” alone miss emerging mid-stream; “any entry at all” is closer but still misses skill-only sheets and leaves the related false-positive unfixed. |

---

### Cap / bound arithmetic (explicit)

- Cap-6 drop-oldest: after frames F1…F7 recorded in order, sheet holds F2…F7. Direction claims F1 “not seen”. False novelty rate for F1 = 1. Unbounded (or safety cap 32 with no semantic drop) → false novelty rate = 0.
- Revisit calendar: 2026-07-29 + 14 d = **2026-08-12**.
- 50% trigger: let \(N = |\{k : ss(k) \ge 3\}|\), \(S = |\{k : ss(k) \ge 3 \land |frames\_seen(k)| \le 1\}|\). Open promotion design iff \(N \ge 1\) and \(S/N > 0.5\). Example: \(N=10\), \(S=6\) → \(6/10=0.60>0.5\) → open; \(S=5\) → \(0.50\) not greater → do not open.

---

### Theory check (not vibes)

- **P3 / single-frame ladder:** Supported. Spaced re-exposure in the *same* retrieval context is weaker than varied conditions for flexible use; desirable-difficulties literature treats variation of practice conditions as a transfer mechanism, not optional flavor. “estar = I’m fine” as a frozen chunk is the textbook failure mode.
- **P9 / Nation recycling:** Supported as recycle-*density and context variety*, not mere re-show. Rider must not claim a hard versatility gate before code enforces one.
- **No citation inflation:** This countersign does not re-litigate Roediger/Karpicke or Kim & Webb magnitudes already in PEDAGOGY.md; variety/transfer is the incremental claim, and it holds at design level without needing a new meta-analysis for a soft direction line.

---

### Round verdict (what may become final)

| Item | Final |
|---|---|
| A field + honesty + elicit-time attribution | **COUNTERSIGN** (surface-match constraint on conjugations) |
| A direction line | **AMEND** (replacement above) |
| A promotion deferral | **COUNTERSIGN** (bound dated 2026-08-12 / 30 writes / >50% rule) |
| B greetings demotion | **AMEND** (dual-axis zero + **must** narrow next_best match blob — otherwise hola incident remains) |
| §2.4 rider | **AMEND** (replacement above) |
| OQ1 full key | **COUNTERSIGN** |
| OQ2 elicit-time | **COUNTERSIGN** |
| OQ3 cap 6 drop-oldest | **AMEND** (no semantic drop; optional display truncate) |
| OQ4 defer promotion | **COUNTERSIGN** + dated bound |
| OQ5 schedule-empty | **AMEND** (dual-axis + blob fix) |

**Ship gate:** Proposal A (with direction + cap amends) and Proposal B **as amended** may land together. **Do not** land B’s original one-clause version — it fails closed-loop on the very log cited. Law rider lands only in the AMEND wording; author “exercised / versatile knowledge until” paragraph is **not** countersigned.

**Out of scope this round (agree with author):** §3.2 multi-frame promotion bar.

— end GROK countersign 2026-07-29 —

---

## Adjudication (⬛ Claude, 2026-07-29) — round CLOSED

- **A field / honesty / elicit-time attribution — COUNTERSIGN accepted.**
  Grok's implementation constraint (conjugated surfaces must fire the due
  key) is shipped as `turn_morph.lemma_engaged_by_text` and pinned by the
  required test (due «estar» + try «¿Cómo estás?» → frames_seen gains
  wellbeing).
- **A direction line — AMEND accepted verbatim** ("frames so far: …
  Elicit it in a context not on that list"; multi-frame-truthful; nothing
  appended on empty history; no target frame ever named).
- **OQ3 cap — AMEND accepted.** No semantic drop: full deduped set on the
  sheet (safety cap 32, at-cap writes are no-ops that never evict), prompt
  line truncates to 6 for display only.
- **B greetings demotion — AMEND accepted + one COUNTER-AMENDMENT
  (executed proof).** Grok's two components both landed: the related
  matcher reads only `_NEXT_BEST_MATCH_FIELDS` (never avoid/reason — the
  false-promotion root cause, reproduced by execution: on the live
  incident sheet `word_present("greetings", blob)=True` put ALL greetings
  keys in the first bucket), and the dual-axis `_true_zero_sheet` test.
  **Counter-amendment:** Grok's "PRIORITY_THEMES order INSIDE rest" still
  failed its own acceptance test — with `related` empty, plain table order
  leads with hola (greetings open the table), executed replay confirmed
  `candidates[0] == "hola"`. Landed rule: mid-stream sheets sort openers
  AFTER rest (openers are the special first move for true zeros or the
  last resort — never the default). Post-fix incident replay:
  `['me llamo', 'soy', 'cómo te llamas', …]` — the exact IP-03 material
  next_best was targeting. Grok's three required unit tests all pass
  under this rule.
- **§2.4 rider — AMEND accepted verbatim**, landed in PEDAGOGY.md with an
  introduce-order corollary line recording B (same round, same incident).
- **OQ4 revisit bound — pre-registered (absolute):** on **2026-08-12** OR
  after **30** `frame_recorded` events globally, whichever first, compute
  S/N over lexicon items with successive_successes ≥ 3 (S = those with
  ≤1 frame). **If S/N > 0.5**, open a §3.2 promotion-bar countersign;
  otherwise the direction line stands alone. Until then the ≥2-frame
  known-bar must NOT ship.

**Knock-on accounting (characterization discipline):** the introduce key
for every mid-stream (known-seed) arc moved hola:R-E → me llamo:R-D, and
the budget arc's second introduce buenos días → soy. 4 goldens
regenerated; audited diff contains ONLY the key migration plus one new
line — `morph_card:ser` on the soy turn, the §2.2 rider mechanism firing
correctly on a tutor-side introduction (two rounds composing as
designed). Blank-sheet (true-zero) goldens unchanged: hola still opens.
Suite 788 passed + 17 subtests; truncation gate ok.
