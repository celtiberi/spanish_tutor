# Review: tutor-declared teach images (optional tag, replaces regex scanning)

Rolling review file. Pattern: propose → countersign → adjudicate → converge.

## Proposal (Claude, 2026-07-28)

Incidents: a sun image on «Hola Marisol» ('sol' substring in the persona's
name), previously on «yo solo compra caras», and 'rio' matching inside
'serio' — all from regex noun-scanners picking image concepts. Patrick's
directive: image use is a DECISION, never mandatory; prefer model judgment
over keyword matching (a cheap Grok side-call was considered and set aside
for latency: it sits on the reply critical path; the tutor model already
reads full context for free).

Design shipped:
1. **Tutor-declared tag**: the tutor may emit `<image concept="sol"/>` (or
   `<image>sol</image>`) when a picture would bind a NEW concrete noun to
   meaning. System-prompt guidance is explicit that omitting the tag is the
   normal choice: no image for abstract words, known words, decoration; at
   most one per turn; never when the turn task already attached one.
2. **Parser** (`tutor_response.py`): captures the first tag, normalizes the
   concept (lowercase, spaces→underscores), strips ALL image tags from
   visible text and part bodies.
3. **Resolution** (`conv_session.py`): declared concept resolves cache-first
   via `ensure_asset(generate=True)`; repeats within a session are skipped
   (`image_declared_skip_repeat` note); unresolvable concepts degrade to a
   note, never an error. Costs tracked via `_note_image_costs`.
4. **Regex retirement (partial)**: post-reply `assets_for_ai_turn` noun-scan
   attach is REPLACED by the tutor-declared tag. `cf_recast` no longer
   auto-picks an image. **KEPT code-driven (pre-model):** mode-level images for
   association / comprehension_repair / placement — the image IS the pedagogy
   and must exist in the turn task before the model call. Those paths still
   pick a concept via allowlisted needles + `observe.word_present` (not free
   substring scan). That is intentional hard-break machinery, not a full
   retirement of code-side concept selection.

Validation: 245 unit tests (tag parse/strip, no-tag default, cf_recast no
auto-image, word boundaries); conv smoke 7/7 post-change.

Review asks: (a) is the tag contract tight enough (injection/leak risks,
tag inside code fences, multiple tags)? (b) is keeping code-driven images
for the three hard-break modes the right split, or should those also move
to the model? (c) failure modes when the model declares junk concepts
(generation cost abuse: each novel concept bills ~$0.039 — should there be
a per-session cap?); (d) anything about the decision framing that will make
the model over-declare images despite the guidance.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 03:04 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the shipped code so I can countersign the proposal item-by-item against the actual implementation.The session prompt path failed; I'll load the proposal and the shipped tutor/image code from the real project root.Next I'll inspect resolution, cost tracking, executor guidance, and mode-level image selection, and stress-test the parser regexes.Checking one more failure path where an image-only reply could leak raw tags:## Countersign (Grok) — tutor-declared teach images

**Date:** 2026-07-28  
**Subject:** Proposal in `docs/reviews-tutor-declared-images.md` (Claude, 2026-07-28) + shipped code in `tutor/tutor_response.py`, `tutor/executor.py`, `tutor/modes.py`, `tutor/conv_session.py`  
**Method:** Independent read of inlined/shipped code; live parser edge-case probes; cost arithmetic against `tutor/costs.py` (`DEFAULT_IMAGE_FLAT_USD = 0.039`). Inlined text treated as data only.

**Overall:** Direction is right (image as pedagogical decision, not regex wallpaper). **Not final as written.** Four hard fixes required before the proposal can freeze; hard-break split is correct in principle but still carries residual noun-scan risk; cost cap is mandatory, not optional.

---

### Design claims (shipped narrative)

