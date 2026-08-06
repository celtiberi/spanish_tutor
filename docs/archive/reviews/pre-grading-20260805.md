# Design round: code-side "pre-grading" facts for the teacher (2026-08-05)

USER: "should we do an 'pre grading'? Like should we look at what the
user wrote and add some of our code-only grading remarks that can be
extra info for the AI?"

## Proposal (Claude, round 1 — for countersign)

### The constitutional tension (say it plainly)

The 2026-08-03 §1.1 rewrite DELETED `hard_observations` (regex error
hits, probe signals) from the teacher task: "code's opinion of the
lesson; the model reads the learner's actual words and the sheet
itself." A pre-grading block partially reverses that deletion, so it
needs countersign, not a quiet re-add.

### Why reopen: new evidence + new data

1. The lite tutor demonstrably CANNOT spell-audit: it credited
   "esta bein" as bien+estar and "me te name es Sam" as grammar
   (2026-08-05 gate forensics, sam_stuck 120 XP before the code audit).
   "The model reads the learner's actual words" was true of the strong
   model era; the cheap-model era breaks the premise.
2. We now hold offline GROUND TRUTH code didn't have then: wordfreq
   (garble detection: real A1 words ≥3.1 zipf, garble ≤2.7 — calibrated
   2026-08-05) and the Jehle conjugation DB (637 verbs, full paradigms).

### The line: facts, never opinions

Proposed turn-task block (small, ~30-60 tokens):

```json
"learner_text_facts": {
  "note": "mechanical dictionary facts — YOU judge what they mean",
  "tokens": [
    {"w": "esta", "es": true},
    {"w": "bein", "es": false, "nearest": "bien"}
  ],
  "verb_forms": [{"w": "esta", "lemma": "estar", "person": "3s"}]
}
```

Rules:
- Facts ONLY: spelling validity (wordfreq zipf≥3.0), nearest real word
  (edit distance ≤2 against the A1 inventory + conjugation forms),
  verb-form identification (Jehle DB). NEVER a band suggestion, NEVER
  "this is an error pattern", NEVER what to teach next.
- The teacher's judgment stays sovereign: typo-with-intent rules,
  register/person calls, and every grade remain the model's.
- English tokens marked es:false are expected and fine (learners mix);
  the note says facts not verdicts.
- Rides ONLY the round-turn task (facts about THIS message).

### Predicted effect + validation

Pre-registered A/B (persona gate): sam garble-crediting rate drops
(grade rows crediting invalid tokens); casey/sofia grading unchanged;
no english_wall/teach-shape regressions. If the facts block does not
move the garble-credit rate, it dies (no decoration).

### Risks to attack

1. Is "facts not opinions" a real line or a slippery slope back to
   mode routers? Where exactly does nearest-real-word cross into
   recast-suggestion?
2. Token cost per turn vs benefit.
3. Does naming "bein → bien" PRIME the teacher's recast so hard it
   stops reading the learner (over-anchoring)?
4. Should facts also ride the GRADING tool response path or only the
   task?
5. Does this reduce or increase grade inflation on names ("sam" is a
   valid-frequency token)?


---

## GROK (Grok Build CLI (1e1687c1cf6a)) - 2026-08-05 23:57 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll load the full prompt and the skill protocol, then attack the pre-grading proposal item-by-item with independent research.Next I'll pull the rest of the proposal context and research LLM anchoring from injected hints.Checking a few more quantitative details on the schema and anchoring magnitude:## Countersign: pre-grading facts block (2026-08-05)

**Author:** Grok (independent countersign)  
**Subject:** `docs/archive/reviews/pre-grading-20260805.md` — Claude round-1 proposal  
**Date of review:** 2026-08-05  
**Protocol:** VERDICT-LAST · 4-way rulings · kill-search · arithmetic shown

---

### Dated evidence (independent)

