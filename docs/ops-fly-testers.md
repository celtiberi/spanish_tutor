# Ops: letting testers try the Spanish teacher (Fly)

**URL for testers:** https://ml-teacher-tutor.fly.dev/?token=<ACCESS_TOKEN>
(one visit with the token sets a 30-day cookie; after that the bare URL
works in that browser). The token is the Fly secret APP_ACCESS_TOKEN —
rotate with `fly secrets set APP_ACCESS_TOKEN=... --app ml-teacher-tutor`.

**Per-tester isolation (MULTI_USER_SHEETS=1, set in fly.toml):** every
browser session gets its own character sheet (`/data/sheets/web-<sid>.json`)
and grade ledger (`/data/grades/web-<sid>.jsonl`); session logs carry the
sid in their filename (`…-conversational-web-<sid>.jsonl`). Without this
flag (local single-operator mode) everyone shares the one global sheet.

**What gets logged, per session, on the persistent volume:**
- `/data/sessions/<YYYY-MM-DD>/<id>.jsonl` — every turn's result (reply,
  notes, grades applied, events)
- `<id>.requests.jsonl` — the full model traffic: exactly what was SENT
  (system blocks, task, history) and RECEIVED (raw incl. the session
  plan, reply, tool calls, usage) per call
- `<id>.md` — readable transcript
- Logs are lazy: a session that never gets a real learner turn writes
  nothing (no probe litter).

**Looking for issues:**
```bash
scripts/pull_fly_logs.sh            # pulls /data → local dir
grep -rl "internal_error" <dir>/sessions/   # no-hide events
grep -rl "gate_fail" <dir>/sessions/        # plumbing faults
grep -rl "session_plan:missing" <dir>/sessions/  # plan-less plan turns
```
Then read the paired `.requests.jsonl` for any suspect turn — it holds
the complete context and raw model output for replay (the llevas-style
A/B replay works on these files directly).

**Known limits for testers:** the machine auto-stops when idle
(fly.toml) — first request after idle takes a few seconds; in-memory
chat continuity is lost on restart though sheets/logs persist; Chirp
WebSocket STT is untested on Fly (browser STT works). Live server
errors: `fly logs --app ml-teacher-tutor`.
