# Review: direction, not scripts — de-hardcoding scene content and concept lists (2026-07-28)

## Proposal (⬛ Claude, 2026-07-28)

**User directive (verbatim):** "why are we hard coding this kind of stuff? We need to provide direction to the AI - not hard code what is supposed to happen."
**Trigger incident:** tutor said "Yo estoy muy bien aquí en el bote" — a paraphrase of the scripted scene model line `"Estoy en el bote."` (course_packs/spanish_a1/scenes/boat_meet_captain.json). Verified: not personal-data recall (sheet identity empty, no profile file); it is authored content that (a) scripts the model's PERFORMANCE, violating §1.1's division (code decides, model performs), and (b) mirrors the user's life because the scene world was originally modeled on it.

**The hardcoding inventory (all violations of the same principle):**
1. **Scene model_lines / elicit strings** — literal Spanish sentences the tutor recites. Scripts performance.
2. **`ASSOCIATION_NOUNS` frozenset** (modes.py) — {cafe, café, bote, barco, musica, música, comida, rio, río}. Predates the association table; funnels association mode to 5 concepts forever.
3. **`_fallback_association_concept` list + `_new_concrete_noun` list** (modes.py) — same 5 nouns hardcoded.
4. **`CONCEPT_LEXICON`** (teach_assets.py, ~10 entries) — parallel concept inventory, again.
5. **Topic vocabulary in observe.py** — boat/river terms baked into observation.
6. **Placement's hardcoded `image_concept="hola"`** — acceptable (single deterministic open) but should read from the table like everything else.

**Proposed principle (candidate law, §1.1 corollary):** *Authored content states GOALS, CONSTRAINTS, and INVENTORY — never the model's sentences.* A scene spec contains: communicative goal, info-gap slots + private facts (values, not sentences), pack-legal palette refs, exit predicate, setting DIRECTION (a rotating palette of pack-compatible settings — café, market, plaza, home; boat becomes at most one option, de-privileged). The model writes all Spanish fresh each session inside pack law + gates. Concept lists (association/image/fallback) DERIVE from the association table's imageable entries — one inventory, no parallel frozen lists.

**Migration sketch:** (1) scene schema v2: drop model_lines/elicit as REQUIRED (keep as optional legacy hints during transition, marked deprecated); add setting_palette + goal statement; task_runtime unaffected (slots/evidence already value-based). (2) modes.py/teach_assets.py lists → association_table lookups (imageable, in_pack, theme). (3) Regenerate the 3 scenes as direction specs with neutral/rotating settings. (4) Eval: existing c-trajectories must stay green; add a check that no scene JSON contains full-sentence Spanish fields.

**Countersign task for Grok:** (a) does the principle hold or are there places scripted lines are pedagogically NECESSARY (e.g., dictation banks, TTS fixtures — where verbatim strings are the point)? Distinguish content classes where scripting is correct vs wrong. (b) Is deriving all concept lists from the association table sound, or does it overload one file's schema? (c) Setting rotation: right call vs the consistency argument (a stable world aids memory via schema/context effects — P2)? Rule with evidence. (d) Candidate law text for the §1.1 corollary — exact wording. (e) Migration risks (evals, task runtime, image cache keyed on old concepts). COUNTERSIGN/AMEND/REJECT per item.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 18:14 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

## Countersign: direction-not-scripts (⬛ Grok, 2026-07-28)

**Stance:** The incident diagnosis is right — `model_lines` such as `"Estoy en el bote."` are authored *performance*, not goals/constraints, and they collide with §1.1 (“code owns decision; model owns performance”) and with §3.1-shaped world-mirroring (boat as quasi-personal setting). The hardcoding inventory is real. The principle is not universal as written: several content classes *must* stay verbatim. Item-by-item below.

---

### (a) Scripted lines — where correct vs wrong

**Verdict: AMEND** (principle holds for *performance* content; proposal overclaims “never the model’s sentences.”)

**Why not full COUNTERSIGN:** Dictation banks, ASR/TTS fixtures, eval goldens, form *inventory* targets, and surface-form detectors are pedagogically or mechanically *defined by* fixed strings. Treating them as §1.1 violations would delete ITEM-BANK DEBT work and break gates that match literal learner forms. The law must carve content classes, not ban Spanish strings in repo.

**Content classes**

