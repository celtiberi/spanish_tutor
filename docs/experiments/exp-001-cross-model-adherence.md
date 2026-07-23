# EXP-001 — Cross-model teaching-policy adherence (claude-opus-4-8 vs grok-4-fast)

**Date:** 2026-07-22/23
**Design:** identical teaching policy (v0.6), identical course pack (v0.6, mode `spec`), identical frozen behavioral gate (13 pre-registered trajectories, `evals/trajectories.py`), mechanical checks in code + pedagogical criteria graded by an independent blind referee (Grok CLI). Not pre-registered as a cross-model comparison — the model switch was a cost decision that produced a natural experiment; treat effect sizes as indicative.

## Results

| Metric | claude-opus-4-8 | grok-4-fast |
|---|---|---|
| Mechanical checks (code-asserted) | 12/12 (after 2 harness fixes) | **13/13 first run** |
| Pedagogical judge criteria (frozen, blind referee) | 5/12 first run → **12/12** after 3 prompt-fix cycles | **6/13 (46.2%)** first run — *with all Opus-derived fixes already in the prompt* |
| Transcript verbosity | baseline | ~2× terser — referee ruling: "under-teaching... the middle of the move sequence is missing," not economy |

## Key asymmetry

The models fail differently. Opus 4.8's initial failures were largely *harness and spec* defects (state-block omission, criterion misalignment) plus targeted behavior gaps that responded to prompt engineering (recency injection worked 3-of-4 times). grok-4-fast's failures are **core pedagogical omissions that the same prompts do not prevent**, ranked by the referee:

1. **Answer-key dump on first pressure** (t04) — the canonical over-help failure the project targets; "cheaper-model helpfulness default looks active."
2. Register remediation without re-production; secondary errors not parked (t01, t13).
3. **Spaced-review ladder semantics wrong** (t03): fail path produced `successes=1, due=+4d` instead of `0, next-day` — while passing every mechanical shape check.
4. Wrong error prioritized on multi-error utterances (t10).
5–8. Roleplay purity, Spanish-echo, probe-offering under lobby, off-script freeze.

**What held on grok-4-fast:** input-first, injection/marker resistance, skip-ahead probes, hint ladder in drill mode, what/how/where framing, spoofed-state rejection.

## Interpretation

1. **Mechanical compliance ≠ pedagogy.** 7 trajectories judge-fail while code-passing. Any evaluation of teaching models that relies on structural checks alone will systematically overstate quality.
2. **Prompted pedagogy does not transfer down-market.** A prompt stack iterated to 12/12 on one model yields 46% on another. Teaching behavior currently lives partly in the *model*, not the prompt — which is the project's thesis: pedagogy must be trained, and this table is its first quantified evidence (plus the Opus-side prompting-ceiling finding on roleplay purity, `docs/reviews-v06-policy.md`).
3. **The over-help literature reproduced on demand:** the plan's §2.3 claim that off-the-shelf LLMs "systematically over-help" appeared verbatim as grok-4-fast's #1 failure.

## Operational decisions

- grok-4-fast = default for **mechanical/harness regression** (cheap, and its 13/13 makes it a fine plumbing canary).
- Pedagogical judge runs = deliberate, per-model, always model-tagged (results now record `model`).
- These transcripts are Phase 4 preference-pair source material (over-help vs withhold; dump vs hint).

**Trails:** `docs/reviews-behavioral-gate.md` (Opus rounds 1–5), `docs/reviews-v06-policy.md` (audit cycles), `docs/reviews-grok-baseline.md` (this baseline).
