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

function renderModeBadge(parts) {
  const mode = parts?.mode || parts?.plan?.mode || "";
  if (!mode) return "";
  const reason = parts?.plan?.mode_reason || parts?.mode_decision?.reason || "";
  const hard = parts?.plan?.hard_break || parts?.mode_decision?.hard_break;
  const label = hard ? `Mode · ${mode} (focus)` : `Mode · ${mode}`;
  const title = reason ? esc(reason) : esc(mode);
  return (
    `<div class="part part-mode" title="${title}">` +
    `<span class="part-label">${esc(label)}</span></div>`
  );
}

function renderTutorParts(parts, fallbackContent) {
  if (!parts || !parts.structured) {
    // Still show teach images if present on unstructured reply
    const img = renderTeachImages(parts);
    return renderModeBadge(parts) + img + esc(fallbackContent || "");
  }
  const blocks = [];
  const modeBadge = renderModeBadge(parts);
  if (modeBadge) blocks.push(modeBadge);
  // Teach image first: associate form with meaning before/with the models
  const imgBlock = renderTeachImages(parts);
  if (imgBlock) blocks.push(imgBlock);

  if (parts.acknowledge) {
    const plan = parts.plan || {};
    const mode = parts.mode || plan.mode || "";
    const isDiag =
      plan.phase === "diagnostic" ||
      plan.move === "english_frame" ||
      plan.move === "associate" ||
      mode === "placement" ||
      mode === "association" ||
      parts.open_phase === "diagnostic";
    // Avoid empty "Got it" when we're framing meaning / associating a form
    let ackLabel = "Got it";
    if (mode === "form_focus") {
      ackLabel = "Form focus";
    } else if (mode === "association" || plan.move === "associate") {
      ackLabel = "Meaning";
    } else if (mode === "placement" || isDiag || plan.move === "english_frame") {
      ackLabel = "Welcome";
    } else if (mode === "cf_recast" || plan.move === "recast_retry") {
      ackLabel = "Almost";
    } else if (mode === "transfer") {
      ackLabel = "Try again";
    } else if (mode === "comprehension_check") {
      ackLabel = "Check";
    }
    blocks.push(
      `<div class="part part-ack"><span class="part-label">${ackLabel}</span>${esc(
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
    const mode = parts.mode || (parts.plan || {}).mode || "";
    const modelLabel =
      mode === "form_focus"
        ? "Focus"
        : mode === "association"
          ? "Form"
          : "Model";
    blocks.push(
      `<div class="part part-model"><span class="part-label">${modelLabel}</span>${esc(
        parts.model
      )}</div>`
    );
  }
  if (parts.try) {
    const mode = parts.mode || (parts.plan || {}).mode || "";
    const tryLabel =
      mode === "comprehension_check"
        ? "Check"
        : mode === "form_focus"
          ? "Practice"
          : mode === "transfer"
            ? "Transfer"
            : "Your turn";
    blocks.push(
      `<div class="part part-try"><span class="part-label">${tryLabel}</span>${esc(
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
  // Primary: this-turn mode (what the tutor is actually doing)
  const mode = f.mode || sheet?.parts?.mode || "—";
  els.focusPill.textContent = mode;
  els.focusPill.classList.toggle("warn", !!f.hard_break || f.skill_status === "fragile");
  els.focusTitle.textContent =
    f.title || nb.statement || "Conversation";

  const why = f.blurb || f.reason_ai || f.why || f.reason || "—";
  const rows = [
    ["This turn", f.activity || mode || "chat"],
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
  if (f.hard_break) {
    chips.push(`<span class="chip" style="color:var(--warn);border-color:#6b5420">hard break</span>`);
  }
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

/** Last rendered durable count — used to show +Δ when it advances. */
let lastDurableCount = null;
let scoreFlashTimer = null;
/** Latest /api/progress payload (journey rail + countable header). */
let lastProgress = null;

function renderCost(sheet) {
  if (!els.costBoard || !els.costValue) return;
  const c = sheet?.session_cost;
  if (!c) return;
  const total = Number(c.total_usd || 0);
  els.costValue.textContent = `$${total.toFixed(total < 0.1 ? 4 : 2)}`;
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

/** Countable-header fallback when /api/progress hasn't answered yet:
 * strict sheet bands only (status known / emerging; interval_days >= 14). */
function countsFromSheet(sheet) {
  let known = 0;
  let emerging = 0;
  for (const v of Object.values(sheet?.skills || {})) {
    const st = String(v?.status || "");
    if (st === "known") known += 1;
    else if (st === "emerging") emerging += 1;
  }
  let durable = 0;
  for (const sec of ["lexicon", "grammar"]) {
    for (const v of Object.values(sheet?.[sec] || {})) {
      if (Number(v?.interval_days || 0) >= 14) durable += 1;
    }
  }
  return { durable, known, emerging };
}

/** Countable header (design-progression-view, amended (e)4): durable-so-far
 * N · can-dos known M · emerging K. The abstract 0-100 score stays in the
 * payload for compat but is no longer the display. */
function renderScore(sheet) {
  if (!els.scoreBoard || !els.countDurable) return;
  const counts = lastProgress?.counts || countsFromSheet(sheet || {});
  const durable = Number(counts.durable || 0);
  const known = Number(counts.known || 0);
  const emerging = Number(counts.emerging || 0);

  const prev = lastDurableCount;
  els.countDurable.textContent = String(durable);
  if (els.countKnown) els.countKnown.textContent = `can-dos known ${known}`;
  if (els.countEmerging) els.countEmerging.textContent = `emerging ${emerging}`;

  if (els.scoreDelta) {
    if (prev !== null && durable > prev) {
      els.scoreDelta.textContent = `+${durable - prev}`;
      els.scoreDelta.classList.remove("hidden");
      els.scoreBoard.classList.add("score-up");
      if (scoreFlashTimer) clearTimeout(scoreFlashTimer);
      scoreFlashTimer = setTimeout(() => {
        els.scoreDelta.classList.add("hidden");
        els.scoreBoard.classList.remove("score-up");
      }, 2800);
    } else if (prev !== null && durable < prev) {
      // reset learner etc. — no flash
      els.scoreDelta.classList.add("hidden");
      els.scoreBoard.classList.remove("score-up");
    }
  }
  lastDurableCount = durable;
}

// ——— Journey rail (left): evidence-backed milestone nodes, session clusters ———
// Honesty law (PEDAGOGY §3 + amended design): nodes render ONLY ledger events;
// no streak chrome, no XP; mastery copy only at the known band; downgraded
// nodes carry a quiet "needs re-check" badge instead of silent permanence.

const JOURNEY_KINDS = {
  planted: { icon: "🌱", label: "planted" },
  taking_root: { icon: "🌿", label: "taking root" },
  rooted: { icon: "🌳", label: "rooted — durable so far" },
  regression: { icon: "↺", label: "reset — will re-check" },
  error_recovered: { icon: "✔", label: "clean streak" },
  can_do_emerging: { icon: "☆", label: "emerging" },
  can_do_known: { icon: "★", label: "known" },
  task_complete: { icon: "⚑", label: "task done" },
};

// Amended (c) first-session copy: durability milestones are multi-day BY
// DESIGN; same-day seeds/tasks still show, and this copy sets the honest
// expectation instead of an empty-looking rail.
const JOURNEY_EMPTY_COPY =
  "Seeds plant today. Sprouts (3-day recall) and trees (2-week hold) " +
  "appear when you come back — that gap is how memory sticks.";

/** Local YYYY-MM-DD for a Date (en-CA locale formats exactly that). */
function localIsoDay(d) {
  return d.toLocaleDateString("en-CA");
}

/** Day-chip label: "Today" / "Yesterday" / "Jul 26". */
function journeyDayLabel(iso) {
  const now = new Date();
  if (iso === localIsoDay(now)) return "Today";
  if (iso === localIsoDay(new Date(now.getTime() - 86400e3))) return "Yesterday";
  const d = new Date(`${iso}T12:00:00`);
  if (isNaN(d.getTime())) return iso || "";
  const opts = { month: "short", day: "numeric" };
  if (d.getFullYear() !== now.getFullYear()) opts.year = "numeric";
  return d.toLocaleDateString(undefined, opts);
}

/** One milestone chip: icon + humanized display name. ONE state per chip
 * (2026-07-28 rail incident): "recheck" REPLACES the celebration icon —
 * history stays in the ledger, the display shows current truth. Hover/tap
 * shows the full evidence sentence (+ gloss, + session id for debug). */
function journeyChip(ev) {
  const meta = JOURNEY_KINDS[ev.kind] || { icon: "•", label: ev.kind };
  const state =
    ev.display_state ||
    (ev.polarity === "down" ? "down" : ev.needs_recheck ? "recheck" : "celebrated");
  const name = ev.display || ev.key;
  const tip = [ev.detail || ""];
  if (ev.gloss) tip.push(`${ev.key} = ${ev.gloss}`);
  let icon = meta.icon;
  let badge = "";
  if (state === "recheck") {
    icon = "↺";
    badge = `<span class="j-badge">re-check</span>`;
    tip.push("The live sheet no longer holds this band — it will be re-checked in conversation");
  } else {
    tip.push(meta.label);
  }
  if (ev.session_id) tip.push(`session ${ev.session_id}`);
  return (
    `<li class="j-chip ${state}" title="${esc(tip.filter(Boolean).join("\n"))}">` +
    `<span class="j-chip-icon" aria-hidden="true">${icon}</span>` +
    `<span class="j-chip-name">${esc(name)}</span>${badge}</li>`
  );
}

/** One day cluster: date chip on the rail spine + inline milestone chips.
 * Theme grouping survives only as ordering + a tiny muted prefix, never as
 * the only visible text (2026-07-28 rail incident: "Greetings — 1 planted"
 * rows said nothing). */
function journeyDay(c, isCurrent) {
  const label = journeyDayLabel(c.date || "");
  const nSess = Number(c.session_count || (c.sessions || []).length || 0);
  const sess = nSess > 1 ? `<span class="j-sess">· ${nSess} sessions</span>` : "";
  const groups =
    c.groups && c.groups.length
      ? c.groups
      : [{ theme: "other", events: c.events || [] }];
  const chips = groups
    .map((g) => {
      const theme = String(g.theme || "");
      const prefix =
        theme && !["abilities", "tasks", "other"].includes(theme)
          ? `<li class="j-theme" aria-hidden="true">${esc((g.label || theme).toLowerCase())}</li>`
          : "";
      return prefix + (g.events || []).map(journeyChip).join("");
    })
    .join("");
  const body = (c.events || []).length
    ? `<ul class="j-chips">${chips}</ul>`
    : `<p class="j-sum">quiet so far — seeds today, sprouts on return</p>`;
  return (
    `<section class="j-day${isCurrent ? " current" : ""}">` +
    `<header class="j-date"><span class="j-dot" aria-hidden="true"></span>` +
    `<span class="j-daylabel">${esc(label)}</span>${sess}</header>` +
    body +
    `</section>`
  );
}

function renderJourney(progress) {
  if (!els.journeyBody) return;
  const clusters = (progress?.clusters || []).slice();
  if (progress?.empty || !clusters.length) {
    els.journeyBody.innerHTML =
      `<p class="j-empty">${esc(JOURNEY_EMPTY_COPY)}</p>`;
  } else {
    const todayIso = localIsoDay(new Date());
    // A live session with no milestones yet still shows an honest, quiet
    // "Today" stop on the path (amended (c): quiet sessions may exist).
    if (progress?.session_id && !clusters.some((c) => c.date === todayIso)) {
      clusters.unshift({
        date: todayIso,
        sessions: [progress.session_id],
        session_count: 1,
        events: [],
        groups: [],
      });
    }
    const html = clusters
      .map((c) => {
        const isCurrent =
          c.date === todayIso ||
          (progress?.session_id &&
            (c.sessions || []).includes(progress.session_id));
        return journeyDay(c, isCurrent);
      })
      .join("");
    els.journeyBody.innerHTML = `<div class="j-rail">${html}</div>`;
  }
  if (els.journeyFoot) {
    const due = Number(progress?.due_soon || 0);
    // Informational only (amended (e)3) — never a failure badge.
    els.journeyFoot.textContent = due > 0 ? `Due soon: ${due}` : "Nothing due right now";
  }
}

async function refreshProgress() {
  try {
    const p = await api("/api/progress");
    lastProgress = p;
    renderJourney(p);
    renderScore(null); // header counts from the fresh payload
  } catch (_) {
    /* rail is telemetry display — never break the chat over it */
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

function renderDebugEntry(e, idx) {
  const u = e.response?.usage || {};
  const summary =
    `turn ${e.turn}${e.is_open ? " (open)" : ""} · ` +
    `${e.mode || "?"}/${e.reason || "?"} · ${e.activity || "—"} · ` +
    fmtTokens(u);
  const sysBlocks = (e.system_blocks || [])
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
  const meta = {
    model: e.model,
    ts: e.ts,
    stop_reason: e.response?.stop_reason || "",
    usage: u,
    gate_faults: e.response?.gate_faults || [],
    gate_notes: e.response?.gate_notes || [],
    notes: e.response?.notes || [],
  };
  const body =
    `<div class="dbg-entry-head">` +
    `<span class="dbg-model">${esc(e.model || "")} · ${esc(e.ts || "")}</span>` +
    `<button type="button" class="btn ghost dbg-copy" data-idx="${idx}" title="Copy this entry as JSON">Copy</button>` +
    `</div>` +
    dbgSection(`SYSTEM BLOCKS · ${(e.system_blocks || []).length}`, sysBlocks) +
    dbgSection("INSTRUCTIONS (mode decision)", dbgPre(e.instructions), {
      open: true,
    }) +
    dbgSection("TASK MESSAGE", dbgPre(e.task_message)) +
    dbgSection(`HISTORY · ${hist.length} messages`, histHtml || '<p class="muted">none</p>') +
    dbgSection(
      "RESPONSE META",
      dbgPre(JSON.stringify(meta, null, 2)),
    );
  return (
    `<details class="dbg-entry">` +
    `<summary class="dbg-entry-sum">${esc(summary)}` +
    ((e.response?.gate_faults || []).length
      ? ` <span class="dbg-faults">gate: ${esc((e.response.gate_faults || []).join(", "))}</span>`
      : "") +
    `</summary>${body}</details>`
  );
}

function renderDebug(entries) {
  const body = document.getElementById("debugBody");
  const count = document.getElementById("debugCount");
  if (!body) return;
  lastDebugEntries = entries || [];
  if (count) count.textContent = lastDebugEntries.length ? `(${lastDebugEntries.length})` : "";
  if (!lastDebugEntries.length) {
    body.innerHTML =
      '<p class="muted">No requests captured yet — send a message.</p>';
    return;
  }
  body.innerHTML = lastDebugEntries.map(renderDebugEntry).join("");
  body.querySelectorAll(".dbg-copy").forEach((btn) => {
    btn.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      const i = Number(btn.dataset.idx);
      const entry = lastDebugEntries[i];
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
  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: text, input_mode: inputMode }),
    });
    typing.remove();
    addBubble("tutor", data.reply, { parts: data.parts });
    setNotes(data.notes);
    renderSheet(data.sheet); // score + static rail immediately
    lastFocusVersion = data.sheet?.focus_version ?? lastFocusVersion;
    scheduleRailRefresh(); // focus LLM finishes async → pull updated rail
    refreshProgress(); // journey rail: nodes appear as milestones fire
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
