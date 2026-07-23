# Course Pack: Spanish A1 — Foundations

**Pack ID:** `spanish_a1_foundations`
**Version:** 0.5 (architecture revision — dual-mode grounding; see `docs/architecture-pack-debate.md`)
**Content mode:** `spec`
*(Known-domain pack: curriculum + PCK + frozen eval constrain the tutor; in-scope explanations/input may be generated. See teaching policy grounding rules. Canonical tables and dialogues below are retained as reference/seed material pending the live smoke test — measurement artifacts, not exclusive content.)*
**Level:** CEFR A1 grammar-core slice (absolute beginner), first ~6 weeks — **not** a complete A1 inventory. Covers greetings/courtesy, noun gender/articles/plurals, subject pronouns, *ser*, *estar* (core contrast), regular present (-ar/-er/-ir), numbers 0–100, *tener* (possession/age), and core question words.
**Explicitly deferred A1 (do not invent; later packs):** alphabet/spelling, possessives as a taught system (*mi/tu/su...*), family vocabulary set (**except** the Unit 6 production collocations *hermano(s)/hermana(s)* with *tener*), days/dates/clock time, *hay* (recognition-only where it already appears), *ir*, food/drink noun sets beyond Unit 5's closed production set, colors, demonstratives, *cuál*, money/*costar*.
**Instruction language:** English (metalanguage), Spanish (target content)
**Variety:** Latin American Spanish as default; European (peninsular) forms noted where they differ.

## How the tutor should use this pack

- Grounding follows the **two-mode rules** in `prompts/teaching_policy.md`. This pack declares `content_mode: spec`: the in-scope inventory and denylist below are law; in-scope content may be generated; frozen items/keys/M-IDs are authoritative.
- Every unit carries **misconception entries with stable IDs** (e.g. `M-4.2`). When diagnosing a learner error, identify the matching misconception ID internally and remediate using that entry's guidance.
- Practice items have answer keys. Reveal rules are **only** those in `prompts/teaching_policy.md` (currently assigned item; first-exposure modeling of a *different* example allowed; answer-key mode scoped there). Do not invent a stricter or looser pack-local reveal rule.
- Sequence: units are ordered by dependency. Do not drill Unit 5 conjugation with a learner who has not shown mastery of Unit 3 pronouns.

### Teaching sequence within a unit (input first)

1. **Input** — open with in-scope Spanish input: the unit's seed dialogue/text, or freshly generated input that stays inside the unit's structures and vocabulary (mode `spec`). Run comprehension checks before any grammar talk. Meaning before form.
2. **Structured input (SI items)** — the learner selects *meaning* from form (who? how many? where or what?) before producing anything.
3. **Explanation + guided practice** — the canonical explanation and keyed practice items, per the teaching policy's reveal rules.
4. **Can-do task (T items)** — a communicative roleplay/production task scored against its success criteria, not against a fixed script.
5. **Recap and schedule** — summarize, then queue missed items for spaced review in later sessions.

### Spacing and interleaving

- Spaced review algorithm and session-open warm-up: follow `prompts/teaching_policy.md` only (do not restate or re-derive intervals from this file).
- When reviewing, **interleave** across units (mix *ser*/*estar*/*tener* items) rather than re-drilling one topic in a block.
- In-unit incidental words in input texts (days, places, *hay*, *mi/su*, *también*) are **recognition-only**: gloss briefly if asked, never drill them.

## Units

| Unit | File | Topic | Depends on |
|------|------|-------|------------|
| 1 | `unit01_greetings.md` | Greetings, introductions, courtesy | — |
| 2 | `unit02_nouns_gender_articles.md` | Nouns, gender, articles, plurals | 1 |
| 3 | `unit03_ser_pronouns.md` | Subject pronouns + *ser* | 2 |
| 4 | `unit04_estar_vs_ser.md` | *Estar*; contrast with *ser* | 3 |
| 5 | `unit05_present_regular.md` | Present tense: regular -ar/-er/-ir verbs | 3 |
| 6 | `unit06_numbers_tener_questions.md` | Numbers 0–100, *tener*, age, question words | 3, 4, 5 |

## In-scope inventory (what the tutor may teach and drill)

Closed list; details live in the unit files. Structures: greeting/courtesy/introduction formulas incl. *me llamo/te llamas/se llama* (U1); noun gender, definite/indefinite articles, plurals, the six listed exception nouns (U2); subject pronouns and *ser*, negation with *no* (U3); *estar* and the ser/estar what/how/where contrast, event-location *ser* as recognition (U4); regular present -ar/-er/-ir with the listed verbs and Unit 5's closed production noun set (U5); numbers 0–100, *tener* for possession and age, the listed question words, *hermano(s)/hermana(s)* with *tener* (U6). Production vocabulary = the words appearing in unit tables, items, and closed sets — not open-world Spanish.

## Scope boundaries (do not teach these)

The following are **out of scope** for this pack. The tutor must decline to teach them (briefly, without lecturing) and steer back to pack material:

- Any past tense (preterite, imperfect), future tense, conditional, compound tenses
- Subjunctive and imperative moods
- Irregular verbs other than *ser*, *estar*, *tener* (e.g. *ir*, *hacer*, stem-changers)
- Reflexive verbs beyond the fixed phrase *me llamo / te llamas / se llama*
- Direct/indirect object pronouns (*lo, la, le...*)
- *Gustar*-type constructions
- *Vos* (voseo) conjugation — acknowledge it exists in parts of Latin America, then defer
- Regional slang; vocabulary lists beyond those in the units

## Global pronunciation notes (usable in any unit)

- Spanish vowels are short and pure: a /a/, e /e/, i /i/, o /o/, u /u/. No English-style glides.
- *h* is always silent: *hola* = "OH-la".
- *ñ* = "ny" as in *canyon*: *años* = "AH-nyos".
- *ll* and *y* are usually pronounced the same (yeísmo). In much of Latin America they sound roughly like English "y": *me llamo* ≈ "meh YAH-mo". In parts of Argentina and Uruguay they sound more like English "sh" or "zh". Do not teach a Spain-only *ll* vs *y* contrast at A1.
- Written accents mark stress (*está*) or distinguish words (*tú* you / *tu* your; *él* he / *el* the). They are not optional decoration.
