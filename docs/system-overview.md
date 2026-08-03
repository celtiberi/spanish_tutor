# ml_teacher — system overview

**Audience:** humans and agents working on the product  
**Status:** living description of the *current* conversational Spanish tutor (as of 2026-08-03, post full-code audit `docs/reviews-full-code-audit-20260803.md`)  
**Repo:** research + product prototype for AI-taught conversational Spanish (A1 first)

**Law:** `PEDAGOGY.md` (how to teach — theory §0 + teaching rules §2) and `ENGINEERING.md` (everything else — axioms, honesty/engineering/process laws, debt registry, enforcement map). This file maps **what ships today** — it must point at the law files, never restate or fork law paragraphs.

This document supersedes older fragments where they conflict. Deeper design debates live under `docs/reviews-*`.

---

## 1. One-line thesis

**The model is the teacher; code is the record-keeper and auditor** (ENGINEERING §1.1).

The learner experiences a warm Spanish chat. The model owns every teaching decision — what to teach, when to break, how to correct. Code supplies **facts** (character sheet, session memory, due items), verifies **plumbing** (truncation, sheet leaks), records **evidence** (ledgers, logs, exposure bookkeeping), and grades only through the model's own tool calls under honesty clamps.

```text
PLAN turn (open / <replan/>): teaching rules + FULL sheet + history
    → model writes its own <plan> + normal <tutor> reply
ROUND turns: model's OWN plan + full sheet + session facts + recent window
    → model teaches; may revise <plan> or request <replan/>
every turn: parse tags → plumbing gate (truncated / sheet_leak)
    → record: tool grades (clamped), first_seen exposure, ledgers, logs
```

---

## 2. Product persona

| | Choice |
|--|--------|
| Who | Adult, boat/café life OK — **not** a kids flashcard app |
| Level | A1 / false-beginner friendly; true zeros welcome |
| Blank sheet | **Unknown**, not proven beginner (diagnose in conversation, no Hola ladder) |
| Language | Spanish-forward; English is a **lifeline**, not dual-subtitle wallpaper |
| Agenda | The **model** owns the teaching agenda; code keeps records and audits |

**Non-goals:** personal-data capture; scripted probe queues; chat-buddy with no teach move; pure worksheet drills.

See `docs/product-persona.md`.

---

## 3. What the learner sees (web)

**Entry:** `python -m tutor.web_app` → `http://127.0.0.1:8765`  
**Engine:** `tutor/conv_session.py` + `tutor/turn_pipeline.py`

| Surface | Role |
|---------|------|
| Chat | Tutor turns as structured parts (acknowledge / recast / model / try / …) |
| Mic | STT (Chirp stream or Gemini / browser paths) |
| Speak replies | Gemini neural TTS by default (rate **1.0**); client Voice slider 0.7–1.2; browser TTS fallback |
| Header score board | Can-do bands from the character sheet (`compute_progress_score`) |
| **Grades** (left rail) | Ability grades from the model's tool calls (`/api/progress` → `grade_log.build_grades_payload`) |
| **This turn** / Morphology (right rail) | Projections of the sheet and the **realized exchange** (`can_dos.build_focus_panel`, `exchange_render`, `turn_morph`) — never an agenda (ENGINEERING §1.1b) |
| Full sheet | Modal: skills, errors, human dump (**ability only**; identity always empty) |
| Composer | Client `maxlength` mirrors `/api/health` `chat_max_chars` (`CHAT_MAX_CHARS=12000`) |
| Teach images | Cache-first referent images when an introduction anchors on one |
| GATE FAIL banner | Plumbing faults ship visibly (no-hide) — never silently sanitized |
| Debug (local) | In-memory request ring + `GET /api/debug/requests` |

Page load starts a **new chat** but keeps the **ability sheet** on disk. "Reset learner" wipes Spanish progress (`reset_sheet`). `clear_personal` / `session.reset_profile` only **deletes leftover** `learner_profile.json` files from the capture era — nothing loads or writes personal facts.

---

## 4. Pedagogy

