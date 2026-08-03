# Architecture refactor (seams, events, item lifecycle)

**Status:** COMPACTED 2026-07-31 · full transcript (append-only debate) preserved at  
`docs/archive/reviews/reviews-architecture-refactor.md`

| | |
|--|--|
| **Date** | 2026-07-28+ |
| **Closure** | Multi-batch SHIPPED (phases 0–4+) |
| **Outcome** | Whole-system defects were seam defects. Phased refactor: characterization harness, typed turn events, SessionState, item status machine, turn pipeline contributor region, inventory-collapse (table fill before list flip). Turn-level FSM rejected (choreography risk). |
| **Law** | Preserves PEDAGOGY §1.1 / §1.1a / §4.1; no new law home |
| **Code / artifacts** | tutor/turn_events.py, turn_pipeline.py, session_state, characterization harness, progress_ledger epoch |

> PEDAGOGY §7.1: the debate transcript is never summarized away — it lives in the archive path above (and in git history).  
> New countersign rounds for this topic: append to the **archive** file, then refresh this stub's Outcome/Law rows.

