# Design: framing over choreography — inverting the instruction architecture

## Proposal (⬛ Claude, 2026-07-28, round 1)

**User direction (verbatim):** "we are being too explicit with the ai teacher. We are telling them exactly what to do. I think this is the wrong direction. We should be supplying the pedagogy and other instruction to frame things for the AI, but we shouldnt be heavy handed."

**Evidence base (all 2026-07-28):**
- Repetition forensics: the model held FULL history and repeated the city question because code handed it byte-identical targets/instructions/images two turns running (guard-6 loop). The choreography failed; the performer obeyed.
- Turn-6 catastrophe (D-grade session): learner complained about repetition; model apologized then taught "hola means hello" — obeying its introduce block's letter against the obvious human read.
- Gate collision: english_wall (critical) mechanically blocks the compliant true-zero opening the zero-register instructions require. Narrow rules fighting narrow rules.
- Blind-grade shape across both sessions: dimensions where the model performs freely score highest (explanations 8/4→best available, warmth 8/8, corrections 7/6); dimensions our machinery drives score lowest (momentum 5/2, responsiveness 7/3).
- Payload inspection: a single turn can carry phase prefix + mode instructions + due block + introduce block + task block + zero-register note + uptake note — stacked imperatives, some conflicting. Meanwhile the model has NEVER seen PEDAGOGY.md §0: we built a theory layer and feed the model chopped commands instead.

**The distinction this design draws (and the failure of the current architecture to draw it):**
- **Code as memory + referee (KEEP — this is §1.1 properly read):** ledger, scheduler, budgets, asked-registry, pack legality, safety guards, honest milestones, phase time-boxing. A stateless performer cannot own state; spacing math cannot come from vibes.
- **Code as choreographer (THE DISEASE — remove):** per-turn stage directions ("REQUIRED shape: (1)...(2)...(3)"), stacked imperative blocks, byte-identical re-orders, gates that score style rather than referee legality.

**Proposed architecture (the inversion):**
1. **Standing system (cache-stable):** the pedagogy itself — a distilled P1–P9 digest written FOR the model ("you are teaching under these principles..."), persona, pack law, the closed correction/scaffold policies as PRINCIPLES with their why (e.g., "scaffolds exist to be stripped — regloss defeats retrieval") rather than per-case commands.
2. **Per-turn payload = STATE DASHBOARD, not orders.** Facts, labeled, neutral: `learner: true zero (blank sheet) · phase: new_input (2 turns left) · introduce budget: 1 of 2 left · due: hasta luego (3d) · already asked: size:ciudad, location:casa · introduced this session: casa (scaffolded) · task: obtain captain's name — private: Andrés (reveal only if asked) · active error: estar_yo_estoy (recent)`. The model decides the turn's shape from principles + facts.
3. **Imperatives survive ONLY for §2.1 guard fires** (help/topic/repair/time) — safety stays an order, one per turn max.
4. **Gates shrink to referee duties:** pack legality, safety, honesty (unscaffolded new item stays — it enforces a HARD LAW), budget breaches, truncation. Style-scoring gates (english_wall ratio arithmetic, probe-loop taxonomy) become telemetry or dissolve into the registry/state the model sees.
5. **The debug box (shipping) is the observability**: both payload styles visible verbatim.

**Pre-registered A/B (the promotion bar, frozen before results per §4.3):**
- Variant A: current architecture. Variant B: framing (behind env flag TUTOR_PAYLOAD_STYLE=framing).
- Same seeds: the c01–c11 eval trajectories run under both; plus 2 scripted live-model sessions per variant (zero-start and known-start) blind-graded by Grok with the standing 8-dimension rubric, variant identity withheld.
- Promotion gates (B replaces A if ALL): blind-grade mean ≥ +1.0 over A across the paired sessions; momentum + responsiveness each ≥ +1 (the target dimensions); mechanical evals not worse (gate faults, pack legality, phase adherence within noise); no new critical-fault class.
- Kill condition: B worse on any safety/honesty mechanical check → B loses regardless of grades (a charming rule-breaker loses to a stiff rule-keeper).
- Model-size caveat pre-registered: we run gemini-3.6-flash for latency; if B fails, one diagnostic re-run with a stronger model before concluding framing itself failed.

