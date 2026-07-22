# ml_teacher — pedagogy-first tutoring model

Research project: train/align a model that is an expert in **teaching**, with subject matter supplied by pluggable course packs. Full plan: `docs/research-and-plan.md` (review trail: `docs/review-research-and-plan.md`).

## Phase 2 vertical slice

A terminal tutor that teaches Spanish A1 from a structured course pack, grounded by a checked-in teaching policy.

```
prompts/teaching_policy.md     # the teaching brain: moves, reveal policy, state spec
course_packs/spanish_a1/       # structured corpus: units, misconception IDs, keyed practice
tutor/                         # CLI app: policy + pack -> claude-opus-4-8, cached prefix
```

### Run it

Requires `ANTHROPIC_API_KEY` in the environment (or an `ant auth login` profile).

```sh
pip install -e .
tutor                # or: python -m tutor.cli
tutor --pack course_packs/<other_pack>
```

Session logs land in `logs/sessions/*.jsonl` (turns, state snapshots, token usage) for later dataset mining.

### Design notes

- **No vector RAG in v0** — the whole pack sits in the cached system prefix (an A1 pack is small; caching makes repeat turns ~90% cheaper). `tutor/corpus.py` is the seam where a retriever slots in when corpora outgrow context.
- **Student state** is maintained by the model itself in a `<session_state>` block at the end of each reply; the harness strips it, persists it, and re-injects it as a mid-conversation system message.
- **Misconception IDs** (`M-x.y`) in the pack double as gold labels for the diagnostic-accuracy rubric dimension.
