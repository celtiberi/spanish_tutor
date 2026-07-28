

---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-26 19:44 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll systematically compare the system overview against the tutor source of truth.# Consistency skim: `docs/system-overview.md` (2026-07-26) vs tutor code

**Rule applied:** code is source of truth; doc is derived. Only mismatches below.  
**Code base checked:** `/Users/patrickcremin/repo/ml_teacher/tutor/*.py` (and thin web static labels where the doc names UI chrome).

---

## BUGs

### 1. Mode `comprehension_check` listed as a shipping mode, but `select_mode` never returns it

**Doc** §4.4 (lines 111–120): table includes `` `comprehension_check` `` under modes code selects.

**Code** `tutor/modes.py`:
- Enum member exists (`Mode.COMPREHENSION_CHECK`, lines 40, 29).
- Every `return ModeDecision(...)` in `select_mode` uses: `CF_RECAST`, `CONVERSATION`, `COMPREHENSION_REPAIR`, `PLACEMENT`, `FORM_FOCUS`, `ASSOCIATION`, `TRANSFER` only (lines 294–597).
- Zero returns of `Mode.COMPREHENSION_CHECK`.

**Verdict:** **BUG**  
**Fix:** Either remove `comprehension_check` from the “what ships today” mode table (keep it only as legacy PlanCard / gate residue), or implement a real guard that returns it. Gate-only contract in `output_gate.py:195–199` is not selection.

---

### 2. Output-gate fault table incomplete (missing machine names the code emits)

**Doc** §8 (lines 205–213): lists 7 faults.

**Code emits additional faults:**

| Fault | Code evidence |
|-------|----------------|
| `pedagogy:recast_without_try` | `pedagogy_contract.py:40, 201–204` → folded into gate via `evaluate_turn` / `faults.append(v)` in `output_gate.py:171–172` |
| `gate:comprehension_needs_check` | `output_gate.py:195–199` |

**Verdict:** **BUG** (missing fields / schema drift)  
**Fix:** Add both rows to §8. Note `pedagogy:recast_without_try` is a real gate fault, not only a soft note.

---

### 3. “Critical faults → one repair” is underspecified and wrong if read as “all listed faults”

**Doc** §8 (lines 215–216) + §7 step 7: critical faults trigger one rewrite; table does not mark critical vs soft.

**Code** `conv_session.py:786–815` — repair only if fault ∈:

```text
pedagogy:no_teach_move
pedagogy:open_needs_model_try
gate:english_wall
gate:form_focus_needs_model
gate:missing_recast
gate:sheet_leak
```

**Not critical (soft / notes only):**  
`gate:probe_loop`, `gate:comprehension_needs_check`, `pedagogy:recast_without_try`.

Also gated by `GATE_REPAIR` (`config.py:107–110`, default `true`) — **not** in doc §15 env table.

**Verdict:** **BUG**  
**Fix:** Split §8 into critical vs soft; document `GATE_REPAIR` (default on). Example:

```markdown
| Critical (one repair if GATE_REPAIR) | Soft (notes only) |
| ... | gate:probe_loop, gate:comprehension_needs_check, pedagogy:recast_without_try |
```

---

### 4. Hard-break budget claim is false as stated

**Doc** §4.4 (line 109): hard breaks “budgeted (≤1 per ~3 turns, not consecutive, none under time pressure).”

**Code:**

- Budget helper `_can_hard_break` (`modes.py:116–124`): block when `turns_since_hard_break < 3` **and** `hard_breaks_this_session > 0`.  
  Arithmetic: after `note_hard_break` sets `turns_since=0`, each turn starts with `tick()` (`conv_session.py:663` → `modes.py:76–77`), so `turns_since` becomes 1, then 2, then 3.  
  Allowed again when `turns_since >= 3` → **two intervening turns** for *budgeted* hard modes. Approx “~3 turns” is fine **only for modes that call `can_hard`**.

- **`comprehension_repair` ignores budget** (`modes.py:318–364`): returns `hard_break=True` with no `can_hard` check → consecutive hard breaks possible after e.g. `form_focus`.

