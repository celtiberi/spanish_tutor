# ml_teacher — pedagogy-first tutoring model

Research project: train/align a model that is an expert in **teaching**, with subject matter supplied by pluggable course packs. Full plan: `docs/research-and-plan.md`.

**Law (sole home of teaching law text):** [`PEDAGOGY.md`](PEDAGOGY.md)  
**Living system overview (architecture, pedagogy, ops):** [`docs/system-overview.md`](docs/system-overview.md)

**Current product path:** conversational Spanish + living **character sheet** (Spanish ability only: can-dos, scaffold/ledger, next_best, retrieval schedule) + **pedagogy engine** (session phases → close, introduce router, association table, task runtime, output gates, progress journey). **Personal-data capture removed by construction (2026-07-28)** — `tutor/learner_profile.py` is disconnected reference code only. Plan/realize controller is tabled.

```
PEDAGOGY.md                       # sole law home (P1–P9 + HARD/BINDING laws)
prompts/conversational_tutor.md   # teaching stance (CLT/TBLT/CI)
course_packs/spanish_a1/          # legal language palette + association_table.json
tutor/conv_session.py             # shared session engine
tutor/character_sheet.py          # Spanish-ability sheet (no personal data)
tutor/session_phases.py           # 5-phase plan (… → close)
tutor/retrieval_scheduler.py      # spaced re-encounter ladder
tutor/introduce_router.py         # first-exposure scaffolding
tutor/web_app.py                  # browser UI (+ browser speech)
```

## Conversational Spanish (primary)

### Web (chat + mic + spoken replies)

```sh
pip install -e ".[web]"
# set GEMINI_API_KEY and/or GROK_API_KEY / ANTHROPIC_API_KEY; TUTOR_MODEL=gemini-3.6-flash
python -m tutor.web_app
# open http://127.0.0.1:8765
```

- **Type** or use the **mic** (browser speech recognition → same chat API).
- **Speak replies** uses **Gemini neural TTS** (`/api/audio/speak`); browser TTS is fallback. Server default rate is **1.0** (native); the UI Voice slider is **0.7–1.2**.
- Right rail: **This turn** (live mode) + **Morphology** (static pack + optional cheap async `FOCUS_MODEL`) + **Progress journey** (append-only milestone ledger).
- Character sheet panel = ability sheet only (no name/personal store).
- Server-side STT/TTS notes: `docs/web-and-audio.md`.

```sh
# optional: cheap Grok for side-rail personalization (default)
export FOCUS_MODEL=grok-3-mini   # or off / static
export GROK_API_KEY=...          # needed if FOCUS_MODEL is a grok-* id
export TUTOR_MODEL=gemini-3.6-flash
```

Session logs: `logs/sessions/*.jsonl`. Ability sheet: `logs/character_sheet.json`. Cost ledger: `logs/costs.jsonl` (when written). Stale `logs/learner_profile.json` from the pre-2026-07-28 capture era is deleted by reset/clear paths only — nothing loads or writes personal facts.

## Legacy single-model pack tutor

Deleted 2026-07-28 (`tutor/cli.py` + planner/controller stack; git history is the archive).

### Design notes

- **No vector RAG in v0** — the whole pack sits in the cached system prefix (an A1 pack is small; caching makes repeat turns ~90% cheaper). `tutor/corpus.py` is the seam where a retriever slots in when corpora outgrow context.
- **Student state** is maintained by the model itself in a `<session_state>` block at the end of each reply; the harness strips it, persists it, and re-injects it as a mid-conversation system message.
- **Misconception IDs** (`M-x.y`) in the pack double as gold labels for the diagnostic-accuracy rubric dimension.
