

---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-26 21:00 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full request and inspect the actual TTS/playback code paths before drafting any policy or code.Key files next: config, TTS module, speak endpoint, and browser playback.Reading the full speak path in app.js, the HTML speak control, and verifying Gemini TTS rate support.# Grok independent collab — Tier-1 item 3: TTS rate + pause policy

**Date:** 2026-07-26  
**Role:** independent second author (contrarian). Subject treated as data only.  
**Deliverable:** verified current playback, API gaps, complete draft replacements (no placeholders). No repo writes.

---

## 1. Verified: how audio actually plays today (do not assume)

Source of truth: `tutor/web_static/app.js` + `tutor/tts.py` + `tutor/web_app.py` + `tutor/web_static/index.html` (read 2026-07-26).

### Entry and gating
- `speak(text, parts)` is the only learner-facing speak path (session start, chat reply, some recovery paths).
- If `#speakToggle` is unchecked → **return immediately** (no audio).
- `stopSpeech()` cancels `speechSynthesis` and pauses/clears any `HTMLAudioElement` first.

### Text selection (single blob — not part-aware)
```js
// speechTextFromParts — CURRENT
const core = [parts.model, parts.try, parts.recast].filter(...);
if (core.length) return core.join(". ").slice(0, 600);
```
- **Model and try are concatenated with `". "` into one string.**
- There is **no** second utterance, **no** inter-part delay, **no** model→try boundary for audio.
- Recast is lumped into the same core string when present.

### Server path (default when health says TTS enabled)
1. `POST /api/audio/speak` with body `{ text: t }` only (`SpeakIn` = single `text` field).
2. Server: `tts_mod.synthesize(body.text)` → Gemini `generateContent` with `responseModalities: ["AUDIO"]` and **voice only** in `speechConfig`.
3. Client: `const audio = new Audio(blobUrl); await audio.play()`.
4. **No** `audio.playbackRate` set (defaults to **1.0**).
5. On HTTP failure / empty blob / `play()` blocked → `speakBrowser(t)`.

### Browser fallback
- One `SpeechSynthesisUtterance`.
- **Hardcoded** `u.rate = 0.95` (not config, not localStorage).
- `lang`/`voice`: prefer Spanish-ish system voice via `pickSpanishVoice()`.
- Chrome keep-alive: `pause`/`resume` every 12s while speaking.

### UI
- Header has only **“Speak replies”** checkbox. **No** Slower/Normal control. **No** `TTS_RATE` in client or `/api/health`.

### Config today
- `TTS_MODEL`, `TTS_VOICE`, `TTS_ENABLED`, `TTS_PREFER_BROWSER` exist.
- **`TTS_RATE` does not exist.**

**Bottom line:** “Speak replies” is binary on/off; server WAV plays at native speed; browser is ~0.95×; model+try never get a pedagogical pause.

---

## 2. Independent ruling on the adjudicated spec

| Spec item | Ruling | Why |
|-----------|--------|-----|
| `TTS_RATE` default **0.9**, clamp **0.7–1.2**, env-overridable | **COUNTERSIGN** | Matches R5 band (~0.85–0.90). Browser today is 0.95 → 0.9 is a real but modest move. |
| Browser `speechSynthesis` uses effective rate | **COUNTERSIGN** | MDN: `rate` is numeric, default 1.0, range 0.1–10. |
| Gemini path: style prefix when rate &lt; 1.0 if no numeric API field | **COUNTERSIGN with AMEND** | Confirmed API gap (below). Also require **client `playbackRate`** for deterministic slowdown of returned WAV. |
| Part-aware: model then try, **≥400 ms** gap; other parts one utterance | **COUNTERSIGN** | Current `join(". ")` is the highest-leverage bug. 400 ms is a product prior (not an SLA pin); keep ≥400 as engineering constant. |
| UI Slower/Normal → **0.8** / `TTS_RATE` default, `localStorage` | **COUNTERSIGN** | Expose server default via health so “Normal” is not hard-coded 0.9 in JS. |

