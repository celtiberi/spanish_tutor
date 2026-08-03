# Teacher context: no silent truncation (testing rule)

## Why this exists

Latency optimisations repeatedly **sliced** what the AI teacher sees:

- character sheet cut mid-skills (so `next_best` / errors vanished)
- course pack truncated
- stance truncated
- chat history hard-capped (`history[-24:]`) while another path claimed “full history”

That made the tutor look like it “didn’t know the sheet” and re-probed randomly. **Do not reintroduce this until pedagogy works end-to-end.**

## Policy

| Mode | Behaviour |
|------|-----------|
| **Default (testing)** | Full sheet, full pack, full stance, full session history |
| **Prod opt-in only** | `TEACHER_CONTEXT_TRUNCATE=1` plus optional `SHEET_PROMPT_CHARS` / `PACK_PROMPT_CHARS` / `STANCE_PROMPT_CHARS` / `HISTORY_TURNS` |

Single history API: `config.history_for_model(history)` — **never mutate** `self.history` to drop turns.

## Git enforcement

```bash
# Install hooks (once per clone)
git config core.hooksPath .githooks

# Manual / CI
python scripts/check_teacher_truncation.py
python scripts/check_teacher_truncation.py --staged
```

Pre-commit runs the staged scan and **fails the commit** on high/medium findings in teacher-path modules:

`conv_session`, `executor`, `character_sheet`, `config`, `modes`, `observe`, `output_gate`, `scenes`, `session_memory`, `rules_planner`, `corpus`, `plan_card`, `pedagogy_contract`, `tutor_response`.

### Allow intentional slices

```python
snippet = text[:80]  # truncation-ok: sheet storage evidence only
```

### Emergency bypass

```bash
SKIP_TRUNCATION_CHECK=1 git commit -m "..."
```

## Plan-mode rounds (the ONE sanctioned window — USER architecture 2026-08-03)

`TEACHER_CONTEXT=plan` (the default) is two-phase: **PLAN turns** (session
open, or after the model emits `<replan/>`) send the FULL context —
PEDAGOGY.md verbatim + full pack + full sheet + full history — and the
model writes its own private `<plan>` block. **ROUND turns** send the
model's OWN plan + full sheet + session facts + the last
`ROUND_HISTORY_MESSAGES` (=12, `tutor/session_plan.py`) messages, no pack.

This window is not a latency slice and is not silent: the line carries a
`# truncation-ok:` marker, the checker gained a **named-constant-window
pattern** (`history[-SOME_CONST:]` now blocks without the marker), and the
characterization guard (`tests/conftest.py::assert_full_teacher_context`)
asserts the round CONTRACT — no pack, `your_session_plan` present,
tail-aligned window of exactly K — instead of exempting round turns.
ENGINEERING.md §3.3 amendment is the law text.

## Agent rule (Claude / Grok / commit tools)

When editing teacher-path code:

1. Do **not** add `[:N]` on sheet/pack/stance/history sent to the model.
2. Do **not** assign `self.history = self.history[-N:]` — with a literal
   OR a named constant; the plan-mode round window in `turn_pipeline.py`
   is the one sanctioned, marker-annotated instance.
3. Prefer full `format_sheet_for_prompt` + `load_pack` + `history_for_model`.
4. Run `python scripts/check_teacher_truncation.py` before committing.
