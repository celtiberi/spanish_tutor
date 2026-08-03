

---

## GROK (Grok Build CLI (1e1687c1cf6a)) - 2026-08-03 16:24 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

The round payload looks incomplete after “THIS ROUND”. I’ll inspect the workspace for inlined subject files and the collab skill so I can review against the actual materials, not the briefing alone.The workspace is empty and “THIS ROUND” has no subject files. I’ll treat only the auto-context and GROK.md as data, verify their load-bearing claims, and produce an append-ready research-round response that states the gap.# GROK research-round (independent) — 2026-08-03

**Status: ROUND INCOMPLETE — NO SUBJECT.**  
Workspace for this call was empty. `===== THIS ROUND =====` contained no research question, no author proposal, and no `--files` payloads beyond auto-orientation + `GROK.md`. Isolation protocol forbids reading the live tree at `/Users/patrickcremin/repo/ml_teacher`. Everything below treats only inlined orientation + briefing as **data**.

---

## 1) Own picture (dated pins)

| Pin date | Claim / state (from inlined data only) | Confidence |
|---|---|---|
| **2026-07-28** | Personal-data capture removed by construction; ability sheet only; `tutor/learner_profile.py` = disconnected reference. | Unverified (code not inlined) |
| **2026-07-28** | PEDAGOGY theory P1–P9 + HARD/BINDING laws enacted. | Unverified (PEDAGOGY.md not inlined) |
| **2026-08-03** | Constitution split: `PEDAGOGY.md` = how to teach; `ENGINEERING.md` = everything else. Matches commit message `0d2a835`. | Orientation-consistent; law text not inspectable |
| **post-split (tip `d51c05f`)** | “The character sheet IS the course pack: prose pack deleted, sheet carries the curriculum.” | Architectural claim — high impact, **zero evidence in this round** |
| **tip stack (orientation)** | Two-phase teaching context (teacher writes own session plan); health reports `teacher_context`; model traffic log for every tutor call. | Ops claims — not auditable without code/docs |

**Independent picture of the product (from briefing, not endorsement):**  
ml_teacher is aiming at pedagogy-first tutoring where Spanish A1 subject matter rides on a living character sheet (can-dos, scaffold/ledger, next_best, retrieval schedule) plus a code-owned pedagogy engine (phases, introduce router, association table, task runtime, output gates). Law is dual-homed after 2026-08-03. Standing reviewer roles are law attack, blind transcript grading, pack fact-check, and plan countersigns.

**What this round can and cannot do:**  
Without PEDAGOGY.md, ENGINEERING.md, character-sheet schema, association tables, or a concrete proposal, a “NEW research round” cannot produce load-bearing countersigns or curriculum fact-checks. Doing so from commit titles alone would be fabrication.

---

## 2) Verify / refute table (every load-bearing claim *in the inlined text*)

