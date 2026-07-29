# Vercel deployment

## Can this run on Vercel?

**Partially yes** for HTTP chat + static UI. **Not a perfect fit** for the full local stack.

| Feature | On Vercel |
|---------|-----------|
| Web UI + REST chat | Works |
| Tutor LLM turns (Gemini/Grok/Anthropic) | Works if API keys set; needs long `maxDuration` |
| Teach images (seeded static) | Works |
| Character sheet / session logs on disk | Ephemeral (`/tmp`) — lost across cold starts |
| In-memory chat sessions | Fragile across serverless instances |
| WebSocket Chirp STT (`/ws/stt`) | Poor / unsupported on standard serverless |
| Google ADC service-account file | Awkward — prefer Gemini STT or browser STT |

**Better full-fidelity hosts** for always-on FastAPI + WebSockets + disk: **Fly.io, Railway, Render**.

We still ship Vercel config for easy previews and HTTP tutor demos, with auto-deploy on push to `main`.

## Auto-deploy

1. Project linked to this repo (`vercel link` / Git integration).
2. Push to `origin` (`main`) → production deploy.
3. Other branches → preview deploys.

## Required env vars (Project → Settings → Environment Variables)

| Name | Purpose |
|------|---------|
| `GEMINI_API_KEY` | Default tutor model |
| `GROK_API_KEY` | Focus model / Grok models |
| `ANTHROPIC_API_KEY` | Optional Claude models |
| `TUTOR_MODEL` | e.g. `gemini-3.6-flash` |
| `FOCUS_MODEL` | e.g. `grok-3-mini` or `off` |
| `TEACHER_MODE` | `planned` (only supported value family; `rules`/`legacy` deleted — E4/E4b 2026-07-28) |
| `TTS_ENABLED` | `true` / `false` |
| `STT_ENABLED` | prefer `false` or browser-side on Vercel |

Do **not** commit `.env`. Chirp (`GOOGLE_APPLICATION_CREDENTIALS`) is not set up for Vercel in this config.

## Local

```bash
vercel dev   # or: python -m tutor.web_app
```
