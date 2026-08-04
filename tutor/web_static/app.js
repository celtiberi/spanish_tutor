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
  ttsRateSlider: $("ttsRateSlider"),
  ttsRateLabel: $("ttsRateLabel"),
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
  scoreBoard: $("scoreBoard"),
  countDurable: $("countDurable"),
  countKnown: $("countKnown"),
  countEmerging: $("countEmerging"),
  scoreDelta: $("scoreDelta"),
  journeyCard: $("journeyCard"),
  journeyToggle: $("journeyToggle"),
  journeyBody: $("journeyBody"),
  journeyFoot: $("journeyFoot"),
  costBoard: $("costBoard"),
  costValue: $("costValue"),
  costBreakdown: $("costBreakdown"),

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

function renderTeachImages(parts) {
  const imgs = parts?.teach_images;
  if (!imgs || !imgs.length) return "";
  return imgs
    .map((img) => {
      const form = esc(img.form || img.concept || "");
      const cap = esc(img.caption || "");
      const url = esc(img.url || "");
      if (!url) return "";
      return (
        `<div class="part part-image">` +
        `<span class="part-label">See · ${form}</span>` +
        `<figure class="teach-figure">` +
        `<img class="teach-img" src="${url}" alt="${form}" loading="lazy" />` +
        (cap ? `<figcaption class="teach-cap"><strong>${form}</strong> — ${cap}</figcaption>` : `<figcaption class="teach-cap"><strong>${form}</strong></figcaption>`) +
        `</figure></div>`
      );
    })
    .join("");
}

// (renderModeBadge DELETED 2026-08-03 with the mode router — parts.mode /
// parts.mode_decision no longer exist.)

function renderTutorParts(parts, fallbackContent) {
  if (!parts || !parts.structured) {
    const img = renderTeachImages(parts);
    return img + esc(fallbackContent || "");
  }
  const blocks = [];
  // Teach image first: associate form with meaning before/with the models
  const imgBlock = renderTeachImages(parts);
  if (imgBlock) blocks.push(imgBlock);

  // Labeled sections (USER 2026-08-03: "the separation helped me know
  // where to look and what it was for") with tooltips explaining each
  // section's job. The acknowledge line stays unlabeled — it is just
  // the tutor reacting. Part order: why never precedes the word
  // (2026-07-29): recast → model → explain → try.
  if (parts.acknowledge) {
    blocks.push(`<p class="part-flow part-ack">${esc(parts.acknowledge)}</p>`);
  }
  const SECTIONS = [
    ["recast", "In natural Spanish",
     "Your sentence, the way a native speaker would say it. Worth re-reading."],
    ["model", "Example",
     "Spanish for you to absorb — often contains what you'll practice next."],
    ["explain", "Why",
     "The meaning or grammar note behind it."],
    ["try", "Your turn",
     "Respond to this — say or type it in Spanish."],
  ];
  for (const [key, label, tip] of SECTIONS) {
    const text = parts[key];
    if (!text) continue;
    const lbl =
      key === "explain" && parts.explain_depth === "deep"
        ? "Why (more)"
        : label;
    blocks.push(
      `<div class="part part-${key}">` +
        `<span class="part-label" title="${esc(tip)}">${esc(lbl)}</span>` +
        esc(text) +
        `</div>`
    );
  }
  // Trailing prose (the <continue> slot left the shape 2026-08-03; the
  // parser still buckets stray closing text here) — unlabeled, muted.
  if (parts.continue) {
    blocks.push(`<p class="part-flow part-continue">${esc(parts.continue)}</p>`);
  }
  // Gate failure (2026-08-01): never hide — show faults + the raw attempt.
  if (parts.gate_fail || parts.gate_hold) {
    const faults = (parts.gate_faults || parts.output_gate?.faults || [])
      .map((f) => esc(String(f)))
      .join(", ");
    blocks.unshift(
      `<div class="part part-gate-fail"><span class="part-label">GATE FAIL</span>` +
        `<span class="gate-fail-body">` +
        `Model reply failed the quality gate` +
        (faults ? `: <code>${faults}</code>` : "") +
        `. This is a system/prompt problem — not normal teaching. ` +
        `The attempt is shown below so it is not hidden.</span></div>`
    );
  }
  if (parts.gate_hold && !blocks.some((b) => b.includes("part-"))) {
    blocks.push(
      `<div class="part part-gate-fail"><span class="part-label">GATE FAIL</span>` +
        `<span class="gate-fail-body">Reply was held empty — investigate gate notes.</span></div>`
    );
  }
  return blocks.length ? blocks.join("") : esc(fallbackContent || "");
}

function addBubble(role, content, { inputMode, parts, timing } = {}) {
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
  let timeLine = "";
  if (role === "tutor") {
    const at = new Date().toLocaleTimeString();
    const bits = [at];
    if (timing?.model_ms != null) bits.push(`model ${(timing.model_ms / 1000).toFixed(1)}s`);
    if (timing?.server_ms != null) bits.push(`server ${(timing.server_ms / 1000).toFixed(1)}s`);
    if (timing?.total_ms != null) bits.push(`round-trip ${(timing.total_ms / 1000).toFixed(1)}s`);
    timeLine = `<span class="bubble-time">${esc(bits.join(" · "))}</span>`;
  }
  div.innerHTML = who
    ? `<span class="who">${who}${mode}</span>${body}${timeLine}`
    : body + timeLine;
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
  // Sheet projection (the this-turn mode pill died with the router)
  els.focusPill.textContent = f.can_do || "sheet";
  els.focusPill.classList.toggle("warn", f.skill_status === "fragile");
  els.focusTitle.textContent =
    f.title || nb.statement || "Conversation";

  const why = f.blurb || f.reason_ai || f.why || f.reason || "—";
  const rows = [
    ["Up next", f.activity || "chat"],
    ["Why", why],
  ];
  // Sheet longer arc — only if different from this-turn title
  const sheetArc = f.sheet_title || nb.statement || "";
  if (sheetArc && sheetArc !== f.title) {
    rows.push([
      "Sheet arc",
      `${f.can_do || nb.can_do || ""} · ${sheetArc}`.replace(/^ · /, ""),
    ]);
  }
  if (f.avoid || nb.avoid) {
    rows.push(["Avoid", f.avoid || nb.avoid || "—", "avoid"]);
  }
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
  if (f.form_focus) {
    chips.push(`<span class="chip on">${esc(f.form_focus)}</span>`);
  }
  if (f.can_do || nb.can_do) {
    chips.push(
      `<span class="chip">${esc(f.can_do || nb.can_do)} · ${esc(
        f.skill_status || "unknown"
      )}</span>`
    );
  }
  chips.push(
    f.scaffold
      ? `<span class="chip on">EN+ES scaffold</span>`
      : `<span class="chip">more Spanish OK</span>`
  );
  const srcLabel = f.live
    ? "live mode"
    : String(src).startsWith("focus_model")
      ? "rail: grok"
      : "rail: static";
  chips.push(`<span class="chip" title="${esc(src)}">${esc(srcLabel)}</span>`);
  els.focusMeta.innerHTML += `<div class="status-bar">${chips.join("")}</div>`;
}

