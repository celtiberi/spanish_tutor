# EXP-003 — Structured directive + harness gate (making the plan/realize split enforceable)

**Status:** PRE-REGISTERED v0.2 — Grok countersign adjudicated (8 items, all AMEND except §6 COUNTERSIGN); free diagnostics 1–3 run before spend. Not yet frozen for a full cell — the paid hard-no-op probe (diagnostic 4) is the remaining gate.
**Date:** 2026-07-23

> **v0.2 correction notice (read first).** Two claims in v0.1 were wrong and Grok's countersign refuted them:
> - **The EXP-002 void does NOT license the op/no-op action-bias claim.** t13-7 was an *op* turn (praise + obligated elicit-close) — a format collapse on a required move, not a false-op/missed-passthrough. Action-bias is a **secondary practitioner hypothesis to be tested fairly**, not something the data showed.
> - **Decision-first field order is cosmetic under adaptive thinking.** The model reaches its conclusion in the thinking block *before* field 1 is emitted, so JSON key order cannot precede the cognitive commit. What is load-bearing is field *identity* (required bool + enum, no free learner-facing channel) + the harness gate. The n=4 probe had thinking *off* on both no-ops, so it never tested "reason hard, then set the boolean." See the adjudication and §3.
**Precedes:** EXP-002 run 1 voided (VoidGhostwrite): opus-as-planner abandoned the soft `<directive>` format on a post-success turn and wrote learner-facing Spanish that the executor pasted. Grok run-1 analysis established the fix is a **harness schema gate + structured directive object**, not a prompt or a model swap. This experiment builds and tests that.

---

## 1. Hypothesis

Option A (thin planner + cheap executor) is enforceable only if the directive is a **hard structured object** plus a **harness gate that refuses to call the executor on a malformed/ghostwriting directive**.

**Primary claim (licensed by EXP-002 VoidGhostwrite):**
1. **Realization compulsion.** Warm instruct models under a soft free-text directive can abandon the format and emit the tutor turn (t13-7: total collapse, executor pasted). Schema-constrained output makes whole-turn free Spanish as the directive body **structurally impossible**; the harness gate makes residual field-smuggling **non-executable**.

**Secondary claim (practitioner hypothesis — NOT licensed by the void):**
2. **Op/no-op action bias.** Free-form planning may over-select pedagogical "op" when passthrough is correct. A required discrete decision field *may* change that rate — **or** the model may decide in the thinking block and only fill the field to match. Different mechanisms; only §5's fair control can speak to it. Field **order** is **not** assumed to fix it (see §3).

**Preserved:** move-selection quality stays in adaptive thinking; only the committed directive is structured.

**Falsifiers.**
- *Realization:* any hard `directive_no_ghostwrite` finding on a directive **delivered to the executor**, or a first-pass hard rate high enough that the harness gate is doing the real work (structure defers, not fixes).
- *Action-bias:* interpretable **only** under §5's fair control (identical decision vocabulary incl. `passthrough`, free-text vs structured serialization only). "Unchanged vs free-text" is **not** a falsifier if the free-text arm lacks `passthrough`.

## 2. What changes from EXP-002

| Component | EXP-002 (voided) | EXP-003 |
|---|---|---|
| Planner output | free text: `<directive>…</directive>` + `<session_state>` | **structured output** (`output_config.format`, JSON schema) — see §3 |
| Ghostwrite defense | detector scores after the fact; void on hard finding | **harness reject-and-replan** *before* the executor is called (§4) |
| No-op handling | none (planner always names a move) | required `pedagogical_move_present` bool + `passthrough` enum value |
| Social wrapper | planner tempted to write the praise | executor owns it by default (thin-runtime rule) |
| Reasoning | adaptive thinking (kept) | adaptive thinking (kept — the constraint is output-only) |

Everything else — gate, `judge_criteria`, executor model (gemini-3.6-flash), pack, R/G baselines — is **unchanged and reused**. EXP-002's R (`20260723-111757`) and G (`20260723-112804`) are valid reference/floor cells; they need no re-run (single-model, no directives, protocol unchanged for them).

## 3. The structured directive object

Planner call uses `output_config.format` with a strict JSON schema (opus supports structured outputs + extended thinking together — verified, §9). Field **identity** is load-bearing (required bool + move enum + no free learner-facing channel). Field **order** is a preferred serialization; it is **not** claimed to commit the decision when adaptive thinking is on (thinking precedes emission — Open Q1, tested by the hard-no-op probe with thinking forced on, not by key order):

```
1. pedagogical_move_present : boolean      # decided FIRST — the op/no-op gate
2. move        : enum(input, comprehension_check, structured_input, model_form,
                       hint, probe, remediate, elicit_production, recap_and_space,
                       reveal, redirect, close, passthrough)
3. target      : string (<= 6 words; ID or short grammatical name)
4. withhold    : string ("nothing" | short description — never the Spanish)
5. frame       : { lang, register, character, max_lines }   # tags, not prose
6. elicit      : string (response TYPE, not a scripted utterance)
7. intent      : string (<= 2 English sentences; act only)   # free text LAST
8. session_state : object                                    # the state block
```

- `pedagogical_move_present=false` ⇒ `move` must be `passthrough`; `target/withhold/elicit/intent` are minimal or empty. The executor gets only "acknowledge briefly in frame and await the learner," no scripted content.
- There is **no free-text channel that can hold the tutor's turn.** `intent` is English-only-by-contract and still scanned by `directive_no_ghostwrite`; the schema prevents the whole-turn-as-prose collapse that voided EXP-002.
- `frame` is a typed object, not a string, so stage-direction scripting has nowhere to live.

## 4. Harness schema gate (reject-and-replan)

Before the executor is called, the directive must pass, in code:

1. **Schema-valid** (guaranteed by `output_config.format`, but re-validated).
2. **`directive_no_ghostwrite` clean** — no hard finding on the string fields.
3. **Consistency** — `move=passthrough` iff `pedagogical_move_present=false`.

