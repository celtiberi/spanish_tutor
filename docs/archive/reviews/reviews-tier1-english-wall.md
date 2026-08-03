

---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-26 21:01 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the gate/test sources so I can operationalize `english_wall` against the adjudicated spec without deferring to the inlined draft.Next I'll pull the full gate implementation, its tests, and the rest of the prompt (including the truncated middle).I'll check call sites and research notes so the ratio helper and wall thresholds match the adjudicated spec.Checking one more edge: whether `is_open` is relied on for English framing in tests or session code.## Grok collab — Tier-1 item 2: `english_wall` operationalization  
**Date:** 2026-07-26  
**Subject:** `tutor/output_gate.py` + `tests/test_output_gate.py`  
**Role:** independent implementer/reviewer (no repo write; draft only)

---

### 1. Independent read of current code vs adjudicated spec

Current wall (as of commit trail ending `c6a20ac` on branch `main`):

- `tutor_spanish_ratio`: closed lexicons `_ES_RE` / `_EN_RE`; returns `None` if `es+en < 3`.
- Critical when `ratio is not None and ratio < min_r`, with `min_r = 0.15` if `is_open` else **`0.35`**.
- No alphabetic-length floor, no `<explain>` sandwich exemption, no always-on `tl_ratio=…` note.

Adjudicated Tier-1 #2 (`docs/reviews-pedagogy-research.md` §4 / R2-#2):

1. Critical **iff** Spanish ratio **&lt; 0.50** **and** learner-facing blob has **≥ 12** alphabetic tokens.  
2. Exempt sandwich: English inside `explain` excluded from the ratio when explain has **≤ 6 English words**.  
3. Pure helper `spanish_token_ratio(text) -> float`; record **`tl_ratio=0.xx` every turn**; no session aggregation here.

**Arithmetic on the threshold change (do not paper over):**

- Old non-open critical band: \(r < 0.35\).  
- New critical band: \(r < 0.50\) and \(N_{\alpha} \ge 12\).  
- Turns with \(r \in [0.35, 0.50)\) and \(N_{\alpha} \ge 12\) **pass today, fail under the new rule**.  
  Example: \(es=4\), \(en=6\) → \(r = 4/(4+6) = 0.40\).  
  Old: \(0.40 \ge 0.35\) → no wall. New: \(0.40 < 0.50\) and \(N_{\alpha}\ge 12\) → wall.  
- Short English: \(r=0.0\), \(N_{\alpha}=6\) → new rule **does not** trip (length floor). Old could trip if \(es+en \ge 3\).

I am **not** preserving `MIN_SPANISH_RATIO = 0.35` / `MIN_SPANISH_RATIO_OPEN = 0.15` for criticality. That would violate the adjudication. “Preserve all existing fault behavior otherwise” is read as: do not touch sheet_leak / probe_loop / pedagogy / form_focus / etc.

---

### 2. Spec ambiguities (must flag; not silent invention)