| # | Claim (inlined) | Ruling | Evidence / method |
|---|---|---|---|
| C1 | Sole law home: PEDAGOGY.md (teaching) + ENGINEERING.md (other), split **2026-08-03** | **ORIENTATION-SUPPORTED, NOT CONTENT-VERIFIED** | Auto-context lists both files; commit `0d2a835` message matches. Law paragraphs themselves not supplied → cannot audit consistency or “sole home” vs leftover docs. |
| C2 | Theory P1–P9 + HARD/BINDING laws enacted **2026-07-28** | **UNVERIFIED** | No PEDAGOGY excerpt. Numbering, binding force, and enactment date cannot be confirmed. |
| C3 | `prompts/teaching_policy.md` is legacy; must not supersede PEDAGOGY.md | **POLICY ASSERTION — UNTESTED** | No either file. Cannot check for contradictory “must” language still live in the harness. |
| C4 | Personal-data capture removed by construction (**2026-07-28**); ability sheet only | **UNVERIFIED** | Code/profile path not inlined. “By construction” is a strong safety claim — needs schema + API surface + storage audit, not a briefing sentence. |
| C5 | Character sheet holds Spanish ability only: can-dos, scaffold/ledger, next_best, retrieval schedule | **DESIGN-PLAUSIBLE, SCHEMA-UNVERIFIED** | CEFR can-do framing is standard practice in language education; “character sheet” as ability ledger is a project metaphor, not a field standard. No JSON/schema inlined. |
| C6 | Tip commit: prose course pack deleted; sheet *is* the curriculum | **HIGH-RISK UNVERIFIED** | Commit message only. Load-bearing product claim: if true, pack verification workflows, association tables under `curriculum/spanish_a1/`, and any “pluggable course packs” language in README must be reconciled. Auto-context still lists `curriculum/spanish_a1/scenes/*.json` and `association_table.json` — **tension with “prose pack deleted / sheet IS the pack”** that this round cannot resolve without those files. |
| C7 | Teacher context: no silent truncation while testing; gate `scripts/check_teacher_truncation.py` via pre-commit | **PROCESS CLAIM — UNVERIFIED** | Auto-context lists `.githooks/pre-commit`; script body not inlined. Cannot confirm the gate actually fails on truncation. |
| C8 | Standing law-review method: cite retrieval practice, spacing, error-correction timing with sources | **SOUND AS METHOD** | Not a project fact; as reviewer mandate it is appropriate. Classic literature (e.g. Roediger & Karpicke retrieval practice; Cepeda et al. spacing meta-analyses; Lyster/Ranta oral corrective feedback timing debates) is real; specific thresholds in PEDAGOGY.md still need file-level attack when inlined. |
| C9 | Product map: `docs/system-overview.md` | **PATH CLAIM ONLY** | Listed in README head; body not inlined. |
| C10 | Recent stack: model traffic log; health reports `teacher_context`; two-phase teaching context; constitution split | **COMMIT-MESSAGE CONSISTENT** | Five tip messages form a coherent narrative (observability → context mode proof → teacher-written plan → law split → sheet-as-pack). Coherence ≠ correctness. |

**Arithmetic note:** 10 load-bearing claims extracted from inlined orientation/briefing.  
Verified content-level: **0 / 10**.  
Orientation/path-consistent: **4 / 10** (C1 partial, C9 partial, C10 partial, C8 method).  
Unverified / high-risk: **6 / 10**.  
Contradiction flag open: **1** (C6 vs listed `curriculum/spanish_a1/**` assets).

---

## 3) What the other author MISSED

1. **Empty research payload.** Invoking `research-round` with no question, no proposal, and no subject files wastes the isolation channel. Auto-context is orientation, not evidence.
2. **Sheet-as-pack vs tree listing.** Commit `d51c05f` (“prose pack deleted, sheet carries curriculum”) coexists in orientation with `curriculum/spanish_a1/scenes/`, `association_table.json`, `asset_sidecar.json`. Either “pack” now means non-prose structured assets, or the tip claim overstates deletion. That disambiguation is the first thing a serious round should settle — it was not posed.
3. **Split-day consistency risk (2026-08-03).** Same calendar day as this call’s user_info date. ENGINEERING.md / PEDAGOGY.md / GROK.md / README dual-homing is a classic stale-pointer hazard; dual-skim or doc-sync was not requested.
4. **“By construction” privacy** is treated as settled in the briefing. An independent reviewer would demand: no PII fields on sheet, no client payloads, no log redaction gaps (traffic log commit `7e640a6` makes this *more* urgent: full request/response on disk can reintroduce personal data even if the sheet is clean).
5. **No standing questions** were registered for this round, so nothing to answer in §4.

---

## 4) Answers to standing questions

**None were asked.** No item list, no countersign slate, no blind rubric+transcript.

---

## 5) Ranking / critique (of the invocation, since no author thesis was supplied)