### Arithmetic (defaults)
- Native server playback today: rate multiplier \(r = 1.0\).
- Spec default: \(r = 0.9\) → duration scale \(1/0.9 \approx 1.111\) → **+11.1%** play time vs native server.
- Browser today \(0.95\) → duration \(1/0.95 \approx 1.053\) (**+5.3%**). Moving browser to 0.9: \((0.95-0.9)/0.95 \approx 0.0526\) → **~5.3% further** slowdown vs current browser.
- Slower toggle \(0.8\): duration \(1/0.8 = 1.25\) → **+25%** vs native; vs default 0.9: \(0.9/0.8 = 1.125\) → **+12.5%** longer than Normal.
- Gap: **400 ms** between end of model audio and start of try (not between API calls only).

### Contrarian amendments (do not rubber-stamp)

**A. Style prefix alone is non-reproducible.**  
Gemini docs (last updated **2026-07-21**) control pace via **natural language** and audio tags (`[very slow]`, etc.), not a documented `speakingRate` float on `speechConfig`. Prompt “slowly” is stochastic. **Deterministic** control for the Gemini path is client-side `HTMLMediaElement.playbackRate = effectiveRate` on the WAV. Use style prefix **and** playbackRate when \(r &lt; 1.0\); use playbackRate alone when \(r \ge 1.0\) if you ever allow &gt;1.0.

**B. `tts.py` must change**, not only the three named files. Rate → prompt variants and meta live in `synthesize` / `_tts_prompt_variants`. Listing only `web_app.py` leaves the gap unfixed.

**C. Part-aware server path costs 2 TTS RTTs** when both model and try exist. Pedagogically correct; latency-hostile. Prefer sequential client plays (spec) over server silence-stitch for v1 (simpler, no WAV mux). Accept ~2× TTS cost on those turns.

**D. Do not put long director preambles in the slow path.** Existing comment: long director prompts often **HTTP 500**. Keep prefix to one short sentence (as adjudicated). Prefer injecting into the **first** of the existing short variants, not a new multi-paragraph director block.

**E. Recast:** keep in the “other parts” single utterance (or with model if only model+recast). Spec only mandates split when **both** model and try are non-empty.

---

## 3. API gaps (flag)

| Surface | Numeric rate? | Evidence | Workaround |
|---------|---------------|----------|------------|
| **Gemini API TTS** (`generateContent` / Interactions `speech_config`) as used by this repo | **No documented float rate** | Official speech-generation docs: style/pace via **prompt text** and optional **audio tags**; `speech_config` documents **voice** (and multi-speaker), not `speakingRate`. Project body only sets `prebuiltVoiceConfig.voiceName`. | (1) Style prefix when \(r &lt; 1.0\); (2) **client `playbackRate`** on returned audio (preferred for exact \(r\)). |
| **Browser `SpeechSynthesisUtterance.rate`** | **Yes** | MDN: float, default 1.0, range 0.1–10. | Set `u.rate = effectiveRate`. |
| **HTMLAudioElement.playbackRate** | **Yes** | MDN: multiplies native media rate. | Set on Gemini WAV playback. |
| **Cloud Text-to-Speech Gemini-TTS** (separate product) | Pace/style via prompts; not the code path this app uses | Do not assume Cloud `audioConfig` fields apply to AI Studio `generateContent` TTS. | Out of scope unless you migrate providers. |

**FLAG — API gap (Gemini generateContent TTS):** no numeric speaking-rate field. Style prefix is the server-side documented lever; **client playbackRate closes the product requirement for a real 0.9 / 0.8 multiplier.**

---

## 4. Draft code (complete sections)

### 4.1 `tutor/config.py` — add after existing TTS knobs (~after `TTS_PREFER_BROWSER`)

