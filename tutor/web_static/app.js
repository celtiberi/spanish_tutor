/* Conversational Spanish tutor — web client
 * Text chat + browser speech (STT/TTS). Right rail: focus + morphology.
 */

const $ = (id) => document.getElementById(id);

const els = {
  messages: $("messages"),
  notes: $("notes"),
  input: $("input"),
  form: $("composer"),
  sendBtn: $("sendBtn"),
  micBtn: $("micBtn"),
  speakToggle: $("speakToggle"),
  sheetToggle: $("sheetToggle"),
  sheetOverlay: $("sheetOverlay"),
  sheetClose: $("sheetClose"),
  sheetBody: $("sheetBody"),
  nextBest: $("nextBest"),
  statusLine: $("statusLine"),
  speechHint: $("speechHint"),
  newChat: $("newChat"),
  resetSheet: $("resetSheet"),
  resetLearner: $("resetLearner"),
  focusPill: $("focusPill"),
  focusTitle: $("focusTitle"),
  focusMeta: $("focusMeta"),
  morphPill: $("morphPill"),
  morphBody: $("morphBody"),
};

let busy = false;
/** Prevents double tutor turns (Send + mic stop racing). */
let turnInFlight = false;
let recognition = null;
let listening = false;

const MIC_IDLE =
  "Mic: click → talk → click again sends the box. Or type and press Send.";
let micIdleHint = MIC_IDLE;

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderTutorParts(parts, fallbackContent) {
  if (!parts || !parts.structured) {
    return esc(fallbackContent || "");
  }
  const blocks = [];
  if (parts.acknowledge) {
    blocks.push(
      `<div class="part part-ack"><span class="part-label">Got it</span>${esc(
        parts.acknowledge
      )}</div>`
    );
  }
  if (parts.recast) {
    blocks.push(
      `<div class="part part-recast"><span class="part-label">Natural Spanish</span>${esc(
        parts.recast
      )}</div>`
    );
  }
  if (parts.explain) {
    const depth = parts.explain_depth === "deep" ? "Why (more)" : "Why";
    blocks.push(
      `<div class="part part-explain"><span class="part-label">${depth}</span>${esc(
        parts.explain
      )}</div>`
    );
  }
  if (parts.model) {
    blocks.push(
      `<div class="part part-model"><span class="part-label">Model</span>${esc(
        parts.model
      )}</div>`
    );
  }
  if (parts.try) {
    blocks.push(
      `<div class="part part-try"><span class="part-label">Your turn</span>${esc(
        parts.try
      )}</div>`
    );
  }
  if (parts.continue) {
    blocks.push(
      `<div class="part part-continue"><span class="part-label">Next</span>${esc(
        parts.continue
      )}</div>`
    );
  }
  return blocks.length ? blocks.join("") : esc(fallbackContent || "");
}

function addBubble(role, content, { inputMode, parts } = {}) {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  const who =
    role === "tutor" ? "Tutor" : role === "you" ? "You" : "";
  const mode =
    inputMode === "speech" ? '<span class="mode-tag">spoken</span>' : "";
  let body;
  if (role === "tutor" && parts && parts.structured) {
    body = renderTutorParts(parts, content);
  } else {
    body = esc(content || "");
  }
  div.innerHTML = who
    ? `<span class="who">${who}${mode}</span>${body}`
    : body;
  els.messages.appendChild(div);
  els.messages.scrollTop = els.messages.scrollHeight;
  return div;
}

function setNotes(notes) {
  if (!notes || !notes.length) {
    els.notes.classList.add("hidden");
    els.notes.textContent = "";
    return;
  }
  els.notes.classList.remove("hidden");
  const warn = notes.includes("rules_backup") && !notes.includes("tool_update");
  els.notes.classList.toggle("warn", warn);
  els.notes.textContent = "sheet: " + notes.join("; ");
}

function pct(c) {
  const n = Number(c) || 0;
  return `${Math.round(n * 100)}%`;
}

