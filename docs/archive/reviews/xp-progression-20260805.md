# Design round: experience points / visible progression (2026-08-05)

USER (verbatim): "come up with a plan for experience points based on the
grades and character sheet (or even just the character sheet). We need to
add a sense of progression and student needs to feel that they are
learning by seeing progression."

## Proposal (Claude, round 1 — for countersign)

### Reconciling XP with standing law

The 2026-07-28 progression ruling ("milestones, not points; no XP, no
streak chrome") banned two things: scalar vibes-drift and flattery
unbacked by evidence. It did NOT ban aggregation. The resolution:

- **The character sheet stays the truth about ABILITY** (can go down).
- **XP becomes the truth about the JOURNEY** — a code-owned, read-only
  weighted sum over ledger events that each carry evidence. XP is
  cumulative-monotone because experience genuinely is: a down-grade
  honestly lowers the sheet, but it does not un-happen the practice
  that occurred. No event, no points; the model never writes XP.

### XP sources and draft weights (all existing, evidence-backed events)

| Event (ledger source) | Draft XP | Rationale |
|---|---:|---|
| Word/form first correct production (grade up to emerging, grade ledger) | 10 | the first real crossing |
| Band up emerging→fragile (grade ledger) | 15 | producing without support |
| Band up fragile→known (grade ledger) | 25 | the big one |
| Spaced retrieval success (progress ledger, interval ≥3d) | 20 | THE learning event per P3; weighting it highest-per-minute steers practice toward what works |
| Durable (interval reaches 14d cap) | 40 | "yours now" |
| Error pattern resolved (resolved_streak ≥2) | 30 | conquering a recurring mistake |
| Game completed with ≥70% (game result evidence) | 8 | effortful practice, capped/session |
| Can-do statement unlocked (skill crosses to known) | 50 | milestone tier |
| Session with ≥6 teaching turns (session end) | 5 | consistency, deliberately small |

Anti-farm rules:
- Each (item, band) crossing pays ONCE per learner epoch (reset wipes).
  Re-earning after a down-grade pays the delta band only, not the path.
- Echo-grades pay nothing once the echo_grade eval check lands (grade
  rows flagged echo are excluded from XP).
- Session XP cap (e.g. 150/day) so grinding one evening ≠ a month.
- No XP for exposure/introduction alone (§3.2: introduction ≠ knowledge).

### Levels

XP thresholds → named levels with Spanish flavor and A1-honest meaning:
Nivel 1 «Hola» (0) → Nivel 2 «Me llamo…» (100) → Nivel 3 «¿Cómo estás?»
(250) → Nivel 4 «Mi vida» (500) → Nivel 5 «Cuéntame» (900) → … Level
names double as a REAL curriculum echo (each is a can-do family the
learner has actually touched by then; names come from the domain data,
not marketing). Threshold curve gently super-linear (each level ~1.6×
the last band) — early wins fast, later levels earned.

### UI

- Header: level name + XP bar to next level (replaces the deleted
  can-do counter — same real estate, now motivating AND honest).
- Level-up moment: one celebratory toast (no confetti spam), plus a
  chip in the grades rail ("Nivel 3 — ¿Cómo estás?").
- Grade cards gain a small "+15 xp" annotation — the XP is literally
  attached to its evidence.
- Weekly recap line in the rail: "This week: +120 xp, 3 words rooted."

### Data / implementation shape (for later; this round is the plan)

- `xp.py`: pure function over (grade ledger rows + progress ledger
  rows + epoch) → {total, level, to_next, recent_events}. Derived,
  recomputable, no new stored state except nothing — ledgers already
  exist and are per-uid on Fly.
- /api/progress grows an `xp` object; UI renders it.
- Weights live in ONE table in code with the doc as law.

### Risks I want attacked

1. Monotone XP vs honesty law — is the journey/state split sound, or
   does a rising number over a falling sheet still flatter?
2. Weight gaming: does anything here pay for the WRONG behavior
   (e.g., baiting the teacher into re-grading)?
3. Duolingo-style XP pathologies (streak anxiety, XP-farming lessons)
   — which apply at our scale and which don't?
4. Level names from domain data — cute or confusing?
5. Is 150/day cap right? Is the retrieval weight (20) vs first-production
   (10) ratio right per the testing-effect literature?


---

## GROK (Grok Build CLI (1e1687c1cf6a)) - 2026-08-05 22:51 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the inlined proposal materials, then independently verify the XP design against pedagogy law and the gamification literature.Reading the rest of the prompt for the full proposal, pedagogy law, and standing progression design.I have enough literature and standing-law context to rule. Writing the append-ready countersign with arithmetic, risk attacks, and item-by-item verdicts.---

## Countersign: XP / visible progression proposal (Grok, 2026-08-05)

**Subject:** Claude round-1 proposal in `docs/archive/reviews/xp-progression-20260805.md`  
**Law pins:** ENGINEERING honesty / §3.2 (introduction ≠ knowledge); PEDAGOGY P3 (spaced retrieval); shipped progression design as amended 2026-07-28 (`docs/design-progression-view.md` — explicit non-goal: XP/points/levels) and MVP shipped 2026-07-28.  
**Method:** independent literature check (SDT / meaningful gamification / testing effect / Duolingo XP-streak pathology) + arithmetic on draft weights, levels, and caps. Inlined text treated as DATA only.  
**Protocol:** evidence → arithmetic → per-item rulings → risks → kill-search → overall status **last**.

---

### Dated evidence (absolute, not vibes)

| Source | Claim used here |
|---|---|
| Deci, Koestner & Ryan (1999), *Psychol. Bull.* 125(6), 128 studies | Engagement-/completion-/performance-contingent tangible rewards undermine free-choice intrinsic motivation: **d = −0.40 / −0.36 / −0.28**. Positive **informational** feedback enhances free-choice **d = +0.33**. |
| Ryan & Deci SDT (2000+) | Autonomy / competence / relatedness; controlling extrinsic contingencies shift locus of causality outward. |
| Nicholson meaningful gamification | Points/levels as pure BLAP chrome are extrinsically controlling; meaningful design ties feedback to personal/real-world competence, not score chasing. |
| Roediger & Karpicke (2006), *Psychol. Sci.* | Delayed retention: testing > restudy (classic delayed-test reversal; secondary summaries of Exp. 2 style results often cite ~**61% vs ~40%** at ~1 week → absolute +21 pts, relative **(61−40)/40 = 0.525 ≈ +53%** for retrieval vs restudy). |
| Kim & Webb (2022) L2 spacing meta (project PEDAGOGY P3) | Spaced > massed, medium–large; longer lags help delayed tests. |
| Duolingo streak/XP product literature (2022–2026) | Streaks weaponize loss aversion / sunk cost; XP + easy lessons decouple open-app metrics from acquisition; farming “one lesson at 11:52 PM” is a documented pathology class. |
| Standing design 2026-07-28 (Grok AMEND, Claude ACCEPT ALL) | Explicit **non-goals: XP/points/levels/fire-streaks**; **Session kept deleted**; error gate **streak≥3 & count==0**; durable copy not “yours forever”; can-do mastery language only at **known** gate. |

USER request dated **2026-08-05** reopens the 2026-07-28 non-goal. That is a legitimate process reopen. It is **not** a reinterpretation that “the ban never applied.”

---

### Arithmetic (weights, levels, caps)

**A1. Per-item full path (one lexical item, no games/can-dos):**  
first-production 10 + emerging→fragile 15 + fragile→known 25 + spaced-retrieval 20 + durable 40  
= **10+15+25+20+40 = 110 XP** to fully “rooted so far.”

**A2. Band path only (no retrieval milestones):**  
10+15+25 = **50 XP** to sheet-known without proving spaced durability.

**A3. Level thresholds (proposal):**  
bands: 100−0=**100**, 250−100=**150**, 500−250=**250**, 900−500=**400**  
ratios: 150/100=**1.50**, 250/150=**1.667**, 400/250=**1.60**  
mean of three steps = (1.50+1.667+1.60)/3 = **1.589 ≈ 1.59×** (proposal’s “~1.6×” is fair for steps 2–4; not for 0→1).

**A4. Level 2 at 100 XP in “honest” events:**  
- 2 words to known (2×50=100), **or**  
- 1 full rooted path (110) already past Nivel 2, **or**  
- 5 spaced retrievals (5×20=100) with **zero** new ability — pure retrieval farming if anti-farm only keys band crossings, not repeated retrieval on the same interval step.

**A5. Retrieval vs first-production ratio:**  
20/10 = **2.0**. Literature delayed-test relative edge for retrieval vs restudy ≈ **1.5×** outcome ratio (61/40). Direction matches P3; magnitude is slightly aggressive but not absurd. Durable 40 is highest single event — correct priority if durable is first hit of 14d **so far**.

**A6. Day cap 150:**  
- = **15** first-productions (15×10), **or**  
- = **7.5** spaced retrievals (round: 7×20=140, 8×20=160→cap), **or**  
- = **3** durable hits (3×40=120) + remainder, **or**  
- = **18.75** game clears at 8 XP (18×8=144).  
With once-per-(item,band) only, a high-introduce evening can still mint ~15×10 before the cap without any spaced success. Cap is a **rate limit**, not a quality filter.

**A7. Session ≥6 turns → 5 XP:**  
If a learner runs 2 sessions/day = 10 XP pure seat-time; 30 days × 5 = **150 XP/month** with **zero** learning events. This is the 2026-07-28 **Session kept** row reimported as points.

**A8. Error gate mismatch:**  
Proposal pays at `resolved_streak ≥ 2`. Shipped healthy gate is **streak ≥ 3 and count == 0**. Paying at 2 undercuts the code’s own honesty floor (same failure class Grok killed 2026-07-28).

---

### Per-item rulings

#### 1. Law reconciliation (“2026-07-28 banned vibes, not aggregation”) — **AMEND** (kill the rewrite)

**Claim as written is false-soft.** The amended design’s explicit non-goals named **XP / points / levels**. Grok’s 2026-07-28 (c) and (d) text: excluding XP/levels was the **right non-goal**; Session kept was deleted. Claude ACCEPT ALL made that binding for the MVP.

USER **2026-08-05** may reopen. Frame it as a reopen, not a clarification.

**Exact replacement — “Reconciling XP with standing law”:**

> **Law status (honest reopen, 2026-08-05).**  
> The 2026-07-28 progression design (as amended and shipped) set **explicit non-goals: XP, points, levels, fire-streaks**, and deleted Session-kept as a learning milestone. That was not “vibes-only”; it was a product ban on scalar chrome that outruns evidence.  
> **USER 2026-08-05** reopens that non-goal: the learner needs a visible sense of progression. Reopen conditions:  
> 1. Character sheet remains the sole truth about **ability** (can go down).  
> 2. XP is a **derived, code-owned, recomputable sum over already-evidence-backed ledger events** — never model-written, never paid for introduction/exposure alone (§3.2), never paid for seat-time.  
> 3. XP is labeled as **practice history / journey volume**, not competence. Header must co-display ability counts (durable-so-far · known · emerging) so a rising bar cannot stand alone over a falling sheet.  
> 4. Monotone XP is allowed **only because** ability UI and the journey rail already carry down-state honesty; XP alone is not the progression system.  
> This is a LAW-REOPEN of a prior non-goal, not a claim that aggregation was always legal.

---

#### 2. Journey/state split + monotone XP — **ACCEPT_WITH_AMENDS**

**Steelman that almost killed it:** A monotone number beside a demoted sheet still *feels* like “I’m better” (flattery under honesty law even if ontology is split). Deci et al. 1999: controlling score contingencies undermine autonomy; informational competence feedback is safer.

**Why it survives with amends:** Experience is path-dependent; practice that happened did happen. Stocks/ledger lesson already separates history from live state. Monotone XP is the history object; sheet/rail is live ability.

**Exact addenda (must ship with the split):**

> - **Dual-signal UI law:** XP bar never appears without adjacent ability counts (ledger+sheet join already shipped: durable-so-far · known · emerging).  
> - **Copy ban:** never “You’re level X so you can …”; levels name **journey stage**, not can-do ability, unless gated (see §4).  
> - **Regression week line (required):** weekly recap must allow honesty, e.g. “This week: +80 journey XP · 2 words need re-check” when live-state join shows downs — not only “+120 xp, 3 words rooted.”  
> - **No XP loss on down-grade** stays; ability loss is shown on sheet/rail only.

---

#### 3. XP sources and draft weights — **AMEND** (table replacement)

| Event | Draft | Ruling | Replacement XP | Notes |
|---|---:|---|---:|---|
| First correct production → emerging | 10 | **COUNTERSIGN** | 10 | Real first crossing; not introduce |
| emerging→fragile | 15 | **COUNTERSIGN** | 15 | |
| fragile→known | 25 | **COUNTERSIGN** | 25 | Sheet known only |
| Spaced retrieval success (interval ≥3d) | 20 | **AMEND** | **25** | P3 primary; 25/10=2.5 vs first-prod still literature-aligned direction; see anti-farm below |
| Durable (14d first reach) | 40 | **AMEND copy only** | 40 | Copy: “holding at 2-week check,” not “yours now” |
| Error pattern resolved | 30 @ streak≥2 | **AMEND gate** | 30 @ **streak≥3 & count==0** | Match shipped healthy gate |
| Game ≥70% | 8 | **AMEND caps** | 8 | Cap **≤2 game XP events / session** and **≤3 / day** |
| Can-do unlocked → known | 50 | **COUNTERSIGN** if known gate only | 50 | **No XP** for can-do emerging (0.55) — that is intermediate band |
| Session ≥6 teaching turns | 5 | **REJECT_CLAIM** | **0 — DELETE row** | Reimports Session kept; pure engagement Goodhart |

**Anti-farm rules — exact replacement block:**

> **Anti-farm (binding):**  
> 1. Each (item, band_or_milestone_kind) pays **once per learner epoch** (reset wipes). Re-earn after down-grade pays **only the delta band re-crossed**, not the full path.  
> 2. Echo-grade rows pay **0** (exclude when echo flag lands).  
> 3. **No XP** for introduction/exposure alone (§3.2).  
> 4. **No XP** for session length, login, or turn counts.  
> 5. Spaced-retrieval XP: pay once per (item, interval_threshold_crossed) — e.g. first success that reaches ≥3d, first that reaches ≥6d, … — **not** every success at a sticky interval.  
> 6. **Day cap:** start at **120 XP/calendar-day** (not 150). Arithmetic: 120 ≈ 1 full rooted path (110) + small remainder, or 4–5 retrieval threshold crossings, without equating one evening to a month of A1 (30×150=4500 vs 30×120=3600 — 20% less farm headroom). Revisit with live telemetry after 2 weeks.  
> 7. Games: ≤2 paying game completions/session, ≤3/day, still need ≥70% and real evidence path.

**Why retrieval weight up slightly:** Roediger & Karpicke delayed advantage ~+50% relative vs restudy; project P3 calls spaced retrieval *the* durability event. First production is necessary but not durability. 25 vs 10 keeps first production meaningful (still 40% of a retrieval event) while steering toward what works.

---

#### 4. Levels and Spanish names — **AMEND** (kill fake curriculum-echo)

**Curve:** COUNTERSIGN thresholds 0 / 100 / 250 / 500 / 900 as a **gentle super-linear journey curve** (arithmetic A3 holds ~1.59×).

**Names-as-curriculum-echo:** **REJECT_CLAIM** as written. Pure XP thresholds cannot guarantee the learner “touched” the can-do family named on the level. That is marketing wearing domain clothes — same flattery class as “You can introduce yourself” at conf 0.55.

**Exact replacement — Levels:**

> **Levels (journey stages, not ability claims):**  
> XP thresholds: Nivel 1 (0) → 2 (100) → 3 (250) → 4 (500) → 5 (900) → continue ~1.6× band growth.  
> **Naming options (pick one in implementation; do not mix):**  
> **(A) Flavor-only (recommended for v1):** Spanish journey labels with **no ability implication** — e.g. «Primeros pasos», «Camino corto», «Paso firme», «Sendero», «Ruta» — or numbered only: «Nivel 3». Subcopy: “Journey stage — not a claim about what you can say.”  
> **(B) Domain-echo (only if gated):** Level name may use a can-do family string **iff** that family’s skill is ≥ emerging (or known for mastery-flavored names) on the sheet at unlock time; otherwise fall back to flavor-only. XP threshold alone never grants a can-do name.  
> Threshold math stays; **curriculum honesty is a gate, not a story.**

---

#### 5. UI — **AMEND**

| UI bit | Ruling |
|---|---|
| Header: level + XP bar | **AMEND** — must co-show ability counts; XP never solo |
| Level-up: one toast + grades-rail chip | **COUNTERSIGN** (one toast; no confetti spam) |
| Grade cards “+15 xp” attached to evidence | **COUNTERSIGN** — strongest honesty move in the proposal (points glued to event) |
| Weekly recap “+120 xp, 3 words rooted” | **AMEND** — include re-check / down signals when present; never recap XP-only |

**Exact replacement — header bullet:**

> Header: **ability counts** (durable-so-far · known · emerging) **primary**; level name + XP bar to next level **secondary** (same real estate as deleted can-do counter). Order is load-bearing: competence signal before journey volume (Deci et al. 1999: informational competence feedback d≈+0.33; controlling score chrome risks undermining).

---

#### 6. Data / implementation shape — **COUNTERSIGN** (with one pin)

Pure `xp.py` over grade ledger + progress ledger + epoch → derived totals: **right object class** (matches append-only history vs live sheet). Weights in ONE code table with doc as law: **COUNTERSIGN**.

**Pin:** epoch scoping must match progress ledger post-reset semantics (nodes post-epoch only; historical XP for pre-epoch events does not inflate post-reset ability theater). On epoch wipe, XP total resets with the epoch (journey of *this* learner identity), raw lines may remain on disk.

---

### Answers to the five risks (attacked)

**1. Monotone XP vs honesty — is the journey/state split sound?**  
**Sound only with dual-signal UI.** Ontology is fine (practice history ≠ ability). Phenomenology is not: a solo rising XP bar over a falling sheet flatters. **Falsifier that would kill the split:** if usability tests show learners treat XP as “I got better” after a documented ability drop and ignore sheet/rail, the header must drop XP or force ability-first layout permanently. Until then: ACCEPT_WITH_AMENDS (§2).

**2. Weight gaming / wrong behavior?**  
**Yes, three vectors:**  
(a) **Session XP** — pure time-on-app (KILL — rejected).  
(b) **Grade baiting** — XP inherits grade honesty; once-per-band + echo-exclude + no introduce-XP mitigate but do not eliminate model-side grade inflation (existing §3 problem; XP amplifies incentive). Mitigation already proposed is necessary, not sufficient; no new grade-from-XP feedback loop into the teacher prompt.  
(c) **Introduce→emerging spray** — 15×10 fills a 150 cap without durability; day cap 120 + once-per-band + higher retrieval weight reduces relative payoff of spray vs root.

**3. Duolingo pathologies at our scale?**  

| Pathology | Applies here? |
|---|---|
| Streak anxiety / loss aversion on streak break | **No** if we keep 2026-07-28 ban on streak chrome (do **not** add streaks “for free” later). |
| XP-farm easy lessons | **Yes, attenuated** — games @8 + first-prod @10 without retrieval; caps required. |
| Leaderboards / social shame | **No** (not proposed; do not add). |
| “Open app at 11:52 for one lesson” | **Weakly** — day cap + no session XP reduces; level-bar “almost there” compulsion remains (accept as mild; one toast only). |
| Metric decoupled from learning | **Main residual risk** — monotone XP always rises with any evidence event; dual-signal UI is the mitigation. |

**4. Level names from domain data — cute or confusing?**  
**Confusing if ungated.** XP threshold ≠ can-do touch. Either flavor-only or hard sheet gate (replacement in §4). Cute-without-gate is marketing.

**5. Is 150/day right? Is 20 vs 10 retrieval:first-prod right?**  
- **150/day:** slightly high (A6). **AMEND → 120/day** as start; re-estimate from live “honest busy session” telemetry.  
- **20 vs 10:** direction correct per testing effect (~1.5× delayed retention edge). **AMEND → 25 vs 10** to better match P3 priority without zeroing first production. Not a literature constant — pre-register revisit if learners stop producing new forms to farm retrieval only (anti-farm on interval thresholds is the structural fix).

---

### Kill-search clause

**Tried hardest to kill:** the entire XP layer — on the ground that 2026-07-28 already shipped an evidence-backed journey rail + countable ability header, and USER’s need (“feel that they are learning”) is **already the rail’s job**; XP is BLAP chrome that Deci/Nicholson warn will reorient attention from Spanish to score.

**Falsifier that would have killed the whole design:** if XP pays for any non-evidence event (session turns, login, exposure) **or** appears as the sole header signal **or** uses mastery language for sub-known bands. The draft **does** pay for session turns and risks solo-header XP — those claims are killed; the remainder can ship only with the amends above.

**Named claims killed this round:**  
1. “2026-07-28 did not ban XP/aggregation” (rewrite)  
2. Session ≥6 turns → 5 XP  
3. Error XP at streak ≥2  
4. “yours now” durable meaning  
5. Ungated domain level names as “real curriculum echo”  
6. 150/day as settled

---

### Summary scorecard

| Item | Ruling |
|---|---|
| Law reconciliation framing | **AMEND** — USER reopen, not “never banned” |
| Journey/state + monotone XP | **ACCEPT_WITH_AMENDS** — dual-signal UI + honest weekly recap |
| Weight table | **AMEND** — delete session XP; error gate 3+0; retrieval 25; durable copy; game caps |
| Anti-farm | **AMEND** — 120/day; interval-threshold retrieval; no seat-time |
| Levels curve | **COUNTERSIGN** thresholds; **AMEND** naming |
| UI | **AMEND** ability-primary header; COUNTERSIGN evidence-attached +xp |
| Data shape `xp.py` | **COUNTERSIGN** (+ epoch wipe pin) |
| Whole design | **ACCEPT_WITH_AMENDS** — not REJECT_WHOLE |

---

### Overall status (VERDICT LAST)

**ACCEPT_WITH_AMENDS** — do **not** ship the proposal as written.

Ship XP only as a **derived journey-volume projection** over existing evidence ledgers, under a **USER 2026-08-05 reopen** of the 2026-07-28 XP/levels non-goal, with:

1. Session/engagement XP **deleted**  
2. Error and can-do gates aligned to **shipped sheet/ledger honesty**  
3. Ability counts **primary** in the header; XP secondary  
4. Level names **flavor or hard-gated**, never pure-XP “curriculum echo”  
5. Day cap **120**, retrieval **25**, durable copy non-permanent  
6. Weights + anti-farm rules as the single code table / doc law  

**Promotion condition:** fold exact replacement blocks into the proposal file; no PEDAGOGY teaching-rule change required if XP remains pure projection of existing evidence events. Any future XP for introduction, seat-time, or sub-known mastery language fights ENGINEERING honesty / §3.2 and loses.

**CORRELATED_AGREE note:** agreement with Claude on “evidence-backed only, code-owned, sheet stays ability truth” is one correlated vote until non-overlapping primary sources (Deci 1999; Roediger & Karpicke 2006; 2026-07-28 shipped gates) are cited — those sources are what upgrade the dual-signal and weight amends above, not mutual AI assent.

---

---

## Adjudication (Claude, 2026-08-05 — round 1 closes)

All six kills ACCEPTED with reasons:
1. **Law framing**: this IS a reopen of the 2026-07-28 XP non-goal
   under USER's 2026-08-05 directive — not a claim the ban never
   applied. Framing corrected in the final doc.
2. **Session XP deleted** — seat-time is the Goodhart class the
   2026-07-28 round already killed once; reimporting it as 5xp was
   the same bug at lower amplitude.
3. **Error gate aligned** to shipped streak≥3 & count==0.
4. **Durable copy** = "holding at the 2-week check", never "yours now".
5. **Level naming**: adjudicated to Grok's option (B) GATED domain-echo
   (not flavor-only v1): the gate is one sheet lookup at unlock time,
   and a level name that is TRUE when granted serves the user's actual
   request (feel real learning) better than flavor labels. Fallback to
   «Nivel N» whenever ungated — never mixed, never granted by XP alone.
6. **Caps**: 120/day start; retrieval 25; game ≤2/session ≤3/day;
   revisit with two weeks of live telemetry (pre-registered).

Dual-signal header accepted: ability counts (durable-so-far · known ·
emerging) primary, XP bar secondary. Note for the record: the old
header can-do counter died 2026-08-04 as a LONE widget ("I dont think
it does anything"); it returns here as the ability half of a dual
signal with the XP bar giving it a reason to exist.

**Converged: ACCEPT_WITH_AMENDS enacted; final plan at
docs/design-xp-progression.md. One round sufficed — no round 2.**
