# ml_teacher — conversational Spanish tutor

**The model is the teacher; code is the record-keeper and auditor** (ENGINEERING §1.1).
A frontier model teaches Spanish (A1 first) in conversation. Code keeps the facts —
character sheet, ledgers, logs — verifies plumbing, and never scripts a teaching move.

**Law:** [`PEDAGOGY.md`](PEDAGOGY.md) — how to teach (theory of acquisition §0 + teaching
rules §2). [`ENGINEERING.md`](ENGINEERING.md) — everything else (axioms, honesty /
engineering / process laws, debt registry, enforcement map).
**System map:** [`docs/system-overview.md`](docs/system-overview.md).

## How it teaches

- **Character sheet** (`logs/character_sheet.json`) = domain model + learner model in one
  artifact: the targets the level covers (domain data in `domain/spanish_a1/`), the
  scope, and per-item learner evidence. The sheet never sequences — the model plans its
  own path through it.
- **Two-phase teacher context** (`tutor/session_plan.py`): PLAN turns (session open, or
  when the model emits `<replan/>`) get the full picture — the teaching rules + full
  sheet + history — and the model writes its own private `<plan>`; ROUND turns run
  small: its plan + full sheet + session facts + a recent history window.
- **Grades** come from the model via the `update_character_sheet` tool; code clamps and
  records them under the honesty laws (ENGINEERING §3 — introduction is never knowledge,
  the display invents nothing).
- **Output gate** is plumbing only: `gate:truncated` + `gate:sheet_leak`. Teaching-quality
  opinions live in `evals/student_checks.py`, never in the runtime.
- **No-hide:** failures are visible (`[no-hide]` on stderr + typed internal_error
  events), never swallowed; `STRICT_ERRORS=1` re-raises.
- **Evals are the promotion bar** (ENGINEERING §4.3): behavior changes prove themselves
  on AI-student transcripts (`evals/run_student_smoke.py`, `evals/run_conv_smoke.py`,
  checks in `evals/student_checks.py` + blind rubric) — doc review never equals
  validation.

## Run it (web: chat + mic + spoken replies)

```sh
pip install -e ".[web]"
# set GEMINI_API_KEY (and/or GROK_API_KEY / ANTHROPIC_API_KEY); TUTOR_MODEL=gemini-3.6-flash
python -m tutor.web_app
# open http://127.0.0.1:8765
```

Type or use the mic (browser / Chirp / Gemini STT); replies speak via Gemini neural TTS
with browser fallback. Audio notes: `docs/web-and-audio.md`.

## Directory map

```
PEDAGOGY.md                  # teaching law (the model receives the rules on plan turns)
ENGINEERING.md               # engineering / honesty / process law
prompts/                     # exactly 3: conversational_tutor, tutor_persona, ai_student
domain/spanish_a1/           # domain data: association_table.json (target inventory),
                             #   asset_sidecar.json, migration_deprecations.json
tutor/web_app.py             # FastAPI UI + session cookies
tutor/conv_session.py        # session engine
tutor/turn_pipeline.py       # staged turn: context → model → gate → record → log
tutor/session_plan.py        # two-phase plan/round teacher context
tutor/character_sheet.py     # the sheet: domain + learner model, honesty clamps
tutor/output_gate.py         # plumbing gate (truncated, sheet_leak) + exposure bookkeeping
evals/                       # promotion bar: AI-student smoke, transcript checks, blind rubric
docs/system-overview.md      # canonical product / architecture map
```

Artifacts on disk (`logs/`): `character_sheet.json` (durable Spanish ability),
`sessions/<YYYY-MM-DD>/<id>.{jsonl,md,requests.jsonl}` (session + model-traffic logs —
created only once a session gets a learner turn; open-only page loads write nothing),
`costs.jsonl`, `progress.jsonl`, `sheet_grades.jsonl`. Personal-data capture is disabled
by construction (2026-07-28) — the sheet is Spanish ability only.
