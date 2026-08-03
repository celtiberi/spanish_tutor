# ml_teacher — system overview

**Audience:** humans and agents working on the product  
**Status:** living description of the *current* conversational Spanish tutor (as of 2026-07-28)  
**Repo:** research + product prototype for **pedagogy-first** tutoring, with Spanish A1 as the first pack

**Law:** `PEDAGOGY.md` is the ONLY home of law text. This file maps **what ships today** — it must point at PEDAGOGY.md, never restate or fork law paragraphs.

This document supersedes older fragments where they conflict. Deeper design debates live under `docs/reviews-*` and `docs/teaching-system.md`.

---

## 1. One-line thesis

**Conversation is the vehicle; teaching is knowing when to break, what goal is open, and whether the form landed.**

The learner experiences a warm Spanish chat. Underneath, code owns the **phase plan** and **mode**, the AI **realizes** the turn in Spanish, code **gates** the reply, and code updates the **ability sheet** (and schedule/ledger fields) from evidence. Personal facts are not captured (2026-07-28).

```text
observe(learner, sheet, session)
    → SessionPhaseController activity hint   # CODE — retrieval/new_input/task/free/close
    → select_mode(...)                       # CODE — deterministic (profile arg unused)
    → AI realize(mode, sheet + pack + stance)  # no personal-context block
    → output_gate(turn)                      # CODE — one repair if critical
    → hard_observer / sheet + schedule/ledger  # CODE — ability only
```

---

## 2. Product persona

| | Choice |
|--|--------|
| Who | Adult, boat/café life OK — **not** a kids flashcard app |
| Level | A1 / false-beginner friendly; true zeros welcome |
| Blank sheet | **Unknown**, not proven beginner (placement, not a Hola ladder) |
| Language | Spanish-forward; English is a **lifeline**, not dual-subtitle wallpaper |
| Agenda | AI realizes the turn; **code** owns phases, mode, ability sheet, gates, introduce/task plans |

**Non-goals:** personal-data capture; scripted social probe queue as the default product; chat-buddy with no teach move; pure worksheet drills.

See `docs/product-persona.md`.

---

## 3. What the learner sees (web)

**Entry:** `python -m tutor.web_app` → `http://127.0.0.1:8765`  
**Engine:** `tutor/conv_session.py` (shared with CLI)

| Surface | Role |
|---------|------|
| Chat | Tutor turns as structured parts (acknowledge / recast / model / try / …) |
| Mic | STT (Chirp stream or Gemini / browser paths) |
| Speak replies | Gemini neural TTS by default (rate **1.0**); client Voice slider 0.7–1.2; browser TTS fallback |
| Progress score | Top header — countable progress from ability + journey ledger (`/api/progress`; legacy `compute_progress_score` still exists) |
| **This turn** (rail) | **Live mode** for the current turn (not a stale can-do title) |
| Morphology (rail) | Forms in play (prefer form_focus e.g. *estar*, not a random can-do); optional async `FOCUS_MODEL` |
| **Journey** (rail) | Append-only milestone ledger + theme grouping + retractions (`tutor/progress_ledger.py`) |
| Full sheet | Modal: skills, errors, next_best, human dump (**ability only**; identity always empty) |
| Composer | Client `maxlength` mirrors `/api/health` `chat_max_chars` (`CHAT_MAX_CHARS=12000` on `ChatIn`) |
| Teach images | When association / repair / concrete intro needs a referent |
| Debug (local) | In-memory request ring + `GET /api/debug/requests` |

Page load starts a **new chat** but keeps the **ability sheet** on disk. “Reset learner” wipes Spanish progress (`reset_sheet`). `clear_personal` / `session.reset_profile` only **deletes leftover** `learner_profile.json` files from the capture era — nothing loads or writes personal facts.

---

## 4. Pedagogy

**Law pointer:** theory (P1–P9), phase architecture, introduce/retrieval/correction, honesty, and enforcement map live only in `PEDAGOGY.md`. Below is the shipping map.

### 4.0 Pedagogy engine (shipped 2026-07-28)

