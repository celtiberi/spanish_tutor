

---

## CLAUDE (Claude Code CLI 2.1.218 (Claude Code)) - 2026-07-25 22:36 UTC
*Headless via claude_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only) unless --workspace.*

## Independent spar — ml_teacher AI-first tutor (Claude, adversarial pass)

Framing up front, because it drives everything below: this project does not have a *rules-vs-AI* problem. It has a **no-hard-gate-on-output** problem. Both the flashcard ladder and the "soften the prompt" edits are attempts to fix output quality in the wrong layer (decision-time rules, or prompt wording) instead of at output-time verification. Grok keeps flipping the default toward whichever failure Patrick complained about last, and each flip re-introduces the opposite failure because the missing piece is never added.

---

### 1. Push back on Grok's trajectory — three overcorrections, with what I'd do instead

**Overcorrection 1 — "don't monologue" became "hardcode the floor."** The diagnostic-monologue fix is `OPEN_HARNESS_DIAGNOSTIC` in `conv_session.py`: it prescribes the *exact* opening — 1–2 English sentences, `<model>` **Hola** + **Estoy bien**, `<try>` "say Hola." That is a flashcard. The fix conflated "don't wall a beginner with intermediate Spanish" with "start every unknown learner at the absolute floor." A blank sheet is not a beginner — it's an *unknown*, and a false-beginner (took HS Spanish, wiped the sheet) gets floored and taught nothing for several turns. `conversational_tutor.md` even admits this ("If they already produce multi-skill Spanish, skip the ladder") while the recipe forbids it. **Instead:** placement can't be done in one canned turn; make the open a genuinely wide prompt that a strong learner can fill with range and a weak learner can copy, then *calibrate to the response* (see §3-C).

**Overcorrection 2 — the ladder was relabeled, not removed.** Commit `c65ee03` "Make rules planner communicative" changed the `models`/`try_prompt` *wording* to sound chattier but left `rules_planner.plan_turn` as an 8-branch fixed-priority ladder (open → loop → error → ask_name → name→origin → origin→gusta → greet+estoy→name → greet→estoy → english → active-error → free_chat). The *control structure* — a fixed get-acquainted topic order (greet → wellbeing → name → origin → likes) — is untouched. That is precisely the "just soften the prompt to see if chat feels nicer" move that `pedagogy-contract.md` explicitly forbids, applied to the planner instead of the prompt. A tone edit masqueraded as an architecture fix. **Instead:** the only things that should *force* a move are (a) a live form error → recast, and (b) an explicit learner request. Everything else is free conversation constrained by the contract (model+try) and the don't-re-ask memory. That deletes ~7 of the 8 branches.

**Overcorrection 3 — "AI is the teacher" reverted the plan's own thesis.** `new-teacher-plan.md` (dated the same day, 2026-07-25) argues: *decide the move as data first (PlanCard), gate it, then generate voice; write the sheet with code, don't "hope the executor tools."* Grok's AI-first switch collapses planner+executor back into one call, **removes the gate on the decision**, and leaves the sheet dependent on `update_character_sheet` tool compliance. `observe.py` detects `estoy`/error hits but — as inlined — passes them to the LLM as advisory `hard_observations` and to session memory; I see no path where they deterministically write the sheet (`_finish` applies only `tool_delta`). *Caveat to verify:* `process_turn` internals aren't inlined — if it already merges detector output into the sheet, this gap is smaller; but the docstrings ("hints… not a lesson script") and the plan's unbuilt **PR3** ("hard observer / reduce dependence on tool_update") say it doesn't. Net: AI-first ≈ the *original* prompt-only conversational tutor (the one that drifted to chat-buddy) plus a richer context payload and a post-hoc `model/try` check. They've come full circle. **Instead:** keep the LLM for voice+move, but re-add code authority on the two things it can't self-guarantee — the sheet, and the output gate (§3-A/B).

---

### 2. AI-first as default — steelman AND attack

**Steelman (where a frontier LLM genuinely beats a closed catalog):**
- **Contingent input.** CI/CLT only works if the input responds to the learner's *meaning* — Long's interaction/negotiation. A catalog produces input that's comprehensible but not contingent; "Me gusta la música pero odio la gramática" walks the learner to the next rung regardless. The LLM answers what was actually said. This is the core pedagogical argument and it's real.
- **Recast quality & error coverage.** A good recast needs the specific error in context; the catalog only covers the ~5 hand-authored patterns in `ERROR_PATTERN_CATALOG`. The LLM covers the open set.
- **Coverage economics.** The ladder is ~250 lines to cover 6 topics *badly*. Authoring a full A1 move catalog is infeasible for a one-dev research project; the prompt is the only way to get breadth. This is decisive for this team.

