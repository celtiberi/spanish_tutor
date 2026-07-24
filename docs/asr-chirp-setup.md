# Dedicated ASR setup — Google Cloud Speech-to-Text (Chirp)

This is the **recommended** mic path for accurate live captions.
Gemini stays as the tutor brain + TTS; **Chirp** becomes the ears.

```text
Browser mic → PCM 16 kHz → Chirp ASR → text → ConversationalSession → Gemini TTS
```

## What you need

- A Google account (can be the same one as AI Studio)
- A **GCP project** with billing enabled (Speech-to-Text has a free tier / low cost for tutor use)
- ~10 minutes for setup

You already have `GEMINI_API_KEY`. Chirp needs **separate** GCP credentials
(`GOOGLE_APPLICATION_CREDENTIALS` or `gcloud auth application-default login`).

---

## 1. Create / pick a GCP project

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or select one), e.g. `ml-teacher`
3. Note the **Project ID** (not just the name)

Enable billing if prompted (required for Speech-to-Text).

---

## 2. Enable the Speech-to-Text API

```bash
# If you install gcloud (optional but handy):
# https://cloud.google.com/sdk/docs/install

gcloud config set project YOUR_PROJECT_ID
gcloud services enable speech.googleapis.com
```

Or in the console: **APIs & Services → Enable APIs → “Cloud Speech-to-Text API”**.

---

## 3. Create a service account + JSON key

1. **IAM & Admin → Service Accounts → Create**
   - Name: `ml-teacher-stt`
2. Grant role: **Cloud Speech Client**  
   (`roles/speech.client`)
3. **Keys → Add key → JSON** → download the file  
4. Put it somewhere **outside git**, e.g.:

```bash
mkdir -p ~/.config/ml_teacher
mv ~/Downloads/your-project-*.json ~/.config/ml_teacher/stt-sa.json
chmod 600 ~/.config/ml_teacher/stt-sa.json
```

**Never commit this JSON** (already covered by typical `.gitignore` for secrets).

---

## 4. Env vars for this repo

Add to `.env` (project root):

```bash
# Dedicated ASR (Chirp)
STT_BACKEND=chirp
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_APPLICATION_CREDENTIALS=/Users/YOU/.config/ml_teacher/stt-sa.json

# Optional Chirp tuning
# STT_CHIRP_LOCATION=us          # or europe-west4, etc. — must support chirp_3
# STT_CHIRP_MODEL=chirp_3
# STT_LANGUAGE_CODES=es-US,en-US   # bilingual learner
```

Install the client:

```bash
cd /path/to/ml_teacher
.venv/bin/pip install 'google-cloud-speech>=2.27'
# or: pip install -e ".[web,asr]"
```

Restart the web app:

```bash
.venv/bin/python -m tutor.web_app
# should log: stt=... stream=chirp ...
```

Check:

```bash
curl -s http://127.0.0.1:8765/api/health | python3 -m json.tool
# "stream_backend": "chirp", "chirp_ready": true
```

---

## 5. How the app uses Chirp

| Mode | Behavior |
|------|----------|
| `STT_BACKEND=chirp` | Live partials + final via **Chirp** (V2 Recognize on buffered PCM) |
| `STT_BACKEND=gemini` | Old path (Gemini generative STT) |
| `STT_BACKEND=auto` | Chirp if credentials work, else Gemini |

WebSocket protocol is unchanged (`/ws/stt`). The UI still streams PCM and shows live captions.

---

## 6. Smoke test (optional)

With the server running and mic allowed in the browser: hard-refresh → click mic → speak Spanish/English → words should appear without invented restaurant/filler phrases.

CLI-level check (no browser):

```bash
.venv/bin/python -c "
from tutor.stt_chirp import chirp_available, transcribe_pcm
print('ready', chirp_available())
# print(transcribe_pcm(open('sample.raw','rb').read()))  # raw s16le 16k mono
"
```

---

## 7. Cost (order of magnitude)

Speech-to-Text is billed **per minute of audio**. Tutor sessions (short turns) are usually cents unless you leave the mic open for hours. See [pricing](https://cloud.google.com/speech-to-text/pricing).

---

## 8. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `chirp_ready: false` | Check `GOOGLE_APPLICATION_CREDENTIALS` path and project ID |
| `403` / permission denied | Service account needs `roles/speech.client` |
| `404` model / location | Try `STT_CHIRP_LOCATION=us` or `us-central1` (Chirp regions vary) |
| Empty transcripts | Speak closer; confirm mic levels in the UI |
| Falls back to Gemini | Logs will say why; fix credentials then restart |

---

## Alternative: Application Default Credentials (no JSON file)

If you install `gcloud`:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
# leave GOOGLE_APPLICATION_CREDENTIALS unset
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
export STT_BACKEND=chirp
```

---

## What we are *not* doing yet

- Full gRPC **StreamingRecognize** word-by-word (Recognize-on-buffer is already far better than Gemini for accuracy)
- Chirp phrase sets tied to character-sheet focus forms (easy follow-up)
- Multi-user production IAM

Once Chirp is green in `/api/health`, use the mic as before — the box should track what you actually said.