| # | Ambiguity | Ruling used in draft | Why / risk |
|---|-----------|----------------------|------------|
| A | **What is a “Spanish token”?** Spec says “Spanish token ratio” but code only knows a tiny closed list. Unlisted Spanish (e.g. *tenemos*, *mañana* is listed, *queremos* is not) does not raise \(r\); unlisted English (*coffee*, *hot*, *outside*) does not lower \(r\). | Keep closed-list \(es/(es+en)\) for the ratio numerator/denominator so behavior stays unit-testable and compatible with existing fixtures. | **Residual false pass:** long English prose outside `_EN_RE` can sit at \(r=1.0\) after empty lexicon hits. This is a pre-existing metric hole; Tier-1 #2 does not fix tokenization. |
| B | **`spanish_token_ratio` always `float` vs current `None`.** Empty / no lexicon hits: what value? | Return **`1.0`** when \(es+en=0\) (no lexicon evidence of English wall). Gate still requires \(N_{\alpha}\ge 12\) to trip, so empty turns stay clean. | Alternative \(0.0\) would false-positive any long out-of-lexicon Spanish. Documented choice. |
| C | **“English words” for ≤6 gloss.** Lexicon hits only vs all alphabetic tokens in `explain`? | **Eligibility:** count alphabetic tokens in `explain` that are **not** matched by `_ES_RE` (English-ish / non-Spanish tokens), cap ≤6. **Effect:** when eligible, strip `_EN_RE` matches *inside explain only* from the ratio text (and also strip those non-ES alpha tokens from the ratio blob so out-of-list gloss words do not… wait they never hit ratio). Actually for ratio, only EN_RE matters. Eligibility uses non-ES alpha ≤6 so pure L1 gloss “means it's hot outside” (hot/outside unlisted) still qualifies as short gloss. | If eligibility used only `_EN_RE`, a 5-word gloss with 1 list hit would still be “short” by A3 word count; using non-ES alpha aligns with “≤6 words” A3. If explain is Spanish metalanguage (“significa calor”), non-ES count is low and ES still counts in ratio — correct. |
| D | **Tagged sandwich:** only `parts["explain"]` or also literal `<explain>…</explain>` in `visible`/`raw`? | Gate already ratios **structured parts**; exemption applies to `parts["explain"]` only. If model dumps English only in `visible` without filling `explain`, no exemption. | Matches current gate blob construction. |
| E | **`is_open` English frame (`MIN_SPANISH_RATIO_OPEN = 0.15`).** Spec is silent. | **Drop open-specific threshold.** Criticality is only \(r < 0.50 \land N_{\alpha} \ge 12\). Short placement frames (\(N_{\alpha} < 12\)) never trip; **long** English opens **will** trip. | Product risk for placement monologues; length floor softens short frames. Keep constants as documentation aliases if desired, but do not branch criticality on `is_open`. |
| F | **`tl_ratio` = raw or post-exemption ratio?** | Record **post-exemption** ratio (same value used for the wall and `OutputGateResult.spanish_ratio`). | Session telemetry of “true TL exposure” may want raw later; out of scope. |
| G | **Alphabetic token definition.** | `[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+` (Spanish-aware letters). Digits/punctuation do not count. | “job” counts; “¡Hola!” → `Hola`. |
| H | **Rename vs keep `tutor_spanish_ratio`.** Spec requires `spanish_token_ratio`. | New pure helper is canonical; `tutor_spanish_ratio` remains a thin legacy wrapper (`None` if \(es+en < 3\)) so existing unit tests that import it keep working until callers migrate. | Gate uses `spanish_token_ratio` only. |

**Contrarian note:** shipping this without fixing (A) means “operationalized” is **adjudicable** but still **weak as immersion science**. ACTFL-style 90% is session-level and needs real tokenization; this item correctly refuses session aggregation, but the per-turn metric remains lexicon-toy. Accept as Tier-1 instrumentation, not as a validity claim.

---

### 3. Draft replacement code (`tutor/output_gate.py`)

Replace constants + ratio helpers + the english_wall block inside `check_output_gate`. Leave sheet_leak / pedagogy / probe_loop / repair text as-is.

```python
# --- constants (replace MIN_SPANISH_RATIO* block) ---

# Adjudicated turn-level wall (2026-07-26 Tier-1 #2):
# critical iff spanish_token_ratio < MIN_SPANISH_RATIO and alphabetic tokens >= MIN_ALPHA_TOKENS.
MIN_SPANISH_RATIO = 0.50
MIN_ALPHA_TOKENS = 12
# Short L1 sandwich in <explain>: exclude English from ratio when explain has
# at most this many non-Spanish alphabetic tokens (A3 "≤6 words" gloss).
MAX_EXPLAIN_GLOSS_WORDS = 6

# Legacy names kept for grep/docs; criticality no longer uses open-specific min.
MIN_SPANISH_RATIO_OPEN = MIN_SPANISH_RATIO  # was 0.15; open uses same rule + length floor

_ALPHA_TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")


def _strip_md_noise(text: str) -> str:
    return re.sub(r"[*_`#]+", " ", text or "")


def alphabetic_tokens(text: str) -> list[str]:
    """Learner-facing alphabetic tokens (Spanish-aware letters)."""
    return _ALPHA_TOKEN_RE.findall(text or "")


def alphabetic_token_count(text: str) -> int:
    return len(alphabetic_tokens(text))


