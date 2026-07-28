

---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-26 20:41 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll treat this as a blind research adjudication on retrieval, spacing, and durability — first pulling the sheet/mode implementation claims from the repo, then checking them against the L2 learning-science literature.
Confirming the conversational path has no review queue while the legacy harness still does — that split is load-bearing for the spacing adjudication.
# GROK — independent research round: RETRIEVAL, SPACING, AND DURABILITY  
**Date of adjudication:** 2026-07-26  
**Role:** contrarian second author (not a countersign of inlined prose)  
**Subject of inspection:** inlined `docs/system-overview.md` (status as of 2026-07-26) + live code paths `tutor/character_sheet.py`, `tutor/modes.py`, residual `tutor/student.py` / `tutor/lesson_flow.py`  
**Scope:** beginner L2 lexis/morphosyntax *in conversation* — retrieval, spacing, interleaving, durability; then (a)/(b)/(c) product choices.

---

## 1. Independent picture (dated pins)

| Pin | Claim I will defend | Anchor |
|-----|---------------------|--------|
| **P1 (2022)** | Spacing beats massing for L2: Kim & Webb meta-analysis, 98 effect sizes / 48 experiments / *N* = 3,411 → **g ≈ 0.58** (immediate posttest) and **g ≈ 0.80** (delayed). Equal vs expanding spacing ≈ **statistically equivalent**. Longer lags beat shorter lags on *delayed* tests. | Kim & Webb, *Language Learning* 72, 2022 |
| **P2 (2008)** | Optimal interstudy gap is a **fraction of desired retention interval** (ridgeline): ~**20–40%** of a ~1-week delay; ~**5–10%** of a ~1-year delay. Arithmetic for a 7-day horizon: 0.20×7 = **1.4 d**, 0.40×7 = **2.8 d** → target re-encounter **~1–3 calendar days** after last success if the goal is week-scale retention. For a 30-day horizon: 0.20×30 = **6 d**. | Cepeda et al., *Psychological Science* 2008 |
| **P3 (2006/2008)** | Retrieval (overt production / cued recall) consolidates far better than re-exposure; dropping items after one success *while continuing restudy* loses most of the gain. Swahili-pair classic: continued retrieval after success ≫ continued study. | Roediger & Karpicke 2006; Karpicke & Roediger 2008 |
| **P4 (1977 + TAP applied to L2)** | Memory performance tracks **overlap of processes at encoding and later use** (Morris, Bransford & Franks 1977). Same form in a *new* micro-context is right for **generalization/transfer**, not a substitute for **delayed** retrieval. | Morris et al. 1977; Lightbown TAP framing for classroom L2 |
| **P5 (2019)** | Interleaving L2 grammar (mix forms/structures across practice) often hurts in-session accuracy but **improves delayed** tests vs blocked practice (Nakata & Suzuki 2019 and follow-ons). Conversation that only rides the hottest error pattern is closer to **blocking**. | Nakata & Suzuki, *MLJ* 2019 |
| **P6 (2019/2023)** | Incidental vocab needs **multiple spaced encounters**; frequency effects are real but noisy (Uchihara, Webb & Yanagisawa 2019; Webb et al. 2023). A tutor that never *schedules* re-use of “known” lemmas/forms is betting that free chat will re-hit them — empirically fragile at A1. | Uchihara et al. 2019; Webb et al. 2023 |
| **P7 (product fact, 2026-07-26)** | Conversational product path: **transfer** fires immediately on resolve; sheet has **per-turn conf caps**, **known @ conf≥0.80 ∧ solid_uses≥2**, **`last_seen` written but unused for decay**, **no re-encounter queue**. Legacy harness still has `review_schedule` / `due_items` (`tutor/student.py`, `tutor/lesson_flow.py`) — **orphaned relative to the shipping conversational pipeline**. | Code inspection 2026-07-26 |

