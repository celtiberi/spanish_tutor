

---

## GROK (Grok Build CLI (bde89716f679)) - 2026-07-22 20:14 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll review the Spanish A1 course pack adversarially. Loading the full prompt and course materials first.Reading all course-pack units in full for a line-by-line linguistic and CEFR review.Verifying contested Spanish claims and CEFR A1 expectations against references.Checking a few more orthographic and dependency details:# Spanish A1 Course Pack v0.1 — Independent Adversarial Review  
**Reviewer role:** contrarian second pass (linguist / CEFR / editor)  
**Date:** 2026-07-22  
**Subject:** `course_packs/spanish_a1/` draft v0.1 (pack + units 1–6)  
**Verdict format:** COUNTERSIGN / AMEND (exact replacement) / REJECT (with arithmetic)  
**Scope of this pass:** factual Spanish, CEFR fit for first ~6 weeks A1, answer keys & misconception quality. No whole-file rewrites.

---

## Global countersigns (checked; no change required)

| Claim area | Verdict | Note |
|---|---|---|
| Greeting gender agreement (*buenos días* / *buenas tardes|noches*) | COUNTERSIGN | Correct; fixed-phrase pedagogy sound |
| *Me llamo / te llamas / se llama* as formula (not full reflexive grammar) | COUNTERSIGN | Correct for A1 |
| *Ser* paradigm; *usted* → 3rd person; profession without article | COUNTERSIGN | Standard A1; keys P-3.1–3.5 correct |
| *Estar* paradigm + accents; location/feelings rule; event-location *ser* (recognition) | COUNTERSIGN | Linguistically accurate; permanent/temporary myth rightly demoted |
| Regular present paradigms (-ar/-er/-ir); *leer* regular in present | COUNTERSIGN | Endings table correct; P-5.1–5.4 keys correct |
| *Tener* irregular paradigm; age = *tener* + *años*; numbers 0–100 orthography (incl. *dieciséis, veintidós, veintitrés, veintiséis, veintiún*) | COUNTERSIGN | Matches RAE-style norms; P-6.1–6.2 keys correct |
| Question-word accents; inverted *¿* | COUNTERSIGN | Correct |
| Misconceptions M-1.1–1.3, M-2.1–2.4, M-3.1–3.4, M-4.1–4.5, M-5.1–5.3, M-6.1, M-6.3–6.5 | COUNTERSIGN | Plausible learner errors + accurate remediation |
| Scope exclusions (past, subjunctive, *gustar*, object pronouns, voseo conjugation, stem-changers) | COUNTERSIGN | Coherent for a 6-unit pilot slice |

---

## Findings (item-by-item)

### F-01 — HIGH — False generalization about conjugation vowels  
**File:** `unit05_present_regular.md`  
**Quoted text:**  
> - The vowel of the family (a/e/i) shows up throughout its endings.

**Problem:** False for **-ir**. Present forms use **e** in *tú/él/ellos* (*vives, vive, viven*) and **i** only in *nosotros/vosotros* (*vivimos, vivís*). “Throughout” overclaims and contradicts the accurate bullet immediately above it (-er/-ir differ only in *nosotros/vosotros*).

**Arithmetic check (vivir present theme vowel):**  
- *vivo* — theme vowel not a/e/i family marker (yo = -o)  
- *vives, vive, viven* — **e** (3/6 forms)  
- *vivimos, vivís* — **i** (2/6 forms)  
Family vowel *i* appears in **2 of 6** person forms, not “throughout.”

**Verdict: AMEND**  
**Replacement text:**  
> - For **-ar**, the family vowel **a** appears in all forms except *yo* (*hablas, habla, hablamos, habláis, hablan*). For **-er**, **e** appears in all forms except *yo*. For **-ir**, most persons use **e** (*vives, vive, viven*); **i** appears only in *nosotros* and *vosotros* (*vivimos, vivís*) — which is exactly where -er and -ir differ.

---

### F-02 — HIGH — Unit 6 dependency omits Unit 4 while requiring *estar*  
**File:** `pack.md` (units table) **and** `unit06_numbers_tener_questions.md` (content)  
**Quoted text (pack.md):**  
> | 6 | `unit06_numbers_tener_questions.md` | Numbers 0–100, *tener*, age, question words | 3, 5 |

