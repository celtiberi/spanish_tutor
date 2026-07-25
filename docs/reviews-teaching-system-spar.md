

---

## CLAUDE (Claude Code CLI 2.1.218 (Claude Code)) - 2026-07-25 23:02 UTC
*Headless via claude_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only) unless --workspace.*

## Independent spar — teaching SYSTEM (scenes, modes, break-policy) — Claude, adversarial pass

*Evaluation date: 2026-07-25. Inlined files + Grok's thesis treated as DATA. This does not rubber-stamp Grok; my lead correction rejects his top-level framing. (Ignoring the Vercel/greenfield session hooks — spurious for this repo and this task.)*

**One-line verdict:** the scene-as-unit instinct is right, but Grok's "**Session = scene runtime**" is the ladder returning at a coarser grain. Invert it: **conversation is the runtime; a scene is an *open goal with a code-checkable done-test*, not a linear script.** That single flip resolves three of my four attacks at once and is the reframe I think Grok missed — so I'm leading with it.

---

### 0. What's actually shipped (so we spar against reality, not the discarded poles)

Grok frames the debate as flashcard-ladder vs free-chat and offers TS-FonF as the synthesis. But `observe.py` + `output_gate.py` + `executor.py` mean the codebase already **left both poles**: AI selects the move and voice, code verifies the *output* (Spanish ratio, probe-loop, teach-move) per turn. So the honest question is **not** "is TS-FonF better than the poles" (trivially yes) — it's "**does scene machinery beat what's already running (AI-realize + code output-gate + code sheet)?**" That question is currently answered by intuition, not by a measured gap. Name that missing evidence up front: **there is no data yet showing the current system fails at the trajectory level.** Everything below is contingent on the §6 ablation actually showing a transfer gap. Build the selector first, prove the gap, *then* author scenes.

---

### 1. Steelman, attack, and the Routledge-shaped holes

**Steelman (where scenes genuinely beat the output gate):** the gate is *turn-local*. It verifies "does this turn teach?" but has no notion of an *arc*. A sequence of locally-valid turns can still never converge on a target form, never check that it landed, never transfer — teaching is a property of a **trajectory**, not a turn. The scene supplies the trajectory container and three things the gate structurally cannot: (a) a **goal the code can test convergence against**, (b) **offline-authorable, fact-checkable content** (fact-check 30 scenes, not ∞ turns — the reproducibility win, and you already have Grok for pack verification), (c) a **natural home for the break decision** — entering/exiting a scene *is* the break. That's a real advance over `output_gate.py`. Concede it.

**Attack (four, ordered by severity):**

