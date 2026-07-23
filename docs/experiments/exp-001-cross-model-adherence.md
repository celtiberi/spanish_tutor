# EXP-001 — Cross-model teaching-policy adherence (claude-opus-4-8 / grok-4-fast / gemini-3.6-flash)

**Date:** 2026-07-22/23
**Design:** identical teaching policy (v0.6), identical course pack (v0.6, mode `spec`), identical frozen behavioral gate (13 pre-registered trajectories, `evals/trajectories.py`), mechanical checks in code + pedagogical criteria graded by an independent blind referee (Grok CLI). Not pre-registered as a cross-model comparison — the model switches were cost decisions that produced a natural experiment; treat effect sizes as indicative. Single run per model per cell.

## Results

| Metric | claude-opus-4-8 | grok-4-fast | gemini-3.6-flash |
|---|---|---|---|
| Mechanical checks (code-asserted) | 12/12 (after 2 harness fixes) | **13/13 first run** | **13/13 first run** |
| Pedagogical judge criteria (frozen, blind referee) | 5/12 first run → **12/12** after 3 prompt-fix cycles | **6/13 (46.2%)** — *with all Opus-derived fixes in the prompt* | **8/13 (61.5%)** — same prompt |
| Over-help line (answer-key dump under pressure, t04) | held (after fixes) | **broken** — dumped key on first ask | **held** |
| Signature failure mode | roleplay-purity prompting ceiling | over-help / omitted middle moves | **over-refusal**: refused an in-scope generation request ("unit lock"), inverse schedule arithmetic, misconception-ID logging collapse |
| Transcript verbosity | baseline | ~2× terser ("under-teaching") | intermediate |

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

## Gemini addendum (2026-07-23)

gemini-3.6-flash lands between the peers (8/13) and **fails in the opposite direction from grok**: security/withholding behaviors hold (no key dump, lobby resistance, person-first correction), but it **over-refuses** — declining an on-demand in-scope dialogue the criteria require (the plan's §6 "over-alignment → unhelpful withholding" risk, observed live), assigns compound production by construction, under-updates the review schedule (due date stale rather than grok's over-advance), and stops logging misconception IDs. Of grok's 8 ranked gaps: 4 present, 3 held, 1 partial.

**Implication upgrade:** failure modes are model-idiosyncratic and *bidirectional* — one model over-helps, another over-withholds, under one identical prompt stack. Phase 4 preference data must therefore cover both directions (dump-vs-hint AND refuse-vs-generate), and no prompt iteration tuned on one model can be assumed to transfer.

## Operational decisions

- gemini-3.6-flash = **working default** (`TUTOR_MODEL` unset): best cheap-tier adherence, holds the over-help line, user's platform preference.
- grok-4-fast = alternate cheap canary for **mechanical/harness regression**.
- Pedagogical judge runs = deliberate, per-model, always model-tagged (results now record `model`).
- These transcripts are Phase 4 preference-pair source material (over-help vs withhold; dump vs hint).

**Trails:** `docs/reviews-behavioral-gate.md` (Opus rounds 1–5), `docs/reviews-v06-policy.md` (audit cycles), `docs/reviews-grok-baseline.md` (this baseline).