function renderFocus(sheet) {
  const f = sheet?.focus || {};
  const nb = sheet?.next_best || {};
  const src = sheet?.focus_source || "static";
  els.focusPill.textContent = f.can_do || nb.can_do || "open";
  els.focusPill.classList.toggle("warn", f.skill_status === "fragile");
  els.focusTitle.textContent =
    f.title || nb.statement || "Open conversation — notice abilities";

  const why = f.blurb || f.reason_ai || f.reason || nb.reason || "—";
  const rows = [
    ["Do", f.activity || nb.activity || nb.stretch || "chat"],
    ["Why", why],
    ["Avoid", f.avoid || nb.avoid || "—", "avoid"],
  ];
  if (f.watch) rows.push(["Watch", f.watch, "avoid"]);
  if (f.error_focus) {
    rows.push([
      "Error",
      `×${f.error_focus.count} ${f.error_focus.label}` +
        (f.error_focus.examples?.length
          ? ` (e.g. ${f.error_focus.examples.slice(-1)[0]})`
          : ""),
      "avoid",
    ]);
  }
  els.focusMeta.innerHTML = rows
    .map(
      ([k, v, cls]) =>
        `<div class="row"><span class="k">${esc(k)}</span>` +
        `<span class="v ${cls || ""}">${esc(v)}</span></div>`
    )
    .join("");

  const chips = [];
  if (f.learner_name) chips.push(`<span class="chip hot">${esc(f.learner_name)}</span>`);
  if (f.error_focus) {
    chips.push(
      `<span class="chip" style="color:var(--warn);border-color:#6b5420">err×${esc(
        String(f.error_focus.count)
      )}</span>`
    );
  }
  if (f.can_do || nb.can_do) {
    chips.push(
      `<span class="chip on">${esc(f.skill_status || "unknown")} · ${pct(
        f.skill_confidence
      )}</span>`
    );
  }
  if (f.band) chips.push(`<span class="chip">${esc(f.band)}</span>`);
  chips.push(
    f.scaffold
      ? `<span class="chip on">EN+ES scaffold</span>`
      : `<span class="chip">more Spanish OK</span>`
  );
  if (f.energy && f.energy !== "unknown") {
    chips.push(`<span class="chip">${esc(f.energy)}</span>`);
  }
  // Source: cheap focus model vs static templates
  const srcLabel = String(src).startsWith("focus_model")
    ? "rail: grok"
    : src === "static_fallback"
      ? "rail: static*"
      : "rail: static";
  chips.push(`<span class="chip" title="${esc(src)}">${esc(srcLabel)}</span>`);
  els.focusMeta.innerHTML += `<div class="status-bar">${chips.join("")}</div>`;
}

function renderMorphology(sheet) {
  const blocks = sheet?.morphology || [];
  const lex = sheet?.lexicon_focus || [];
  if (!blocks.length && !lex.length) {
    els.morphBody.innerHTML =
      '<p class="muted">No morphology target yet — chat a bit and the stretch will fill in.</p>';
    els.morphPill.textContent = "waiting";
    return;
  }
  els.morphPill.textContent =
    blocks.length === 1
      ? blocks[0].lemma || "forms"
      : `${blocks.length} sets`;

  let html = "";
  for (const b of blocks) {
    const learner = b.learner
      ? ` · you: ${b.learner.status || "?"} (${pct(b.learner.confidence)})`
      : "";
    const rows = (b.paradigm || [])
      .map(
        (p) =>
          `<tr class="${p.highlight ? "hi" : ""}">` +
          `<td class="form">${esc(p.form)}</td>` +
          `<td class="person">${esc(p.person || "")}</td>` +
          `<td class="gloss">${esc(p.gloss || "")}</td>` +
          `</tr>`
      )
      .join("");
    html += `
      <div class="morph-block">
        <h3>${esc(b.label || "Forms")}</h3>
        <div class="morph-lemma">${esc(b.pos || "")}${
      b.lemma ? " · " + esc(b.lemma) : ""
    }${esc(learner)}</div>
        <table class="morph-table">${rows}</table>
        ${
          b.note
            ? `<p class="morph-note">${esc(b.note)}</p>`
            : ""
        }
        ${
          b.watch
            ? `<p class="morph-watch">Watch: ${esc(b.watch)}</p>`
            : ""
        }
      </div>`;
  }
  if (lex.length) {
    html += `
      <div class="morph-block">
        <h3>In your lexicon</h3>
        <div class="lex-row">
          ${lex
            .map(
              (x) =>
                `<span class="lex-chip" title="${esc(x.status)}">${esc(
                  x.form
                )}</span>`
            )
            .join("")}
        </div>
      </div>`;
  }
  els.morphBody.innerHTML = html;
}