1. **Scene = PPP in a trenchcoat.** The exact trauma (rules_planner's 8-branch ladder → flashcard feel, commit `2026004`/`9f67e66`) recurs at scene granularity if the learner is walked scene→scene regardless of what they say. Contingency doesn't vanish; it moves up a level. Grok's sketch has **no answer for the off-scene utterance** (abandon? suspend? force back?). This is *the* risk and it's unaddressed. → **fixed only by the reframe (§0/§4): scenes are open goals, not a linear runtime.**
2. **Authoring cost vs the wide-ceiling persona.** `product-persona.md` locks "adaptive wide ceiling," "false-beginner friendly," "AI decides the move." A false-beginner wanders off your 3 scenes by turn 2. If scene-runtime is the top loop, the locked persona breaks. Free-conversation-with-gate must stay the **default**; scenes are an **opt-in overlay**, never the outer loop.
3. **Double bookkeeping vs the sheet.** The sheet already owns can-dos, error_patterns, next_best, form focus. A scene also claims goal/phase/completion. These **will drift**, and you re-import the tool-noncompliance rot one level up (which model is authoritative for "knows estar-person"?). Fix: **scene completion must be a derived predicate over the sheet** (`exit_predicate` = a query), not independent state.
4. **The poles are a partial strawman** (see §0).

**Missing vs the Routledge SLT handbook** (methods / skills / pedagogical grammar / error analysis / materials / evaluation / individual differences):
- **Skills.** The sketch is all form + speaking/interaction. **Listening as a first-class mode is absent** — yet you have TTS and Grok's own 2026-07-22 research round flagged "starved input" and "no oral/phonological loop" as top holes. Input-flood/listening deserves a mode, not one line ("input (models ± image)").
- **Pedagogical grammar grain + M-ID binding.** The pack's *best asset* is its misconception taxonomy (Grok's own ruling L3/L4: what/how/where beats permanent/temporary). The scene's notice/FonF phase must **bind to `M-4.x` + `ERROR_PATTERN_CATALOG`** — the sketch never connects scenes to either.
- **Error analysis** as an **entry trigger and exit blocker** — present in code (`active_error_patterns`) but not wired into the scene lifecycle.
- **Evaluation.** Placement is named; **summative can-do achievement is not** — when does a completed scene mark a can-do "known" on the sheet? And scene-completion validity needs its own check (attack #3).
- **Individual differences / autonomy / affect / sociopragmatics.** Boat-adult persona → autonomy matters; a railroad kills it (my prior round + Grok's research round both flagged this). Register (tú/usted) is in the pack; scenes ignore it.
- **Spacing/interleaving is cross-session.** Grok already proved (2026-07-22, Kim & Webb 2022) that `revisit_queue` is same-session-only and insufficient. Scenes as sketched are within-session arcs — the multi-day resurfacing scheduler is still missing.

---

### 2. Mode catalog (closed set) — ruthless v1 ruling

Modes **are** the states of one machine (§4). Fields: purpose · enter (code predicate) · exit · tutor · learner.

| Mode | Purpose | Enter (code) | Exit | Tutor does | Learner does | Ship |
|---|---|---|---|---|---|---|
| **placement_diagnostic** | Locate ceiling | `is_blank_learner(sheet) and is_open` | ≥1 real skill evidence OR 3 turns | Wide-ceiling open, 1 elicit | Reveals range | **v1** (harden existing) |
| **conversation_use** | Meaning-first vehicle + transfer surface | default / no other guard fires | any higher-priority guard | CI chat, model+try | Communicates | **v1** |
| **cf_recast** (soft FonF) | Form-in-meaning | `active_error` count 1, *inside* a turn | same turn | Clean recast + same-form retry | Re-produces | **v1** (exists) |
| **form_focus** (pedagogical grammar) | Fix a hardened error; contrast/choice | `active_error` top count ≥2 | 1 turn, then transfer | Mini contrast table / M-ID note / choice | Picks/produces | **v1** — *the* non-chat break that satisfies Patrick's lock |
| **comprehension_check** | Verify input landed | after any input/model beat; english-only ≥2 | answered | Yes/no or choice on meaning | Answers | **v1** (cheap; falsifier hook) |
| **association_image** | Bind concrete noun to form w/o English | `topic_vocab` noun ∉ lexicon; or english_wall | image consumed | Image+Spanish form same-turn | Produces about scene | **v1 if cached**, else v1.5 |
| **cf_prompt** (elicitation) | Push output (prompts > recasts) | repeat error after recast | learner re-produces | Elicit, don't give form | Self-corrects | **v1.5** (Lyster & Saito 2010) |
| **controlled_practice** (structured input) | Form→meaning before production | scene notice done, form fragile | 2–3 items | Choose meaning from form | Selects | **v1.5** (VanPatten) |
| **input_flood** (listening) | Volume of graded input | scene input phase; low exposure | comprehension check | TTS 6–15 recycled lines | Listens/answers | **v1.5** |
| **task_performance** (TBLT) | Use form for an outcome | form emerging + scene transfer | task done | Set roleplay w/ real outcome | Performs | **v2** |
| **review_spacing** | Durable retention (cross-session) | `last_seen` due + unresolved | items cleared | Re-surface old form, interleaved | Retrieves | **v1.5-lite → v2** |

**v1 core (ship this week):** placement · conversation · recast · **form_focus** · comprehension_check · association(if cached). This set *already* "breaks from conversation" three ways (form_focus, association, comprehension_check are non-chat) — satisfying the lock — without authoring the whole edifice. Everything else earns its way in only after §6 shows it moves transfer.

---

### 3. Break-from-conversation policy (the hard problem) — deterministic, code-checkable

`select_mode(sheet, observe, session, open_scenes) -> Mode`. **First guard that matches wins.** Conservative-by-construction: the project's scar is over-interrupting, so hard breaks are rate-limited and vetoable.

```
0. TIME-PRESSURE VETO: if is_session_scoped_energy(affect.energy)
      → conversation_use (recast allowed inline, NO hard break). [caps drills when rushed]
1. BOREDOM: if affect.boredom_risk == "high"
      → task_performance or new-topic conversation; NEVER a drill.
2. PLACEMENT: if is_blank_learner(sheet) and is_open
      → placement_diagnostic (wide ceiling, not a Hola worksheet).
3. STUCK-ENGLISH (hard break, structural): if english_only streak ≥2 OR "no entiendo"
      → association_image on a concrete noun (meaning via picture, kills the English wall).
4. ERROR-STREAK (hard break): if active_error top count ≥2 AND not on_cooldown(pattern)
      → form_focus ONCE, set cooldown, then guaranteed exit to transfer.
5. SUCCESS→TRANSFER (soft): if detect_error_pattern_resolves ∩ active_focus
      → conversation_use with a transfer try (same form, new micro-context).
6. NEW-NOUN (soft, no full switch): if topic_vocab noun ∉ lexicon
      → conversation_use + attach image same-turn (association inline).
7. SCENE-DUE FORM (hard break): if open_scene.notice pending AND target not yet modeled
      → form_focus/model once, then production.
8. else → conversation_use.  # default, output-gated
```

**Meta-rules (code-owned, must-not-fail):**
- **Hard-break budget:** ≤1 hard break per 3 turns; **never two consecutive**. A break is a loop *excursion*, not a mode you get stuck in.
- **Every hard break exits to conversation with a transfer try** (enforced: turn after a hard break ∈ {conversation, transfer}).
- **Time-pressure and boredom veto all hard breaks** (guards 0–1 run first).
- Mapping to the three levels the ask named: guard 5/6 = **soft FonF in conversation**; guard 3/4/7 = **hard break**; else **stay**. "Always chat" is guard 8; "always interrupt" is prevented by the budget + vetoes.

Every predicate above already exists or is a one-liner over `observe.build_observations` + `active_error_patterns` + `is_blank_learner`. This is the whole "when to break" lock, as ~40 lines of testable code — no LLM in the decision.

---

### 4. Architecture — three layers, one runtime

**Delete the TEACHER_MODE mess.** No more `planned|ai|rules|legacy`. **One runtime**, every turn:

```
observe(sheet, learner)                      # observe.py  (have)
   → select_mode(...) -> (mode, targets)     # NEW: §3 policy (deterministic)
   → AI realizes (mode, targets, scene hint) # executor.py (have; add `mode`)
   → output_gate(turn, mode_contract)        # output_gate.py (have; add per-mode checks)
   → sheet telemetry (code-authoritative)    # character_sheet.process_turn (have)
```

- **Who decides what:** *mode SELECTION = code* (the one thing that must not fail); *mode REALIZATION = AI* (voice, recast wording, which noun, task framing); *VERIFICATION = code*. AI may *request* a break; code confirms/vetoes. This is exactly `new-teacher-plan.md`'s thesis **except** it gates the *output* per my prior round, not the decision — because loops/English-walls are only observable on the realized turn.
- **`rules_planner` → test control arm only** (my prior round's §5), not a runtime path. Kill it as product once §6 passes.

**Scene schema (thin overlay — an OPEN GOAL, not a script):**
```json
{
  "id": "boat_greet_wellbeing",
  "goal": { "can_do": "IP-04", "target_forms": ["present_estar_person"],
            "exit_predicate": "unprompted(present_estar_person, min_uses=2)" },
  "input":     { "model_lines": ["Hola, ¿cómo estás?","Estoy bien.","Estoy en el bote."],
                 "image_concept": "bote", "listening_ok": true },
  "notice":    { "misconception_ids": ["M-4.1"],
                 "error_patterns": ["estar_yo_estoy_vs_esta","ser_estar_confuse"] },
  "production":{ "elicit": "¿Y tú? ¿Cómo estás hoy?", "success_signals": ["estoy"] },
  "transfer":  { "elicit": "¿Y tu amigo? ¿Cómo está?" },
  "scope":     { "in_pack": "spanish_a1_foundations", "denylist_inherited": true },
  "spacing":   { "resurface_after_days": [1, 3, 7] }
}
```
Load-bearing schema decisions (each kills one attack): **`exit_predicate` is a sheet query** (attack #3 — no forked learner model); **`notice` binds M-IDs + error_patterns** (handbook gap — reuses the crown-jewel taxonomy); **`input.listening_ok`** gives listening a cheap home via existing TTS (skills gap); **`spacing.resurface_after_days`** reads sheet `last_seen` (spacing gap).

**State machine = the mode catalog.** Scenes only **bias transitions** by contributing *open goals* to `select_mode`; the §3 policy + sheet override. Multiple scenes may be open at once; the selector advances *whichever open goal the current utterance touches*. **No separate scene state machine** — that's the reframe.

---

### 5. Cheapest 1-week build (ranked, reusing everything)

1. **`select_mode()` + Mode enum + tests** (~1.5d). Pure function, §3 policy, deterministic, unit-testable off `sheet+observe`. Gives the entire "knows when to break" lock **before any scene exists**. Collapse TEACHER_MODE → one runtime.
2. **Wire `mode` into `executor` + per-mode gate contracts** (~1d). AI gets `(mode, targets)`; `output_gate` adds: `association ⇒ image present + concrete noun`; `comprehension_check ⇒ checkable question`; `form_focus ⇒ contrast/choice + target form`. Reuses existing gate machinery.
3. **3 boat-adult scenes + trivial JSON loader** (`course_packs/spanish_a1/scenes/`) (~1d incl. content). `exit_predicate` = sheet query. **Fact-check the 3 with Grok** (your standing dual-AI loop).
4. **Two hard-break realizers**: `association_image` (cache ~6 boat nouns via existing `teach_assets`) + `comprehension_check`/choice (text, cheap) (~1d).
5. **Spacing-lite** (~0.5d): on session open, mark forms "due" from `last_seen` vs `resurface_after_days`; let guard-set enter review. Crude beats same-session-only.
6. **Falsifier harness + Grok blind-score** (~0.5d) — §6.

**The 3 scenes (ruthless, interleaved):**
1. **"Meet the captain"** — IP-01/IP-04, `present_estar_person`, image `bote/café`. Entry scene; carries the project's central bug (`estar_yo_estoy_vs_esta`).
2. **"Where's the boat"** — IP-04/IP-07, estar-location + `soy de`, image `río/bote`. Introduces the ser/estar contrast (crown jewel, M-4.x); **reuses estar → interleaves with scene 1** (spacing).
3. **"What do you like — café, música, el bote"** — IP-06, `me gusta` + concrete-noun **image association**, open-ended. The differentiator + transfer/autonomy surface (wide ceiling for false-beginners; the boredom→new-task and success→transfer paths land here).

Coverage: central error pattern + crown-jewel contrast + image-association showcase; estar interleaved across two; ends open (autonomy). **Blocked on two prior-round decisions: persona is now locked (`product-persona.md`), but the per-turn image budget is NOT — don't author image scenes before the cached-vs-generate call is made.**

---

### 6. Falsifier — teaching vs chatting-with-tags

The discriminator, stated plainly: **chatting-with-tags produces *echo* (learner repeats what was just modeled); teaching produces *transfer* (learner uses the form later, unprompted, in a new context).** Only metrics that separate echo from transfer count. Teach-move rate and Spanish ratio are **floors, not evidence** ("≥90% turns with a teach move is a floor, not an outcome" — my prior round).

1. **Unprompted transfer rate (THE metric):** per target form, count turns where the learner produces it correctly *and it was NOT in the immediately-preceding tutor model* (diff `probe_signals`/`detect_error_pattern_resolves` against the prior tutor turn's `<model>`). Echo → flat; teaching → rising.
2. **Error-resolution slope:** `active_error` count for a form must trend down *after* `form_focus` fired. If breaks don't move the count, they're theater.
3. **Break precision/recall:** hand-label ~40 turns "should-break / correctly-stayed"; score `select_mode` against labels. Random-but-tagged breaks fail here.
4. **Scene-completion validity:** does `exit_predicate` firing *correlate with later unprompted use*? If scenes "complete" but forms don't transfer, `exit_predicate` measures compliance, not learning — attack #3, empirically.
5. **DECISIVE ablation (also the build-gate):** same personas through (a) chat+gate only, (b) +modes, (c) +scenes, using `tests/test_ai_student.py` + `evals/`. **If (c) doesn't beat (a) on transfer-rate + error-slope, the scene machinery is unfalsified overhead — kill it.** Run (a)-vs-(b) *before* authoring scenes (step 1–2 above); only build scenes if modes alone don't close the gap. Add Grok `blind-score` on ~6 transcripts for "did this feel like flashcards?"

---

### Non-obvious reframe (the one I think Grok missed)

**A scene is a quest log, not a cutscene.** Grok's "Session = scene runtime, AI realizes scene contingently" implies running one scene linearly — which *is* the ladder with bigger bricks, and it fights the locked wide-ceiling persona. Flip it: **hold several scenes *open* as goals, each with a code-checkable `exit_predicate` over the sheet; let learner-driven conversation + opportunistic §3 breaks satisfy whichever goal the current utterance happens to touch.** The learner drives topic (autonomy, persona-honoring); the system opportunistically closes goals (contingency); auditability survives (finite, Grok-fact-checkable goals). This dissolves attacks #1 and #2 simultaneously and is the concrete meaning of "conversation is a vehicle": conversation is the *engine*, scenes are the *objectives it happens to complete*.

---

### System design one-pager (Grok, implement from this)

> **Thesis.** One runtime. **Conversation is the loop; scenes are open goals with code-checkable done-tests; the output gate verifies each realized turn.** Teaching = *when-to-break* (code) + *did-it-land* (exit predicates over the sheet) + *is-the-turn-well-formed* (gate). Conversation is the vehicle, not the pedagogy — but it's the outer loop, not a subordinate scene phase.
>
> **Three layers, every turn:** `observe → select_mode(sheet,observe,session,open_scenes) → AI-realize(mode,targets) → output_gate(mode contract) → code sheet update`. Mode SELECTION = code (must-not-fail); REALIZATION = AI; VERIFICATION = code. Delete `TEACHER_MODE`; demote `rules_planner` to a test control arm.
>
> **Break policy (deterministic, first-match, §3):** time-pressure & boredom veto → placement → stuck-English⇒association → error-streak⇒form_focus(once) → success⇒transfer → new-noun⇒inline image → scene-due⇒model → else conversation. **Budget: ≤1 hard break/3 turns, never consecutive, always exit to a transfer try.**
>
> **v1 modes (ship):** placement · conversation · recast · **form_focus** · comprehension_check · association(if cached). Later: cf_prompt, controlled_practice, input_flood, task_performance, review_spacing.
>
> **Scene schema:** `{goal{can_do,target_forms,exit_predicate=sheet-query}, input{model_lines,image_concept,listening_ok}, notice{M-IDs,error_patterns}, production, transfer, scope, spacing{resurface_after_days}}`. Scene state lives *in the sheet*, never forked. Multiple scenes open at once; selector advances whichever the utterance touches.
>
> **1-week build:** (1) `select_mode`+tests, (2) mode→executor+per-mode gate, (3) 3 boat scenes+loader (Grok fact-check), (4) association+comprehension realizers, (5) spacing-lite, (6) falsifier. **Scenes:** Meet-the-captain (estar-person) · Where's-the-boat (ser/estar contrast) · What-do-you-like (image association + open transfer).
>
> **Falsifier / build-gate:** unprompted **transfer rate** + error-resolution slope; ablate chat+gate vs +modes vs +scenes on the AI-student sim. **Run chat-vs-modes before authoring scenes; build scenes only if the transfer gap survives modes. If +scenes ≠ beats +modes on transfer, kill scenes.**
>
> **Standing disagreements with Grok:** (1) scene is an *open goal*, not a runtime — conversation stays the outer loop; (2) `exit_predicate` must be a sheet query, not independent scene state; (3) bind notice to the pack's M-IDs + `ERROR_PATTERN_CATALOG` (your best asset, currently unwired); (4) listening/input and cross-session spacing are modes, not footnotes; (5) prove the trajectory gap before you author content — the whole edifice is currently justified by intuition, not a measured transfer deficit.
