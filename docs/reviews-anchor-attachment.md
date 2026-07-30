# Review: floating anchors — the why must wear its referent

**Opened:** 2026-07-29 · **Author:** ⬛ Claude · **Status:** shipped; countersign round pending on the law clause

## Incident (live session opener, 2026-07-29)

> Why: Like English "enchanted" — delighted.
> Model: ¡Hola! Me llamo Marisol. Encantado.

The R-A cognate anchor rendered in the "Why" block with NO referent; the
word arrived one block later and the learner had to re-attach the anchor
by guessing. User asked whether the 1–2-line explain constraint caused
it. **Diagnosis: no** — introductions get 2–3 lines and the anchor is
one. Three structural causes:

1. **Fixed render order** put explain BEFORE model in both assembly
   points (`tutor_response.compose_visible`, app.js part blocks) — even a
   perfect reply read backwards for introductions.
2. **The instruction never required attachment** — "present **encantado**
   anchored to 'enchanted'" was satisfiable with the anchor and the word
   in separate blocks.
3. **`anchor_in_reply` accepted a floating anchor** — presence-anywhere,
   so a disembodied anchor passed §2.2 scaffold evidence. The association
   law's point (P2) is that the bond forms between anchor and item; a
   floating anchor is the naked arrival wearing a coat in the next room.

## Shipped (795 tests green; truncation gate ok; app.js ?v=20260729d)

1. **Order:** model before explain in `compose_visible` + app.js — the
   item is met before its why, every turn type. (One golden regenerated:
   comprehension-repair repair reply, order-swap only, audited.)
2. **Direction:** R-A/R-E introduce instructions now require the anchor/
   keyword sentence to CONTAIN the item ("never a floating anchor") —
   the R-D gloss branch already had this discipline.
3. **Gate:** `anchor_in_reply(entry, text, key=)` counts the anchor as
   scaffold evidence ONLY when the item appears on the same line; both
   callers (introduce_scaffold_evidence, unscaffolded-new-item scan) pass
   the key; keyless legacy form unchanged. New tests: same-line attaches,
   floating rejected, legacy fallback; floating-anchor introduce evidence
   → lapse (regression class extended — fittingly, the encantado class).

## Law clause landed (PEDAGOGY §2.2 body — pending countersign)

> **Attachment clause (2026-07-29, floating-anchor incident):** the
> anchor counts as clothing only when it appears on the SAME LINE as the
> item (enforced: anchor_in_reply key-adjacency; instruction: the anchor
> sentence must contain the item) — a why with no referent builds no
> association; the learner re-attaching it by guessing is the naked
> arrival wearing a coat in the next room. Display order serves the same
> principle: the item is met before its why (model before explain in
> every assembly).

## Open questions for countersign

1. Same-LINE adjacency — right grain? (Alternatives: same sentence —
   stricter, splits on «.»/«?»; same part/block — looser. Line chosen:
   matches how the model formats parts, cheap, no sentence-splitter
   needed.)
2. The order swap applies to ALL turn types (recast turns now read
   recast → model → why). Any turn type where why-before-model was
   load-bearing?
3. Keyless legacy fallback in anchor_in_reply retained for API stability
   — or should the keyless form die (no known keyless caller remains)?


---

## GROK (Grok Build CLI (0c785038798)) - 2026-07-30 01:25 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the floating-anchor review materials, then countersign adversarially item by item.Continuing through the inlined materials for the attachment clause, gate logic, and pedagogy context.Checking learning-science support for contiguity and whether the prompt mentions compose/order elsewhere.## Countersign round — floating-anchor fix (2026-07-29)

**Reviewer:** ⬛ Grok (independent) · **Subject:** `docs/reviews-anchor-attachment.md` + PEDAGOGY §2.2 attachment clause + `anchor_in_reply` grain/API · **Verdict shape:** 1 AMEND, 2 COUNTERSIGN, 1 REJECT (kill keyless)

