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

## Teaching modalities (the system expands here)

Pedagogy is not “text chat with a smart tone.” It is a **set of channels** that
build form–meaning links. v1 only enforces text moves (`model` / `try` /
`recast`). Later channels join the **same contract**, not the decorative UI.

| Modality | Pedagogical job | Status |
|----------|-----------------|--------|
| **Text model** | Put target form in ears/eyes | v1 required path |
| **Text try** | Elicit production | v1 required path |
| **Recast** | Focus on form in meaning | v1 |
| **Audio (TTS)** | Pronunciation + memory via voice | shipped (playback) |
| **STT** | Production under speaking pressure | shipped (mic) |
| **Visual / image** | Bind **nouns, scenes, concepts** to form so the learner associates meaning without English gloss | **planned — pedagogy, not garnish** |
| **Gesture / emoji (light)** | Comprehensible-input scaffold | opportunistic only |
| **Task / roleplay** | TBLT use of form | sheet `next_best` activities |

### Visual association (image generation)

When we add images, they are a **teach move**, not a wallpaper:

1. **Target-linked** — image depicts the *same* noun/scene/concept as the
   form in `model` / `try` (e.g. *el bote*, *estoy en el bote*, *café*).
2. **Same turn as the form** — show image with model/try so form + meaning
   land together (dual coding / CI support).
3. **Contract-shaped** — e.g. structured part `<image concept="bote" …>` or
   a sheet/tool field `teach_assets[]` with `{concept, form, asset_id}`.
4. **Measurable** — sim/live logs: “image present for target concept?” not
   “pretty picture count.”
5. **Experiment, not vibe** — enable via contract version bump + tests
   (when is image required? which concepts? cache vs generate?).

Images must **not** become:

- random decoration unrelated to the teach target  
- English-label stickers that short-circuit inference  
- a side feature the tutor “sometimes remembers”

They belong in the **same teach cycle**:

```
meaning → model (+ visual of the referent) → try → recast → transfer
```

### How modalities enter the system

1. Name the modality in this doc + `TEACH_MODALITIES` in code.  
2. Define when it is **optional** vs **required** (contract version).  
3. Wire structured part or tool + logging.  
4. Tests for the new invariant.  
5. Prompt/harness only after the contract knows about it.

## Future (deliberate upgrades)

- Blocking retry when model omits teach moves (one re-ask to the LLM).
- UI badge when `pedagogy:no_teach_move` fires.
- Sim report section: % turns with teach moves.
- Link can-do `next_best` to required try templates.
- **v1.x:** optional `image` teach asset on noun/lexicon targets.
- **v2:** contract may require visual for selected concept classes
  (concrete nouns, locations, food) when generation is reliable.
