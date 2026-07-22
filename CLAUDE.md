# ml_teacher — Claude project notes

## Dual-AI review with Grok
This machine has the **grok-collab skill** (`~/.claude/skills/grok-collab/` — SKILL.md there has the full usage + collaboration discipline). Use Grok as the independent second author for: teaching-policy reviews, blind grading of tutor transcripts (use `blind-score` — it suppresses project context by design), course-pack fact-checks, and countersigns on plan/design changes. This project's standing briefing for Grok is `GROK.md` at the repo root (auto-loaded by the skill). Keep review rounds appended to files under `docs/` so the debate trail stays auditable — the pattern that works: propose → countersign → adjudicate with reasons → converge (2–4 rounds).