| Module | Role |
|--------|------|
| `tutor/session_phases.py` | Turn plan: retrieval / new_input / task / free / **close** (1-turn coda, USER-ratified 2026-07-28). Clock freezes on §2.1 guards/repairs. |
| `tutor/retrieval_scheduler.py` | Introduced/first_seen ledger + due ladder; introduce ≠ ability bump |
| `tutor/association_table.py` + pack `association_table.json` | 175 keys (incl. 20 false-friend slots); cluster/theme helpers |
| `tutor/introduce_router.py` | One-target IntroducePlan; mark ledger only if key is visible in reply |
| `tutor/task_runtime.py` | Info-gap / convergent task state on task-phase turns |
| `tutor/output_gate.py` | incl. `gate:unscaffolded_new_item`, `gate:unscaffolded_flood`, `gate:regloss`; placement/blank_zero `english_wall` floor 0.25 |
| `tutor/progress_ledger.py` | Journey rail milestones + retractions |
| `tutor/signal_classifier.py` | Shadow labels `content_offer`, `self_flagged_form` (not routing authority yet) |
| `tutor/costs.py` | Per-session cost ledger |

Build history: `docs/build-plan-pedagogy-engine.md`. Do not copy law text from PEDAGOGY.md into this section.

### 4.1 Learning science we optimize for

| Idea | Product translation |
|------|---------------------|
| **CLT** | Language for real communication, not isolated drills |
| **Comprehensible input (CI)** | Mostly clear Spanish the learner can map to meaning |
| **Association** | Form ↔ meaning (image, context) before English gloss walls |
| **Focus on form** | Brief recast / contrast *inside* meaning; then transfer |
| **Transfer** | Same form, **new** micro-context — not re-drill the same line |
| **Trajectory** | Teaching is multi-turn: model → try → feedback → transfer |

### 4.2 Teach move (contract)

Every turn must include at least one of:

- **model** — Spanish they should hear  
- **try** — one real elicit (question / invite)  
- **recast** — clean form when they erred  

Bare hangout (“¡Hola!” only) is a contract violation. Open requires **model + try**.

Machine check: `tutor/pedagogy_contract.py`  
Human write-up: `docs/pedagogy-contract.md`

### 4.3 Structured reply shape

The model writes tagged parts (learner never sees tags):

```xml
<tutor>
  <acknowledge>…</acknowledge>
  <recast>…</recast>
  <explain depth="brief">…</explain>
  <model>…</model>
  <try>…</try>
  <continue>…</continue>
</tutor>
```

Parser: `tutor/tutor_response.py`.  
**Forbidden in the reply:** character-sheet JSON, tool dumps, can-do codes, confidence blobs. That is a **gate fault** (`gate:sheet_leak`), not something to silently scrub into a “success.”

### 4.4 Modes (when to break from free chat)

Code selects mode (`tutor/modes.py`). First matching guard wins. Budgeted hard modes (`form_focus`, hard `association`) are blocked while `turns_since_hard_break < 3` after a prior hard break; **`comprehension_repair` and blank-sheet `placement` bypass the budget**, so back-to-back hard breaks are possible. “Time pressure” means sheet `affect.energy == "limited_time"` (forces conversation / soft `cf_recast`).

| Mode | Intent |
|------|--------|
| `placement` | Blank sheet open — wide ceiling, short Spanish |
| `conversation` | Default vehicle |
| `cf_recast` | Soft form fix: short `<recast>` + continue chat |
| `form_focus` | Hard break: wrong→right contrast, produce once |
| `association` | Form ↔ image meaning (English wall or new concrete noun) |
| `comprehension_repair` | They didn’t get our Spanish — **same idea**, re-model, re-ask (no topic jump) |
| `transfer` | Just succeeded on a form — same form, new context |

**Routing signals (updated 2026-07-28):** English topic/activity requests set probe signal `topic_request` → `conversation` reason `learner_topic_request` (never comprehension failure). `await_comprehension` arms only on `meta_comprehension`. Grammar questions while also answering in the learner’s own Spanish (quotes + “no entiendo” stripped) → `conversation` reason `grammar_question_inline`. Topic-change / boredom phrases can set `affect.boredom_risk=high` (forces fresh-topic chat); high decays to **medium** on next session open (`clear_session_scoped_affect`), not a full clear. Topic suggestions come from `corpus.pack_topic_titles` (pack.md unit table), not a hardcoded boat/café list. **Probe-loop detection** uses the semantic **`asked_topics` registry** on session memory (not a fixed four-name list). Personal hooks / known-open name paths are **gone** (personal capture disabled). Shadow classifier may label `content_offer` / `self_flagged_form` without changing routing until promoted via evals.

`comprehension_check` exists as an enum value and a gate concept (`gate:comprehension_needs_check`), but `select_mode` never returns it today — it is not a shipping mode.

Detailed break policy: `docs/teaching-system.md`.

### 4.5 Scenes (open goals)