**Law pointer:** the teaching rules live only in `PEDAGOGY.md` (§0 theory, §2 rules). The model **receives the rules** on plan turns (NOTES/INTERNAL spans cut — `session_plan.load_pedagogy`); code never re-implements them as runtime judgment. Whether pedagogy + prompts are working is judged by **evals over AI-student transcripts** (`evals/student_checks.py` + blind rubric), not by runtime gates.

### 4.0 What ships (surviving modules)

| Module | Role |
|--------|------|
| `tutor/session_plan.py` | Two-phase teacher context: PLAN turns (full rules + sheet + history) vs ROUND turns (model's own plan + sheet + facts + window) |
| `tutor/character_sheet.py` | The sheet: domain model + learner model; honesty clamps on tool grades |
| `tutor/retrieval_scheduler.py` | first_seen/introduced ledger + due ladder; introduce ≠ ability bump |
| `tutor/association_table.py` + `domain/spanish_a1/association_table.json` | Target inventory (keys, themes, clusters) |
| `tutor/introduce_router.py` | Shadow introduce planning + R-B image attach + ledger writes — telemetry and bookkeeping, no instruction text ships |
| `tutor/output_gate.py` | Plumbing gate (`gate:truncated`, `gate:sheet_leak`) + first-exposure scan (bookkeeping) |
| `tutor/progress_ledger.py` | Append-only milestone history (journey/grades data) |
| `tutor/grade_log.py` | Model tool-grade ledger (`logs/sheet_grades.jsonl`) |
| `tutor/signal_classifier.py` | Shadow intent labels (`content_offer`, `self_flagged_form`, …) — audit trail, not routing authority |
| `tutor/costs.py` | Per-session cost ledger |

**Deleted machinery (2026-08-03 full-code audit — see `docs/reviews-full-code-audit-20260803.md`):** the mode router (`modes.py`), session phases, task runtime, scenes, the prose course pack, `corpus.py`, `focus_enrich.py`, the falsifier prompt arms, and every runtime teaching-opinion gate. Git history is the archive (ENGINEERING §4.6).

### 4.1 Learning science we optimize for

| Idea | Product translation |
|------|---------------------|
| **CLT** | Language for real communication, not isolated drills |
| **Comprehensible input (CI)** | Mostly clear Spanish the learner can map to meaning |
| **Association** | Form ↔ meaning (image, context) before English gloss walls |
| **Focus on form** | Brief recast / contrast *inside* meaning; then transfer |
| **Transfer** | Same form, **new** micro-context — not re-drill the same line |
| **Trajectory** | Teaching is multi-turn: model → try → feedback → transfer |

### 4.2 Teach move

The teach-every-turn expectation (model / try / recast; open needs model + try) is **law text the model receives** (PEDAGOGY §2), checked as **eval findings** over transcripts (`evals/student_checks.check_teach_shape`), not enforced by runtime gates. `tutor/pedagogy_contract.py` keeps only mechanical helpers (`is_blank_learner`, `open_phase`, `has_teach_move`); the runtime judgment half was deleted (S11, 2026-08-03). Historical write-up: `docs/pedagogy-contract.md`.

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

Plus the private context tags: `<plan>…</plan>` (session plan, stripped before the learner sees anything) and `<replan/>` (request full-context re-plan).

Parser: `tutor/tutor_response.py` (+ `session_plan.extract_plan`).  
**Forbidden in the reply:** character-sheet JSON, tool dumps, can-do codes, confidence blobs. That is a **gate fault** (`gate:sheet_leak`), not something to silently scrub into a "success."

### 4.4 Modes — DELETED

The code-owned mode router (`tutor/modes.py`) was deleted 2026-08-03 (full-code-audit S4): the model decides when to break, correct, or repair. Surviving wires (image attach, introduce bookkeeping, uptake flag) moved to evidence-based stages in `turn_pipeline.py`.

### 4.5 Scenes — DELETED

Scene JSON and its shipping path were deleted 2026-08-03 (full-code-audit S1a/S9): scripted scene lines into the teacher prompt were the forbidden class (ENGINEERING §1.1a), and goal/exit residue was still code-selected steering.

---

## 5. Character sheet (domain model + learner model)

The sheet is ONE artifact holding both the **domain model** (every target the level covers: inventory keys, grammar forms, can-dos, scope — domain data in `domain/spanish_a1/`) and the **learner model** (per-item evidence, confidence, schedule). It is **never a curriculum**: it never sequences; the model plans its own path (`session_plan.PLAN_INSTRUCTIONS`).

As of **2026-07-28**, the store is Spanish **ability only**. Personal-data capture is removed by construction (ENGINEERING §3.1; `docs/reviews-personal-data-removal.md`).

**Path:** `logs/character_sheet.json` locally; on serverless the data root moves to `ML_TEACHER_DATA_DIR` or `/tmp/ml_teacher` (`config._DATA_ROOT`)  
**Module:** `tutor/character_sheet.py`

| Field | Meaning |
|-------|---------|
| `version` / `framework` | Sheet schema metadata |
| `identity` | **Always empty** — stripped at load/normalize/`process_turn`/session open; never written |
| `skills` | Can-dos (IP-01 …) with status / confidence / evidence |
| `grammar` / `lexicon` | Form/word inventory + **schedule/ledger** fields (`introduced_at`, `scaffold`, `first_seen`, `next_due`, `interval_days`, …) — introduce ≠ confidence (ENGINEERING §3.2) |
| `error_patterns` | Recurring constructions (e.g. *estoy* vs *está*, *hace calor*) — shipped to the model as **facts** (label + example), never as imperatives |
| `receptive` | Comprehension-side flags (e.g. `needs_english_scaffold`) |
| `affect` | `energy` (session-scoped; cleared on new open). The boredom pathway was deleted 2026-07-30 (`evals/omission_ledger.jsonl`) |
| `next_best` | UI/telemetry stretch hint only — **stripped from the model payload** (S1b, 2026-08-03) |
| `coverage` | Topics touched |

A corrupt sheet file is **quarantined** (renamed `<name>.corrupt-<stamp>`) with a visible error, never silently overwritten (S5.1).

### Who writes what

| Writer | Role |
|--------|------|
| **Model tool** `update_character_sheet` | THE ability path (`SHEET_TOOLS` default **on**). Tool grades pass honesty clamps (`_clamp_skill_entry`: rate-limited confidence, no promotion by claim — ENGINEERING §3.2/§4.5) and land in the grade ledger. Tools off → ability **freezes** (no silent regex bumps; the rules-based updater died 2026-07-31) |
| **Retrieval scheduler** | Ledger/schedule fields only; cannot move ability confidence |
| **First-exposure scan** | `output_gate.scan_first_exposures` → `first_seen` for every visibly-used table key (bookkeeping, not judgment) |
| **recompute_next_best** | Sheet-file/UI stretch hint (not sent to the model) |
| **Progress ledger** | Milestone history (separate append-only file; not ability confidence) |

The AI is told the sheet is **read-only context** in the reply; it must **not** paste sheet JSON into chat (gate:sheet_leak). Ability moves ride the tool call.

### Learner profile (reference only — hard-disabled)

`tutor/learner_profile.py` is **disconnected**. Writers no-op / raise; load does not resurrect disk files. `profile_path_for_sheet` remains only so `reset_profile` can **delete** stale `logs/learner_profile.json` from the capture era. Re-enabling any user model is USER-ONLY (ENGINEERING §7.4).

| Reset | Effect |
|-------|--------|
| `session.reset_sheet` / "Reset learner" | Wipes ability sheet + chat memory |
| `session.reset_profile` / API `clear_personal` | Deletes leftover personal-file if present; ability unchanged |

---

## 6. Session memory (per chat, not durable)

`tutor/session_memory.py`

- What they already **showed** (greet, estoy, …) and what we already **asked** — the semantic **`asked_topics` registry** (feeds the executor's do-not-re-ask facts)
- Images shown; last tutor model/try
- **Seeded from the ability sheet** on open (`seed_from_sheet`) so a returning learner is not treated as blank

Page refresh wipes chat history and the session memory object, then re-seeds from the sheet. Web sessions: idle **2h** reaper closes orphans (`IDLE_REAP_SEC` in `tutor/web_app.py`).

---

## 7. Turn pipeline (the only teacher runtime)

`TEACHER_MODE=planned` (default; aliases `plan|new|ai`). Any other value is a hard `ValueError` at session construction (E4/E4b deletion, 2026-07-28). Stages live in `tutor/turn_pipeline.py`; context policy in `tutor/session_plan.py`.

1. **Observe** — signals, error hits, blank detection (`observe.py`); shadow classifier may run in parallel (`signal_classifier.py`)
2. **Context build** — PLAN turn (no stored plan / `<replan/>` requested): teaching rules + full sheet + full history + plan instructions. ROUND turn: model's own plan + full sheet + session facts + due data + `ROUND_HISTORY_MESSAGES=12` window (the one sanctioned, `truncation-ok`-annotated window — ENGINEERING §3.3)
3. **Teach image (pre-AI)** — evidence-based attach (introduce R-B / declared image): cache hit or Gemini generate same-turn
4. **tutor_turn** — frontier model (default Gemini) with the `update_character_sheet` tool; reply budget `TUTOR_MAX_TOKENS` default **4096** (thinking tokens share it)
5. **Plan harvest** — `<plan>` stored verbatim, `<replan/>` flagged (cleared only after a successful call); plan text lands in the audit trail
6. **Parse** — `process_tutor_raw` tags → parts; `stop_reason=max_tokens` → `gate:truncated`
7. **Plumbing gate** — `gate:truncated` + `gate:sheet_leak` ONLY (S11); faults ship visibly (GATE FAIL banner + notes) — no rewrite loop, no teaching opinions
8. **Record** — tool grades through honesty clamps + grade ledger; `first_seen` exposure bookkeeping; retrieval/introduce ledgers; progress milestones; atomic sheet commit
9. **Log** — debug ring + `logs/sessions/<YYYY-MM-DD>/<id>.{jsonl,md,requests.jsonl}` (files created lazily on the first learner turn) + cost notes

---

## 8. Output gate (plumbing only — verify, don't hide)

`tutor/output_gate.py` — reduced to what code can actually judge (S11 ruling, 2026-08-03: "Why are you making gates for this?"):

| Fault | Meaning |
|-------|---------|
| **`gate:truncated`** | Provider cut the reply (`stop_reason=max_tokens`) |
| **`gate:sheet_leak`** | Internal JSON / tool talk in learner-visible text |

Both are critical; the raw reply still ships with a visible GATE FAIL banner + `still_fail` notes (no-hide — never sanitize a fault into a green turn). There is no repair/rewrite loop.

Every former teaching-opinion check (english_wall, probe_loop, unscaffolded/cluster, regloss, teach-move contracts) lives ONLY as eval findings over AI-student transcripts: `evals/student_checks.py` (severity ledger in its header). The teaching rules themselves stay in PEDAGOGY §2 — the model still receives them.

The gate module also hosts `scan_first_exposures` (+ `gloss_after_key` / `anchor_in_reply`) — first-exposure **bookkeeping** shared with the introduce ledger, not judgment.

---

## 9. Teach images

`tutor/teach_assets.py` + `tutor/image_gen.py`

- **When:** an introduction anchors on a referent (R-B image scaffold) or the tutor declares an image — evidence-based, not every turn
- **How:** disk cache under `tutor/web_static/teach_assets/`; miss → Gemini `gemini-2.5-flash-image` generate → cache; metadata sidecar `domain/spanish_a1/asset_sidecar.json` (keys validated against the association table)
- **Policy:** generate on miss when a Gemini key is present (`TEACH_IMAGE_GENERATE` auto)

Images bind **referent ↔ Spanish**, not wallpaper.

---

## 10. Audio

| Path | Implementation |
|------|----------------|
| **TTS (default)** | Server Gemini TTS (`/api/audio/speak`), voice e.g. Sulafat; **`TTS_RATE` default 1.0** (native). Slow-style director prefix only at low rates (≤ ~0.8). Client Voice slider 0.7–1.2 |
| **TTS interruption** | Client `speakGeneration` token aborts stale speech loops; interruption must **not** fall back to OS voice for the cut segment; reset/open speak **model/try parts**, not the raw blob |
| **TTS fallback** | Browser `speechSynthesis` |
| **STT local** | Chirp streaming WebSocket when ADC/credentials ready; else Gemini / browser |
| **Vercel** | Prefer browser STT; WS Chirp is a poor fit on serverless |

---

## 11. Models and providers

| Role | Default (typical) | Config |
|------|-------------------|--------|
| Tutor | `gemini-3.6-flash` | `TUTOR_MODEL` (read into the `config.MODEL` constant; there is no `MODEL` env var) |
| Signal classifier (shadow) | `gemini-flash-lite-latest` | `SIGNAL_CLASSIFIER_MODEL` (`off` in CI) |
| TTS | `gemini-2.5-flash-preview-tts` | `TTS_*` |
| Images | `gemini-2.5-flash-image` | `TEACH_IMAGE_MODEL` |

Clients: `tutor/providers.py` (Anthropic / xAI-compat / Gemini adapters).

---

## 12. Teacher context policy

Two-phase (TEACHER_CONTEXT=`plan`, the default): PLAN turns carry the full rules + full sheet + full history; ROUND turns carry the model's own plan + full sheet + facts + the versioned 12-message window — the ONE sanctioned window (ENGINEERING §3.3 amendment 2026-08-03). `TEACHER_CONTEXT=full` restores historical every-turn full context.

**Do not silently truncate** sheet / stance / history on the teacher path. No `[:N]` slices, no `history[-N:]` drops (literal or named-constant).

- Commit gate: `scripts/check_teacher_truncation.py` + `.githooks/pre-commit`
- Policy: `docs/teacher-context-no-truncate.md`
- `TEACHER_CONTEXT_TRUNCATE=1` enables the explicit prod-tuning caps (`*_PROMPT_CHARS`, `HISTORY_TURNS`); default off

---

## 13. Domain data

`domain/spanish_a1/` — the domain-model **data** for the level (no prose, no path law). This directory IS the level slice; editing it changes what the teacher teaches and grades, zero code edits (S10, executed 2026-08-03):

- `association_table.json` — target inventory (~175 keys; themes, clusters, false-friend slots)
- `can_dos.json` — can-do inventory + theme→can-do routing + per-can-do phrase chunks + stretch-activity labels
- `grammar_forms.json` — supporting forms (supports/priority/error_example) merged with their teaching paradigms
- `domain_scope.json` — level + deferred / out-of-scope / recognition-only lists
- `misconceptions.json` — error-pattern catalog (labels, form links, pack M-ID provenance, detect/resolve regexes as data)
- `asset_sidecar.json` — teach-image metadata keyed by table keys
- `migration_deprecations.json` — retired-key escape hatch for sidecar validation

`tutor/domain_data.py` loads + validates the four S10 files at startup (all problems listed, loud failure — no silent default); `tutor/can_dos.py` / `tutor/character_sheet.py` bind their public names (`CAN_DOS`, `FORM_INVENTORY`, `MORPHOLOGY_BY_FORM`, `DOMAIN_SCOPE`, `ERROR_PATTERN_CATALOG`) from it and keep mechanics only. The prose course pack (`pack.md` + units), `corpus.py` (its retrieval seam), and the scenes JSON were **deleted 2026-08-03** (full-code audit S1/S2/S9): the character sheet carries the domain targets + scope, and the model plans from sheet + PEDAGOGY.md.

---

## 14. Repo map (what matters day-to-day)

| Path | Role |
|------|------|
| `tutor/web_app.py` | FastAPI UI + session cookies |
| `tutor/conv_session.py` | Session engine (owns state, history, ledger wiring) |
| `tutor/turn_pipeline.py` | Staged turn: context → model → gate → record → log |
| `tutor/session_plan.py` | Two-phase plan/round context + `<plan>`/`<replan/>` harvest |
| `tutor/executor.py` | AI system + user task builders (facts in, no scripts) |
| `tutor/character_sheet.py` | The sheet: load/save/quarantine, tool-grade clamps, next_best |
| `tutor/grade_log.py` | Tool-grade ledger + `/api/progress` payload |
| `tutor/retrieval_scheduler.py` | Due ladder + introduce/first_seen ledger honesty |
| `tutor/association_table.py` / `introduce_router.py` | Target inventory + shadow introduce planning/bookkeeping |
| `tutor/output_gate.py` | Plumbing gate + first-exposure scan |
| `tutor/progress_ledger.py` | Milestone history |
| `tutor/costs.py` / `signal_classifier.py` | Cost ledger + shadow intent labels |
| `tutor/tutor_response.py` | Tag parse / compose |
| `tutor/teach_assets.py` / `image_gen.py` | Images |
| `tutor/session_memory.py` / `session_state.py` | Per-chat memory + aggregate session state |
| `tutor/can_dos.py` / `domain_data.py` | Can-do/form mechanics + focus-panel projection over the `domain/` data (validating loader) |
| `tutor/exchange_render.py` / `turn_morph.py` | Realized-exchange projections for the rail (ENGINEERING §1.1b) |
| `tutor/session_log.py` | Lazy dated session logs + model traffic log |
| `tutor/ai_student.py` | AI learner simulator (evals) |
| `tutor/learner_profile.py` | **Hard-disabled** personal-profile reference; delete-only path for stale files |
| `PEDAGOGY.md` / `ENGINEERING.md` | The law files |
| `prompts/` | Exactly 3: `conversational_tutor.md`, `tutor_persona.md`, `ai_student.md` |
| `domain/spanish_a1/` | Domain data (see §13) |
| `evals/` | The promotion bar (see §16) |
| `logs/character_sheet.json` | Durable Spanish ability |
| `logs/sessions/<YYYY-MM-DD>/` | Session + traffic logs (lazy — first learner turn creates them) |
| `tests/` | Unit tests (~705 as of 2026-08-03) |

---

## 15. Important env vars (truth source: `tutor/config.py`)

| Variable | Notes |
|----------|--------|
| `GEMINI_API_KEY` | Tutor + TTS + images + classifier default |
| `GROK_API_KEY` / `ANTHROPIC_API_KEY` | Alternative tutor/classifier providers |
| `TUTOR_MODEL` | default `gemini-3.6-flash` |
| `TUTOR_MAX_TOKENS` | default **4096** (Gemini thinking shares this budget with visible text) |
| `GEMINI_REASONING_EFFORT` | optional `low` / `medium` / `high` for Gemini thinking models |
| `TEACHER_MODE` | `planned` (default; aliases `plan|new|ai` — the only runtime; other values error) |
| `TEACHER_CONTEXT` | `plan` (default two-phase) or `full`; `brief` deleted 2026-08-03 |
| `SHEET_TOOLS` | default **`true`** — model tool grading on; off = ability freezes |
| `STRICT_ERRORS` | default off — errors visible but non-fatal; `1` re-raises (no-hide) |
| `TUTOR_PERSONA` | default on; `off` disables the persona layer |
| `TEACHER_CONTEXT_TRUNCATE` | default off (testing = full context); `1` enables the `*_PROMPT_CHARS` / `HISTORY_TURNS` caps |
| `SIGNAL_CLASSIFIER_MODEL` / `_TIMEOUT_S` / `_BLOCKING` | shadow intent classifier (`off` in CI; blocking promotion gated on evals) |
| `TTS_ENABLED` / `TTS_VOICE` / `TTS_MODEL` / `TTS_RATE` / `TTS_PREFER_BROWSER` | server voice; model default `gemini-2.5-flash-preview-tts`; rate default 1.0 |
| `TEACH_IMAGE_GENERATE` / `TEACH_IMAGE_MODEL` | auto on with Gemini key; model default `gemini-2.5-flash-image` |
| `GRADE_LOG_PATH` | override the tool-grade ledger path (evals pin it per run) |
| `COST_PRICING_JSON` | per-model price overrides for the cost ledger |
| `ML_TEACHER_DATA_DIR` | Override data root (sheet, sessions); serverless falls back to `/tmp/ml_teacher` |

Deleted knobs (do not reintroduce): `FOCUS_MODEL`/`FOCUS_ASYNC`/`FOCUS_BLOCKING` (focus enricher), `GATE_REPAIR` (gate rewrite), `TEACHER_PROMPT_ORDER` (falsifier arms), `POLICY_PATH`, `CONTROLLER_*`, `PLANNER_MAX_TOKENS`.

---

## 16. How to run, test, and debug

```bash
# local web
cd /path/to/ml_teacher
.venv/bin/python -m tutor.web_app
# → http://127.0.0.1:8765

# unit suite
.venv/bin/python -m pytest tests/ -q

# truncation commit check
.venv/bin/python scripts/check_teacher_truncation.py
git config core.hooksPath .githooks   # once per clone

# behavioral evals (live model calls; THE promotion bar — ENGINEERING §4.3)
.venv/bin/python -m evals.run_conv_smoke          # scripted conv trajectories
.venv/bin/python -m evals.run_conv_smoke c01      # cheapest single check
.venv/bin/python -m evals.run_student_smoke       # AI-student sim + student_checks
```

**Session logs:** `logs/sessions/<YYYY-MM-DD>/<id>.md` (+ `.jsonl` twin) — created only once a session gets a learner turn; open-only page loads write nothing.  
**Model traffic:** `logs/sessions/<YYYY-MM-DD>/<id>.requests.jsonl` — full request + response per tutor call (`sent` / `received`, no truncation).  
**Ability sheet:** `logs/character_sheet.json` or the Full sheet modal.  
**Grades:** `GET /api/progress` / Grades rail; ledger at `logs/sheet_grades.jsonl`.  
**Debug ring:** `GET /api/debug/requests` (local, in-memory).  
**Personal profile:** not a live store; `clear_personal` only removes leftover files.

---

## 17. Deploy notes

- **Local / Fly / Railway:** full fidelity (WS STT, disk sheet).  
- **Vercel:** HTTP chat + static UI OK; disk/sessions ephemeral; Chirp WS poor fit. See `docs/vercel-deploy.md`.

---

## 18. Dual-AI collaboration

- Project notes: `CLAUDE.md`, `GROK.md`  
- Design spars and adjudications: `docs/reviews-*.md` (catalog: `docs/reviews-index.md`)  
- Standing rule: **propose → countersign → adjudicate → converge**; append, don't rewrite history.

---

## 19. Known tensions / watch-outs

1. **Sheet dump in chat** — model failure; visible gate fault, not silent strip.  
2. **Truncation regressions** — commit checker; ROUND window is the only sanctioned slice.  
3. **Plan staleness** — the model replans rarely; revive-condition for any forced replan is a live transcript showing plan/window drift (S9 ruling — the traffic log captures the evidence).  
4. **Image gen latency** — first miss can take seconds; then cached.  
5. **Serverless vs local** — sheet path and STT differ on Vercel.  
6. **Content-as-code** — DONE 2026-08-03 (S10): the domain model lives in `domain/spanish_a1/` as data; `can_dos.py` / `character_sheet.py` keep mechanics only. Watch that new teaching content lands in the JSON, not back in Python literals.

---

## 20. Related docs

| Doc | Content |
|-----|---------|
| **`PEDAGOGY.md`** | Teaching law (theory §0 + rules §2) |
| **`ENGINEERING.md`** | Engineering/honesty/process law + debt + enforcement |
| `docs/reviews-full-code-audit-20260803.md` | The 2026-08-03 audit slate + execution stamps |
| `docs/pedagogy-contract.md` | Teach-move invariants (historical; enforcement moved to evals) |
| `docs/product-persona.md` | Locked persona |
| `docs/character-sheet-deep-dive.md` | Sheet structure (may lag) |
| `docs/design-progression-view.md` | Grades/journey rail design |
| `docs/reviews-personal-data-removal.md` | Personal-data removal adjudication |
| `docs/spanish-can-dos-novice.md` | Can-do inventory |
| `docs/teacher-context-no-truncate.md` | Context / commit gate |
| `docs/web-and-audio.md` | Audio architecture |
| `docs/vercel-deploy.md` | Deploy constraints |
| `README.md` | Front door |

---

*When behavior and this file disagree, trust the code paths above and update this overview in the same change set.*