**Synthesis picture:** ml_teacher optimizes **within-session trajectory** (model → try → recast → immediate transfer) and **honesty of “known” labels**, which is real pedagogical engineering. It does **not** currently optimize **between-session durability**. Those are different objective functions. The overview’s learning-science table lists CLT/CI/association/focus-on-form/transfer/trajectory and is silent on spacing/retrieval schedules — that silence is the load-bearing omission of this dimension.

---

## 2. Verify / refute table (load-bearing claims)

| # | Claim (from overview / product choices) | Verdict | Evidence & arithmetic |
|---|------------------------------------------|---------|------------------------|
| C1 | Transfer = same form, **new** micro-context after success | **VERIFY (mechanism)**; **REFUTE (as durability strategy)** | Code: `modes.py` §5, `reason="success_transfer"`, instructions: “Same form, NEW micro-context.” Pedagogically TAP-aligned for **near transfer**. It is **massed successive retrieval** (lag ≈ 0–1 turns), not spaced practice. Kim & Webb: spacing advantage **g = 0.80** on delayed tests is about **lags**, not same-session recontexting. |
| C2 | Transfer after **one** success is enough to leave the form | **AMEND / mostly REFUTE for durability** | One correct production is a weak mastery signal (product even admits this via `KNOWN_MIN_SOLID_USES = 2`). Immediate transfer is good **practice design** for generalization; treating it as “done until they err again” is the opposite of testing-effect logic (keep retrieving after success; Karpicke & Roediger 2008). |
| C3 | Per-turn confidence caps (`MAX_CONF_UP_PER_TURN = 0.25`) | **VERIFY as anti-overclaim** | Honest harness: stops 0→1 in one utterance. Binding path to *known* via successive +0.15 bumps: 0.80 ÷ 0.15 = **5.333 → ≥6 successful bumps** before conf alone clears 0.80 (uses need only 2, so **conf is the binding constraint**). Good for label honesty; **orthogonal** to forgetting. |
| C4 | `known` at conf ≥ 0.80 **and** solid_uses ≥ 2 | **VERIFY as implemented**; **REFUTE as long-term competence model** | Code: `KNOWN_MIN_CONF = 0.80`, `KNOWN_MIN_SOLID_USES = 2`. Two solid uses can be **same session, same topic**. That is performance, not storage strength (Bjork storage vs retrieval strength). |
| C5 | **No time decay** on confidence / known | **VERIFY (code)**; **REFUTE as science-aligned durability model** | `last_seen = today()` is set on bump; nothing in conversational modes/sheet recomputes conf from age. Forgetting is not optional; it is the reason spacing works. A 0.90 “known” from 2026-06-01 still reads as known on 2026-07-26 with zero intervening retrieval — **25 calendar days of unmeasured decay**. |
| C6 | **No scheduled review / re-encounter queue** on conversational path | **VERIFY** | Character sheet has no due-queue. Modes never select “review due item.” Ironically, **legacy** `review_schedule` + `due_items()` still exist — product path abandoned the only spacing artifact in the repo. |
| C7 | `next_best` = single longer-arc stretch guide | **VERIFY** | `recompute_next_best` writes one `next_best` object (can-do **or** form primary). Modes treat it as optional steer, not multi-item scheduler. Single stretch ≠ interleaving of prior items. |
| C8 | Learning-science stack in overview (CLT, CI, association, FoF, transfer, trajectory) is complete for “what we optimize” | **REFUTE (completeness)** | Missing: retrieval practice, spacing, interleaving, lag×retention interaction. Overview optimizes **teach moves and session feel**, not **retention curves**. |
| C9 | Conversation as vehicle automatically supplies enough re-encounters | **REFUTE as default assumption** | At A1 palette size, free chat systematically re-uses greetings/estar and under-samples lower-frequency can-dos/lexemes unless forced. Uchihara et al. 2019: repetition–learning correlation is positive but **activity- and context-dependent**; you cannot outsource spacing to chat entropy. |
| C10 | Expanding spacing is required for MVP | **REFUTE (requirement)** | Kim & Webb 2022: equal vs expanding **not reliably different**. **Any spacing > massing** is the first-order win; expanding is a later refinement. |
| C11 | Immediate transfer implements “desirable difficulty” | **PARTIAL** | Contextual variation = desirable difficulty (Bjork). **Zero lag** between success and transfer reduces retrieval effort (too easy). Desirable difficulty wants **some** forgetting before re-retrieval. |
| C12 | Form-error weaning / active patterns provide enough re-practice | **PARTIAL** | Hot error patterns get repeated focus — good for fragile forms **while hot**. Once resolved and conf high, **no return path** until a new error appears. Silent attrition of correct-but-unused forms is uninstrumented. |