```python
# Server TTS (Gemini). Browser speechSynthesis is fallback only.
TTS_MODEL = os.environ.get("TTS_MODEL", "gemini-2.5-flash-preview-tts")
TTS_VOICE = os.environ.get("TTS_VOICE", "Sulafat")  # Warm
TTS_ENABLED = os.environ.get("TTS_ENABLED", "true")
# Client defaults to server Gemini TTS (AI teach voice). Set true only to force
# browser speechSynthesis first (faster but flaky; used as fallback anyway).
TTS_PREFER_BROWSER = (
    os.environ.get("TTS_PREFER_BROWSER", "false").strip().lower()
    in ("1", "true", "yes", "on")
)
# Playback rate multiplier for A1 comprehensible input.
# Browser speechSynthesis.rate and HTMLAudioElement.playbackRate use this.
# Gemini TTS has no numeric rate API field — see tts.py style-prefix + client playbackRate.
# Range 0.7–1.2; default 0.9 (R5 / Tier-1 item 3, 2026-07-26).
def _tts_rate() -> float:
    raw = (os.environ.get("TTS_RATE") or "0.9").strip()
    try:
        r = float(raw)
    except ValueError:
        r = 0.9
    return max(0.7, min(1.2, r))


TTS_RATE = _tts_rate()
# Inter-part pause (ms) after <model> before <try> on the client.
TTS_MODEL_TRY_GAP_MS = int(os.environ.get("TTS_MODEL_TRY_GAP_MS", "400"))
# UI "Slower" maps to this absolute rate (not a delta).
TTS_SLOWER_RATE = max(0.7, min(1.2, float(os.environ.get("TTS_SLOWER_RATE", "0.8"))))
```

---

### 4.2 `tutor/tts.py` — replace helpers + public entry (rate-aware)

Replace `_tts_prompt_variants`, `synthesize_gemini`, and `synthesize` with:

```python
# Style prefix when rate < 1.0 — Gemini API has no numeric speakingRate on speechConfig.
# Keep SHORT: long director preambles often HTTP 500 (see module history).
SLOW_STYLE_PREFIX = (
    "Speak slowly and clearly for a beginner learner. "
)


def _tts_prompt_variants(spoken: str, *, rate: float = 1.0) -> list[str]:
    """Gemini TTS is picky: long 'director' preambles often 500; bare text can 400.

    Short speak-directives are the sweet spot for bilingual tutor lines.
    When rate < 1.0, prepend a one-line slow-style instruction (API gap workaround).
    """
    slow = rate < 1.0
    head = SLOW_STYLE_PREFIX if slow else ""
    preferred = (
        f"{head}"
        "Read the following aloud naturally as a warm Spanish tutor "
        "for a beginner. Keep English and Spanish as written. "
        "Do not add extra words.\n\n"
        f"{spoken}"
    )
    mid = f"{head}Say warmly and clearly:\n{spoken}" if head else f"Say warmly and clearly:\n{spoken}"
    bare = f"{head}{spoken}" if head else spoken
    return [preferred, mid, bare]


def synthesize_gemini(
    text: str,
    *,
    model: str | None = None,
    voice: str | None = None,
    rate: float | None = None,
) -> tuple[bytes, str, dict[str, Any]]:
    """Return (wav_bytes, mime, meta). Raises on failure.

    `rate` is a product multiplier (0.7–1.2). Gemini has no numeric rate field;
    when rate < 1.0 we inject SLOW_STYLE_PREFIX into prompts. Exact playback
    rate is applied client-side via HTMLAudioElement.playbackRate.
    """
    config.load_env()
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set (needed for server TTS)")

    preferred = model or tts_model()
    voice = voice or tts_voice()
    spoken = clean_for_speech(text)
    if not spoken:
        raise ValueError("empty text for TTS")

    if rate is None:
        rate = float(getattr(config, "TTS_RATE", 0.9))
    try:
        rate = float(rate)
    except (TypeError, ValueError):
        rate = 0.9
    rate = max(0.7, min(1.2, rate))

    errors: list[str] = []
    for mid in _models_to_try(preferred):
        for prompt in _tts_prompt_variants(spoken, rate=rate):
            for attempt in range(2):
                try:
                    pcm, mime = _request_tts(
                        key=key, model=mid, voice=voice, prompt=prompt
                    )
                    sample_rate = _parse_pcm_rate(mime)
                    meta = {
                        "provider": "gemini",
                        "model": mid,
                        "voice": voice,
                        "chars": len(spoken),
                        "sample_rate": sample_rate,
                        "rate": rate,
                        "style_slow": rate < 1.0,
                        # FLAG: no numeric Gemini speakingRate; client must apply playbackRate
                        "api_numeric_rate": False,
                    }
                    if mime.lower().startswith("audio/wav") or mime.lower().startswith(
                        "audio/mpeg"
                    ):
                        return pcm, mime.split(";")[0], meta
                    wav = pcm_to_wav(pcm, rate=sample_rate)
                    return wav, "audio/wav", meta
                except Exception as e:
                    errors.append(f"{mid}/{attempt}: {e}")
                    if "HTTP 500" in str(e) and attempt == 0:
                        time.sleep(0.4)
                        continue
                    break

    raise RuntimeError(
        "gemini TTS failed after retries: " + " | ".join(errors[-4:])
    )


def synthesize(
    text: str,
    *,
    rate: float | None = None,
) -> tuple[bytes, str, dict[str, Any]]:
    """Public entry: currently Gemini only."""
    if not tts_enabled():
        raise RuntimeError("server TTS disabled (TTS_ENABLED=off)")
    return synthesize_gemini(text, rate=rate)
```