function renderMorphology(sheet) {
  const blocks = sheet?.morphology || [];
  const lex = sheet?.lexicon_focus || [];
  if (!blocks.length && !lex.length) {
    els.morphBody.innerHTML =
      '<p class="muted">The tutor puts a verb table here when a form matters — none yet this chat.</p>';
    els.morphPill.textContent = "—";
    return;
  }
  els.morphPill.textContent =
    blocks.length === 1
      ? blocks[0].lemma || "forms"
      : `${blocks.length} sets`;

  let html = "";
  for (const b of blocks) {
    // §1.1b honesty carve-out: agenda-sourced blocks render only as
    // labeled "up next" — never silently as this-turn engagement.
    const known = b.learner && b.learner.status === "known";
    const upNext =
      b.live === false
        ? known
          ? ` <span class="muted" title="a form your sheet shows you know — reference table, not this turn's focus">· you know this</span>`
          : ` <span class="muted" title="a form your sheet shows in progress — reference table, not this turn's focus">· working on</span>`
        : "";
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
    const when = b.ts
      ? `<span class="muted morph-when" title="when the tutor sent this card">· ${esc(String(b.ts).replace("T", " ").slice(11, 16))}</span>`
      : "";
    html += `
      <div class="morph-block">
        <h3>${esc(b.label || "Forms")}${upNext}${when}</h3>
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

/** Last rendered durable count — used to show +Δ when it advances. */
let lastDurableCount = null;
let scoreFlashTimer = null;
/** Latest /api/progress payload (grade feed + countable header). */
let lastProgress = null;

function renderCost(sheet) {
  if (!els.costBoard || !els.costValue) return;
  const c = sheet?.session_cost;
  if (!c) return;
  const total = Number(c.total_usd || 0);
  const unpriced = c.unpriced_models || [];
  // §3.4 rider (2026-08-04): the flag rides the surface it protects — a
  // clean dollar figure while models run unpriced is a swallow.
  els.costValue.textContent = unpriced.length
    ? `$${total.toFixed(total < 0.1 ? 4 : 2)} ⚠ UNPRICED: ${unpriced.join(", ")}`
    : `$${total.toFixed(total < 0.1 ? 4 : 2)}`;
  els.costValue.classList.toggle("cost-unpriced", unpriced.length > 0);
  const cats = c.by_category || {};
  const parts = Object.entries(cats)
    .sort((a, b) => (b[1]?.usd || 0) - (a[1]?.usd || 0))
    .map(([k, v]) => `${k} $${Number(v?.usd || 0).toFixed(4)}`);
  if (els.costBreakdown) {
    const today = Number(c.today_usd || 0);
    els.costBreakdown.textContent = parts.length
      ? parts.join(" · ")
      : "no API calls yet";
    els.costBoard.title =
      `API spend this chat session.\n` +
      (parts.length ? parts.join("\n") + "\n" : "") +
      (c.unpriced_models?.length
        ? `UNPRICED models (add to tutor/costs.py): ${c.unpriced_models.join(", ")}\n`
        : "") +
      `All processes today (ledger): $${today.toFixed(4)}`;
  }
}

/** Countable-header fallback from the ability sheet. */
function countsFromSheet(sheet) {
  let known = 0;
  let emerging = 0;
  for (const v of Object.values(sheet?.skills || {})) {
    const st = String(v?.status || "");
    if (st === "known") known += 1;
    else if (st === "emerging") emerging += 1;
  }
  return { durable: known, known, emerging };
}

/** Header: known can-dos (solid) + emerging count. */
function renderScore(sheet) {
  if (!els.scoreBoard || !els.countDurable) return;
  const counts = lastProgress?.counts || countsFromSheet(sheet || {});
  const known = Number(counts.known || 0);
  const emerging = Number(counts.emerging || 0);

  const prev = lastDurableCount;
  els.countDurable.textContent = String(known);
  if (els.countKnown) els.countKnown.textContent = `known ${known}`;
  if (els.countEmerging) els.countEmerging.textContent = `emerging ${emerging}`;

  if (els.scoreDelta) {
    if (prev !== null && known > prev) {
      els.scoreDelta.textContent = `+${known - prev}`;
      els.scoreDelta.classList.remove("hidden");
      els.scoreBoard.classList.add("score-up");
      if (scoreFlashTimer) clearTimeout(scoreFlashTimer);
      scoreFlashTimer = setTimeout(() => {
        els.scoreDelta.classList.add("hidden");
        els.scoreBoard.classList.remove("score-up");
      }, 2800);
    } else if (prev !== null && known < prev) {
      els.scoreDelta.classList.add("hidden");
      els.scoreBoard.classList.remove("score-up");
    }
  }
  lastDurableCount = known;
}

// ——— Grades rail (left): teacher tool ability moves with why ———
const GRADES_EMPTY_COPY =
  "When the teacher moves a skill up or down, it shows here with a reason. " +
  "No silent auto-grades — only deliberate judgments from the conversation.";

function gradeWhen(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const now = new Date();
  const sameDay =
    d.toLocaleDateString("en-CA") === now.toLocaleDateString("en-CA");
  if (sameDay) {
    return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  }
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function gradeLabel(g) {
  if (g.statement) return g.statement;
  if (g.section === "skills") return g.field_id || "skill";
  if (g.section === "grammar") return `form: ${g.field_id || "?"}`;
  if (g.section === "lexicon") return g.field_id || "word";
  return g.field_id || "grade";
}

function gradeChip(g, curSid) {
  const dir = g.direction === "down" ? "down" : g.direction === "up" ? "up" : "hold";
  const arrow = dir === "up" ? "↑" : dir === "down" ? "↓" : "·";
  const band =
    g.to_status && g.from_status && g.to_status !== g.from_status
      ? `${g.from_status} → ${g.to_status}`
      : g.to_status || "";
  const tip = [g.why || "", g.evidence ? `“${g.evidence}”` : "", band, gradeWhen(g.ts)]
    .filter(Boolean)
    .join("\n");
  const whyLine = g.why
    ? `<span class="j-chip-why">${esc(g.why)}</span>`
    : "";
  const ev = (g.evidence || "").trim();
  const evLine = ev
    ? `<span class="j-chip-ev">“${esc(ev.length > 90 ? ev.slice(0, 90) + "…" : ev)}”</span>`
    : "";
  const earlier = curSid && g.session_id && g.session_id !== curSid;
  const metaLine =
    `<span class="j-chip-meta">${esc(gradeWhen(g.ts) || "")}` +
    (earlier ? " · earlier session" : "") +
    `</span>`;
  return (
    `<li class="j-chip grade-${dir}${earlier ? " grade-past" : ""}" title="${esc(tip)}">` +
    `<span class="j-chip-icon" aria-hidden="true">${arrow}</span>` +
    `<span class="j-chip-body">` +
    `<span class="j-chip-name">${esc(gradeLabel(g))}</span>` +
    evLine +
    whyLine +
    metaLine +
    `</span></li>`
  );
}

function renderJourney(progress) {
  if (!els.journeyBody) return;
  const grades = (progress?.grades || []).slice();
  if (progress?.empty || !grades.length) {
    els.journeyBody.innerHTML =
      `<p class="j-empty">${esc(GRADES_EMPTY_COPY)}</p>`;
  } else {
    const chips = grades
      .map((g) => gradeChip(g, progress?.session_id || ""))
      .join("");
    els.journeyBody.innerHTML =
      `<div class="j-rail"><section class="j-day current">` +
      `<header class="j-date"><span class="j-dot" aria-hidden="true"></span>` +
      `<span class="j-daylabel">recent grades</span></header>` +
      `<ul class="j-chips">${chips}</ul></section></div>`;
  }
  if (els.journeyFoot) {
    const n = grades.length;
    els.journeyFoot.textContent =
      n === 0
        ? "No grades this learner yet"
        : n === 1
          ? "1 grade recorded"
          : `${n} recent grades`;
  }
}

async function refreshProgress() {
  try {
    const p = await api("/api/progress");
    lastProgress = p;
    renderJourney(p);
    renderScore(null);
  } catch (_) {
    /* rail is display only — never break the chat over it */
  }
}

// ——— Debug box: outbound AI requests + response metadata ———
// Local debug tool: GET /api/debug/requests (in-memory ring, newest first).
// Collapsed by default; open state persists in localStorage; refreshed after
// each chat turn while open.

const LS_DEBUG_OPEN = "debugOpen";
/** Latest entries (for the per-entry copy button). */
let lastDebugEntries = [];

function fmtTokens(u) {
  const n = (x) => Number(x || 0);
  return (
    `in ${n(u.input_tokens)} (cache ${n(u.cached_input_tokens)}) / ` +
    `out ${n(u.output_tokens)} / think ${n(u.thinking_tokens)}`
  );
}

function dbgPre(text) {
  return `<pre class="dbg-pre">${esc(text || "")}</pre>`;
}

function dbgSection(title, innerHtml, { open = false } = {}) {
  return (
    `<details class="dbg-sub"${open ? " open" : ""}>` +
    `<summary>${esc(title)}</summary>${innerHtml}</details>`
  );
}

let dbgSel = 0;
let dbgTab = localStorage.getItem("debugTab") || "input";

function dbgJson(obj) {
  return `<pre class="dbg-pre">${esc(JSON.stringify(obj, null, 2))}</pre>`;
}

/** Pretty-print the <tutor_turn_task> payload. Nested JSON strings
 *  (student_character_sheet.sheet) are parsed so the sheet reads as real
 *  JSON, not one escaped line. Falls back to raw text on any parse miss. */
function prettyTask(text) {
  const t = text || "";
  const a = t.indexOf("{");
  const b = t.lastIndexOf("}");
  if (a < 0 || b <= a) return dbgPre(t);
  try {
    const payload = JSON.parse(t.slice(a, b + 1));
    const sheet = payload?.student_character_sheet;
    if (sheet && typeof sheet.sheet === "string") {
      try { sheet.sheet = JSON.parse(sheet.sheet); } catch (_) {}
    }
    return dbgJson(payload);
  } catch (_) {
    return dbgPre(t);
  }
}

function dbgInputView(e) {
  const blocks = e.system_blocks || [];
  const sysBlocks = blocks
    .map((b) =>
      dbgSection(
        `${b.label}${b.cached ? " · cache-marked" : ""} · ${(b.text || "").length} chars`,
        dbgPre(b.text)
      )
    )
    .join("");
  const hist = e.history || [];
  const histHtml = hist
    .map(
      (m) =>
        `<div class="dbg-msg"><span class="dbg-role">${esc(m.role)}</span>` +
        dbgPre(m.content) +
        `</div>`
    )
    .join("");
  return (
    dbgSection("TASK — this turn's payload (formatted)", prettyTask(e.task_message), { open: true }) +
    dbgSection(`SYSTEM BLOCKS · ${blocks.length}`, sysBlocks) +
    dbgSection(`HISTORY · ${hist.length} messages`, histHtml || '<p class="muted">none</p>')
  );
}

function dbgOutputView(e) {
  const raw = e.response?.raw || "";
  const planM = raw.match(/<plan>([\s\S]*?)<\/plan>/i);
  const reply = e.response?.reply || "";
  return (
    (planM
      ? dbgSection(
          "SESSION PLAN — model-authored, learner never sees this",
          dbgPre(planM[1].trim()),
          { open: true }
        )
      : "") +
    dbgSection("VISIBLE REPLY", reply ? dbgPre(reply) : '<p class="muted">none recorded</p>', {
      open: !planM,
    }) +
    (e.response?.tool_calls
      ? dbgSection(
          "TOOL CALL — sheet grade (update_character_sheet)",
          dbgJson(e.response.tool_calls),
          { open: true }
        )
      : "") +
    dbgSection(`RAW MODEL TEXT · ${raw.length} chars`, raw ? dbgPre(raw) : '<p class="muted">none</p>')
  );
}

function dbgMetaView(e) {
  return dbgJson({
    model: e.model,
    ts: e.ts,
    turn: e.turn,
    is_open: !!e.is_open,
    stop_reason: e.response?.stop_reason || "",
    usage: e.response?.usage || {},
    gate_faults: e.response?.gate_faults || [],
    gate_notes: e.response?.gate_notes || [],
    notes: e.response?.notes || [],
  });
}

function renderDebug(entries) {
  const body = document.getElementById("debugBody");
  const count = document.getElementById("debugCount");
  if (!body) return;
  lastDebugEntries = entries || [];
  if (count) count.textContent = lastDebugEntries.length ? `(${lastDebugEntries.length})` : "";
  if (!lastDebugEntries.length) {
    body.innerHTML = '<p class="muted">No requests captured yet — send a message.</p>';
    return;
  }
  if (dbgSel >= lastDebugEntries.length) dbgSel = 0;
  const e = lastDebugEntries[dbgSel];
  const turnBtns = lastDebugEntries
    .map((en, i) => {
      const faults = (en.response?.gate_faults || []).length;
      return (
        `<button type="button" class="dbg-turn-btn${i === dbgSel ? " active" : ""}${faults ? " fault" : ""}" data-turn="${i}">` +
        `turn ${en.turn}${en.is_open ? " · open" : ""}${faults ? " ⚠" : ""}</button>`
      );
    })
    .join("");
  const tabs = ["input", "output", "meta"]
    .map(
      (t) =>
        `<button type="button" class="dbg-tab${t === dbgTab ? " active" : ""}" data-tab="${t}">${t.toUpperCase()}</button>`
    )
    .join("");
  const view =
    dbgTab === "output" ? dbgOutputView(e) : dbgTab === "meta" ? dbgMetaView(e) : dbgInputView(e);
  body.innerHTML =
    `<div class="dbg-turns">${turnBtns}</div>` +
    `<div class="dbg-tabbar">${tabs}` +
    `<span class="dbg-model">${esc(e.model || "")} · ${fmtTokens(e.response?.usage || {})}</span>` +
    `<button type="button" class="btn ghost dbg-copy" data-idx="${dbgSel}" title="Copy this entry as JSON">Copy</button>` +
    `</div>` +
    `<div class="dbg-view">${view}</div>`;
  body.querySelectorAll(".dbg-turn-btn").forEach((btn) =>
    btn.addEventListener("click", () => {
      dbgSel = Number(btn.dataset.turn);
      renderDebug(lastDebugEntries);
    })
  );
  body.querySelectorAll(".dbg-tab").forEach((btn) =>
    btn.addEventListener("click", () => {
      dbgTab = btn.dataset.tab;
      localStorage.setItem("debugTab", dbgTab);
      renderDebug(lastDebugEntries);
    })
  );
  body.querySelectorAll(".dbg-copy").forEach((btn) => {
    btn.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      const entry = lastDebugEntries[Number(btn.dataset.idx)];
      if (!entry) return;
      navigator.clipboard
        ?.writeText(JSON.stringify(entry, null, 2))
        .then(() => {
          btn.textContent = "Copied";
          setTimeout(() => (btn.textContent = "Copy"), 1200);
        })
        .catch(() => {});
    });
  });
}

async function refreshDebug(force = false) {
  const det = document.getElementById("debugDetails");
  if (!det || (!det.open && !force)) return;
  try {
    const data = await api("/api/debug/requests");
    renderDebug(data.entries || []);
  } catch (_) {
    /* debug box is telemetry — never break the chat over it */
  }
}

function initDebugBox() {
  const det = document.getElementById("debugDetails");
  if (!det) return;
  det.open = localStorage.getItem(LS_DEBUG_OPEN) === "1";
  det.addEventListener("toggle", () => {
    localStorage.setItem(LS_DEBUG_OPEN, det.open ? "1" : "0");
    if (det.open) refreshDebug(true);
  });
  document
    .getElementById("debugRefresh")
    ?.addEventListener("click", (ev) => {
      ev.preventDefault();
      refreshDebug(true);
    });
  if (det.open) refreshDebug(true);
}

function syncJourneyToggle() {
  if (!els.journeyCard || !els.journeyToggle) return;
  const collapsed = els.journeyCard.classList.contains("collapsed");
  els.journeyToggle.textContent = collapsed ? "Show" : "Hide";
  els.journeyToggle.setAttribute("aria-expanded", String(!collapsed));
}

function initJourney() {
  if (!els.journeyCard || !els.journeyToggle) return;
  if (window.matchMedia && window.matchMedia("(max-width: 1100px)").matches) {
    els.journeyCard.classList.add("collapsed");
  }
  syncJourneyToggle();
  els.journeyToggle.addEventListener("click", () => {
    els.journeyCard.classList.toggle("collapsed");
    syncJourneyToggle();
  });
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
    renderScore(sheet);
  } catch (e) {
    console.error("renderScore", e);
  }
  try {
    renderCost(sheet);
  } catch (e) {
    console.error("renderCost", e);
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

/** Keep refs so Chrome does not GC utterance mid-speech / drop audio. */
let currentAudio = null;
let currentUtterance = null;
let ttsKeepAlive = null;
/** Server Gemini TTS is the AI teach voice; health may flip this off. */
let serverTtsAvailable = true;
/**
 * Interruption token: every stopSpeech() bumps this so any in-flight speak()
 * loop exits instead of playing stale segments (or worse, re-speaking an
 * interrupted server segment with the OS voice via the failure fallback).
 */
let speakGeneration = 0;

function stopSpeech() {
  speakGeneration += 1;
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

/** Server default rate from /api/health; fallback when no user choice yet. */
let ttsDefaultRate = 1.0;
let ttsModelTryGapMs = 400;

const LS_TTS_RATE = "ttsRate"; // user Voice slider value, "0.7".."1.2"
const LS_TTS_SLOWER_LEGACY = "ttsSlower"; // pre-slider checkbox; migrated once

function clampRate(r) {
  const n = Number(r);
  if (!Number.isFinite(n)) return ttsDefaultRate;
  return Math.max(0.7, Math.min(1.2, n));
}

/** One-time migration: legacy "Slower" checkbox ("1") seeds the slider at 0.8. */
function migrateLegacyTtsSlower() {
  const legacy = localStorage.getItem(LS_TTS_SLOWER_LEGACY);
  if (legacy === null) return;
  if (legacy === "1" && localStorage.getItem(LS_TTS_RATE) === null) {
    localStorage.setItem(LS_TTS_RATE, "0.8");
  }
  localStorage.removeItem(LS_TTS_SLOWER_LEGACY);
}

/** Effective rate: the user's Voice slider (localStorage), clamped 0.7–1.2. */
function effectiveTtsRate() {
  const stored = localStorage.getItem(LS_TTS_RATE);
  return clampRate(stored === null ? ttsDefaultRate : stored);
}

function ttsRateLabelText(rate) {
  const r = clampRate(rate);
  const x = r.toFixed(2).replace(/(\.\d)0$/, "$1"); // 1 → "1.0", 0.95 stays
  return r <= 0.8 ? `Voice ${x}× (slow)` : `Voice ${x}×`;
}

function syncTtsRateUi() {
  if (!els.ttsRateSlider) return;
  const r = effectiveTtsRate();
  els.ttsRateSlider.value = String(r);
  if (els.ttsRateLabel) {
    els.ttsRateLabel.textContent = ttsRateLabelText(r);
  }
}

function wireTtsRateSlider() {
  if (!els.ttsRateSlider) return;
  migrateLegacyTtsSlower();
  syncTtsRateUi();
  els.ttsRateSlider.addEventListener("input", () => {
    localStorage.setItem(
      LS_TTS_RATE,
      String(clampRate(els.ttsRateSlider.value))
    );
    syncTtsRateUi();
  });
}

function sleepMs(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Browser speech for one segment; resolves when the utterance ends/errors.
 * Must retain utterance on a global — Chrome GCs it and speech dies silently.
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
    // Chrome desktop sometimes freezes speech after ~15s without pause/resume
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
 * When both model and try exist → two segments with a pedagogical gap.
 * All other cases → one segment (prefer short speech; skip long explains).
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

/** Legacy single-blob helper; kept for debug callers. */
function speechTextFromParts(parts, fallback) {
  return speechSegmentsFromParts(parts, fallback)
    .map((s) => s.text)
    .join(". ");
}

function preferServerTts() {
  // Opt out of AI voice: localStorage ttsPreferBrowser=1
  if (localStorage.getItem("ttsPreferBrowser") === "1") return false;
  // Explicit force server
  if (
    window.__TTS_SERVER__ === true ||
    localStorage.getItem("ttsPreferServer") === "1"
  ) {
    return true;
  }
  // Default: use Gemini teach voice when server reports TTS enabled
  if (window.__TTS_SERVER__ === false) return false;
  return serverTtsAvailable;
}

/**
 * Play one server WAV segment; playbackRate applies the exact rate
 * (Gemini has no numeric rate API field).
 * `isStale` re-checks AFTER the synthesis fetch resolves: TTS takes seconds,
 * and audio requested before an interruption must never start playing late
 * on top of the next reply's voice.
 */
async function playServerSegment(text, rate, isStale) {
  const res = await fetch("/api/audio/speak", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, rate: clampRate(rate) }),
  });
  if (isStale?.()) return;
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
  if (isStale?.()) return;
  if (!blob || blob.size < 64) throw new Error("empty TTS audio");
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  currentAudio = audio;
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
    audio.play().catch((playErr) => {
      // Autoplay blocked (e.g. first greeting before any click) → reject
      URL.revokeObjectURL(url);
      if (currentAudio === audio) currentAudio = null;
      reject(playErr);
    });
  });
}

/**
 * AI teach voice = server Gemini TTS (good Spanish). Browser is fallback only.
 * ONE voice block: the whole on-screen reply in a single TTS call — no
 * part-splitting, no mid-reply pauses (learner feedback 2026-07-28).
 * Force browser: localStorage.setItem("ttsPreferBrowser","1")
 */
/**
 * Voice block = ONLY the teaching core (recast + model + try) in ONE
 * continuous read. Acknowledge/explain/continue stay on screen: the card is
 * for reading, the voice is for the Spanish that matters — and a short block
 * synthesizes seconds faster.
 */
function voiceBlockFromParts(parts, fallback) {
  if (parts && parts.structured) {
    const bits = [parts.recast, parts.model, parts.try]
      .map((s) => (s || "").trim())
      .filter(Boolean);
    if (bits.length) return bits.join(" ");
  }
  return (fallback || "").trim() || speechTextFromParts(parts, "");
}

async function speak(text, parts) {
  if (!els.speakToggle?.checked) return;
  const block = voiceBlockFromParts(parts, text);
  if (!block) return;
  stopSpeech();
  // Claim the generation AFTER stopSpeech's bump; any later stopSpeech()
  // (send, new turn, reset, reload race) makes this call exit silently —
  // including audio whose synthesis fetch resolves AFTER the interruption.
  const gen = speakGeneration;
  const interrupted = () => gen !== speakGeneration;

  const rate = effectiveTtsRate();
  if (!preferServerTts()) {
    await speakBrowserSegment(block, rate);
    return;
  }
  try {
    await playServerSegment(block, rate, interrupted);
  } catch (err) {
    // Interruption (stopSpeech clears audio.src → onerror) is NOT a TTS
    // failure — never re-speak an interrupted reply with the OS voice.
    if (interrupted()) return;
    console.warn("server TTS failed, browser fallback:", err);
    await speakBrowserSegment(block, rate);
  }
}

async function initTtsPolicy() {
  try {
    const h = await fetch("/api/health", { credentials: "same-origin" }).then(
      (r) => r.json()
    );
    serverTtsAvailable = !!(h?.tts && h.tts.enabled !== false);
    const stampEl = document.getElementById("buildStamp");
    if (stampEl && h?.version) {
      stampEl.textContent = `v${h.version}`;
      if (h.stale_code) {
        stampEl.textContent = `v${h.version} → disk v${h.disk_version} (RESTART)`;
        stampEl.classList.add("stale");
      }
    }
    if (h?.stale_code) {
      // Server process is older than the code on disk — fixes are NOT live
      // (July-26 process silently ignored two days of work, 2026-07-28)
      els.statusLine.textContent =
        "⚠ Server is running OLD code — restart the server to load fixes";
      els.statusLine.style.color = "#e5484d";
    }
    if (Number(h?.chat_max_chars) > 0) {
      // Composer cap mirrors the API's ChatIn max_length (server is authority)
      els.input.maxLength = Number(h.chat_max_chars);
    }
    if (h?.tts?.voice) {
      window.__TTS_VOICE__ = h.tts.voice;
    }
    if (h?.tts?.rate != null) {
      ttsDefaultRate = clampRate(h.tts.rate);
    }
    if (h?.tts?.model_try_gap_ms != null) {
      ttsModelTryGapMs = Math.max(0, Number(h.tts.model_try_gap_ms) || 400);
    }
  } catch (_) {
    // Keep default true; speak() will fall back on failure
    serverTtsAvailable = true;
  }
  wireTtsRateSlider();
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
    const err = new Error(
      data.detail || data.error || res.statusText || "Request failed"
    );
    err.status = res.status;
    throw err;
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

/** Side-rail focus LLM runs async on the server — poll until it settles. */
let railPollTimer = null;
let lastFocusVersion = null;

function scheduleRailRefresh() {
  if (railPollTimer) {
    clearTimeout(railPollTimer);
    railPollTimer = null;
  }
  const delays = [350, 900, 1800, 3200];
  let i = 0;
  const tick = async () => {
    try {
      const sheet = await api("/api/sheet");
      const ver = sheet?.focus_version;
      if (ver != null && ver !== lastFocusVersion) {
        lastFocusVersion = ver;
        renderSheet(sheet);
      } else if (sheet) {
        // Still refresh score / sheet fields even if version unchanged
        renderSheet(sheet);
        lastFocusVersion = ver ?? lastFocusVersion;
      }
      if (sheet?.focus_pending && i < delays.length - 1) {
        i += 1;
        railPollTimer = setTimeout(tick, delays[i]);
        return;
      }
      // One more pull after pending clears
      if (!sheet?.focus_pending && i < 2) {
        i += 1;
        railPollTimer = setTimeout(tick, delays[Math.min(i, delays.length - 1)]);
      }
    } catch (_) {
      /* ignore */
    }
  };
  railPollTimer = setTimeout(tick, delays[0]);
}

/**
 * Session-lifecycle single-flight (2026-07-28 reset-race forensics): a reset
 * and a start must NEVER run concurrently — the later Set-Cookie orphans the
 * earlier session server-side. Every session-creating call (start, new chat,
 * hard reset) claims this flag and AWAITS its response (and Set-Cookie)
 * before any other lifecycle call may begin.
 */
let sessionFlowInFlight = false;

async function startSession() {
  if (sessionFlowInFlight) return;
  sessionFlowInFlight = true;
  setBusy(true);
  els.statusLine.textContent = "Connecting…";
  // Every full page load (including Ctrl/Cmd+Shift+R) starts a clean chat.
  // Character sheet is kept unless user hits Reset learner.
  try {
    els.messages.innerHTML = "";
    const data = await api("/api/session/start", {
      method: "POST",
      body: JSON.stringify({ fresh: true }),
    });
    showMessages(data.messages);
    setNotes(data.notes);
    renderSheet(data.sheet);
    lastFocusVersion = data.sheet?.focus_version ?? null;
    scheduleRailRefresh();
    refreshProgress();
    refreshDebug();
    els.statusLine.textContent = `Model ${data.model || "tutor"} · new chat`;
    if (data.reply) speak(data.reply, data.parts);
  } catch (e) {
    addBubble("system", `Could not start: ${e.message}`);
    els.statusLine.textContent = "Error — check API keys / server logs";
  } finally {
    sessionFlowInFlight = false;
    setBusy(false);
    els.input.focus();
  }
}

/**
 * @param {string} text
 * @param {string} inputMode
 * @param {{ alreadyLocked?: boolean }} [opts]
 */

// ——— Model-led game widgets (2026-08-04; Grok game-feel countersign
// docs/reviews-game-widgets.md — per-item commit, micro-motion, on-card
// feedback, explicit send with idle auto-send) ———

function normEs(s) {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[¿¡?!.,]/g, "")
    .trim();
}

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const KIND_LABEL = {
  match: "Match",
  choose: "Choose",
  type: "Type",
  order: "Order",
  gist: "Gist",
};

function ensureProgress(card, total) {
  let row = card.querySelector(".game-progress");
  if (!row) {
    row = document.createElement("div");
    row.className = "game-progress";
    const anchor = card.querySelector(".game-instructions") ||
      card.querySelector(".game-head");
    anchor.after(row);
  }
  while (row.children.length < total)
    row.appendChild(document.createElement("i"));
  return row;
}

function updateGameProgress(card, n) {
  const row = card.querySelector(".game-progress");
  if (!row) return;
  [...row.children].forEach((dot, i) => dot.classList.toggle("on", i < n));
}

function gameDone(card, kind, title, right, total, missed) {
  card.classList.add("game-finished");
  if (right === total) card.classList.add("game-all-ok");
  const missTxt = missed.length ? `; missed: ${missed.join(", ")}` : "";
  const summary = `[game: ${kind} "${title}" — ${right}/${total} correct${missTxt}]`;
  const note = document.createElement("p");
  note.className = "game-result" + (right === total ? " perfect" : "");
  note.innerHTML =
    `<strong>${right}/${total}</strong>` +
    `<span>${right === total ? "Nice." : ""}</span>`;
  card.appendChild(note);
  if (missed.length) {
    const ul = document.createElement("ul");
    ul.className = "game-miss-list";
    missed.forEach((m) => {
      const li = document.createElement("li");
      li.textContent = m;
      ul.appendChild(li);
    });
    card.appendChild(ul);
  }
  let sent = false;
  const send = () => {
    if (sent) return;
    sent = true;
    card.classList.add("game-done");
    btn.textContent = "Sent to tutor";
    sendMessage(summary);
  };
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "btn game-check";
  btn.textContent = "Send result to tutor";
  const idle = setTimeout(send, 8000);
  btn.onclick = () => {
    clearTimeout(idle);
    send();
  };
  card.appendChild(btn);
}

function gameChoiceQuestion(card, container, prompt, options, answer, onCommit) {
  const q = document.createElement("div");
  q.className = "game-q";
  if (prompt) q.innerHTML = `<p class="game-prompt">${esc(prompt)}</p>`;
  for (const opt of options || []) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "game-tile game-opt-btn";
    b.textContent = opt;
    b.onclick = () => {
      if (q.dataset.locked) return;
      q.dataset.locked = "1";
      const ok = opt === (answer || "");
      b.classList.add(ok ? "ok" : "bad", ok ? "pop" : "shake");
      if (!ok) {
        [...q.querySelectorAll(".game-opt-btn")].forEach((x) => {
          if (x.textContent === answer) x.classList.add("ok", "reveal");
        });
      }
      q.querySelectorAll(".game-opt-btn").forEach((x) => (x.disabled = true));
      onCommit(ok);
    };
    q.appendChild(b);
  }
  container.appendChild(q);
}

function renderGameWidget(game) {
  if (!game || game.error) {
    if (game?.error)
      addBubble("system", `⚠ game failed (not hidden): ${game.error}`);
    return;
  }
  const card = document.createElement("div");
  card.className = "bubble game-card";
  const items = game.items || [];
  card.innerHTML =
    `<div class="game-head">` +
    `<span class="game-kind">${esc(KIND_LABEL[game.kind] || game.kind)}</span>` +
    `<span class="game-title">${esc(game.title || "Quick game")}</span></div>` +
    (game.instructions
      ? `<p class="game-instructions">${esc(game.instructions)}</p>`
      : "");
  const missed = [];
  let right = 0;
  let answered = 0;

  if (game.kind === "match") {
    const pairs = items.filter((i) => i && i.es && i.en);
    ensureProgress(card, pairs.length);
    const wrap = document.createElement("div");
    wrap.className = "match-wrap";
    const left = document.createElement("div");
    const rightCol = document.createElement("div");
    left.className = "match-col";
    rightCol.className = "match-col";
    let sel = null;
    let solved = 0;
    for (const p of pairs) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "game-tile";
      b.textContent = p.es;
      b.onclick = () => {
        if (b.disabled) return;
        left.querySelectorAll(".sel").forEach((x) => x.classList.remove("sel"));
        b.classList.add("sel");
        sel = { btn: b, pair: p };
      };
      left.appendChild(b);
    }
    for (const p of shuffle(pairs)) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "game-tile";
      b.textContent = p.en;
      b.onclick = () => {
        if (b.disabled || !sel) return;
        if (sel.pair.en === p.en) {
          sel.btn.disabled = true;
          b.disabled = true;
          sel.btn.classList.add("ok", "pop");
          b.classList.add("ok", "pop");
          right += 1;
          solved += 1;
          sel = null;
          updateGameProgress(card, solved);
          if (solved === pairs.length)
            gameDone(card, "match", game.title, right, pairs.length, missed);
        } else {
          b.classList.add("bad", "shake");
          sel.btn.classList.add("shake");
          if (!missed.includes(`${sel.pair.es}→${p.en}`))
            missed.push(`${sel.pair.es}→${p.en}`);
          const leftBtn = sel.btn;
          sel = null;
          setTimeout(() => {
            b.classList.remove("bad", "shake");
            leftBtn.classList.remove("sel", "shake");
          }, 280);
        }
      };
      rightCol.appendChild(b);
    }
    wrap.appendChild(left);
    wrap.appendChild(rightCol);
    card.appendChild(wrap);
  } else if (game.kind === "choose") {
    ensureProgress(card, items.length);
    for (const it of items) {
      gameChoiceQuestion(card, card, it.prompt, it.options, it.answer, (ok) => {
        if (ok) right += 1;
        else missed.push(`${(it.prompt || "").slice(0, 24)}→${it.answer}`);
        answered += 1;
        updateGameProgress(card, answered);
        if (answered === items.length)
          gameDone(card, "choose", game.title, right, items.length, missed);
      });
    }
  } else if (game.kind === "gist") {
    let totalQ = 0;
    for (const it of items) totalQ += (it.questions || []).length;
    ensureProgress(card, totalQ);
    for (const it of items) {
      const passage = document.createElement("blockquote");
      passage.className = "game-passage";
      passage.textContent = it.text || "";
      card.appendChild(passage);
      for (const qq of it.questions || []) {
        gameChoiceQuestion(card, card, qq.q, qq.options, qq.answer, (ok) => {
          if (ok) right += 1;
          else missed.push(`${(qq.q || "").slice(0, 28)}→${qq.answer}`);
          answered += 1;
          updateGameProgress(card, answered);
          if (answered === totalQ)
            gameDone(card, "gist", game.title, right, totalQ, missed);
        });
      }
    }
  } else if (game.kind === "type") {
    ensureProgress(card, items.length);
    for (const it of items) {
      const q = document.createElement("div");
      q.className = "game-q";
      q.innerHTML = `<p class="game-prompt">${esc(it.en || "")}</p>`;
      const inp = document.createElement("input");
      inp.type = "text";
      inp.className = "game-input";
      inp.placeholder = "escribe en español…";
      q.appendChild(inp);
      const hint = document.createElement("p");
      hint.className = "game-hint";
      hint.hidden = true;
      q.appendChild(hint);
      const commit = () => {
        if (inp.dataset.locked) return;
        inp.dataset.locked = "1";
        const ok = normEs(inp.value) === normEs(it.answer || "");
        inp.classList.add(ok ? "ok" : "bad", ok ? "pop" : "shake");
        inp.readOnly = true;
        if (ok) right += 1;
        else {
          missed.push(`${it.en}→${it.answer}`);
          hint.hidden = false;
          hint.textContent = it.answer || "";
        }
        answered += 1;
        updateGameProgress(card, answered);
        if (answered === items.length)
          gameDone(card, "type", game.title, right, items.length, missed);
      };
      inp.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          commit();
        }
      });
      const ok = document.createElement("button");
      ok.type = "button";
      ok.className = "game-tile game-commit";
      ok.textContent = "✓";
      ok.onclick = commit;
      q.appendChild(ok);
      card.appendChild(q);
    }
  } else if (game.kind === "order") {
    ensureProgress(card, items.length);
    for (const it of items) {
      const q = document.createElement("div");
      q.className = "game-q";
      const tiles = shuffle(it.tiles || []);
      const build = document.createElement("p");
      build.className = "game-build";
      const tileRow = document.createElement("div");
      tileRow.className = "game-tilerow";
      const chosen = [];
      for (const w of tiles) {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "game-tile";
        b.textContent = w;
        b.onclick = () => {
          if (b.disabled || q.dataset.locked) return;
          b.disabled = true;
          b.classList.add("used");
          chosen.push(w);
          build.textContent = chosen.join(" ");
        };
        tileRow.appendChild(b);
      }
      const undo = document.createElement("button");
      undo.type = "button";
      undo.className = "game-tile game-clear";
      undo.textContent = "⌫";
      undo.title = "Undo last";
      undo.onclick = () => {
        if (q.dataset.locked) return;
        const last = chosen.pop();
        if (last == null) return;
        build.textContent = chosen.join(" ");
        for (const btn of tileRow.querySelectorAll(
          "button.game-tile:not(.game-clear)"
        )) {
          if (btn.disabled && btn.textContent === last) {
            btn.disabled = false;
            btn.classList.remove("used");
            break;
          }
        }
      };
      tileRow.appendChild(undo);
      const check = document.createElement("button");
      check.type = "button";
      check.className = "game-tile game-commit";
      check.textContent = "✓";
      check.onclick = () => {
        if (q.dataset.locked || !chosen.length) return;
        q.dataset.locked = "1";
        const ok = normEs(chosen.join(" ")) === normEs(it.answer || "");
        build.classList.add(ok ? "ok" : "bad");
        if (ok) right += 1;
        else missed.push(`→${it.answer}`);
        answered += 1;
        updateGameProgress(card, answered);
        if (answered === items.length)
          gameDone(card, "order", game.title, right, items.length, missed);
      };
      tileRow.appendChild(check);
      q.appendChild(tileRow);
      q.appendChild(build);
      card.appendChild(q);
    }
  }
  els.messages.appendChild(card);
  els.messages.scrollTop = els.messages.scrollHeight;
}

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
  // User responded — cancel the previous reply's voice NOW, including audio
  // whose TTS synthesis hasn't returned yet (it must never play late over
  // the next reply's voice).
  stopSpeech();

  addBubble("you", text, { inputMode });
  els.input.value = "";
  els.input.classList.remove("speech-interim");
  autosize();
  setMicStatus("working", "Tutor is thinking…");
  const typing = addBubble("system", "Tutor is thinking…");
  typing.classList.add("typing");
  const _sentAt = performance.now();
  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: text, input_mode: inputMode }),
    });
    const _totalMs = Math.round(performance.now() - _sentAt);
    typing.remove();
    // No-hide (2026-08-03): a turn that carries an error must SHOW it —
    // an empty tutor bubble with the error invisible was the silent-
    // failure class (provider errors rendered as blank turns).
    if (data.error) {
      addBubble("system", `TURN ERROR (not hidden): ${data.error}`);
    }
    const internalErrs = (data.notes || []).filter((n) =>
      String(n).startsWith("internal_error:")
    );
    for (const n of internalErrs) {
      addBubble("system", `⚠ ${n}`);
    }
    if ((data.reply || "").trim() || !data.game) {
      addBubble("tutor", data.reply, {
        parts: data.parts,
        timing: {
          model_ms: data.model_ms,
          server_ms: data.server_ms,
          total_ms: _totalMs,
        },
      });
    }
    if (data.game) renderGameWidget(data.game);
    setNotes(data.notes);
    renderSheet(data.sheet); // score + static rail immediately
    lastFocusVersion = data.sheet?.focus_version ?? lastFocusVersion;
    scheduleRailRefresh(); // focus LLM finishes async → pull updated rail
    refreshProgress(); // grades rail: tool grades appear with why
    refreshDebug(); // debug box: pull the new request entry when open
    // Start voice ASAP (browser TTS); don't block UI on server TTS RTT
    speak(data.reply, data.parts);
    setMicStatus("idle", micIdleHint);
    return true;
  } catch (e) {
    typing.remove();
    // Server restart wipes in-memory sessions → /api/chat 404s. Recover with
    // a fresh session automatically instead of a dead error bubble.
    if (e.status === 404 && /session/i.test(e.message || "")) {
      addBubble(
        "system",
        "Session was lost (server restarted) — starting a fresh chat. " +
          "Please resend your last message."
      );
      endTurn();
      await startSession();
      return false;
    }
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
  if (busy || turnInFlight || sessionFlowInFlight) return;
  // SEQUENCE, never race (2026-07-28 forensics): the reset response carries
  // the new session + Set-Cookie and is fully AWAITED under the lifecycle
  // lock — no startSession may fire until it lands (the reset reply IS the
  // new session's opening turn; no separate start call happens).
  sessionFlowInFlight = true;
  setBusy(true);
  try {
    const data = await api("/api/session/reset", {
      method: "POST",
      body: JSON.stringify({ reset_sheet: false }),
    });
    showMessages(data.messages);
    setNotes(data.notes);
    renderSheet(data.sheet);
    refreshProgress();
    refreshDebug();
    setMicStatus("idle", "New chat — same learner sheet");
    speak(data.reply, data.parts);
  } catch (e) {
    addBubble("system", e.message);
  } finally {
    sessionFlowInFlight = false;
    setBusy(false);
  }
});

async function hardResetLearner() {
  if (busy || turnInFlight || sessionFlowInFlight) {
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
  // SEQUENCE, never race (2026-07-28 forensics: reset raced startSession →
  // stale cookie → orphaned session 20260728-120331): the reset response
  // (and its Set-Cookie) is fully AWAITED under the lifecycle lock before
  // any other session-creating call may run.
  sessionFlowInFlight = true;
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
    refreshProgress();
    refreshDebug();
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
    speak(data.reply, data.parts);
  } catch (e) {
    addBubble("system", `Reset failed: ${e.message}`);
  } finally {
    sessionFlowInFlight = false;
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
// Discover server Gemini TTS, then open session (opening line uses AI voice)
initJourney();
initDebugBox();
initTtsPolicy().finally(() => startSession());
