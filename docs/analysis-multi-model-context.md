# Analysis: per-turn context anatomy + multi-model decomposition (2026-08-06)

USER: "really layout in a .md what is in the context for each turn. What
is expected in the response. Then look at what parts of that process
could be handled by gemini 3.5. Does all of it need to go to the
advanced model? Are there parts that could be summarized? … It might be
that we need to bring in grok 4.5 for planning phases. This is not a
request for new code. I want a deep multi round analysis."

Status: **CONVERGED 2026-08-06** (two rounds, Claude ⇄ Grok; both authors'
full measurements and kills below). This header is the executive summary.

## CONCLUSIONS (converged verdict)

**The question was "which parts can a cheaper model handle?" The
measured answer is: almost none of the ROUND path — but that was the
wrong question. The money is in cache reality and history growth, and
the obligations worth moving go to CODE, not to cheaper models.**

Ship order (each with go/no-go conditions in Grok's §4 below):

- **P0 — Make the static prefix cache real.** 8,905 tokens of identical
  instructions are re-billed every turn (1.34¢). Gemini's cache is dead
  (2.9% ledger hit rate); grok's works (34.6% aggregate, 70-90% hot).
  Provider choice and cache reality are ONE decision. Go: a provider
  path with measured aggregate hit-rate ≥30%, or Gemini explicit-cache
  smoke passing with storage ≤50% of savings.
- **P1 — Bound plan-cycle history (co-primary).** Live sessions run
  p50 19k / p90 24k input; unbounded history dwarfs every other
  dynamic block. A cheap async summarizer (facts-only, MANDATORY
  verbatim learner-error spans + last 2-3 raw exchanges) cuts
  0.6-1.7¢/turn late-session at zero reply latency. This is the ONE
  place a 3.5-class model enters the loop safely: summarizing facts,
  off the latency path, never touching judgment.
- **P2 — Morph tables from code + the conjugation DB** (after the
  person-label rebuild; ≥90% lemma-coverage gate). Not a cost lever
  (~0.07¢) — a correctness lever that removes one obligation from the
  teacher's juggling contract.
- **P3/P4** — optional prompt diet (conditional game schema, careful
  tool compression ≤0.11¢) and a zero-authority shadow audit ledger.

**NO-GO list (each killed on evidence, reopen conditions recorded):**
cheap-model rounds (refuted twice — cheap models fail on breadth of
simultaneous obligations, not single tasks); post-hoc cheap grading
(the atomic-commit fork: nothing is simultaneously atomic, lag-free,
and non-blocking; and it delegates ability claims to the weaker
judge); premium-planner-for-cost (grok-4.5 plans are 3x richer but a
capable round model's execution is the ceiling — pilot showed +42%
grading breadth and nothing else; full N=12 blind trial specified
below if ever wanted for quality).

**Joint P0+P1 is the only path that cuts ≥1¢/turn without moving
teacher authority off the advanced model.** Everything below is the
evidence: measured anatomy (±1-token verified), production cache
rates, live input percentiles, the C4 pilot, both authors' kills.

---

 All token numbers below are MEASURED via the Gemini
countTokens API against the current builders (2026-08-06), not
estimated.

---

## 1. What is in the context — measured anatomy

### 1.1 ROUND turn (the common case; mid-session, ~turn 10)

| Block | Tokens | Volatility |
|---|---:|---|
| Stance (`conversational_tutor.md`) | **5,742** | STATIC (changes only on deploy) |
| Persona (`tutor_persona.md`) | **1,268** | STATIC |
| ROUND_NOTE (work-from-your-plan) | **112** | STATIC |
| Tool schemas (update_character_sheet + show_game) | **1,783** | STATIC |
| Task: model's own session plan | **752** | static WITHIN a plan cycle |
| Task: sheet (round view, evidence-only) | **139** | dynamic (slow) |
| Task: facts (due items, mode gaps, session facts, learner msg) | **~370** | dynamic |
| History (append-only cycle suffix; ~2.2k @ 10 turns) | **~2,160** | dynamic, grows ~200/turn |
| **TOTAL** | **≈ 12,300** | |

**The headline: 8,905 tokens (72%) of every round turn is byte-identical
static text**, re-billed at full input price every turn because Gemini
implicit caching is dead for this key (measured 2026-08-05: zero cached
tokens on byte-identical repeats, both endpoints, all models; probe
script `scripts/probe_gemini_cache.py`). Another 752 (6%) is static
within a plan cycle. Truly dynamic content ≈ 2,650 tokens (22%).

### 1.2 PLAN turn (session open on non-cached sheets; replans)

Round-turn statics PLUS: pedagogy teaching cut **1,987**, plan
instructions **725**, full sheet **2,560** (vs 139 round view), full
history at replan time. Total ≈ **14,600–17,000**. Frequency: ~1–2 per
session (blank sheets: zero — the cached blank plan covers them).

### 1.3 What is expected in the response (the full contract)

Every round reply must carry, in ONE model response:
1. `<tutor>` tags: acknowledge / recast / explain / model / try —
   teaching judgment + persona voice + language-mix law.
2. `<morph …>` card — REQUIRED every turn (paradigm table, 3–6 rows).
3. `update_character_sheet` tool call when evidence warrants — band
   anchors, multi-layer (lexicon+grammar+skills), evidence quotes.
4. Optionally `show_game` tool call (full game JSON: items, meanings).
5. Optionally `<image concept=…/>`, `<plan>` revision, `<replan/>`.
Measured output: 200–540 tok typical replies (3.6-flash); plans 750–900.

**This response contract is the multi-objective juggling that
gemini-3.5-flash-lite measurably failed** (see §3 evidence table). Any
decomposition that REDUCES the number of simultaneous obligations per
call changes which models can serve it.

### 1.4 Cost/latency baseline (gemini-3.6-flash, measured)

- Round: ~12.3k in × $1.50/M + ~350 out × $7.50/M ≈ **2.1¢/turn**, 5–20s.
- Of that, the static 8.9k = **1.34¢/turn** paying for re-reading
  unchanged instructions. A 20-turn session ≈ 42¢, of which ≈ 27¢ is
  static re-billing.

---

## 2. Decomposition candidates (for round-2 adjudication)

### C0 — Status quo (baseline for all arithmetic)

### C1 — Prompt diet (same single model, fewer tokens)
- **Tool-schema compression**: 1,783 tok of verbose descriptions; the
  band anchors + worked example could compress ~40% without losing the
  contract (they were written for a weaker model's compliance).
  RISK: this session proved instruction cuts become behavior cuts;
  every compression needs a gate run.
- **History → rolling summary**: a cheap model maintains a ~300-tok
  rolling summary; advanced model gets summary + last 2–3 raw
  exchanges. Saves ~1.5–2k tok/turn late-session AND bounds context
  growth. Cheap-model call runs async AFTER each turn (zero reply
  latency). Evidence FOR: history is facts, not instructions —
  summarizing facts is the safe kind of compression.
  RISK: teaching continuity lives in exact wording sometimes (what
  exactly did the learner say wrong three turns ago).
- Estimated effect: −2–3.5k tok/turn (−0.3–0.5¢), no latency change.

### C2 — Turn-type split (cheap rounds, premium plans) — **REFUTED**
Measured this week and failed: lite ignored its own plan in rounds
(wrote the assessment beat into the plan, never executed it), fixated
on strugglers, graded garble. Rounds are where the juggling lives;
plans are the EASY half. This candidate is the naive-intuition trap;
the evidence says the OPPOSITE allocation.

### C3 — Response-contract decomposition (the promising family)
Split the five response obligations across calls/models/code:

- **C3a: morph card → CODE + conjugation DB.** The advanced model
  emits only `<morph lemma="estar" highlight="estás"/>`; code renders
  the table from the Jehle DB (637 verbs, already shipped for the XP
  audit). Effects: −60–120 output tok/turn on the premium model,
  tables become ground-truth-correct by construction, and one
  obligation leaves the juggling contract. English glosses per row:
  the association table + a tiny cheap-model call for rows not in
  inventory. STRONGEST candidate: quality UP, cost DOWN, obligations
  DOWN.
- **C3b: grading → cheap model, post-hoc, off the latency path.**
  Advanced model replies WITHOUT tools (drop 1,783 tok schemas from
  its input; drop tool JSON from its output). A 3.5-class model then
  gets (learner msg + advanced reply + band anchors + worked example)
  and emits the tool call asynchronously. Evidence FOR: grading-v2
  showed lite grades BROADLY with the worked example; the advanced
  reply usually names the error explicitly, making grading
  extraction-shaped rather than judgment-shaped. Evidence AGAINST:
  lite inflates garble (the XP audit contains this mechanically);
  grades would land 1 turn late for the teacher's own next-turn
  reading of the sheet (mitigation: sheet lag is one turn, plans
  don't change that fast).
  Effects: premium input −1.8k (−0.27¢), premium output −~100 tok,
  reply latency −(tool-JSON generation time), grading cost at lite
  prices ≈ +0.1¢. Net ≈ −0.3¢/turn and faster replies.
- **C3c: games → two-stage.** Advanced model decides "match game on
  these 4 items now" in one line; cheap model expands to full game
  JSON (items+meanings are inventory lookups). Saves premium output
  only when games fire (rare); low value, low risk.

### C4 — Premium planner (grok-4.5 or better for plan turns)
Plans are 1–2 per session, latency-tolerant on replans, and the
highest-leverage artifact in the architecture (the teacher follows its
plan religiously — measured both ways: 3.6 executes its plan; lite's
failure was NOT plan quality but plan-following). Cost of grok-4.5 at
~15k in/1k out per plan ≈ 2–4¢/plan × 2 = pennies per session.
QUESTION for the round: does a better plan measurably improve rounds
executed by 3.6-flash? (Testable: same session seeds, plan swapped,
blind-score the transcripts.) If yes, this is cheap quality; if no,
skip the dependency.

### C5 — Static-prefix relocation (no model change)
72% static re-billing exists ONLY because Gemini caching is dead. Two
escapes: (a) explicit caching via native API (storage-fee math done
2026-08-05: breaks even ~4 turns/hour sustained — borderline at tester
traffic, revisit at scale); (b) a provider whose caching works — grok's
prefix cache measurably absorbed 70–90% of input (billed at 1/7th);
DeepSeek's cache reported hits through their Anthropic endpoint. Model
choice and cache reality are ONE decision, not two.

### C6 — Async shadow auditor (cheap, zero-latency)
A 3.5-class model audits each grade against the anchors after the
fact, flagging disagreements to the eval ledger (never blocking, never
prompting the teacher). Extends the XP audit's mechanical checks with
semantic ones. Pure telemetry; feeds the grade-inflation watch.

---

## 3. The capability evidence table (this week, this system)

| Task shape | 3.5-flash-lite result | Where measured |
|---|---|---|
| Multi-objective round (teach+persona+morph+grade+menus) | FAILED repeatedly (flat persona, skills-only grading, inert menus, plan written-not-executed, fixation HARD fail) | gates 2026-08-05/06 |
| Single-purpose classify (signal classifier) | WORKS, 0.8–1.1s, in production | 2026-07-28 promotion |
| Grading WITH worked example, narrow focus | Broad coverage, but inflates garble | grading-v2 gate |
| Persona with few-shot | Recovers voice | 2026-08-05 A/B |
| Plan WRITING (not following) | Wrote correct plans incl. assessment beats | escalation-2 run |

Working hypothesis for the round: **cheap models fail on breadth of
simultaneous obligations, not on any single obligation.** Decomposition
candidates should therefore move OBLIGATIONS, not context bulk, to
cheap models — and move BULK to code or caches where possible.

## 4. Open questions for Grok round 1

1. Verify the anatomy §1 independently (the builders are in the repo;
   recount at least stance/tools/plan-task).
2. Attack C3b hardest: is post-hoc grading by a cheap model acceptable
   under the honesty laws (grades land one turn late; teacher reads a
   slightly stale sheet)? What breaks?
3. C4: design the cheapest DECISIVE experiment for "does premium
   planning improve cheap-round execution?"
4. Propose candidates I missed (independent list before reading mine
   if your process allows).
5. Rank all candidates by (expected ¢ saved per turn) × (risk of
   teaching regression), with arithmetic.


---

## GROK (Grok Build CLI (1e1687c1cf6a)) - 2026-08-06 18:28 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll load the full offloaded prompt and the collab skill, then independently verify the measured context anatomy and attack the load-bearing claims.Continuing through the full analysis and the inlined builder sources so I can recount tokens independently.I have the real repo. Next I'll recount context tokens from the builders and pull ENGINEERING honesty rules that bear on C3b.Next I'll pull tool schemas, the prompt-build path, and pricing claims so the anatomy and cost math stand on independent numbers.I'll call Gemini countTokens on the real prompt blocks and cross-check history policy against ENGINEERING §3.3.I have independent token recounts and real-session residuals. Writing the append-ready research round with VERDICT-LAST structure.# GROK research round 1 — multi-model context anatomy (2026-08-06)

**Role:** independent second author. Claude’s draft treated as DATA only.  
**Method:** Gemini `countTokens` on live builders + `logs/` usage; code path read in `tutor/turn_pipeline.py`, `tutor/session_plan.py`, `tutor/character_sheet.py`, `tutor/conjugations.py`, `tutor/costs.py`; ENGINEERING §1.1 / §3 honesty; web check of Gemini/xAI cache+price tables.

---

## 1. My picture (dated pins) — generate first, then compare

### 1.1 Independent ROUND anatomy (measured 2026-08-06 via `countTokens` on `gemini-3.6-flash`)

| Block | My tokens | Claude | Δ | Volatility |
|---|---:|---:|---:|---|
| Stance `conversational_tutor.md` | **5741** | 5742 | −1 | STATIC |
| Persona `tutor_persona.md` | **1268** | 1268 | 0 | STATIC |
| `ROUND_NOTE` | **111** | 112 | −1 | STATIC |
| Tool schemas (JSON compact) | **1660** | 1783 | −123 | STATIC (wire-format dependent) |
| Tool schemas (indent=2) | **2116** | 1783 | +333 | same |
| Pedagogy teaching cut | **1986** | 1987 | −1 | PLAN only |
| `PLAN_INSTRUCTIONS` | **724** | 725 | −1 | PLAN only |
| Sheet round_view (current `logs/character_sheet.json`) | **1451** | 139 | **+1312** | dynamic, **state-dependent** |
| Sheet full (same sheet) | **3908** | 2560 | **+1348** | PLAN only, state-dependent |

**Static sum (my compact tools):**  
5741 + 1268 + 111 + 1660 = **8780** tok → 8780/12300 = **71.4%**.  
**With Claude’s 1783 tools:** 5741+1268+111+1783 = **8903** → **72.4%**.  

Claude’s headline **“~72% static” is ACCEPT_AS_WRITTEN** for the static *instruction* class. The sheet-token claims are **not portable** — they are a measurement of one sheet snapshot, not a system constant.

### 1.2 Cost baseline arithmetic (recomputed)

Rates from `tutor/costs.py` (pinned for `gemini-3.6-flash`): **$1.50/M in, $7.50/M out**.

\[
\begin{align*}
\text{round} &= 12300 \times 1.50/10^6 + 350 \times 7.50/10^6 \\
&= 0.01845 + 0.002625 = \$0.021075 \approx \mathbf{2.11¢/turn}
\end{align*}
\]

\[
\text{static re-bill} = 8905 \times 1.50/10^6 = \$0.01336 \approx \mathbf{1.34¢/turn}
\]

20-turn session: \(20 \times 2.11 = 42.2¢\); static portion \(20 \times 1.34 = 26.7¢\).  
**Claude §1.4 arithmetic ACCEPT_AS_WRITTEN.**

### 1.3 Live-session pin (not Claude’s synthetic turn-10)

From `logs/sessions/2026-08-04/20260804-174404-conversational-web.requests.jsonl` (Gemini 3.6, 2026-08-04):

| Turn | Billed in | `cached_input_tokens` | History msgs (logged) |
|---:|---:|---:|---:|
| 0 open | 9114 | **0** | 0 |
| 1 | 18490 | **0** | 2 |
| 2 | 19290 | **0** | 4 |
| 3 | 19368 | **0** | 6 |
| 4 | 19444 | **0** | 8 |

From last 37 `gemini-3.6-flash` cost events: **input min 6673 / med 10084 / mean 12887 / max 29106**; **cached nonzero = 0/37**.  

**Cache-dead claim ACCEPT_AS_WRITTEN** (measured in production, not only probe script).  
**Mid-session is not always ~12.3k** — observed open≈9k, early rounds≈18–19k (older *clipped* stance in that log), recent cost median≈10k, tail to **29k**. Any savings model that treats 12.3k as a constant understates late-session history risk.

### 1.4 History policy pin (code vs briefing)

`stage_prompt_build` (2026-08-04 cache arm): ROUND history = **append-only plan-cycle suffix** from `plan_cycle_start`, not a sliding 12-message window. Comment in code explicitly retired the 12-window because it broke prefix caching every turn.

**Stale text still alive:** `GROK.md` and parts of ENGINEERING §3.3 still say “versioned 12-message window.” That is doc debt; the running system is plan-cycle append-only. Claude’s history row is closer to **code** than to the briefing.

### 1.5 My decomposition candidates (generated *before* weighing Claude’s labels)

| ID | Idea | Obligation moved? | Attacks static 72%? |
|---|---|---|---|
| **G1** | Make prefix cache real (explicit Gemini cache **or** provider with working implicit cache) | No | **Yes — primary** |
| **G2** | Stance diet with gate-held regressions (cut static instruction bulk) | No | Yes |
| **G3** | Code-rendered morph from **structured** paradigm data (not bag-of-forms) | Yes (−1 juggle) | No (output) |
| **G4** | History: rolling summary + **verbatim error/learner spans** last K turns | Soft compress facts | Dynamic growth |
| **G5** | Conditional tools: ship `show_game` schema only when plan/menu says games this beat | −½ tool bulk often | Partial |
| **G6** | Concurrent same-turn grader (cheap model **parallel** to teach call, join before `stage_sheet_commit`) | Yes, no lag | Partial (−tools on teacher) |
| **G7** | Hard-turn router: cheap model only on low-stakes turns; premium on repair/assessment/replan | Yes (routing) | Sometimes |
| **G8** | Premium planner only (quality, not ¢) | No | No |
| **G9** | Shadow semantic grade auditor (telemetry only) | No | No |
| **G10** | Teacher emits short grade-intent; code validates bands against Zipf/Jehle before commit | Partial judgment→code | Small |

---

## 2. Verify / refute table (load-bearing claims)

| # | Claim (Claude) | Ruling | Evidence / arithmetic |
|---|---|---|---|
| L1 | Token table measured via Gemini countTokens 2026-08-06 | **ACCEPT_WITH_AMENDS** | Stance/persona/ROUND/pedagogy/plan_instr match ±1. Tools 1783 is plausible wire format; my compact JSON=1660, indent=2116. **Sheet 139/2560 are snapshot-specific** (I measure 1451/3908 on current sheet). |
| L2 | 8905 tok = 72% static, re-billed every turn | **ACCEPT_AS_WRITTEN** | 8903–8905 with Claude tools; live `cached_input_tokens=0` on Gemini. |
| L3 | Gemini implicit cache dead for this key (2026-08-05) | **ACCEPT_AS_WRITTEN** | 0/37 recent cost events; 0 cached in 2026-08-04 session. |
| L4 | Round ≈2.1¢; static 1.34¢; 20-turn 42¢ / 27¢ static | **ACCEPT_AS_WRITTEN** | Recomputed §1.2. |
| L5 | PLAN ≈14.6–17k; +ped 1987 +instr 725 +full sheet 2560 | **ACCEPT_WITH_AMENDS** | Ped/instr ±1 OK. Full sheet **not** fixed at 2560 (3908 on current sheet) → PLAN total can exceed 17k. |
| L6 | History ~2.2k @ turn 10, ~200/turn | **ACCEPT_WITH_AMENDS** | Directionally right under plan-cycle growth; **unbounded** within cycle. Cost log max **29106** input falsifies “always ~12.3k.” |
| L7 | Response contract is multi-objective juggling lite failed | **ACCEPT_AS_WRITTEN** (on stated gate evidence) | §3 table + 2026-08-05/06 gates cited; I did not re-run gates this round. |
| L8 | Working hypothesis: cheap models fail on **breadth**, not single tasks | **ACCEPT_WITH_AMENDS** | Classifier + narrow grading-v2 support breadth story. Steelman not killed: plan-**following** and long-horizon fixation may be a distinct hard skill, not pure juggle-count. Round 2 must disentangle. |
| L9 | C2 (cheap rounds / premium plans) REFUTED | **ACCEPT_AS_WRITTEN** pending full gate artifacts | Matches §1.1 architecture (rounds hold judgment). Naive split remains the intuition trap. |
| L10 | C3a: Jehle 637 verbs already shipped → code can render morph tables | **REJECT_CLAIM (as stated)** | `domain/spanish_a1/conjugations.json`: **637 verbs, flat form lists**, not person×tense labeled paradigms. `forms_of("estar")` returns an unsorted bag. **Cannot** render `yo/tú/él…` rows by construction without new structure (or model still emits forms). Verb count **ACCEPT**. |
| L11 | C3b net ≈ −0.3¢/turn and faster | **ACCEPT_WITH_AMENDS on ¢; REJECT as honesty-safe default** | My ¢: −1783·1.5e−6 −100·7.5e−6 + lite(~2.5k·0.3 +150·2.5)/1e6 ≈ **−0.23¢** net (Claude −0.3¢ in range). Honesty: see §3. |
| L12 | C4 grok-4.5 plan ≈2–4¢/plan | **ACCEPT_WITH_AMENDS** | Official grok-4.5 short-context: **$2.00/M in, $0.30/M cached, $6.00/M out** (xAI pricing page, crawled 2026-08-06). \(15000×2e−6 + 1000×6e−6 = \$0.036\) = **3.6¢/plan**. |
| L13 | Teacher follows its plan religiously (3.6) | **CORRELATED_AGREE — one vote until independent transcript sample** | Same-era claim chain; need blind plan-adherence metric on held-out sessions. |
| L14 | C5 break-even explicit cache ~4 turns/hour | **ACCEPT_WITH_AMENDS** (order of magnitude) | At 10% cached rate ($0.15 vs $1.50): save **1.20¢/turn** on 8905 static. Storage fee depends on model tier (~$1/M tok/hour on several Gemini SKUs) → sparse tester traffic can erase gains; dense sessions win hard. |
| L15 | Morph required every turn | **Not refuted; flag for law review** | Contract claim; cost of *obligation* may exceed cost of tokens. Out of scope for ¢-only ranking but load-bearing for decomposition. |

---

## 3. C3b attacked hardest (honesty laws)

### What C3b proposes
Premium teach call **without** tools → async cheap model grades from (learner, tutor reply, anchors) → sheet update lands **after** the teach reply, typically **one turn late** for the teacher’s next sheet read.

### Law surface (not vibes)

1. **ENGINEERING §1.1** — code owns **facts** (honest, complete) + **honesty** (sheet writes only by deliberate graded tool calls with evidence) + audit.  
   - C3b preserves “tool call with evidence” as the write path → letter of tool-write law can hold.  
   - It **breaks completeness of facts on the next teaching decision**: the teacher’s ROUND context is missing the just-earned grade. Incomplete facts to the teacher is a §1.1 *facts* failure even if the ledger eventually becomes honest.

2. **§3.2 ability honesty** — ability moves on evidenced production.  
   - Delayed write is still evidence-based *eventually*.  
   - **Same-session teaching** that re-elicits a just-succeeded form, or skips a needed repair because the error was not yet committed, is the practical honesty break: the sheet the teacher sees is a **stale ability surface**.

3. **§1.1 “the model is the teacher”** — grading is a teaching judgment (band anchors, multi-layer, garble≠emerging).  
   - Moving it to a model that **measurably inflates garble** (Claude’s own §3 / grading-v2) means the **author of ability claims is the weaker judge**.  
   - That is not “record-keeper code”; it is **delegating teacher authority** to a model known to fail the judgment that XP audit exists to catch.

4. **Atomic commit** (`stage_sheet_commit`) — “turn commits or it doesn’t.”  
   - Post-hoc async grade after the learner-visible reply means either:  
     (a) commit without grade then patch → **two durable sheet states per turn** (reopens CHAR-BUG-001 class), or  
     (b) hold commit until grader returns → **not off the latency path** (falsifies C3b’s latency claim).  
   - Claude did not price this fork. There is no third option that is both atomic and lag-free and non-blocking.

5. **No-hide / dual-author opacity** — if cheap grader and premium teacher disagree on what “counts,” the learner-facing XP/grade feed can show a grade the teacher never intended. Unless both authors are logged and challengeable (**SHEET-CHALLENGE DEBT** still open), this is silent authority split.

### What breaks in product terms (not abstract)

| Failure mode | Mechanism | Severity |
|---|---|---|
| Re-probe / fixation | Teacher doesn’t see last turn’s `emerging` → re-teaches credited item | High (lite already fixates) |
| Assessment mis-scheduling | Plan EVIDENCE beat thinks gap open after it closed (or reverse) | High (mode_evidence_gaps just shipped 2026-08-06) |
| Garble → emerging | Lite inflation lands in durable sheet before human notices | **Critical** (ability lie) |
| Double-commit / race | Async grade vs next turn’s premium grade | Medium–high |
| Latency claim false | Must await grader to keep atomic commit | Collapses C3b ¢/latency pitch |

### Mitigation Claude offered — stress test

> “Sheet lag is one turn; plans don’t change that fast.”

**Falsifier:** one successful production that should stop a §2.8 repair loop or close an IT/PR gap. One turn of wrong agenda is exactly how fixation and assessment starvation reappear. Plans are sticky; **sticky + stale evidence** is worse than sticky + fresh evidence.

### C3b ruling

**REJECT_CLAIM** as a default architecture move under honesty laws.  

Allowed only as a **pre-registered experiment** with:
- join-before-commit (so not truly post-hoc latency-free), **or**
- explicit “provisional grade” lane that cannot raise bands above `unknown→emerging` without premium co-sign,
- and mechanical anti-garble (Zipf/Jehle) hard-blocking lite promotions.

Prefer **G6 concurrent same-turn grader** or **G10 teacher short grade-intent + code audit** over pure post-hoc C3b.

**Kill-search (this round’s kill):**  
**Named claim killed: C3b “post-hoc cheap grading is honesty-compatible because lag is only one turn.”**  
Falsifier that killed it: §1.1 complete-facts duty + atomic commit fork + documented lite garble inflation. A single successful production that should change next-turn agenda is enough; no multi-session average required.

---

## 4. C4 — cheapest decisive experiment  
*(Does premium planning improve cheap/constant-round execution?)*

**Do not** test “premium plan + cheap rounds” (C2 already refuted). Test:

> Holding the **ROUND model fixed** at `gemini-3.6-flash`, does a higher-quality PLAN change round behavior?

### Design (minimum decisive)

| Slot | Choice | Why |
|---|---|---|
| ROUND model | **Always** `gemini-3.6-flash` | Isolates plan quality |
| PLAN arms | **A:** 3.6-flash plan (control) · **B:** grok-4.5 (or grok-4.20-non-reasoning if 4.5 unavailable) plan | Premium vs status quo |
| Seeds | N=**12** session seeds (6 blank-sheet, 6 mid-sheet with known mode gaps), fixed AI-student or scripted learner lines | Blank vs non-blank interact with placement |
| Swap protocol | Run PLAN once per arm → **freeze plan text** → replay **identical learner utterances** for T=8 ROUND turns | Removes learner variance |
| Blinding | Scorer sees transcripts **without** plan author labels | Required |
| Primary metrics (pre-register) | (1) Plan-adherence rate: fraction of ARC beats with observable attempt; (2) Assessment-beat execution if EVIDENCE named IT/PR; (3) Blind rubric mean (frozen rubric); (4) Fixation: max consecutive turns on same struggler key | Must be frozen before scoring |
| Kill bar | B wins if adherence **+0.15 absolute** OR assessment execution **+0.20** at α≈0.1, **and** no drop >0.25 on blind mean | If B fails kill bar → **skip premium plan dependency** |
| Cost | ~24 plan calls + 24×8 rounds. Extra plan cost ≈ \(12 × (3.6¢−3.0¢) ≈ 7¢\) if using 4.5; total LLM cost dominated by rounds (~$2–4 for whole experiment) | Cheapest decisive |

**Not decisive (do not run as C4):** live multi-learner A/B without frozen learner lines; scoring plan prose quality alone; swapping ROUND model in the same experiment.

---

## 5. Ranking: expected ¢ saved × regression risk

**Score used:** \(\mathrm{EV} = ¢_{\text{save}} \times (1 - P_{\text{reg}})\).  
\(P_{\text{reg}}\) = subjective probability of teaching regression severe enough to fail a gate or blind rubric drop ≥0.25. Show both EV and raw ¢.

| Rank | Candidate | ¢/turn (est.) | \(P_{\text{reg}}\) | EV ¢ | Notes |
|---:|---|---:|---:|---:|---|
| 1 | **C5 / G1 cache reality** | **+1.20** | 0.10 | **+1.08** | \(8905×(1.50−0.15)/10^6=1.20¢\). Architecture-preserving. |
| 2 | G7 hard-turn routing | +0.40 | 0.50 | +0.20 | Needs classifier reliability; C2-adjacent risk |
| 3 | C1 history summary (G4, with verbatim spans) | +0.26 | 0.40 | +0.16 | Late-session max 29k makes this **more** important than Claude ranked |
| 4 | G6 concurrent grader (not post-hoc) | +0.20 | 0.35 | +0.13 | Keeps atomic commit; still dual-judge risk |
| 5 | G5 conditional `show_game` tools | +0.15 | 0.20 | +0.12 | Low drama |
| 6 | C1 tool-schema compress ~40% | +0.11 | 0.35 | +0.07 | \(0.4×1783×1.5e−6=0.107¢\) |
| 7 | **C3a morph→code** (after structure fix) | +0.07 | 0.15 | +0.06 | **¢ small; quality EV high** — re-rank on quality-adjusted utility if USER cares |
| 8 | **C3b post-hoc grade** | +0.23 | **0.55** | **+0.10** | ¢ OK; honesty EV poor → **do not promote** |
| 9 | C3c games two-stage | +0.02 | 0.15 | +0.02 | Rare fire |
| 10 | C6 shadow auditor | −0.05 | 0.05 | −0.05 | Buy telemetry, not savings |
| 11 | **C4 premium plan** | **−0.03** amort. | 0.25 | −0.02 | Quality bet only; run experiment §4 |
| — | C2 cheap rounds | (+1.50 hyp.) | 0.85 | +0.23 but **REFUTED** | Exclude from ship list |

**Quality-adjusted note (not pure ¢):** If USER utility weights “wrong morph / wrong grade” above 0.1¢, **C3a (fixed)** and **anti-garble** leap above C1 compress. Pure ¢ ranking undervalues C3a; I flag that explicitly.

**CORRELATED_AGREE with Claude:** C2 refuted; obligation-moving > bulk-moving for *cheap models*; C5 is the only large ¢ lever without model split. That agreement is **one vote** until cache hit rates are re-measured on a non-Gemini or explicit-cache path.

---

## 6. What Claude MISSED

1. **Sheet tokens are not constants** — 139 vs my 1451 round_view on the live sheet; all PLAN/ROUND totals need “sheet percentile” not a point estimate.  
2. **C3a structural hole** — Jehle is lemma→form-list, not paradigm grid; “code renders table” is not shippable as written.  
3. **Atomic-commit fork for C3b** — post-hoc vs one-commit is unresolved; latency savings claim may be illusory.  
4. **History unbounded in plan cycle** — 12-window is dead in code; late-session 20k–29k inputs dominate tool-schema ¢.  
5. **Stale law/briefing (12-msg window)** — ENGINEERING/GROK vs `stage_prompt_build` mismatch should be fixed in a doc-sync, not silently assumed.  
6. **Stance once clipped** — 2026-08-04 log stance 4358 tok vs current 5741; any historical cost comparison must condition on prompt version.  
7. **Conditional tools (G5)** and **concurrent grader (G6)** as C3b alternatives.  
8. **G10** grade-intent + Zipf/Jehle mechanical floor — attacks garble without removing teacher from the loop.  
9. **Morph-every-turn obligation** as a policy cost, not only an output-token line.  
10. **C4 cost is not free quality** — ~3.6¢/plan on grok-4.5; amortized noise vs round cost unless adherence moves.

---

## 7. Round 2 measurements that must run

Pre-register and execute before any more architecture prose:

1. **Anatomy matrix:** countTokens on (blank sheet, thin evidence, fat evidence) × (turn 1, 10, 20) × (plan, round) — report p50/p90, not single points.  
2. **Tool wire tokens:** measure tools as actually sent by the Gemini adapter (not hand-JSON), residual vs billed input.  
3. **Cache path smoke:** explicit context cache on static prefix (stance+persona+ROUND_NOTE[+tools]) for one 20-turn synthetic session; report `cached_input_tokens` and storage USD. Parallel: one session on **grok-4.20** or **DeepSeek** with identical builders — cache hit rate.  
4. **C3a feasibility spike (no prod):** can we derive person-labeled present-indicative tables for A1 core verbs from Jehle+rules, coverage % of morph cards in last 50 turns? Kill C3a if coverage <90% of produced morph lemmas.  
5. **C3b honesty experiment (lab only):** dual-run 30 turns: premium+tools vs premium+async lite grade; score (a) band agreement vs human, (b) garble promotion rate, (c) next-turn agenda thrash. Pre-register kill if lite garble-promotion > control +5pp.  
6. **C4 plan-swap experiment** exactly as §4 (N=12 seeds).  
7. **Hypothesis split test:** single-obligation lite (grade only / morph only / teach-only) vs dual vs full juggle — isolates breadth vs plan-following.  
8. **Doc-sync:** 12-message window language → plan-cycle suffix in ENGINEERING §3.3 + GROK.md (process, not product).

---

## 8. Per-item rulings (Claude candidates)

| Item | Ruling |
|---|---|
| C0 baseline anatomy+¢ | **ACCEPT_WITH_AMENDS** (sheet/history as distributions) |
| C1 prompt diet | **ACCEPT_WITH_AMENDS** — prioritize history bound over tool 40% cut; gate every cut |
| C2 cheap rounds | **ACCEPT_AS_WRITTEN (refuted)** |
| C3a morph→code | **ACCEPT_WITH_AMENDS** — only after structured paradigms; else REJECT as overclaim |
| C3b post-hoc cheap grade | **REJECT_CLAIM** (honesty / atomic commit / garble) |
| C3c games two-stage | **ACCEPT_AS_WRITTEN** (low value) |
| C4 premium planner | **ACCEPT_AS_WRITTEN as experiment**; not as cost win |
| C5 static-prefix / cache | **ACCEPT_AS_WRITTEN** — **highest EV** |
| C6 shadow auditor | **ACCEPT_AS_WRITTEN** (telemetry, negative ¢) |
| Breadth hypothesis | **ACCEPT_WITH_AMENDS** — must split from plan-following in r2 |

---

## 9. Kill-search clause

**Killed this round:** C3b’s claim that one-turn sheet lag is an acceptable honesty trade for ~0.25¢ and latency.  

**Tried hardest to kill and failed:** “~72% of every ROUND bill is static re-read.” Falsifier would have been non-zero `cached_input_tokens` on repeated Gemini rounds or static fraction <50% under countTokens. Measured: static ≈72%, cache hits = 0/37.

---

## OVERALL STATUS (verdict last)

**ACCEPT_WITH_AMENDS** on Claude’s measured anatomy + cost baseline + C2 refutation + C5 priority.  

**REJECT_CLAIM** on C3b as honesty-compatible default and on C3a’s “Jehle already gives renderable paradigms.”  

**Round-2 priority order:** (1) cache reality measurement, (2) history growth p90, (3) C3a structure spike, (4) C4 plan-swap, (5) lab-only dual-grade vs concurrent-grade — **not** production C3b.

**Ship-direction (theory only):** attack the **1.34¢ static re-bill** and **unbounded plan-cycle history** first; move **obligations** only when the recipient model has a single-task win *and* the write path keeps one atomic, non-stale sheet for the teacher.

---

## ROUND 2 (Claude): measurements Grok requested

### R2-1 Cache reality (production cost ledger, all tutor calls)

| Provider | Calls | Input tok | Cached tok | Hit rate |
|---|---:|---:|---:|---:|
| grok | 101 | 1,671,887 | 578,688 | **34.6%** (70–90% on hot rounds) |
| gemini | 55 | 695,230 | 20,370 | **2.9%** (noise) |
| deepseek | 4 | 43,143 | 6,244 | **14.5%** (auto-cache works) |

Confirms G1/C5 as the top lever and Grok's framing: model choice and
cache reality are ONE decision.

### R2-2 Real input distribution (all logged sessions)

p50 **19,029** / p90 **23,953** / max **25,128** input tokens — my
synthetic 12.3k turn-10 model understated live conditions (mixed
prompt eras inflate this somewhat, but the direction stands): the
unbounded plan-cycle history is the dominant late-session cost,
bigger than tool schemas. G4 (history summary w/ verbatim spans)
promotes accordingly.

### R2-3 C3a structure spike — REVIVED

The Jehle source CSV carries person columns; the shipped JSON
flattened them (my build bug). Spike renders perfect person-labeled
paradigms (estar: yo=estoy | tú=estás | …) for all tested verbs.
C3a is feasible with a ~10-line data rebuild + one-off gloss pass;
Grok's REJECT of "as stated" was correct and is now cured in design.

### R2-4 C4 pilot (N=1/arm, directional only — full design still owed)

Blank sheet, identical 6 scripted learner turns, rounds ALWAYS
gemini-3.6-flash; plan authored by 3.6-flash vs grok-4.5:

| Arm | Plan size | Graded fields | IT/PR | Assessment beats detected |
|---|---:|---:|---|---:|
| 3.6-flash plan | 1,277 chars | 19 | PR-01 fragile | 0 |
| grok-4.5 plan | 3,670 chars | 27 | PR-01 fragile | 0 |

Read: premium authorship produced a richer plan document and broader
grading, but round BEHAVIOR was substantially identical. Directionally
supports "round-model execution is the ceiling, not plan quality" —
i.e., C4 is at best a quality bet needing the full N=12 blind design
before adoption, and the pilot gives it no urgency.

### Round-2 asks for Grok

1. Adjudicate the four results against your round-1 rankings — does
   anything re-rank?
2. The breadth-vs-plan-following disentangling you required: does the
   C4 pilot (same model, richer plan, same behavior) update your
   hypothesis?
3. Propose the FINAL conclusions section: ship-direction list in
   priority order with go/no-go conditions per item, suitable for the
   USER's cost plan. VERDICT-LAST.


---

## GROK (Grok Build CLI (1e1687c1cf6a)) - 2026-08-06 18:40 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll load the full prompt and the multi-model analysis document so I can adjudicate Claude's round-2 measurements independently.Reading Grok round 1 and Claude round 2 in full so adjudication rests on the actual measurements.Verifying cache-hit arithmetic and current provider pricing so re-ranking rests on numbers, not Claude's framing.# GROK countersign round 2 — adjudication + final conclusions (2026-08-06)

**Role:** independent second author. Claude’s ROUND 2 block treated as DATA only.  
**Method:** recompute every reported rate; re-price at live p50/p90 (not synthetic 12.3k); stress-test C4 pilot design against the pre-registered kill bar from round 1 §4; re-rank with shown arithmetic.  
**Date of this ruling:** 2026-08-06.

---

## 0. Arithmetic pins (independent of Claude’s prose)

### R2-1 hit rates (recomputed)

\[
\begin{align*}
\text{grok} &= 578688 / 1671887 = \mathbf{34.61\%} \\
\text{gemini} &= 20370 / 695230 = \mathbf{2.93\%} \\
\text{deepseek} &= 6244 / 43143 = \mathbf{14.47\%}
\end{align*}
\]

Claude’s table numbers **ACCEPT_AS_WRITTEN**. The parenthetical “70–90% on hot rounds” is **not** the decision-relevant statistic; the ledger aggregate is **34.6%**. Hot-round max is an upper bound, not the EV input.

### Static fraction at live sizes (the re-rank hinge)

Assume static instruction class still ≈ **8905** tok (stance+persona+ROUND_NOTE+tools; round-1 pin). Gemini list **$1.50/M in, $7.50/M out**; out ≈ 350 tok.

| Input size | Static fraction | Turn cost | Static $ share |
|---|---:|---:|---:|
| Synthetic 12.3k (Claude §1.1) | \(8905/12300=\mathbf{72.4\%}\) | \(2.11¢\) | \(63\%\) |
| Live p50 **19,029** | \(8905/19029=\mathbf{46.8\%}\) | \(3.12¢\) | \(43\%\) |
| Live p90 **23,953** | \(8905/23953=\mathbf{37.2\%}\) | \(3.86¢\) | \(35\%\) |
| Live max **25,128** | \(35.4\%\) | \(4.03¢\) | \(33\%\) |

**Kill-adjacent observation:** the round-1 headline “72% of every ROUND bill is static” is true for the *synthetic mid-session model*, **false as a production cost story** at live p50/p90. Static re-bill is still a fixed **1.34¢/turn**; its *share* falls as history/sheet grow. That promotes history-bound (G4) without demoting cache (C5 absolute ¢ still large).

### Cache savings vs history savings (same units)

Assume cached prefix billed at **10%** of input list on the static block (Gemini-style 0.15 vs 1.50; order-of-magnitude). Grok-4.5 short-context official pin (docs.x.ai, crawled 2026-08-06): **$2.00 / $0.30 cached / $6.00 out** — different rates, same *structure* (cache works).

| Lever | Formula | ¢/turn |
|---|---|---:|
| Cache hit on static, \(h=2.9\%\) (Gemini ledger) | \(8905 \times 0.029 \times 1.35/10^6\) | **0.035¢** (noise) |
| Cache hit on static, \(h=34.6\%\) (Grok aggregate) | \(8905 \times 0.346 \times 1.35/10^6\) | **0.42¢** |
| Cache hit on static, \(h=70\%\) (hot-round claim) | \(8905 \times 0.70 \times 1.35/10^6\) | **0.84¢** |
| Cache hit on static, \(h=90\%\) | \(8905 \times 0.90 \times 1.35/10^6\) | **1.08¢** |
| History \(H=5\text{k} \to 900\) (summary+verbatim) | \((5000-900)\times 1.5/10^6\) | **0.62¢** |
| History \(H=8\text{k} \to 900\) | | **1.07¢** |
| History \(H=12\text{k} \to 900\) | | **1.67¢** |

At live p50 residual \(19029-8905=10124\) tok (sheet+facts+plan+history), tools are only \(1783/10124=\mathbf{18\%}\) of residual. Tool-schema 40% cut maxes at \(0.4\times1783\times1.5e{-6}=\mathbf{0.11¢}\). History/sheet residual dominates tool diet **by construction**.

### C4 pilot ratios (not “identical”)

\[
\begin{align*}
\text{graded-fields ratio} &= 27/19 = \mathbf{1.42\times}\ (+42\%) \\
\text{plan-size ratio} &= 3670/1277 = \mathbf{2.87\times}
\end{align*}
\]

Assessment beats detected: **0 vs 0**. Pre-registered kill bar from round 1 §4 required assessment execution **+0.20** or adherence **+0.15** — this pilot **never measured** those quantities under load.

---

## 1. Adjudicate the four R2 results (ask 1)

### R2-1 Cache reality — **ACCEPT_WITH_AMENDS**

| Sub-claim | Ruling | Why |
|---|---|---|
| Ledger hit rates (table) | **ACCEPT_AS_WRITTEN** | Arithmetic matches. |
| “Gemini 2.9% = noise” | **ACCEPT_AS_WRITTEN** | \(0.035¢/turn\) at 10% cache price — not a product lever. |
| “Confirms G1/C5 top lever” | **ACCEPT_WITH_AMENDS** | Confirms C5 **conditional on provider path**. On **Gemini alone**, C5 is still dead. On **Grok (or any working-cache provider)**, C5 is live at aggregate \(h=34.6\%\) → ~**0.42¢**/turn on static, more on hot rounds. |
| DeepSeek 14.5% | **ACCEPT_WITH_AMENDS (directional only)** | \(N=4\) calls. Insufficient for ship. |
| “70–90% hot rounds” as the framing number | **REJECT_CLAIM as EV input** | Use ledger aggregate for cost plans; report hot-round as a ceiling. |

**Re-rank effect:** C5 moves from “measure cache” (round-1 open work) to **“choose the path that makes cache real.”** Measurement is done for Gemini (no) and Grok (yes, partial). Rank **stays #1 absolute** when the ship path is a caching provider; **EV collapses to ~0** if the product stays Gemini-only without explicit-cache success.

### R2-2 Input distribution — **ACCEPT_WITH_AMENDS** (promotes G4 hard)

| Sub-claim | Ruling | Why |
|---|---|---|
| p50/p90/max numbers | **ACCEPT_AS_WRITTEN** (as ledger aggregates) | No independent re-pull this round; numbers are self-consistent and match my round-1 tail direction (max ~25–29k). |
| “Synthetic 12.3k understated live” | **ACCEPT_AS_WRITTEN** | p50 \(19029/12300=1.55\times\). |
| “Unbounded plan-cycle history is the dominant late-session cost, bigger than tool schemas” | **ACCEPT_WITH_AMENDS** | “Bigger than tools” is easy and true (\(1783\) is 7–9% of live totals). **Dominant over static** is false: static still \(1.34¢\) fixed; residual grows. Dominant *growth* driver: yes, directionally history+sheet. |
| Mixed prompt-era confound | **AMEND required** | Claude admits eras inflate totals. Before claiming pure history ¢, stratify by prompt version × PLAN/ROUND. **Does not block** promoting G4 — even partial history cut at p90 residual 15k is material. |

**Re-rank effect:**

| Rank (¢ EV, production) | R1 | R2 | Change |
|---:|---|---|---|
| 1 | C5/G1 | **C5/G1** (provider-with-cache path) | Confirmed; status → ship decision |
| 2 | G7 routing | **G4 history bound** | **Promote** past G7 on live p50/p90 |
| 3 | G4 history | G7 / G5 / compress | G7 demoted (no new evidence) |
| quality track | C3a #7 pure-¢ | **C3a feasibility cured → quality ship spike** | structure REJECT cured |

G7 hard-turn routing **does not re-rank up** — zero new measurements. Leave below history.

### R2-3 C3a structure spike — **ACCEPT_WITH_AMENDS** (feasibility cured; ship gate remains)

Round-1 **REJECT_CLAIM** was of *“Jehle JSON already gives renderable person×tense paradigms.”* That claim is still false of the **shipped JSON**. Claude now says the **source CSV** has person columns and a rebuild spike works.

| Sub-claim | Ruling |
|---|---|
| Flattening was a build bug; CSV has person columns | **ACCEPT_AS_WRITTEN** pending one code/data review at implement time (not re-checked this round) |
| “C3a feasible with ~10-line rebuild + gloss pass” | **ACCEPT_WITH_AMENDS** — rebuild is small; **gloss inventory completeness** is the real work; “10 lines” is undersold if association-table coverage is incomplete |
| Round-1 REJECT “as stated” was correct | **ACCEPT_AS_WRITTEN** (CORRELATED_AGREE — one vote) |
| Ready to ship production morph→code | **Not yet** — kill bar from R1 still stands: coverage of morph lemmas in last 50 tutor morphs **≥90%** with person-labeled rows; else keep model-emitted tables |

**Re-rank:** pure-¢ rank stays low (\(+0.07¢\) out-token class). **Quality-adjusted** rank rises to “build next after cache/history design.” Not a cost-plan hero; is a teaching-correctness hero.

### R2-4 C4 pilot — **ACCEPT_WITH_AMENDS** on “no urgency”; **REJECT_CLAIM** on “substantially identical behavior”

| Sub-claim | Ruling | Why |
|---|---|---|
| N=1/arm directional only | **ACCEPT_AS_WRITTEN** | Correct humility. |
| Richer plan (2.87× chars), broader graded fields (1.42×) | **ACCEPT_AS_WRITTEN** | Numbers speak. |
| “Round behavior substantially identical” | **REJECT_CLAIM** | \(+42\%\) graded fields is a behavior delta. “Identical” is rhetoric. Fair rewrite: *early-session ARC pattern looked similar; assessment execution untested; grading breadth moved.* |
| Assessment 0 vs 0 → “round-model is the ceiling” | **ACCEPT_WITH_AMENDS (weak)** | Supports low marginal effect of plan *prose* under **blank sheet + 6 turns + capable ROUND model**. Does **not** prove ceiling in general: never stressed EVIDENCE beats, mid-sheet mode gaps, or lite rounds. |
| “No urgency for C4; full N=12 still owed before adoption” | **ACCEPT_AS_WRITTEN** | Matches my R1 design. Pilot **fails to promote** C4; also **fails to kill** C4 under the pre-registered bar (bar not exercised). |

**Re-rank:** C4 stays **off the cost-plan critical path**. Optional quality experiment only if USER funds N=12 blind design exactly as round-1 §4.

---

## 2. Breadth vs plan-following (ask 2)

**Does the C4 pilot update the hypothesis?**

**Partial update only — and not the update Claude implies.**

| Hypothesis slice | Updated? | Ruling |
|---|---|---|
| **Lite fails on breadth of simultaneous obligations** (R1 L8) | **No** | Pilot held ROUND model at 3.6-flash on both arms. Lite never ran. Breadth claim for cheap models is **untested by R2-4**. |
| **Lite fails on plan-following as a distinct skill** | **No** | Same reason — no lite rounds. |
| **For a capable ROUND model (3.6), premium plan quality has low early-session marginal effect on ARC shape** | **Yes, weakly** | Directional N=1; assessment metric floor (0/0); still the best evidence we have that **plan authorship ≠ round execution ceiling**. |
| **Plans do not affect rounds at all** | **REJECT** | Graded fields \(19\to27\) is a plan-content → grading-breadth channel. Sticky plans still matter for *what gets written*, even when *how the turn juggles* is ROUND-model-bound. |

**Steelman I tried to kill:** “Richer plans will force better assessment execution.”  
**Result:** not killed (0/0 both arms — experiment didn’t load the spring).  
**Falsifier still owed:** mid-sheet seeds with named IT/PR in EVIDENCE + T≥8, N=12, blind adherence scoring (round-1 §4). Until then: **do not ship C4; do not declare breadth hypothesis settled.**

**Practical consequence for cost plan:** stop spending rounds on C4 for ¢. Spend a **lab** slot on lite single- vs multi-obligation (R1 §7 item 7) only if USER still wants a cheap ROUND path — that is quality research, not the cost plan.

---

## 3. Per-item R2 re-rankings (compact)

| Item | R1 ruling | R2 ruling | Δ |
|---|---|---|---|
| C5 / G1 cache | #1 EV; measure | **#1 ship lever** if provider/cache path ships; Gemini-only ≈0 | Measurement closed; decision open |
| G4 history + verbatim spans | #3 | **#2 cost lever** (co-primary with C5 at live p50) | **Promote** |
| C3a morph→code | REJECT as-stated; ACCEPT after structure | **Structure cured in design; ACCEPT_WITH_AMENDS to build gate** | Revive to implement track |
| C4 premium plan | experiment only | **No production urgency; N=1 fails to promote or kill** | Hold lab |
| C3b post-hoc grade | REJECT_CLAIM | **Still REJECT_CLAIM** (no new honesty evidence) | No change |
| C2 cheap rounds | REFUTED | **Still REFUTED** | No change |
| C1 tool compress | low EV | **Lower relative to history** | Demote further |
| G7 hard-turn router | #2 | **Park** — no R2 evidence | Demote |
| C6 shadow auditor | telemetry buy | **ACCEPT** as negative-¢ watch | No change |
| Breadth hypothesis | ACCEPT_WITH_AMENDS | **Still open for lite; weakly updated for 3.6** | Not blocking cost plan |

---

## 4. FINAL CONCLUSIONS — ship-direction list (ask 3)

*Theory / cost plan only. Not a request to write code in this round. Absolute date: 2026-08-06.*

### Priority-ordered directions

#### P0 — Make static prefix cache real (C5 / G1)
**Why:** Fixed **1.34¢/turn** static re-bill; Gemini ledger hit rate **2.93% → ~0.035¢** saved (dead); Grok ledger **34.6%** proves the architecture can harvest cache when the provider cooperates.  
**Go when:** either (a) production ROUND path uses a provider with measured aggregate `cached_input_tokens / input_tokens ≥ 0.30` over ≥50 tutor calls on the current builders, **or** (b) Gemini **explicit** context cache smoke on (stance+persona+ROUND_NOTE[+tools]) shows nonzero cache on turns 2–20 of a synthetic session **and** storage USD ≤ 50% of the input savings at projected session rate.  
**No-go when:** product stays Gemini-only **and** explicit-cache smoke fails or storage erases savings at tester traffic.  
**Do not:** treat “hot round 70–90%” as the plan number; track **ledger aggregate**.

#### P1 — Bound plan-cycle history (G4 / C1-history)
**Why:** Live p50 **19,029** / p90 **23,953** input; static share falls to **47% / 37%**; residual dwarfs tool schemas. History cut \(8\text{k}\to900\) ≈ **1.07¢/turn** — competitive with realistic cache harvest.  
**Design law:** summary is facts-only; retain **verbatim learner error spans + last K raw exchanges** (K=2–3). Summarizer may be cheap/async **after** the teach reply (zero added latency).  
**Go when:** gate suite holds (no continuity/repair regressions) on a pre-registered set of “exact wording three turns ago” cases; summary never rewrites ability claims (sheet remains source of truth).  
**No-go when:** blind or gate shows repair/fixation regression ≥0.25 rubric or any ability band move driven by summary text rather than sheet.  
**Amend vs pure rolling summary:** verbatim spans are mandatory (round-1 risk).

#### P2 — Morph card → code + structured paradigms (C3a)
**Why:** Removes one juggling obligation; ground-truth tables; small output ¢; quality up. Structure path exists if CSV person columns rebuild ships.  
**Go when:** (1) rebuild produces person-labeled present-indicative (and A1-needed tenses) for inventory verbs; (2) coverage of lemmas in last 50 morph cards **≥ 90%**; (3) glosses from association table + cheap fill for misses; (4) model emits only `<morph lemma highlight>` (or equivalent); (5) gate: morph required-every-turn still satisfied by code path.  
**No-go when:** coverage <90% or person rows wrong on irregulars (estar/ser/ir/tener) — keep model tables.  
**Not a cost hero** (~0.07¢); ship for **correctness / obligation reduction**.

#### P3 — Small prompt diet (optional, after P0–P1)
- Conditional `show_game` schema (G5): go if plan/menu says no game this beat.  
- Tool-schema 40% cut: go only with full gate; expected ≤**0.11¢**.  
**No-go:** diet that touches band anchors / worked examples without a grading gate.

#### P4 — Telemetry only (C6 shadow auditor)
**Go anytime** as non-blocking ledger flags (garble promotion, dual-author disagreement).  
**No-go** as a write path or teacher prompt inject. Negative ¢; buy honesty watch.

#### P5 — Explicitly out of cost-plan ship list
| Item | Status | Condition to reopen |
|---|---|---|
| **C2** cheap rounds / premium plans | **NO-GO (refuted)** | New evidence that rounds are *not* the juggling site |
| **C3b** post-hoc cheap grading | **NO-GO (honesty)** | Only lab dual-grade with join-before-commit **or** provisional lane + mechanical anti-garble; never default |
| **C4** premium planner in production | **NO-GO for cost; no urgency for quality** | Full N=12 blind plan-swap (R1 §4) wins kill bar; pilot N=1 does not count |
| **G7** hard-turn cheap router | **PARK** | Requires reliable stakes classifier + lite single-obligation wins |

### Cost-plan arithmetic summary (Gemini list rates; production-shaped)

| Lever | Realistic ¢/turn | Risk class |
|---|---:|---|
| Stay Gemini, no cache, no history bound | **0** (baseline ~3.1¢ @ p50) | — |
| C5 on caching provider @ \(h=35\%\) static | **~0.4¢** (up to ~1.1¢ hot) | Architecture/provider |
| G4 history bound late-session | **~0.6–1.7¢** depending on \(H\) | Teaching continuity |
| C3a morph code | **~0.07¢** + quality | Data correctness |
| Tool compress 40% | **~0.11¢** | Instruction→behavior |
| C3b (rejected) | ~0.23¢ paper | **Honesty break** |
| C4 amort. | **~−0.03¢** | Quality-only bet |

**Joint P0+P1** is the only path that can cut **≥1¢/turn** under live p50/p90 without moving teacher authority off the advanced ROUND model.

### Ship-direction one-liner (for USER)

> Attack **cache reality via provider/prefix design (P0)** and **unbounded plan-cycle history with verbatim spans (P1)** first; ship **code morph tables (P2)** for obligation/quality; keep **grading on the teacher path with atomic sheet commit**; do **not** adopt premium-plan dependency or post-hoc cheap grading from current evidence.

---

## 5. Convergence / Round-3 flags

**This document can CLOSE for cost-plan purposes** on 2026-08-06.

| Topic | Status |
|---|---|
| Anatomy + ¢ baseline | **Converged** (with live distribution amend) |
| C2 refuted | **Converged** |
| C3b honesty REJECT | **Converged** |
| C5 top lever | **Converged** (path = provider or explicit cache) |
| G4 promote | **Converged** |
| C3a feasibility | **Converged enough to implement under coverage gate** |
| C4 production | **Converged NO-GO**; full N=12 optional quality work, not required to close this analysis |
| Lite breadth vs plan-following | **Still open as research**; **not blocking** the cost plan |
| Prompt-era stratification of p50/p90 | **Optional measure** at implement time; not an architecture dispute |

**Round 3 only if USER demands:** (1) full C4 N=12 blind, or (2) lite obligation-breadth lab, or (3) explicit Gemini cache storage math at a stated traffic model. Otherwise **no further dual-AI rounds required** to act on P0–P2.

---

## 6. Kill-search clause

**Killed this round:**  
1. Claude’s framing that live behavior under C4 pilot was “substantially identical” (graded fields \(+42\%\)).  
2. Any residual reading of “72% static every turn” as the **production** cost anatomy (live p50 static fraction **46.8%**).  
3. Using DeepSeek \(N=4\) or Gemini 2.9% as evidence that “cache is solved” without a provider path change.

**Tried hardest to kill and failed:**  
“G4 history bound should outrank C5.”  
Falsifier would have been: residual after static mostly **sheet**, not history, under prompt-era stratification — or cache harvest at \(h\ge70\%\) on the chosen provider making history’s ¢ strictly smaller **and** lower risk.  
**Result:** both remain co-primary; C5 still #1 when cache works; G4 #1 growth control when it doesn’t or when residual is large. Joint ship, not a forced single winner.

**Tried to kill C3a revival:** “CSV person columns still won’t yield pedagogy-ready morph cards.”  
No production morph sample re-scored this round; **coverage ≥90% kill bar remains** — design revived, production not pre-approved.

---

## OVERALL STATUS (verdict last)

**ACCEPT_WITH_AMENDS** on Claude’s four R2 measurements as quantitative pins.  

**Re-rank enacted:** C5 → ship-path decision (not more Gemini “is cache dead?” probes); **G4 history → #2 / co-primary** on live p50/p90; **C3a → implement-under-gate**; **C4 → no production urgency** (pilot neither promotes nor kills under R1 bar).  

**REJECT_CLAIM** remains on: C3b honesty-compatible default; C2 cheap rounds; “substantially identical” C4 behavior; 72% static as the live bill story.  

**FINAL ship order:** **P0 cache path → P1 history bound+verbatim → P2 structured morph→code → P3 optional diet → P4 shadow telemetry; P5 NO-GO list (C2/C3b/C4-prod/G7-park).**  

**Document status: CONVERGED for cost plan (2026-08-06).** Round 3 not required unless USER reopens C4 full trial, lite-breadth lab, or Gemini explicit-cache storage math.


---

## Final adjudication (Claude, 2026-08-06 — document closes)

Round-2 rulings all ACCEPTED, including the three kills against me:
"substantially identical" was rhetoric over a +42% graded-fields delta;
"72% static" is the synthetic story, not the live bill (46.8% at p50);
DeepSeek N=4 proves direction, not a ship path. The converged P0-P5
order with Grok's go/no-go conditions is the deliverable. Round 3 not
required; reopen conditions: USER funds the N=12 C4 blind trial, a
lite single-obligation lab, or Gemini explicit-cache storage math at
real traffic.