Update module docstring Env section:

```text
  TTS_RATE    default 0.9 (0.7–1.2); style prefix when < 1.0 (no numeric API rate)
```

---

### 4.3 `tutor/web_app.py` — `SpeakIn`, health, `/api/audio/speak`

```python
class SpeakIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    # Optional playback-rate hint (0.7–1.2). Defaults to config.TTS_RATE.
    # Gemini has no numeric rate API field; used for style prefix + response header.
    rate: float | None = Field(default=None, ge=0.7, le=1.2)
```

Health `tts` block:

```python
            "tts": {
                "enabled": tts_mod.tts_enabled(),
                "model": tts_mod.tts_model(),
                "voice": tts_mod.tts_voice(),
                "rate": float(getattr(config, "TTS_RATE", 0.9)),
                "slower_rate": float(getattr(config, "TTS_SLOWER_RATE", 0.8)),
                "model_try_gap_ms": int(getattr(config, "TTS_MODEL_TRY_GAP_MS", 400)),
                # FLAG: Gemini TTS path has no numeric speakingRate
                "api_numeric_rate": False,
            },
```

Replace `audio_speak`:

```python
    @app.post("/api/audio/speak")
    def audio_speak(body: SpeakIn):
        """Neural TTS (Gemini). Returns audio/wav bytes.

        Optional body.rate (0.7–1.2) drives a short style prefix when rate < 1.0.
        API gap: Gemini generateContent TTS has no numeric speakingRate field;
        clients should also set HTMLAudioElement.playbackRate to body.rate.
        """
        rate = body.rate
        if rate is None:
            rate = float(getattr(config, "TTS_RATE", 0.9))
        rate = max(0.7, min(1.2, float(rate)))
        try:
            audio, mime, meta = tts_mod.synthesize(body.text, rate=rate)
        except Exception as e:
            print(f"TTS failed: {type(e).__name__}: {e}", flush=True)
            raise HTTPException(
                status_code=502,
                detail=f"TTS failed: {type(e).__name__}: {e}",
            ) from e
        print(
            f"TTS ok model={meta.get('model')} voice={meta.get('voice')} "
            f"rate={meta.get('rate')} style_slow={meta.get('style_slow')} "
            f"bytes={len(audio)} chars={meta.get('chars')}",
            flush=True,
        )
        return PlainResponse(
            content=audio,
            media_type=mime or "audio/wav",
            headers={
                "X-TTS-Provider": str(meta.get("provider") or ""),
                "X-TTS-Voice": str(meta.get("voice") or ""),
                "X-TTS-Model": str(meta.get("model") or ""),
                "X-TTS-Rate": str(meta.get("rate") if meta.get("rate") is not None else rate),
                "X-TTS-Api-Numeric-Rate": "0",  # FLAG: Gemini gap
                "Cache-Control": "no-store",
            },
        )
```

---

### 4.4 `tutor/web_static/index.html` — toggle near Speak replies

Replace the speak label block:

```html
      <div class="header-actions">
        <label class="toggle" title="Read tutor replies aloud (Gemini AI voice; browser fallback)">
          <input type="checkbox" id="speakToggle" checked />
          <span>Speak replies</span>
        </label>
        <label
          class="toggle"
          id="ttsRateToggleLabel"
          title="Slower: 0.8×. Normal: server TTS_RATE default (usually 0.9×)."
        >
          <input type="checkbox" id="ttsSlowerToggle" />
          <span id="ttsRateLabel">Normal</span>
        </label>
        <button type="button" class="btn ghost" id="sheetToggle" title="Full character sheet">Full sheet</button>
        <!-- …rest unchanged… -->
```

