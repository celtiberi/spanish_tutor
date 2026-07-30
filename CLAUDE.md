# ml_teacher — Claude project notes

## THE LAW: PEDAGOGY.md (read it first)
`PEDAGOGY.md` at the repo root is the ONLY home of law text: the theory of acquisition (§0), the architecture axioms, the teaching/honesty/engineering/process laws, the debt registry, and the enforcement map. Every session and every agent contract starts there. If anything here, in memory, in prompts, or in code comments conflicts with PEDAGOGY.md, PEDAGOGY.md wins. A review that changes teacher behavior is not closed until its law paragraph lands there (LAW-PROMOTION GATE, §7.2). Never duplicate law text into this file — point at it.

## Dual-AI review with Grok
This machine has the **grok-collab skill** (`~/.claude/skills/grok-collab/` — SKILL.md there has the full usage + collaboration discipline). Use Grok as the independent second author for: teaching-policy reviews, blind grading of tutor transcripts (use `blind-score` — it suppresses project context by design), course-pack fact-checks, and countersigns on plan/design changes. This project's standing briefing for Grok is `GROK.md` at the repo root (auto-loaded by the skill). Keep review rounds appended to files under `docs/` so the debate trail stays auditable — the pattern that works: propose → countersign → adjudicate with reasons → converge (2–4 rounds).

## No silent teacher-context truncation
Testing mode sends the AI teacher **full** sheet / pack / stance / chat history. Do **not** reintroduce `[:N]` slices or `history[-N:]` drops on the teacher path for latency. Policy + commit gate: `docs/teacher-context-no-truncate.md`, `scripts/check_teacher_truncation.py`, `.githooks/pre-commit`. Before commit: `python scripts/check_teacher_truncation.py`. Install hook: `git config core.hooksPath .githooks`.

## System map
Canonical product/architecture/pedagogy overview: `docs/system-overview.md`.
Earned agent-engineering practices (ours + elfric survey, incident-backed):
`docs/ai-agent-best-practices.md`.

## Cross-project: the stocks repo's method
`docs/from-the-stocks-repo-2026-07-28.md` — a note from the sibling project's Claude
(`/Users/patrickcremin/repo/stocks`): what to study there (canonical models with
challenge lanes, blind-arm/reconcile backtests, lints-as-law, watchdog, agent
supervisor) and which patterns map to this project's objects. Pointer only; PEDAGOGY.md
remains the sole law here.