function renderSheet(sheet) {
  if (!sheet) {
    // Keep rail usable even if API omitted sheet
    els.focusTitle.textContent = "Sheet unavailable — try New chat";
    els.focusPill.textContent = "—";
    els.morphBody.innerHTML =
      '<p class="muted">No sheet data from server.</p>';
    return;
  }
  // Always paint static next_best even if focus block missing
  if (!sheet.focus && sheet.next_best) {
    sheet = {
      ...sheet,
      focus: {
        can_do: sheet.next_best.can_do,
        title: sheet.next_best.statement,
        activity: sheet.next_best.activity || sheet.next_best.stretch,
        reason: sheet.next_best.reason,
        avoid: sheet.next_best.avoid,
      },
    };
  }
  try {
    renderFocus(sheet);
  } catch (e) {
    console.error("renderFocus", e);
    els.focusTitle.textContent = "Focus render error";
  }
  try {
    renderMorphology(sheet);
  } catch (e) {
    console.error("renderMorphology", e);
    els.morphBody.innerHTML =
      '<p class="muted">Morphology render error — see console.</p>';
  }

  const nb = sheet.next_best || {};
  if (els.nextBest) {
    els.nextBest.innerHTML = `
      <div><strong>Next best</strong> ${esc(nb.can_do || "—")}</div>
      <div>${esc(nb.activity || nb.stretch || "")}</div>
      <div style="color:var(--muted);margin-top:0.35rem">${esc(nb.reason || "")}</div>
      <div style="color:var(--warn);margin-top:0.25rem">avoid: ${esc(nb.avoid || "—")}</div>
    `;
  }
  if (els.sheetBody) {
    els.sheetBody.textContent = sheet.human || JSON.stringify(sheet, null, 2);
  }
}

let currentAudio = null;

function stopSpeech() {
  try {
    window.speechSynthesis?.cancel();
  } catch (_) {}
  if (currentAudio) {
    try {
      currentAudio.pause();
      currentAudio.src = "";
    } catch (_) {}
    currentAudio = null;
  }
}

function speakBrowser(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "es-ES";
  u.rate = 0.95;
  const voices = speechSynthesis.getVoices();
  const es =
    voices.find(
      (v) =>
        v.lang &&
        v.lang.startsWith("es") &&
        /google|premium|enhanced|neural|natural/i.test(v.name)
    ) || voices.find((v) => v.lang && v.lang.startsWith("es"));
  if (es) u.voice = es;
  speechSynthesis.speak(u);
}

/** Prefer server Gemini TTS; fall back to browser speechSynthesis (macOS voice). */
async function speak(text) {
  if (!els.speakToggle.checked) return;
  const t = (text || "").trim();
  if (!t) return;
  stopSpeech();

  try {
    const res = await fetch("/api/audio/speak", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: t }),
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
    audio.onended = () => {
      URL.revokeObjectURL(url);
      if (currentAudio === audio) currentAudio = null;
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      console.warn("server TTS audio play failed → browser voice");
      if (typeof setMicStatus === "function") {
        setMicStatus(
          "error",
          "Server voice failed to play — using Mac/browser voice"
        );
      }
      speakBrowser(t);
    };
    await audio.play();
  } catch (e) {
    console.warn("server TTS failed, browser fallback:", e);
    if (typeof setMicStatus === "function") {
      setMicStatus(
        "error",
        "Server voice offline — using Mac/browser voice (not Gemini)"
      );
    }
    speakBrowser(t);
  }
}

function updateComposerControls() {
  // Send greyed while mic recording or a turn is in flight
  const sendOff = busy || listening || turnInFlight;
  els.sendBtn.disabled = sendOff;
  els.sendBtn.classList.toggle("mic-locked", listening || turnInFlight);
  els.sendBtn.title = listening
    ? "Mic is on — click the mic again to send the box"
    : turnInFlight
      ? "Wait for the tutor…"
      : "Send message";
  // Keep box editable while recording so user can correct captions
  els.input.disabled = (busy || turnInFlight) && !listening;
  // Block starting a second mic session while a turn runs
  els.micBtn.disabled = turnInFlight && !listening;
}

function setBusy(on) {
  busy = on;
  updateComposerControls();
}

/** Synchronous single-flight guard for tutor turns. */
function beginTurn() {
  if (turnInFlight || busy) return false;
  turnInFlight = true;
  busy = true;
  updateComposerControls();
  return true;
}

function endTurn() {
  turnInFlight = false;
  busy = false;
  updateComposerControls();
}

/** Tear down mic without sending (used when Send wins the race). */
function forceStopMicOnly() {
  if (!listening && !streamActive && !sttWs && !mediaStream) return;
  listening = false;
  streamActive = false;
  els.micBtn.classList.remove("listening");
  els.micBtn.setAttribute("aria-pressed", "false");
  els.micBtn.title = "Click to record";
  try {
    if (sttWs && sttWs.readyState === WebSocket.OPEN) {
      sttWs.send(JSON.stringify({ type: "cancel" }));
    }
  } catch (_) {}
  closeSttWs();
  stopCapture();
  // Clear any pending final waiters without starting a send
  if (finalResolver) {
    const r = finalResolver;
    finalResolver = null;
    finalRejecter = null;
    r({ type: "final", text: "", empty: true, reason: "cancelled" });
  }
  updateComposerControls();
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || data.error || res.statusText || "Request failed");
  }
  return data;
}

