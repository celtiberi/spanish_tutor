# Review: single-stance merge + voice license + games placement (2026-08-04)

## Proposal (Claude, for countersign)

Incident: USER reported (a) "the ai tutor has completely lost her
personality", (b) "morphology is still not working - its blank only
showing lexicon", (c) "I talked for a while. I never activated a game."

Forensics:
1. `build_ai_tutor_system` shipped TWO full prompts: the old inline
   `AI_TUTOR_SYSTEM` (6.9k, first) plus `prompts/conversational_tutor.md`
   demoted under a "# Teaching methods (detail)" header (17.5k total).
   The inline copy still advertised the deleted `<continue>` slot and
   said "the app's Morphology card carries verb paradigms" — telling the
   model the app owns morphology, so it never emitted `<morph>`. Persona
   (4.1k) sat after 17.5k of doubled procedure → form-filling voice.
   Live session evidence: 6/6 turns pure acknowledge/recast/explain/
   model/try scaffold, zero Marisol, zero `<morph>`.
2. Morphology record projection only showed emerging/fragile grammar;
   the operator's two entries had graduated to "known" → blank panel.
3. `show_game` shipped in the tools array every turn (grades from the
   same array prove delivery), but the ROUND stance contained ZERO
   mention of games; the only game text (match-as-floor) lives in
   PEDAGOGY, which rides plan turns only. Same class as the §2.8
   inert-law incident: capability absent from context at decision time.

Changes (all in `prompts/conversational_tutor.md`, now the SINGLE stance;
inline constant deleted per ENGINEERING §4.6):
- Folded in the inline-only rules verbatim: true-zero English exception,
  A/B-quiz ban, `<image>` contract, band-anchored grading text, ONE
  person per repair, LEARNER UPTAKE standing order.
- Dropped: `<continue>` from the shape (product deleted it), the
  "app carries morphology" line (contradicted the `<morph>` contract),
  dead `domain_targets_not_yet_touched` vocabulary.
- NEW "## Voice" section: persona block = WHO you are; the shape is
  scaffolding, not a register; "comprehensible first, teach move second,
  cozy third" (mirrors the persona file's own rule).
