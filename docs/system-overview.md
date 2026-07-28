# ml_teacher — system overview

**Audience:** humans and agents working on the product  
**Status:** living description of the *current* conversational Spanish tutor (as of 2026-07-27)  
**Repo:** research + product prototype for **pedagogy-first** tutoring, with Spanish A1 as the first pack

This document supersedes older fragments where they conflict. Deeper design debates live under `docs/reviews-*` and `docs/teaching-system.md`; this file is the map of **what ships today**.

---

## 1. One-line thesis

**Conversation is the vehicle; teaching is knowing when to break, what goal is open, and whether the form landed.**

The learner experiences a warm Spanish chat. Underneath, code selects a **mode**, the AI **realizes** the turn in Spanish, code **gates** the reply, and code updates the **ability sheet** and **learner profile** from evidence.

```text
observe(learner, sheet, session)
    → select_mode(..., profile=) # CODE — deterministic
    → AI realize(mode, sheet + personal context)
    → output_gate(turn)          # CODE — one repair if critical (incl. gate:truncated)
    → hard_observer / sheet + profile   # CODE — ability vs personal, separate stores
```

---

## 2. Product persona

| | Choice |
|--|--------|
| Who | Adult, boat/café life OK — **not** a kids flashcard app |
| Level | A1 / false-beginner friendly; true zeros welcome |
| Blank sheet | **Unknown**, not proven beginner (placement, not a Hola ladder) |
| Language | Spanish-forward; English is a **lifeline**, not dual-subtitle wallpaper |
| Agenda | AI realizes the turn; **code** owns mode, ability sheet, learner profile, and output gate |

**Non-goals:** scripted social probe queue as the default product; chat-buddy with no teach move; pure worksheet drills.

See `docs/product-persona.md`.

---

## 3. What the learner sees (web)

**Entry:** `python -m tutor.web_app` → `http://127.0.0.1:8765`  
**Engine:** `tutor/conv_session.py` (shared with CLI)

| Surface | Role |
|---------|------|
| Chat | Tutor turns as structured parts (acknowledge / recast / model / try / …) |
| Mic | STT (Chirp stream or Gemini / browser paths) |
| Speak replies | Gemini neural TTS by default; browser TTS fallback |
| Progress score | Top header — 0–100 ≈ mean confidence over the 11 tracked can-dos × 100, plus up to +5 for resolved error-pattern streaks (`compute_progress_score`) |
| **This turn** (rail) | **Live mode** for the current turn (not a stale can-do title) |
| Morphology (rail) | Forms in play (prefer form_focus e.g. *estar*, not a random can-do) |
| Full sheet | Modal: skills, errors, next_best, human dump (ability only; name may be shimmed from profile for display) |
| Composer | Client `maxlength` mirrors `/api/health` `chat_max_chars` (`CHAT_MAX_CHARS=12000` on `ChatIn`) |
| Teach images | When association / repair / concrete intro needs a referent |

Page load starts a **new chat** but keeps the **ability sheet** and **learner profile** on disk. “Reset learner” wipes Spanish progress (`reset_sheet`) and **keeps** the profile; personal-only clear is `clear_personal` / `session.reset_profile` (API).

---

## 4. Pedagogy

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

**Routing signals (2026-07-27):** English topic/activity requests set probe signal `topic_request` → `conversation` reason `learner_topic_request` (never comprehension failure). `await_comprehension` arms only on `meta_comprehension`. Grammar questions while also answering in the learner’s own Spanish (quotes + “no entiendo” stripped) → `conversation` reason `grammar_question_inline`. Topic-change / boredom phrases can set `affect.boredom_risk=high` (forces fresh-topic chat); high decays to **medium** on next session open (`clear_session_scoped_affect`), not a full clear. Topic suggestions come from `corpus.pack_topic_titles` (pack.md unit table), not a hardcoded boat/café list. Known-open personal hooks are optional/varied and **skipped** under topic fatigue.

`comprehension_check` exists as an enum value and a gate concept (`gate:comprehension_needs_check`), but `select_mode` never returns it today — it is not a shipping mode.

Detailed break policy: `docs/teaching-system.md`.

### 4.5 Scenes (open goals)

JSON under `course_packs/spanish_a1/scenes/`. A scene is an **open goal with an exit predicate**, not a cutscene. Conversation can satisfy whichever goal the utterance touches.

---

## 5. Character sheet + learner profile (two durable stores)

As of **2026-07-27**, Spanish **ability** and **who the person is** are separate files/lifecycles.

### Ability sheet

**Path:** `logs/character_sheet.json` locally; on serverless the data root moves to `ML_TEACHER_DATA_DIR` or `/tmp/ml_teacher` (`config._DATA_ROOT`)  
**Module:** `tutor/character_sheet.py`  
**Scope:** Spanish ability only (skills, grammar, errors, next_best, affect, coverage).

| Field | Meaning |
|-------|---------|
| `version` / `framework` | Sheet schema metadata |
| `identity` | **Deprecated on the ability sheet** — legacy sheets migrate into the profile on session load (`migrate_from_sheet`); `engagement_notes` is retired in favor of profile `hooks` / `sensitive` |
| `skills` | Can-dos (IP-01 …) with status / confidence / evidence |
| `grammar` | Form inventory (e.g. `present_estar_person`) |
| `error_patterns` | Recurring constructions (e.g. *estoy* vs *está*, *hace calor*) |
| `lexicon` | Concrete words with confidence |
| `receptive` | Comprehension-side flags (e.g. `needs_english_scaffold`) |
| `affect` | energy, boredom_risk — session-scoped energy clears on new open; **`boredom_risk=high` decays to `medium`** on open (not wiped) |
| `next_best` | Longer-arc stretch (can-do and/or form focus) — **guide**, not the chat script |
| `coverage` | Topics touched |