**Evidence of required Unit 4 material in Unit 6:**  
- Example: `¿Dónde está el baño?`  
- P-6.4 (c): answer `Está en la mesa` → key `¿Dónde está...?`  
- M-6.1 diagnosis mentions *estar* with age  

**Arithmetic:** Unit 6 officially depends on **2** units (3, 5). Content uses *estar* forms taught only in Unit 4 → dependency set size should be **3** (3, 4, 5). 2 ≠ 3.

**Verdict: AMEND**  
**Replacement text (pack.md table cell):**  
> | 6 | `unit06_numbers_tener_questions.md` | Numbers 0–100, *tener*, age, question words | 3, 4, 5 |

**Also add under Unit 6 “Scope notes” (new bullet):**  
> - Assumes Unit 4: *estar* for location appears in question-word examples and P-6.4(c).

---

### F-03 — MEDIUM — *Perdón / Disculpe* formality gloss is wrong/ambiguous  
**File:** `unit01_greetings.md`  
**Quoted text:**  
> **Perdón / Disculpe** (sorry / excuse me, formal).

**Problem:** Parenthetical reads as if both are formal, or maps only the second word to “formal.” *Perdón* is register-neutral (often the default bump/attention apology). *Disculpe* is the formal *usted* form; informal counterpart is *disculpa*. Pairing is pedagogically useful but the gloss is inaccurate.

**Verdict: AMEND**  
**Replacement text:**  
> **Perdón** (sorry / excuse me — neutral), **Disculpe** (excuse me — formal *usted*; informal: *disculpa*).

---

### F-04 — MEDIUM — P-1.5 prompt says “4-line”; model is 5 turns  
**File:** `unit01_greetings.md`  
**Quoted text:**  
> **P-1.5 (production)** — Write a 4-line dialogue: two strangers meet in the evening, greet, exchange names, and part.  
> **Key (model answer):** *— Buenas noches. — Buenas noches. ¿Cómo se llama usted? — Me llamo Ana, ¿y usted? — Soy Luis. Mucho gusto. — Igualmente. Hasta luego.*

**Arithmetic (speaker turns in model):**  
1. Buenas noches.  
2. Buenas noches. ¿Cómo se llama usted?  
3. Me llamo Ana, ¿y usted?  
4. Soy Luis. Mucho gusto.  
5. Igualmente. Hasta luego.  
**5 turns ≠ 4 lines.**

Spanish in the model is fine (register + agreement). Failure is prompt/key alignment.

**Verdict: AMEND**  
**Replacement text:**  
> **P-1.5 (production)** — Write a short dialogue (about 4–6 turns): two strangers meet in the evening, greet, exchange names, and part.  
> **Key (model answer):** *— Buenas noches. — Buenas noches. ¿Cómo se llama usted? — Me llamo Ana, ¿y usted? — Soy Luis. Mucho gusto. — Igualmente. Hasta luego.* Accept variations with correct register and agreement; do not require this exact wording or turn count.

---

### F-05 — MEDIUM — P-2.4 key gloss: “him/he” after preposition  
**File:** `unit02_nouns_gender_articles.md`  
**Quoted text:**  
> **Key:** *Una foto de él y su amigo.* (*foto* is feminine; *él* = "him/he" after a preposition.)

**Problem:** After *de*, *él* is the prepositional object (“him”), not the subject pronoun “he.” Answer form is correct; metalanguage is not.

**Verdict: AMEND**  
**Replacement text:**  
> **Key:** *Una foto de él y su amigo.* (*foto* is feminine → *Una*; after a preposition use *él* “him,” never the article *el*.)

---

### F-06 — MEDIUM — M-2.5 remediation uses *tiene* before Unit 6  
**File:** `unit02_nouns_gender_articles.md`  
**Quoted text:**  
> **Remediation:** *el* = "the" (no accent), *él* = "he" (accent). Minimal pair sentence: *Él tiene el libro.*

**Problem:** *Tener* is Unit 6. Unit 2’s own scope should not introduce an irregular verb from later. Diagnosis/remediation idea is good; example is out of sequence.

**Verdict: AMEND**  
**Replacement text:**  
> **Remediation:** *el* = "the" (no accent), *él* = "he" (accent). Minimal pair: *el libro* vs *él*; full sentence using only known patterns once *ser* is available: *Él es el amigo.* Until then, contrast the written forms in isolation.