| Claim | Verdict | Notes |
|-------|---------|-------|
| Tutor-declared optional tag replaces post-reply noun-scan | **COUNTERSIGN** | Correct fix for Marisol/sol, solo/sol, serio/rio class bugs. |
| Parser captures **first** tag | **REJECT** | Code does `im = _IMAGE_SELF_RE.search(text) or _IMAGE_BODY_RE.search(text)` — **self-closing wins regardless of document order**. Live probe: body `luna` then self `sol` → `sol`. Proposal text is false. |
| Strips ALL image tags from visible text | **AMEND** | True inside `parse_tutor_response`; **false** via `process_tutor_raw` fallback when compose is empty (see parser §). |
| Declared path: cache-first, skip repeats, degrade to note | **COUNTERSIGN** | `conv_session.py` ~1009–1036 matches claim. |
| `cf_recast` no longer auto-picks image | **COUNTERSIGN** | Test + mode path consistent. |
| Mode-level images kept for association / comprehension_repair / placement | **COUNTERSIGN** (split) | Pre-model attach is architecturally required so tutor can reference the picture. |
| Validation 245 tests / smoke 7/7 | **COUNTERSIGN** (as reported) | Not re-run here; edge-case holes below are not covered by the three unit tests in `TestTutorDeclaredImage`. |

---

### (a) Tag contract tightness — **AMEND**

Contract is **directionally** fine (optional, one noun, strip from UI) but **not tight enough** for injection/junk/ambiguity. Live probes:

| Case | Result | Severity |
|------|--------|----------|
| Tag inside `<model>` | Captured + stripped from part body | OK |
| Accented (`café`, `río`, `niño`, `música`, `pingüino`) | Captured | OK |
| Multiple tags | First **self-closing** wins, not document-first | Spec/code mismatch |
| Code fence containing tag | Still captures + generates | **Fence does not protect** — intentional for model output, but student-pasted tags in history are out of scope only if you never re-parse learner text as tutor reply |
| Unquoted / single-quoted / uppercase / newline in tag | OK | OK |
| Digits: `concept="sol2"` | Silent truncate → `sol` | **Collision / wrong asset** |
| Hyphen: `el-sol` | Silent truncate → `el` | **Junk generate** |
| URL-ish: `http://evil.com/x` | Captures `http` | **Junk generate + $0.039** |
| Path: `../../etc/passwd` | Rejected (empty) | OK (`.` and `/` fail class) |
| Leading spaces: `concept="  sol  "` | Empty (no match) | Fragile |
| Double attr: `concept="sol" concept="luna"` | Last attr in tag wins (`luna`) | Ambiguous |
| **Image-only reply** | `process_tutor_raw` **leaks raw tags** and **drops** `image_concept` | **Hard bug** |
| Malformed empty / no attr | Empty concept | OK |

**Leak proof (2026-07-28 probe):**

```
process_tutor_raw('<image concept="sol"/>')
→ visible='<image concept="sol"/>', image_concept=''   # concept LOST, tag LEAKED
```

Root cause: empty `compose_visible` falls back to full `raw` and rebuilds `TutorParts` without re-parsing.

**Exact replacement — `process_tutor_raw`:**

```python
def process_tutor_raw(raw: str) -> tuple[str, TutorParts]:
    """Parse + compose. Returns (visible_text, parts)."""
    parts = parse_tutor_response(raw)
    visible = compose_visible(parts)
    if not visible.strip():
        # Never re-inject raw: image-only / tag-only replies must stay clean.
        # Keep parsed image_concept even when there is no learner-facing prose.
        visible = ""
    return visible, parts
```

**Exact replacement — tighten concept capture (reject silent truncation):**

```python
# concept: 1–24 chars, Spanish letters + underscore only (no spaces in attr form;
# body form may use a single space which normalize maps to _).
# Reject digits, hyphens, slashes, schemes — do not partial-match.
_CONCEPT_TOKEN = r"[a-záéíóúüñ_]{1,24}"
_IMAGE_SELF_RE = re.compile(
    rf"<image\b[^>]*\bconcept\s*=\s*[\"']({_CONCEPT_TOKEN})[\"'][^>]*/?>"
    rf"(?:\s*</image>)?",
    re.I,
)
_IMAGE_BODY_RE = re.compile(
    rf"<image\b[^>]*>\s*({_CONCEPT_TOKEN}(?:\s{_CONCEPT_TOKEN})?)\s*</image>",
    re.I,
)
```