function showMessages(list) {
  els.messages.innerHTML = "";
  for (const m of list || []) {
    const role = m.role === "tutor" ? "tutor" : m.role === "you" ? "you" : "system";
    addBubble(role, m.content, {
      inputMode: m.input_mode,
      parts: m.parts,
    });
  }
}

async function startSession() {
  setBusy(true);
  els.statusLine.textContent = "Connecting…";
  try {
    const data = await api("/api/session/start", { method: "POST", body: "{}" });
    showMessages(data.messages);
    setNotes(data.notes);
    renderSheet(data.sheet);
    els.statusLine.textContent = `Model ${data.model || "tutor"} · character sheet live`;
    if (data.reply && !data.resumed) speak(data.reply);
  } catch (e) {
    addBubble("system", `Could not start: ${e.message}`);
    els.statusLine.textContent = "Error — check API keys / server logs";
  } finally {
    setBusy(false);
    els.input.focus();
  }
}

/**
 * @param {string} text
 * @param {string} inputMode
 * @param {{ alreadyLocked?: boolean }} [opts]
 */
async function sendMessage(text, inputMode = "text", opts = {}) {
  text = (text || "").trim();
  if (!text) return false;
  // One tutor turn at a time (blocks Send + mic-stop double fire)
  if (!opts.alreadyLocked) {
    if (!beginTurn()) {
      console.warn("sendMessage blocked — turn already in flight");
      return false;
    }
  } else if (!turnInFlight) {
    if (!beginTurn()) return false;
  }
  // If mic still open, kill it without a second send
  forceStopMicOnly();

  addBubble("you", text, { inputMode });
  els.input.value = "";
  els.input.classList.remove("speech-interim");
  autosize();
  setMicStatus("working", "Tutor is thinking…");
  const typing = addBubble("system", "Tutor is thinking…");
  typing.classList.add("typing");
  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: text, input_mode: inputMode }),
    });
    typing.remove();
    addBubble("tutor", data.reply, { parts: data.parts });
    setNotes(data.notes);
    renderSheet(data.sheet);
    speak(data.reply);
    setMicStatus("idle", micIdleHint);
    return true;
  } catch (e) {
    typing.remove();
    addBubble("system", `Error: ${e.message}`);
    setMicStatus("error", `Error: ${e.message}`);
    return false;
  } finally {
    endTurn();
    els.input.focus();
  }
}

function autosize() {
  const t = els.input;
  t.style.height = "auto";
  t.style.height = Math.min(t.scrollHeight, 140) + "px";
}

// ——— Mic: click → stream PCM → live captions in the text box → click → final → send ———
// Interim STT updates the box while speaking. If the user edits the box, we keep
// their text (final STT must not overwrite corrections).
// Silence is gated (models invent Spanish on empty audio).

const MIC_MIN_PEAK_RMS = 0.012;
const MIC_MIN_MS = 400;
const PCM_TARGET_RATE = 16000;

let mediaStream = null;
let audioCtx = null;
let scriptNode = null;
let silentGain = null;
let sttWs = null;
let peakRms = 0;
let lastRms = 0;
let recordTimer = null;
let recordStartedAt = 0;
let interimText = "";
/** Last text written into the box by STT (interim or final). */
let lastAutoCaption = "";
/** True once the user types/edits away from lastAutoCaption. */
let userEditedCaption = false;
let sttBackend = "";
let finalResolver = null;
let finalRejecter = null;
let streamActive = false;

/** @param {"idle"|"recording"|"working"|"error"} state */
function setMicStatus(state, message) {
  els.speechHint.dataset.state = state || "idle";
  els.speechHint.classList.toggle("listening-active", state === "recording");
  els.speechHint.classList.toggle("mic-working", state === "working");
  els.speechHint.classList.toggle("mic-error", state === "error");
  if (message !== undefined) els.speechHint.textContent = message;
}

function setListeningUi(on) {
  listening = on;
  els.micBtn.classList.toggle("listening", on);
  els.micBtn.setAttribute("aria-pressed", on ? "true" : "false");
  els.micBtn.title = on
    ? "Click to stop and send what's in the box"
    : "Click to record";
  updateComposerControls();
}

