# ml_teacher — pedagogy-first tutoring model

Research project: train/align a model that is an expert in **teaching**, with subject matter supplied by pluggable course packs. Full plan: `docs/research-and-plan.md`.

**Current product path:** conversational Spanish + living **character sheet** (can-dos, scaffold, next_best). Plan/realize controller is tabled.

```
prompts/conversational_tutor.md   # teaching stance (CLT/TBLT/CI)
course_packs/spanish_a1/          # legal language palette
tutor/conv_session.py             # shared session engine
tutor/conversational.py           # terminal UI
tutor/web_app.py                  # browser UI (+ browser speech)
```

## Conversational Spanish (primary)

### CLI

```sh
pip install -e .
# set GEMINI_API_KEY and/or GROK_API_KEY / ANTHROPIC_API_KEY; TUTOR_MODEL=gemini-3.6-flash
python -m tutor.conversational
```

### Web (chat + mic + spoken replies)

```sh
pip install -e ".[web]"
python -m tutor.web_app
# open http://127.0.0.1:8765
```

- **Type** or use the **mic** (browser speech recognition → same chat API).
- **Speak replies** uses **Gemini neural TTS** (`/api/audio/speak`); browser TTS is fallback.
- Right rail: **Focus now** + **Morphology** (static pack + optional cheap `FOCUS_MODEL`).
- Character sheet panel = same model as CLI `/sheet`.
- Server-side STT/TTS is the next audio step — see `docs/web-and-audio.md`.

```sh
# optional: cheap Grok for side-rail personalization (default)
export FOCUS_MODEL=grok-3-mini   # or off / static
export GROK_API_KEY=...          # needed if FOCUS_MODEL is a grok-* id
export TUTOR_MODEL=gemini-3.6-flash
```

Session logs: `logs/sessions/*.jsonl`. Sheet: `logs/character_sheet.json`.

## Legacy single-model pack tutor

```sh
tutor                # or: python -m tutor.cli
tutor --pack course_packs/<other_pack>
```

### Design notes

- **No vector RAG in v0** — the whole pack sits in the cached system prefix (an A1 pack is small; caching makes repeat turns ~90% cheaper). `tutor/corpus.py` is the seam where a retriever slots in when corpora outgrow context.
- **Student state** is maintained by the model itself in a `<session_state>` block at the end of each reply; the harness strips it, persists it, and re-injects it as a mid-conversation system message.
- **Misconception IDs** (`M-x.y`) in the pack double as gold labels for the diagnostic-accuracy rubric dimension.