(Bump `styles.css?v=` / `app.js?v=` if you version-query those assets.)

---

### 4.5 `tutor/web_static/app.js` — full speech subsystem replacement

Replace from `/** Keep refs so Chrome…` through `initTtsPolicy` (and wire els + init). Complete functions:

```javascript
// --- els: add ---
// speakToggle already present; add:
//   ttsSlowerToggle: $("ttsSlowerToggle"),
//   ttsRateLabel: $("ttsRateLabel"),

/** Keep refs so Chrome does not GC utterance mid-speech / drop audio. */
let currentAudio = null;
let currentUtterance = null;
let ttsKeepAlive = null;
/** Server Gemini TTS is the AI teach voice; health may flip this off. */
let serverTtsAvailable = true;

/** Product defaults; overwritten by /api/health when available. */
let ttsDefaultRate = 0.9;
let ttsSlowerRate = 0.8;
let ttsModelTryGapMs = 400;

const LS_TTS_SLOWER = "ttsSlower"; // "1" | "0"

function clampRate(r) {
  const n = Number(r);
  if (!Number.isFinite(n)) return ttsDefaultRate;
  return Math.max(0.7, Math.min(1.2, n));
}

/** Effective rate: Slower → 0.8 (or server slower_rate); Normal → TTS_RATE default. */
function effectiveTtsRate() {
  const slower =
    els.ttsSlowerToggle?.checked ||
    localStorage.getItem(LS_TTS_SLOWER) === "1";
  return clampRate(slower ? ttsSlowerRate : ttsDefaultRate);
}

function syncTtsRateUi() {
  if (!els.ttsSlowerToggle) return;
  const slower = localStorage.getItem(LS_TTS_SLOWER) === "1";
  els.ttsSlowerToggle.checked = slower;
  if (els.ttsRateLabel) {
    els.ttsRateLabel.textContent = slower ? "Slower" : "Normal";
  }
}

function wireTtsRateToggle() {
  if (!els.ttsSlowerToggle) return;
  syncTtsRateUi();
  els.ttsSlowerToggle.addEventListener("change", () => {
    localStorage.setItem(
      LS_TTS_SLOWER,
      els.ttsSlowerToggle.checked ? "1" : "0"
    );
    syncTtsRateUi();
  });
}

function stopSpeech() {
  if (ttsKeepAlive) {
    clearInterval(ttsKeepAlive);
    ttsKeepAlive = null;
  }
  try {
    window.speechSynthesis?.cancel();
  } catch (_) {}
  currentUtterance = null;
  if (currentAudio) {
    try {
      currentAudio.pause();
      currentAudio.src = "";
    } catch (_) {}
    currentAudio = null;
  }
}

function pickSpanishVoice() {
  const voices = speechSynthesis.getVoices() || [];
  return (
    voices.find(
      (v) =>
        v.lang &&
        v.lang.startsWith("es") &&
        /google|premium|enhanced|neural|natural|samantha|monica|jorge|paulina|juan/i.test(
          v.name
        )
    ) ||
    voices.find((v) => v.lang && v.lang.startsWith("es")) ||
    null
  );
}

function sleepMs(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Browser speech for one segment. rate from effectiveTtsRate() (or override).
 * Resolves when utterance ends or errors.
 */
function speakBrowserSegment(text, rate) {
  return new Promise((resolve) => {
    if (!window.speechSynthesis) {
      console.warn("speechSynthesis unavailable");
      resolve();
      return;
    }
    const u = new SpeechSynthesisUtterance(text);
    currentUtterance = u;
    u.lang = "es-ES";
    u.rate = clampRate(rate);
    const es = pickSpanishVoice();
    if (es) {
      u.voice = es;
      if (es.lang) u.lang = es.lang;
    }
    const done = () => {
      if (currentUtterance === u) currentUtterance = null;
      if (ttsKeepAlive) {
        clearInterval(ttsKeepAlive);
        ttsKeepAlive = null;
      }
      resolve();
    };
    u.onend = done;
    u.onerror = (ev) => {
      console.warn("browser TTS error:", ev?.error || ev);
      done();
    };
    speechSynthesis.speak(u);
    ttsKeepAlive = setInterval(() => {
      try {
        if (!speechSynthesis.speaking) {
          clearInterval(ttsKeepAlive);
          ttsKeepAlive = null;
          return;
        }
        speechSynthesis.pause();
        speechSynthesis.resume();
      } catch (_) {}
    }, 12000);
  });
}

/** @deprecated single-shot name kept for any stray callers */
function speakBrowser(text) {
  return speakBrowserSegment(text, effectiveTtsRate());
}

/**
 * Build speech segments for part-aware playback.
 * When both model and try exist → two segments with gap between them.
 * All other cases → one segment (acknowledge/model/try/recast soft join).
 */
function speechSegmentsFromParts(parts, fallback) {
  if (parts && typeof parts === "object") {
    const model = (parts.model || "").trim();
    const tryP = (parts.try || "").trim();
    if (model && tryP) {
      return [
        { kind: "model", text: model.slice(0, 600) },
        { kind: "try", text: tryP.slice(0, 600) },
      ];
    }
    const core = [parts.model, parts.try, parts.recast]
      .map((s) => (s || "").trim())
      .filter(Boolean);
    if (core.length) {
      return [{ kind: "core", text: core.join(". ").slice(0, 600) }];
    }
    const soft = [parts.acknowledge, parts.model, parts.try]
      .map((s) => (s || "").trim())
      .filter(Boolean);
    if (soft.length) {
      return [{ kind: "soft", text: soft.join(". ").slice(0, 600) }];
    }
  }
  const fb = (fallback || "").trim().slice(0, 600);
  return fb ? [{ kind: "fallback", text: fb }] : [];
}

/** Legacy helper used nowhere critical after part-aware speak; keep for debug. */
function speechTextFromParts(parts, fallback) {
  return speechSegmentsFromParts(parts, fallback)
    .map((s) => s.text)
    .join(". ");
}

function preferServerTts() {
  if (localStorage.getItem("ttsPreferBrowser") === "1") return false;
  if (
    window.__TTS_SERVER__ === true ||
    localStorage.getItem("ttsPreferServer") === "1"
  ) {
    return true;
  }
  if (window.__TTS_SERVER__ === false) return false;
  return serverTtsAvailable;
}

/**
 * Play one server WAV segment; apply playbackRate (Gemini has no numeric rate API).
 */
async function playServerSegment(text, rate) {
  const res = await fetch("/api/audio/speak", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, rate: clampRate(rate) }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail =
      typeof err.detail === "string"
        ? err.detail
        : err.detail
          ? JSON.stringify(err.detail)
          : res.statusText;
    throw new Error(detail || res.statusText);
  }
  const blob = await res.blob();
  if (!blob || blob.size < 64) throw new Error("empty TTS audio");
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  currentAudio = audio;
  // Deterministic rate: API gap workaround for Gemini WAV
  audio.playbackRate = clampRate(rate);
  await new Promise((resolve, reject) => {
    audio.onended = () => {
      URL.revokeObjectURL(url);
      if (currentAudio === audio) currentAudio = null;
      resolve();
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      if (currentAudio === audio) currentAudio = null;
      reject(new Error("audio element error"));
    };
    audio.play().catch(reject);
  });
}

/**
 * AI teach voice = server Gemini TTS; browser fallback.
 * Part-aware: model then ≥400ms then try when both present.
 */
async function speak(text, parts) {
  if (!els.speakToggle?.checked) return;
  const segments = speechSegmentsFromParts(parts, text);
  if (!segments.length) return;
  stopSpeech();

  const rate = effectiveTtsRate();
  const gapMs = Math.max(0, Number(ttsModelTryGapMs) || 400);

  const playBrowserAll = async () => {
    for (let i = 0; i < segments.length; i++) {
      await speakBrowserSegment(segments[i].text, rate);
      if (
        i < segments.length - 1 &&
        segments[i].kind === "model" &&
        segments[i + 1].kind === "try"
      ) {
        await sleepMs(gapMs);
      }
    }
  };

  if (!preferServerTts()) {
    await playBrowserAll();
    return;
  }

  try {
    for (let i = 0; i < segments.length; i++) {
      try {
        await playServerSegment(segments[i].text, rate);
      } catch (segErr) {
        console.warn("server TTS segment failed, browser fallback:", segErr);
        await speakBrowserSegment(segments[i].text, rate);
      }
      if (
        i < segments.length - 1 &&
        segments[i].kind === "model" &&
        segments[i + 1].kind === "try"
      ) {
        await sleepMs(gapMs);
      }
    }
  } catch (e) {
    console.warn("server TTS failed, browser fallback:", e);
    await playBrowserAll();
  }
}

async function initTtsPolicy() {
  try {
    const h = await fetch("/api/health", { credentials: "same-origin" }).then(
      (r) => r.json()
    );
    serverTtsAvailable = !!(h?.tts && h.tts.enabled !== false);
    if (h?.tts?.voice) {
      window.__TTS_VOICE__ = h.tts.voice;
    }
    if (h?.tts?.rate != null) {
      ttsDefaultRate = clampRate(h.tts.rate);
    }
    if (h?.tts?.slower_rate != null) {
      ttsSlowerRate = clampRate(h.tts.slower_rate);
    }
    if (h?.tts?.model_try_gap_ms != null) {
      ttsModelTryGapMs = Math.max(0, Number(h.tts.model_try_gap_ms) || 400);
    }
  } catch (_) {
    serverTtsAvailable = true;
  }
  wireTtsRateToggle();
}
```