---

## 3. What the other author / system overview MISSED

1. **Two timescales, one model.** Within-session transfer ≠ between-session spacing. Overview collapses “transfer” into the learning-science table as if it covered durability. It does not.

2. **Orphaned legacy scheduler.** `tutor/student.py` still carries `review_schedule`; `lesson_flow.due_items()` still opens with due review. Conversational product (`character_sheet` + `modes`) never wires it. Either delete the dead path or **port a minimal due queue into the sheet** — silence here is architectural amnesia, not a principled rejection of SRS.

3. **`last_seen` is dead weight.** Written every successful bump; never used for due computation, decay, or mode priority. That is half an implementation of spaced review without the review.

4. **Progress score amplifies the illusion.** Header score ≈ mean confidence × 100 (+ streak bonus). With no decay, score is a **monotonic career high-water mark**, not current retrievability. Arithmetic: mean conf 0.72 → score 72 even if every item is 3 weeks cold.

5. **Interleaving of *prior* can-dos is absent.** `next_best` picks weakest open interpersonal item or active form error — never “mix IP-04 + IP-06 this session because both are due.” Blocking-on-hot-error is the default.

6. **Receptive vs productive retrieval.** Sheet bumps largely track **production** patterns in learner text. Comprehension repair re-models input but does not systematically schedule **later productive** retrieval of the same form after lag (testing effect wants *learner* retrieval, not only tutor model).

7. **No operational definition of “re-encounter success.”** Without a due item + elicit + binary outcome, you cannot run a spacing experiment on this product. Eval trajectories (`c06_transfer_after_resolve`) check mode presence, not delayed retention.

8. **Risk of “known” locking out practice.** `recompute_next_best` skips `is_known` can-dos. Combined with no decay, a twice-lucky form exits the stretch agenda forever until spontaneous error.

---

## 4. Standing product choices — (a)/(b)/(c)

### (a) Transfer mode = same form in NEW micro-context **immediately** after one success

| Aspect | Ruling |
|--------|--------|
| As **near-transfer / generalization** drill | **KEEP.** Aligns with TAP and “vary conditions of practice” (Bjork). Better than re-asking the same line. |
| As **proof of learning** | **REJECT.** One success + immediate recontext is massed practice with surface variation. |
| As **spacing mechanism** | **REJECT.** Lag ≈ 0 turns; Cepeda’s ridgeline wants days for week-scale retention. |
| Adjudication | **AMEND:** keep immediate transfer **once** after resolve; then **enqueue** that form for delayed conversational retrieval (see MVP below). Do not treat transfer as the end of the scheduling problem. |

### (b) Confidence model: capped bumps; known @ ≥0.80 + 2 solid uses; **no decay**; **no review queue**

| Piece | Ruling |
|-------|--------|
| Caps + known gate | **KEEP.** Correct honesty response to model over-rating. 6×0.15 conf math above. |
| No time decay | **REJECT as permanent design.** Acceptable only as explicit v0 limitation with a measured replacement date. |
| No re-encounter queue | **REJECT for any claim of durability pedagogy.** Optional if product is “single-session demo”; not if character sheet is “durable learner model.” |
| Adjudication | **AMEND:** keep bump honesty; add **age-aware retrievability** (even crude) and a **due queue of forms/can-dos** separate from “known” status. Status = historical evidence; due = scheduling signal. |