| Aspect | Score (1–5) | Note |
|---|---|---|
| Isolation hygiene | 5 | Empty cwd; no leakage from live repo in this agent view. |
| Round readiness | 1 | No subject. |
| Briefing usefulness (GROK.md) | 4 | Clear roles, law pointers, conventions — good *when* paired with files. |
| Evidence density for research | 1 | Commit titles ≠ research corpus. |

**Do not treat any of the above as COUNTERSIGN of product design.** There was no design to countersign.

---

## Required re-invoke (minimal viable research-round)

Re-run with **at least**:

1. Explicit question or author thesis under `THIS ROUND`.  
2. `--files` including: `PEDAGOGY.md`, `ENGINEERING.md`, character-sheet schema/source of truth, and (if pack claims matter) `curriculum/spanish_a1/association_table.json` + one scene.  
3. If the thesis is tip `d51c05f`: the before/after pack representation and what “prose pack deleted” means operationally.

Until then: **NO COUNTERSIGN · NO REFUTE OF PRODUCT LAW · NO PACK FACT-CHECK · ROUND VOID ON SUBSTANCE.**


---

## GROK (Grok Build CLI (1e1687c1cf6a)) - 2026-08-03 16:28 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

Verifying a few more precise citations, then writing the append-ready countersign.## COUNTERSIGN ROUND — character-sheet terminology (2026-08-03)

**Role:** independent second author. Proposal under attack is Author A’s post-research position in `vocab-round-brief.md`. Code evidence from inlined `tutor/character_sheet.py` (`CURRICULUM_SCOPE`, `curriculum_scope`, `curriculum_targets_not_yet_touched`, `_untouched_targets`).

**Verdict shape:** literature mostly backs “sheet ≠ curriculum (as sequence).” Renames need AMENDs; one ban clause is wrong; curricular *selection* still lives on the sheet.

---

### 1. Literature verify / refute

| Claim (Author A) | Ruling | Evidence |
|---|---|---|
| CEFR is descriptive, **not** a curriculum | **VERIFY** | CEFR Companion Volume (Council of Europe, 2020) restates CEFR 2001 Notes to the User: *“We have NOT set out to tell practitioners what to do, or how to do it… It is not the function of the Common European Framework to lay down the objectives that users should pursue or the methods they should employ.”* Companion also: CEFR is *“a tool to facilitate educational reform projects, not a standardisation tool”*; descriptors aim to *“provide input for curriculum development”* and are *“illustrative, not… mandatory.”* |
| ACTFL / NCSSFL–ACTFL Can-Do are **not** a curriculum | **VERIFY** | ACTFL educator page (2026 Can-Do set): *“The sets of examples are not a prescribed curriculum”*; *“Can-Do Statements do not show what to learn or teach at each sublevel”*; they are goal/progress tools, not ready-made lessons. |
| Classical ITS split: domain / student / tutor (pedagogical) models | **VERIFY** | Standard ITS architecture: domain (what can be known/taught), student/learner model (beliefs about the learner), tutoring/pedagogical model (how to teach / plan intervention). Survey lineage: Nwana 1990; restated in modern GIFT / ITS design literature (e.g. Sottilare et al.). Author A’s three-way split is correct. |
| Open learner models (Bull & Kay SMILI) “facilitate planning” | **AMEND the attribution** | Bull & Kay, *Student Models that Invite the Learner In: The SMILI☺ Open Learner Modelling Framework* (IJAIED, 2007): OLM is the *externalized student model* for inspection, reflection, negotiation, metacognition. Planning support is a documented *use* of OLMs, not their definition. **Session planning in ITS is primarily the tutor/pedagogical model reading domain + student models.** Do not brand the whole sheet as “an OLM” alone. |
| Sheet = domain model **+** open learner model | **VERIFY as composite; AMEND as pure label** | In code: inventory + scope (`CURRICULUM_SCOPE`, association-table untouched targets, can-do/grammar/lex keys) = **domain slice**; status/confidence/evidence/schedule/next_best = **learner model**. One JSON document holds both axes. Correct ITS label: *domain model co-located with (open) learner model*, not “only OLM” and not “only proficiency framework.” |
| “Proficiency framework instantiated per learner” | **PARTIAL** | Can-dos / level band are framework-aligned. The closed A1 vocab, deferred lists, and `out_of_scope_decline_briefly` are **local product scope**, not CEFR/ACTFL text. CEFR does not ship “no past tense” as a hard A1 law; this project does. |
| Teacher practice: standards-based gradebook / progress record | **VERIFY for the state half only** | Status/confidence/evidence/next_best ≈ gradebook/progress record. Inventory + deferral lists are **standards / domain scope**, not grades. |

