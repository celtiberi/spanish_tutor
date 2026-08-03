# ml_teacher — Claude project notes

## THE LAW: PEDAGOGY.md + ENGINEERING.md (read both first)
Split 2026-08-03 (USER: "Pedagogy is how to teach. That is a coding decision"): `PEDAGOGY.md` holds ONLY teaching knowledge — theory of acquisition (§0) + teaching principles (§2). `ENGINEERING.md` holds the architecture axioms, honesty/engineering/process laws, debt registry, and enforcement map (§1, §3–§9, historical numbering kept so old "PEDAGOGY §N" citations resolve there). Every session and every agent contract starts there. If anything here, in memory, in prompts, or in code comments conflicts with the law files, the law files win — PEDAGOGY.md on teaching, ENGINEERING.md on everything else. A review that changes teacher behavior is not closed until its law paragraph lands in the right law file (LAW-PROMOTION GATE, ENGINEERING §7.2). Never duplicate law text into this file — point at it.

## Dual-AI review with Grok
This machine has the **grok-collab skill** (`~/.claude/skills/grok-collab/` — SKILL.md there has the full usage + collaboration discipline). Use Grok as the independent second author for: teaching-policy reviews, blind grading of tutor transcripts (use `blind-score` — it suppresses project context by design), domain-data fact-checks (`domain/spanish_a1/`), and countersigns on plan/design changes. This project's standing briefing for Grok is `GROK.md` at the repo root (auto-loaded by the skill). Keep review rounds auditable: append full debate under `docs/archive/reviews/`, keep hot-path outcome stubs at `docs/reviews-*.md` (catalog: `docs/reviews-index.md`). Pattern: propose → countersign → adjudicate with reasons → converge (2–4 rounds).

## No silent teacher-context truncation
PLAN turns send the AI teacher the **full** sheet (domain model + learner state — the prose course pack was DELETED 2026-08-03; sheet is never called a curriculum) / pedagogy / chat history; plan-mode ROUND turns run on the model's own plan + full sheet + a versioned 12-message window (ENGINEERING.md §3.3 amendment 2026-08-03 — the one sanctioned, `truncation-ok`-annotated window). Do **not** reintroduce `[:N]` slices or `history[-N:]` drops (literal or named-constant) on the teacher path for latency. Policy + commit gate: `docs/teacher-context-no-truncate.md`, `scripts/check_teacher_truncation.py`, `.githooks/pre-commit`. Before commit: `python scripts/check_teacher_truncation.py`. Install hook: `git config core.hooksPath .githooks`.

## System map
Canonical product/architecture/pedagogy overview: `docs/system-overview.md`.
Earned agent-engineering practices (ours + elfric survey, incident-backed):
`docs/ai-agent-best-practices.md`.

## Cross-project: the stocks repo's method
`docs/from-the-stocks-repo-2026-07-28.md` — a note from the sibling project's Claude
(`/Users/patrickcremin/repo/stocks`): what to study there (canonical models with
challenge lanes, blind-arm/reconcile backtests, lints-as-law, watchdog, agent
supervisor) and which patterns map to this project's objects. Pointer only; this
project's own law files (PEDAGOGY.md + ENGINEERING.md) remain the only law here.

`docs/from-the-stocks-repo-2026-07-30.md` — return letter answering your 2026-07-30
one: the watchdog + agent-supervisor patterns you asked for, the shadow-desk
convergence with your item 3 (§2p — adversarial counterpart as a mirrored desk with
call-vs-call arms), a new exportable law ("pinned-source authority covers stated
figures, not derived superlatives"), receipts for what your letter changed there, and
a P.S. proposing a standing cross-project exchange folder (user-initiated) for your
side to ratify or decline under your own law.