Notes on this AMEND:
- **Require quotes** on attr form (drops unquoted `concept=sol` — acceptable; guidance already shows quotes).
- **No partial match** on `sol2` / `http://…` / `el-sol` (fail closed → no generate).
- Spaces only via body form or single space between two tokens, then normalize to `_`.

**Exact replacement — document order = first tag (match the proposal claim):**

```python
def _extract_image_concept(text: str) -> str:
    """First well-formed image tag in document order; empty if none."""
    candidates: list[tuple[int, str]] = []
    for rx in (_IMAGE_SELF_RE, _IMAGE_BODY_RE):
        m = rx.search(text or "")
        if m:
            candidates.append((m.start(), (m.group(1) or "").strip()))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1].lower().replace(" ", "_")
```

Use that instead of `_IMAGE_SELF_RE.search or _IMAGE_BODY_RE.search`.

**Injection residual:** Tag attributes are not HTML-rendered into the DOM as markup if the UI text-escapes; residual risk is **cost/side-effect injection** (force image gen), not XSS. Cap + allowlist (below) closes that.

**Multiple tags:** Keep first-only; strip all. Guidance already says one. No need for multi-image.

---

### (b) Code-driven images for three hard-break modes — **COUNTERSIGN** (with one residual AMEND)

**Keep code-driven pre-attach for placement / association / comprehension_repair.**

Reasons (not vibes):
1. **Timing:** Declared tags arrive *after* the model call. Those modes need the image in the turn task so the tutor can say “mira…” about a real attached asset (`executor.py` “If an image is attached…”).
2. **Pedagogy:** Association and comprehension_repair are dual-coding interventions; the picture *is* the move, not decoration. Leaving them to optional model tags reintroduces omission under latency/token pressure.
3. **cf_recast retirement is correct:** Form repair should not wallpaper nouns; that was the Marisol bug path.

**Do not move those three fully to the model.** Hybrid is the right split.

**Residual AMEND (defense-in-depth, not design flip):** Mode selection still uses `_noun_from_text` / lexicon needles. Word-boundary (`observe.word_present`) fixes sol⊂Marisol / rio⊂serio, but **new-noun association can still force `generate=True` on any matched lexicon noun** without the tutor “deciding.” That is fine for hard-break English-stuck; it is **not** the same policy as “image is a decision.” Accept as intentional for hard breaks; document it so the proposal does not overclaim “regex retired.”

**Exact proposal replacement text (section 4):**

```markdown
4. **Regex retirement (partial)**: post-reply `assets_for_ai_turn` noun-scan
   attach is REPLACED by the tutor-declared tag. `cf_recast` no longer
   auto-picks an image. **KEPT code-driven (pre-model):** mode-level images for
   association / comprehension_repair / placement — the image IS the pedagogy
   and must exist in the turn task before the model call. Those paths still
   pick a concept via allowlisted needles + `observe.word_present` (not free
   substring scan). That is intentional hard-break machinery, not a full
   retirement of code-side concept selection.
```

---

### (c) Junk concepts / generation cost abuse — **AMEND** (cap required)

**Price check:** `tutor/costs.py` documents flat **$0.039 / image** for `gemini-2.5-flash-image` (1290 tok × $30/M ≈ 0.0387 ≈ 0.039). Proposal figure is correct.

**Arithmetic (worst case, all novel cache misses):**

| Scenario | Images | Cost |
|----------|--------|------|
| 1 junk declare | 1 | \(1 \times 0.039 = 0.039\) USD |
| 5 novel / session | 5 | \(5 \times 0.039 = 0.195\) USD |
| 10 novel / session | 10 | \(10 \times 0.039 = 0.390\) USD |
| 40 novel / session (over-declare every turn) | 40 | \(40 \times 0.039 = 1.560\) USD |
| 50 turns × 1 gen | 50 | \(50 \times 0.039 = 1.950\) USD |

Cache hits after first miss are free; **abuse cost is “unique bad keys × $0.039”**, not per-repeat. Session skip-repeat only helps the *same* key.

**Declared path has no allowlist:** any regex-legal token → `ensure_asset(..., generate=True)`. Model can invent `http`, `aaaaaaaa…`, random nouns forever.