**Net on Author A’s concession to B:** Directionally right for **curriculum-as-path/sequence**. Wrong if read as “nothing curricular remains.”

---

### 2. Where level boundaries live

**Ruling: domain / proficiency-scope layer, not curriculum-as-sequence, not learner state.**

| Layer | What lives there | This project’s payload |
|---|---|---|
| Proficiency framework (CEFR/ACTFL) | Descriptive bands of ability | Reference only (“CEFR A1 grammar-core slice”) |
| Domain model (level slice) | What exists / is deferred / recognition-only **for this product** | `CURRICULUM_SCOPE` lists; association-table inventory; can-do/grammar catalogs |
| Learner model | Measured state on those items | status, confidence, evidence, schedule, coverage touched |
| Tutor model / session plan | Path, sequence, activities | Generated at session open; not stored on sheet (per brief) |
| Curriculum (classical content+sequence) | Selection **and** organization over time | Selection still on sheet; sequence deliberately discarded with prose pack |

**Arithmetic (axes on the composite sheet):**

- Domain-axis fields in prompt payload: `curriculum_scope` + `curriculum_targets_not_yet_touched` + catalog structure of skills/grammar/lex keys = **3 structural domain carriers**
- Learner-axis fields: skills/grammar/lex/error state + coverage + receptive + next_best + affect ≈ **6+ state carriers**
- Sequence/curriculum-path fields on sheet: **0** (by design after 2026-08-03 pack delete)

So: level boundaries **belong on the sheet document** (so the teacher model can plan without a second artifact) but they are **domain scope**, not “the learner’s level” and not “the curriculum.”

**AMEND Author A’s sentence:**

> Level boundaries belong ON the sheet (CEFR levels ARE the boundary of what exists at a level) — only the name was wrong.

**Exact replacement:**

> Level-slice **scope** (what this product treats as in-scope, deferred, recognition-only, or hard out-of-scope at A1) belongs on the sheet as **domain-model constraints**, co-located with learner state so the session-planning model can read one artifact. CEFR/ACTFL supply descriptive bands; they do **not** equal this project’s authored deferral lists. Naming was wrong (`curriculum_*`); placement was right.

---

### 3. Per-rename rulings

#### 3a. `curriculum_targets_not_yet_touched` → `abilities_not_yet_touched`

**REJECT** target name. **AMEND.**

**Reason (code, not taste):** `_untouched_targets(lex)` walks the **association table** and emits theme → `"key — gloss"` for keys **not yet in `lexicon`**. That is **domain inventory not yet on the learner model**, not can-dos/skills (“abilities”) in the ACTFL sense. Calling it `abilities_*` collides with `skills` and overclaims.

**Exact replacement:**

```text
curriculum_targets_not_yet_touched  →  domain_targets_not_yet_touched
```

Acceptable aliases if you want shorter keys: `targets_not_yet_touched` or `inventory_not_yet_touched`. Do **not** use `abilities_not_yet_touched`.

Docstring in `_untouched_targets` still says *“the curriculum's closed vocabulary”* — that comment must move with the key.

---

#### 3b. `curriculum_scope` → `level_boundaries`

**AMEND.**

**Reason:** Payload is not only “boundaries.” Keys are `level`, `deferred_do_not_introduce`, `out_of_scope_decline_briefly`, `recognition_only` — **authored domain-slice policy**. “Boundaries” under-describes recognition-only and deferred-intro buckets; “level_boundaries” also over-identifies the list with CEFR itself (see §2).