JSON under `domain/spanish_a1/scenes/`. A scene is an **open goal with an exit predicate**, not a cutscene. Conversation can satisfy whichever goal the utterance touches.

---

## 5. Character sheet (ability only) + disconnected profile stub

As of **2026-07-28**, the product store is Spanish **ability only**. Personal-data capture is removed by construction (PEDAGOGY §3.1; `docs/reviews-personal-data-removal.md`).

### Ability sheet

**Path:** `logs/character_sheet.json` locally; on serverless the data root moves to `ML_TEACHER_DATA_DIR` or `/tmp/ml_teacher` (`config._DATA_ROOT`)  
**Module:** `tutor/character_sheet.py`  
**Scope:** Spanish ability only (skills, grammar, errors, lexicon schedule/ledger, next_best, affect, coverage).

| Field | Meaning |
|-------|---------|
| `version` / `framework` | Sheet schema metadata |
| `identity` | **Always empty** — stripped at load/normalize/`process_turn`/session open; never written |
| `skills` | Can-dos (IP-01 …) with status / confidence / evidence |
| `grammar` / `lexicon` | Form/word inventory + **schedule/ledger** fields (`introduced_at`, `scaffold`, `first_seen`, `next_due`, `interval_days`, …) — introduce ≠ confidence |
| `error_patterns` | Recurring constructions (e.g. *estoy* vs *está*, *hace calor*) |
| `receptive` | Comprehension-side flags (e.g. `needs_english_scaffold`) |
| `affect` | energy, boredom_risk — session-scoped energy clears on new open; **`boredom_risk=high` decays to `medium`** on open (not wiped) |
| `next_best` | Longer-arc stretch (can-do and/or form focus) — **guide**, not the chat script |
| `coverage` | Topics touched |

### Learner profile (reference only — hard-disabled)

**Module:** `tutor/learner_profile.py` — **disconnected**. Writers no-op / raise; load does not resurrect disk files. `profile_path_for_sheet` remains only so `reset_profile` can **delete** stale `logs/learner_profile.json` from the capture era. Re-enabling any user model is USER-ONLY (PEDAGOGY §7.4), not a flip switch.

| Reset | Effect |
|-------|--------|
| `session.reset_sheet` / “Reset learner” | Wipes ability sheet + chat memory |
| `session.reset_profile` / API `clear_personal` | Deletes leftover personal-file if present; ability unchanged |

`select_mode(..., profile=)` still accepts a profile dict for call compatibility; runtime passes `{}` and does not use personal hooks. Realization prompts do **not** inject a personal-context block.

### Who writes what

| Writer | Role |
|--------|------|
| **Hard observer (sheet)** | Every turn: pattern hits, confidence bumps from learner Spanish |
| **Retrieval scheduler** | Ledger/schedule fields only; cannot move ability confidence |
| **Tool** `update_character_sheet` | Optional (`SHEET_TOOLS=1`); default **off** for latency; identity + schedule fields stripped from model tool path |
| **recompute_next_best** | After evidence, sets stretch + form priority |
| **Progress ledger** | Journey milestones (separate append-only file; not ability confidence) |

The AI is told the sheet is **read-only context**. It must **not** paste sheet JSON into chat. The app owns updates.

### Sheet vs “This turn” rail

| UI | Source of truth |
|----|-----------------|
| **This turn** | Last **mode decision** (live pedagogy) |
| **Sheet arc** (secondary) | `next_best` (longer-term stretch) |
| Morphology | Prefer active **form_focus**, not a mismatched can-do (e.g. names while working *estoy*) |

Older “Focus now = IP-03 always” was misleading after modes shipped.

---

## 6. Session memory (per chat, not durable)

`tutor/session_memory.py`

- What they already **showed** (greet, estoy, name-pattern use, …)  
- What we already **asked** — semantic **`asked_topics` registry** (replaces fixed name-list probes for loop detection)  
- Images shown; last tutor model/try (for comprehension repair)  
- **Seeded from the ability sheet** on open (`seed_from_sheet(sheet, profile={})`) so a returning ability sheet is not blank placement  

Page refresh wipes **chat history** and session memory object, then **re-seeds** from the ability sheet. Web sessions: reset-race fixed 2026-07-28; idle **2h** reaper closes orphan sessions (`IDLE_REAP_SEC` in `tutor/web_app.py`).

---

## 7. Turn pipeline (planned — the only teacher runtime)

`TEACHER_MODE=planned` (default; aliases `plan|new|ai`). Any other value is a
hard `ValueError` at session construction (E4/E4b deletion, 2026-07-28).