**Attack (the four failure modes named — with which are actually enforced):**
- **Loops:** the catalog *structurally* can't loop (shown/asked gate branches). AI-first prevents loops only via advisory `session_facts.topics_tutor_already_asked` — a distracted model still re-asks. Structural guarantee traded for a hint.
- **English walls:** the stated #1 failure has **zero enforcement.** The contract checks `model/try` presence, not Spanish ratio. `observe.py` computes `es_hits`/`en_words` but only on *learner* text, never on the *tutor* turn, never as a gate. Frontier models over-explain in English exactly when the learner is confused — the moment it matters most.
- **Fake intermediate chat on blank sheet:** the default open path (`_execute_ai_tutor`, `is_open=True`) **bypasses `OPEN_HARNESS_DIAGNOSTIC` entirely** — it passes `blank_sheet=True` as a soft fact plus "place them gently." The one hard guard against the *original* monologue bug is gone from the default. That bug can recur, and there's no test asserting it can't.
- **Tool noncompliance:** AI-first leans *harder* on `update_character_sheet` (no rules phase computing state), so the student model rots silently — and since stale `next_best`/`error_patterns` feed back into context, the rot compounds turn over turn.

**Honest verdict:** AI-first is *right* for move-selection and voice, and *wrong* to also hand the LLM (a) blank-sheet placement with no floor, (b) sheet maintenance with no code writer, (c) English-ratio discipline with no gate. The overcorrection isn't "use the LLM" — it's "use the LLM for the three things code was supposed to guarantee."

---

### 3. Creative alternatives (specific to these files)

**A. Generate-then-verify (gate the *output*, not the decision).** Invert the plan's pipeline. Let the frontier LLM freely produce the turn *plus* a small self-report JSON (`{move, target_form, models[], try, reused_probe?}`). Then a **cheap code+tiny-model verifier** checks the *actual* turn against hard rules that are code-computable: Spanish ratio (reuse `observe.py`'s `es_hits/en_words` — pointed at tutor output this time), re-asked-probe detection (reuse session memory), model+try (the contract). On violation → **one** bounded re-ask with the specific fault ("you re-asked their name; advance"). This is cheaper than a separate planner and catches the two failures AI-first can't self-enforce. Non-obvious reframe: *the plan gated the decision; you should gate the output, because that's where the failures are observable and code-checkable.*

**B. Deterministic sheet, generative voice (the skipped PR3).** Stop treating the sheet as something the teacher *writes*; treat it as **telemetry the code computes from the transcript.** Wire `probe_signals` + `detect_error_pattern_hits` to deterministically bump evidence/confidence/error counts every turn; demote `update_character_sheet` to affect-only soft notes. Duolingo doesn't ask its content model to update ability — the IRT code does. Decouples "did the LLM remember to log" from "do we know the learner." Combine with A.

**C. Placement-as-adaptive-mini-dialogue.** For blank sheets, neither a canned floor nor "place gently" vibes. Run an explicit 2–3 turn probe with a *widening ceiling*: turn 1 = open prompt admitting any level ("cuéntame algo de ti — Spanish or English, whatever you can"); code reads response richness (`multi_skill`, `spanish_ok` signals already exist) and picks the turn-2 ceiling. False beginner who dumps a paragraph gets bumped up immediately; true zero gets the floor. Hand off to the conversational path once skill-conf crosses a threshold or after 3 turns. Fixes overcorrection-1 *without* the canned open.

**D. Dual-coding-first for concrete nouns (pull PR5 forward).** For `café / bote / río / comida` (all in the pack), build the turn *around* an image + the Spanish form; the `try` is producing language about the depicted scene. This is the one modality that *structurally* suppresses the English wall — meaning is carried by the picture, so the model has less pull to translate. Images are currently timid (blank-open "wave" + post-hoc only). Reframe: images aren't PR5 garnish, they're the **cheapest structural fix for the #1 failure mode**, and the scaffolding (`teach_assets`, `image_concept`) already exists.

*(Bonus E — combiner:* ~30 human-authored, Grok-fact-checked A1 **scene cards** (target forms, image, model lines, expected-answer patterns, common errors) computed *offline*; the LLM *realizes* the current scene contingently online while code tracks which forms landed. Gets auditability (fact-check 30 cards, not infinite turns — and you already have Grok for pack verification) + contingency + cacheable images. Best fit for a *reproducible* research project.)

My pick: **A + B + C now**, D/E as the product differentiator once budget/persona are decided.

---

### 4. Decisions the AIs keep making implicitly via flag-defaults — surface them