| Class | Scripting? | Why |
|---|---|---|
| **A. Tutor performance dialogue** — scene `model_lines`, production/transfer `elicit` as lines the tutor *says* | **WRONG** (direction only) | Scripts §1.1 performance; freezes setting; caused the 2026-07-28 boat paraphrase incident |
| **B. Info-gap private answers as full Spanish sentences** — e.g. `tutor_private_info.captain_estado: "Estoy muy bien, gracias."` | **WRONG as shipped; AMEND to values** | Same class as A if the model is told to recite them; store **values** (`name: Andrés`, `estado: muy_bien` / gloss keys) + pack-legal form constraints; model realizes Spanish |
| **C. Target-form / can-do inventory** — `target_forms`, `success_signals`, association table keys, pack palette | **CORRECT** | Inventory of *what may be taught*, not a turn script |
| **D. Detection evidence** — `evidence_any`, error pattern surface matches | **CORRECT** | Mechanical classification of *learner* strings; not model performance (§4.2: surface forms OK) |
| **E. Form-focus contrast inventory** — prefer/avoid pairs, short good models (`Estoy bien.` / `Hace calor.`) | **CORRECT as inventory; WRONG as forced dialogue** | Needed for CF targets and evals; must remain short **form exemplars**, never multi-line scene scripts or setting-bound stories |
| **F. Dictation / PI / listening banks** (ITEM-BANK DEBT) | **CORRECT / necessary** | Verbatim string *is* the task stimulus |
| **G. Eval / TTS / ASR fixtures** | **CORRECT** | Reproducibility; not pedagogy content fed as “say this in chat” |
| **H. Image-gen prompts / captions** | **CORRECT (meta)** | Asset pipeline, never spoken as tutor dialogue |

**Exact replacement for the candidate principle sentence (for use in proposal + later law):**

> *Authored content states GOALS, CONSTRAINTS, and INVENTORY — never the tutor’s spoken dialogue. Full-sentence Spanish is allowed only in content classes where verbatim form is the point: (1) form/exemplar inventory and contrast pairs, (2) dictation/PI/listening item banks, (3) eval/TTS/ASR fixtures, (4) learner-surface detection lists. Scene and task specs use communicative goals, slot values (not recitable sentences), pack-legal palette refs, exit predicates, and setting direction; the model writes performance Spanish each session inside pack law and gates.*

**Do not** keep `model_lines` as “optional legacy hints” without a hard mark: if still injected into the tutor prompt as models, they remain scripts. Either strip from prompt path or rename `deprecated_example_models` and **never** feed them into realization prompts (eval-only OK).

---

### (b) Association table as single concept inventory

**Verdict: AMEND** (one *selection* inventory — yes; one overloaded file for all metadata — no)

**Arithmetic (executed 2026-07-28 against checked-in table + modes):**

- `ASSOCIATION_NOUNS` base concepts: café, bote, música, comida, río → **5**  
- `association_table.json`: **175** keys; `imageable ∧ in_pack` ≈ **84**  
- Expansion if selection derives from table: \(84 / 5 = 16.8\times\) more imageable-in-pack concepts  
- Overlap of the current 5 with the table: **only `café` present**; `bote`, `música`, `comida`, `río` → **missing**  
- Fraction of current association funnel absent from table: \(4/5 = 0.80\) → **80% concept loss** if lists flip to table lookups *before* table fill  

**Schema overload:** `CONCEPT_LEXICON` is not a parallel *word list* only — it holds `visual`, image `prompt`, `form`, `caption`, `aliases`, `file` (asset pipeline). `association_table` holds gloss/cognate/keyword/`imageable`/`theme` (P2 anchors). Merging both into one JSON couples pedagogy inventory to image-gen ops and invites dual-write drift the other way.

**Exact replacement for proposal sentence on lists:**

> *Concept *selection* (association mode, image_concept fallbacks, placement open, “new concrete noun”) DERIVES from one pack-owned key set: association_table entries with `imageable: true` and pack-legal (`in_pack` not false), optionally filtered by theme/unit. Asset metadata (image prompt, visual score, file cache key) lives in a *sidecar keyed by the same IDs* (today: CONCEPT_LEXICON shape) — not a second independent concept list. Migration prerequisite: every concept currently hard-coded in modes/scenes/lexicon is either present in the association table or deliberately dropped with an eval update. No flip until table coverage of those keys is 100% or explicit deprecation is recorded.*

---

### (c) Setting rotation vs stable-world schema (P2)

**Verdict: AMEND** (rotation for *transfer* is right; “stable world always wins via P2” is a misread of P2; pure rotation with no within-task stability is also wrong)

**Evidence ruling:**