1. **Observe** — `mode_state.tick()`, signals, error hits, blank?, next_best snapshot (`observe.py`); phase clock / activity from `SessionPhaseController`  
2. **select_mode** — deterministic ModeDecision (`profile=` accepted, unused for personal data)  
3. **Teach image (pre-AI)** — if mode needs concept: cache hit or **generate** (Gemini image) same-turn  
4. **Build AI context** — ability sheet + pack + stance + mode/task/introduce blocks + session facts (**no** personal-context block)  
5. **tutor_turn** — frontier model (default Gemini); reply budget `TUTOR_MAX_TOKENS` default **4096** (thinking tokens share this budget); classifier shadow may run in parallel  
6. **process_tutor_raw** — first parse of tags (feeds the gate); `stop_reason=max_tokens` → truncated  
7. **output_gate** — teach move, Spanish ratio (`english_wall`), probe loop (`asked_topics`), missing recast, **sheet_leak**, **truncated**, **unscaffolded_new_item** / flood / **regloss**  
8. **One repair** if critical fault and `GATE_REPAIR` (re-parse + re-gate)  
9. **process_turn** — re-parse → hard observer + schedule/ledger + next_best + progress milestones (`_finish`)  
10. **Focus rail** — static live mode immediately; optional async `FOCUS_MODEL` enrich, scheduled **before** logging  
11. **Teach image (post-AI)** — second pass if the turn still has no image and models are present  
12. **Log** — `logs/sessions/*-conversational-web.{md,jsonl}` + cost notes  

Former alternate paths: `TEACHER_MODE=rules` (PlanCard ladder) and the `legacy` harness were **deleted** (E4/E4b, `docs/reviews-architecture-refactor.md`, 2026-07-28) — both bypassed the gate/mode/scheduler/phase layers.

---

## 8. Output gate (verify, don’t hide)

`tutor/output_gate.py`

**Critical faults** — trigger **one** rewrite instruction (when `GATE_REPAIR`, default on):

| Fault | Meaning |
|-------|---------|
| `pedagogy:no_teach_move` | No model/try/recast |
| `pedagogy:open_needs_model_try` | Open without both |
| `gate:english_wall` | Tutor turn mostly English |
| `gate:missing_recast` | Mode required recast tag |
| `gate:form_focus_needs_model` | Hard form break without model/contrast |
| **`gate:sheet_leak`** | Model dumped sheet/tool JSON into the reply |
| **`gate:truncated`** | `stop_reason=max_tokens` — reply cut mid-sentence (one-shot repair retry) |
| **`gate:unscaffolded_new_item`** | Naked first exposure / same-theme cluster extra (r7 S3) |

**Soft faults** — recorded in notes only, no rewrite:

| Fault | Meaning |
|-------|---------|
| `gate:regloss` | Re-gloss of an already-introduced item without same-turn retrieval failure |
| `gate:unscaffolded_flood` | Many bare new keys in one turn (storm soften; cluster extras stay critical) |
| `gate:probe_loop` | Re-asked a semantic topic already in `asked_topics`, or a covered social probe |
| `gate:comprehension_needs_check` | `comprehension_check` turn lacks a real yes/no or A/B ask (unreachable today — that mode is never selected) |
| `pedagogy:recast_without_try` | Recast given but no elicit |

**English wall floors:** default critical below spanish ratio 0.50 (with length floor). **Placement / blank_zero** use floor **0.25** so a compliant glossed true-zero open passes while ratio ≈ 0 still faults (2026-07-28 incident).

Failures stay in **notes** so we can see regressions — do not silently sanitize model faults into a green turn.

---

## 9. Teach images

`tutor/teach_assets.py` + `tutor/image_gen.py`

- **When:** association, comprehension repair, high-visual concrete intro — not every turn  
- **How:** disk cache under `tutor/web_static/teach_assets/`; miss → Gemini `gemini-2.5-flash-image` generate → cache  
- **Policy:** generate on miss when Gemini key present (`TEACH_IMAGE_GENERATE` auto)  

Images bind **referent ↔ Spanish**, not wallpaper.

---

## 10. Audio