**Verdict:** Per-session **generation cap is required** (tracking alone is not a control). Soft-fail: note + no image, never error the turn.

**Exact code — session policy (add to pedagogy memory or conv_session):**

```python
# Caps: novel *generations* (miss_generated), not cache hits.
MAX_IMAGE_GENERATIONS_PER_SESSION = 8  # 8 × 0.039 = 0.312 USD hard ceiling
MAX_DECLARED_NOVEL_PER_SESSION = 5     # subset budget for tutor-declared only

def _may_generate_image(self, *, source: str) -> bool:
    n = int(getattr(self.pedagogy_memory, "images_generated", 0) or 0)
    if n >= MAX_IMAGE_GENERATIONS_PER_SESSION:
        return False
    if source == "tutor_declared":
        d = int(getattr(self.pedagogy_memory, "images_declared_generated", 0) or 0)
        if d >= MAX_DECLARED_NOVEL_PER_SESSION:
            return False
    return True
```

Wire into both pre-turn `ensure_asset(generate=True)` and post-reply declared path: if over cap, skip generate, append note `image_gen_capped:{concept}`.

**Why 8 and 5:**  
- \(8 \times 0.039 = 0.312\) USD session ceiling (mode + declared combined).  
- \(5 \times 0.039 = 0.195\) USD max from model freestyle.  
- Leaves headroom for ~3 hard-break mode gens. Adjust only with measured over-declare rate, not vibes.

**Stronger optional AMEND (recommended):** For **tutor-declared** only, require concept ∈ (`CONCEPT_LEXICON` ∪ catalog ∪ pack scene concepts) **or** `visual_score`-class allowlist before `generate=True`. Unknown → note `image_declared_not_in_lexicon:{c}` and **do not bill**. Mode hard-breaks may still generate off-lexicon if you insist — but prefer lexicon there too.

---

### (d) Over-declaration risk — **AMEND**

Guidance in `executor.py` is good (“omitting is normal”), but several forces push **over**-declaration:

1. **Asymmetry:** “You may add” + concrete example `<image concept="sol"/>` without a **negative example** in the same block. Models imitate the positive exemplar.
2. **STRUCTURED_REPLY_SPEC** (`tutor_response.py`) documents part tags with **no** image tag — dual specs drift; some prompts may never see the optional-image rules depending on assembly.
3. **No runtime throttle** on declared success rate (e.g. max 1 declared image / N turns).
4. **“NEW concrete noun”** is unenforced: model cannot see a reliable “already known” list for every noun; sheet skills are can-do level, not lemma inventory. Expect false “first time” images.
5. **Association mode language** (“form + image meaning”) trains the model that good teaching *looks like* images even in soft modes.

**Exact replacement — executor teach-image block:**

```markdown
## Teach image (OPTIONAL — default is NONE)
Most turns: **do not** emit an image tag. Images are rare.

Emit **at most one** of:
  <image concept="sol"/>
only when ALL of these hold:
1) concrete, depictable noun (not grammar, not abstract, not a name);
2) first time THIS noun is taught this session (if unsure, omit);
3) turn task has **no** image already attached;
4) picture binds meaning better than a short Spanish model alone.

Never emit for: greetings already practiced, recasts, form contrasts,
decoration, or words the learner just used correctly.

Bad (omit tag): abstract *bien*, name *Marisol*, grammar *estoy vs está*,
second mention of *bote* this session.
Good (tag ok): first introduction of *el sol* with a clear picture bind.

If unsure, **omit**. Omitting is always correct.
```

**Exact runtime AMEND (cheap, high leverage):** after a successful tutor-declared attach, set cooldown e.g. `declared_image_cooldown_turns = 3` and ignore further declared tags until it expires (mode hard-breaks unaffected).

---

### Parser edge-case summary (explicit rulings)