function setInputBox(text, { interim = false, fromStt = false } = {}) {
  const t = text || "";
  // Never clobber a user edit with STT updates
  if (fromStt && userEditedCaption) return;
  els.input.value = t;
  els.input.classList.toggle("speech-interim", !!interim && !!t);
  if (fromStt || interim) {
    lastAutoCaption = t;
  }
  autosize();
}

function noteUserEditFromInput() {
  if (!listening && !streamActive) return;
  const cur = (els.input.value || "").trim();
  const auto = (lastAutoCaption || "").trim();
  if (cur !== auto) userEditedCaption = true;
}

function formatRecSecs() {
  const secs = recordStartedAt
    ? Math.max(0, Math.floor((Date.now() - recordStartedAt) / 1000))
    : 0;
  const ss = String(secs % 60).padStart(2, "0");
  const mm = String(Math.floor(secs / 60));
  return `${mm}:${ss}`;
}

function levelBars(rms) {
  const n = Math.min(5, Math.max(0, Math.round(rms * 40)));
  return "▁▂▃▄▅".slice(0, Math.max(1, n)) || "▁";
}

function paintRecordingStatus() {
  if (!listening) return;
  const bars = levelBars(Math.max(lastRms, peakRms * 0.4));
  if (userEditedCaption) {
    setMicStatus(
      "recording",
      `● Recording ${formatRecSecs()} ${bars} — your edit kept · click mic to send`
    );
    return;
  }
  if (interimText) {
    setMicStatus(
      "recording",
      `● Live caption ${formatRecSecs()} ${bars} — edit box anytime · click mic when done`
    );
    return;
  }
  const heard =
    peakRms >= MIC_MIN_PEAK_RMS
      ? "hearing you — first words appear in a moment…"
      : "waiting for voice…";
  setMicStatus(
    "recording",
    `● Recording ${formatRecSecs()} ${bars} — ${heard}`
  );
}

function startRecordUi() {
  stopRecordUi();
  recordStartedAt = Date.now();
  peakRms = 0;
  lastRms = 0;
  interimText = "";
  lastAutoCaption = "";
  userEditedCaption = false;
  setInputBox("");
  els.input.placeholder = "Speak… edit the text anytime before send";
  paintRecordingStatus();
  recordTimer = setInterval(() => {
    if (listening) paintRecordingStatus();
  }, 200);
}

function stopRecordUi() {
  if (recordTimer) {
    clearInterval(recordTimer);
    recordTimer = null;
  }
  recordStartedAt = 0;
  els.input.placeholder = "Type… or click mic, talk, click again";
}