---

### F-07 — MEDIUM — LA-default pack uses peninsular-leaning *coche* as default noun  
**File:** `unit02_nouns_gender_articles.md`  
**Quoted text:**  
> *el coche, la noche, el papel, la flor*

**Problem:** Pack claims Latin American default (`pack.md`). *Coche* is widely understood but *carro* / *auto* are the unmarked LA choices in much of the Americas. Not “wrong Spanish,” but variety policy failure.

**Verdict: AMEND**  
**Replacement text:**  
> *el carro* (also *el auto*; Spain: *el coche*), *la noche, el papel, la flor*

---

### F-08 — MEDIUM — *ll*/*y* pronunciation note overstates uniformity  
**File:** `pack.md`  
**Quoted text:**  
> - *ll* and *y* sound like English "y" (in most of Latin America): *me llamo* = "meh YAH-mo".

**Problem:** Yeísmo is widespread, but large LA populations (Rioplatense Argentina/Uruguay) realize *ll*/*y* as [ʃ]/[ʒ] (“sh”/“zh”), not English “y.” “Most of Latin America” is directionally true; the absolute gloss is too strong for a pack that claims LA default without regional caveat.

**Verdict: AMEND**  
**Replacement text:**  
> - *ll* and *y* are usually pronounced the same (yeísmo). In much of Latin America they sound roughly like English "y": *me llamo* ≈ "meh YAH-mo". In parts of Argentina and Uruguay they sound more like English "sh" or "zh". Do not teach a Spain-only *ll* vs *y* contrast at A1.

---

### F-09 — MEDIUM — Pack labels “CEFR A1” but first-6-week inventory has material gaps  
**File:** `pack.md`  
**Quoted text:**  
> **Level:** CEFR A1 (absolute beginner), first ~6 weeks

**CEFR check (first ~6 weeks of A1, not full A1):**  
Typical early A1 also includes, at minimum: alphabet/spelling names; possessives *mi/tu/su*; immediate family set; days of the week; *hay*; high-frequency *ir* (even as fixed phrases); a small concrete noun set for *comer/beber*.  

This pack is a **grammar-core slice** (greetings → nouns → *ser* → *estar* → regular present → numbers/*tener*/questions). That is defensible for a pilot, but the level line currently over-promises relative to CEFR “A1 can-do” breadth.

**Arithmetic (illustrative load):**  
- Common full-A1 guided hours often cited ≈ **90–100 h**.  
- “First ~6 weeks” at **5 h/week** = **30 h** → **30/100 = 30%** of a full A1 hour budget.  
- At **10 h/week** intensive = **60 h** → **60%**.  
Either way this is partial A1; content should say so.