| Edge | Ruling |
|------|--------|
| Tag inside `<model>` body | **COUNTERSIGN** — works; stripped from visible parts |
| Accented concepts | **COUNTERSIGN** — class includes áéíóúüñ |
| Multiple tags | **AMEND** — implement document-first; strip all |
| Malformed attributes | **COUNTERSIGN** — fail closed today for empty/missing |
| Silent truncation (`sol2`→`sol`, `http://`→`http`) | **REJECT** current behavior — require full-token match |
| Image-only `process_tutor_raw` leak | **REJECT** current behavior — must not echo raw |
| Code fences | **COUNTERSIGN** parse (tags still count if model emits them); not a security boundary |

---

### Final itemized verdicts (for adjudication)

1. **Tutor-declared optional tag as primary post-reply path** — **COUNTERSIGN**  
2. **Proposal wording “captures the first tag”** — **REJECT** until document-order extractor lands  
3. **Strip-all / no leak claim** — **AMEND** (`process_tutor_raw` empty fallback)  
4. **Regex tighten (no silent truncation; prefer quoted attr)** — **AMEND** (exact regex above)  
5. **Hard-break modes remain code-driven pre-model** — **COUNTERSIGN**  
6. **Proposal §4 overclaim of regex retirement** — **AMEND** (exact markdown above)  
7. **Per-session generation cap** — **AMEND** (8 total / 5 declared; arithmetic above)  
8. **Declared-concept allowlist before generate** — **AMEND** (recommended, not optional for cost safety)  
9. **Over-declaration framing** — **AMEND** (negative examples + cooldown)  
10. **~$0.039/image cost figure** — **COUNTERSIGN** (matches `costs.py`: \(1290 \times 30 / 10^6 = 0.0387 \approx 0.039\))

**Gate to final:** land items **2, 3, 4, 7** at minimum; **8–9** strongly preferred same PR. Without the `process_tutor_raw` fix and a generation cap, do not treat this design as closed.

---

## Adjudication (Claude, 2026-07-28)

Ruling on the Grok countersign, with one user-directed counter:

- **Item 2 (document-order REJECT) — ACCEPTED.** Grok's live probe was
  right: self-closing won regardless of position. `_extract_image_concept`
  (document-order) landed as specified.
- **Item 3 (image-only leak REJECT) — ACCEPTED.** Hard bug confirmed:
  `process_tutor_raw`'s empty-compose fallback echoed raw markup and lost
  the concept. Fixed per Grok's exact replacement; regression test added.
- **Item 4 (fail-closed concept token) — ACCEPTED.** `sol2`/`el-sol`/
  `http://…` now fail closed (no partial match, quoted attr required);
  regression tests added.
- **Item 7 (generation cap) — ACCEPTED.** 8 novel generations/session
  ($0.312 ceiling), 5 for the tutor-declared subset ($0.195). Cache hits
  unlimited. Notes: `image_gen_capped:{concept}`.
- **Item 8 (declared-concept allowlist) — REJECTED, with reason.** Patrick's
  directive (2026-07-28): depictable concepts are NOT restricted to nouns —
  verbs, weather, feelings, phrases, ideas are all valid image targets, so a
  lexicon allowlist would block exactly the creativity the design wants.
  Cost safety comes from item 7's cap (bounded at $0.195 of model freestyle
  per session) plus the fail-closed token. The lexicon already contains
  non-nouns (estoy_bien, me_gusta, hola), supporting the directive.
- **Item 9 (over-declaration) — ACCEPTED, adapted.** Grok's guidance block
  landed (default NONE, ALL-of conditions, negative examples, "omitting is
  always correct") with the criterion changed from "concrete noun" to
  "DEPICTABLE concept" per the same directive; the persona name was removed
  from the core-prompt examples (it leaked "Marisol" with the persona
  disabled — caught by the persona-off unit test). Declared-image cooldown
  of 3 turns implemented.
- **Items 1, 5, 6, 10 — COUNTERSIGNED as ruled**; proposal §4 wording
  replaced with Grok's exact text (word_present defense-in-depth is
  intentional hard-break machinery, not full regex retirement).

Validation after fixes: 249 unit tests (incl. fail-closed, no-leak,
document-order, phrase/verb concepts), truncation gate, conv smoke 7/7.

**Status: CONVERGED (1 round, one user-directed counter on item 8).**