- **`placement` ignores budget** on blank open (`modes.py:367–378`): `hard_break=True` without `can_hard`.

- Time pressure: only `energy == "limited_time"` (`modes.py:291–305`) — not a generic “time pressure” flag.

- Budgeted modes that *do* check `can_hard`: `form_focus` (456–457), english-stuck `association` (511), optional hard on new noun (548).

**Verdict:** **BUG** (wrong universal rule)  
**Fix:** Replace line 109 with something accurate, e.g.:

> Budgeted hard modes (`form_focus`, hard `association`): blocked while `turns_since_hard_break < 3` after a prior hard break. **`comprehension_repair` and blank `placement` bypass the budget.** Time pressure = sheet `affect.energy == "limited_time"` only (forces chat / soft `cf_recast`).

---

### 5. Turn pipeline order / steps incomplete

**Doc** §7 (lines 185–195): ordered 1…11; teach image only pre-AI; focus **after** log.

**Code** `_execute_ai_tutor` + `_finish` actual order:

1. `mode_state.tick()`  
2. `build_observations`  
3. `select_mode`  
4. Pre-AI teach image (`ensure_asset` / `assets_for_ai_turn`)  
5. Build system + task  
6. `tutor_turn`  
7. `process_tutor_raw` **for gate** (`conv_session.py:775–785`)  
8. Optional one repair + re-gate  
9. `_finish`: `process_tutor_raw` again → `process_turn` → **schedule focus** (`517–522`)  
10. **Optional post-tutor teach image** if still empty and models present (`904–917`)  
11. Mode-state bookkeeping  
12. **Log** (`990–995`)

Mismatches:

| Doc claim | Reality |
|-----------|---------|
| process_tutor_raw only after repair (step 8) | Also runs **before** gate/repair |
| Teach image only step 3 | Second pass **after** tutor reply (`904–917`) |
| Focus after Log (10→11) | Focus scheduled in `_finish` **before** log |

**Verdict:** **BUG**  
**Fix:** Rewrite §7 to match `_execute_ai_tutor` / `_finish`, including pre- and post-model image paths and focus-before-log.

---

### 6. Character sheet field list missing durable keys the code always has

**Doc** §5 (lines 136–144): identity, skills, grammar, error_patterns, lexicon, affect, next_best, coverage.

**Code** `default_sheet()` (`character_sheet.py:321–356`) also includes:

- `version`, `framework`  
- **`receptive`** (`needs_english_scaffold`, etc.) — also exposed in `sheet_public` (`conv_session.py` return includes `"receptive"`)  
- identity also has **`goals`** (not only preferred_name / L1 / engagement_notes)

**Verdict:** **BUG** (missing fields)  
**Fix:** Add `receptive` (and optionally `version` / `framework` / `goals`) to the §5 table so the overview matches the sheet schema.

---

### 7. Env / model config: `MODEL` as tutor knob is misleading

**Doc** §11 (line 246): Config `TUTOR_MODEL` / `MODEL`.

**Code** `config.py:64`:  
`MODEL = os.environ.get("TUTOR_MODEL", "gemini-3.6-flash")`  

There is **no** `os.environ.get("MODEL", …)` for the tutor. `MODEL` is the Python constant only.

**Verdict:** **BUG** (unsigned / wrong config name if read as env)  
**Fix:** Config column: `TUTOR_MODEL` only (Python name `config.MODEL`).

---

### 8. Important env table incomplete for behavior the overview describes

**Doc** §15 omits knobs that gate documented pipeline behavior:

| Missing env | Default (code) | Why it matters |
|-------------|----------------|----------------|
| `GATE_REPAIR` | true | §7/§8 one-repair path (`config.py:107–110`) |
| `FOCUS_ASYNC` | true | §7/§19 async focus (`config.py:96–99`) |
| `FOCUS_BLOCKING` | false | latency path (`config.py:91–94`) |
| `TTS_MODEL` | `gemini-2.5-flash-preview-tts` | §11 TTS row |
| `TEACH_IMAGE_MODEL` | `gemini-2.5-flash-image` | §11 images (`image_gen.py:20–24`) |