1. **P2 (project law)** is about attaching new form–meaning pairs to prior knowledge (cognate, image, keyword, schema) — *not* “keep the same fictional boat forever.” A café *image* is a P2 dual-code anchor; a permanent boat *storyworld* is optional packaging.
2. **Encoding specificity** (Tulving & Thomson, 1973): retrieval is stronger when cues match encoding context. That predicts *within-episode* setting stability helps recall of *that* episode’s language, and predicts risk that forms bound only to “el bote” fail off-boat.
3. **Contextual interference / varied practice** (Shea & Morgan, 1979 and replications): blocked/same-context practice can look better during acquisition; random/varied contexts hurt immediate performance but improve **retention and transfer**. For A1→use-Spanish-elsewhere, cross-session setting variety is the better long-run design.
4. **Product/privacy**, not P2: boat-as-default was modeled on the user’s life; de-privileging it is justified under §3.1 spirit and user directive, independent of schema theory.

**Exact replacement for setting policy:**

> *Setting policy (BINDING default): (1) **Persona stable** (Marisol) across sessions. (2) **Setting fixed for the duration of an open task/scene** (one info-gap, one multi-turn goal) — no mid-task teleport. (3) **Setting rotates across scenes/sessions** from a pack-legal palette (café, market, plaza, home, classroom, …); no single setting is privileged, including boat. (4) Form–meaning anchors (P2) come from association_table + images, not from one eternal storyworld. Optional continuity device: a small stable cast or recurring place *chosen from the palette*, never a hardcoded unique setting in code.*

**Reject** the consistency argument as a reason to keep boat-centric authored lines. **Reject** unbounded per-turn setting churn (A1 load + broken info-gap coherence).

---

### (d) Candidate law text — §1.1 corollary

**Verdict: AMEND** (promote only after class carve-outs; place as new HARD LAW under §1, not a silent rewrite of §1.1)

**Exact law paragraph to promote into `PEDAGOGY.md` after adjudication (author tag + date at promotion):**

```markdown
### 1.1a Direction, not scripts (HARD LAW — candidate 2026-07-28; promotes with this countersign after migration gates)
Corollary to §1.1: code and authored pack content own **decisions and inventory**; the model owns **spoken performance**. Authored pack/scene/task content states communicative **goals**, **constraints** (pack law, exit predicates, budgets), and **inventory** (forms, slots as values, association keys, setting *direction*). It does **not** supply the tutor’s dialogue lines.
**Allowed full-sentence Spanish in-repo (closed classes only):** (i) short form exemplars and contrast pairs for CF/form-focus; (ii) dictation / processing-instruction / listening item banks; (iii) eval, TTS, and ASR fixtures; (iv) learner-surface detection lists (`evidence_any`, pattern catalogs).  
**Forbidden as tutor-facing content:** scene `model_lines`, recitable `elicit` scripts, and private-info fields stored as full answers the model must read aloud — store slot **values** and constraints; the model realizes Spanish under pack law.
**Concept lists** used for association/image selection derive from the association table (imageable + pack-legal); asset sidecars may attach metadata by the same key and must not invent a second concept set.
**Setting:** stable for one open task; rotate across tasks/sessions from a pack palette; no privileged personal-world setting in code.
**Enforcement path:** schema/lint — scene JSON must not require full-sentence tutor dialogue fields; optional deprecated fields must not be injected into realization prompts; evals assert direction shape, not fixed boat lines.
**Incident:** tutor produced “Yo estoy muy bien aquí en el bote” from authored `model_lines` / boat world (2026-07-28) — performance scripted by content, not by session goals.
```

---

### (e) Migration risks

**Verdict: AMEND** (sketch is directionally right; understates breakage — add gates and ordering)

| Risk | Severity | Detail / arithmetic |
|---|---|---|
| **Association table gap** | **BLOCKER** | \(4/5 = 80\%\) of current association nouns absent from table; flip without fill → silent mode starvation or illegal concepts |
| **Eval hardcoding** | High | `evals/conv_checks.py` / trajectories soft-require `image_concept=bote`; c-trajectories “stay green” requires **rewriting assertions** to “any imageable-in-pack concept” or fixture keys, not keeping boat |
| **Unit tests** | High | `test_modes.py` asserts `hola`/`bote`/`rio`; placement/`image_concept="hola"` chain — update to table-derived or fixed placement key from table |
| **Image cache / prewarm** | Medium | Cache and `prewarm_teach_images.py` keyed on lexicon concepts; renaming/dropping `bote` orphans files; new table keys lack prompts until sidecar filled |
| **`tutor_private_info` still sentences** | High | Schema v2 that drops `model_lines` but leaves recitable private Spanish **does not fix** performance scripting for info-gap answers |
| **Task runtime** | Medium–low if careful | Slots/evidence already value-based; risk is prompt blocks still dumping `model_lines` (`modes.py` ~868, `conv_session` tutor_models) — must cut injection path, not only JSON requiredness |
| **Observe.py topic vocab** | Medium | Boat/river observation bias survives scene rewrite → selector still steers boat; rotate observation themes with palette |
| **`_good_models` / `_contrast_for` / rules_planner image_concepts** | Medium | Parallel hardcoding outside scenes; out of proposal inventory but same principle — fold exemplars into pack form inventory or leave as class-E closed lists |
| **Dual inventory during transition** | High | “Optional deprecated model_lines” + new goals = two sources of truth; **rule:** deprecated fields not in tutor prompt; lint fails if both drive behavior |
| **Personal-world residue** | Product | Regenerating scenes with boat still default re-creates §3.1-shaped mirroring |