**Verdict: AMEND**  
**Replacement text:**  
> **Level:** CEFR A1 grammar-core slice (absolute beginner), first ~6 weeks — **not** a complete A1 inventory. Covers greetings/courtesy, noun gender/articles/plurals, subject pronouns, *ser*, *estar* (core contrast), regular present (-ar/-er/-ir), numbers 0–100, *tener* (possession/age), and core question words.  
> **Explicitly deferred A1 (do not invent; later packs):** alphabet/spelling, possessives as a taught system (*mi/tu/su…*), family vocabulary set, days/dates/clock time, *hay*, *ir*, food/drink noun sets, colors, demonstratives, *cuál*, money/*costar*.

---

### F-10 — LOW — M-5.4 / progressive talk without Unit 4 dependency  
**File:** `unit05_present_regular.md` (depends only on Unit 3 per pack table)  
**Quoted text:**  
> \**Estoy comer* or a request for the progressive.

**Problem:** Remediation is correct for A1. But diagnosing *estar* + infinitive is cleaner if the learner already has *estar*. Soft sequencing issue, not a Spanish error.

**Verdict: AMEND** (pack.md Unit 5 row optional soft-dep; or Unit 5 scope note)  
**Replacement text (add to Unit 5 Scope notes):**  
> - M-5.4 mentions *estar* only to block the progressive; if Unit 4 is not yet done, remediate with “use the simple present (*Como*)” and do not drill *estar* forms here.

---

### F-11 — LOW — *porque* vs *¿Por qué?* not flagged  
**File:** `unit06_numbers_tener_questions.md`  
**Quoted text:**  
> | **¿Por qué?** | Why? | *¿Por qué estudias español?* |

**Problem:** Highest-frequency confusion is *porque* (because) vs *por qué* (why). Not taught; misconception list omits it. Real A1 error.

**Verdict: AMEND** (add misconception; do not expand into full causal clauses)  
**Replacement text (new entry after M-6.5):**  
> ### M-6.6 — *porque* and *¿por qué?* are the same  
> \**Porque estudias español?* or \**estudio español ¿por que?* **Diagnosis cue:** missing accent/split or using the answer-form as a question. **Remediation:** question = two words + accent *¿por qué?*; answer-word *porque* (“because”) is out of scope for production — recognition only if it appears.

---

### F-12 — LOW — Unit 5 teaches *comer/beber* with almost no food nouns  
**File:** `unit05_present_regular.md`  
**Problem:** CEFR/editor: conjugation without collocates forces empty drills (*como mucho*, *bebo agua* never listed). Not a factual Spanish error; weak pack usability for a tutor that may only teach from the pack.

**Verdict: AMEND** (minimal closed vocab list)  
**Replacement text (add under “Core A1 regular verbs” paragraph):**  
> Closed practice nouns for this unit only: *agua, café, pan, pizza, carne, fruta, casa, español, inglés, libros*. Do not expand beyond this list in Unit 5.

---

### F-13 — LOW — P-6.3 key is correct; accept-note should prefer *años* when age is stated  
**File:** `unit06_numbers_tener_questions.md`  
**Quoted text:**  
> **Key:** *Mi hermano tiene quince años y yo tengo veintiuno.* (Accept *veintiún años*.)

**Problem:** Key is grammatical. For age answers the pack’s own rule is “Always include *años* at this level.” Bare *veintiuno* answers “how many?” more than “how old?” Prefer the form with *años*.

**Verdict: AMEND**  
**Replacement text:**  
> **Key:** *Mi hermano tiene quince años y yo tengo veintiún años.* (Also accept *…tengo veintiuno* only if the learner is clearly counting, not stating age; prefer the form with *años*.)

---

### F-14 — EDITORIAL COUNTERSIGN WITH NIT — P-4.4 event location  
**File:** `unit04_estar_vs_ser.md`  
**Quoted:** *La fiesta es en la casa de Ana.*  
**Verdict: COUNTERSIGN** — Correct *ser* for event locus; accept-note *en casa de Ana* is good. No change.

---

### F-15 — EDITORIAL COUNTERSIGN — *Encantado* gender  
**File:** `unit01_greetings.md`  
**Verdict: COUNTERSIGN** — Speaker-gender agreement is standard teaching Spanish. Non-example is valid.

---

### F-16 — LINGUIST NIT (no mandatory amend) — *Más o menos / Mal*  
**File:** `unit01_greetings.md`  
Bare *Mal* as a full reply is grammatical but abrupt; *No muy bien* / *Estoy mal* are more natural. Acceptable A1 minimum. **COUNTERSIGN** for A1 scope; optional later polish only.

---

## Answer-key audit (all practice items)

| Item | Key OK? | Action |
|---|---|---|
| P-1.1 | Yes | — |
| P-1.2 | Yes (*Buenas / llamo / llamas*) | — |
| P-1.3 | Yes | — |
| P-1.4 | Yes | — |
| P-1.5 | Spanish OK; turn-count mismatch | F-04 |
| P-2.1 | Yes | — |
| P-2.2 | Yes (*lápices*, accent drop *lecciones*) | — |
| P-2.3 | Yes | — |
| P-2.4 | Form OK; gloss wrong | F-05 |
| P-2.5 | Model OK | — |
| P-3.1–P-3.5 | Yes | — |
| P-4.1–P-4.5 | Yes | — |
| P-5.1 | Yes (*trabajo, comes, vivimos, estudian, escribe*) | — |
| P-5.2 | Yes (*viven / trabaja / lee*) | — |
| P-5.3 | Yes | — |
| P-5.4 | Yes (simple present, no progressive) | — |
| P-5.5 | Model OK | — |
| P-6.1 | Yes | — |
| P-6.2 | Yes | — |
| P-6.3 | Grammatical; prefer *veintiún años* | F-13 |
| P-6.4 | Yes (needs Unit 4 for (c)) | F-02 |
| P-6.5 | Yes | — |

**Wrong-key count:** **0** fully wrong Spanish keys.  
**Keys needing edit:** **3** (P-1.5 alignment, P-2.4 gloss, P-6.3 preference) + **1** dependency (P-6.4).

---

## Summary table by severity

| ID | Severity | Type | File | Verdict |
|---|---|---|---|---|
| F-01 | **HIGH** | Linguist (false grammar claim) | `unit05_present_regular.md` | **AMEND** |
| F-02 | **HIGH** | Editor / sequencing | `pack.md` + `unit06_…` | **AMEND** |
| F-03 | **MEDIUM** | Linguist (register gloss) | `unit01_greetings.md` | **AMEND** |
| F-04 | **MEDIUM** | Editor (prompt/key mismatch) | `unit01_greetings.md` | **AMEND** |
| F-05 | **MEDIUM** | Editor (metalanguage) | `unit02_…` | **AMEND** |
| F-06 | **MEDIUM** | Editor (scope bleed) | `unit02_…` | **AMEND** |
| F-07 | **MEDIUM** | Linguist (LA vs peninsular default) | `unit02_…` | **AMEND** |
| F-08 | **MEDIUM** | Linguist (pronunciation overclaim) | `pack.md` | **AMEND** |
| F-09 | **MEDIUM** | CEFR (level claim / missing inventory) | `pack.md` | **AMEND** |
| F-10 | **LOW** | Editor (soft dependency) | `unit05_…` | **AMEND** |
| F-11 | **LOW** | Editor / learner error gap | `unit06_…` | **AMEND** |
| F-12 | **LOW** | CEFR / usability | `unit05_…` | **AMEND** |
| F-13 | **LOW** | Editor (key preference) | `unit06_…` | **AMEND** |
| F-14–F-16 | — | Countersigns / nits | various | **COUNTERSIGN** |

**Counts:** HIGH **2** · MEDIUM **7** · LOW **4** · fully wrong answer keys **0** · REJECT **0**

---

## Overall ruling

**Do not ship v0.1 as final without applying HIGH items F-01 and F-02.**  
The pack’s Spanish core is largely solid: paradigms, accents on numbers, *ser/estar* framing, and most misconception remediations hold up under adversarial check. The serious problems are (1) one false conjugation generalization that an AI tutor would teach as fact, and (2) a broken Unit 6 dependency that can surface *estar* before Unit 4.

**After HIGH + MEDIUM amends:** suitable to promote to **v0.2 (post-review)** as a pilot grammar-core pack, provided `pack.md` clearly states it is **not** a complete CEFR A1 course (F-09).

**No REJECT items:** nothing requires discarding a unit wholesale; all issues have exact replacement text above.

---

*End of independent review — 2026-07-22.*


---

## GROK (Grok Build CLI (bde89716f679)) - 2026-07-22 20:19 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll referee pack v0.2 against the three frozen gates. Loading the full prompt, collab skill, and course-pack files so every F-01–F-13 amendment can be checked against the actual text.The workspace is empty; the pack lives only in the inlined prompt. Reading the rest of the prompt and extracting every unit plus REVIEW.md findings.Verifying a few Spanish claims and scanning for residual contradictions the amendments may have introduced.Checking one more potential contradiction: deferred possessives vs. keys that still use *su*.# Spanish A1 Course Pack v0.2 — Gate Referee Report  
**Role:** independent referee (pre-registered gates; no retro-fit)  
**Date:** 2026-07-22  
**Subject:** `course_packs/spanish_a1/` pack v0.2 (post F-01..F-13 application)  
**Baseline for amendments:** round-1 findings F-01..F-13 as frozen in inlined `REVIEW.md`  
**Confound (named once):** sandbox has no pre-revision tree; “introduced by revision” is inferred from (a) exact F-replacement text now present and (b) residual pack text that conflicts with that new text—not from a git diff.

---

## GATE-1 — Every amendment F-01..F-13 correctly and completely applied  

**Rule:** each AMEND’s specified replacement text (or dual-site requirement) must appear; residual false claims targeted by the finding must be gone.

| ID | Required fix | Evidence in inlined files | Status |
|---|---|---|---|
| F-01 | Replace false “family vowel throughout” claim with accurate -ar/-er/-ir theme-vowel note | `unit05`: new bullet present (“For **-ir**, most persons use **e**… **i** only in *nosotros*/*vosotros*”); residual “throughout” **absent** | **APPLIED** |
| F-02 | Unit 6 deps → `3, 4, 5` **and** Unit 6 scope bullet on Unit 4 / *estar* | `pack.md` table: `3, 4, 5`; `unit06` scope: “Assumes Unit 4…” | **APPLIED** |
| F-03 | Split *Perdón* (neutral) vs *Disculpe* (formal; informal *disculpa*) | `unit01` Courtesy line matches replacement | **APPLIED** |
| F-04 | P-1.5 → “about 4–6 turns” + accept-variation note | Present; model turn count = **5** (arithmetic: 5 turns; allowed 4–6 → 4 ≤ 5 ≤ 6) | **APPLIED** |
| F-05 | P-2.4 gloss: *él* = “him” after preposition, not “him/he” | Key gloss matches replacement | **APPLIED** |
| F-06 | M-2.5: drop *tiene*; isolation + *Él es el amigo* once *ser* available | *tiene el libro* **absent**; new remediation present | **APPLIED** |
| F-07 | LA default: *el carro* (+ *auto*; Spain *coche*) | `unit02` gender bullet matches | **APPLIED** |
| F-08 | Yeísmo + Rioplatense sh/zh caveat | `pack.md` pronunciation bullets match | **APPLIED** |
| F-09 | Grammar-core / not full A1 + deferred inventory list | Level line + “Explicitly deferred A1…” present | **APPLIED** |
| F-10 | Unit 5 scope note for M-5.4 without Unit 4 | Scope note present | **APPLIED** |
| F-11 | Add M-6.6 *porque* vs *¿por qué?* | `unit06` M-6.6 present with diagnosis + remediation | **APPLIED** |
| F-12 | Closed practice noun list + “Do not expand…” | List of **10** nouns + ban sentence present | **APPLIED** (as written) |
| F-13 | Prefer *veintiún años* in P-6.3 | Key prefers *tengo veintiún años*; bare *veintiuno* demoted | **APPLIED** |