### (c) `next_best` as a **single** longer-arc stretch goal

| Aspect | Ruling |
|--------|--------|
| As UI/guidance for “what we’re stretching toward” | **KEEP** one human-readable stretch. |
| As complete curriculum controller | **REFUTE.** One stretch cannot implement interleaving or multi-item review. |
| Adjudication | **AMEND:** `next_best` stays the **headline**; add parallel **`due_reencounters[]`** (max 2–3) that modes can soft-inject into conversation without becoming a flashcard app. |

---

## 5. Do we need a spaced re-encounter scheduler? MVP form?

**Yes — minimal viable form, not Anki-in-chat.**

Evidence priority: spacing vs massing is medium–large on delayed L2 tests (Kim & Webb 2022: **g = 0.80** delayed). Expanding vs equal is **not** required for v1. Full SM-2 is overkill and fights the product persona (adult boat/café chat, not kids flashcards).

### MVP scheduler (adjudicable, implementable in sheet + modes)

**Data (on each skill/grammar/lex entry or a parallel list):**
- `last_success_at` (ISO datetime; you already almost have `last_seen`)
- `successive_successes` (int; solid_uses can double)
- `next_due` (date)
- `interval_days` (float)

**On successful productive use in a *new* context (transfer success or free correct use):**
```
if successive_successes == 1: interval_days = 1
elif successive_successes == 2: interval_days = 3
else: interval_days = min(interval_days * 2, 14)   # cap at 2 weeks for A1 session cadence
next_due = today + interval_days
```
**On fail / error pattern hit:** `interval_days = 1`, `next_due = tomorrow`, demote status if needed (existing down-bump).

**Arithmetic check vs Cepeda (week-scale retention):** first gaps **1 d** and **3 d** sit inside the **1.4–2.8 d** band for a 7-day retention goal (0.20–0.40 × 7). Cap 14 d ≈ 0.20 × 70 d horizon — coarse but science-shaped, not vibes.

**Mode integration (conversation-native, not drill):**
- New soft mode or conversation branch: **`reencounter`** (not hard break): if any item `next_due ≤ today` and `turns_since_hard_break` allows soft work, inject **one** try that elicits that form in the *current* topic (TAP: same process as chat).
- Budget: **at most one due re-encounter try per N turns** (e.g. N=4) so it never becomes a quiz app.
- Hard modes (form_focus, association, comprehension_repair) still outrank.
- UI: do **not** show due list to learner; sheet modal can show “due soon” for debug.

**What MVP explicitly is not:** flashcards, English gloss review, equal-interval CRM, or expanding-only religion.

---

## 6. Ranked improvement proposals (impact vs cost)

| Rank | Proposal | Impact | Cost | Citation basis | Adjudicable acceptance test |
|------|----------|--------|------|----------------|------------------------------|
| **1** | **Ship MVP due-queue + soft conversational re-encounter** (above). Wire `last_seen` → `next_due`. | **High** — closes the largest science gap (spacing on delayed retention, g≈0.80 class of effect). | **Med** — sheet fields + one mode branch + 2–3 unit tests + one smoke traj. | Kim & Webb 2022; Cepeda et al. 2008; Roediger & Karpicke 2006 | Unit: success sets `next_due = today+1`; after fake clock +2d, mode can select reencounter; fail resets interval to 1. Behavioral: session log shows ≥1 due elicit across 2 simulated “days” without form_focus. |
| **2** | **Split “status” from “retrievability”.** Keep known gate; add `retrievability = f(conf, days_since_success)` used only for scheduling/score, not chat. Simple: if days_since > 2×interval and no success, flag `stale` and force due. | **High** — kills false mastery in progress score and next_best skip. | **Low–med** | Bjork storage/retrieval strength; testing effect literature | Progress score drops when items go stale without error; known status may remain until fail. |
| **3** | **Post-success multi-retrieval policy:** after resolve, (i) immediate transfer once, (ii) do **not** mark known from that alone, (iii) require ≥1 **delayed** success (different session or ≥ interval) before conf can cross 0.80 *or* before solid_uses from same-session massing count past 1. | **Med–high** — aligns known with durable retrieval. | **Med** (policy + cap logic) | Karpicke & Roediger 2008 (retrieval after success) | Same-session three lucky estoy → conf capped so known unreachable without delayed use. |
| **4** | **Interleave due items with next_best stretch** (max 2 due + 1 stretch in mode context prompt). Prefer mixing two prior forms over grinding one hot error after weaning. | **Med** — Nakata & Suzuki interleaving benefit on delayed grammar. | **Low** if due-queue exists | Nakata & Suzuki 2019 | Prompt/context contains two distinct form_ids when two items due; session uses both within 8 turns. |
| **5** | **Expanding vs equal A/B later** — only after MVP equal-ish ladder works. | **Low near-term** | **High** (needs multi-day eval harness) | Kim & Webb: expanding ≈ equal | Do **not** prioritize until (1) ships. |