**Exact replacement:**

```text
curriculum_scope  →  domain_scope
```

Constant rename: `CURRICULUM_SCOPE` → `DOMAIN_SCOPE`.

If you insist on “level” in the name: `level_scope` is second-best. Prefer `domain_scope` for ITS alignment with the directory rename.

---

#### 3c. Directory `curriculum/` → `domain/`

**COUNTERSIGN with a scoped caveat (not a full blank check).**

**Reason:** Inventory side (`association_table.json`, form/can-do sources, deprecations) is domain content. **But** inlined tree also has `curriculum/spanish_a1/scenes/*` (boat scenes etc.) — situation/encounter **assets** for tutoring, closer to content/materials than pure “domain model.”

**Exact policy text to adopt:**

> Rename data root `curriculum/` → `domain/` for level-slice inventories (association table, catalogs, migration tables). Scene/encounter JSON may live under `domain/<slice>/scenes/` as **domain-situated materials**, but do not treat scene scripts as learner-model state or as a resurrected lesson sequence. If scenes later encode multi-step lesson paths, split them to `content/` or `encounters/` rather than smuggling curriculum-as-sequence back under `domain/`.

---

#### 3d. Ban words: “curriculum / syllabus / course” for the sheet; reserve “plan / course” for the model’s session plan

**AMEND (two fixes).**

| Phrase | Ruling |
|---|---|
| Ban **curriculum** as name for the sheet / its payload keys | **COUNTERSIGN** |
| Ban **syllabus** for the sheet | **AMEND** — ban as *primary product name*; allow in research prose only when meaning “inventory of forms/targets” (language-teaching jargon), never as the sheet’s official label |
| Ban **course** for the sheet | **COUNTERSIGN** |
| Reserve **plan** for the model’s session plan | **COUNTERSIGN** |
| Reserve **course** for the model’s session plan | **REJECT** |

**Arithmetic on “course”:**  
Session plan duration ≈ 1 session.  
A course (product sense) ≈ many sessions (n ≥ 2, usually n ≫ 1).  
1 ≠ n for n ≥ 2 → **session plan is not a course.**

**Exact replacement for the ban clause:**

> Do not call the character sheet a curriculum, syllabus, or course. Call it the **character sheet** (composite **domain scope + learner model**). Reserve **session plan** (or **plan**) for the teacher model’s private per-session plan. Do **not** call that plan a “course.” “Course” / “course pack,” if used at all, means the product slice (e.g. Spanish A1 domain materials), never the sheet and never one session plan.

Also flag conflict with commit `d51c05f` message *“The character sheet IS the course pack”*: keep the engineering fact (inventory absorbed into sheet) but **retire that slogan** under the new vocabulary.

---

### 4. Risks of the vocabulary shift (over-read hazards)

1. **Curricular selection still rides on the sheet.** Discarded: unit order, 5-step sequences, reveal rules (organization/path). **Still present:** closed association-table vocab, can-do set, grammar inventory, `deferred_*` / `out_of_scope_*` / `recognition_only`, `DEFAULT_COVERAGE.never_touched`. Those are **content-selection decisions**. Saying “the sheet is not a curriculum” must mean *not a sequenced course design*, not *has no curricular content*.

2. **Domain + learner co-location can be misread as pure OLM.** Planners need both axes. If docs only say “learner model,” domain scope becomes invisible law and out-of-scope drift returns.

3. **`abilities_not_yet_touched` would hide that the list is lexicon-table residue**, not full ability coverage (skills/grammar can lag lexicon independently).

4. **Scenes under `domain/`** can re-import “mini-curricula” if anyone treats boat scene order as unit order. Keep scenes as optional encounter fuel, not path law.

5. **CEFR-washing risk:** labeling product deferrals `level_boundaries` invites “CEFR says so” claims for local choices (e.g. hard ban on past tense, closed food set). Keep product scope named as **domain_scope**.

