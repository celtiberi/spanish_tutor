# Pedagogy contract (conversational)

**Status:** source of truth for “does this turn teach?”  
**Code:** `tutor/pedagogy_contract.py`  
**Version:** see `CONTRACT_VERSION` in that file.

## Why this exists

We drifted into chat-buddy mode even though the product is a **tutor**. The
root cause was structural:

| Layer | What went wrong |
|-------|-----------------|
| Prompt only | Teach rules lived in markdown. “Language mix” / anti-drill edits overwrote them with no failing test. |
| Soft harness | OPEN said “invite easy chat / don’t start a worksheet” — anti-drill became anti-teach. |
| No gate | Structured parts parsed recasts, but **model/try were optional**. A bare `¿Cómo estás?` was “valid.” |
| Metrics | Sims scored language mix and error tracking, not “did the turn teach?” |
| Experiments | Tabled plan/executor still had gates (`directive_gate`); conversational path did not. |

**Rule:** Pedagogy is a **system**. Experiments expand it on purpose. A tone
tweak must not delete teaching.

## Contract v1 (invariants)

1. Every turn has a **teach move**: non-empty `model` and/or `try` and/or `recast`.
2. **Open** requires `model` **and** `try` (not a bare greeting).
3. **Recast** should pair with **try** (same-form retry).
4. `continue` alone = **violation**.

Enforcement today: non-blocking for the learner (reply still shown) but
**always** attached to turn notes / `parts.pedagogy` / session logs:

- `pedagogy:ok`
- `pedagogy:no_teach_move`
- `pedagogy:open_needs_model_try`
- `pedagogy:recast_without_try`

## Layers (who owns what)

```
docs/pedagogy-contract.md     ← human intent + history of versions
tutor/pedagogy_contract.py    ← machine invariants + evaluate_turn()
prompts/conversational_tutor.md  ← implements contract for the LLM
tutor/conv_session.py         ← calls evaluate_turn every finish
tests/test_pedagogy_contract.py  ← regression (incl. prompt needles)
```

Prompts may change tone, Spanish-forward rules, examples. They must still
satisfy the contract. If an experiment needs weaker teaching for a baseline,
bump `CONTRACT_VERSION` and update tests **in the same PR**.

## How to experiment safely

1. Write the hypothesis (what teach move changes, what we measure).
2. Change `pedagogy_contract.py` + tests first (or with the prompt).
3. Then change prompt/harness.
4. Run: `python -m unittest tests.test_pedagogy_contract tests.test_tutor_response`
5. Short AI-student or live log: count `pedagogy:ok` vs violations.

Do **not** “just soften the prompt” to see if chat feels nicer.

## Future (deliberate upgrades)

- Blocking retry when model omits teach moves (one re-ask to the LLM).
- UI badge when `pedagogy:no_teach_move` fires.
- Sim report section: % turns with teach moves.
- Link can-do `next_best` to required try templates.