**Explicit non-proposal:** full SM-2 / Leitner UI. Persona and CLT contract forbid flashcard product surface; scheduler must stay **invisible infrastructure** under conversation.

---

## 7. Bottom-line countersigns on the three choices

| Choice | Vote | One-line reason |
|--------|------|-----------------|
| (a) Immediate transfer after one success | **AMEND** | Keep as near-transfer move; add delayed re-encounter — transfer alone is massed variation, not spacing. |
| (b) Caps + known@0.8/2 uses; no decay; no queue | **AMEND hard** | Caps/gate stay; **no-decay + no-queue is pedagogically indefensible** for a “durable” sheet given Kim & Webb / Cepeda. |
| (c) Single next_best stretch | **AMEND soft** | Keep as headline; add parallel due list for interleaving/review. |

**Do we need a spaced re-encounter scheduler?**  
**Yes.** Minimal viable form is a **sheet-side due date + interval ladder (1 → 3 → ×2 cap 14) + soft conversational elicit**, not flashcards and not expanding-spacing research theatre.

---

## 8. Sources used (absolute bibliographic pins)

- Kim, S. K., & Webb, S. (2022). The effects of spaced practice on second language learning: A meta-analysis. *Language Learning, 72*(1), 269–319. (g ≈ 0.58 immediate / 0.80 delayed; equal ≈ expanding.)  
- Cepeda, N. J., Vul, E., Rohrer, D., Wixted, J. T., & Pashler, H. (2008). Spacing effects in learning: A temporal ridgeline of optimal retention. *Psychological Science*.  
- Nakata, T. (2015). Effects of expanding and equal spacing on second language vocabulary learning. *SSLA*.  
- Nakata, T., & Suzuki, Y. (2019). Effects of massing and spacing on the learning of L2 grammar. *Modern Language Journal* (interleaving vs blocking).  
- Roediger, H. L., & Karpicke, J. D. (2006). Test-enhanced learning. *Psychological Science*.  
- Karpicke, J. D., & Roediger, H. L. (2008). The critical importance of retrieval for learning. *Science*.  
- Morris, C. D., Bransford, J. D., & Franks, J. J. (1977). Levels of processing versus transfer appropriate processing. *JVLVB*.  
- Uchihara, T., Webb, S., & Yanagisawa, A. (2019). The effects of repetition on incidental vocabulary learning: A meta-analysis. *Language Learning*.  
- Bjork, R. A. / Bjork & Bjork — desirable difficulties; storage vs retrieval strength (review essays 2011+).  
- Code pins (2026-07-26): `tutor/character_sheet.py` (`KNOWN_MIN_CONF`, `MAX_CONF_UP_PER_TURN`, `_bump_status`, `recompute_next_best`); `tutor/modes.py` (transfer on `success_transfer`); legacy `tutor/lesson_flow.py` `due_items`.

---

*End of Grok independent round — RETRIEVAL, SPACING, AND DURABILITY (2026-07-26). Append under provenance tag as-is.*
