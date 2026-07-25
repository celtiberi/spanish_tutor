# Web UI + audio path

## Run

```sh
pip install -e ".[web]"   # or: pip install fastapi uvicorn
python -m tutor.web_app   # http://127.0.0.1:8765
```

Env: same as CLI (`GEMINI_API_KEY` / `GROK_API_KEY` / `ANTHROPIC_API_KEY`, `TUTOR_MODEL`).

## Architecture

```text
Browser  ──JSON──►  FastAPI (tutor.web_app)
                      │
                      ▼
              ConversationalSession (tutor.conv_session)
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
   TUTOR_MODEL                FOCUS_MODEL (cheap)
   (e.g. gemini flash)        (default: grok-3-mini)
   reply + sheet tool         focus + morphology rail
                              static templates if off/fail
```

### Models

| Env | Default | Role |
|-----|---------|------|
| `TUTOR_MODEL` | `gemini-3.6-flash` | Learner-facing chat + sheet tool updates |
| `FOCUS_MODEL` | `grok-3-mini` | Side-rail personalization (blurb, watch, highlights) |
| `FOCUS_MODEL=off` | — | Static can-do morphology only (no second API call) |

Focus enrich runs after turns (and when stretch/`next_best` changes). It never invents can-do scores; harness clamps stay authoritative.

| Surface | Module |
|---------|--------|
| CLI | `python -m tutor.conversational` |
| Web | `python -m tutor.web_app` |
| Engine | `tutor.conv_session.ConversationalSession` |

Same sheet file by default: `logs/character_sheet.json`.

### API (v0)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Chat UI |
| POST | `/api/session/start` | Open / resume session (cookie) |
| POST | `/api/chat` | `{ message, input_mode: text\|speech }` → reply + optional `parts` |

### Structured tutor reply parts

The teaching model is asked to emit labeled blocks (not shown as raw tags to the learner):

| Part | Role |
|------|------|
| `acknowledge` | Meaning / rapport (never “spot on” for wrong Spanish) |
| `recast` | Clean model when form/register/construction was off (**required** then) |
| `explain` | Optional brief/deep focus-on-form |
| `continue` | Next conversational beat / stretch |

Parser: `tutor/tutor_response.py`. Web UI styles parts (Try this / Why / Next).  
Policy: recast before chasing `next_best`.
| GET | `/api/sheet` | Public character sheet |
| POST | `/api/session/reset` | `{ reset_sheet?: bool }` new chat |

## Audio roadmap

### Now

- **STT (mic, primary):** streaming PCM over WebSocket `WS /ws/stt`  
  - Browser streams 16 kHz **LINEAR16** PCM while you talk (Cloud STT best practice)  
  - Server **VAD**: peak RMS + speech-ratio; trim leading/trailing silence  
  - Gemini batch STT with `temperature=0`, structured `{has_speech, transcript}`  
  - Rolling partials (~1.6s) for live box captions — only if VAD passes;  
    partials **never jump** to an unrelated invented phrase  
  - On stop: final STT is authoritative → auto-send  
  - Model: `STT_MODEL` (default `gemini-3.6-flash`)
- **STT (fallback HTTP):** `POST /api/audio/transcribe` still available  
- **TTS (tutor speak):** **server Gemini TTS** via `POST /api/audio/speak`  
  - Model: `TTS_MODEL` (default `gemini-2.5-flash-preview-tts`)  
  - Voice: `TTS_VOICE` (default `Sulafat` — warm)  
  - Fallback: browser `speechSynthesis` if server TTS fails or `TTS_ENABLED=off`

### Why not “just Gemini Live / partial every second”?

Google’s [audio docs](https://ai.google.dev/gemini-api/docs/audio) point dedicated
real-time transcription at **Cloud Speech-to-Text (Chirp)**. Gemini is a
generative multimodal model: on silence or incomplete audio it often invents
phrases (we reproduced Spanish/English hallucinations). Mitigations we use:
VAD gates, silence trim, JSON `has_speech`, neutral prompts, stable partials.

### Mic UX

1. Click mic → stream PCM; status shows levels  
2. After ~1.2s of real speech, **words appear in the box** (provisional)  
3. Click mic → final transcript → send  

True word-streaming ASR still needs Chirp + GCP credentials.

### Next

1. Optional Cloud Speech-to-Text (Chirp) for lower-latency word-by-word captions.
2. Stream TTS for lower latency.
3. Optional duplex / hands-free VAD mode (keep structured tutor turns).

Do **not** put API keys in the browser; STT/TTS keys stay server-side.

## Product notes

- Character sheet panel = same living model as CLI `/sheet`.
- Tool updates still run after turns; notes appear under the chat.
- Multi-user production would need real auth + per-user sheet storage (today: cookie session + shared default sheet path).

## AI student simulation (testing)

Run a Grok-powered learner against the tutor on a **separate** sheet:

```sh
# requires GROK_API_KEY (+ tutor GEMINI_API_KEY by default)
python -m tutor.ai_student --turns 6 --persona alex_boat
python -m tutor.ai_student --persona maya_shy --keep-sheet --turns 4
python -m tutor.ai_student --level intermediate_low --persona jordan_travel --turns 6
python -m tutor.ai_student --json-out logs/ai_student_report.json
```

- Sheet: `logs/ai_student_sheet.json` (not Patrick’s live sheet)
- Student model: `AI_STUDENT_MODEL` (default `grok-4.5`)
- Teacher model: `TUTOR_MODEL`
- Personas: `alex_boat` (yo/está), `maya_shy` (ser/estar), `jordan_travel` (stronger)
- Ability bands (`--level`): `novice_low`, `novice_mid`, `intermediate_low`
- Student keeps structured `learner_state` each turn (forms, confidence, can_try_now) + full chat memory
- Prints turn log + verification checks (error tracking, learning, recasts)

See `tutor/ai_student.py` and `prompts/ai_student.md`.
