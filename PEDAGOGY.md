# PEDAGOGY.md — how to teach

<!-- INTERNAL:BEGIN — everything to INTERNAL:END is project bookkeeping.
     load_pedagogy() (tutor/session_plan.py) strips, before sending to
     the AI teacher: (1) INTERNAL blocks, (2) NOTES blocks (§0 theory &
     evidence — ours, not the teacher's), (3) every HTML comment. The
     teacher receives ONLY the rules. USER 2026-08-03: "one THEORY AND
     NOTES file and one HERE ARE THE RULES file… fixed with markers."

**Scope (USER-corrected 2026-08-03: "Pedagogy is how to teach. That
[architecture] is a coding decision"):** this file contains ONLY teaching
knowledge — the theory of how adults acquire a second language (§0) and
the teaching rules that follow from it (§2). It is written for THE
TEACHER — today a frontier model — and contains nothing about software.
If a sentence here could not be said to a human Spanish teacher, it does
not belong in the SENT portion; it belongs in a NOTES or INTERNAL block.

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

INTERNAL:END -->

<!-- NOTES:BEGIN — §0 is the project's theory & evidence record: the
     acquisition claims each rule serves, with citations. It is OUR
     justification file (reviews attack it; laws cite it). The teacher
     model is not sent a literature review. -->

## §0. The theory of acquisition — why every rule below exists

These are the project's claims about how an adult acquires a second language on an A1→A2 track. Each is a claim about *learning*, not a teaching procedure. Teaching rules live in §2 and must serve these claims; engineering/process law lives in ENGINEERING.md. Claims are falsifiable: if one falls, its dependent laws fall with it.

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

**P8 — Items progress through stages; automatization needs easy re-use of known language.** Rough stages: encounter → mapped → retrievable → usable under pressure → more automatic (skill-acquisition / DeKeyser; Nation's knowledge dimensions). Early stages need mapping and retrieval; later stages need speeded, low-burden re-use of *already known* language (fluency development). Nation's four strands (meaning-focused input, meaning-focused output, language-focused learning, fluency) is a **balance heuristic** (~equal time as a design target), not a law of the brain. *Known gap:* this system has no true fluency-development activity yet (free chat still pushes new/corrective work) — theory-level debt, §8.
*Served by:* §1.2 phase architecture (approximation only), §2.4 stage-aware re-encounters, ledger stage fields.

**P9 — Frequency and recycling entrench what association only starts.** Forms with higher type/token frequency and clearer form–function contingency are acquired earlier and more robustly (usage-based accounts: N. Ellis; Bybee). A closed inventory still needs deliberate recycle density; one-shot introduce without scheduled return under-teaches even perfect first associations.
*Served by:* §2.4 scheduler, introduce budget ≤2/session, frequency fields (PACK-FREQUENCY DEBT, §8).

**P10 — Support must be contingent on learner success.** Scaffolding is temporary, adaptive control of task elements the learner cannot yet manage (Wood, Bruner & Ross 1976). Contingent shift: fail → more tutor control/support; succeed → less (Wood, Wood & Middleton 1978; related observational line Wood & Middleton 1975). van de Pol, Volman & Beishuizen 2010: contingency, fading, and transfer of responsibility are the three key characteristics of scaffolding — contingency is necessary, not the only one. Bloom mastery learning: advance on demonstrated mastery with corrective loops, not on calendar or agenda pressure. Rosenshine 2012: novice guided-practice success near ~80%. Boundary on Bjork's desirable difficulties: difficulty is desirable only when effort can still succeed; repeated unrecoverable failure is not a desirable difficulty. Serves/constrains P1 (persistent failure ≈ input beyond reach), P6 (failure spiral → anxiety → WTC collapse).
*Served by:* §2.8; also §2.1 (uptake/repair), §2.5 (same-item repair), §2.7 (affect as signal).

<!-- NOTES:END -->

---

## §2. The teaching rules

### 2.1 Learner uptake outranks everything
Answer the human first, teach second. Help requests, topic requests, and comprehension failure preempt every plan and agenda — and confusion never burns the session's budget.
<!-- INTERNAL: HARD LAW — frozen 2026-07-28, adaptivity review; standing
order in the tutor system prompt AND the guard chain. Guard-chain order
in tutor/modes.py select_mode is frozen (shadow telemetry since the §1.1
rewrite 2026-08-03; scripts never ship). Incident: learner said "I didn't
understand" and was railroaded onward (2026-07-28, the review's founding
transcript — now a permanent CI fixture). -->

### 2.1a Learner-initiated content earns one turn of uptake
When the learner volunteers meaning that is **not** an answer to your outstanding prompt and not itself a §2.1 signal — an attempted description, an off-script topic, a self-flagged form (quotes, "?", "I don't know the word") — take it up the **same turn**, before any agenda move: (1) model the offered meaning in correct in-scope Spanish (one short model); (2) set the try **on that meaning**. Your agenda waits one turn.
Self-flagged forms are corrected same turn with one clear model when in scope; if out of scope, give one brief gloss or the nearest in-scope paraphrase — no multi-turn side quest (§2.6 still applies), and don't treat it as a taught item.
Budget: at most 1 consecutive uptake deferral, and ≤1 per 3 teaching turns. When exhausted: acknowledge in a clause, then proceed.
<!-- INTERNAL: BINDING — ⬛ Claude proposed, ⬛ Grok amended ×4 and
countersigned, promoted 2026-07-28; subordinate to §2.1 (reopened per
§7.3 without weakening it). Content-uptake does NOT freeze the session
phase clock (unlike §2.1 guards). Same-turn self-flag repair does not
consume the §2.5 hard-break budget unless escalated to multi-step drill;
no ledger/sheet introduce for off-catalog glosses. Architecture: code
owned the agenda-yield decision pre-§1.1-rewrite; detector work stays
shadow (§4.3 pre-registration; regex-only meaning classification is a
smell, §4.2). Incidents: weather and breakfast abandoned mid-attempt;
«uvia»/«circa» unrepaired — session 20260728-103617 (blind-graded #1/#4
defects). Reviewer test: an off-script attempted description answered
with an unrelated-agenda try, budget unspent, no §2.1 guard → violation. -->

### 2.2 Nothing new arrives naked
A new item must be *attached* to something the learner already holds at the moment it first appears — an association is built, or nothing is. First exposure routes by item class, in evidence order: true-cognate anchor → image → engineered high-coverage context → one ≤6-word English micro-gloss. One new item per introduce move; ≤2 introductions per session; near-synonyms of the same theme never co-introduce.
The anchor must sit **on the same line** as the item — a why with no referent builds no association. The item is met before its why: model before explain.
The scaffold exists to be stripped: it appears at first exposure and never again unless retrieval fails.
For structural items, chat adds a short explain beat — normally 1–2 lines; the first introduction of a new structure this session earns 2–3 lines of meaning and use — and never a dumped conjugation table or full paradigm in chat. Depth belongs where it has a designed home (the morphology card); chat brevity is not under-teaching when the depth has a home, and depth with no home is the fault.
<!-- INTERNAL: HARD LAW — enacted 2026-07-28, r7 CONVERGED; enforced by
gate:unscaffolded_new_item; serves P1, P2, P3. Cluster ban is CODE VETO
at any count (Tinkham/Waring). Engineered ≥95%-coverage context is
DEFERRED (§8). Attachment clause 2026-07-29 (floating-anchor incident;
⬛ Grok AMEND): enforced as anchor_in_reply(..., key=) line adjacency —
presence-anywhere is not scaffold evidence. Display order enforced in
compose_visible + UI part blocks. Morphology-card rider (enacted
2026-07-29, docs/reviews-morph-card-introductions.md): when the
introduced item maps to verb morphology, the Morphology card MUST show
that paradigm same turn, selected in CODE from typed INTRODUCED /
FIRST_SEEN events — never by prompt request; learner engagement outranks
the introduction fill. Reopen bound (Grok Q2): multi-verb introduce
turns ≥1/50 → reopen the first-hit picker. Incidents: «hasta luego» +
«adiós» introduced together, bare (2026-07-28, founding failure of r7);
estar introduced 2026-07-29 with the card blank. Reviewer test: a table
key's first appearance in a session log must carry a rule_id or a
scaffold, or the gate must have fired. -->

### 2.3 English is scaffold, not wallpaper
English has three jobs: (1) lifeline when the learner is stuck — once, short, then back to Spanish; (2) the first-exposure micro-gloss (§2.2); (3) cognate/keyword anchors. Dual-subtitle walls (X = Y on every line) are banned. Never re-gloss an already-introduced item unless retrieval failed this turn — the crutch must stay gone.
<!-- INTERNAL: BINDING — amended policy, r7 §6; enforced by
gate:english_wall and gate:regloss. -->

### 2.4 Memory is retrieval, not re-exposure
Introduced items come back on an expanding ladder — 1 day → 3 days → doubling, capped at 14 days; a failure resets to 1 day. Due items are woven into conversation as natural elicits — no flashcard chrome. Strip the scaffold on re-encounter. Record outcomes only on clear evidence; **silence records nothing** — a guess recorded as data is worse than no data.

**Placement-window rider (2026-08-06, onboarding round — ⬛ Grok ACCEPT_WITH_AMENDS, docs/archive/reviews/onboarding-placement-20260806.md):** a blank (ability-empty) learner's first session opens with ONE short English orientation (≤80 words, no test/quiz/exam language) then an adaptive mini-placement: assessment-move evidence types in rough difficulty order, model-authored items, hard stop on first clear level signal or one failed beat, true-zero settle by beat 1–2, N ≤ 5 beats. INSIDE this window only, the ≤1-per-3-turns assessment density cap and the §2.8 repair obligation are suspended — placement failures are level data, not struggle to repair; both rules resume in full at landing. Placement evidence is provisional altitude (§3.2): recognition/comprehension → at most emerging, production stretch → at most fragile, never `known` from placement alone. Self-report routes the next probe, never concludes level (shared variance with measured proficiency ≈ 20–40% — citations in the round doc). Non-blank sheets never re-enter placement; only an explicit learner reset does.

**Assessment-move rider (2026-08-06, r6 round — ⬛ Grok ACCEPT_WITH_AMENDS, docs/pedagogy-research-r6-assessment-moves.md):** the natural elicit stays the DEFAULT realization; additionally, due/stale items and mode-starved can-dos may be realized through the assessment-move menu — receptive/productive recall ("¿qué significa X?" / "how do you say Y?"), single-sentence translation, gated elicited imitation, preconditioned dictation, gist+detail probes on a short text, picture description, paraphrase, prepared mini-monologue. These are TEACHING (effortful retrieval per P3 + mode evidence), bounded hard: ≤1 assessment beat per 3 teaching turns (stale evidence is a priority trigger INSIDE the cap, never a second channel); an assessment beat and a §2.5 form-focus break never both fire in one turn; never two failed checks in a row (§2.8); A/B English-meaning recognition on known items stays banned (chrome). Grading honesty: interpretive credit (IT) requires interpretive-valid behavior (gist/recognition-in-context), presentational credit (PR) requires presentational-valid production (monologue or spontaneous multi-sentence self-presentation); an accurate echo (EI) grades emerging at best — mode-VALID evidence is required; the menu lists canonical ways to obtain it, not mandates. Direction variety (L2→L1 and occasional L1→L2) is preferred, never a per-item mandate. (Evidence base and citations: docs/pedagogy-research-r6-assessment-moves.md — research stays in the notes, not in this teaching cut.)
Vary the frame: eliciting an item in the same context every time is re-exposure wearing retrieval's clothes. Each due elicit should reach for a context the item has not been retrieved in yet — the due data shows which frames are already used.
<!-- INTERNAL: HARD LAW — enacted 2026-07-28, r3/r6;
tutor/retrieval_scheduler.py. Varied-retrieval rider enacted 2026-07-29
(⬛ Grok AMEND verbatim; docs/design-encounter-variety.md): frames_seen
is scheduler-owned exposure history, never ability evidence; soft
direction only (§1.1a); a multi-frame promotion bar needs the
pre-registered revisit bound + a separate §3.2 countersign. Incidents:
estar's every exercise through 2026-07-29 was the wellbeing frame.
Introduce-order corollary (tutor/introduce_router.py, shadow):
greeting/farewell openers lead only for a true-zero sheet; matcher reads
only next_best targeting fields, never avoid/reason (the avoid-string
"greetings" had promoted greetings — hola-on-known-open incident). -->

### 2.5 Correction is timely, budgeted, and repair-seeking — never an ambush
Track errors as patterns with recency; never break a clean turn for a stale error. Form-focus hard breaks are budgeted: ≤1 per 3 turns. Default move when flow matters: a short recast. When a pattern is being targeted and affect allows: prompt for learner self-repair instead of recasting — prompts beat recasts for student-generated repair. Comprehension repair stays on the SAME item — re-model, associate, no topic jump.
<!-- INTERNAL: BINDING — r1 + example-bleed review 2026-07-28; theory:
amended P5; Grok-amended 2026-07-28. Recency window K=4 learner turns +
cooldowns in code. Elicitation path is CF-PROMPT DEBT (§8) until built.
Incidents: «llama» re-corrected on a clean turn from stale sheet counts
(2026-07-28). Citation-inversion incident: first draft cited Lyster &
Ranta FOR recast-first; their finding is the opposite (Grok countersign
2026-07-28). -->

### 2.6 The level's scope is a closed world
The sheet's `domain_scope` says what is deferred, out of scope, or recognition-only at this level: decline out-of-scope requests briefly, without lecturing, and steer back. Grammar and skills you teach come from the sheet's inventories; vocabulary is yours to choose — concrete, everyday, level-appropriate words that serve the abilities being built. Every model, example, and scaffold you produce must stay inside the level's rules.
<!-- INTERNAL: HARD LAW — standing. REWRITTEN 2026-08-03 twice: (1) was
"The pack is a closed world" citing the deleted course pack; (2) later
same day the closed WORD LIST died too (USER: "Why are we telling this
smart ai what spanish words to use?") — scope is the level's RULES
(domain_scope + grammar/skills inventories); vocabulary is open within
them. The association table remains internal data (images, glosses,
exposure bookkeeping), never prompt content. Incident: the author's own
"pack-legal" replacement examples were 50% illegal (Grok REJECT,
example-bleed review); the scope law binds authors, not just the model. -->

### 2.7 Affect is a signal, not decoration
Limited time compresses the session; anxiety shifts the balance toward input over forced production. Read affect and adapt; don't perform concern or treat it as an on/off switch.
<!-- INTERNAL: GUIDELINE — r4; partially built (WTC proxy — DEBT, §8).
Boredom machinery DELETED 2026-07-30 (junk audit): affect.boredom_risk
fired in 0 of 207 real turns and its guard sat above comprehension
repair — P6 stays theory; code returns only on the omission-ledger
revive condition (evals/omission_ledger.jsonl). A principle needs no
runtime until an observed failure demands one. -->

### 2.8 Support rises when the learner struggles — and fades when they succeed
Contingency is the rule: after a failed, garbled, or clearly stuck attempt on an item, the *next* turn raises support — shorter and simpler Spanish, more English scaffolding when needed, re-model the *same* item, and a smaller ask (recognition or yes/no before free production). After a clear success, hand control back: less support, a bigger ask.
If the learner fails the same item twice in a row even after raised support, stop eliciting production of it for now. Model it again, check comprehension only, and return to something the learner *can* do — bank a success before retrying the hard thing. Novices need mostly-successful practice; a failure streak teaches anxiety, not Spanish. A good floor activity when production keeps failing is a quick match-the-word game (word ↔ meaning, right in the chat): deliberate form–meaning matching is fast, well-evidenced, and takes the communicative pressure off.
While the learner is struggling on the current work, introduce nothing new: new items wait until the learner is succeeding again. New items ride on a base of success, never on top of confusion.
Grade honestly: a garbled or uninterpretable attempt is evidence of difficulty or non-evidence for ability — never grounds to mark an ability as emerging. Struggle must not be rewritten as progress.
<!-- INTERNAL: HARD LAW — proposed from the 2026-08-04 stress-test
session (USER as failing student: tutor kept pace through 4 straight
failures and offered a NEW WORD after explicit distress; grades
inflated garble to "emerging"). ⬛ Claude drafted, ⬛ Grok AMENDed ×4
(Wood, Wood & Middleton 1978 attribution fix; contingency starts at
fail #1 — the two-fail production freeze is PROJECT POLICY, not a
literature constant, N change requires a pre-registered live bound;
grading rider reworded to reinforce ENGINEERING §3.2 without implying
a struggle field), all accepted; USER-ratified 2026-08-04. Serves P10,
P1, P6. Round: docs/reviews-contingent-support.md.
Matching-floor sentence added 2026-08-04 (USER "go"): deliberate
paired-associate matching as the recognition rung — Nation
(language-focused learning strand), Webb (deliberate vocabulary
learning), Nakata (flashcard spacing); recognition retrieval weaker
than recall for retention (Kang) but the correct rung when recall
fails; affect win per P6. Later the same day the show_game widget
shipped (USER games directive) — the matching floor now has both a
chat form and a widget form; the stance's Games section carries the
round-turn placement. -->
