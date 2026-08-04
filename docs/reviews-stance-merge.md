# Outcome stub: single-stance merge + voice + games placement (2026-08-04)

Full debate: docs/archive/reviews/stance-merge-20260804.md

- USER regressions: persona flattened, morphology blank, games never
  fired. Root cause: the old inline AI_TUTOR_SYSTEM still shipped as a
  first full prompt (stale <continue>, "app carries morphology" line),
  with the real stance demoted to an appendix — two competing shape
  contracts. Deleted (§4.6); conversational_tutor.md is now the ONLY
  stance.
- Morphology record projection gained a known-tier fallback (panel
  never blank once evidence exists). Traffic log now records sent.tools
  (the games forensics were unanswerable without it).
- Games/Voice both got round-turn placement WITH behavioral teeth
  (Grok A1–A3, accepted verbatim): anti-scaffold floor, 4+ turn pacing
  gate + affect condition, teach-cycle tether on game turns, restored
  flashcard-ladder and bare-praise bans.
- Verdict: ACCEPT_WITH_AMENDS, enacted. OPEN pre-registered check
  before complaints (a)/(c) close: ≥6-turn session with persona
  markers per eligible turn + a justified game (or explicit
  zero-with-reason). Morphology complaint (b) closed.