def spanish_token_ratio(text: str) -> float:
    """Fraction of (es+en) closed-lexicon hits that look Spanish.

    Always returns float in [0, 1]. When there are no lexicon hits, returns 1.0
    (no evidence of English wall from the lists). Pure: no I/O, no mutation.
    """
    t = _strip_md_noise(text)
    es = len(_ES_RE.findall(t))
    en = len(_EN_RE.findall(t))
    if es + en == 0:
        return 1.0
    return es / (es + en)


def tutor_spanish_ratio(text: str) -> float | None:
    """Legacy helper: same ratio, but None if fewer than 3 lexicon hits."""
    t = _strip_md_noise(text)
    es = len(_ES_RE.findall(t))
    en = len(_EN_RE.findall(t))
    if es + en < 3:
        return None
    return es / (es + en)


def _is_spanish_lexicon_token(tok: str) -> bool:
    return bool(_ES_RE.search(tok))


def explain_gloss_word_count(explain: str) -> int:
    """Non-Spanish alphabetic tokens in explain (short L1 gloss budget)."""
    n = 0
    for tok in alphabetic_tokens(explain):
        if not _is_spanish_lexicon_token(tok):
            n += 1
    return n


def _strip_en_lexicon(text: str) -> str:
    """Remove closed-list English hits so they do not affect spanish_token_ratio."""
    return _EN_RE.sub(" ", text or "")


def learner_facing_blob(parts: dict | None, visible: str) -> str:
    """Same composition the gate already used for the wall."""
    parts = parts or {}
    blob = " ".join(
        str(parts.get(k) or "")
        for k in ("acknowledge", "recast", "explain", "model", "try", "continue")
    )
    if not blob.strip():
        blob = visible or ""
    return blob


def ratio_blob_with_sandwich_exempt(parts: dict | None, visible: str) -> str:
    """Learner-facing text for ratio; short <explain> L1 gloss English stripped."""
    parts = parts or {}
    explain = str(parts.get("explain") or "")
    exempt = bool(explain.strip()) and explain_gloss_word_count(explain) <= MAX_EXPLAIN_GLOSS_WORDS
    chunks: list[str] = []
    for k in ("acknowledge", "recast", "explain", "model", "try", "continue"):
        piece = str(parts.get(k) or "")
        if k == "explain" and exempt:
            piece = _strip_en_lexicon(piece)
        chunks.append(piece)
    blob = " ".join(chunks)
    if not blob.strip():
        # visible has no structured explain tag for exemption
        blob = visible or ""
    return blob


# --- inside check_output_gate, REPLACE the english_wall block only ---
# (keep everything above probe_loop unchanged)

    # English wall on learner-facing text (model+try+ack+recast+explain)
    # Spec 2026-07-26: critical iff ratio < 0.50 AND >= 12 alphabetic tokens;
    # short L1 sandwich in explain excluded from ratio when <= 6 non-ES words.
    full_blob = learner_facing_blob(parts, visible)
    ratio_blob = ratio_blob_with_sandwich_exempt(parts, visible)
    ratio = spanish_token_ratio(ratio_blob)
    n_alpha = alphabetic_token_count(full_blob)
    notes.append(f"tl_ratio={ratio:.2f}")
    if n_alpha >= MIN_ALPHA_TOKENS and ratio < MIN_SPANISH_RATIO:
        faults.append("gate:english_wall")
        notes.append(
            f"gate:english_wall ratio={ratio:.2f}<{MIN_SPANISH_RATIO}"
        )

# --- return OutputGateResult: keep spanish_ratio=ratio (post-exemption) ---
```

`repair_user_message` and other faults: **unchanged**.

---

### 4. Draft tests (add/replace in `tests/test_output_gate.py`)

```python
"""Output gate + hard observer (no live API)."""

import re
import unittest

from tutor.character_sheet import default_sheet, process_turn
from tutor.output_gate import (
    MIN_ALPHA_TOKENS,
    MIN_SPANISH_RATIO,
    alphabetic_token_count,
    check_output_gate,
    detect_sheet_leak,
    detect_tutor_probe_keys,
    spanish_token_ratio,
    tutor_spanish_ratio,
)