**Arithmetic:** **13 / 13** amendments present as specified.  
**Spanish check on F-13 form:** *veintiún* + masculine *años* is standard apocope (RAE-style); not a failed application.

**GATE-1 verdict: PASS**

---

## GATE-2 — Corpus contract  

**Required per unit:** learning objectives; canonical explanation; examples **and** non-examples; misconceptions with stable IDs **and** remediation; practice items with answer keys; scope notes.  
**Required in pack manifest:** scope boundaries.

| Unit | LO | Canon | ✅/❌ | M-IDs | Remediation count | Practice keys | Scope |
|---|---|---|---|---|---|---|---|
| 1 | yes | yes | 2/3 | M-1.1–1.4 (4) | 4 | 5 | yes |
| 2 | yes | yes | 2/3 | M-2.1–2.5 (5) | 5 | 5 | yes |
| 3 | yes | yes | 2/3 | M-3.1–3.4 (4) | 4 | 5 | yes |
| 4 | yes | yes | 2/3 | M-4.1–4.5 (5) | 5 | 5 | yes |
| 5 | yes | yes | 2/3 | M-5.1–5.5 (5) | 5 | 5 | yes |
| 6 | yes | yes | 2/3 | M-6.1–6.6 (6) | 6 | 5 | yes |

**Pack:** `## Scope boundaries (do not teach these)` present; unit dependency table present; version labeled **0.2**.