function floatTo16BitPCM(float32) {
  const out = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    let s = Math.max(-1, Math.min(1, float32[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

function downsampleTo16k(float32, fromRate) {
  if (fromRate === PCM_TARGET_RATE) return float32;
  const ratio = fromRate / PCM_TARGET_RATE;
  const newLen = Math.floor(float32.length / ratio);
  if (newLen <= 0) return new Float32Array(0);
  const result = new Float32Array(newLen);
  for (let i = 0; i < newLen; i++) {
    // simple average over the source window
    const start = Math.floor(i * ratio);
    const end = Math.min(float32.length, Math.floor((i + 1) * ratio));
    let acc = 0;
    let n = 0;
    for (let j = start; j < end; j++) {
      acc += float32[j];
      n++;
    }
    result[i] = n ? acc / n : float32[start] || 0;
  }
  return result;
}

function wsSttUrl() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}/ws/stt`;
}

function closeSttWs() {
  streamActive = false;
  if (sttWs) {
    try {
      if (sttWs.readyState === WebSocket.OPEN) {
        sttWs.send(JSON.stringify({ type: "cancel" }));
      }
      sttWs.close();
    } catch (_) {}
    sttWs = null;
  }
  if (finalRejecter) {
    const r = finalRejecter;
    finalResolver = null;
    finalRejecter = null;
    r(new Error("STT connection closed"));
  }
}

function stopCapture() {
  stopRecordUi();
  if (scriptNode) {
    try {
      scriptNode.disconnect();
    } catch (_) {}
    scriptNode.onaudioprocess = null;
    scriptNode = null;
  }
  if (silentGain) {
    try {
      silentGain.disconnect();
    } catch (_) {}
    silentGain = null;
  }
  if (audioCtx) {
    try {
      audioCtx.close();
    } catch (_) {}
    audioCtx = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => {
      try {
        t.stop();
      } catch (_) {}
    });
    mediaStream = null;
  }
}

function openSttSocket() {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsSttUrl());
    sttWs = ws;
    let settled = false;
    const timer = setTimeout(() => {
      if (!settled) {
        settled = true;
        reject(new Error("STT WebSocket timeout"));
        try {
          ws.close();
        } catch (_) {}
      }
    }, 8000);

    ws.binaryType = "arraybuffer";
    ws.onopen = () => {
      /* wait for ready */
    };
    ws.onerror = () => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        reject(new Error("STT WebSocket failed"));
      }
    };
    ws.onclose = () => {
      if (sttWs === ws) sttWs = null;
      // Prefer resolving empty over hanging; stopMicAndSend handles empty
      if (finalResolver) {
        const r = finalResolver;
        finalResolver = null;
        finalRejecter = null;
        r({ type: "final", text: "", empty: true, reason: "socket_closed" });
      } else if (finalRejecter) {
        const r = finalRejecter;
        finalResolver = null;
        finalRejecter = null;
        r(new Error("STT socket closed before final"));
      }
    };
    ws.onmessage = (ev) => {
      let msg;
      try {
        msg = JSON.parse(ev.data);
      } catch (_) {
        return;
      }
      if (msg.type === "ready" && !settled) {
        settled = true;
        clearTimeout(timer);
        sttBackend = msg.backend || "stream";
        resolve(ws);
        return;
      }
      if (msg.type === "interim" && msg.text) {
        interimText = String(msg.text).trim();
        // Live captions → box, unless the user already corrected text
        if ((listening || streamActive) && !userEditedCaption) {
          setInputBox(interimText, { interim: true, fromStt: true });
          paintRecordingStatus();
        } else if (listening || streamActive) {
          paintRecordingStatus();
        }
        return;
      }
      if (msg.type === "status") {
        if (msg.backend) sttBackend = msg.backend;
        if (msg.phase === "transcribing") {
          setMicStatus("working", "Transcribing…");
        } else if (msg.phase === "fallback_batch") {
          setMicStatus("working", "Streaming unavailable — batch STT…");
        } else if (msg.phase === "listening" || msg.phase === "recording") {
          if (listening) paintRecordingStatus();
        }
        return;
      }
      if (msg.type === "final") {
        if (finalResolver) {
          const r = finalResolver;
          finalResolver = null;
          finalRejecter = null;
          r(msg);
        }
        return;
      }
      if (msg.type === "error") {
        if (finalRejecter) {
          const r = finalRejecter;
          finalResolver = null;
          finalRejecter = null;
          r(new Error(msg.message || "STT error"));
        } else if (!settled) {
          settled = true;
          clearTimeout(timer);
          reject(new Error(msg.message || "STT error"));
        } else {
          setMicStatus("error", msg.message || "STT error");
        }
      }
    };
  });
}

async function startMic() {
  if (busy || listening || turnInFlight) return;
  if (!window.isSecureContext) {
    setMicStatus("error", "Open http://127.0.0.1:8765 for mic (not file://).");
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    setMicStatus("error", "Mic not supported in this browser.");
    return;
  }

  stopSpeech();
  closeSttWs();
  setInputBox("");
  interimText = "";
  setMicStatus("working", "Starting microphone…");

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        channelCount: 1,
      },
    });
  } catch (e) {
    const name = e?.name || "";
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      setMicStatus("error", "Mic blocked — allow microphone in the address bar.");
    } else if (name === "NotFoundError") {
      setMicStatus("error", "No microphone found.");
    } else {
      setMicStatus("error", `Mic error: ${name || e}`);
    }
    return;
  }

  try {
    setMicStatus("working", "Connecting speech stream…");
    const ws = await openSttSocket();
    ws.send(JSON.stringify({ type: "start" }));
    streamActive = true;

    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") await audioCtx.resume();
    const source = audioCtx.createMediaStreamSource(mediaStream);
    const bufferSize = 4096;
    scriptNode = audioCtx.createScriptProcessor(bufferSize, 1, 1);
    const fromRate = audioCtx.sampleRate || 48000;

    scriptNode.onaudioprocess = (ev) => {
      if (!listening || !streamActive || !sttWs || sttWs.readyState !== WebSocket.OPEN) {
        return;
      }
      const input = ev.inputBuffer.getChannelData(0);
      // RMS for level UI + gate
      let acc = 0;
      for (let i = 0; i < input.length; i++) acc += input[i] * input[i];
      const rms = Math.sqrt(acc / input.length);
      lastRms = rms;
      if (rms > peakRms) peakRms = rms;

      const down = downsampleTo16k(input, fromRate);
      const pcm = floatTo16BitPCM(down);
      try {
        sttWs.send(pcm.buffer);
      } catch (_) {
        /* socket may be closing */
      }
    };

    silentGain = audioCtx.createGain();
    silentGain.gain.value = 0;
    source.connect(scriptNode);
    scriptNode.connect(silentGain);
    silentGain.connect(audioCtx.destination);

    setListeningUi(true);
    startRecordUi();
  } catch (e) {
    stopCapture();
    closeSttWs();
    setListeningUi(false);
    setMicStatus("error", `Mic setup failed: ${e.message || e}`);
  }
}

function waitForFinal() {
  return new Promise((resolve, reject) => {
    finalResolver = resolve;
    finalRejecter = reject;
    setTimeout(() => {
      if (finalRejecter === reject) {
        finalResolver = null;
        finalRejecter = null;
        reject(new Error("Timed out waiting for transcript"));
      }
    }, 30000);
  });
}

async function stopMicAndSend() {
  if (!listening) return;
  // Another turn already running (e.g. Send just won) — only stop the mic
  if (turnInFlight || busy) {
    forceStopMicOnly();
    return;
  }

  const elapsed = recordStartedAt ? Date.now() - recordStartedAt : 0;
  const peak = peakRms;
  // Whatever is in the box at stop is authoritative
  noteUserEditFromInput();
  let boxText = (els.input.value || "").trim();

  // Claim turn before listening=false re-enables Send
  const locked = beginTurn();
  if (!locked) {
    forceStopMicOnly();
    return;
  }

  setListeningUi(false);
  streamActive = false;

  // Stop mic capture immediately
  if (scriptNode) {
    try {
      scriptNode.disconnect();
    } catch (_) {}
    scriptNode.onaudioprocess = null;
    scriptNode = null;
  }

  // Box has text → send it under the lock we already hold
  if (boxText) {
    stopCapture();
    closeSttWs();
    els.input.classList.remove("speech-interim");
    lastAutoCaption = boxText;
    userEditedCaption = false;
    setMicStatus("working", "Sending…");
    await sendMessage(boxText, "speech", { alreadyLocked: true });
    return;
  }

  // Box empty: try one final STT pass, then send if anything comes back
  if (elapsed < MIC_MIN_MS) {
    stopCapture();
    closeSttWs();
    endTurn();
    setMicStatus("error", "Too short — click mic, talk, click again.");
    return;
  }
  if (peak < MIC_MIN_PEAK_RMS) {
    stopCapture();
    closeSttWs();
    endTurn();
    setMicStatus(
      "error",
      "No voice detected — check the mic is unmuted and speak closer."
    );
    return;
  }

  if (!sttWs || sttWs.readyState !== WebSocket.OPEN) {
    stopCapture();
    closeSttWs();
    const fallback = (interimText || "").trim();
    if (fallback) {
      await sendMessage(fallback, "speech", { alreadyLocked: true });
      return;
    }
    endTurn();
    setMicStatus("error", "Speech stream lost — try again.");
    return;
  }

  // Already locked from beginTurn above — wait for final STT under that lock
  setMicStatus("working", "Transcribing…");
  try {
    sttWs.send(JSON.stringify({ type: "stop" }));
    const result = await waitForFinal();
    stopCapture();
    try {
      sttWs.close();
    } catch (_) {}
    sttWs = null;

    boxText = (els.input.value || "").trim();
    let text =
      boxText ||
      (result.text || "").trim() ||
      (interimText || "").trim();
    if (!text) {
      setInputBox("");
      const why =
        result.reason === "no_voice"
          ? "No voice detected — speak closer and try again."
          : result.reason === "socket_closed"
            ? "Connection dropped during STT — try again."
            : "No speech heard — try again a bit louder.";
      setMicStatus("error", why);
      endTurn();
      return;
    }
    setInputBox(text, { interim: false });
    await sendMessage(text, "speech", { alreadyLocked: true });
  } catch (e) {
    stopCapture();
    closeSttWs();
    const box = (els.input.value || "").trim() || (interimText || "").trim();
    if (box) {
      await sendMessage(box, "speech", { alreadyLocked: true });
      return;
    }
    endTurn();
    setMicStatus("error", `Transcribe failed: ${e.message || e}`);
  }
}

function initSpeech() {
  if (!window.isSecureContext) {
    setMicStatus("error", "Open via http://127.0.0.1:8765 for mic access.");
  } else if (!navigator.mediaDevices?.getUserMedia) {
    setMicStatus("error", "Mic not supported in this browser.");
    els.micBtn.disabled = true;
  } else {
    setMicStatus("idle", micIdleHint);
  }
  els.micBtn.setAttribute("aria-pressed", "false");
  fetch("/api/health")
    .then((r) => r.json())
    .then((h) => {
      if (h?.stt?.stream) {
        sttBackend = h.stt.stream_backend || "gemini";
        const chirp = h.stt.chirp?.available ? "chirp ASR" : "gemini STT";
        micIdleHint =
          `Mic: click → talk (live ${chirp}) → click again sends the box. Send button for typing.`;
        if (!listening && !busy) setMicStatus("idle", micIdleHint);
      }
    })
    .catch(() => {});
}

els.micBtn.addEventListener("click", (e) => {
  e.preventDefault();
  e.stopPropagation();
  if (turnInFlight || (busy && !listening)) {
    setMicStatus("working", "Wait for the tutor…");
    return;
  }
  if (listening) stopMicAndSend();
  else startMic();
});

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  // Mic owns send while recording; single-flight otherwise
  if (listening || turnInFlight || busy) return;
  sendMessage(els.input.value, "text");
});

els.input.addEventListener("input", () => {
  noteUserEditFromInput();
  autosize();
});
els.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (listening || turnInFlight || busy) return;
    sendMessage(els.input.value, "text");
  }
});

function setSheetOpen(open) {
  if (!els.sheetOverlay) return;
  els.sheetOverlay.hidden = !open;
  if (els.sheetToggle) {
    els.sheetToggle.textContent = open ? "Hide sheet" : "Full sheet";
    els.sheetToggle.setAttribute("aria-expanded", open ? "true" : "false");
  }
  document.body.style.overflow = open ? "hidden" : "";
}

els.sheetToggle?.addEventListener("click", () => {
  // Toggle: when overlay has [hidden], open it
  setSheetOpen(!!els.sheetOverlay?.hidden);
});

els.sheetClose?.addEventListener("click", () => setSheetOpen(false));

els.sheetOverlay?.addEventListener("click", (e) => {
  // Click backdrop (not the modal card) to close
  if (e.target === els.sheetOverlay) setSheetOpen(false);
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && els.sheetOverlay && !els.sheetOverlay.hidden) {
    setSheetOpen(false);
  }
});

els.newChat.addEventListener("click", async () => {
  if (busy || turnInFlight) return;
  setBusy(true);
  try {
    const data = await api("/api/session/reset", {
      method: "POST",
      body: JSON.stringify({ reset_sheet: false }),
    });
    showMessages(data.messages);
    setNotes(data.notes);
    renderSheet(data.sheet);
    setMicStatus("idle", "New chat — same learner sheet");
    speak(data.reply);
  } catch (e) {
    addBubble("system", e.message);
  } finally {
    setBusy(false);
  }
});

async function hardResetLearner() {
  if (busy || turnInFlight) {
    addBubble("system", "Wait for the current turn to finish, then Reset learner again.");
    return;
  }
  if (
    !confirm(
      "Hard reset: wipe the character sheet (skills, errors, name) and start a blank learner?\n\nThis cannot be undone."
    )
  ) {
    return;
  }
  setBusy(true);
  setSheetOpen(false);
  try {
    forceStopMicOnly();
  } catch (_) {}
  try {
    const data = await api("/api/session/reset", {
      method: "POST",
      body: JSON.stringify({ reset_sheet: true }),
    });
    // Full UI wipe before painting the new open
    els.messages.innerHTML = "";
    showMessages(data.messages);
    setNotes(
      (data.notes || []).concat(
        data.fresh_learner || data.sheet_reset
          ? ["fresh_learner"]
          : ["reset_may_have_failed"]
      )
    );
    renderSheet(data.sheet);
    els.statusLine.textContent = data.fresh_learner
      ? `Fresh learner · model ${data.model || "tutor"}`
      : `Model ${data.model || "tutor"} · character sheet live`;
    setMicStatus("idle", "Fresh learner — sheet wiped");
    addBubble(
      "system",
      data.fresh_learner
        ? "Hard reset complete: blank character sheet + new session."
        : "Reset ran but server did not confirm fresh_learner — check sheet."
    );
    speak(data.reply);
  } catch (e) {
    addBubble("system", `Reset failed: ${e.message}`);
  } finally {
    setBusy(false);
    els.input.focus();
  }
}

els.resetSheet?.addEventListener("click", () => hardResetLearner());
els.resetLearner?.addEventListener("click", () => hardResetLearner());

if (window.speechSynthesis) {
  speechSynthesis.getVoices();
  speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
}

initSpeech();
startSession();