class TestOutputGate(unittest.TestCase):
    def test_spanish_ratio_high(self):
        r = tutor_spanish_ratio("¡Hola! Estoy bien. ¿Cómo estás hoy?")
        self.assertIsNotNone(r)
        self.assertGreaterEqual(r, 0.5)

    def test_spanish_ratio_english_wall(self):
        r = tutor_spanish_ratio(
            "Good job! That means how are you. Please try to say the word hello."
        )
        self.assertIsNotNone(r)
        self.assertLess(r, 0.35)

    def test_spanish_token_ratio_always_float(self):
        self.assertIsInstance(spanish_token_ratio(""), float)
        self.assertEqual(spanish_token_ratio(""), 1.0)
        r = spanish_token_ratio(
            "Good job! That means how are you. Please try to say the word hello."
        )
        self.assertLess(r, 0.50)

    def test_probe_keys(self):
        k = detect_tutor_probe_keys("¿Cómo te llamas?")
        self.assertIn("ask_name", k)

    def test_gate_ok_spanish_teach(self):
        parts = {
            "acknowledge": "¡Qué bien!",
            "model": "Me llamo Sofía.",
            "try": "¿Y tú? ¿Cómo te llamas?",
            "structured": True,
        }
        g = check_output_gate(
            parts,
            "¡Qué bien! Me llamo Sofía. ¿Cómo te llamas?",
            is_open=False,
            already_asked=set(),
            already_shown=set(),
        )
        self.assertTrue(g.ok, g.faults)
        self.assertTrue(
            any(n.startswith("tl_ratio=") for n in g.notes),
            g.notes,
        )

    def test_gate_loop_reask_name(self):
        parts = {
            "acknowledge": "¡Hola!",
            "model": "Me llamo Sofía.",
            "try": "¿Cómo te llamas?",
            "structured": True,
        }
        g = check_output_gate(
            parts,
            "¿Cómo te llamas?",
            already_asked={"ask_name"},
            already_shown={"name"},
        )
        self.assertFalse(g.ok)
        self.assertIn("gate:probe_loop", g.faults)

    def test_gate_english_wall_long_mostly_english_trips(self):
        """Long mostly-English turn: ratio < 0.50 and alpha >= 12 → critical."""
        parts = {
            "acknowledge": "Good job you nailed it!",
            "model": "That means my name is.",
            "try": "Please say your name in Spanish now.",
            "structured": True,
        }
        blob = " ".join(
            str(parts.get(k) or "")
            for k in ("acknowledge", "recast", "explain", "model", "try", "continue")
        )
        # Arithmetic check baked into the fixture:
        # closed-list ratio → 0.0; alphabetic tokens → 17 >= 12.
        self.assertEqual(spanish_token_ratio(blob), 0.0)
        self.assertGreaterEqual(alphabetic_token_count(blob), MIN_ALPHA_TOKENS)
        g = check_output_gate(parts, "Good job...", is_open=False)
        self.assertFalse(g.ok)
        self.assertIn("gate:english_wall", g.faults)
        self.assertTrue(any(n.startswith("tl_ratio=") for n in g.notes), g.notes)
        self.assertIsNotNone(g.spanish_ratio)
        self.assertLess(g.spanish_ratio, MIN_SPANISH_RATIO)

    # keep old name as alias so renames in CI stay obvious
    def test_gate_english_wall(self):
        self.test_gate_english_wall_long_mostly_english_trips()

    def test_gate_english_wall_short_mostly_english_no_trip(self):
        """Short mostly-English: ratio may be 0 but alpha < 12 → never wall."""
        parts = {
            "acknowledge": "Good job!",
            "model": "Try this.",
            "try": "Say it.",
            "structured": True,
        }
        blob = " ".join(
            str(parts.get(k) or "")
            for k in ("acknowledge", "recast", "explain", "model", "try", "continue")
        )
        # Good job Try this Say it → 6 alphabetic tokens; ratio 0.0 on lexicon hits.
        n = alphabetic_token_count(blob)
        self.assertLess(n, MIN_ALPHA_TOKENS)  # 6 < 12
        self.assertEqual(spanish_token_ratio(blob), 0.0)
        g = check_output_gate(parts, blob, is_open=False)
        self.assertNotIn("gate:english_wall", g.faults)
        self.assertTrue(any(n.startswith("tl_ratio=") for n in g.notes), g.notes)
        # still a teach move (model+try) so wall absence is the claim under test
        self.assertTrue(
            g.ok or "gate:english_wall" not in g.faults,
            g.faults,
        )

    def test_gate_sandwich_gloss_exempt(self):
        """Short <explain> L1 gloss excluded from ratio → no english_wall.

        Body (lexicon):
          es: Hola, estoy, bien, gracias, amigo, Qué, te, gusta  → 8
          en: The, and, you, are, how                           → 5
          r_body = 8/(8+5) = 8/13 ≈ 0.6154  (>= 0.50)
        Explain (5 non-ES words, all EN-list): means you the word phrase
          without exemption: en=5+5=10 → r = 8/18 ≈ 0.4444 (< 0.50) would trip
          with exemption: en stays 5 → r = 8/13 ≈ 0.6154 no trip
        Alphabetic tokens on full blob = 18 >= 12 (length would allow a trip).
        """
        parts = {
            "acknowledge": "Hola estoy bien gracias amigo",
            "model": "The and you are how",
            "try": "Qué te gusta",
            "explain": "means you the word phrase",
            "structured": True,
        }
        full = " ".join(
            str(parts.get(k) or "")
            for k in ("acknowledge", "recast", "explain", "model", "try", "continue")
        )
        self.assertGreaterEqual(alphabetic_token_count(full), MIN_ALPHA_TOKENS)
        # Without exemption this fixture is under 0.50:
        r_raw = spanish_token_ratio(full)
        self.assertLess(r_raw, MIN_SPANISH_RATIO)  # 8/18 ≈ 0.444
        # 8/13 ≈ 0.615
        self.assertAlmostEqual(8 / 13, 0.6153846153846154, places=6)
        self.assertAlmostEqual(8 / 18, 0.4444444444444444, places=6)

        g = check_output_gate(parts, full, is_open=False)
        self.assertNotIn("gate:english_wall", g.faults)
        self.assertIsNotNone(g.spanish_ratio)
        self.assertGreaterEqual(g.spanish_ratio, MIN_SPANISH_RATIO)
        # note always present
        ratio_notes = [n for n in g.notes if n.startswith("tl_ratio=")]
        self.assertEqual(len(ratio_notes), 1)
        self.assertRegex(ratio_notes[0], r"tl_ratio=0\.\d{2}")

    def test_gate_long_explain_not_exempt(self):
        """Explain with >6 non-ES words counts fully toward the wall."""
        parts = {
            "acknowledge": "Hola estoy bien gracias amigo",
            "model": "The and you are how",
            "try": "Qué te gusta",
            # 7+ English-ish words → no sandwich exemption
            "explain": (
                "means you the word phrase please try say the sentence "
                "with your name right now"
            ),
            "structured": True,
        }
        g = check_output_gate(parts, "x", is_open=False)
        self.assertIn("gate:english_wall", g.faults)

    def test_tl_ratio_note_always_present(self):
        parts = {
            "acknowledge": "¡Qué bien!",
            "model": "Me llamo Sofía.",
            "try": "¿Cómo te llamas?",
            "structured": True,
        }
        g = check_output_gate(parts, "hola", is_open=False)
        self.assertTrue(any(re.match(r"tl_ratio=\d+\.\d{2}$", n) for n in g.notes), g.notes)
        # empty-ish visible fallback path
        g2 = check_output_gate({}, "", is_open=False)
        self.assertTrue(any(n.startswith("tl_ratio=") for n in g2.notes), g2.notes)

    def test_gate_no_teach_move(self):
        parts = {
            "acknowledge": "¡Hola amigo!",
            "continue": "¿Todo bien?",
            "structured": True,
        }
        g = check_output_gate(parts, "¡Hola!", is_open=False)
        self.assertFalse(g.ok)

    def test_gate_sheet_leak_is_hard_fault(self):
        raw = (
            '<tutor><model>Estoy bien.</model></tutor>\n'
            '```json {"active_error_focus":[{"id":"estar_yo_estoy_vs_esta"}],'
            '"grammar":{"present_estar_person":{"confidence":0.8,"solid_uses":2}}}\n```'
        )
        self.assertTrue(detect_sheet_leak(raw))
        parts = {"model": "Estoy bien.", "structured": True}
        g = check_output_gate(parts, "Estoy bien.", raw=raw)
        self.assertFalse(g.ok)
        self.assertIn("gate:sheet_leak", g.faults)
        self.assertIn("JSON", g.repair_instruction)