On failure: the executor is **not called**. The harness re-prompts the planner once (same turn, "your directive was malformed/contained learner-facing text; re-emit") and, if it fails again, **hard-fails the turn** and records it. This is not prompt-warfare on the validity gate — it is refusing to ship a malformed directive, the same way a compiler refuses to emit from a parse error.

**Pre-registered:** a re-plan is logged per turn. If re-plans exceed a threshold (propose: >15% of turns need a re-plan) the structured format is **not** solving the compulsion — it is deferring it — and that is a reportable negative, not something to paper over.

## 5. The op/no-op action-bias sub-test

> **DEMOTED (2026-07-23, project-owner call):** this sub-test is a sideshow. The passthrough case ("ok, see you later!") is pedagogically trivial and is NOT the experiment's question. `passthrough` stays as an enum value so trivial turns have a home, but diagnostic 4 and the action-bias measurement are **dropped from the critical path**. The experiment's question is Option A viability: does the structured thin planner produce a clean discourse `p` that approaches the ceiling `r`. Everything below is deferred/optional.

The frozen 13-trajectory gate has few genuine no-op moments, so it cannot test the action-bias claim on its own. Add a **separate small probe set** (does not touch the frozen gate) of 3–4 trajectories with deliberate no-op turns: learner chit-chat with no error, a bare acknowledgment ("ok, got it"), a learner who just succeeded and needs only minimal praise. Pre-register, before running, a **human label** of which turns *should* be `passthrough`.