1. **True beginner vs adult false-beginner.** The entire flashcard-vs-chat oscillation is downstream of this one unmade decision. Pack is greetings-first A1; the "adult / boat life / café" voice is intermediate-casual. If the target is true zeros, the floor/ladder is *correct* and "flashcard feel" is a feature. If it's adults refreshing, the ladder is wrong and the diagnostic floor actively mis-serves them. **My read:** the boat/café/adult framing + the anti-flashcard aversion imply the real target is false-beginners — in which case *lean chat, and the hard floor is wrong for them.* Decide this and half the architecture argument dissolves.
2. **Same-turn image latency budget.** Dual-coding needs the image *with* the form. Generate-on-demand = contingent but +2–4s and $/turn; pre-cached allowlist = fast/bounded but less contingent. For A1 the concept set is ~30 nouns → I'd **cache**. But that's a decision the "images later" punt dodges.
3. **Per-turn cost/latency budget.** AI-first = 1 frontier call; generate-verify = 1 frontier + 1 cheap; planner/executor = 2 frontier. Set an explicit ceiling (e.g. **< $0.02 and < 2s/turn**) and several architecture choices collapse immediately.
4. **Placement tool vs practice tool.** "Placement in turn 1 then seamless chat" is *why* the open turn is contorted. Decide: is an explicit placement phase (first 3 turns) *allowed* to feel like assessment? If yes → C is clean. If no → you're stuck trusting vibes.
5. **Success metric.** There is none that measures *learning* — "≥90% turns with a teach move" is a floor, not an outcome. Adopt a code-detectable north star: **learner produces a target form unprompted in a later turn** (transfer), measurable by diffing `probe_signals` across turns. Without this, every architecture claim is unfalsifiable.

---

### 5. Cheapest falsifier this week

**A/B sim on the two discriminating failures (loops, English walls) + placement mismatch**, using the existing AI-student harness (`tests/test_ai_student.py`, `evals/`). No new infra.

- **Arms:** `TEACHER_MODE=planned` (AI-first) vs `TEACHER_MODE=rules` (ladder), as control.
- **Personas (×3):** (a) true zero-beginner; (b) false-beginner who dumps intermediate Spanish on turn 1; (c) a "no entiendo" learner that stress-tests English walls.
- **N ≈ 20 sessions/arm × 8 turns** → ~40 sessions, one afternoon.
- **Metrics, all code-computable from logs:** loop rate (re-asked answered probe, via memory diff); tutor English ratio (`observe.py` `es_hits/en_words` on *tutor* output); placement lag for persona-b (turns before models exceed Hola/Estoy); teach-move rate (`pedagogy:ok`, already logged). Optional: hand ~6 transcripts to Grok `blind-score` for "did this feel like flashcards?"

**What falsifies what:** if AI-first shows *lower* loop rate AND *lower* English ratio AND faster placement than the ladder → ship AI-first, don't bring structure back. If AI-first regresses on loops or English (likely on persona-c) → you need the **verifier gate (A)**, *not* the full ladder. The experiment's real payoff is that it discriminates "need a thin output gate" from "need the whole ladder back" — different amounts of structure — and it reuses the exact detectors that should *become* the gate.

---

### If I were shipping this weekend (ranked)

1. **Add a code output-gate (A) on the two real failures.** Spanish-ratio (reuse `observe.py`) + loop detection (reuse memory) on the *actual* tutor turn; one bounded re-ask on violation. Small; kills the two failures AI-first can't self-enforce. *(~½ day)*
2. **Make the sheet code-authoritative (B / the skipped PR3).** Detectors write evidence/error counts deterministically; demote `update_character_sheet` to affect-only. Stops silent student-model rot. *(~½ day)*
3. **Fix the blank-open regression.** The default AI-first open bypasses `OPEN_HARNESS_DIAGNOSTIC`. At minimum restore a hard floor for `is_open+blank` + a test that asserts it; better, ship C-lite (read turn-1 richness, branch ceiling). *(~½ day)*
4. **Run the §5 falsifier before deleting `rules_planner`.** Keep `TEACHER_MODE=rules` as the *control arm*, not legacy cruft, until the sim shows AI-first+gate beats it. *(~½ day)*
5. **Decide persona (Q4-1) and per-turn budget (Q4-3).** These unblock images and stop the oscillation. *(a conversation)*
6. **Only then** pull dual-coding forward (D), cached allowlist, if budget/persona allow.

This deliberately does **not** countersign "AI is the teacher." AI is the *voice and move*; **code is the gate, the sheet, and the placement floor.** That's closer to `new-teacher-plan.md`'s own thesis than either the ladder or today's AI-first-with-soft-facts — and I'll disagree with the plan too: it wanted to gate the *decision*; the evidence says gate the *output*, because that's the only layer where loops and English walls are observable and code-checkable.