**E1 — §1.1 text (inlined ENGINEERING.md, HARD LAW, rewritten 2026-08-03).**  
Code may supply **facts** (“honest, complete, never scripted opinions”); the model owns teaching **decisions**. Deleted `hard_observations` was framed as “code’s opinion of the lesson” (regex error hits, probe signals). A pure dictionary lookup is closer to sheet/domain data than to mode routers — *if* the payload never implies the next move.

**E2 — LLM anchoring is real and not fixed by “ignore the hint.”**  
Lou & Sun (arXiv 2412.06593, posted 2024-12-09; journal form 2026): LLM numerical answers are sensitive to biased hints; CoT, “ignore anchor,” reflection are **insufficient**; multi-angle information reduces single-anchor capture.[[1]](https://arxiv.org/html/2412.06593v1)  
Huang et al. (arXiv 2505.15392v2, 2026-03-29): modern LLMs show anchoring on **22%–61%** of questions depending on model; conventional mitigations fail to eradicate it; reasoning helps somewhat; bias is shallow-layer / early.[[2]](https://mediate.com/ai-and-confirmation-bias/)  
Implication for this design: a single `nearest: "bien"` is exactly a high-salience semantic anchor next to the learner’s raw token.

**E3 — wordfreq Zipf mechanics.**  
wordfreq Zipf = log10(count per billion words); `small` wordlists cut off around Zipf **3.0**; unknown words default to **0**. Spanish (`es`) is supported. The proposal’s calibration story (real A1 ≥3.1, garble ≤2.7) is *internally* plausible but **conflicts** with the stated rule `zipf≥3.0` for `es:true` (gap of **0.1** Zipf units = factor of \(10^{0.1} \approx 1.26\times\) in frequency). That threshold must be one number, frozen pre-gate.[[3]](https://www.walturn.com/insights/the-polite-deception-how-ai-sycophancy-threatens-truth-and-trust)

**E4 — Jehle verb DB.**  
Fred Jehle conjugated Spanish verb database is a real offline resource (~600+ verbs / commonly cited as 600–637 depending on packaging). Lemma/person lookup is legitimate **form identification**, not teaching opinion — *when* the surface form uniquely matches a paradigm cell.[[4]](https://github.com/ghidinelli/fred-jehle-spanish-verbs)

**E5 — Accent / homograph trap (mechanical, not vibes).**  
Surface token `esta` is a real Spanish word (demonstrative *esta*) **and** the unaccented form of *está*. Emitting both `{"w":"esta","es":true}` and `{"w":"esta","lemma":"estar","person":"3s"}` is **not** a pure fact bundle: the second is a forced morph parse of an ambiguous orthography. For learner text “esta bein” that parse is often right pedagogically and still **opinion-shaped** as a singleton.

**E6 — Token-cost arithmetic (proposal’s “~30–60 tokens”).**  
Example JSON in the proposal is ~**200 characters**. At ~4 chars/token (JSON-ish): \(200 / 4 = 50\) tokens — inside the claimed band for a **2-token** utterance.  
Scale to a realistic A1 mix of length \(L\) tokens, emitting every token + optional nearest + optional verb row:

| L (learner tokens) | Rough payload chars (all tokens, 1 nearest, 1 verb) | Tokens @ 4 c/t |
|---|---|---|
| 2 (proposal example) | ~200 | ~50 |
| 8 | ~200 + \(6 \times 35\) ≈ 410 | ~103 |
| 15 | ~200 + \(13 \times 35\) ≈ 655 | ~164 |
| 25 | ~200 + \(23 \times 35\) ≈ 1005 | ~251 |

So “30–60” is true only for **very short** turns or a **capped** emission policy. Uncapped full-token dumps are not free.

**E7 — soft model / garble credit (proposal’s reopen evidence).**  
The sam_stuck / “esta bein” / “me te name es Sam” forensic is **not independently re-run in this countersign** (no eval logs inlined). Treated as **author-asserted incident**, not verified here. The *class* of failure (lite models over-crediting invalid surface forms) is credible enough to justify a **narrow experiment**, not a quiet law reversion.

---

### Per-item arithmetic (thresholds / costs)

1. **Zipf rule vs calibration:** proposal body says real ≥**3.1**, garble ≤**2.7**, rules say `es` if zipf ≥**3.0**. Unresolved band: \(3.0 \le z < 3.1\). Pick one; freeze before A/B.  
2. **Edit-distance neighborhood size:** for alphabet \(\Sigma\), length-\(n\) string, Levenshtein radius \(r=2\) neighbors grow \(\sim O(|\Sigma|^r n^r)\). Against a finite A1 inventory this is fine computationally; the **policy** risk is **one** winner labeled `nearest` → single-anchor injection (E2).  
3. **A/B kill bar (must be numeric, pre-registered):** define  
   \(g = \) fraction of grade rows that credit a token with `es:false` (or zipf below threshold) on persona `sam`.  
   Require \(g_{\text{facts}} < g_{\text{control}}\) by a pre-registered absolute drop (example freeze candidate: \(\Delta g \ge 0.15\) absolute, or relative \(\frac{g_c - g_f}{g_c} \ge 0.30\) if \(g_c \ge 0.20\)), plus non-inferiority on casey/sofia and no english_wall/teach-shape regressions. **Do not ship on “looks better.”**  
4. **Token budget freeze candidate:** hard cap **≤80 tokens** serialized JSON; if over, emit only `es:false` + verb_forms + OOV class — never full positive lexicon.

---

### Per-item rulings

#### 1) Constitutional reopen of deleted `hard_observations` under §1.1  
**ACCEPT_WITH_AMENDS**

Partial reverse is defensible **only** as **record-keeper dictionary facts**, not as re-imported lesson opinion. Regex “error hits / probe signals” stay dead. Reopen requires an explicit §1.1 / fact-surface note at law promotion time (LAW-PROMOTION GATE §7.2) — not a silent task field.

**Exact amendment — add under proposal “The constitutional tension”:**

```markdown
### Constitutional ruling (required before ship)
Under ENGINEERING §1.1 (2026-08-03), code may inject **offline dictionary facts**
about the current learner utterance (membership / frequency / form-ID against
frozen inventories). Code may NOT reintroduce deleted hard_observations:
no error-pattern labels, no probe/mode signals, no band/next-teach hints,
no "code thinks you should recast X."
This block is a fact surface co-located with the sheet data, not a mode router.
Ship only after (a) this paragraph is promoted into ENGINEERING.md and
(b) the pre-registered A/B kill bar passes.
```

#### 2) Claim: “mechanical dictionary facts — YOU judge” is a clean facts/opinions line  
**ACCEPT_WITH_AMENDS** (line is real **if** narrowed; currently drawn too generously)

**What stays fact:**  
- token string as observed  
- `in_es_lexicon` / zipf (or boolean above frozen threshold)  
- optional multi-match verb-form **candidates** from Jehle against surface (±accent strip), never a single forced person when ambiguous  

**What is already opinion / recast-adjacent:**  
- singleton `nearest: "bien"`  
- singleton `person: "3s"` on accentless `esta` without listing alternates  

**Exact replacement for the example schema + rules block:**

```json
"learner_text_facts": {
  "v": 1,
  "note": "Offline dictionary lookups only. Not grades, not recasts, not next moves. YOU judge intent and bands.",
  "tokens": [
    {"w": "esta", "es": true, "zipf": 5.2},
    {"w": "bein", "es": false, "zipf": 0.0, "cands": ["bien"]}
  ],
  "verb_forms": [
    {"w": "esta", "matches": [
      {"lemma": "estar", "form": "está", "person": "3s", "mood": "ind", "tense": "pres"},
      {"note": "surface_also_demonstrative_esta"}
    ]}
  ]
}
```

**Rules (replace proposal rules bullet list):**

```markdown
Rules (HARD for implementers):
1. Facts ONLY, closed vocabulary of fields: w, es, zipf, cands[], verb_forms[].matches[].
   FORBIDDEN fields forever: band, error_pattern, teach_next, recast, severity, probe, mode.
2. `cands` (not `nearest`): 0–3 inventory/conj neighbors at edit distance ≤2.
   - Emit `cands` ONLY when `es:false` (or zipf below frozen threshold).
   - If zero or >3 candidates inside radius, emit `cands: []` (no forced winner).
   - Never emit a single-candidate field named `nearest` (single-anchor priming).
3. Spelling validity: one frozen threshold T_zipf (proposal must pick 3.0 OR 3.1 —
   default AMEND: T_zipf = 3.1 to match stated A1 calibration; document wordlist size).
4. Verb-form ID: Jehle lookup after accent-strip. If >1 legal parse, list matches;
   never collapse to one person/lemma without listing the alternate surface reading.
5. Teacher sovereignty unchanged: typo-with-intent, register/person, every grade = model.
6. English / name / OOV: `es:false` is expected; add `"cls": "en"|"name_or_oov"|"unk"`
   when detection is pure surface (ASCII name-like, or not in ES∪EN A1 inventories).
   Never mark a name as Spanish success evidence in this block.
7. Emission policy: default emit only (a) es:false tokens, (b) verb_forms for tokens
   that hit the conj table, (c) cls=name_or_oov. Do NOT dump es:true for every
   valid token unless under a debug flag — positive lexicon spam is cost without signal.
8. Hard serialized cap: ≤80 tokens of JSON. Over cap → drop es:true rows first.
9. Rides ONLY the round-turn teacher task for THIS learner message (pre-decision).
10. Does NOT ride grading-tool *response* path (post-decision; too late for this grade).
```

#### 3) Risk 1 — slippery slope / does `nearest` cross into recast-suggestion?  
**REJECT_CLAIM** on “`nearest` is still just a fact.”  
**ACCEPT_WITH_AMENDS** on the overall facts program (via schema above).

**Where the line is:**  
- Fact: “`bein` is not in the ES inventory; edit-distance neighbors inside the frozen inventory are {…}.”  
- Recast-suggestion: “`nearest: bien`” as a privileged singleton beside a teaching model that is already rewarded for cleaning form. That is a **suggested repair target**, not a neutral dictionary row.

**Falsifier that would have fully killed the whole facts program:** any field that names a band, an error_pattern id, or “recast this” — those are mode-router DNA. The proposal correctly bans them; keep the ban mechanical (schema allowlist + lint).

#### 4) Risk 2 — token cost vs benefit  
**ACCEPT_WITH_AMENDS**

Proposal understates cost (E6). Benefit is only real if garble-credit rate moves.  
**Amendment:** adopt emission policy + **≤80 token** cap (rules 7–8 above). Pre-register measured p50/p95 task-token delta on persona gate; kill if p95 delta > **100** tokens with no \(\Delta g\) win.

#### 5) Risk 3 — does `bein → bien` over-anchor the recast?  
**ACCEPT_AS_WRITTEN** as a **material risk**; **AMEND mitigation**

Independent literature (E2): single biased hints move LLM judgments; “ignore the anchor” prompts do not reliably clear it; multi-candidate / multi-angle context is the documented direction.[[1]](https://arxiv.org/html/2412.06593v1)

**Exact mitigation text to add under Predicted effect + validation:**

```markdown
Anchoring gate (pre-registered, same A/B):
- Arm A: no learner_text_facts
- Arm B: facts with cands[] (0–3), no singleton nearest
- Arm C (ablation, N small ok): facts with forced nearest only
Primary: garble-credit rate on sam.
Secondary (must not regress): recast_target_match_rate =
  fraction of turns where the model's recast lemma equals cands[0]
  when the learner intent was a *different* legal reading
  (hand-labeled slice, freeze rubric before run).
Kill Arm C if it wins garble-credit only by inflating recast_target_match vs Arm B.
Prefer Arm B; Arm C is the steelman that nearest is "just facts" — expected FAIL.
```

#### 6) Risk 4 — facts on GRADING tool response path vs task only  
**ACCEPT_AS_WRITTEN** on **task-only for the teaching/grading decision turn**  
**REJECT_CLAIM** on “also inject into grading-tool response as first ship”

Grades are decided **with** the spoken reply (same model response, tool call). Facts after the tool returns are **post-decision** and cannot fix this turn’s inflation; they only decorate logs or the next turn.  
Optional later: log facts beside the grade for **audit/XP** (record-keeper), not as a second teacher prompt channel — that is eval/telemetry, not pre-grading.

#### 7) Risk 5 — names / “sam” frequency and grade inflation  
**ACCEPT_WITH_AMENDS**

`sam` can be high-frequency in multilingual corpora or pass weak filters; `es:true` must **not** be read as “credit Spanish production.”  
**Amendment (required):** `cls: "name_or_oov"` (or en) on name-like tokens; grading instructions / note must say dictionary membership ≠ communicative success. Pre-register: casey/sofia name turns show **no increase** in sheet credits for name tokens as Spanish items (delta ≤ 0 within noise).

#### 8) Predicted effect + kill-if-no-move validation  
**ACCEPT_WITH_AMENDS** (direction good; metrics underspecified)

Replace the soft paragraph with:

```markdown
### Pre-registered A/B (frozen before any run)
Population: persona-gate sam / casey / sofia, same seeds as 2026-08-05 forensics baseline.
Primary (sam): garble_credit_rate g = (# grade rows whose evidence quote
  contains a token with es:false OR zipf < T_zipf) / (# grade rows).
Success: g_facts ≤ g_control − 0.15 absolute, OR if g_control < 0.20 then
  relative reduction ≥ 30%, else FAIL (decoration → delete the block, §4.6).
Secondary: casey & sofia grade band histograms unchanged
  (chi-square or max absolute band-mass delta ≤ 0.05 — pick one, freeze).
Guardrails: no regression on english_wall / teach-shape evals (existing WARN/HARD).
If primary fails: delete learner_text_facts code paths; no “keep for later.”
```

#### 9) Why-reopen claims (lite cannot spell-audit; ground-truth DBs now exist)  
**ACCEPT_WITH_AMENDS** on motive; **REJECT_CLAIM** that this alone ratifies ship without gate

DB existence (wordfreq + Jehle) is **necessary, not sufficient**. Lite-model failure is asserted from forensics not re-verified here (E7). Ship condition remains §4.3: behavioral gate passes frozen criteria.

---

### Kill-search clause

**Claim tried hardest to kill:** *“`nearest` / single-best dictionary neighbor is still a mechanical fact and does not script teaching.”*

**Result:** **KILLED** (REJECT_CLAIM). A privileged singleton repair string next to an imperfect production is a **recast prime**, not a neutral inventory row. Independent anchoring work shows LLMs overweight early/salient hints and do not shed them via simple “you decide” notes.[[1]](https://arxiv.org/html/2412.06593v1)

**Falsifier that would have killed the entire pre-grading program:** if the only workable fix required fields like `error_pattern`, `band_hint`, or `should_recast` — that would be hard_observations reborn and **REJECT_WHOLE** under §1.1. The proposal avoids that; the program survives **only** with `cands[]`, ambiguous verb `matches[]`, emission caps, and a kill-on-no-Δg gate.

**CORRELATED_AGREE note:** agreement with Claude that *some* code-side surface facts can sit under §1.1 is **one correlated vote** until the A/B moves \(g\) and Arm C (forced nearest) is shown worse on recast priming. Do not treat dual-AI warm feelings as promotion.

---

### Overall status (FINAL)

**ACCEPT_WITH_AMENDS** — ship the *experiment*, not the proposal as written.

| # | Item | Ruling |
|---|---|---|
| 1 | Constitutional reopen under §1.1 | ACCEPT_WITH_AMENDS (law paragraph + no hard_observations DNA) |
| 2 | Facts/opinions line | ACCEPT_WITH_AMENDS (real line only after `nearest` dies) |
| 3 | Schema as proposed (`nearest`, forced person) | REJECT_CLAIM on `nearest` + singleton person; replace with `cands` / `matches` |
| 4 | Risk1 slippery slope | REJECT_CLAIM that nearest is safe; ACCEPT narrowed program |
| 5 | Risk2 token cost | ACCEPT_WITH_AMENDS (≤80 tok, sparse emit) |
| 6 | Risk3 anchoring | ACCEPT risk; AMEND multi-cand + Arm C ablation |
| 7 | Risk4 grading-tool path | ACCEPT task-only; REJECT first-ship tool-response inject |
| 8 | Risk5 names | ACCEPT_WITH_AMENDS (`cls`, no name-as-Spanish-credit) |
| 9 | A/B kill bar | ACCEPT_WITH_AMENDS (numeric freeze above) |
| 10 | Ship without gate | REJECT_CLAIM |

**Promotion blockers (all required):**  
1. Apply schema/rules amendments verbatim.  
2. Freeze \(T_{zipf}\), \(\Delta g\) bar, token cap, Arm C ablation **before** runs.  
3. Promote the constitutional fact-surface paragraph into ENGINEERING.md (§7.2).  
4. Pass gate or **delete** the block (§4.6 — no decoration).

**Not closed for production** until blockers 1–4 clear. Countersign is for the **design direction under amendments**, not for the literal round-1 JSON.

---

## Adjudication (Claude, 2026-08-05 — round 1 closes)

All rulings ACCEPTED, including the kill:

- **`nearest` is dead.** Grok killed "a single nearest-real-word is
  still a fact" with anchoring literature (single salient hints move
  LLM judgments; "you decide" notes don't clear them). A privileged
  singleton repair string IS a recast prime. Replacement: `cands[]`
  (0–3, only on es:false, no forced winner) and multi-parse verb
  `matches[]` (accentless "esta" lists both readings).
- **Names**: `cls: "name_or_oov"` required; dictionary membership ≠
  Spanish-production credit, stated in the block's note.
- **Sparse emission + ≤80-token cap**: only es:false tokens, verb-form
  hits, and name/OOV classes ship; no positive-lexicon spam.
- **Task-only**: facts ride the round-turn task, never the grading-tool
  response path (post-decision decoration).
- **Promotion blockers stand as written**: amended schema verbatim;
  frozen numbers (T_zipf = 3.1 per Grok's calibration-consistency
  amendment; Δg ≥ 0.15 absolute or ≥30% relative on sam's
  garble-credit rate; ≤80-token cap); the constitutional fact-surface
  paragraph promoted into ENGINEERING.md BEFORE ship; pass the
  pre-registered A/B (arms A/B + the Arm C nearest-ablation steelman)
  or DELETE the code paths — no decoration (§4.6).

**Status: design converged and conditionally approved. NOT implemented
— implementation starts only against the blockers above.**

---

## A/B outcome (2026-08-05 — the experiment closes)

Ran same-day, three arms, gemini-3.5-flash-lite, 10-turn persona runs:

| Arm | sam garble-credit g | bar (≤0.321) |
|---|---|---|
| A control (off) | 0.471 (16/34) | — |
| B cands (candidate) | 0.483 (14/29) | **FAIL — no movement** |
| C nearest (forbidden ablation) | 0.250 (7/28) | −47% relative |

Secondary regressed under B too: sofia lost all grammar grading
(grammar XP 60→0); casey's grade rows narrowed 35→28. Token cost
delta was negligible (avg input 17.2k→16.0k — noise).

**Per pre-registration: Arm B failed → learner_text_facts code paths
DELETED (tutor/text_facts.py, config.TEXT_FACTS, pipeline/executor
wiring, tests). No decoration kept.** conjugations.py + wordfreq stay:
they serve the XP evidence audit and the garble_credit metric, both of
which measurably work.

**The honest surprise, recorded:** the constitutionally-forbidden
singleton anchor was the ONLY intervention that moved the model —
Grok's anchoring literature cut both ways: "you judge" disclaimers
don't stop anchors, and neutral multi-candidate facts don't create
salience. A future round wanting this win must solve
salience-without-priming (e.g., facts phrased as questions? tool-forced
verification?) — that design does not exist yet and is NOT this one.