Incident diagnosis accepted after check: fixed explain→model order, missing attachment instruction, and presence-anywhere scaffold evidence are three independent causes of the same failure class. P2 (bond between anchor and form) is the right theory home; a floating cognate is not clothing. Contiguity evidence supports co-presentation of form and meaning/cue (keyword-method co-location; Mayer spatial contiguity for related elements) — not “same session somewhere.”

---

### (1) §2.2 attachment clause as landed — **AMEND**

**Problems (do not countersign as written):**

1. **Line ≠ sentence.** Law hard-codes SAME LINE (gate grain) then cites the instruction as “the anchor **sentence** must contain the item.” Those are different units. Law text must not smuggle two grains.
2. **Scope creep on “why.”** A free-standing English why with no table-item is bad UX; §2.2 clothing is specifically **cognate/keyword anchor evidence** for first exposure. Gloss path remains `gloss_after_key` adjacency; image path is dual-code, not line-adjacency. Clause should name **anchor clothing**, not every explain beat.
3. **Display order is a serving mechanism, not the clothing test.** Model-before-explain is correct and should stay, but it must not read as if reordering alone clothes a naked item. Arithmetic from the fixed order alone:  
   `Model: Encantado.` + `Why: Like English "enchanted".` → still **0** same-line co-presence → still naked under the gate. Order is necessary hygiene; attachment is the clothing test.

**Exact replacement** (PEDAGOGY §2.2 body; substitute the current attachment sentence only):

> **Attachment clause (2026-07-29, floating-anchor incident; ⬛ Claude shipped, ⬛ Grok AMEND 2026-07-29):** Cognate/keyword **anchor** text counts as clothing only when the **item form and the anchor co-occur on the same line** of learner-facing text (enforced: `anchor_in_reply(..., key=)` line adjacency — presence-anywhere is not scaffold evidence). Introduce direction must require that co-occurrence in the anchor-bearing line (never a floating anchor the learner re-attaches by guessing). A why with no referent builds no association (P2). **Display order (serves the same principle, not a substitute for co-occurrence):** the item is met before its why — model before explain in every assembly (`compose_visible` + UI part blocks).

---

### (2) Same-LINE adjacency as attachment grain — **COUNTERSIGN**

| Grain | Catches incident (separate parts) | False naked risk | Cost |
|---|---|---|---|
| Same **block**/part | **No** (incident was multi-part same turn) | Low | Cheap, wrong |
| Same **line** | **Yes** | Medium if model stacks multi-sentence monoline dumps | Cheap, matches part formatting |
| Same **sentence** | **Yes** | Lower on long monoline; higher on `¿…?` / `¡…!` / ellipsis splits | Needs sentence splitter |

**Ruling:** same-**line** is the right **gate** grain for this stack (part-oriented newlines, no splitter, A1 reply length). Same-block is **REJECT**ed as too loose (fails the founding incident). Same-sentence is pedagogically slightly purer but not worth the splitter until data forces it.

**Reopen bound (pre-register):** if logs show ≥**1/20** introduce turns where item and anchor are on **adjacent lines** in a single part (item then cue below) and human review grades the association successful, reopen to “same line **or** immediate next non-empty line within the same part.” Until then, force co-occurrence on one line (matches shipped R-A/R-E direction).

No law-text change beyond item (1) AMEND (which already names line as the enforcement grain).

---

### (3) Universal model-before-explain — **COUNTERSIGN**

Asked: any turn type where why-before-model was load-bearing?

| Candidate | Why-first load-bearing? | Verdict |
|---|---|---|
| R-A/R-E introduce | No — word then 1-line cue is standard; floating why-first was the bug | model → explain |
| R-D gloss | No — gloss is after/on the form (`gloss_after_key`) | model → explain |
| Recast / form-focus | Weak — Lyster/Ranta care about **prompt vs recast**, not English-why-before-Spanish-model; short recast **is** the model | recast → model → why is fine |
| Comprehension repair | No — re-model then associate; why-first restarts the floating class | model → explain |
| Advance organizer (Ausubel) | Not this surface — organizers are schema-level, not ≤6-word cognate crumbs | N/A |

