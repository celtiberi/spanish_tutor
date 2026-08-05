# Design: XP + levels — visible progression (converged plan, 2026-08-05)

USER request: "come up with a plan for experience points based on the
grades and character sheet… student needs to feel that they are
learning by seeing progression."

Status: **PLAN, converged with Grok in one round** (debate:
docs/archive/reviews/xp-progression-20260805.md). Not yet implemented.
This document is a USER-initiated REOPEN of the 2026-07-28 progression
non-goal (XP/points/levels were explicitly out of scope then); the
reopen conditions below are binding.

## The two truths (the core design)

- **Character sheet = ability.** Honest, evidence-graded, CAN GO DOWN.
- **XP = journey volume.** A derived, code-owned, recomputable weighted
  sum over already-evidence-backed ledger events (grade ledger +
  progress ledger). Monotone, because practice that happened happened.
  The model never writes XP; nothing pays without a ledger event.

Monotone XP is legal ONLY because the UI always co-displays ability
(dual-signal law below). XP alone is not the progression system.

## XP events and weights (the one table; code mirrors it exactly)

| Event (ledger source) | XP | Gate |
|---|---:|---|
| First correct production (up to emerging, grade ledger) | 10 | not introduction — §3.2 |
| emerging→fragile (grade ledger) | 15 | |
| fragile→known (grade ledger) | 25 | |
| Spaced retrieval success (progress ledger) | 25 | pays once per (item, interval-threshold crossed: ≥3d, ≥6d, …) |
| Durable — first reach of 14d interval | 40 | copy: "holding at the 2-week check" |
| Error pattern resolved | 30 | shipped gate: resolved_streak ≥3 AND count == 0 |
| Game completed ≥70% | 8 | ≤2 paying games/session, ≤3/day |
| Can-do unlocked (skill reaches known) | 50 | known only; emerging pays nothing |

**Deleted by review:** session/turn-count XP (seat-time Goodhart — the
"Session kept" milestone died in 2026-07-28 for the same reason).

## Anti-farm (binding)

1. Each (item, band-or-milestone) pays once per learner epoch; reset
   wipes XP with the epoch. Re-earn after a down-grade pays only the
   band re-crossed, not the path.
2. Echo-grade rows pay 0 (when the echo_grade eval flag lands).
3. No XP for introduction, exposure, login, session length, or turns.
4. Day cap **120 XP** (≈ one fully-rooted item + change). Pre-registered
   revisit after two weeks of live telemetry.

## Levels

Thresholds: Nivel 1 (0) → 2 (100) → 3 (250) → 4 (500) → 5 (900) →
~1.6× band growth after. Names use the GATED domain-echo rule:

- A level may carry a can-do family name (e.g. «Me llamo…») **iff**
  that family's skill is ≥ emerging on the sheet at unlock time
  (mastery-flavored names require known).
- Otherwise the level unlocks as plain «Nivel N». XP alone never
  grants a named level. Never mixed, never retro-renamed.

## UI (dual-signal law)

- **Header**: ability counts primary (durable-so-far · known ·
  emerging), level + XP bar to next level secondary. Order is
  load-bearing (informational competence feedback first; journey
  volume second — Deci et al. 1999).
- **Grade cards** annotate their XP ("+15 xp") — every point visibly
  glued to its evidence.
- **Level-up**: one toast + one chip in the grades rail. No confetti
  spam, no streak chrome, no leaderboards (standing bans).
- **Weekly recap** must carry down-state when present: "+80 xp · 2
  words need re-check" — never an XP-only recap over a falling sheet.

## Implementation shape (when built)

- `tutor/xp.py`: pure function (grade ledger rows, progress ledger
  rows, epoch) → {total, level, level_name, to_next, recent}. Derived
  and recomputable; no new stored state; per-uid on Fly for free.
- `/api/progress` grows an `xp` object; app.js renders header +
  annotations. Weights constant table mirrors THIS doc.
- Epoch pin: XP resets with learner epoch (post-reset identity), raw
  ledger lines stay on disk.

## Pre-registered checks before "done"

1. Dual-signal falsifier: if learners read rising XP as "I got better"
   after a documented ability drop (ignoring the ability half), the
   header drops XP or forces ability-first permanently.
2. Cap/weight revisit at two weeks of live telemetry: does anyone farm
   retrieval thresholds or first-production spray? Adjust from data.
3. The persona-gate students must show XP accrual matches their
   scripts: sam_stuck earns near-zero XP honestly; sofia earns fast.
