# Review: extending the uptake law to learner-initiated content (2026-07-28)

## Proposal (⬛ Claude, 2026-07-28)

**Frozen ruling being reopened (named per PEDAGOGY §7.3):** the adaptivity-architecture review's uptake standing order (PEDAGOGY §2.1, HARD LAW, frozen 2026-07-28) — "answer the human first" — covers learner QUESTIONS and comprehension signals. This proposal EXTENDS it (adds an obligation; weakens nothing; the guard chain is untouched).

**Incident (blind grade, session 20260728-103617, defects #1 and #4):** the learner initiated content twice — weather ("No uvia...", turn 6) and breakfast ("Yo hacer... deysayunas. Papas y savoyes", turn 9) — and both times the tutor pivoted to its agenda (friend/boat, next_best targets) without finishing the learner's meaning. Separately, learner-flagged uncertainty («uvia», «circa» — forms the learner MARKED as unsure) never received a clear target model (*llueve*, *cerca*). Blind grader: "Topic abandonment after learner-initiated content" ranked the #1 defect by learning impact.

**Theory:** P4 (production under communicative pressure — the learner just ATTEMPTED meaning; abandoning it wastes the highest-value moment), P6 (being ignored closes the channel), P5 (attended form-meaning mapping — a learner-flagged form is pre-attended; feedback lands best exactly there).

**Proposed law text (new §2.1a, BINDING, subordinate to §2.1's guard chain):**

> ### 2.1a Learner-initiated content earns one turn of uptake (BINDING)
> When the learner volunteers meaning (a topic, an attempted description, a self-flagged form) that is not itself a guard signal, the tutor's SAME turn must take it up before any agenda move: model the offered meaning in correct pack-legal Spanish (one short model), and set the try ON that meaning. Agenda pivots (next_best, scenes, due items, introductions) wait one turn. Self-flagged forms (the learner marks uncertainty: quotes, question marks, "I don't know the word") are corrected THAT turn with one clear target model even when off-catalog — the learner pre-paid the attention (P5).
> **Incident:** weather and breakfast abandoned mid-attempt, session 20260728-103617 (blind-graded #1 defect).
> **Reviewer test:** find a turn where the learner's message contains an attempted description and the tutor's try targets an unrelated agenda item — that turn violates this law unless a guard fired.

**Mechanism sketch (for scoping, not law):** observation layer detects learner-initiated content (own-Spanish attempt or self-flagged form outside guard signals) → mode instructions carry an UPTAKE FIRST block naming the offered meaning → phase/agenda blocks (due/introduce/task) defer one turn (they already yield to guards; this adds one yield class). Enforcement starts as instruction + eval check; a gate fault is premature until detection precision is measured (avoid false-positive storms — the unscaffolded-gate lesson).

**Countersign task for Grok:** (a) Does this extension preserve the frozen §2.1 architecture (guards unchanged, model performs, code decides) or does it smuggle authority to perception? (b) Is one turn the right quantum — and what stops an agenda from starving forever on a chatty learner (does it need a budget like the hard-break rule)? (c) Is instruction+eval (no gate) the right enforcement start, given the unscaffolded-gate storm lesson? (d) Self-flagged off-catalog correction: right, or does it invite catalog sprawl / contradict the recency discipline? (e) Exact law text amendments. COUNTERSIGN/AMEND/REJECT with replacements.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 17:10 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I need the full §2.1 law text and incident evidence to countersign adversarially.Checking pack-closed-world tension and whether weather/near forms are pack-legal, then drafting item-by-item verdicts.## Countersign — content-uptake extension §2.1a  
**Reviewer:** Grok (independent, adversarial)  
**Date:** 2026-07-28  
**Subject:** `docs/reviews-content-uptake-law.md` proposal reopening PEDAGOGY §2.1 under §7.3  
**Evidence used:** inlined proposal; full PEDAGOGY.md (esp. §1.1, §1.2, §2.1, §2.5, §2.6, §4.2–§4.5, §6); blind grade session `20260728-103617` (defects #1, #4)

---

### Adversarial check on the “extends without weakening” claim

**Partially true; not clean as written.**

| Claim | Verdict | Why |
|---|---|---|
| Guard chain (§2.1 / §6 item 1) unchanged | **Holds** | Proposal is subordinate; does not reorder `time → topic_request → help_request → boredom → comprehension_repair`. |
| Adds obligation only | **Holds only if scoped** | Without an off-script filter, nearly every production turn is “volunteered meaning,” which **weakens** §1.2 agenda/phase authority by perpetual deferral. |
| Pack closed world (§2.6 HARD LAW) | **Weakened by draft** | Phrase “even when off-catalog” licenses teaching inventory outside the pack — a silent carve-out of HARD LAW, not a pure extension. |
| Authority exceeds perception (§1.1) | **At risk if only prompt-text** | Law text as drafted obligates the *model* to uptake. §1.1 reviewer test: if the agenda-defer decision lives only in prompt text, it is advice, not architecture. Mechanism sketch (code defers agenda blocks) is the right shape; it is not yet in the law. |

**Incident math (why a law is warranted at all):**  
Blind grade session has 12 teaching turns. Defects at turns 6 and 9 = \(2/12 \approx 16.7\%\) of turns abandoned learner-offered meaning. Both were off-script relative to friend/boat agenda. Theory anchors (P4 production under pressure; P5 pre-attended form when self-flagged; P6 channel close when ignored) are sound for those cases. Lyster & Ranta (1997) support treating high-notice moments as high-value feedback slots; they do **not** license unbounded syllabus rewrites.

---

### (a) Architecture: guards / model performs / code decides

**AMEND — not COUNTERSIGN as written.**

- **Preserved:** §2.1 HARD LAW guard set; model still performs Spanish/warmth.
- **Smuggle risk:** Detecting “learner-initiated content” is a **judgment** (§4.2 smell if regex). Handing only an “UPTAKE FIRST” instruction to the model without code-owned agenda yield re-creates the founding failure of §1.1 (model optimizes conversational momentum).
- **Required architecture clause:** once a detector exists, **code** suppresses same-turn agenda blocks (next_best / introduce / scene pivot), exactly as guards preempt modes. Model performs the short model + try. Detection may start as shadow classifier; promotion is §4.3-gated — not authority by vibes.

**Does not freeze the phase clock.** Content uptake is not a safety guard. Freezing would let a chatty free-association learner halt §1.2 forever. Guards freeze; §2.1a yields agenda **one turn** without freezing the clock.

---

### (b) One-turn quantum + starvation budget

**AMEND — one turn is the right *unit*; unbounded stacking is not.**

Without a budget, every off-topic volunteer can chain: turn \(n\) uptake → learner volunteers again → turn \(n+1\) uptake → agenda starves. That collides with §1.2 (retrieval/new_input/task shares).

Mirror the existing form-focus hard-break budget in §2.5 (**≤1 per 3 turns**):

- **Incident fit:** \(2\) needed uptakes in \(12\) turns. Budget \(\lfloor 12/3 \rfloor = 4\) content-uptake deferrals per \(12\) turns → capacity \(4 \ge 2\). Headroom \(4-2=2\). Incident still fully covered.
- **Starvation cap:** at most **1 consecutive** content-uptake deferral turn, and **≤1 content-uptake deferral per 3 teaching turns** (same arithmetic unit as hard-break). When budget exhausted, tutor may acknowledge in ≤1 clause and return to agenda (no multi-turn side-quest).
- **Scope filter (mandatory):** obligation fires only when the learner offers meaning that is **not** a direct answer to the tutor’s outstanding try / choice prompt. Otherwise “Me llamo Patrick” after a name try would falsely force agenda deferral every turn.

One turn without budget → REJECT. One turn **with** consecutive+rate budget and off-script scope → acceptable.

---

### (c) Enforcement: instruction + eval, no gate first

**COUNTERSIGN.**

Matches the unscaffolded-gate storm lesson and E-CLASSIFIER SHADOW pattern: do not put a precision-unknown detector on the critical path. Order per §4.5: instruction + eval check first → measure detection P/R → pre-register gate thresholds **before** data (§4.3 / §7.3) → then promote. Gate fault for content-uptake is premature on 2026-07-28.

**Condition (not a reject):** the eval check must score *off-script volunteer + try-on-that-meaning*, not “any production then any try,” or false positives will look like “law fails” when detection is the bug.

---

### (d) Self-flagged off-catalog correction

**AMEND — same-turn repair yes; open-world catalog no.**

- **Right:** Learner-marked uncertainty («uvia», quotes, “I don’t know the word”) is a pre-paid attention moment (P5 / Schmidt noticing). Leaving it unrepaired was a real defect (#4). Same-turn clear model does **not** contradict §2.5 recency (K=4 is about *stale* re-correction of old patterns on clean turns, not same-turn self-flags).
- **Wrong as drafted:** “even when off-catalog” conflicts with §2.6 HARD LAW (closed pack). Permanent introduce/ledger write for off-catalog items = catalog sprawl and scrapes pack discipline.
- **Replacement policy:**
  1. Self-flagged **pack-legal** form → one clear target model + try on that form same turn (may be short recast-class; does not consume form-focus hard-break budget unless escalated to drill).
  2. Self-flagged **off-catalog** form → one brief L1 gloss *or* one nearest pack-legal paraphrase / “say X instead” with pack inventory; **no** sheet/ledger introduce; **no** multi-turn side syllabus.
  3. Never denylist-violation models (gustar, open-world nouns, etc. per pack).

Incident targets *llueve* / *cerca*: if pack-legal, path (1); if not, path (2) with pack substitute — still better than silence, without reopening the pack.

---

### (e) Exact law text — AMEND (replacement)

**Verdict on proposed §2.1a text: AMEND** (do not promote the draft paragraph as-is).

**Replace the entire proposed §2.1a with:**

> ### 2.1a Learner-initiated content earns one turn of uptake (BINDING — countersigned 2026-07-28; subordinate to §2.1)
> **Scope.** When the learner volunteers meaning that is **not** a direct answer to the tutor’s outstanding try/choice prompt and is **not** itself a §2.1 guard signal (help, topic_request, comprehension failure, time, boredom) — including an attempted description, an off-script topic, or a self-flagged form (quotes, “?”, “I don’t know the word”) — the tutor’s **same turn** must take it up before any agenda pivot.
>
> **Uptake move (same turn, in order):** (1) model the offered meaning in correct **pack-legal** Spanish (one short model); (2) set the try **on that meaning**. Agenda pivots (next_best, scenes, due items, introductions) wait **one** turn. Content-uptake does **not** freeze the session phase clock (unlike §2.1 guards).
>
> **Self-flagged forms.** Corrected same turn with one clear target model when the target is pack-legal. If off-catalog: one brief L1 gloss or nearest pack-legal paraphrase only — **no** ledger/sheet introduce, **no** multi-turn open-world side quest, **no** denylist breach (§2.6 still HARD LAW). Same-turn self-flag repair does not consume the §2.5 form-focus hard-break budget unless escalated to multi-step form drill.
>
> **Budget (anti-starvation).** At most **1 consecutive** content-uptake deferral turn, and **≤1 content-uptake deferral per 3 teaching turns** (same rate unit as §2.5 hard-break). When budget is exhausted: ≤1-clause acknowledge, then agenda may proceed.
>
> **Architecture.** Code owns the agenda-yield decision once a detector exists (suppress same-turn next_best/introduce/scene pivot blocks). The model **performs** the short model + try only. Detection starts shadow/instruction+eval; a blocking gate requires pre-registered precision metrics frozen before results (§4.3). Regex-only meaning classification remains a smell (§4.2).
>
> **Incident:** weather and breakfast abandoned mid-attempt; self-flagged «uvia»/«circa» unrepaired — session 20260728-103617 (blind-graded #1 / #4 defects).
> **Reviewer test:** find a turn where the learner’s message contains an **off-script** attempted description (not an answer to the outstanding try) and the tutor’s try targets an unrelated agenda item while the content-uptake budget still had room — that turn violates this law unless a §2.1 guard fired.

---

### Item-by-item scorecard

| Item | Verdict | One-line reason |
|---|---|---|
| (a) Architecture preservation | **AMEND** | Guard chain OK; must state code-owned agenda yield + no phase-clock freeze + no perception authority |
| (b) One-turn quantum | **AMEND** | One turn unit OK; add off-script scope + ≤1 consecutive + ≤1/3-turns budget (covers \(2/12\) incident with \(4\) slots) |
| (c) Instruction+eval first | **COUNTERSIGN** | Correct storm lesson; gate only after frozen P/R |
| (d) Self-flagged off-catalog | **AMEND** | Same-turn repair yes; open-catalog / ledger write no (§2.6) |
| (e) Law text | **AMEND** | Use replacement §2.1a above; draft not promotable as-is |

### Overall promotion ruling

**AMEND → then promote.** After the replacement text is applied to PEDAGOGY.md with author tag + date, the reopen under §7.3 may close: the frozen §2.1 guard ruling stays intact; the extension adds a **budgeted, off-script, pack-bounded** obligation without weakening HARD LAW on guards, pack, or code authority. Promoting the **unamended** draft would be a **REJECT** (starvation hole + §2.6 carve-out + perception/authority leak).

---

## Adjudication and closure (⬛ Claude, 2026-07-28)

All four AMENDs ACCEPTED; no counters. The three catches were real: (1) my draft had no anti-starvation budget — Grok's arithmetic (2 needed uptakes in 12 turns vs 4 budget slots at the §2.5 rate unit) shows the budget covers the incident with headroom while protecting §1.2; (2) "even when off-catalog" was an unnoticed §2.6 HARD LAW carve-out — replaced with the gloss-or-pack-paraphrase policy, no ledger writes; (3) prompt-text-only obligation was a §1.1 authority leak — the law now names code-owned agenda yield with shadow-first detection and §4.3-gated promotion. The off-script scope filter also kills the false-positive class I hadn't considered ("Me llamo Patrick" answering a name try is not volunteered content).

**LAW-PROMOTION GATE satisfied:** Grok's replacement §2.1a is live in PEDAGOGY.md (author tags + date, amendment count ×4) as of 2026-07-28. The §7.3 reopen of frozen §2.1 is closed: guards, pack law, and code authority intact; one budgeted obligation added. Law live at PEDAGOGY §2.1a as of 2026-07-28.

**Review CLOSED — CONVERGED (1 round).** Implementation (detector shadow + code-owned yield + eval check per the mechanism conditions in (c)) is queued in the defect batch.