### Learner profile (personal / PII)

**Path:** `logs/learner_profile.json` (or `*.profile.json` sibling for non-default sheet paths)  
**Module:** `tutor/learner_profile.py`  
**Fields:** `preferred_name`, `l1`, `goals`, `hooks`, `interests`, `sensitive` (care notes, e.g. bereavement guidance).

| Reset | Effect |
|-------|--------|
| `session.reset_sheet` / “Reset learner” | Wipes ability sheet + chat memory; **keeps** profile |
| `session.reset_profile` / API `clear_personal` | Clears personal data only; **keeps** Spanish progress |

`process_turn(..., profile=)` and `select_mode(..., profile=)` take the profile. Prompts send **two** system blocks: ability sheet vs personal context (`personal_context_for_prompt`).

### Who writes what

| Writer | Role |
|--------|------|
| **Hard observer (sheet)** | Every turn: pattern hits, confidence bumps from learner Spanish |
| **Hard observer (profile)** | Name capture + personal facts → profile (`learner_profile.capture_name` / updates) |
| **Tool** `update_character_sheet` | Optional (`SHEET_TOOLS=1`); default **off** for latency |
| **recompute_next_best** | After evidence, sets stretch + form priority |

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

- What they already **showed** (greet, estoy, name, …)  
- What we already **asked** (avoid re-probing)  
- Images shown; last tutor model/try (for comprehension repair)  
- **Seeded from the ability sheet + profile** on open (`seed_from_sheet(sheet, profile)`) so a new chat does not treat a known learner as blank placement  

Page refresh wipes **chat history** and session memory object, then **re-seeds** from sheet + profile.

---

## 7. Turn pipeline (planned / default)

`TEACHER_MODE=planned` (default).

1. **Observe** — `mode_state.tick()`, signals, error hits, blank?, next_best snapshot (`observe.py`)  
2. **select_mode** — deterministic ModeDecision (`profile=` for known-open hooks / care rules)  
3. **Teach image (pre-AI)** — if mode needs concept: cache hit or **generate** (Gemini image) same-turn  
4. **Build AI context** — ability sheet block + personal-context block + pack + stance + mode task + session facts  
5. **tutor_turn** — frontier model (default Gemini); reply budget `TUTOR_MAX_TOKENS` default **4096** (thinking tokens share this budget)  
6. **process_tutor_raw** — first parse of tags (feeds the gate); `stop_reason=max_tokens` → truncated  
7. **output_gate** — teach move, Spanish ratio, probe loop, missing recast, **sheet_leak**, **truncated**  
8. **One repair** if critical fault and `GATE_REPAIR` (re-parse + re-gate)  
9. **process_turn** — re-parse → hard observer + next_best (`_finish`)  
10. **Focus rail** — static live mode immediately; optional async `FOCUS_MODEL` enrich, scheduled **before** logging  
11. **Teach image (post-AI)** — second pass if the turn still has no image and models are present  
12. **Log** — `logs/sessions/*-conversational-web.{md,jsonl}`  

Legacy paths: `TEACHER_MODE=rules` (PlanCard), `legacy` harness — not the product default.

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

**Soft faults** — recorded in notes only, no rewrite:

| Fault | Meaning |
|-------|---------|
| `gate:probe_loop` | Re-asked name / how-are-you / etc. already covered |
| `gate:comprehension_needs_check` | `comprehension_check` turn lacks a real yes/no or A/B ask (unreachable today — that mode is never selected) |
| `pedagogy:recast_without_try` | Recast given but no elicit |

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
| **TTS (default)** | Server Gemini TTS (`/api/audio/speak`), voice e.g. Sulafat; short director line (`SLOW_STYLE_PREFIX = "Speak slowly and clearly. "` when rate &lt; 1.0) |
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

`course_packs/spanish_a1/`

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
| `tutor/character_sheet.py` | Ability sheet load/save, observer, next_best |
| `tutor/learner_profile.py` | Personal profile (name, hooks, sensitive); migrate from legacy sheet identity |
| `tutor/output_gate.py` | Generate-then-verify |
| `tutor/tutor_response.py` | Tag parse / compose |
| `tutor/teach_assets.py` / `image_gen.py` | Images |
| `tutor/session_memory.py` | Per-chat memory + seed from sheet + profile |
| `tutor/can_dos.py` | Can-dos, morphology, **This turn** rail |
| `prompts/conversational_tutor.md` | Teaching stance text |
| `logs/character_sheet.json` | Durable Spanish ability |
| `logs/learner_profile.json` | Durable personal facts (PII; separate reset) |
| `logs/sessions/` | Turn logs for debugging |
| `tests/` | Unit tests (gate, modes, sheet, focus, truncation) |

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
| `TEACHER_MODE` | `planned` (default) |
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

**Session logs:** open latest `logs/sessions/*conversational-web.md` — mode, gate notes, teach_images, next_best.  
**Ability sheet:** `logs/character_sheet.json` or Full sheet modal.  
**Personal profile:** `logs/learner_profile.json` (not wiped by Reset learner).

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
| `docs/teaching-system.md` | Modes, breaks, scenes design |
| `docs/pedagogy-contract.md` | Teach-move invariants |
| `docs/product-persona.md` | Locked persona |
| `docs/character-sheet-deep-dive.md` | Sheet structure (may lag slightly) |
| `docs/spanish-can-dos-novice.md` | Can-do inventory |
| `docs/teacher-context-no-truncate.md` | Context / commit gate |
| `docs/web-and-audio.md` | Audio architecture |
| `docs/vercel-deploy.md` | Deploy constraints |
| `README.md` | Quick start |

---

*When behavior and this file disagree, trust the code paths above and update this overview in the same change set.*