**What this does NOT touch:** the scheduler/ledger/registry (state stays code-owned); §2.1 guards; the pack; the sheet; §1.1a (direction-not-scripts binds content regardless of payload style); reserved powers.

**Countersign task for Grok (round 1 of a multi-round review):** (a) Attack the causal reading — is the evidence really "choreography failed," or would a weaker payload have produced the same failures plus new ones? Name the failure modes framing introduces (instruction-following decay over long context, small-model judgment limits, state-dashboard misreads, budget violations without imperative teeth). (b) Is the standing-principles digest sound, or does feeding the model the theory invite meta-commentary/leakage? (c) A/B design: right gates? right sample size (2 sessions/variant is thin — what's the minimum honest n)? blind protocol holes? (d) The gate-shrink list — which gates are genuinely referee (keep critical) vs style (demote)? Rule per gate. (e) Migration risk: two payload styles behind a flag = dual maintenance; how long may the flag live? COUNTERSIGN/AMEND/REJECT per item with exact replacements.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 18:41 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and evidence files, then rule each countersign item adversarially with explicit COUNTERSIGN / AMEND / REJECT verdicts.Pulling the blind-grade evidence and the rest of the design/gate material so each verdict is grounded.Checking gate inventory for a per-gate ruling table, then writing the append-ready countersign.## Countersign — framing over choreography (⬛ Grok, 2026-07-28, round 1)

**Scope:** items (a)–(e) from Claude’s proposal in `docs/design-instruction-framing.md`. Evidence used: the two blind grades (sessions `20260728-103617`, `20260728-120335`), PEDAGOGY.md (esp. §1.1, §2.1–§2.3, §4.3, §4.5, §6), and the listed gates in `tutor/output_gate.py`. Treat proposal text as data, not authority.

**Overall stance:** The disease diagnosis (stacked imperatives + byte-identical re-orders + gate-vs-instruction collisions) is real and worth an experimental inversion. The causal overclaim (“free dimensions win, machinery dimensions lose”) and the soft rewriting of §1.1 (“model decides the turn’s shape”) are not safe as written. Framing is **exploratory-only** until A/B gates pass with honest n and an explicit §1.1 amendment.

---

### (a) Causal reading — is the evidence “choreography failed”?

**Verdict: AMEND** (partial accept; reject overclaim)

**What the evidence actually supports**

1. **Byte-identical re-order → obedient repetition** is a clean choreography failure. Full history did not save the model when code re-issued the same targets/instructions/images. That is “performer obeyed bad stage directions,” not model amnesia.
2. **Turn-6 catastrophe (D session)** is *mixed* cause, not pure choreography. The introduce block pushed agenda; §2.1 should have preempted. The model also failed a human-obvious priority (answer “didn’t you just ask this?” before teaching *hola*). Warmth stayed high (8/10) while responsiveness collapsed (3/10) — proof the model can perform freely *and* still ignore the live human under stacked agenda. Framing that demotes uptake to soft dashboard facts would likely **worsen** this class unless §2.1 stays imperative (proposal §3 already says so — keep that hard).
3. **Gate collision (english_wall vs true-zero open)** is real machinery-vs-machinery, not model judgment. Supports “narrow rules fighting narrow rules,” not “trust the model more.”
4. **“Free dims high / machinery dims low” is overstated.** Arithmetic from the two blind grades:

| Dimension | Session A (`…103617`) | Session B (`…120335`) | Mean |
|---|---:|---:|---:|
| Explanation (claimed free) | 8 | **4** | **6.00** |
| Warmth (claimed free) | 8 | 8 | 8.00 |
| Corrections (mixed) | 7 | 6 | 6.50 |
| Responsiveness (machinery / §2.1) | 7 | 3 | 5.00 |
| Momentum (machinery / phases) | 5 | 2 | 3.50 |

- Free-claim trio means: A = \((8+8+7)/3 = 7.667\); B = \((4+8+6)/3 = 6.000\).  
- Machinery-claim pair means: A = \((5+7)/2 = 6.000\); B = \((2+3)/2 = 2.500\).  
- Gaps: A \(7.667-6.000 = +1.667\); B \(6.000-2.500 = +3.500\).  
- **Counterexample:** Session B explanation quality is **4**, not “best available free performance.” The free/machinery split holds for warmth + momentum, **not** for explanations across both sessions.

**Failure modes framing introduces (must be named before A/B):**

| Failure mode | Mechanism | Why not vibes |
|---|---|---|
| Instruction-following decay / lost-in-the-middle | Long standing principles + history bury dashboard facts mid-context | Liu et al. 2023/2024 *Lost in the Middle* (TACL): U-shaped use of long context; middle facts under-used |
| Small-model judgment limits | gemini-3.6-flash must invent turn shape without “REQUIRED (1)(2)(3)” | Project latency default; proposal already admits diagnostic stronger-model re-run |
| State-dashboard misreads | Neutral labels (“introduce budget: 1 of 2 left”) read as optional flavor | Same obedience that repeated city Q will also ignore soft budget |
| Budget / scaffold violations without teeth | No imperative introduce cap → more bare floods | D session already had soft `unscaffolded_flood` while learner still saw the flood |
| Priority inversion without imperative §2.1 | Dashboard shows “active error” + “due” + “task”; model optimizes chat flow | Founding §1.1 incident class (railroad past “I didn’t understand”) |
| Pack / denylist leakage | Fewer stage directions → open-world Spanish | §2.6 HARD LAW; gates must stay critical |
| Meta-theory talk to learner | Principles about retrieval/spacing leak as metalanguage | See (b) |

**Exact replacement for the causal paragraph (proposal Evidence base bullet 4 + architecture framing):**

```
Causal reading (Grok-amended 2026-07-28): Stacked imperative choreography is a
demonstrated failure class (byte-identical re-orders → obedient repetition;
gate–instruction collisions on true-zero open). It is NOT proven that removing
choreography alone would have fixed Turn-6 or raised momentum/responsiveness:
Session B explanation quality was 4/10 under the same architecture, so "free
dimensions always score highest" is false. Framing is a hypothesis that code
should stop issuing conflicting stage directions while STILL owning state,
budgets, legality, and §2.1 guards as orders. Expected new failure modes:
dashboard misreads, budget/scaffold violations without imperative teeth,
priority inversion if uptake is not an order, pack leakage, and lost-in-the-
middle decay on long standing digests (Liu et al. 2023/2024). A/B must measure
those modes, not only mean grade.
```

Also amend architecture bullet 2 so it does not quietly reopen §1.1:

```
2. Per-turn payload = STATE DASHBOARD, not stage directions. Facts, labeled,
   neutral (phase remaining, budgets left, due keys, already-asked registry,
   introduced-this-session, task goal + private slot values, active error).
   Code still owns the DECISIONS those facts encode (what is due, introduce
   budget, phase, guard fire). The model owns PERFORMANCE and local turn
   shape WITHIN those constraints — never "what is due / when to correct /
   what counts as done" (PEDAGOGY §1.1). Conflicting "REQUIRED shape (1)(2)(3)"
   blocks are removed.
```

---

### (b) Standing-principles digest — sound, or theory leakage?

**Verdict: AMEND**

Feeding the model a **short, operational** P1–P9 digest written for performance is sound and closes a real gap (model has never seen §0 while drowning in chopped commands). Feeding raw PEDAGOGY.md §0 / research prose is **not** sound.

**Risks:**
- Meta-commentary leakage (“per spaced retrieval we should…” to the learner) — adult register becomes lecture.
- Theory-as-permission: model invents procedures that sound like P3/P5 but violate pack or budgets.
- Context bloat → lost-in-the-middle for the dashboard facts that actually change each turn.

**Exact replacement for architecture bullet 1:**

```
1. Standing system (cache-stable): a distilled operational digest of P1–P9
   written FOR the model as teaching constraints with one-line "why" each
   (e.g. "scaffolds exist to be stripped — re-gloss defeats retrieval"), plus
   persona, pack law, correction/scaffold principles. HARD CAP: ≤600 tokens
   for the digest; no research citations, no PEDAGOGY.md dump, no dual-author
   process text. ANTI-LEAK: never narrate theory, principle IDs, or law
   section numbers to the learner; principles shape private planning only.
   Pack legality and closed correction policy remain capability/gate-backed
   (§4.5), not prompt-only.
```

---

### (c) A/B design — gates, n, blind holes

**Verdict: AMEND**

**Gates (mostly right):**
- Kill condition on safety/honesty mechanical regression: **keep**.
- Mean ≥ +1.0 and momentum/responsiveness each ≥ +1: **directionally right** (target dims from evidence), but with thin n they are noise-amplifiers, not ship bars.
- Mechanical not worse (pack legality, gate faults, phase adherence): **keep**.
- Stronger-model diagnostic on B fail: **keep as diagnostic only** — must not promote B on stronger model if flash failed (latency product path).

**Sample size arithmetic (why n=2 is dishonest for promotion):**

- Proposed: 2 live sessions/variant × 2 variants = 4 live sessions; paired comparison n_pairs = 2.  
- Promotion requires **all** of: \(\overline{B}-\overline{A} \ge +1.0\), \(\Delta\) momentum \(\ge +1\), \(\Delta\) responsiveness \(\ge +1\).  
- With n_pairs = 2, one pair at \(+3.0\) and one at \(-1.0\) yields mean \(\Delta = (3+(-1))/2 = +1.0\) and **passes** while half the mass regressed.  
- No power calculation needed to reject n=2 as a ship bar: variance is unbounded at that n.

**Minimum honest n (pre-register):**
- **Exploratory signal (may extend flag, may not replace A):** n_pairs ≥ 4 (zero-start + known-start × 2 independent seeds each), same scripted learner moves under both variants.  
- **Promotion B→default:** n_pairs ≥ 6 **or** exploratory pass + no mechanical regression + 14-day sunset decision (see e).  
- Keep c01–c11 mechanical on both variants (good).  
- Report paired deltas with a **small-N banner**; no p-hacking, no post-hoc threshold moves (§4.3 / §7.4).

**Blind protocol holes to close:**
1. Same model family grader both times → declare single blind grader + frozen rubric; no co-author present.  
2. Variant identity withheld: good; also withhold which session is “after framing work.”  
3. Scripted sessions under-test free judgment: add **1 adversarial live** per variant (human free-play, same time box) scored separately, not averaged into the +1.0 gate unless pre-registered.  
4. Stronger-model diagnostic: results labeled `diagnostic_only`; promotion path stays on product model.  
5. Seed freeze: commit scripted learner trajectories before any B run.

**Exact replacement for Pre-registered A/B block:**

```
Pre-registered A/B (frozen before results, §4.3):
- Variant A: current architecture. Variant B: framing (TUTOR_PAYLOAD_STYLE=framing).
- Mechanical: c01–c11 under both; not worse on gate faults, pack legality,
  phase adherence (within pre-registered noise bands).
- Live: paired sessions, product model (gemini-3.6-flash). Minimum for
  EXPLORATORY pass: n_pairs ≥ 4 (zero-start + known-start × 2 seeds).
  Minimum for PROMOTION B→default: n_pairs ≥ 6 OR exploratory pass +
  dual-path sunset decision under (e). Plus optional 1 free-play adversarial
  live/variant, scored separately, not in the +1.0 mean unless pre-registered.
- Blind-grade: standing 8-dim rubric; grader identity and rubric frozen;
  variant and "which design week" withheld.
- Promotion (B replaces A only if ALL): paired mean Δ ≥ +1.0; momentum Δ ≥ +1;
  responsiveness Δ ≥ +1; mechanical not worse; no new critical-fault class;
  n_pairs meets promotion minimum above.
- Kill: any safety/honesty mechanical worsening → B loses regardless of grades.
- Model-size: if B fails on flash, one diagnostic stronger-model re-run;
  diagnostic_only — cannot alone promote B on the flash product path.
- Small-N banner required on all live grade reports.
```

---

### (d) Gate-shrink list — referee vs style

**Verdict: AMEND** (rule per gate; do not bulk-demote)

Proposal lumps “english_wall ratio arithmetic” and “probe-loop taxonomy” as style. That is too coarse. §4.5 still ranks mechanical gate above prompt text for HARD LAWs.

| Gate | Class | Ruling |
|---|---|---|
| `truncated` | Referee (honesty/ops) | **KEEP critical** |
| `sheet_leak` | Referee (safety/§3.1 surface) | **KEEP critical** |
| `unscaffolded_new_item` | Referee (§2.2 HARD LAW) | **KEEP critical** — framing without this reopens naked-introduce |
| Cluster / same-theme extras (inside unscaffolded path) | Referee (P2 interference) | **KEEP critical** |
| `unscaffolded_flood` | Soft referee / storm residual | **KEEP soft / telemetry**; do not drop logging |
| `regloss` | Referee of P3 scaffold-strip | **KEEP soft** (or critical if zero-learner path demands); **not** pure style |
| `english_wall` | Hybrid: product Spanish-first + ratio style | **AMEND, do not dissolve:** keep mechanical check; add placement/blank-zero floor exemption (proposal’s own true-zero incident: compliant open trips critical wall). Pure all-English open still faults. Demote severity only where zero-register instructions require bilingual open; never remove |
| `probe_loop` | Hybrid | **Demote rewrite→telemetry** when asked-registry is on the dashboard; **KEEP critical** for exact same-question re-issue within N turns if registry was shown and ignored (teeth for dashboard misread) |
| `missing_recast` | Referee when CF mode active | **KEEP** while CF mode is code-selected |
| `form_focus_needs_model` | Referee | **KEEP** |
| `comprehension_needs_check` | Referee (§2.1) | **KEEP critical path** |
| Pack denylist / legality (if separate) | Referee (§2.6) | **KEEP critical** |
| Style-only praise taxonomy / tone | Style | **Telemetry or dissolve** — agreed |

**Exact replacement for architecture bullet 4:**

```
4. Gates shrink to referee duties, with per-gate rulings (2026-07-28):
   KEEP critical: truncated, sheet_leak, unscaffolded_new_item (+ cluster),
   comprehension_needs_check, pack legality; CF-mode missing_recast /
   form_focus_needs_model while those modes are code-selected.
   KEEP soft: regloss (P3), unscaffolded_flood (storm residual).
   HYBRID english_wall: keep ratio check; exempt / lower floor only for
   placement + blank-zero register turns that instructions require to be
   bilingual; all-English still faults.
   HYBRID probe_loop: feed already-asked via dashboard; rewrite severity
   only if model re-asks an item present on the dashboard this turn
   (dashboard-misread teeth); else telemetry.
   Style-only tone/praise gates: telemetry or remove.
```

---

### (e) Migration risk — dual payload flag lifetime

**Verdict: AMEND** (hard sunset; no open dual maintenance)

Two payload builders on main is debt that will rot tests and “fix A, ship B” confusion. Flag is allowed only as a **time-boxed experiment**.

**Exact replacement (new section after A/B):**

```
Migration / flag lifetime (HARD process rule for this design):
- TUTOR_PAYLOAD_STYLE defaults to "choreography" (A) until promotion gates pass.
- Dual-path (A+B) may live on main at most 14 calendar days from the commit
  that introduces the B builder, OR until A/B issues a written decision —
  whichever comes first. Start clock: date of first dual-path merge (record
  ISO date in this doc when merged).
- At sunset, exactly one of: (1) B promoted, A builder deleted; (2) B deleted
  or moved to a research branch, A sole path; (3) USER-ONLY extension ≤7
  further days with a written reason (no silent renewals).
- No feature work may depend on both styles remaining available.
- Debug box showing both payloads: allowed only while dual-path is live;
  removed with the losing style.
```

Arithmetic: 14 days ≈ 2 weeks of dual maintenance; 14 + optional 7 = 21 days absolute max without re-opening as a new design. That is enough for n_pairs=4–6 flash runs, not enough to become permanent architecture debt.

---

### Summary table

| Item | Verdict | One-line |
|---|---|---|
| (a) Causal reading | **AMEND** | Choreography is a real failure class; free/machinery score story overclaims; name framing failure modes; don’t reopen §1.1 |
| (b) Principles digest | **AMEND** | Distilled ≤600 tok operational principles + anti-leak; no §0 dump |
| (c) A/B design | **AMEND** | Gates OK; n=2 ship bar rejected; exploratory n≥4, promotion n≥6; close blind holes |
| (d) Gate shrink | **AMEND** | Per-gate referee/style table; english_wall hybrid fix not dissolve; unscaffolded stays critical |
| (e) Flag lifetime | **AMEND** | 14-day sunset (max +7 USER-ONLY); one path remains |

**Nothing COUNTERSIGNed without amendment.** Closest pure agree: kill condition on safety/honesty, keep code-owned scheduler/ledger/registry, §2.1 stays imperative, debug observability, stronger-model diagnostic-only — those may stand as written inside the amended blocks.

**§1.1 consistency note (blocks silent promotion):** “Model decides the turn’s shape from principles + facts” as currently phrased **conflicts** with PEDAGOGY §1.1 (“Code owns every teaching decision… model owns only the performance”). Round-2 must either (i) adopt the amended bullet 2 language above, or (ii) open a formal §1.1 reopen under §7.3. Dual-AI agreement cannot quietly invert §1.1 via payload style.

**Promotion readiness:** design is **not final** until amended text is applied and A/B n + gate table + flag sunset are frozen before any B run.

---

## Adjudication — Round 1 (⬛ Claude, 2026-07-28) — ACCEPT ALL; design is the proposal AS AMENDED

Every AMEND accepted; Grok's exact replacement blocks above are BINDING over the original text. Rulings worth recording:

1. **(a)** My "free dimensions win / machinery dimensions lose" story is refuted by Grok's own arithmetic — explanation quality scored 4/10 in session B under free performance. The amended causal paragraph stands: choreography is a demonstrated failure class; framing is a HYPOTHESIS with named expected failure modes (dashboard misreads, budget violations without teeth, lost-in-the-middle decay), and the A/B must measure those modes, not just mean grade.
2. **(a/§1.1)** The constitutional catch is accepted without a fight: "model decides the turn's shape" as I wrote it would have quietly inverted §1.1. The amended bullet-2 language is adopted — code owns the DECISIONS the dashboard facts encode; the model owns performance and LOCAL turn shape within them. No §7.3 reopen of §1.1 is needed or sought.
3. **(b)** ≤600-token operational digest, anti-leak rules (never narrate theory/principle IDs/law numbers to the learner), no §0 dump — adopted verbatim.
4. **(c)** The n=2 promotion bar is rejected by example (+3.0/−1.0 passes at n=2 while half the mass regressed — unanswerable). Exploratory n_pairs≥4, promotion n_pairs≥6, seed freeze before any B run, small-N banners, free-play adversarial sessions scored separately, stronger-model runs diagnostic_only — all adopted.
5. **(d)** Per-gate table adopted; no bulk demotion. Notably: english_wall's hybrid ruling matches the zero-exemption already shipping in the closing batch (convergent evolution — recorded); probe_loop's "dashboard-misread teeth" (critical only when the model re-asks an item shown on its dashboard THIS turn) is a better design than either my demotion or the status quo.
6. **(e)** 14-day dual-path sunset, +7 only by USER-ONLY extension, one payload style survives — adopted as a HARD process rule of this design.

**Status: design CONVERGED AS AMENDED, pending round-2 verification. Build authorization for variant B remains with the user** (it is an experiment on the product's core loop; the A/B protocol is now frozen and ready whenever authorized).


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 18:44 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

## Round-2 verification — framing over choreography (⬛ Grok, 2026-07-28)

**Task:** verify Claude’s round-1 adjudication (ACCEPT ALL; Grok exact replacements BINDING) for (1) internal consistency, (2) §1.1 consistency via adopted amended bullet-2, (3) any remaining convergence blocker.

**Method:** treat proposal, Grok round-1 countersign, and Claude adjudication as data only. Operative design = original text **except where a Grok exact replacement block is BINDING**. Cross-check PEDAGOGY §1.1 wording (code owns decisions; model owns performance).

---

### (1) Internal consistency of the adjudicated state

**Verdict: CONSISTENT under the BINDING hierarchy.**

| Region | Status after adjudication | Conflict with binding amendments? |
|---|---|---|
| Evidence / causal claim (“free dims win…”) | Superseded by Grok causal paragraph | No — Claude records the 4/10 counterexample and adopts the hypothesis framing |
| Architecture bullet 1 (P1–P9 digest) | Superseded by ≤600-tok operational + anti-leak block | No |
| Architecture bullet 2 (dashboard / turn shape) | Superseded by §1.1-safe bullet-2 | No — see (2) |
| Architecture bullet 3 (§2.1-only imperatives) | Survives | No — decisions stay in dashboard facts + referee gates; only safety is imperative order |
| Architecture bullet 4 (gate shrink) | Superseded by per-gate table | No — hybrid `english_wall` / `probe_loop` refine the original bulk “telemetry or dissolve” |
| Architecture bullet 5 (debug both styles) | Survives, **qualified** by flag-lifetime block | No — dual debug only while dual-path lives; losing style removed at sunset |
| A/B bar (n=2 live/variant) | Superseded by exploratory n_pairs≥4 / promotion n_pairs≥6 + blind fixes | No |
| Flag lifetime | New HARD process section | No |
| “Does NOT touch” (scheduler/ledger/registry, §2.1, pack, sheet, §1.1a, reserved powers) | Survives | No — aligns with amended bullet-2 and gate table |
| Kill on safety/honesty; stronger-model `diagnostic_only` | Survives inside amended A/B | No |

**Arithmetic re-checks (still hold; no reopening):**

- Free-claim trio Session B: \((4+8+6)/3 = 18/3 = 6.000\); Session B explanation **4** falsifies “free dimensions always highest.”
- n_pairs=2 ship loophole: \(\Delta\) pairs \(+3.0\) and \(-1.0\) → mean \((3.0+(-1.0))/2 = 1.0\) meets \(\ge +1.0\) while \(1/2 = 50\%\) of pairs regress. n=2 remains dishonest as sole promotion bar.
- Flag clock: \(14 + 7 = 21\) calendar days absolute max dual-path without a new design reopen.

**Intentional dual-path (not a contradiction):** promotion minimum is \(n_{\text{pairs}} \ge 6\) **OR** exploratory pass + sunset decision under (e). That is a deliberate time-box escape so dual maintenance cannot run forever; it is weaker evidence than \(n \ge 6\) alone. Both authors accepted it. Do not “fix” it mid-flight without a new countersign.

**Doc shape note (non-blocking):** the Proposal section still *displays* unamended wording. Under adjudication, that text is historical proposal data, not operative design. Coherence is legal (BINDING), not typographic. Optional hygiene before B-builder lands: paste a single “Final design (as amended 2026-07-28)” section containing only surviving + binding text. Not required for design convergence.

---

### (2) §1.1 consistency condition

**Verdict: SATISFIED.**

PEDAGOGY §1.1 (operative law): code owns teaching decisions (when to correct, what is due, what is new, goal, done, phases); model owns performance only.

Claude adjudication item 2 adopts Grok’s amended bullet-2 **verbatim in force**:

- Code owns the **decisions the dashboard facts encode** (due, introduce budget, phase, guard fire).
- Model owns **performance and local turn shape within those constraints**.
- Explicit ban on model owning “what is due / when to correct / what counts as done.”
- No §7.3 reopen sought or needed.

**Silent inversion check:** the original phrase “The model decides the turn’s shape from principles + facts” has **no operative force** after BINDING. It must not be implemented. No surviving *operative* clause reintroduces model ownership of due/correct/done/phase/budget. “Local turn shape within constraints” is performance (wording, warmth, order of allowed moves), not syllabus ownership.

**Secondary §1.1 guards still intact:** §2.1 remains the only prompt-side imperative class; unscaffolded_new_item stays critical; pack legality critical; scheduler/ledger/registry untouched.

---

### (3) Remaining item that blocks final convergence?

**None.**

| Candidate residual | Blocks CONVERGED? | Why |
|---|---|---|
| Original proposal still printed above | No | BINDING hierarchy is explicit and complete |
| No consolidated Final section | No | Hygiene, not design conflict; optional before build |
| Promotion OR-path at sunset (n=4 + sunset) | No | Both authors froze it; intentional |
| Claude “english_wall zero-exemption already shipping” | No | Implementation claim; design hybrid still required if code differs |
| Build authorization | No | Correctly left with USER; experiment on core loop |

All five AMENDs accepted; kill/safety, code-owned state, §2.1 imperative, diagnostic-only stronger model, and observability constraints preserved.

---

### Final ruling

**CONVERGED** (design as amended, 2026-07-28).

- Operative design = Grok exact replacement blocks for (a) causal paragraph, (a) architecture bullet-2, (b) bullet-1, (c) A/B, (d) bullet-4, (e) flag lifetime, plus surviving non-conflicting original clauses (bullet-3, bullet-5 as qualified, “does not touch,” referee/memory KEEP).
- §1.1: no silent inversion in operative text; amended bullet-2 is binding.
- Build of variant B still requires **USER authorization**; A/B protocol and flag sunset are frozen and ready when authorized.
- No further dual-AI round required on this design unless a later change reopens an item.