| Path | Implementation |
|------|----------------|
| **TTS (default)** | Server Gemini TTS (`/api/audio/speak`), voice e.g. Sulafat; **`TTS_RATE` default 1.0** (native). Slow-style director prefix only at low rates (≤ ~0.8). Client Voice slider 0.7–1.2. |
| **TTS interruption** | Client `speakGeneration` token aborts stale speech loops; interruption must **not** fall back to OS voice for the cut segment; reset/open speak **model/try parts**, not the raw blob |
| **TTS fallback** | Browser `speechSynthesis` |
| **STT local** | Chirp streaming WebSocket when ADC/credentials ready; else Gemini / browser |
| **Vercel** | Prefer browser STT; WS Chirp is a poor fit on serverless |

---

## 11. Models and providers

| Role | Default (typical) | Config |
|------|-------------------|--------|
| Tutor | `gemini-3.6-flash` | `TUTOR_MODEL` (read into the `config.MODEL` constant; there is no `MODEL` env var) |
| Focus rail (optional) | `grok-3-mini` | `FOCUS_MODEL` (`off` = static only) |
| TTS | `gemini-2.5-flash-preview-tts` | `TTS_*` |
| Images | `gemini-2.5-flash-image` | `TEACH_IMAGE_MODEL` |

Clients: `tutor/providers.py` (OpenAI-compatible / Anthropic / Gemini adapters).

---

## 12. Context policy (testing)

**Do not silently truncate** sheet / pack / stance / chat history fed to the teacher while testing. Premature caps made the model “forget” the sheet.

| Flag | Effect |
|------|--------|
| `TEACHER_CONTEXT_TRUNCATE=0` (default) | Full context |
| `=1` | Optional caps for later prod tuning |

- History store: **full session** (no `history[-24:]` drop)  
- Send window: `config.history_for_model()` only when caps enabled  
- Commit gate: `scripts/check_teacher_truncation.py` + `.githooks/pre-commit`  
- Policy: `docs/teacher-context-no-truncate.md`

---

## 13. Course pack

`domain/spanish_a1/` (DATA only — association table, asset sidecar, scenes; the prose course pack was DELETED 2026-08-03: the character sheet carries the curriculum)

- `pack.md` + `unit*.md` — legal language palette (full pack in system context; A1 fits)  
- `scenes/*.json` — open goals  
- `corpus.pack_topic_titles` — unit topic titles from the pack.md table (mode “change topic” palette; no hardcoded boat/café list; association fallback is lexicon-driven, not default `bote`)  
- Can-dos / forms: `tutor/can_dos.py`, `docs/spanish-can-dos-novice.md`  

No vector RAG in v0; swap seam is `tutor/corpus.py`.

---

## 14. Repo map (what matters day-to-day)

| Path | Role |
|------|------|
| `tutor/web_app.py` | FastAPI UI + session cookies |
| `tutor/conv_session.py` | Session engine, planned pipeline |
| `tutor/modes.py` | Mode selection |
| `tutor/executor.py` | AI system + user task builders |
| `tutor/character_sheet.py` | Ability sheet load/save, observer, next_best, schedule fields |
| `tutor/learner_profile.py` | **Hard-disabled** personal-profile reference; delete-only path for stale files |
| `tutor/session_phases.py` | Phase plan + close coda |
| `tutor/retrieval_scheduler.py` | Due ladder + introduce ledger honesty |
| `tutor/association_table.py` / `introduce_router.py` | Association inventory + IntroducePlan |
| `tutor/task_runtime.py` | Info-gap task state |
| `tutor/progress_ledger.py` | Journey milestones |
| `tutor/costs.py` / `signal_classifier.py` | Cost ledger + shadow intent labels |
| `tutor/output_gate.py` | Generate-then-verify (incl. unscaffolded / regloss / flood) |
| `tutor/tutor_response.py` | Tag parse / compose |
| `tutor/teach_assets.py` / `image_gen.py` | Images |
| `tutor/session_memory.py` | Per-chat memory + `asked_topics` + seed from sheet |
| `tutor/can_dos.py` | Can-dos, morphology, **This turn** rail |
| `PEDAGOGY.md` | Sole law home |
| `prompts/conversational_tutor.md` | Teaching stance text |
| `logs/character_sheet.json` | Durable Spanish ability |
| `logs/sessions/` | Turn logs for debugging |
| `tests/` | Unit tests (~526 test methods as of 2026-07-28; gate, phases, scheduler, introduce, task, progress, costs, …) |

---

## 15. Important env vars