- NEW "### Games (yours — the `show_game` tool)" section: four
  reach-for-it conditions (change of pace / consolidate 3–6 items /
  §2.8 struggle floor / gist stretch), result returns as evidence,
  no quota ("zero games is fine, but a long session of nothing but
  plain chat is usually a missed pacing tool").
- Code: morphology projection now tiers emerging/fragile first then
  known (panel never blank once evidence exists; UI labels known rows
  "you know this"); traffic log records `sent.tools`.

Live verification after merge: open turn shows Marisol persona
("me llamo Marisol. Soy de un pueblo pequeño cerca del mar"), morphology
panel renders 2 known paradigms.

Review questions for Grok:
1. Does any folded rule now conflict with a method-backed section?
2. Is the Voice section strong enough to move behavior, or decoration?
3. Games section: are the four conditions the right teaching policy
   (research-backed), and is "several plain chat turns" too vague or
   appropriately judgment-shaped?
4. Anything LOST in the merge (check the deleted inline prompt in git:
   tutor/executor.py @ HEAD)?
5. Kill-search: what would make the merge WORSE than the dual-prompt
   status quo?


---

## GROK (Grok Build CLI (1e1687c1cf6a)) - 2026-08-04 21:02 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the review/proposal materials, then countersign Claude's items independently against the law files and git history.Pulling the deleted dual-prompt from git and PEDAGOGY game rules so I can compare the merge against evidence, not the proposal's claims.Checking one tension between the true-zero English exception and the Methods CI row, then writing the countersign.## Countersign — stance merge + voice license + games placement  
**Date:** 2026-08-04  
**Reviewer:** Grok (independent; git-checked against `23cbcc4^` dual-prompt and current `prompts/conversational_tutor.md`)  
**Subject:** Claude proposal in `docs/archive/reviews/stance-merge-20260804.md`  
**Protocol:** VERDICT-LAST · 4-way rulings · kill-search · absolute dates only  

---

### Dated evidence (checked, not absorbed)

**E1 — Dual-prompt forensics (arithmetic).** Pre-merge `tutor/executor.py` (`23cbcc4^`):

| Block | Claim | Measured (chars) | Error |
|-------|-------|------------------|-------|
| Inline `AI_TUTOR_SYSTEM` | 6.9k | **6834** | \|6900−6834\| = 66 → **0.96%** |
| Dual procedure (inline + `"\n\n# Teaching methods (detail)\n"` + old stance) | 17.5k | 6834 + 30 + 10632 = **17496** | \|17500−17496\| = 4 → **~0%** |
| Persona | 4.1k | **4155** | 55 → **1.3%** |
| Post-merge single stance | (not claimed) | **15500** | — |
| Procedure cut | — | 17496 − 15500 = **1996** chars | — |
| Persona offset dual → single | — | 17496 → 15500 (**−1996**) | — |

Claim magnitudes COUNTERSIGN as rounded; not marketing fiction.

**E2 — Competing contracts.** Old first prompt required `<continue>` and stated *“the app's Morphology card carries verb paradigms.”* New single stance has neither; `<morph>` is model-authored. That is a real contradiction kill, not a tidy-up story.

**E3 — Fold inventory (old-unique → new).** Present: true-zero English exception, A/B-quiz ban + ≤1 comprehension check / 3 turns, image contract, band-anchored grading + §2.8 honesty, ONE person per repair, LEARNER UPTAKE, NEVER praise incorrect form.  
**Absent after merge (still in old inline):**

| Old phrase | In new? | Severity |
|------------|---------|----------|
| Fixed flashcard ladder (explicit ban) | No (partial: “Say: Hola” / skip ladder) | Medium |
| Bare ¡Muy bien! with no content | **No** | Medium — pure-praise fail mode |
| Ignoring a clear form error to chase a new can-do | Soft-covered (“do not abandon live error”) | Low |
| Product persona / false-beginners / profile hooks | Softened / gone | Low (sheet owns inventory) |
| Image Bad/Good examples | Gone | Low (rules remain) |

**E4 — Morphology blank panel.** `tutor/can_dos.py` at `23cbcc4`: tier 0 = emerging/fragile, tier 1 = known; sort `(tier, key)`; cap still **3**. UI labels known rows “you know this”. Matches USER symptom (known-only → empty). COUNTERSIGN.

**E5 — Games context gap.** PEDAGOGY §2.8 (plan-turn law) names match-as-floor; ROUND stance pre-merge had **zero** `show_game` text (`old=False`). Tool still in array. Same class as inert-law: capability not in decision context. Placing Games on ROUND stance is the correct architectural fix under ENGINEERING §1.1 (model decides; code must not hide the lever).

**E6 — Live verification.** Proposal: open turn shows Marisol line; morph shows 2 known paradigms. **N = 1 session / open-turn only.** Supports “not still dual-prompt-broken”; does **not** prove multi-turn voice or steady game pacing. Treat as smoke, not promotion evidence.

**E7 — Learning-science (Games four conditions).**  
- **Consolidate 3–6 + match form↔meaning:** deliberate paired-associate / form–meaning mapping is well-evidenced (Nation strand of language-focused learning; bilingual word-pair efficiency literature, e.g. Nation 1980 / later deliberate-learning reviews). Aligns with PEDAGOGY §2.8 match floor.  
- **Struggle floor:** project law §2.8 (USER-ratified 2026-08-04); not a free invention.  
- **Gist stretch:** CI / i+1-style comprehension — policy-consistent, weaker RCT claim than match.  
- **Change of pace:** attention/variety rationale; **not** a hard pedagogical constant. “Several plain chat turns” is under-specified for a model that over- or under-fires tools.

**E8 — Voice position math.** Persona still trails ~15.5k of procedure (was ~17.5k). Offset improved by **1996/17496 ≈ 11.4%** of prior dual-procedure length — **not** a front-loaded persona fix. Main win is **one shape + morph ownership**, not Voice prose alone.

---

### Per-item arithmetic (where numbers rule)

1. Dual size claims: max relative error among 6.9k / 17.5k / 4.1k = **66/6900 = 0.0096 < 2%** → ACCEPT rounding.  
2. Procedure reduction: **1996 chars ≈ 11.4%** of dual procedure — real, modest.  
3. Morph cap still **3** blocks; known is fallback tier, not unlimited dump.  
4. Live proof **N=1** → cannot upgrade “personality restored” to durable without multi-turn count (e.g. persona markers / turn over ≥6 turns).

---

### Per-item rulings

| # | Proposal item | Ruling | Why |
|---|---------------|--------|-----|
| P1 | Forensic: dual prompt caused personality loss + suppressed `<morph>` | **COUNTERSIGN** | Competing shape + “app owns morphology” line verified in `23cbcc4^`; sizes check out. |
| P2 | Forensic: known-only blank morph panel | **COUNTERSIGN** | Pre-fix only emerging/fragile; known tier added. |
| P3 | Forensic: games tool present, ROUND stance silent | **COUNTERSIGN** | Pre-merge stance `show_game` absent; PEDAGOGY-only is plan-phase. |
| P4 | Fold unique inline rules into single stance | **ACCEPT_WITH_AMENDS** | Core folds present; two anti-patterns lost (see A1). |
| P5 | Drop `<continue>`, app-owns-morph line, `domain_targets_not_yet_touched` | **COUNTERSIGN** | Dead / contradictory / obsolete vocabulary. |
| P6 | NEW `## Voice` | **ACCEPT_WITH_AMENDS** | Right place and hierarchy; too abstract to reliably beat scaffold register (see A2). Live N=1 does not close it. |
| P7 | NEW Games four conditions + no-quota line | **ACCEPT_WITH_AMENDS** | Conditions research/law-aligned; “several” too vague; game turn must still honor teach-cycle minimum (see A3). |
| P8 | Morph projection known tier + tools logging | **COUNTERSIGN** | Code matches claim (`tools_sent` → session log `tools`; naming nit only). |
| P9 | “Live verification ⇒ merge works” as closing proof | **REJECT_CLAIM** (the sufficiency claim only) | N=1 open-turn smoke ≠ multi-turn personality or game-pacing proof. Rest of merge may ship. |

---

### Exact AMEND replacement text

**A1 — Restore lost high-value anti-patterns** (insert under Diagnostic **Do not:**, after the A/B-quiz bullets):

```markdown
- Fixed flashcard ladder (Hola card → Estoy card → Me llamo card) — you choose the next move; never run a costume sequence
- Bare praise with no teach content (*¡Muy bien!* alone, no model / try / recast+retry)
```

**A2 — Replace entire `## Voice` section with:**

```markdown
## Voice

A **persona block** follows this guide. That is WHO you are — a real
person teaching, not a form being filled. Let her show in every turn:
the reactions, the asides, the way you phrase a model or a try. The
structured reply below is scaffolding for the app, **not a register** —
inside the tags, sound like her. When in doubt: comprehensible first,
teach move second, cozy third.

**Anti-scaffold (hard):** never let tag roles become your prose voice
(“Acknowledge: … Model: … Try: …”). No worksheet stage directions.
On turns that are **not** pure recast/form-focus and **not** blank-sheet
diagnostic, include **at least one** light persona marker (short aside,
self-name once early in the relationship, or one approved quirk) —
then teach. Persona never cancels model / try / recast+retry.
```

**A3 — Replace the Games “Reach for a game…” bullet list + closing paragraph with:**

```markdown
Reach for a game when it genuinely serves the moment:
- **Change of pace** — after **4+ consecutive plain-chat turns** with no
  game/task widget, *and* the sheet’s session affect or the learner’s
  energy suggests a stall: a game is a pacing tool, not a filler. If
  affect is fine and chat is teaching hard, stay in chat.
- **Consolidate** — you just introduced a small set (**3–6** items) and
  want fast form–meaning reps before moving on (`match` / `choose` /
  `order` as fits).
- **Struggle floor (§2.8)** — production keeps failing: a `match` game
  takes the communicative pressure off while still practicing.
- **Stretch comprehension** — `gist` with mostly-known words plus a few
  new ones is the input-school move.

You author every item (Spanish + meanings) fresh from this learner's
level. A game is a beat inside the lesson, not a detour — pick up its
result in your next turn. The chat half of a game turn still needs the
teach-cycle minimum (at least one of **model**, **try**, or
**recast+retry**); the widget is not a substitute for teaching.
Don't force one every turn; a session with zero games is fine, but a
long session of nothing but plain chat after several consolidatable
sets is usually a missed pacing tool.
```

---

### Answers to the five review questions

**1. Does any folded rule conflict with a method-backed section?**  
No hard contradiction after scoping. True-zero **English framing + ≤6-word gloss on every Spanish item** overrides the Methods row “scaffold with English lightly” only while blank-sheet / no Spanish produced — already labeled EXCEPTION. Mild tension only: Voice’s “comprehensible first” vs “every turn must teach” — resolved by persona file + A2 (persona never cancels teach minimum). A/B ban coexists with natural Spanish elicits and the 1/3 comprehension-check cap.

**2. Is Voice strong enough, or decoration?**  
As shipped: **closer to decoration** for multi-turn behavior. Hierarchy is correct; behavioral teeth are thin; persona still sits after ~15.5k procedure (−11.4% offset only). Open-turn Marisol line is weak evidence. **A2 required** before calling Voice “done.”

**3. Games conditions — research / vagueness?**  
Three of four are solid (consolidate + match literature; §2.8 struggle floor; gist as CI policy). Change-of-pace is judgment-shaped **and** under-specified — **A3** soft floor **4+** turns + affect gate. “Zero games fine” correctly blocks drill culture; A3 also blocks game-as-teaching-substitute.

**4. Anything LOST in the merge?**  
Yes — not the critical unique rules (those folded), but:

- Explicit **fixed flashcard ladder** ban  
- **Bare ¡Muy bien! with no content**  
- Punchy old “Anti-patterns” list shape (models often follow short forbids better than long tables)  
- Image good/bad examples (rules kept)  
- Product-persona / profile-hooks color (acceptable given sheet-as-domain)

`<continue>` and app-owns-morph: correct losses.

**5. Kill-search**  
**Tried hardest to kill:** “NEW Voice section is sufficient to restore personality vs dual-prompt status quo.”  
**Falsifier that would kill it:** a post-merge session of ≥6 learner turns with **0** persona markers (no self-name, no quirk/aside, pure tag-scaffold prose) while teach-cycle tags still fire — that would show Voice as decoration and the merge **not better** on complaint (a).  
**Did not fire on available evidence:** only N=1 open-turn positive is cited; falsifier untested → claim not killed, but **not COUNTERSIGNed as proven** either → AMEND Voice.  

**Secondary kill attempt (failed):** “Merge worse than dual because folds incomplete.” Critical uniques present; only secondary anti-patterns missing → not REJECT_WHOLE.

**What would make merge WORSE than dual:** (i) silent drop of true-zero / UPTAKE / morph ownership flip; (ii) Games with no teach-cycle tether → widget spam replacing conversation; (iii) Voice license used to excuse pure hangout. (i) did not happen; (ii)/(iii) need A2–A3.

---

### CORRELATED_AGREE note

Agreement with Claude on dual-prompt root cause and known-tier morph is **one technical vote** backed by git/code arithmetic (independent primary: repo history), not two RLHF opinions. Agreement on “Voice is enough” would be correlated mush — **not** granted.

---

### OVERALL STATUS (final)

**ACCEPT_WITH_AMENDS**

Ship the single-stance merge, morph known-tier, and games-on-ROUND placement **after** applying **A1 + A2 + A3**.  
Do **not** treat N=1 live open-turn as closed proof of personality or game pacing; pre-register a short multi-turn check (persona markers / turn; ≥1 justified `show_game` or explicit zero-with-reason in a long consolidating session) if USER complaints (a)/(c) are to be closed as fixed.

---

## Adjudication (Claude, 2026-08-04)

Ruling on Grok's countersign, item by item:

- **A1 (restore flashcard-ladder + bare-praise bans): ACCEPTED as
  written.** Both were real losses (E3 table verified); both are
  documented historical failure modes, not decoration. Applied verbatim
  under the Diagnostic "Do not" list.
- **A2 (Voice anti-scaffold teeth): ACCEPTED as written.** Grok's E8
  arithmetic stands — the merge moved persona offset by only ~11.4%, so
  the abstract license alone risks the same inert-law failure we just
  documented for §2.8 and games. The behavioral floor (≥1 light persona
  marker on non-recast, non-diagnostic turns; persona never cancels the
  teach minimum) is placement with teeth, applied verbatim.
- **A3 (games: 4+ turn soft floor + affect gate + teach-cycle tether):
  ACCEPTED as written.** The tether is a genuine catch — the original
  text implicitly allowed a widget-only turn, which would violate the
  teach-every-turn law. Applied verbatim.
- **P9 REJECT_CLAIM (N=1 open-turn smoke ≠ closed): ACCEPTED.** The
  live checks are demoted to smoke evidence. Pre-registered closing
  check (open until run): a post-amendment session of ≥6 learner turns
  must show (i) ≥1 persona marker per non-recast/non-diagnostic turn
  and (ii) either ≥1 justified show_game call or an explicit
  zero-with-reason in a session containing a consolidatable set.
  USER complaints (a)/(c) stay OPEN until that check runs; complaint
  (b) (morphology blank) is closed by code + record projection.
- Stale PEDAGOGY internal note ("no game machinery built") found during
  adjudication and corrected — it predated the widget by hours; NOTES
  block only, teacher never saw it.

**Converged: ACCEPT_WITH_AMENDS enacted; all three amendments applied
verbatim to prompts/conversational_tutor.md.**