**Verdict:** **BUG** (missing fields relative to “what ships” claims)  
**Fix:** Add these rows (or drop the behaviors from the “important” claim surface).

---

### 9. Progress score is not *only* can-do confidences

**Doc** §3 (line 53): “crude 0–100 from can-do confidences.”

**Code** `compute_progress_score` (`character_sheet.py:407–444`):

- Base: mean confidence over **11** tracked can-dos  
  `IP-01…IP-08` + `IT-01`, `IT-02`, `PR-01` →  
  `score = round((total_conf / 11) * 100)`  
- **Plus** `min(5, err_bonus)` where each error pattern with `resolved_streak >= 2` adds 1.

**Verdict:** **BUG** (incomplete formula)  
**Fix:** “0–100 ≈ mean conf of 11 can-dos × 100, plus up to +5 for resolved error streaks.”

---

### 10. Sheet path claim is local-only; serverless path differs

**Doc** §5 / §14: path `logs/character_sheet.json`.

**Code** `config.py:30–42`:  
`_DATA_ROOT = ML_TEACHER_DATA_DIR` or `/tmp/ml_teacher` on Vercel/Lambda, else `REPO_ROOT/logs`.  
So sheet is `_DATA_ROOT/character_sheet.json`, not always `logs/…`.

**Verdict:** **BUG** (drift vs deploy §17)  
**Fix:** “Local default: `logs/character_sheet.json`; serverless: `/tmp/ml_teacher/character_sheet.json` (or `ML_TEACHER_DATA_DIR`).”

---

## Claims checked and **PASS** (not expanded)

Mode name set except `comprehension_check`; first-guard-wins structure; teach-move contract IDs `pedagogy:no_teach_move` / `open_needs_model_try`; XML part tags; `gate:sheet_leak` / english_wall / probe_loop / missing_recast / form_focus_needs_model; `TEACHER_MODE` default `planned`; `SHEET_TOOLS` default off; `FOCUS_MODEL` default `grok-3-mini` with `off`/`static`/`none` disabling AI; tutor default `gemini-3.6-flash`; TTS Sulafat / `gemini-2.5-flash-preview-tts`; image model `gemini-2.5-flash-image`; cache dir `tutor/web_static/teach_assets/`; port 8765; log glob `*-conversational-web.{md,jsonl}`; session seed from sheet; Reset learner keeps vs wipes sheet; no vector RAG in `corpus.py`; truncation flags; stance path `prompts/conversational_tutor.md`.

---

## Not verifiable from tutor Python alone (coverage limits)

These overview claims need other files / runtime / external services; not contradicted here, but **not proven** by tutor sources alone:

| Claim | Needs |
|-------|--------|
| Detailed break policy in `docs/teaching-system.md` | that doc |
| Pedagogy write-up `docs/pedagogy-contract.md`, persona, can-do inventory | docs/* |
| Scene JSON exit predicates “open goals” | full `course_packs/spanish_a1/scenes/*.json` semantics + `tutor/scenes.py` (partially code; scene *content* not fully audited) |
| Commit hook `.githooks/pre-commit` + `scripts/check_teacher_truncation.py` | scripts/hooks (script header seen; full hook body not fully audited) |
| Unit test inventory in §16 | `tests/*` names exist; not re-run |
| Vercel deploy constraints (`docs/vercel-deploy.md`) | deploy docs + `vercel.json` |
| Chirp readiness / ADC / GCP project | credentials + live GCP |
| Gemini image/TTS quality and real latency | live API |
| Dual-AI process (`Claude.md` / `GROK.md`) | process docs only |
| “Adult boat/café persona” product lock | `docs/product-persona.md` |
| UI “Focus now” vs “This turn” wording evolution | historical only |

---

## Summary counts

- **BUG items:** 10  
- **Highest risk if left unfixed:** mode table (`comprehension_check`), gate critical/soft split, hard-break budget overclaim, pipeline order (esp. post-model images + focus-before-log).

*End of consistency skim — append-ready.*

---

## CLAUDE (Fable 5) — Adjudication of dual-skim round 1 — 2026-07-26

**Protocol:** each Grok claim re-verified against working-tree code before ruling. No averaging.

| # | Claim | Ruling | Verification |
|---|-------|--------|--------------|
| 1 | `comprehension_check` never selected | **ACCEPT** | grep: enum only at `modes.py:40`; `can_hard`/returns confirm no selection path |
| 2 | Gate fault table missing 2 emitted faults | **ACCEPT** | `output_gate.py:198`, `pedagogy_contract.py:40` |
| 3 | Critical/soft split + `GATE_REPAIR` undocumented | **ACCEPT** | critical set at `conv_session.py:786–793`; `GATE_REPAIR` default true `config.py:107` |
| 4 | Hard-break budget bypassed by `comprehension_repair` + blank `placement` | **ACCEPT** | `can_hard` consulted only at `modes.py:456,511,548` — neither bypass mode checks it |
| 5 | §7 pipeline order wrong (double parse, post-model image, focus-before-log) | **ACCEPT** (line cites spot-checked, not exhaustively re-traced) | repair/re-gate block confirmed at `conv_session.py:812–826` |
| 6 | Sheet schema missing `receptive`/`version`/`goals` | **ACCEPT** | `character_sheet.py:323,332,338` |
| 7 | `MODEL` is not an env var | **ACCEPT** | `config.py:64` reads only `TUTOR_MODEL` |
| 8 | §15 env table missing 5 knobs | **ACCEPT** | `config.py:91–110` confirms `FOCUS_BLOCKING`/`FOCUS_ASYNC`/`GATE_REPAIR` + defaults |
| 9 | Progress score has resolved-error bonus | **ACCEPT** | `compute_progress_score` adds capped bonus beyond can-do mean |
| 10 | Sheet path varies on serverless (`_DATA_ROOT`) | **ACCEPT** | `config.py:34–42` |

**Adjudicator note on rejection rate:** 10/10 accepted. This does not indicate steering — the doc under skim is one day old and unreviewed; the round was a mismatch hunt with exact line evidence, all independently re-verified.

### Claude's independent findings (outside skim scope)

- **C1.** `tests/test_character_sheet.py` — 2 failures. Tests predate "hard observer always runs" (`character_sheet.py:1675`). Underlying design wrinkle: `_bump_status` docstring claims per-turn cap but cap is per-call; stacked bumps (+0.10 pattern, +0.25 name capture) exceed `MAX_CONF_UP_PER_TURN` net; erroneous production ("Me llama es") earns a success bump.
- **C2.** `evals/` (promotion bar) drives legacy `tutor.cli.run_turn` / `tutor.planner` (EXP-002); last touched pre-conversational-architecture (`ba7517c`). No behavioral gate exists for modes / output gate / conv_session pipeline.
- **C3.** `comprehension_repair` has zero unit-test coverage (no hits in `tests/`).

**Status:** round 1 converged on doc corrections (Grok #1–#10 accepted; edits pending). C1–C3 are code/process items, not doc edits — tracked for separate action.

---

## CLAUDE (Fable 5) — Round 1 close-out: fixes applied — 2026-07-26

- Grok #1–#10: all doc corrections applied to `docs/system-overview.md` in this change set (mode table + budget claim, gate critical/soft split + `GATE_REPAIR`, §7 pipeline order, sheet schema + serverless path, `TUTOR_MODEL` only, §15 env rows, progress-score formula). One refinement over Grok's text: `gate:comprehension_needs_check` documented as **unreachable today** (fires only under mode `comprehension_check`, which `select_mode` never returns).
- C1: implemented `_cap_turn_confidence` in `tutor/character_sheet.py` — net per-turn ceiling `max(turn_start + MAX_CONF_UP_PER_TURN, tool/AI-staged value)` applied after the hard observer in all three `process_turn` branches. Rationale: strongest-single-signal wins; stacked detectors of one utterance must not sum. Both previously failing tests now pass with their ORIGINAL expectations (0.25 / 0.5) — the tests' encoded contract was correct; the code drifted. Erroneous-but-communicative production (e.g. "Me llama es Patrick") still earns can-do credit by design (CLT: functional success; form error tracked in `error_patterns`). Design change — pending Grok countersign.
- C3: added `TestComprehensionRepair` (3 tests) to `tests/test_modes.py`: trigger + same-topic targets, hard-break-budget bypass (documents intentional behavior), no-repair-without-prior-turn.
- Suite: 188/188 pass; truncation gate ok.
- C2 (evals port): Grok drafting `evals/run_conv_smoke.py` port — round pending in `docs/reviews-evals-port.md`.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-26 20:08 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I need the full in-scope hunks and the surrounding character-sheet logic before ruling item-by-item.Checking one more edge: whether status can desync when conf is pulled down.## Countersign — character-sheet confidence ceiling (2026-07-26)

**Scope checked:** `_cap_turn_confidence`, `_bump_status` docstring, three `process_turn` call sites, `TestComprehensionRepair`, plus the deliberate CLT can-do/form split. Other diff hunks ignored.

**Independent verification (not author claims):**
- Uncapped tool + hard observer on `"Me llama es Patrick"`: IP-03 confidence \(0 \rightarrow 0.5\), solid_uses \(0 \rightarrow 2\).
- With current cap: conf ends at \(0.25\); **solid_uses still \(2\)**.
- AI full rewrite with conf \(0.9\): ends at \(0.9\) (no +0.25 honesty clamp on that path).
- Stacked success bumps from start conf \(0.50\), uses \(1\): after cap → **status `known`, conf \(0.75\), solid_uses \(4\)** — violates `KNOWN_MIN_CONF = 0.80`.

---

### Item 1 — Rationale (1): stacked observer double-counts one utterance (\(0 \rightarrow 0.5\))

**COUNTERSIGN.**

Arithmetic (tool delta conf \(0.4\), start \(0\)):
1. `apply_delta` / `_clamp_skill_entry`: \(0 + 0.25 = 0.25\), solid_uses \(+1\) → \(1\)
2. Name observer `_bump_status(..., amount=0.25)`: \(0.25 + 0.25 = 0.5\), solid_uses \(+1\) → \(2\)

Uncapped end: conf \(0.5\), uses \(2\). Cap fixes conf only. Claim holds for confidence.

---

### Item 2 — Rationale (2): “strongest-single-signal should win over summed detectors”

**AMEND** (wording / mental model).

Implementation is not max-of-detectors. It is:

\[
\text{ceiling} = \max(\text{start\_c} + \texttt{MAX\_CONF\_UP\_PER\_TURN},\ \text{staged\_c})
\]

Observer detectors still **sum**, then the sum is clipped. Only the tool/AI stage can win if it already exceeds `start + 0.25`.

**Exact docstring replacement for `_cap_turn_confidence`:**

```python
def _cap_turn_confidence(start: dict, staged: dict, final: dict) -> dict:
    """Enforce a net per-turn confidence (and solid_uses) ceiling after stacking.

    _bump_status caps a single call, but tool credit plus stacked observer
    bumps double-count one utterance (empirically conf 0→0.5 and solid_uses
    0→2). Final conf for a key may not exceed
    max(start_c + MAX_CONF_UP_PER_TURN, staged_c). Final solid_uses may not
    exceed max(start_uses + 1, staged_uses). After clipping conf, re-gate
    status so 'known' cannot remain with conf < KNOWN_MIN_CONF or uses
    < KNOWN_MIN_SOLID_USES.

    staged is the sheet after tool/AI merge and before apply_rule_updates.
    Observer-only paths pass start as staged (ceiling = start + cap only).
    """
```

---

### Item 3 — Rationale (3): tool/AI staged values keep their own clamp paths

**REJECT as stated; AMEND the claim.**

| Path | Honesty clamp before observer? | Evidence |
|------|--------------------------------|----------|
| tool_delta | Yes — `_clamp_skill_entry` (+0.25 / −0.35, known-gate) | Conf 0.4 request → staged 0.25 |
| revised_sheet (AI) | **No** — `normalize_sheet` only clamps to \([0,1]\) | Conf 0.9 request → final 0.9 |
| rules_backup | N/A (staged = start) | ceiling = start + 0.25 |

The new ceiling **preserves** AI overclaims via `max(..., staged_c)`. Saying “AI has its own clamp path” is false as of 2026-07-26.

**Exact claim replacement (for design notes / commit message):**

> Tool deltas keep `_clamp_skill_entry`. The AI full-rewrite path does **not** yet apply a per-turn honesty clamp; `_cap_turn_confidence` preserves staged AI conf as-is. Closing that gap is a separate change (run AI skills/grammar through `_clamp_skill_entry` against turn-start before staging).

Do **not** expand this PR to fix AI honesty unless you intend a behavior change vs `test_process_turn_ai_revised_sheet` (expects 0.5 from AI).

---

### Item 4 — Rationale (4): pre-existing tests at 0.25 and 0.5 still pass

**COUNTERSIGN.**

- `test_process_turn_tool_delta`: expects IP-03 \(0.25\) — matches capped tool path.
- `test_process_turn_ai_revised_sheet`: expects IP-03 \(0.5\) — matches `staged_c` preserve.
- `test_apply_delta_receptive_and_sanitize`: expects \(0.25\) — `apply_delta` only; cap not required.

---

### Item 5 — `_cap_turn_confidence` implementation

**AMEND** — conf ceiling is right; **solid_uses and status are not re-synced**.

Reproduced failure:
- start: conf \(0.50\), uses \(1\)
- three success bumps → conf \(0.95\), uses \(4\), status `known`
- after current cap → conf \(0.75\), uses \(4\), status **`known`**

But gates require conf \(\ge 0.80\) and uses \(\ge 2\). Result: **known below conf gate**.

Also on the motivating utterance: conf capped to \(0.25\) while solid_uses stays \(2\) — one utterance already meets the uses half of the known gate.

**Exact function body replacement:**

```python
def _cap_turn_confidence(start: dict, staged: dict, final: dict) -> dict:
    """Enforce a net per-turn confidence (and solid_uses) ceiling after stacking.

    _bump_status caps a single call, but tool credit plus stacked observer
    bumps double-count one utterance (empirically conf 0→0.5 and solid_uses
    0→2). Final conf for a key may not exceed
    max(start_c + MAX_CONF_UP_PER_TURN, staged_c). Final solid_uses may not
    exceed max(start_uses + 1, staged_uses). After clipping conf, re-gate
    status so 'known' cannot remain with conf < KNOWN_MIN_CONF or uses
    < KNOWN_MIN_SOLID_USES.

    staged is the sheet after tool/AI merge and before apply_rule_updates.
    Observer-only paths pass start as staged (ceiling = start + cap only).
    """
    for section in ("skills", "grammar", "lexicon"):
        fin = final.get(section)
        if not isinstance(fin, dict):
            continue
        st = start.get(section) if isinstance(start.get(section), dict) else {}
        stg = staged.get(section) if isinstance(staged.get(section), dict) else {}
        for key, entry in fin.items():
            if not isinstance(entry, dict):
                continue
            st_e = st.get(key) if isinstance(st.get(key), dict) else {}
            stg_e = stg.get(key) if isinstance(stg.get(key), dict) else {}
            start_c = float(st_e.get("confidence") or 0.0)
            staged_c = float(stg_e.get("confidence") or 0.0)
            try:
                start_u = int(st_e.get("solid_uses") or 0)
            except (TypeError, ValueError):
                start_u = 0
            try:
                staged_u = int(stg_e.get("solid_uses") or 0)
            except (TypeError, ValueError):
                staged_u = 0

            if entry.get("confidence") is not None:
                try:
                    cur = float(entry["confidence"])
                except (TypeError, ValueError):
                    cur = None
                if cur is not None:
                    ceiling = max(start_c + MAX_CONF_UP_PER_TURN, staged_c)
                    if cur > ceiling:
                        entry["confidence"] = round(ceiling, 3)
                        cur = float(entry["confidence"])
                else:
                    cur = None
            else:
                cur = None

            try:
                cur_u = int(entry.get("solid_uses") or 0)
            except (TypeError, ValueError):
                cur_u = 0
            u_ceiling = max(start_u + 1, staged_u)
            if cur_u > u_ceiling:
                entry["solid_uses"] = u_ceiling
                cur_u = u_ceiling

            # Re-gate known after any clip (conf and/or uses).
            if entry.get("status") == "known":
                conf_now = cur if cur is not None else float(entry.get("confidence") or 0.0)
                if conf_now < KNOWN_MIN_CONF or cur_u < KNOWN_MIN_SOLID_USES:
                    entry["status"] = "emerging"
    return final
```

**Add tests (required with this amend):**
1. Tool + name observer on `"Me llama es Patrick"`: conf \(= 0.25\), solid_uses \(= 1\) (not 2).
2. Construct stacked success from conf \(0.50\), uses \(1\): after process/cap, conf \(\le 0.75\) and status \(\ne\) `known` if conf \(< 0.80\).

---

### Item 6 — `_bump_status` docstring (“per-call” + pointer to process_turn)

**COUNTERSIGN**, subject to Item 5 body landing (doc already says net ceiling is in `process_turn`).

---

### Item 7 — `process_turn` three branch wirings

**AMEND** the rules_backup branch only; tool/AI wirings **COUNTERSIGN**.

**Bug:** cap runs *before* `inline_delta`:

```python
s = apply_rule_updates(...)
s = _cap_turn_confidence(before, before, s)  # too early
if inline_delta:
    s = apply_delta(s, inline_delta)         # can rise further past turn ceiling
```

Arithmetic: start \(0\), rules → \(0.12\), cap keeps \(0.12\), inline requests \(0.40\) → `_clamp_skill_entry` allows up to \(0.12 + 0.25 = 0.37\). Net rise from turn start \(= 0.37 > 0.25\).

**Exact replacement for the else branch:**

```python
    else:
        # Backup: rules + optional inline delta (no second model call)
        s = apply_rule_updates(sheet, learner, visible)
        notes = ["rules_backup", "hard_observer"]
        if inline_delta:
            s = apply_delta(s, inline_delta)
            notes.append("inline_delta")
        # Cap after all staged work so inline cannot exceed the turn ceiling.
        s = _cap_turn_confidence(before, before, s)
        s = update_scaffold_flag(s, learner)
        s = recompute_next_best(s)
        s = _preserve_identity(sheet, s)
```

Tool path (`staged` after tool, cap after observer) and AI path (same shape): **COUNTERSIGN** for the stacking problem they target.

---

### Item 8 — Deliberate CLT choice: erroneous-but-communicative production still SUCCESS-bumps can-do; form in `error_patterns`

**COUNTERSIGN.**

- Can-do IP-03 is communicative (“say my name”), not form accuracy. `"Me llama es Patrick"` transmits name → success credit is coherent with ACTFL-style can-dos and CLT/TBLT meaning priority.
- Form is recorded: `me_llamo_es` count \(1\), priority medium; `form_id` is `None` so grammar block is not double-punished — form lives in `error_patterns`, can-do in skills. Matches Long-style focus-on-form (meaning primary; form attended when it arises), not focus-on-forms as the progress metric.
- Recast path remains product-side (existing teach_hint / form-in-talk next_best).

**Caveat (non-blocking):** same turn also bumps IP-07 via `\b(soy|eres|es)\b` matching the erroneous `es` (\(0 \rightarrow 0.08\)). Separate false-positive; not introduced by this cap change. Track if you open a detector hygiene pass.

---

### Item 9 — `TestComprehensionRepair`

**COUNTERSIGN as mode-regression tests; AMEND packaging.**

- Assertions match landed comprehension-repair behavior (same topic, hard_break, budget bypass, no repair without `last_tutor_try`).
- Orthogonal to confidence semantics. Landing them in the same commit as the cap is fine if CI needs them, but they do **not** exercise `_cap_turn_confidence`. Do not treat green repair tests as evidence for the conf design.

**No code change required** for the tests themselves.

---

## Verdict table

| Item | Ruling |
|------|--------|
| 1. Double-count conf \(0\to0.5\) | **COUNTERSIGN** (verified) |
| 2. “Strongest signal” framing | **AMEND** docstring (sum-then-cap + staged max) |
| 3. Tool/AI own clamps | **REJECT claim**; AI path has no +0.25 clamp |
| 4. Legacy 0.25 / 0.5 tests | **COUNTERSIGN** |
| 5. `_cap_turn_confidence` body | **AMEND**: also cap solid_uses; re-gate `known` |
| 6. `_bump_status` docstring | **COUNTERSIGN** |
| 7. `process_turn` branches | **COUNTERSIGN** tool/AI; **AMEND** backup (cap after inline) |
| 8. CLT success + separate form error | **COUNTERSIGN** |
| 9. `TestComprehensionRepair` | **COUNTERSIGN** tests; note orthogonal |

**Package status: not final until Items 5 and 7 land.**  
With those amends: conf honesty matches the stated +0.25/turn contract, solid_uses cannot hit the known-uses gate from a single double-counted utterance, and `known` cannot survive below `KNOWN_MIN_CONF`. Without them, the conf fix is real but leaves a second double-count channel (uses) and a status invariant hole — ship-blocking for a “confidence semantics” change.

---

## CLAUDE (Fable 5) — Adjudication of cap-change countersign + close-out — 2026-07-26

| Item | Grok ruling | Adjudication |
|------|-------------|--------------|
| 1, 4, 6, 8 | COUNTERSIGN | Accepted; no action |
| 2 (framing) | AMEND | **Accepted** — docstring now states sum-then-clip with staged max, not "strongest signal wins" |
| 3 (AI clamp claim) | REJECT claim | **Accepted** — my rationale overstated; AI full-rewrite path has no +0.25 honesty clamp. Gap documented in `_cap_turn_confidence` docstring; closing it is a **deliberate follow-up** (would change `test_process_turn_ai_revised_sheet` semantics) |
| 5 (solid_uses + known re-gate) | AMEND | **Accepted and landed** — uses ceiling `max(start+1, staged)`; `known` re-gated after clip. Both required tests added (`test_cap_tool_plus_observer_single_use`, `test_cap_stacked_bumps_cannot_reach_known`) |
| 7 (backup branch order) | AMEND | **Accepted and landed** — cap moved after `inline_delta` |
| 9 (test packaging) | COUNTERSIGN + note | Accepted; repair tests are mode-regression coverage, not conf-design evidence |

### Bonus: first live run of the new conv gate caught a product bug

`c06_transfer_after_resolve` failed: correct "Estoy bien." (resolving hot `estar_yo_estoy_vs_esta`) still triggered a `form_focus` hard break on the same form — the guard at `modes.py` priority 3 never consulted same-turn `resolves` (only the lower-priority transfer guard did). Fixed: resolve now suppresses form_focus for that pattern. Unit tests both directions; live re-run: c03 `[conversation, form_focus]`, c06 `[conversation, transfer, transfer]`. Full conv gate now 7/7.

**Converged.** Open follow-ups (tracked, not in this change set): AI-rewrite honesty clamp; IP-07 detector false-positive on erroneous "es" (Grok item 8 caveat); offline `select_mode`-only CI arm (Grok port review, open question 2).

**Final state:** 192/192 unit tests; truncation gate ok; conv behavioral gate 7/7 live on `gemini-3.6-flash`.