| Variable | Notes |
|----------|--------|
| `GEMINI_API_KEY` | Tutor + TTS + images |
| `GROK_API_KEY` | Focus model if Grok |
| `TUTOR_MODEL` | e.g. `gemini-3.6-flash` |
| `FOCUS_MODEL` | `grok-3-mini` or `off` |
| `TUTOR_MAX_TOKENS` | default **4096** (was 1024; Gemini thinking shares this budget with visible text) |
| `GEMINI_REASONING_EFFORT` | optional `low` / `medium` / `high` for Gemini thinking models |
| `TEACHER_MODE` | `planned` (default; aliases `plan|new|ai` — only runtime; `rules`/`legacy` deleted E4/E4b, other values error) |
| `SHEET_TOOLS` | default `false` |
| `TEACHER_CONTEXT_TRUNCATE` | default off |
| `TTS_ENABLED` / `TTS_VOICE` / `TTS_MODEL` | Server voice; model default `gemini-2.5-flash-preview-tts` |
| `TEACH_IMAGE_GENERATE` / `TEACH_IMAGE_MODEL` | auto on with Gemini key; model default `gemini-2.5-flash-image` |
| `GATE_REPAIR` | default `true` — one rewrite on critical gate fault (includes `gate:truncated`) |
| `FOCUS_ASYNC` | default `true` — focus-rail LLM off the tutor latency path |
| `FOCUS_BLOCKING` | default `false` — never block reply on focus enrich |
| `ML_TEACHER_DATA_DIR` | Override data root (sheet, sessions); serverless falls back to `/tmp/ml_teacher` |

---

## 16. How to run and debug

```bash
# local web
cd /path/to/ml_teacher
.venv/bin/python -m tutor.web_app
# → http://127.0.0.1:8765

# tests (sample)
.venv/bin/python -m unittest tests.test_pedagogy_contract tests.test_output_gate \
  tests.test_tutor_response tests.test_focus_panel tests.test_teacher_truncation_check

# truncation commit check
.venv/bin/python scripts/check_teacher_truncation.py
git config core.hooksPath .githooks   # once per clone

# behavioral gate (live model calls; the promotion bar)
.venv/bin/python -m evals.run_conv_smoke          # all 7 conv trajectories
.venv/bin/python -m evals.run_conv_smoke c01      # cheapest single check
```

**Session logs:** open latest `logs/sessions/*conversational-web.md` — mode, phase/activity, gate notes, teach_images, next_best.  
**Ability sheet:** `logs/character_sheet.json` or Full sheet modal.  
**Journey:** `GET /api/progress` / journey rail.  
**Debug ring:** `GET /api/debug/requests` (local).  
**Personal profile:** not a live store; `clear_personal` only removes leftover files.

---

## 17. Deploy notes

- **Local / Fly / Railway:** full fidelity (WS STT, disk sheet).  
- **Vercel:** HTTP chat + static UI OK; disk/sessions ephemeral; Chirp WS poor fit. See `docs/vercel-deploy.md`.

---

## 18. Dual-AI collaboration

- Project notes: `Claude.md`, `GROK.md`  
- Design spars and adjudications: `docs/reviews-*.md`  
- Standing rule: **propose → countersign → adjudicate → converge**; append, don’t rewrite history.

---

## 19. Known tensions / watch-outs

1. **Mode vs next_best** — UI “This turn” must track mode; sheet arc is secondary.  
2. **Sheet dump in chat** — model failure; gate + repair, not silent strip.  
3. **Truncation regressions** — commit checker; keep full context in testing.  
4. **Async focus LLM** — must not block tutor latency; live mode titles must not wait on it.  
5. **Image gen latency** — first miss can take seconds; then cached.  
6. **Serverless vs local** — sheet path and STT differ on Vercel.

---

## 20. Related docs

| Doc | Content |
|-----|---------|
| **`PEDAGOGY.md`** | **Sole law home** (theory + laws + debt + enforcement map) |
| `docs/build-plan-pedagogy-engine.md` | Engine build phases + ship log |
| `docs/teaching-system.md` | Modes, breaks, scenes design |
| `docs/pedagogy-contract.md` | Teach-move invariants |
| `docs/product-persona.md` | Locked persona |
| `docs/character-sheet-deep-dive.md` | Sheet structure (may lag slightly) |
| `docs/design-progression-view.md` | Journey rail design |
| `docs/reviews-personal-data-removal.md` | Personal-data removal adjudication |
| `docs/spanish-can-dos-novice.md` | Can-do inventory |
| `docs/teacher-context-no-truncate.md` | Context / commit gate |
| `docs/web-and-audio.md` | Audio architecture |
| `docs/vercel-deploy.md` | Deploy constraints |
| `README.md` | Quick start |

---

*When behavior and this file disagree, trust the code paths above and update this overview in the same change set.*
