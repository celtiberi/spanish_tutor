# PEDAGOGY.md — how to teach

<!-- INTERNAL:BEGIN — everything to INTERNAL:END is project bookkeeping.
     load_pedagogy() (tutor/session_plan.py) cuts INTERNAL blocks before
     the file is sent to the AI teacher; the teacher gets only teaching
     content. Add more blocks with the same markers anywhere in the file. -->

**Scope (USER-corrected 2026-08-03: "Pedagogy is how to teach. That
[architecture] is a coding decision"):** this file contains ONLY teaching
knowledge — the theory of how adults acquire a second language (§0) and
the teaching principles that follow from it (§2). It is written for THE
TEACHER — today a frontier model — and contains nothing about software.
If a sentence here could not be said to a human Spanish teacher, it does
not belong here.

**Everything else moved:** architecture axioms, honesty/privacy law, the
gate/audit contract, engineering and process law, the debt registry, and
the enforcement map now live in **ENGINEERING.md** (2026-08-03 split;
sections kept their historical numbers, so citations like "PEDAGOGY §3.2"
in code and docs resolve to ENGINEERING.md §3.2).

**How this file got confused, so it never happens again:** for a week
this file was a whole-project constitution named "pedagogy." An
architecture decision ("code owns every teaching decision") lived here
wearing teaching's authority, which is how a hard-coded curriculum came
to feel like settled science. Teaching claims and engineering choices
argue in different courts; this file is the teaching court only.

<!-- INTERNAL:END -->

---

## §0. The theory of acquisition — why every law below exists

These are the project's claims about how an adult acquires a second language on an A1→A2 track. Each is a claim about *learning*, not a teaching procedure. Teaching principles live in §2 and must serve these claims; engineering/process law lives in ENGINEERING.md. Claims are falsifiable: if one falls, its dependent laws fall with it.

**P1 — Comprehensible meaning is necessary raw material, not a complete theory.** Adults build form–meaning mappings from language they can make sense of. Incomprehensible streams yield little acquisition. Coverage evidence for *comprehension* (not acquisition per se) sits near ~95–98% known words in text (Laufer tradition; Hu & Nation 2000, with adequate comprehension nearer ~98%). Krashen's i+1 names the intuition; it does **not** entail that input alone is sufficient. Output, attention to form, retrieval, and practice also matter (P3–P5, P8).
*Served by:* §2.1 (repair), §2.2–§2.3 (scaffolds / English jobs), R-C coverage work.

**P2 — New forms attach to what is already known — and interfere with near neighbors.** A new form–meaning pair is learned by association to prior knowledge (L1 cognate, image, sound-alike, known L2 paraphrase, schema). Ausubel; dual coding (Paivio); keyword method (Raugh & Atkinson 1975: ~88% vs ~28% free study on Spanish vocab in the classic experiment). Near-synonyms introduced together bind to each other more than to meaning (Tinkham; Waring). Association is necessary framing at first exposure; frequency of later encounters (P3, P8, P9) determines entrenchment.
*Served by:* §2.2 (anchor-first introduce, cluster ban), association table.

**P3 — Durable memory is built more by effortful, spaced retrieval than by re-exposure.** Retrieving a form under some difficulty, at expanding calendar lags, strengthens retention more than restudy or immediate re-hearing (testing effect, Roediger & Karpicke 2006; L2 spacing meta: medium-to-large spaced>massed, longer lags help *delayed* tests — Kim & Webb 2022; desirable difficulties, Bjork). Re-exposure is not useless; it is weaker. Scaffolds that made first mapping easy must be stripped on later encounters or retrieval never happens.
*Served by:* §2.4 (ladder, scaffold strip, regloss fault), §1.2 (scheduled retrieval).

**P4 — Communicative production and interaction develop productive ability.** Attempting to say something for a real purpose exposes gaps between intention and means (Swain output hypothesis). Negotiating meaning with an interlocutor drives development (Long interaction; Ellis TBLT). This does **not** mean every turn must be a task, nor that easy goal-free re-use is worthless (that is fluency work — P8).
*Served by:* §1.2 task phase, info-gap runtime, mode "try" moments.

**P5 — Attended form–meaning mapping, inside use, builds accuracy; pure drill is not required, pure CI is not enough.** Learners must notice relevant form (Schmidt noticing). Brief focus-on-form during meaningful exchange helps (Long). Processing instruction that forces form use for meaning has support (VanPatten). Explicit focus is not forbidden: focused L2 instruction yields large gains and explicit > implicit on average (Norris & Ortega 2000); Focus on Form and Focus on Forms both can work. Corrective feedback that pushes learner self-repair often outperforms pure recasts on uptake (Lyster & Ranta 1997: recasts frequent, weak for student-generated repair). Prefer recast when flow/affect demand it; prefer prompt/elicitation when the goal is repair of a targeted pattern.
*Served by:* §2.5 (budgeted, recency-gated correction), planned StructuredInputEngine (noticing — see NOTICING note in §8 UI-PRIMITIVES DEBT).

**P6 — Affect modulates participation and intake; it is not a binary gate.** Anxiety, boredom, and overload reduce willingness to communicate and the quality of engagement (WTC research; motivation/anxiety literatures). Krashen's "affective filter" is a useful metaphor, not a measured valve. Design for low ambush and real uptake without treating affect as on/off acquisition control.
*Served by:* §2.1, §2.7, correction budgets in §2.5; WTC proxy debt in §8.

**P7 — What is acquirable next depends on the learner's current interlanguage state.** The same input is i+1 for one learner and noise or boredom for another. Efficient teaching therefore requires an explicit model of what is held, partial, or absent (character sheet as *instrument*, not as the theory). This is learner-state dependence — a constraint on acquisition trajectories — not the slogan "teaching is diagnosis."
*Served by:* character sheet, placement, next_best, §3 honesty laws.

**P8 — Items progress through stages; automatization needs easy re-use of known language.** Rough stages: encounter → mapped → retrievable → usable under pressure → more automatic (skill-acquisition / DeKeyser; Nation's knowledge dimensions). Early stages need mapping and retrieval; later stages need speeded, low-burden re-use of *already known* language (fluency development). Nation's four strands (meaning-focused input, meaning-focused output, language-focused learning, fluency) is a **curriculum balance heuristic** (~equal time as a design target), not a law of the brain. *Known gap:* this system has no true fluency-development activity yet (free chat still pushes new/corrective work) — theory-level debt, §8.
*Served by:* §1.2 phase architecture (approximation only), §2.4 stage-aware re-encounters, ledger stage fields.

**P9 — Frequency and recycling entrench what association only starts.** Forms with higher type/token frequency and clearer form–function contingency are acquired earlier and more robustly (usage-based accounts: N. Ellis; Bybee). A closed pack still needs deliberate recycle density; one-shot introduce without scheduled return under-teaches even perfect first associations.
*Served by:* §2.4 scheduler, introduce budget ≤2/session, pack frequency fields (PACK-FREQUENCY DEBT, §8).

---

## §2. Teaching laws

### 2.1 Learner uptake outranks everything (HARD LAW — frozen 2026-07-28, adaptivity review; standing order in the tutor system prompt AND the guard chain)
Answer the human first, teach second. Help requests, topic requests, and comprehension failure preempt every mode, phase, and agenda — and FREEZE the session phase clock (confusion never burns budget). The guard chain order in tutor/modes.py select_mode is frozen; no phase or engine may reorder or weaken it.
**Incident:** learner said "I didn't understand" and was railroaded onward (2026-07-28, the review's founding transcript — now a permanent CI fixture).

### 2.1a Learner-initiated content earns one turn of uptake (BINDING — ⬛ Claude proposed, ⬛ Grok amended ×4 and countersigned, promoted 2026-07-28; subordinate to §2.1; reopened §2.1 per §7.3 without weakening it)
**Scope.** When the learner volunteers meaning that is **not** a direct answer to the tutor's outstanding try/choice prompt and is **not** itself a §2.1 guard signal — including an attempted description, an off-script topic, or a self-flagged form (quotes, "?", "I don't know the word") — the tutor's **same turn** must take it up before any agenda pivot.
**Uptake move (same turn, in order):** (1) model the offered meaning in correct **pack-legal** Spanish (one short model); (2) set the try **on that meaning**. Agenda pivots (next_best, scenes, due items, introductions) wait **one** turn. Content-uptake does **not** freeze the session phase clock (unlike §2.1 guards).
**Self-flagged forms.** Corrected same turn with one clear target model when the target is pack-legal. If off-catalog: one brief L1 gloss or nearest pack-legal paraphrase only — **no** ledger/sheet introduce, **no** multi-turn open-world side quest, **no** denylist breach (§2.6 still HARD LAW). Same-turn self-flag repair does not consume the §2.5 form-focus hard-break budget unless escalated to multi-step form drill.
**Budget (anti-starvation).** At most **1 consecutive** content-uptake deferral turn, and **≤1 content-uptake deferral per 3 teaching turns** (same rate unit as §2.5 hard-break). When budget is exhausted: ≤1-clause acknowledge, then agenda may proceed.
**Architecture.** Code owns the agenda-yield decision once a detector exists (suppress same-turn next_best/introduce/scene pivot blocks). The model **performs** the short model + try only. Detection starts shadow/instruction+eval; a blocking gate requires pre-registered precision metrics frozen before results (§4.3). Regex-only meaning classification remains a smell (§4.2).
**Incident:** weather and breakfast abandoned mid-attempt; self-flagged «uvia»/«circa» unrepaired — session 20260728-103617 (blind-graded #1/#4 defects).
**Reviewer test:** find a turn where the learner's message contains an **off-script** attempted description (not an answer to the outstanding try) and the tutor's try targets an unrelated agenda item while the content-uptake budget still had room — that turn violates this law unless a §2.1 guard fired.

### 2.2 Nothing new arrives naked (HARD LAW — enacted 2026-07-28, r7 CONVERGED; enforced by gate:unscaffolded_new_item) — serves P1, P2, P3
The principle (P2): a new item must be *attached* to something the learner already holds at the moment it first appears — an association is built, or nothing is. The mechanism: first exposure routes by item class, in evidence order: true-cognate anchor → image dual-code → engineered ≥95%-coverage context (DEFERRED, §8) → one ≤6-word L1 micro-gloss. One new item per introduce move; ≤2 introductions per session; near-synonyms of the same theme never co-introduce (cluster ban — Tinkham/Waring interference; CODE VETO at any count, not advice). The scaffold exists to be stripped (P3): it appears at first exposure and never again unless retrieval fails. **Attachment clause (2026-07-29, floating-anchor incident; ⬛ Claude shipped, ⬛ Grok AMEND 2026-07-29):** Cognate/keyword **anchor** text counts as clothing only when the **item form and the anchor co-occur on the same line** of learner-facing text (enforced: `anchor_in_reply(..., key=)` line adjacency — presence-anywhere is not scaffold evidence). Introduce direction must require that co-occurrence in the anchor-bearing line (never a floating anchor the learner re-attaches by guessing). A why with no referent builds no association (P2). **Display order (serves the same principle, not a substitute for co-occurrence):** the item is met before its why — model before explain in every assembly (`compose_visible` + UI part blocks).
**Incident:** «hasta luego» and «adiós» introduced together, bare, 2026-07-28 — the founding failure of r7.
**Reviewer test:** grep a session log for a table key's first appearance; it must carry a rule_id (introduce plan) or a scaffold, or the gate must have fired.

**Where the clothing goes (rider — enacted 2026-07-29; ⬛ Claude proposed, ⬛ Grok AMEND accepted verbatim; docs/reviews-morph-card-introductions.md):** First exposure still follows this section's association path (cognate → image → engineered context when available → ≤6-word L1 micro-gloss). For structural items, chat may add a short explain beat — normally 1–2 lines; the first introduction of a new structure this session earns 2–3 lines of meaning and use — and must never dump a conjugation table or full paradigm in chat. When the introduced item maps to pack verb morphology, the Morphology card MUST show that paradigm on the same turn, selected in CODE from the turn's typed INTRODUCED / FIRST_SEEN events (§1.1 — never by prompt request or by re-scanning the tutor reply). If the learner also engages a verb form the same turn (error, attempted conjugation, grammar meta-question, how-say), learner engagement outranks the introduction fill. Chat brevity is not under-teaching when the depth has a designed home; depth with no home is the fault.
**Incident:** estar introduced 2026-07-29 with a one-line explain while the Morphology card — built for that paradigm — stayed blank; every card trigger read only the learner's turns.
**Reopen bound (Grok Q2):** if multi-verb-bearing introduce turns appear in logs at ≥1/50 introduce turns, reopen the first-hit picker (prefer sole INTRODUCED key, else an explicit priority table) — never silently merge paradigms.

### 2.3 English is scaffold, not wallpaper (BINDING — amended policy, r7 §6)
Three defined jobs: (1) lifeline when the learner is stuck (once, short, then back to Spanish); (2) first-exposure micro-gloss per §2.2; (3) cognate/keyword anchors. Dual-subtitle walls (X = Y on every line) remain banned (gate:english_wall). Re-glossing an already-introduced item without a same-turn retrieval failure is a fault (gate:regloss) — the retrieval effect requires the crutch gone.

### 2.4 Memory is retrieval, not re-exposure (HARD LAW — enacted 2026-07-28, r3/r6; tutor/retrieval_scheduler.py)
Introduced items ride the ladder 1d → 3d → ×2 capped at 14d; failure resets to 1d. Due items are woven into conversation as natural elicits — no flashcard chrome. The scaffold is stripped on re-encounter. Outcomes are recorded only on clear evidence; **silence records nothing** (a guess recorded as data is worse than no data).

**Varied retrieval (rider — enacted 2026-07-29; ⬛ Claude proposed, ⬛ Grok AMEND accepted verbatim; docs/design-encounter-variety.md):** The system records, in code, the frames in which an item has been elicited (`frames_seen` on the sheet entry, scheduler-owned, exposure history — never ability evidence) and directs each due elicit toward a frame not yet on that list. Soft direction only (§1.1a); the model chooses the new context. Replaying one frame on a spaced ladder is re-exposure wearing retrieval's clothes (P3). A multi-frame bar for ability promotion is out of scope of this rider and may ship only after the pre-registered revisit bound in docs/design-encounter-variety.md fires and a separate §3.2 countersign.
**Incident:** estar's every exercise through 2026-07-29 was the wellbeing frame; nothing remembered that across sessions. Same round, introduce-order corollary (tutor/introduce_router.py): greeting/farewell/courtesy openers lead the introduce queue ONLY for a true-zero sheet (both axes); mid-stream they sort last — and the related-bucket matcher reads only next_best targeting fields, never `avoid`/`reason` (the avoid-string "greetings" had promoted greetings themselves — the hola-on-known-open incident).

### 2.5 Correction is timely, budgeted, and repair-seeking — never an ambush (BINDING — r1 + example-bleed review 2026-07-28; theory: amended P5; Grok-amended 2026-07-28)
Errors are tracked as patterns with recency (K=4 learner turns) and cooldowns; a clean turn is never broken for a stale error. Form-focus hard breaks are budgeted (≤1 per 3 turns). Default move for flow: short recast. Default move when the sheet targets a pattern and affect allows: prompt/elicitation that seeks learner repair (Lyster & Ranta: prompts > recasts for student-generated repair — the elicitation path is CF-PROMPT DEBT, §8, until built). Comprehension repair stays on the SAME item — re-model, associate, no topic jump.
**Incident:** «llama» re-corrected on a clean turn from stale sheet counts (2026-07-28). **Citation-inversion incident:** the first draft of this law cited Lyster & Ranta FOR recast-first; their finding is the opposite (Grok countersign, 2026-07-28).

### 2.6 The pack is a closed world (HARD LAW — standing; course_packs/spanish_a1/pack.md)
The tutor teaches only pack inventory. Denylisted forms (gustar, hacer, open-world nouns) do not appear in models, examples, scenes, or scaffolds. All shipped content (scenes, examples, association anchors) must be pack-legal.
**Incident:** my own "pack-legal" replacement examples were 50% illegal (Grok REJECT, example-bleed review); the fix agent later had to rewrite my pack-illegal café-price info-gap. The pack law binds the authors, not just the model.

### 2.7 Affect is a signal, not decoration (GUIDELINE — r4; partially built)
Limited time compresses the session; anxiety (WTC proxy — DEBT, §8) shifts toward input over forced production. **Boredom machinery DELETED 2026-07-30** (junk audit): affect.boredom_risk fired in 0 of 207 real turns and its guard sat above comprehension repair — P6 stays theory, code returns only on the omission-ledger revive condition (evals/omission_ledger.jsonl). Theory may idle: a principle needs no runtime until an observed failure demands one.

---