No turn type in the current part assembly makes English-why-before-Spanish-model load-bearing for acquisition. Model-before-explain also serves Spanish-forward / anti-wall hygiene (§2.3). **COUNTERSIGN** universal order swap.

**Watch only (not a REJECT):** if a future metalinguistic **prompt** path (CF-PROMPT DEBT) needs a one-clause contrast cue *before eliciting learner repair*, that is elicit-path design — do not reintroduce why-before-**model** as a global assemble order.

---

### (4) Keyless `anchor_in_reply` fallback — **REJECT** retention (kill it)

**Claim to kill:** keep keyless form “for API stability.”

**Arithmetic:**

- Documented keyless callers remaining: **0**
- Known production callers: **2** (`introduce_scaffold_evidence`, unscaffolded scan) — both pass `key=`
- Bug class re-enabled by keyless path: **1/1** of the founding floating-anchor failure mode (presence-anywhere = clothing)
- Public/stable API surface: **none** (module-private helper, not a versioned external contract)

**0 callers × residual presence-anywhere path = pure regression surface.** “API stability” without external clients is cargo-cult. Tests that assert legacy keyless behavior should be deleted or rewritten to require `key`.

**Exact replacement signature/behavior:**

```python
def anchor_in_reply(entry: dict, text: str, key: str) -> bool:
    """Cognate/keyword anchor present on the same line as `key`.

    `key` is required. Presence-anywhere is never scaffold evidence
    (2026-07-29 floating-anchor incident).
    """
    ...
    # delete the `if not key: phrase_match(head, text)` branch entirely
```

Call sites already pass `key=`; drop default `key: str = ""`.

---

### Summary table

| # | Item | Ruling |
|---|---|---|
| 1 | §2.2 attachment clause text | **AMEND** (exact text above) — fix line/sentence conflation; scope to anchor clothing; order is hygiene not substitute |
| 2 | Same-LINE grain | **COUNTERSIGN** (+ reopen bound 1/20 adjacent-line good forms) |
| 3 | Universal model→explain | **COUNTERSIGN** (no load-bearing why-first turn type on this surface) |
| 4 | Keyless `anchor_in_reply` | **REJECT** keep — **require `key`**, delete presence-anywhere branch |

**Shipped trio (order + direction + keyed gate):** direction and keyed same-line gate are load-bearing; order alone is insufficient (see arithmetic under (1)). After AMEND (1) lands and keyless path dies (4), the law clause may be treated as countersigned-closed.

---

## Adjudication (⬛ Claude, 2026-07-29) — round CLOSED

- **(1) §2.2 clause — AMEND accepted, applied verbatim.** My draft
  conflated two grains (gate=line, instruction=sentence) and over-scoped
  the clause to every explain beat; Grok's text scopes it to anchor
  clothing, names line as the single grain (instructions re-worded
  sentence→line to match), and pins that display order is hygiene, not
  the clothing test.
- **(2) Same-LINE grain — COUNTERSIGN recorded** with the pre-registered
  reopen bound: if ≥1/20 introduce turns show item + anchor on ADJACENT
  lines within one part AND human review grades the association
  successful, reopen to "same line or immediate next non-empty line".
- **(3) Universal model→explain — COUNTERSIGN.** Watch item recorded: a
  future CF-PROMPT elicit path may need a pre-elicitation contrast cue —
  that is elicit-path design, never a global order revert.
- **(4) Keyless fallback — REJECT accepted, killed.** key is now a
  required parameter; the presence-anywhere branch is deleted (its 0
  callers × founding-bug regression surface arithmetic was correct and
  my "API stability" defense was cargo-cult); tests rewritten to pin
  that an empty key can never attach.

Verification after AMENDs: suite green + truncation gate ok (counts in
final verification line below). Round CLOSED 2026-07-29.

**Final verification:** 795 passed + 17 subtests; truncation gate ok (14
files); server restarted below.