6. **Standards-based gradebook analogy** underplays the domain half; tutors need inventory of *not-yet-touched targets*, which gradebooks usually do not list exhaustively by theme.

7. **Doc/code lag:** comments still say *“the character sheet IS the course pack”* and *“plan the course from the sheet alone”* (`format_sheet_for_prompt`, `CURRICULUM_SCOPE` header). Vocabulary law without a doc sweep will fork speech in one week.

---

### Global verdict on Author A’s position

| Element | Verdict |
|---|---|
| Concede: sheet is not a curriculum-as-sequence | **COUNTERSIGN** |
| Frame: domain model + learner model (composite) | **COUNTERSIGN** (prefer this over “OLM only” or “CEFR instance only”) |
| Level scope on sheet | **COUNTERSIGN placement; AMEND justification** (§2) |
| Rename targets → `abilities_not_yet_touched` | **REJECT → `domain_targets_not_yet_touched`** |
| Rename scope → `level_boundaries` | **AMEND → `domain_scope`** |
| Dir `curriculum/` → `domain/` | **COUNTERSIGN** (scenes caveat) |
| Word bans + “course” = session plan | **AMEND** (ban curriculum for sheet; do not call session plan a course) |

**Bottom line for finalization:** Adopt the composite ITS framing; kill `curriculum_*` keys; do **not** replace them with `abilities_*` / `level_boundaries`; use `domain_scope` + `domain_targets_not_yet_touched`; reserve **session plan** for the model’s plan; document that **selection remains, sequence does not**.

---

## CLAUDE — adjudication of the countersign round (2026-08-03)

Context for the record: round 1 (16:24 UTC above) was VOID — the prompt
did not survive invocation plumbing; Grok correctly refused to fabricate.
Round 2 (16:28 UTC) received the full brief + `character_sheet.py`.

| Grok ruling | Adjudication |
|---|---|
| `abilities_not_yet_touched` REJECT → `domain_targets_not_yet_touched` | **ACCEPT.** The section is association-table lexicon residue, not ability coverage; "abilities" would collide with `skills` and overclaim. Shipped as `domain_targets_not_yet_touched`. |
| `level_boundaries` AMEND → `domain_scope` | **ACCEPT.** The CEFR-washing catch is real: our deferral lists are authored product scope, not CEFR text; naming them "level_*" would launder local choices as framework law. Shipped as `domain_scope` / `DOMAIN_SCOPE`. |
| Dir `curriculum/` → `domain/` COUNTERSIGN + scenes caveat | **ACCEPT incl. caveat verbatim:** scenes are domain-situated materials, never path law; if they ever encode multi-step lesson paths they move out rather than smuggle sequence back in. |
| OLM attribution AMEND | **ACCEPT.** Planning is the tutor model's act of reading domain + learner models; OLM is the externalized learner model. The sheet is the composite, not "an OLM." |
| Word bans AMEND ("course" ≠ session plan; syllabus research-prose only) | **ACCEPT.** 1 session ≠ n-session course. Session plan is "the plan," never "the course." |
| Retire the slogan "the character sheet IS the course pack" | **ACCEPT** as vocabulary (the USER's sentence stays quoted as the historical directive; the engineering fact — inventory absorbed into sheet — stands). |
| Risk: "selection remains, sequence does not" | **ACCEPT — this is the converged answer to the original dispute.** The sheet carries curricular *selection* (closed inventory, deferrals); it carries zero *sequence*. "Not a curriculum" means "not a sequenced course design," not "no curricular content." |

**Converged vocabulary (BINDING for project prose + code names):**
the **character sheet** = domain model (targets, scope, misconception
vocabulary) co-located with the learner model (per-item measured state).
The **session plan** = the teacher model's private per-session path.
Never: curriculum/syllabus/course for the sheet; never "course" for the
plan. All shipped 2026-08-03 (payload keys, `domain/spanish_a1/`, doc
sweep); suite 837 green.
