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

## Agent rule (Claude / Grok / commit tools)

When editing teacher-path code:

1. Do **not** add `[:N]` on sheet/pack/stance/history sent to the model.
2. Do **not** assign `self.history = self.history[-N:]`.
3. Prefer full `format_sheet_for_prompt` + `load_pack` + `history_for_model`.
4. Run `python scripts/check_teacher_truncation.py` before committing.