**Arithmetic:**  
- Units fully structured: **6 / 6**  
- Misconception entries with remediation: **4+5+4+5+5+6 = 29 / 29**  
- Practice items with keys: **5 × 6 = 30 / 30**  
- Spot-check of Spanish keys (P-1.x–P-6.x paradigms, *ser*/*estar*/*tener*, numbers incl. *dieciocho, veintidós, veintiún, cien*): **0** fully wrong Spanish keys found in this pass.

**GATE-2 verdict: PASS**

---

## GATE-3 — No new Spanish-language errors; no new internal contradictions  

### Spanish-language errors introduced by revision  
Re-audit of amended Spanish (F-01 theme vowels; F-07 *carro*; F-08 yeísmo; F-13 *veintiún años*; F-11 *por qué* orthography): **no new Spanish falsehoods** found. Core paradigms remain correct.

### New internal contradictions (revision-introduced)

**C-1 — HIGH-for-editor (GATE-3 FAIL trigger): F-12 absolute closed-list ban vs Unit 5 body**

F-12 added, verbatim:  
> Closed practice nouns… *agua, café, pan, pizza, carne, fruta, casa, español, inglés, libros*. **Do not expand beyond this list in Unit 5.**

Closed-set size = **10**. Same unit still contains (non-exhaustive) material **outside** that set:

| Location | Out-of-list tokens |
|---|---|
| Canonical example | *Bogotá*, *banco* |
| P-5.3 | *francés*, *idiomas* |
| P-5.4 | *hoy* |
| P-5.5 model | *familia*, *lunes*, *domingos*, *sábados*, *Austin* |

**Arithmetic:** **≥ 8** distinct forms outside a **10**-item ban list appear in Unit 5 teaching/model text.  
Under a literal reading of the new rule, Unit 5’s own examples and keys **violate** Unit 5’s own scope. That contradiction **did not exist** before the closed-list sentence was inserted; applying F-12 without aligning examples/keys created it.

**C-2 — MEDIUM tension: F-09 deferred possessives vs residual *su***  
F-09 lists possessives as a taught system (*mi/tu/su…*) as **explicitly deferred**. P-2.4 key still contains *su amigo*. *su* was pre-existing; F-09 **sharpens** the contradiction by writing the deferral into the manifest without scrubbing the key. Secondary to C-1; alone would be a nit, not a free-standing Spanish error.

**C-3 — Cross-check with F-09 deferred days / family**  
P-5.5 model uses *lunes/domingos/sábados* and *familia* while F-09 defers “family vocabulary set” and “days/dates/clock time.” Same family of pack-self-consistency issues as C-1.

**Not counted as GATE-3 fails (confound / pre-existing):**  
- Bare *Mal* as A1 reply (F-16 countersign).  
- Soft *ser* preview in M-2.5 (explicitly conditional; matches F-06 text).  
- *Hay* only in M-6.5 diagnosis example (Unit 6 already allows recognition-only *hay*).

**GATE-3 verdict: FAIL**  
Reason: **C-1** is a new internal contradiction introduced by the F-12 application. Compound gate requires *both* no new Spanish errors *and* no new contradictions; Spanish side passes, contradiction side fails → whole gate **FAIL**.

---

## Gate summary

| Gate | Verdict | One-line reason |
|---|---|---|
| GATE-1 | **PASS** | 13/13 F-amends present as specified |
| GATE-2 | **PASS** | 6/6 units + pack satisfy contract checklist |
| GATE-3 | **FAIL** | F-12 “do not expand” closed list vs Unit 5 examples/P-5.3–5.5 |

---

## Overall ruling: **DO-NOT-SHIP** pack v0.2 as Phase 2 pilot corpus

**Not** because HIGH linguistic items from round 1 remain (they do not: F-01 false -ir claim is fixed; F-02 Unit 6/*estar* dependency is fixed).  
**Because** GATE-3 fails under the frozen rule set: the revision left a self-contradictory Unit 5 vocabulary rule that an AI tutor grounded on this pack can obey only by ignoring its own models, or violate only by ignoring its own ban.

### Minimal unblock (not a retro-fit of gates; remediation path only)

Either of the following restores GATE-3 without reopening F-01..F-13 substance:

1. **Soften F-12 language** to tutor-guidance, e.g. closed set for *free production drills*; pack examples/models may use proper names and other already-in-pack words; **or**  
2. **Hard-align Unit 5** so every example and model answer stays inside the 10-noun set (and strip deferred day/family lexemes from P-5.5), **and**  
3. Optionally resolve C-2: replace *su* in P-2.4 with a non-possessive frame, or mark *su* as recognition-only in Unit 2 scope.

Until C-1 is resolved, **v0.2 remains DO-NOT-SHIP** for pilot corpus use.

---

*End of gate referee report — 2026-07-22.*