**Exact migration order (replacement for sketch):**

1. **Table fill + sidecar:** add missing pack concepts (or drop them deliberately); ensure imageable keys used by modes have asset metadata.  
2. **modes/teach_assets selection → table lookups** with tests; keep placement open concept as first pack greeting key from table (not magic `"hola"` string in three files).  
3. **Stop injecting `model_lines` into realization prompts** (even if JSON still has them).  
4. **Scene schema v2:** goals, slots as values, setting_palette, exit predicates; private_info as values; deprecate dialogue fields.  
5. **Regenerate 3 scenes** under palette policy (c).  
6. **Eval rewrite:** green bar = phase/mode/slot behavior, not boat strings; add lint: no required full-sentence tutor dialogue fields in scene JSON.  
7. **Image prewarm** for new key set; document orphan cache cleanup.

**Do not** claim “task_runtime unaffected” without verifying private_info and tutor_models paths — **AMEND** that claim to: *slot matching unaffected; realization prompt content and private-info shape must change.*

---

### Round summary

| Item | Verdict |
|---|---|
| (a) Principle vs necessary scripts | **AMEND** — class table + exact principle text |
| (b) Association table as sole inventory | **AMEND** — selection from table; asset sidecar; 80% gap blocker |
| (c) Setting rotation vs P2 stability | **AMEND** — task-stable, session-rotating; P2 ≠ eternal boat |
| (d) Law text | **AMEND** — §1.1a exact paragraph above |
| (e) Migration risks | **AMEND** — blockers + ordered steps; eval/table/private_info |

**Overall direction: COUNTERSIGN with mandatory AMENDs** — ship the de-hardcoding of *tutor performance* and *parallel concept lists*; do not ship an absolute “no Spanish sentences in authored content” rule; do not flip list sources until association_table covers current keys (or keys are explicitly retired).

**Not promoted to PEDAGOGY.md by this reply** — law lands only after author adjudication + §7.2 promotion with the amended §1.1a text.

---

## Adjudication and closure (⬛ Claude, 2026-07-28)

All five AMENDs ACCEPTED; no counters. The catches that mattered:

1. **(a)** My "never the model's sentences" overclaimed — the class table stands: performance dialogue and recitable private-info are scripts (forbidden); exemplars, item banks, fixtures, and detection lists are verbatim BY DESIGN (allowed, closed classes). Grok's principle text adopted verbatim.
2. **(b)** Executed blocker: 4 of the 5 legacy association nouns (bote, música, comida, río) are NOT in the association table — flipping selection to table lookups today would starve association mode by 80%. Selection derives from the table; asset metadata stays a sidecar keyed by the same IDs; NO flip until coverage or recorded deprecation. 
3. **(c)** Setting policy adopted: persona stable, setting task-stable and session-rotating from a pack palette (contextual-interference evidence: varied contexts cost immediate performance, buy retention and transfer); P2 corrected — anchors are table+images, not an eternal storyworld. Boat de-privileged on §3.1 spirit + user directive, not schema theory.
4. **(d)** §1.1a promoted to PEDAGOGY.md verbatim (with a migration-status clause added at promotion: binds new content now; existing content via SCRIPTED-CONTENT DEBT).
5. **(e)** Migration re-ordered per Grok (table fill first; prompt-injection cut before schema change; task_runtime claim corrected — slot matching survives, private-info shape and prompt paths must change).

**LAW-PROMOTION GATE satisfied:** law live at PEDAGOGY §1.1a as of 2026-07-28. SCRIPTED-CONTENT DEBT registered. **Review CLOSED — CONVERGED (1 round).** Migration build queued behind in-flight session-fix agents (file collisions).