class TestHardObserver(unittest.TestCase):
    def test_tool_path_still_bumps_from_learner_text(self):
        sheet = default_sheet()
        tool_delta = {
            "reason": "saw greeting",
            "skills": {
                "IP-01": {"status": "emerging", "confidence": 0.2},
            },
        }
        s, _, notes = process_turn(
            sheet,
            "Hola, estoy bien. Me llamo Patrick.",
            "¡Hola Patrick!",
            tool_delta=tool_delta,
        )
        self.assertIn("hard_observer", notes)
        self.assertIn("tool_update", notes)
        ip3 = (s.get("skills") or {}).get("IP-03") or {}
        ip4 = (s.get("skills") or {}).get("IP-04") or {}
        self.assertGreater(float(ip3.get("confidence") or 0), 0.05)
        self.assertGreater(float(ip4.get("confidence") or 0), 0.05)
        self.assertEqual(
            (s.get("identity") or {}).get("preferred_name", "").lower(),
            "patrick",
        )


if __name__ == "__main__":
    unittest.main()
```

---

### 5. Fixture arithmetic (explicit)

| Fixture | \(es\) | \(en\) | \(r = es/(es+en)\) | \(N_{\alpha}\) | Expected wall |
|---------|-------:|-------:|-------------------:|---------------:|---------------|
| Short EN teach | 0 | 4 list hits | \(0/4 = 0.00\) | 6 | **no** (\(6 < 12\)) |
| Long EN teach (existing) | 0 | 11 | \(0.00\) | 17 | **yes** (\(0 < 0.50\) and \(17 \ge 12\)) |
| Sandwich body only | 8 | 5 | \(8/13 \approx 0.6154\) | — | pass |
| Sandwich + explain raw | 8 | 10 | \(8/18 \approx 0.4444\) | 18 | would yes |
| Sandwich + exempt | 8 | 5 | \(8/13 \approx 0.6154\) | 18 | **no** |

---

### 6. Countersign

| Item | Ruling |
|------|--------|
| Critical iff \(r < 0.50 \land N_{\alpha} \ge 12\) | **COUNTERSIGN** — matches adjudication; implements with explicit constants. |
| Sandwich exemption on short `explain` | **COUNTERSIGN** with eligibility = non-Spanish alphabetic tokens ≤ 6 (see ambiguity C). |
| `spanish_token_ratio` + always `tl_ratio=` note | **COUNTERSIGN** — no session aggregation, no other fault restructure. |
| Drop `is_open` 0.15 threshold | **AMEND product behavior** — required by silent conflict with the new single threshold; length floor is the new short-open safety. If author wants open still softer, they must re-adjudicate (e.g. `is_open` → min 0.35 or disable wall). |
| Closed-list ratio as “Spanish tokens” | **ACCEPT for this PR only; REJECT as scientific TL%** — flag for a later tokenizer upgrade; do not claim ACTFL 90% from this field. |

---

### 7. Apply notes for the authoring agent

1. Patch only `tutor/output_gate.py` ratio/wall surface + `tests/test_output_gate.py`.  
2. Run: `python -m unittest tests.test_output_gate -v`.  
3. Do **not** add session aggregation, telemetry sinks, or repair-ladder work (Tier-1 #1 / Tier-2).  
4. `OutputGateResult.spanish_ratio` already exists — feed it the post-exemption ratio; consumers of `as_dict()` get the same number the note logs.  
5. Optional follow-up (out of scope): replace closed lists with a real ES/EN tagger or char-n-gram classifier; until then `tl_ratio` is **gate-lexicon ratio**, not true token TL%.

— end Grok collab draft, 2026-07-26