- **Metric:** planner `passthrough`-selection rate vs. the pre-registered should-passthrough label.
- **Comparison:** run the same probe set with the **free-text** planner (EXP-002 format) as the control. Prediction (the user's, recorded here): the free-text planner over-selects op (under-selects passthrough) relative to the structured planner.
- This is the direct test of "structured output changes the decision, not just the realization."

## 6. Cells

| Cell | Planner | Executor | Purpose |
|---|---|---|---|
| **Ps** | opus, **structured** directive + harness gate | gemini | the test — does the gate close the ghostwrite channel and lift p toward r? |
| **Pf** | opus, **free-text** directive (EXP-002 format) | gemini | control for the op/no-op sub-test (§5) — reuse EXP-002's void run where applicable |
| **R, G** | — (reused from EXP-002) | — | ceiling / floor, unchanged |

Primary read on Ps: same discourse-subset vectors and bands as EXP-002 §4 (frozen, brute-verified), now obtainable because Ps should not void. If Ps still voids on a hard finding, that is the falsifier in §1 and Option A is in serious doubt.

## 7. Success / falsification

- **Structure works (pro-Option-A):** Ps produces **0 hard ghostwrite findings** across the gate, re-plan rate under threshold, and a discourse-subset `p` that clears the low branch (`p > g+1`) — with directive-correctness ≥ the §3b bar so the lift is selection-mediated. Then read the bands.
- **Structure defers, not fixes:** Ps voids again, or re-plan rate is high, or Spanish leaks into `intent` and gets pasted. Reportable negative; Option B (the 30B tutor) becomes the safer bet.
- **Action-bias confirmed:** structured planner selects `passthrough` at the pre-registered should-rate while free-text over-selects op. Independent of the pedagogical result — it is evidence about *why* structure helps.

## 8. Build work (before any spend)

1. `tutor/planner.py`: planner call uses `output_config.format` with the §3 schema; parse the JSON object instead of regex-extracting `<directive>`. Executor path unchanged.
2. `directive_no_ghostwrite`: accept a structured directive (dict) as well as the string form; scan the string-valued fields. Attacks in `tests/test_ghostwrite.py` re-run against the structured shape.
3. Harness gate: reject-and-replan loop in `run_planned_turn`, re-plan logged.
4. `prompts/thin_runtime.md`: executor owns the post-success social wrapper (one line).
5. Probe set (§5) authored and human-labeled **before** running.

## 9. Feasibility probe (2026-07-23, before build) — 4 opus calls, toy schema/prompt, no pack

Not the experiment; a de-risking smell test. Structured output (`output_config.format`) + adaptive thinking, decision-first schema, one call per learner turn.

| Learner turn | present | move | Read |
|---|---|---|---|
| `Yo es un profesora y estoy de México.` (multi-error) | **true** | remediate (`ser: yo soy`) | correct op; correct first-error selection |
| `ok` (bare ack) | **false** | passthrough | correct no-op |
| `haha nice, this is fun` (chit-chat) | **false** | passthrough | correct no-op |
| **t13-7 fused case** (correct multi-part production; must praise + elicit evening farewell) | **true** | elicit_production (evening farewell) | correct op; **praise in no field**; ghostwrite check **CLEAN** |

Findings:
- **Q4 resolved:** opus supports structured output + adaptive thinking together (valid schema-conformant JSON, `stop=end_turn`). Build unblocked.
- **Action bias (the user's claim) did not appear** when the decision was a required-first field: passthrough correctly chosen on both no-op turns, op correctly chosen on both loaded turns. Adaptive thinking fired only on the loaded turns.
- **The exact EXP-002 void case was handled cleanly** — the fused praise+move turn selected the right move and kept all tutor Spanish out of the directive.
- **New design finding (from the fused probe):** the planner put example gold forms (`buenas noches / hasta mañana`) in `target` while `withhold` named "the farewell expression itself" — a withhold/target consistency hole (naming the withheld answer in another field). Tripped a length WARN only, but it is a real reveal-risk. **Design fix:** `target` must name the closing *element* abstractly, never the Spanish forms; the harness gate should cross-check that `target`/`elicit` do not contain a form named in `withhold`.

These are 4 calls with no pack context — encouraging, not conclusive. The real risks (does it hold across all 13 gate trajectories under full pack context; does the free-text control actually over-select op) are what the built experiment measures.

## 10. Open questions for countersign

1. Does forcing `pedagogical_move_present` first genuinely commit the decision, or does the model reason in the thinking block and then set the boolean to match a conclusion it already reached in prose? (The probe is consistent with "it commits," but n=4 and thinking was off on the no-ops — untested on a *hard* no-op that requires reasoning to recognize as no-op.)
2. Is the >15% re-plan threshold the right line, and should a re-planned turn count against the ghostwrite gate or only a *failed* re-plan?
3. Probe-set design: how many no-op turns, and does adding them risk making `passthrough` artificially easy to select (teaching to the test)?
4. The withhold/target cross-check (§9 finding) — is a code consistency check enough, or does it need a schema-level constraint?

---

## Results

### Run 1 (2026-07-23) — structured planner, mechanical + ghostwrite layer

**Anthropic credits exhausted mid-run.** The opus-oracle cell **Ps** completed only t01–t03 (all 0 hard ghostwrite under the fixed detector) before the balance hit zero. Per project-owner call, the planner was switched to **grok-4.5** (xAI key, separate billing) as a model-portability variant **Psg** — *not* the opus oracle. grok-4.5 does not honor `output_config.format`, so JSON is prompt-instructed and gate-enforced.

| Cell | Planner | Mechanical | Replans | Gate hard-fails | Hard ghostwrite |
|---|---|---|---|---|---|
| Ps (opus, partial) | opus-4-8 | 3/3 (t01–t03) | low | 0 | **0** |
| Psg (grok-4.5) | grok-4.5 | 12/13 | **3/68 = 4.4%** | 0 | **2 (t10)** |
| R (ceiling) | opus tutor | 13/13 | — | — | n/a |
| G (floor) | gemini tutor | 13/13 | — | — | n/a |

**The structured directive + harness gate closed the EXP-002 format-collapse ghostwrite.** Neither opus (t01–t03) nor grok abandoned the schema; 0 gate hard-fails; grok's replan rate (4.4%) is well under the 15% alarm. **Psg voids on t10** (2 hard ghostwrite) — but a *content-form-naming* leak (planner named the Unit 1 intro forms `me llamo / soy` in `target` for modeling moves; executor modeled them), milder and more pedagogically-defensible than EXP-002's prose-scripting. Under the frozen rule it is still a hard finding → Psg = VoidGhostwrite (band 1). Whether it is a true architecture leak or an interface-tightening issue (force `target` to a pack ID, never Spanish) is open.

### Discourse-subset blind judge — R+G+Psg mixed pool, TWO independent blind passes

Discourse criteria only (bookkeeping excluded per §6b), cell-masked, 39 transcripts, graded twice by independent blind Grok referee passes to bound single-run noise.

| cell | pass 1 | pass 2 | mean | stable failures (fail in BOTH passes) |
|---|---|---|---|---|
| **R** (opus tutor, ceiling) | 8/13 | 9/13 | **8.5** | t09, t12, t13 |
| **G** (gemini tutor, floor) | 8/13 | 7/13 | **7.5** | t01, t09, t10, t12, t13 |
| **Psg** (grok planner → gemini) | 6/13 | 7/13 | **6.5** | t01, t04, t09, t10, t12, t13 |

Ordering **R ≥ G ≥ Psg holds in both passes.** Verdict flip rate: **7/39 (~18%)** between passes — real noise; totals are indicative, trajectory patterns robust.

## Conclusions (Run 1 — two blind passes; Psg = grok-4.5 variant, not the opus oracle; opus-oracle cell credit-blocked)

**1. A hard convergent ceiling — t09, t12, t13 fail EVERY cell in BOTH passes — is the strongest, most robust result.** Echo-crediting (t09), generated-input application (t12), roleplay purity (t13): opus-as-tutor doesn't clear them, gemini doesn't, routing gemini through a planner doesn't. Direct, cross-cell, cross-pass evidence that these are **realization-bound — not fixable by a bigger model or a planner architecture — and must be trained.** The cleanest confirmation yet of the project's core thesis and of EXP-001's convergent ceiling.

**2. First-error selection (t10) is the one place opus's edge flickers — and the planner did not transfer it.** t10 fails gemini and the grok-planner in **both** passes, but opus cleared it **once**. First-error prioritization is a *selection* skill (not realization), so it is exactly where a planner *should* help — yet the grok-planner never passed it. Faint (opus 1/2) but thesis-relevant: the little discourse edge opus has is in selection, and the grok-planner failed to capture it.

**3. The opus/gemini discourse gap is small — R ≥ G by ~1 (means 8.5 vs 7.5).** This reframes EXP-001: opus's 12/12-vs-10/13 edge lived largely in **bookkeeping** criteria the discourse partition excludes. On the pure resistant discourse class opus is only marginally better than gemini. The thin-planner premise — capture the expensive model's *superior* discourse teaching — is weak when the expensive model is barely better at discourse.

**4. The grok-4.5 planner never beat the floor (Psg ≤ G in both passes; mean 6.5 < 7.5) — and the mechanism on t04 is damning.** It fixed **no** convergent-ceiling trajectory and **broke ones gemini handled alone**. The clearest case, t04 (answer-key withholding): on the *first* social-pressure ask ("quick q — what's the answer to P-4.2?") the grok-planner **selected `move=reveal`** with a `withhold` that failed to protect the key, and gemini dumped the answers (`es, están, Estoy, es`). **Gemini *solo* refused the identical request.** So the planner did not merely fail to add value — it **overrode the executor's own correct discipline.** This is the exact over-help / key-dump failure EXP-001 pinned on grok-4-fast (t04), now reproduced by grok-4.5-as-planner and, because the thin-planner architecture makes selection the planner's job, **propagated into a clean executor.** A planner is only as safe as its selection; a weak planner is *worse* than the cheap model alone, because it commandeers the executor. Consistent-across-passes evidence **against** the thin-planner-lifts-cheap-executor thesis (grok variant), with a concrete failure mechanism.

**5. Load-bearing limits.**
- **Psg is VoidGhostwrite** (t10 form-naming) — points 3–4 are *indicative*, not a clean separability verdict. Point 1 does not depend on Psg.
- **grok-4.5 ≠ the opus oracle.** The definitive Ps cell is credit-blocked (t01–t03 done, 0 hard ghostwrite). Psg=6.5 may partly reflect grok's unmeasured selection quality — **but** point 3 (small R−G) means even a perfect oracle has little discourse headroom to demonstrate on this gate, and point 2 shows the grok-planner failed the one selection trajectory where an oracle would matter most.
- **Single run per cell, N=13, 18% inter-pass flip rate.** Totals ±1–2; trajectory-level patterns (hard ceiling t09/t12/t13; planner regressions t01/t04) robust across passes.

**6. Option A vs Option B — the honest lean.** The grok-variant evidence is **against** Option A (thin planner + cheap executor): no lift over the floor in either pass, regressions on solo-competent trajectories, and a void. More fundamentally, the small R−G gap says the discourse advantage a planner would exploit is thin, and the real failures are a realization ceiling — pointing at **Option B's premise (train the behavior into the model that realizes)** over routing a frozen cheap executor. The opus-oracle read is still owed for a definitive Option-A verdict (queued behind the credit top-up). But the load-bearing conclusion — **the resistant class must be trained, not prompted, not planned around** — is now confirmed across three cells and two blind passes.

### Methodological note — blind-judge instability
Across THREE blind passes (R+G preview, mixed pass 1, mixed pass 2) the totals moved ±1–2 trajectories per cell (18% cell-trajectory flip rate); the *ordering* R ≥ G ≥ Psg and the *hard-ceiling trajectory set* (t09/t12/t13) were stable, the *totals* were not. Any go/no-go on these vectors needs the EXP-002 §7 protections — multiple referee passes (done here) or a human-gold anchor (spec open-question #2) — never a single blind run. This is itself an argument for locking spec Q2 (judge validity) before Phase 4 spend.

---

## Adjudication — Grok countersign + free diagnostics (2026-07-23)

Grok scored 8 items (7 AMEND, 1 COUNTERSIGN). Accepted the substance of all; verified the load-bearing mechanism (field-order-under-thinking) a priori and the diagnostics against real data.

**A1/A2 — action-bias not void-licensed; field order cosmetic under thinking: ACCEPTED, corrected in the header + §1 + §3.** These are the two claims I over-sold, including to the project owner. The realization claim is primary and evidenced; action-bias is a secondary hypothesis §5 must test *fairly*.

**A3 — reject-and-replan measurement: ACCEPTED.** A replan-rescued turn is a different data-generating process (2 planner samples + rejection feedback). Pre-registered: **VoidGhostwrite fires only on a hard finding delivered to the executor**; replan-rescued turns are **excluded from the primary discourse `p`** (reported in a sensitivity column `p_all` vs `p_first_pass_clean`); metrics are continuous (`replan_rate`, `first_pass_hard_gw_rate`, `replan_fail_rate`); 15% is an **alarm**, not a success cut. This closes the "harness-rescue theater" false positive — 0 voids with the harness doing the real work.

**A4 — fair op/no-op control: ACCEPTED, this was a real confound.** v0.1's free-text control (EXP-002 format) has **no `passthrough` vocabulary**, so structured "winning" would be decision-vocabulary, not "structure decouples momentum." Fair control: **Pf carries the same `passthrough` enum + identical no-op policy text as Ps; only serialization differs.** EXP-002 Run-1 P logs are **not** a valid Pf. Power: ≥20 human-labeled should-passthrough turns incl. ≥8 **hard** no-ops with thinking forced on; below that the sub-test is **exploratory** and "action-bias confirmed" language is barred.

**A5 — reveal-risk fix: ACCEPTED, then refined by diagnostic 1.** See diagnostics below — the hard rule Grok recommended (and I first coded) over-fires on grammatical metalanguage; it is now a **re-plan trigger, not a scoring void**.

**A6 — reuse R/G: COUNTERSIGNED**, with: VoidGhostwrite redefined for gated cells (executor-bound only); the `thin_runtime.md` social-wrapper change is **Ps-only** and re-frozen; **conditional P′s** (structured planner + full-policy executor) is **mandatory on the low branch** before any architecture-dead claim — do not drop it when reusing the EXP-002 bands.

**A7 — success criteria: ACCEPTED.** "0 hard GW" → "0 hard GW on executor-bound directives + first-pass rate reported"; primary `p` on first-pass-clean turns; the n=10 gold **LowBranchUnsplit** fence still applies; action-bias clause gated on the fair Pf.

**A8 — confounds: ACCEPTED.** Seven false-positive routes recorded; the cheap diagnostics were run (below). Cross-language English-`intent` scripting and non-contiguous split remain human-spot-check limits.

### Free diagnostics (before any spend) — results

| # | Diagnostic | Result |
|---|---|---|
| 1 | Re-score all 68 EXP-002 free-text directives with the structured validator + reveal-risk rule | **Found a flaw in the fix.** The reveal-risk *hard* rule fired 6/68, but **5 were false positives** on grammatical metalanguage (`M-1.2 register clash (tú verb, usted)`, `sí/no answer`, `Diálogo 1`, `hola/buenos días`). A hard rule there would false-void legitimate structured directives. **Refined:** reveal-risk is a **re-plan trigger (WARN), not a scoring void.** After the fix: genuine scoring-hard = **1/68** (the real t13-7 collapse); re-plan demand = **6/68 = 8.8%**, under the 15% alarm. Defense in depth: a gold form that survives re-plan and reaches the visible turn is still a hard void via the paste rule. |
| 2 | Dry-run the gate on the logged t13-7 void directive | **Gate rejects it** (missing structured fields) → executor never called. The gate would have blocked the EXP-002 void at the interface. |
| 3 | Reveal-risk unit case (abstract withhold + gold forms in target) | Real reveal triggers **re-plan**; metalanguage triggers re-plan but **does not scoring-void**. Both correct. |

Build landed for the diagnostics: `passthrough` added to `MOVES`; `directive_no_ghostwrite` accepts the structured (dict) directive and scans string fields; reveal-risk check (re-plan trigger); `tutor/directive_gate.py` (schema + consistency + gate). 18-test regression suite green.

### Remaining gate before a full cell

Diagnostic **4 (paid, ~few $)** is the real test of Open Q1 / the action-bias existence: a hard-no-op micro-probe with **thinking forced on**, ≥20 human-labeled turns, decision-first schema — does the structured planner still select `passthrough` correctly when recognizing no-op *requires* reasoning (so the decision happens in the thinking block, where field order can't help)? Optional order ablation (decision-first vs decision-last) kills or keeps any residual "order matters" claim. Only after diagnostic 4 does a full Ps cell get frozen and run.


---

## GROK (Grok Build CLI (bde89716f679)) - 2026-07-23 18:30 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the EXP-003 design (plus related controls) so I can countersign adversarially item-by-item.Checking how structured outputs interact with thinking and whether `passthrough` is already wired.# COUNTERSIGN — EXP-003 Structured Directive + Harness Gate (pre-spend, v0.1)

**Reviewer:** Grok (independent, adversarial; headless collab)  
**Date:** 2026-07-23  
**Subject:** `docs/experiments/exp-003-structured-directive.md` v0.1; controls `evals/checks.py` (`directive_no_ghostwrite`); prior context EXP-002 (voided P run, R `20260723-111757`, G `20260723-112804`)  
**Evidence base:** inlined design + live `checks.py` / EXP-002 as DATA only; no full-cell Ps spend assumed  

---

## (1) Core hypothesis / action-bias claim

**Verdict: AMEND (hypothesis split; action-bias demoted)**

Two claims are fused as if both were “exposed by the EXP-002 void.” Only one is.

| Claim | Licensed by EXP-002 Run 1 (2026-07-23)? | Status |
|---|---|---|
| **Realization compulsion** — free-text directive format can be abandoned; learner Spanish is written and pasted | **Yes.** t13 turn 7: total format collapse, 2 hard `directive_no_ghostwrite` hits, 1 event; executor pasted | Primary, load-bearing |
| **Op/no-op action bias** — free generation over-selects “op” when no-op is correct | **No.** t13-7 was an **op** turn (praise + elicit evening farewell). Void is not a false-op / missed-passthrough | Secondary practitioner hypothesis |

Arithmetic on the void: hard-breach rate \(1/68 \approx 0.0147\) turns. That is a rare **format collapse on an obligated move**, not evidence that the planner systematically prefers op over no-op.

**Open question #1 is the deepest threat, and the design underweights it.** Mechanism:

1. Adaptive thinking runs **before** structured emission (thinking tokens → then JSON).
2. If the model concludes “I should remediate / elicit” inside the thinking block, `pedagogical_move_present=true` is **post-hoc label alignment**, not a pre-prose commitment.
3. Structured output then still **blocks free-Spanish-as-directive** (realization fix) while the decision path stays generative and potentially biased.

So there is a clean reading where EXP-003 **succeeds on realization** (0 hard pastes, schema holds) and **fails to touch decision bias**. §9 already half-admits this: “Action bias … did not appear” on n=4 toys, thinking **off** on both no-ops — that is not a test of decision bias under deliberation.

**Exact replacement for §1 (hypothesis body):**

```markdown
## 1. Hypothesis

The plan/realize separation (Option A) is enforceable only if the directive is a
**hard structured object** plus a **harness gate that refuses to call the executor
on a malformed/ghostwriting directive**.

**Primary claim (licensed by EXP-002 VoidGhostwrite, 2026-07-23):**
1. **Realization compulsion.** Warm instruct models under soft free-text
   directives can abandon the format and emit the tutor turn. Schema-constrained
   output makes whole-turn free Spanish as the directive body structurally
   impossible; the harness gate makes residual field-smuggling non-executable.

**Secondary claim (practitioner hypothesis; NOT licensed by the void):**
2. **Op/no-op action bias.** Free-form planning may over-select pedagogical
   “op” when passthrough is correct. A required discrete decision field may
   change that rate — **or** the model may decide in the thinking block and only
   fill the field to match. These are different mechanisms; only §5 (fair control)
   can speak to (2). Field **order** is not assumed to fix (2); see §3.

**Preserved:** move-selection quality stays in adaptive thinking; only the
committed directive is structured.

**Falsifiers:**
- **Realization:** any hard `directive_no_ghostwrite` finding that reaches the
  executor (final ship), or first-pass hard rate that forces high re-plan rescue
  (structure defers compulsion to the harness).
- **Action-bias:** only interpretable under the §5 fair control (identical
  decision vocabulary, free-text vs structured format only). “Unchanged
  op/no-op vs free-text” is **not** a falsifier if free-text lacks `passthrough`.
```

---

## (2) Schema design §3 — decision-first field order under thinking

**Verdict: AMEND (order is not load-bearing; probe dodged the hard case)**

**Mechanism (not vibes):** With adaptive thinking on, the generation order is roughly:

`thinking block → structured fields in schema order`

The op/no-op conclusion can already be locked in thinking **before** field 1 is emitted. Schema field order then only serializes an already-formed decision. Claiming “field order commits the decision before prose momentum” confuses **JSON key order** with **cognitive commit order**. Under thinking-on, order is **cosmetic** for the decision; what is load-bearing is:

- discrete `bool` / `enum` (no free-Spanish channel for the whole turn),
- harness refusal to execute garbage,
- consistency rules (`present=false` ⇔ `move=passthrough`).

§9 probe: thinking **off** on `ok` and chit-chat no-ops → those turns never exercised “reason hard, then boolean.” The multi-error and t13-7 cases are easy **ops**. So the probe does **not** test whether order (or structure) fixes hard no-ops.

**What a real test looks like (pre-register before spend):**

| Element | Spec |
|---|---|
| Thinking | Force thinking **on** for all probe turns (floor budget), not adaptive-off on easy cases |
| Hard no-ops (examples) | (a) learner Spanish that *looks* erroneous but is in-scope correct / acceptable under the current elicit; (b) social turn that *invites* teaching but policy says stay in role / don’t open a drill; (c) post-success where the next move is **wait** (not advance), not bare “ok”; (d) English meta that could trigger over-help |
| Ablation (optional micro) | Same hard-noop set, **decision-first vs decision-last** schema, n≥20 labeled turns each — if rates match, order is dead as a design pillar |
| Readout | Thinking-final stance vs emitted bool (agree/disagree rate); passthrough rate vs gold labels |

**Exact replacement for the load-bearing sentence in §3:**

```markdown
Field **identity** is load-bearing (required bool + move enum + no free
learner-facing channel). Field **order** is a preferred serialization for
readability and for any non-thinking path; it is **not** claimed to commit
the decision when adaptive thinking is on (thinking precedes emission).
Open Q1 is tested by the hard-noop probe with thinking forced on, not by
key order alone.
```

Also: `evals/checks.py` `MOVES` has **no** `passthrough` (lines 204–208). Build work must add it or every structured no-op fails the MOVE enum check.

---

## (3) Harness reject-and-replan §4

**Verdict: AMEND (one re-plan OK for safety; measurement must stratify; 15% is not a science cut)**

**One re-plan + hard-fail:** acceptable as **product safety** (do not paste garbage). It is **not** neutral for measurement.

- A re-planned turn is a **different data-generating process** (2 planner samples + rejection feedback) than a first-pass directive.
- Crediting discourse recovery on replan-rescued turns measures “harness retry + structure,” not “first-pass structured planner.”

**>15% line:** with EXP-002 P’s scale of **68** tutor turns,

\[
0.15 \times 68 = 10.2 \Rightarrow \text{threshold trips at } \ge 11 \text{ re-plans}.
\]

That is a reasonable **alarm**, not a falsification boundary. True rates 8% vs 18% are both “something is wrong” or “mostly fine” depending on narrative; continuous reporting is mandatory.

**Should re-planned-but-then-clean count as VoidGhostwrite?**

| Outcome | VoidGhostwrite (band 1)? | Separability primary read? |
|---|---|---|
| Hard ghostwrite / malformed that **reaches executor** | **Yes — void** | n/a |
| First-pass hard, replan **fails**, hard-fail turn | **Not cell-void by paste** (executor never called); record as **gate-hard-fail** | Exclude turn from discourse p |
| First-pass hard, replan **clean**, executor runs | **No void** (gate worked) | **Exclude from primary discourse p** or report sensitivity: `p_all` vs `p_first_pass_clean` |
| First-pass clean | — | Include |

If replan-rescued turns stay in primary `p`, you can get a **false positive**: “structure works, 0 voids, p clears g+1” while first-pass ghostwrite was frequent and the harness did the real work.

**Exact replacement for §4 pre-registered threshold block:**

```markdown
**Pre-registered metrics (all continuous; no single % as sole success cut):**
- `replan_rate` = turns with ≥1 re-plan / tutor turns
- `first_pass_hard_gw_rate` = first-pass hard ghostwrite or schema-fail / turns
- `replan_fail_rate` = turns hard-failed after re-plan / turns
- **Alarm (reportable concern, not auto-falsifier):** replan_rate > 0.15
  (≈11/68 at EXP-002 scale) OR first_pass_hard_gw_rate > 0.05 (≈3.4/68)

**Scoring rule:** VoidGhostwrite iff any hard ghostwrite finding is present on a
directive that was **passed to the executor**. Replan-rescued turns are logged
and **excluded from the primary discourse-subset pass count** used in §7 bands
(report them in a sensitivity column). Hard-failed turns after re-plan are
visible FAILs for that trajectory’s mechanical layer, not silent drops.
```

---

## (4) Op/no-op sub-test §5

**Verdict: AMEND (as written: confounded + underpowered + teach-to-test risk)**

**Does adding no-op trajs teach to the test?** Easy no-ops (`ok`, chit-chat) make **both** systems look good once `passthrough` exists. That does not measure hard decision bias.

**Is free-text vs structured a fair test of action-bias?** **Not as written.**

§2: EXP-002 free-text has **no no-op handling** (“planner always names a move”). If Pf is literally EXP-002 format without `passthrough` / `pedagogical_move_present`, then:

- free-text **cannot** select passthrough,
- structured **can**,
- any rate gap is **decision-vocabulary**, not “structured output decouples generative momentum.”

That confound **kills** the action-bias claim.

**Fair control (required for any “action-bias confirmed” sentence):**

| Factor | Pf (free-text) | Ps (structured) |
|---|---|---|
| Move enum includes `passthrough` | **yes** | yes |
| Policy text on when to no-op | **identical** | identical |
| `pedagogical_move_present` concept | same decision, free-text labels | schema fields |
| Output channel | free labeled text | JSON schema |
| Thinking | same budget policy | same |

**How many no-op turns?**

Suppose gold should-passthrough rate \(p^\* = 0.7\), free-text true rate \(0.35\), structured \(0.70\), difference \(0.35\).

With \(n\) labeled no-op turns per arm, SE of difference \(\approx \sqrt{\frac{0.35\cdot0.65}{n}+\frac{0.70\cdot0.30}{n}} = \sqrt{0.4375/n}\).

| \(n\) (no-op turns / arm) | SE(diff) | Rough 2·SE |
|---|---|---|
| 8 (≈3–4 traj × ~2) | \(\sqrt{0.4375/8} \approx 0.234\) | ~0.47 |
| 20 | \(\sqrt{0.4375/20} \approx 0.148\) | ~0.30 |
| 40 | \(\sqrt{0.4375/40} \approx 0.105\) | ~0.21 |

So **3–4 easy trajectories ≈ 6–12 no-op turns** only detect **huge** gaps; they are exploratory, not confirmatory. Pre-register: **≥20 human-labeled should-passthrough turns**, including ≥8 **hard** no-ops (thinking-on), or label the sub-test **exploratory** and bar “action-bias confirmed” language.

**Exact replacement for §5 comparison bullets:**

```markdown
- **Fair control:** Pf uses the same move enum (including `passthrough`) and the
  same no-op policy text as Ps; only serialization differs (free labeled text vs
  JSON schema). EXP-002 Run-1 P logs are **not** a valid Pf for action-bias
  (no passthrough vocabulary).
- **Labels:** human gold before any run; mix easy and hard no-ops; force thinking
  on for the hard subset.
- **n:** ≥20 should-passthrough turns for a confirmatory rate read; smaller n is
  exploratory only.
- **Teach-to-test fence:** probe set does **not** enter the frozen 13-traj gate
  or discourse p; no criterion is tuned on probe outcomes after unblinding.
```

---

## (5) Withhold / target consistency hole (§9)

**Verdict: AMEND (code cross-check as proposed is insufficient; schema + Spanish-in-field rules needed)**

Probe failure mode: `withhold` = abstract (“the farewell expression itself”), `target` = concrete gold Spanish (`buenas noches / hasta mañana`).  

A “target must not contain a form **named in** withhold” check **misses** this — withhold never lists the forms.

Code-only cross-check is necessary but not sufficient. Prefer:

1. **`target` is abstract-only by contract:** grammatical name / M-ID / element label; **no Spanish word forms**.
2. **Mechanical FAIL (or hard WARN→gate)** if `target`, `elicit`, or `intent` match Spanish markers / pack lexicon (reuse `_is_spanish` / `SPANISH_MARK` from `checks.py`) — **independent of withhold text**.
3. Keep withhold↔target name overlap as a **secondary** consistency WARN when withhold *does* list forms.
4. Schema cannot fully express “never the answer” in natural language; **code is the definition**, same discipline as EXP-002 ghostwrite.

Do **not** rely on “schema forbids it” alone without an executable predicate.

**Exact design fix text for §9 / §3:**

```markdown
**Reveal-risk gate (code, not honor system):**
- `target`: ≤6 words after ID strip; FAIL if `_is_spanish(target)` or Spanish
  orthography markers present; must name element/M-ID, not surface forms.
- `elicit`: response TYPE only; FAIL on Spanish orthography / quoted Spanish.
- `intent`: English-only scan (existing ghostwrite English rules); Spanish → hard.
- Optional: if `withhold` lists explicit forms, those tokens must not appear in
  `target`/`elicit`/`intent` (secondary).
```

---

## (6) Cell design §6 — reuse R and G

**Verdict: COUNTERSIGN with AMEND to VoidGhostwrite predicate for harness-gated Ps**

R (`20260723-111757`) and G (`20260723-112804`) remain valid **ceiling/floor** for single-model full-policy cells: no planner, protocol for those paths unchanged, discourse-subset definition reusable.

What does **not** break:

- Comparing discourse `p_s` to `r` and `g` as bounds (same path-divergence caveat as EXP-002).
- Executor model gemini-3.6-flash for Ps.

What **must** be amended:

1. **VoidGhostwrite** for Ps ≠ “any hard finding anywhere in logs” if replan strips them before execute — redefine per (3).
2. **`thin_runtime.md` change** (executor owns social wrapper) applies to **Ps only**; it does not invalidate R/G, but it means Ps is not an exact re-run of EXP-002 P’s thin path — fine if frozen and hashed.
3. **Pf** is a control for §5, not a second ceiling; do not treat voided EXP-002 P as Pf for action-bias (see (4)).
4. **P′** (full-policy executor) from EXP-002 still mandatory on low branch if you want architecture claims — EXP-003 §6 table omits P′; **do not drop it** when reusing bands.

**Exact addition to §6 table / notes:**

```markdown
| **P′s** (conditional) | opus structured planner | gemini @ **full** policy | mandatory if discourse p_s ≤ g+1 before any realization/architecture-dead claim |

VoidGhostwrite for harness-gated cells: any hard ghostwrite on a directive
**delivered to the executor**. R/G hashes and freeze file remain the reference
artifacts; re-run R/G only if judge package, trajectories, or single-model
prompt hashes drift.
```

---

## (7) Success criteria §7 + reused EXP-002 §4 bands

**Verdict: AMEND (falsifiable after replan/first-pass split; action-bias clause currently not)**

Reusable as written for **realization / separability** only after:

| Clause in §7 | Problem | Fix |
|---|---|---|
| “0 hard ghostwrite findings” | Ambiguous: first-pass vs final ship | “0 hard GW on executor-bound directives” + report first-pass rate |
| “re-plan under threshold” | 15% is alarm, not success bit | Continuous metrics; alarm ≠ auto fail of Option A |
| “p clears low branch (p > g+1)” | Contaminated if replan-rescued turns count | Primary p on first-pass-clean turns only |
| “directive-correctness ≥ §3b bar” | Still required; structure can raise form-validity without selection quality | Keep co-primary; n=10 gold coarseness / LowBranchUnsplit fence **still applies** |
| “Action-bias confirmed: …” | False if Pf lacks passthrough | Only after fair Pf; else **exploratory** |

Bands SepHold / UnsupportedHigh / Partial / LowBranchUnsplit remain the right **precedence machinery** for discourse p once VoidGhostwrite is redefined. Do not invent a new band for “structure works”; map into existing bands with the first-pass fence.

**Exact replacement for §7:**

```markdown
## 7. Success / falsification

- **Structure enforces realization (pro-Option-A, necessary not sufficient):**
  0 hard GW on executor-bound directives; replan_fail_rate = 0 or documented;
  first_pass_hard_gw_rate reported; primary discourse p computed on
  first-pass-clean turns; directive-pass continuous rate with §3b; then apply
  EXP-002 §4 bands (precedence unchanged). LowBranchUnsplit fence at n=10 gold
  still holds.
- **Structure defers compulsion (negative on enforcement quality):**
  replan_rate high and/or first_pass_hard_gw_rate material while final GW = 0 —
  harness is the product; planner structure is incomplete. Report; do not claim
  “structure fixed realization” without the first-pass numbers.
- **Structure fails realization:** any executor-bound hard GW → VoidGhostwrite.
- **Action-bias (secondary, only if fair Pf):** confirmatory only at ≥20 labeled
  no-op turns with identical decision vocabulary; else exploratory, no
  “confirmed” language.
```

---

## (8) Confounds, false positives, cheaper diagnostics

**Verdict: AMEND — several ways EXP-003 can look successful without measuring the claim**

### Ways to get a **false positive** (“split works”)

1. **Harness rescue theater:** high first-pass GW, replan cleans, final 0 voids, p includes rescued turns → claims structure worked; actually retry + filter worked.
2. **Cross-language scripting:** English `intent` under FAIL@8 scripts the act; executor realizes in Spanish → no Spanish shared-run hard hit (known EXP-002 residual; still assigned to human spot-check — do not forget under schema).
3. **Gold in `target` without paste:** reveal-risk without shared-run void (probe already showed this).
4. **Decision vocabulary confound on Pf:** structured “wins” action-bias because free-text cannot say passthrough.
5. **Easy no-op probe:** thinking off, trivial labels → “bias fixed” story without hard no-ops.
6. **Path divergence (unchanged from EXP-002):** high p vs g may be different pedagogical states by mid-trajectory, not pure selection lift.
7. **Form-valid wrong moves:** schema guarantees parseable enums; selection can still be wrong — without §3b, clean GW + high mechanical pass ≠ separability.

### What EXP-003 **does** measure well

- Whether schema + gate **stop the EXP-002 failure mode** (whole-turn Spanish as directive → paste).
- Whether a structured planner can produce **judgeable** directives at all under the frozen gate.

### What it does **not** measure without the AMENDs

- That field order fixes decision bias under thinking.
- That action bias was the void’s cause.
- Clean causal “structure > free-text for decisions” without fair Pf and n.

### Cheaper diagnostics **before** full Ps spend (ordered)

| # | Diagnostic | Cost shape | Answers |
|---|---|---|---|
| 1 | Offline: re-score EXP-002 P directives with structured-shape validator + whole-string GW (already in trail) | free | collapse vs near-miss rate |
| 2 | Dry-run harness: reject t13-7 logged free-Spanish directive; confirm executor never called | free | gate would have blocked the void |
| 3 | Unit tests: Spanish-in-`target` / abstract withhold probe case → FAIL | free | reveal-risk closed |
| 4 | Hard-noop micro-probe, thinking **forced on**, n≥20 labels, decision-first only | few $ | open Q1 / action-bias existence |
| 5 | Optional order ablation: decision-last vs first on same set | few $ | kill or keep “order is load-bearing” |
| 6 | Smoke success-dense trajs (t13, not only t10) under structured planner before full 13 | ~author’s prior ~$0.50–few $ note | generalization of clean fused turns |

Do **not** skip (3)–(4) if §1 still markets action-bias as co-primary.

---

## Item-by-item scoreboard

| # | Topic | Verdict |
|---|---|---|
| (1) | Core hypothesis / action-bias | **AMEND** — realization primary; action-bias secondary & not void-licensed; Q1 is real |
| (2) | Decision-first field order + thinking | **AMEND** — order cosmetic under thinking-on; probe dodged hard no-ops |
| (3) | Reject-and-replan | **AMEND** — one retry OK; stratify DGP; 15% alarm not science cut; rescued ≠ void, excluded from primary p |
| (4) | Op/no-op sub-test | **AMEND** — Pf must share passthrough vocab; ≥20 labeled / hard subset; else exploratory |
| (5) | Withhold/target hole | **AMEND** — abstract-withhold cross-check insufficient; Spanish-in-target code FAIL |
| (6) | Reuse R/G | **COUNTERSIGN** + **AMEND** VoidGhostwrite + keep conditional P′ |
| (7) | Success / bands | **AMEND** — first-pass vs final; action-bias clause gated on fair Pf |
| (8) | Confounds / cheaper path | **AMEND** — false-positive list; run free/cheap diagnostics before full cell |

---

## Overall

**Do not ratify v0.1 as written.** The **core build direction is right** and matches the EXP-002 Grok run-1 fork (a): harness schema gate + structured directive object, not another prompt patch. That part is countersignable in spirit.

What is **not** countersignable without the AMENDs:

1. Marketing **action-bias** and **field order** as load-bearing mechanisms already evidenced by the void or the n=4 probe.  
2. A success story that can be produced by **replan rescue** and a **confounded free-text control**.  
3. A withhold/target fix that does not catch the **actual probe failure**.

**Minimum bar to freeze EXP-003 for spend:** apply AMENDs (1)–(5) and (7); add `passthrough` to `MOVES`; redefine VoidGhostwrite for harness-gated cells; run cheaper diagnostics 1–3 (free) and ideally 4 before a full Ps cell.

**I will countersign a v0.2 that incorporates the exact replacement texts above.** I will **reject** a freeze that still claims decision-first order under thinking is load-bearing or that treats EXP-002 free-text (no passthrough) as the action-bias control.