Also add to the `els` object at top:

```javascript
  speakToggle: $("speakToggle"),
  ttsSlowerToggle: $("ttsSlowerToggle"),
  ttsRateLabel: $("ttsRateLabel"),
```

`initTtsPolicy().finally(() => startSession());` already exists — keep it; rate UI wires inside `initTtsPolicy`.

---

## 5. Implementation checklist (for the author who can write the repo)

1. `config.py`: `TTS_RATE`, `TTS_SLOWER_RATE`, `TTS_MODEL_TRY_GAP_MS`.
2. `tts.py`: rate arg + short style prefix when \(r &lt; 1.0\); meta flags.
3. `web_app.py`: `SpeakIn.rate`, health TTS fields, headers.
4. `app.js` + `index.html`: rate UI, part-aware segments, gap ≥400 ms, `playbackRate` + browser `rate`.
5. Tests (governance Tier-1): pure unit tests for `speechSegmentsFromParts` logic if extracted, or a tiny node/js fixture; Python test that `_tts_prompt_variants(..., rate=0.9)` contains the slow prefix and `rate=1.0` does not; clamp of `TTS_RATE` env outliers.
6. **Do not claim “improved”** until smoke trajectory shows model→gap→try in a logged turn (telemetry Tier-1 item 1 can log `tts_rate`, `tts_segments`, `gap_ms`).

---

## 6. What I reject / will not countersign as-is

| Claim | Stance |
|-------|--------|
| Style prefix alone satisfies “rate 0.9” for Gemini | **REJECT as sole mechanism** — not quantitative. Require client `playbackRate`. |
| Shipping only config + speak endpoint without `app.js` part split | **REJECT** — the live bug is join-without-pause. |
| Assuming Gemini `speechConfig` has a rate float | **REJECT** — not in current Gemini TTS docs (2026-07-21). |
| Hard-coding 0.9 in JS as “Normal” without health | **AMEND** — read `h.tts.rate` so env overrides work. |

---

## 7. Countersign summary

**COUNTERSIGN** Tier-1 item 3 with **AMENDs**: (1) dual-path rate — browser `SpeechSynthesisUtterance.rate` + Gemini **style prefix when \(r &lt; 1.0\)** **plus** `HTMLAudioElement.playbackRate`; (2) change **`tts.py`** as well as config/web_app/app.js; (3) expose rates/gap on `/api/health`; (4) part-aware model→≥400 ms→try only when both parts non-empty; (5) flag Gemini **no numeric speakingRate** as an open API gap.

Highest-leverage line in the current codebase: `core.join(". ")` in `speechTextFromParts` — that is where the pedagogical pause dies.
