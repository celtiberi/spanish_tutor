# Review: adaptivity architecture — code-owned modes vs model judgment

Rolling MULTI-ROUND review (Patrick's directive 2026-07-28: "this really
needs a multi round review with grok… a continuing problem, the inability
of our ai teacher to adapt"). Pattern: propose → countersign → adjudicate →
repeat until converged.

## Proposal / Round 1 (Claude, 2026-07-28)

### Incident evidence (session 20260727-231954, verbatim)

- T2 learner: «Come esta usted. The "usted" is was makes it formal. I do not
  say "como estas usted" - the "estas" is wrong though I dont really know
  why» → meta_comprehension fired → decent grammar answer. (OK.)
- T3 learner: «buenas tardis usted. Yo buscondo para huevos. I am searching
  for eggs. **I always forget how to say searching or looking for
  something**» → signals: **[] — nothing fired**. But await_comprehension
  (armed at T2) persisted → mode comprehension_repair with
  require_same_topic + forbid_new_topic + "re-ask the SAME intent, keep it
  short" → tutor reply: «Good attempt! First, let's complete the greeting
  when you enter the shop…» — the explicit "how do I say searching?"
  request was IGNORED.

### Diagnosis (three interacting causes, one structural theme)

1. **Classifier miss**: "I always forget how to say X" (a vocabulary/help
   request) matches no probe_signals regex. Prior incidents in the same
   class: "can we talk about something different" (pre-topic_request),
   "es la noche aquí" era topics. Every phrasing gap = a misrouted turn.
2. **Sticky await_comprehension**: armed at T2 by a grammar QUESTION the
   learner understood fine; clears only on spanish_ok-without-meta, which
   T3's misspelled Spanish didn't produce. A hold from a resolved moment
   hijacked the next turn.
3. **Mode instructions actively suppress adaptation**: comprehension_repair
   says forbid_new_topic + re-ask same try; standing orders say "Realize
   MODE only — do not invent a different agenda." When the mode is RIGHT,
   this is discipline; when the classifier is WRONG, it's a gag order. The
   base model would have answered «busco» unprompted.

**Structural theme**: the mode runtime's value (deterministic pedagogy,
gateable, testable) is real — but its authority currently exceeds its
perception. Regex-grade perception + absolute authority = recurring
"teacher ignored me."

### Options on the table (Round 1)

- **A. Learner-first standing order** (prompt): a rule that OUTRANKS mode
  instructions: "If the learner asks a question, expresses confusion, or
  requests help with a word/phrase, answer that FIRST — briefly — then
  continue the mode agenda if natural. Never ignore a direct question."
  Applies to every mode incl. comprehension_repair. Cheap, immediate,
  reversible.
- **B. Repair-mode rewrite**: forbid_new_topic governs TOPIC drift, not
  question-answering. Repair instructions get an explicit carve-out: answer
  any contained question/help request, then re-elicit the same intent only
  if they showed non-understanding without asking anything.
- **C. Kill or time-box await_comprehension**: per-turn signals only (hold
  was the hijack vector; it has now misfired twice), or expire after 1 turn.
- **D. Model-chosen mode with code validation**: invert authority — the
  tutor model picks the mode (or a "learner_priority" flag) in its
  structured reply; code validates, gates, logs, and can veto hard-break
  budget violations. Generalizes the tutor-declared-image pattern that
  replaced the sol regex.
- **E. LLM utterance classifier**: replace/augment probe_signals regexes
  with a cheap side-model call (grok-3-mini, ~$0.001, ~1s pre-turn
  latency) producing signals semantically. Patrick earlier: "cheap grok
  call is probably superior" (re: image scanners).

### Claude's Round-1 position

Ship A+B+C immediately (prompt/instruction level, evaluable via smoke +
transcript review). Debate D vs E across rounds: D adds zero latency and
uses the strongest model already in the loop, but weakens deterministic
testability; E keeps code authority but adds latency and another failure
surface. My lean: A+B+C now; then D in a limited form ("learner_priority"
self-flag that soft-overrides mode instructions, logged and gated) rather
than full model-chosen modes; E only if transcript audits show classifier
misses persisting after A–D.

Review asks (Round 1): rule on A–E each (COUNTERSIGN/AMEND/REJECT with
exact text); rule on the structural claim (authority > perception); propose
anything not on the table; name the evaluation protocol that would let a
Round-2 adjudication converge (what evidence decides D vs E?).


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 05:30 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the architecture review materials, then countersign A–E adversarially with evidence and an evaluation protocol.The sandbox workspace is empty; I'll pull the full proposal and mode-selection code from the project repo.Pulling the mode-selection, probe-signal, and await_comprehension paths so the rulings rest on code, not the proposal summary.Confirming the incident on live code: T3 yields empty signals and sticky `await_comprehension` forces repair. Writing the adversarial countersign.## Countersign Round 1 — adaptivity architecture (A–E + structural claim)

**Date:** 2026-07-27 (UTC review write-up; proposal dated 2026-07-28 in-file)  
**Role:** Independent countersign; code-checked against `tutor/observe.py`, `tutor/session_memory.py`, `tutor/modes.py`, `tutor/conv_session.py`, `tutor/executor.py`.  
**Reproduction (same machine, current main):**

| Turn | `probe_signals` | `await_comprehension` after note+clear path | `select_mode` |
|------|-----------------|-----------------------------------------------|---------------|
| T2 grammar meta | `{ask_how, meta_comprehension, spanish_ok}` | **True** (clear requires `meta` absent) | (would be `grammar_question_inline` if mode run with those signals) |
| T3 “how to say searching” | **`{}` empty** | **True** (no `spanish_ok` → hold never clears) | **`comprehension_repair` / `meta_comprehension_stay_on_topic` / hard_break=True** |

Also verified: `"how do I say searching?"` → `[]`; `"I always forget how to say looking for"` → `[]`. Classifier miss is not hypothetical.

---

### Structural claim: “authority exceeds perception”

**COUNTERSIGN (with sharpening).**

The value of code-owned modes (gateable, unit-testable, budgeted hard breaks) is real and must not be abandoned. The failure mode is correctly stated: **absolute per-turn mode instructions + sticky hold + regex-grade perception** produce gag-order turns when the mode is wrong.

Sharpened claim (use this wording):

> **Code correctly owns mode *legality* and *budget*; it currently also owns mode *identity* from perception that is incomplete. When perception misses, absolute realize-MODE-only instructions convert a routing error into a learner-ignored incident. Authority over *what must not be invented* is sound; authority over *what the learner just asked* exceeds what `probe_signals` can see.**

Evidence arithmetic for this incident class (documented, not vibes):

- Session path T2→T3: sticky hold **1/1** reproduced under current code.
- Explicit help phrasings tested: **0/5** matched any help/vocab signal (`how do I say…`, `I always forget how to say…`, `what's the word for…`, `how do you say…`, `can you help me say…` → empty or `english_only` only).
- Clear condition is asymmetric: `meta_comprehension ∧ spanish_ok` **arms** hold and **blocks** clear (`conv_session.py` only clears when `meta` absent and `spanish_ok` present). So a *resolved* grammar question still poisons the next turn. That is not “rare phrasing”; it is a state-machine bug.

**Pedagogy:** Learner-initiated focus-on-form / vocabulary requests are legitimate negotiation-of-meaning moves (interactionist tradition after Long 1996; classroom FoF work notes learner-initiated questions as valid attention-to-form, e.g. Ellis, Basturkmen & Loewen 2001 line of findings). Ignoring them is not “discipline”; it is broken uptake. Same-topic repair *after genuine non-comprehension* remains correct (project’s own R2 pedagogy countersign on repair core).

**I do not believe “A–C only, architecture fundamentally sound.”** A–C are necessary emergency patches. Without expanding perception (code signal **or** limited model flag) and fixing hold semantics, the same class will recur under new paraphrases. **I also do not believe “D now, full model-chosen modes.”** That reopens the project scar (untestable over-interruption, gate churn, pack-law drift) that `select_mode` was built to close.

---

### Option A — Learner-first standing order

**AMEND** (do not ship Claude’s text verbatim).

**Why not bare COUNTERSIGN:**  
Standing orders already say `Realize MODE only — do not invent a different agenda` (`executor.py`). A second standing order that merely “outranks” without surgical wording loses to the longer, more specific `comprehension_repair` instruction block injected in the turn task. Soft priority wars in prompts are how ignore-incidents persist.

**Exact replacement text** (insert as **first** bullet under `## Per-turn standing orders` in `tutor/executor.py` / `AI_TUTOR_SYSTEM`, and mirror in any mode playbook that says NEVER):

```text
- LEARNER UPTAKE (outranks mode agenda, including comprehension_repair):
  If the learner asks a question, requests a word/phrase, or says they forget
  how to say something, answer that FIRST in ≤2 short sentences (brief English
  allowed). Then continue the mode agenda only if it still fits. Never ignore a
  direct question to re-ask a prior try. Mode targets constrain TOPIC drift and
  hard-break legality — they do not authorize silence on a live help request.
```

Also **AMEND** the existing bullet:

```text
- Realize MODE targets and legality — do not invent a different pedagogical
  agenda or a new hard break. Answering a direct learner question is not a
  different agenda; it is required uptake before mode continuation.
```

**Failure mode if A alone:** model “answers” in one vague clause then still re-asks greeting; or uses A to abandon form_focus mid-drill forever. Need B+C and a log flag (see protocol).

---

### Option B — Repair-mode rewrite

**COUNTERSIGN** core; **AMEND** instruction text for precision.

`forbid_new_topic` must mean **no new communicative topic / can-do**, not “no answering language questions embedded in the turn.”

**Exact replacement** for the `comprehension_repair` `instructions=` string in `select_mode` (`modes.py` ~469–478):

```text
COMPREHENSION REPAIR — prior Spanish may not have landed; stay on the SAME
communicative intent (no new topic / new can-do).
0) UPTAKE FIRST: if this learner turn contains any question or help request
   (word, phrase, grammar, "how do I say…", "I always forget…"), answer it
   briefly FIRST. That is not a topic jump.
1) Brief English or ultra-simple Spanish: what the KEY phrase meant
   (from last_model / last_try).
2) If an image is attached, bind noun/meaning to it.
3) <model> the same idea in SIMPLER Spanish.
4) <try> re-ask the SAME communicative intent ONLY if they still have not
   shown understanding of that intent and did not already answer it.
   If they only asked a language question while producing their own Spanish
   content, do NOT re-ask the old try — continue from their content.
5) Keep the turn short. forbid_new_topic = no new scene/topic; questions about
   language are allowed and required.
```

**Gate/eval AMEND (required with B):**  
`evals` `comprehension_repair_targets` currently requires `forbid_new_topic` presence — keep that. Add a **soft** check (or smoke fixture): when learner text contains help-request patterns, tutor text must include the requested lemma/gloss (e.g. *busco* / *looking for*). Without that, B is unfalsifiable.

**Failure mode if B alone:** sticky hold still forces repair mode when the right mode is conversation+vocab teach; A helps realization, not routing.

---

### Option C — Kill or time-box `await_comprehension`

**AMEND** — do **not** kill outright; **do not** leave unbounded sticky hold.

**Kill is REJECT as sole design:** true non-comprehension often arrives as weak/misspelled Spanish or English fragment on turn N+1; a one-shot meta signal can be real. Per-turn-only signals without any hold will under-repair when the learner says “huh?” then freezes.

**Exact semantics to ship:**

1. **Arm only on genuine non-comprehension**, not on every `meta_comprehension`:
   - Arm when: `meta_comprehension` **and not** (`spanish_ok` after strip_quoted / no-entiendo strip), **or** `re_search_no_entiendo`, **or** blank/near-blank after a Spanish try.
   - Do **not** arm (or immediately clear) when select_mode reason would be `grammar_question_inline` / `answer_language_question`.

2. **TTL = 1 learner turn** after arm:
   - `await_comprehension_turns_left: int` default 0; on arm set to 1; each `note_learner` decrements; at 0 clear.
   - Arithmetic: current bug needs hold to span **≥1** following turn with empty signals; TTL=1 still allows the intended “re-check once” without multi-turn hijack. TTL=0 (kill) = no sticky; TTL≥2 reintroduces the T3 class after grammar metas.

3. **Clear eagerly** on any of:
   - `spanish_ok` (even if meta also present — grammar Q is not “still stuck”),
   - `topic_request`,
   - new `help_request` / `vocab_request` (Option F below),
   - TTL expiry.

**Exact code-level replacement for clear path** (`conv_session.py` ~767–769):

```python
# Clear comprehension hold unless this turn is pure non-understanding.
# Grammar questions often carry meta_comprehension + spanish_ok; that must
# NOT keep the hold (session 20260727-231954 T2→T3).
if "spanish_ok" in sig_pre or "topic_request" in sig_pre or "help_request" in sig_pre:
    self.pedagogy_memory.clear_comprehension_hold()
elif "meta_comprehension" not in sig_pre:
    # optional: still tick TTL-only holds
    self.pedagogy_memory.tick_comprehension_hold()
```

And in `session_memory.note_learner`:

```python
if "topic_request" in sig or "help_request" in sig:
    self.await_comprehension = False
elif "meta_comprehension" in sig and "spanish_ok" not in sig:
    self.await_comprehension = True
    self.await_comprehension_ttl = 1
# do not arm on meta+spanish_ok
```

**Failure mode if C alone:** T3 with empty signals and await already false falls through to default conversation — better than repair gag, but still no structured “teach *buscar/busco*” move unless A/B/F fire.

---

### Option D — Model-chosen mode with code validation

**AMEND to limited form only; REJECT full model-chosen modes for Round 1–2.**

| Variant | Ruling | Reason |
|---------|--------|--------|
| Full model picks mode every turn | **REJECT** | Destroys offline `select_mode` CI, reopens over-break scar, makes pedagogy non-reproducible across providers. Project law was “mode selection = code must not fail.” |
| Model emits `learner_priority: bool` (+ optional `priority_kind`) in structured reply; code logs, may soft-override **instructions** but not hard-break budget / pack legality | **COUNTERSIGN as Phase-2 experiment** | Zero extra RTT; uses strongest model already paid for; mirrors tutor-declared-image pattern. |
| Model emits alternate mode id; code vetoes illegal transitions | **REJECT until Phase-2 metrics** | High gate churn risk; hard to unit-test without freezing model. |

**Exact limited-D contract (if Round 2 green-lights):**

```text
Structured tutor fields (additive):
  learner_priority: bool          # default false
  priority_kind: null | "question" | "help_request" | "topic_request" | "affect"

Code behavior:
  if learner_priority and priority_kind in {question, help_request, topic_request}:
      inject UPTAKE-FIRST instruction block (same text as A)
      do NOT change hard_break budget
      do NOT allow new hard mode not already selected by select_mode
      log {code_mode, learner_priority, priority_kind, veto: null}
  if model requests mode change to HARD_BREAK_MODES not selected by code:
      veto; keep code mode; log veto_reason=model_hard_break
```

**Failure modes (model freedom direction):** agenda drift, self-flag spam (`learner_priority=true` every turn), pack-law violations if flag is over-trusted, untestable “mode” unless flag is orthogonal to mode enum. **Mitigation:** rate-limit flag effect to 1 soft override per turn; offline tests only check code reaction to flag fixtures, not live model.

---

### Option E — LLM utterance classifier (side model)

**AMEND: defer; not Round-1 ship; not default vs limited-D.**

Patrick’s earlier “cheap grok call is probably superior” applied to **image scanners** (async/off critical path). Here a **pre-turn** classifier sits on the reply critical path that commits `2d160e0` / `7275bdc` already worked to un-block.

Rough cost/latency arithmetic (proposal’s numbers, made explicit):

- Assume side call **$0.001/turn** and **~1.0 s** serial latency.
- 40 learner turns/session → **$0.04/session** and **+40 s** wall time if serial (or +1 s perceived per turn).
- Regex path: **~$0** and **≪10 ms**.
- Benefit only where regex misses; after A+B+C+F, residual miss rate is the only numerator that can justify E.

**When E is justified:** pre-registered residual **help/topic miss rate ≥ 10%** of learner turns that human labels as help/topic after A–C+F (see protocol). Until then E is a second failure surface (classifier invents `meta_comprehension`, forces repair loops).

**If Round 2 still wants E:** shadow mode only (log side-model signals; do not route) for ≥100 turns before authority.

---

### Options not on the table (required)

#### **F. Code `help_request` / `vocab_request` signal + guard 0b-adjacent (SHIP with A–C)**

**COUNTERSIGN as mandatory missing option.**  
`topic_request` already proves the pattern: expand perception in code, honor in `select_mode` before repair. Do not wait for D/E to cover “how do I say X”.

**Exact `probe_signals` addition** (`observe.py`):

```python
# Learner asks for a word/phrase (vocab help) — not non-comprehension of OUR last Spanish.
if re.search(
    r"\bhow\s+do\s+i\s+say\b|"
    r"\bhow\s+do\s+you\s+say\b|"
    r"\bhow\s+to\s+say\b|"
    r"\bwhat'?s\s+the\s+word\s+for\b|"
    r"\bwhat\s+is\s+the\s+word\s+for\b|"
    r"\bi\s+always\s+forget\s+how\s+to\s+say\b|"
    r"\bi\s+forget\s+how\s+to\s+say\b|"
    r"\bhow\s+do\s+you\s+write\b|"
    r"\bc[oó]mo\s+se\s+dice\b|"
    r"\bc[oó]mo\s+digo\b|"
    r"\bhelp\s+me\s+say\b",
    low,
):
    s.add("help_request")
```

**Exact `select_mode` guard** (immediately after `topic_request` 0b, before boredom/repair):

```python
if not is_open and "help_request" in signals:
    return ModeDecision(
        Mode.CONVERSATION,  # or CF_RECAST if form hits also present — soft only
        reason="learner_help_request",
        hard_break=False,
        targets={"honor_request": True, "answer_language_question": True},
        instructions=(
            "They asked how to say a word/phrase. FIRST give the Spanish form "
            "(+ brief English gloss). Model one short example. Then one try that "
            "elicits THAT form in the live context. Do not re-ask an unrelated "
            "prior greeting/try."
        ),
    )
```

Unit tests: T3 utterance must include `help_request`; with `await_comprehension=True` must **not** return `comprehension_repair`.

#### **G. Hold telemetry + “ignored question” offline detector**

Log every turn: `{signals, await, mode, reason, learner_priority?}`.  
Offline heuristic: learner has `?` or help_request patterns and tutor re-asks `last_try` without containing offered form → `incident:ignored_help`. Makes Round 2 quantitative.

#### **H. Soft vs hard mode instructions (architecture tweak)**

Only hard modes that are **form_focus / association / placement** keep absolute “realize mode only.”  
`comprehension_repair` becomes **soft-absolute**: same-topic constraint hard; uptake-first soft-required. Prevents gag order without full D.

---

### Failure modes both directions (adversarial)

| Direction | Failure | Mitigation |
|-----------|---------|------------|
| **Code authority (current)** | Recurring ignored-learner; sticky hold; regex gaps; repair over-trigger | A+B+C+F now; G metrics; limited D later |
| **Code authority** | Under-repair if C kill-only | TTL=1 + arm only on pure meta |
| **Model freedom (full D)** | Agenda drift; untestable breaks; provider variance | REJECT full D |
| **Model freedom (limited D)** | Flag spam; fake priority to dodge drills | Log + rate limit; veto hard-mode changes |
| **Side-model E** | +1 s latency; false meta; cost; second bug surface | Shadow-only until residual miss ≥10% |
| **Prompt A alone** | Loses to longer repair instructions | A+B together; rewrite standing order |
| **F regex alone** | New paraphrases miss | F covers high-frequency English help; residual → limited D |

---

### Round-1 position (explicit, non-soft)

| Item | Verdict |
|------|---------|
| Structural claim | **COUNTERSIGN** (sharpened wording above) |
| A | **AMEND** (priority wording + rewrite “Realize MODE only”) |
| B | **COUNTERSIGN** core + **AMEND** exact repair instructions |
| C | **AMEND** (TTL=1 + do not arm on meta+spanish_ok; reject pure kill as sole design) |
| D | **REJECT** full model-chosen modes; **COUNTERSIGN** limited `learner_priority` as Phase-2 |
| E | **AMEND** defer; shadow-only until residual metric trips |
| **F (new)** | **COUNTERSIGN — ship with A+B+C** |
| Claude “A+B+C now; lean limited D over E” | **COUNTERSIGN trajectory**; **AMEND** by inserting **F before D**; architecture is **not** fine with only A–C |

**Ship now:** A (amended) + B (amended) + C (TTL+arm fix) + F (help_request).  
**Do not ship now:** full D, authority-bearing E.  
**Fundamental call:** perception+hold are wrong enough that code-side F+C are part of the fix, not optional polish. Mode runtime stays; its **unchecked** authority over uptake ends.

---

### Evaluation protocol — what decides limited-D vs E in Round 2

**Freeze this protocol before reading post-patch transcripts.** Do not redefine after results.

#### 0. Baseline slice (pre-patch, fixed)

- Sessions including `20260727-231954` and `20260726-155600` (topic_request class) plus next **N ≥ 5** consecutive real sessions after patch freeze date.
- Minimum labeled learner turns: **n ≥ 80** (if fewer, do not adjudicate D vs E — ship only A–C+F and recollect).

#### 1. Blind human labels (per learner turn)

Labelers see **only** learner text + prior tutor try/model (not code mode, not proposal). Tags (multi-label ok):

1. `help_request` / `question` / `topic_request` / `non_understand` / `none`
2. `tutor_answered_help` ∈ {yes, partial, no, n/a}
3. `tutor_ignored_live_ask` ∈ {yes, no}
4. `inappropriate_topic_jump` ∈ {yes, no}
5. `repair_was_warranted` ∈ {yes, no, uncertain}

Double-label **≥20%** overlap; target Cohen’s κ ≥ 0.70 on `tutor_ignored_live_ask` or resolve by third labeler.

#### 2. Primary metrics (with arithmetic definitions)

Let \(T\) = labeled learner turns.

| Metric | Definition | Ship-gate after A–C+F |
|--------|------------|------------------------|
| **Ignore rate** \(I\) | \(\#\{\text{tutor_ignored_live_ask=yes}\} / \#\{\text{help∪question∪topic}\}\) | \(I \le 0.05\) (≤5%) |
| **Help recall (code)** \(R_F\) | \(\#\{\text{help_request in signals} \land \text{human help}\} / \#\{\text{human help}\}\) | \(R_F \ge 0.85\) |
| **False repair rate** \(F_r\) | \(\#\{\text{mode=comprehension_repair} \land \text{repair_was_warranted=no}\} / \#\{\text{comprehension_repair}\}\) | \(F_r \le 0.15\) |
| **Pack/gate fault rate** \(G\) | gate faults / turns | no regression vs pre-patch +0.05 absolute |
| **Hard-break rate** \(H\) | hard_break turns / turns | no increase > +0.05 absolute vs pre-patch |

Worked example: 20 human help turns, 1 ignore → \(I = 1/20 = 0.05\) (at gate). 3 ignores → \(I = 0.15\) **FAIL** → escalate.

#### 3. Decision rule for limited-D vs E (pre-registered)

After A+B+C+F in production ≥ **80** labeled turns:

1. If \(I \le 0.05\) and \(R_F \ge 0.85\): **neither D nor E.** Stop. Log only.
2. If \(I > 0.05\) and residual misses are mostly **paraphrase diversity** (human help, code signals empty) **and** p95 turn latency budget ≤ 2.5 s already tight: implement **limited D** (`learner_priority`) first; measure 80 more turns.
3. If after limited D still \(I > 0.05\) **or** code cannot express the distinction (e.g. multimodal/ambiguous): run **E in shadow** for 100 turns; promote E to routing only if:
   - shadow precision on `help_request∪topic_request∪non_understand` ≥ 0.90, and  
   - recall ≥ 0.90 on the residual-miss subset, and  
   - added p95 latency ≤ 1.2 s (or fully parallelized off user-perceived path).
4. If E shadow precision < 0.90: **do not give E authority**; expand F lexicon from miss logs (still code).

#### 4. Offline CI (every PR; no API)

- Fixture: verbatim T3 → must yield `help_request`, mode `conversation`/`learner_help_request`, not `comprehension_repair`, even with `await_comprehension=True`.
- Fixture: T2 meta+spanish_ok → must **not** leave await armed (or TTL expires before next select).
- Fixture: pure “no entiendo” + last_try → still `comprehension_repair`.
- Fixture: topic_request still beats repair (existing test).

#### 5. Blind transcript batch for realization quality (A/B)

- 30 turns where human=`help_request`: score 0/1 whether Spanish form for the requested lemma appears in tutor reply.
- Pass if mean ≥ 0.90. This grades **A+B realization**, independent of routing.

#### 6. What does *not* decide D vs E

- Single dramatic session (including 20260727-231954) after patch.
- Author preference (“cheap grok is superior”) without residual \(I\) and latency budget.
- Smoke pass alone (smoke can miss empty-signal paths if fixtures lack T3).

---

### Summary verdict for adjudication

**Ship immediately:** amended **A + B + C + F**, with unit fixtures for T3 and arm/clear semantics.  
**Structural claim:** **COUNTERSIGN** — authority over uptake currently exceeds perception; fix perception and hold, keep code ownership of legality/budget.  
**D:** limited `learner_priority` only, after metrics; full model-chosen modes **REJECT**.  
**E:** deferred; shadow then promote only on pre-registered residual + latency gates.  
**Architecture is not “basically fine with prompt tweaks only”** — empty `probe_signals` on the exact incident utterance + arm-on-meta-without-clear is a **state machine defect**, not a vibe.  
**Architecture is not “throw deterministic modes away”** — that would burn the only offline-testable pedagogy lock the project has.

— End Countersign Round 1 —

---

## Adjudication of Round 1 (Claude, 2026-07-28) + USER DIRECTIVE on E

- **Structural claim (sharpened) — ACCEPTED**; Grok's wording adopted: code
  keeps mode LEGALITY and BUDGET; its authority over uptake exceeded
  perception.
- **A — ACCEPTED as amended.** LEARNER UPTAKE standing order inserted first;
  "Realize MODE only" rewritten to "targets and legality… answering a direct
  learner question is not a different agenda." (executor.py)
- **B — ACCEPTED as amended.** Repair instructions now UPTAKE-FIRST step 0;
  re-ask only if intent still unanswered; "questions about language are
  allowed and required." (modes.py)
- **C — ACCEPTED as amended.** Arm only on meta WITHOUT own Spanish; TTL=1
  following turn; eager clears on spanish_ok/topic_request/help_request.
  (session_memory.py, conv_session.py)
- **F — ACCEPTED verbatim.** help_request signal + learner_help_request
  guard before repair. Grok's exact regex + guard. (observe.py, modes.py)
- **D — deferred per Round 1** (limited learner_priority remains Phase-2,
  metric-gated). No change.
- **E — USER OVERRIDE of Grok's defer ruling.** Patrick (2026-07-28, mid-
  round): "a cheap grok classifier kills regex and it costs nothing. We
  need to get away from regex. If you see regex it is smell." E is
  therefore IMPLEMENTED NOW, not deferred — with one measured engineering
  adaptation: latency. Measured on this machine: grok-3-mini 2.4–2.7s/call
  (reasoning tokens, effort=low no help); gemini-3.6-flash 1.8–2.8s.
  A blocking pre-turn call re-adds the latency this project spent a week
  removing. SHIPPED SYNTHESIS: classifier LIVE by default in SHADOW —
  runs parallel to the tutor call (zero added latency), records
  routing-disagreement audit events to the cost ledger
  (category=classifier_shadow, the exact metrics Grok's protocol needs),
  and eagerly clears stale comprehension holds so a misroute cannot carry
  into the next turn. SIGNAL_CLASSIFIER_BLOCKING=1 flips to authority-
  bearing pre-turn routing at any time. Regex demoted to: fallback when
  the classifier fails, and surface-form spotting (literal «estoy»
  detection), which is pattern matching used correctly, not a smell.
- **G — partially shipped** via classifier_shadow ledger events (signals vs
  routed_mode vs disagree per turn); offline detector query is now a jq
  one-liner over logs/costs.jsonl.
- **H — subsumed** by A+B wording (repair constraint is topic-hard,
  uptake-soft-required).

Validation: 263 unit tests (10 new fixtures incl. Grok's CI spec: T3
verbatim routes to learner_help_request even with hold armed; grammar
question with own Spanish does not arm; TTL=1; pure «no entiendo» still
repairs; help clears hold), truncation gate, conv smoke 7/7.

**Round 2 asks:** verify the implementation matches Round-1 amendments
(files inlined); rule on the E synthesis (shadow-with-flag) against
Patrick's directive and your latency concern — is shadow-default the right
reading, or should blocking be default despite +2.5s/turn?; confirm or
amend the promotion metrics for shadow→blocking; declare convergence or
name Round-3 items.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 05:48 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the shipped implementation so Round-2 countersigns rest on code, not summaries.Pulling the Round-1 exact amendment texts and the shipped implementation files next.Reading Round-1 exact texts and the shipped code sections in detail.Checking one more potential TTL/edge-case issue, then writing the append-ready Round-2 countersign.## Countersign Round 2 — adaptivity architecture (implementation verify + E synthesis)

**Date:** 2026-07-27 (review write-up; adjudication dated 2026-07-28 in-file)  
**Role:** Independent countersign against **inlined shipped code only** (not Claude’s claims).  
**Scope:** (1) A/B/C/F land check vs Round-1 exact texts, (2) E shadow-default vs Patrick’s directive + latency, (3) adversarial `signal_classifier.py`, (4) shadow→blocking promotion metrics, (5) CONVERGED / Round-3 list.

---

### 1) Round-1 amendment land check (exact-text fidelity)

| Item | File(s) | Verdict | Severity of drift |
|------|---------|---------|-------------------|
| **A** LEARNER UPTAKE first bullet | `executor.py` L793–799 | **MATCH** — character-for-character with Round-1 exact text | none |
| **A** Realize MODE rewrite | `executor.py` L800–802 | **MATCH** | none |
| **B** repair instructions | `modes.py` L1535–1551 | **LANDS (intent + substance)** | **LOW** cosmetic |
| **C** arm / TTL / clear | `session_memory.py` + `conv_session.py` | **LANDS (intent)** | **LOW** literal TTL wording; see below |
| **F** `help_request` regex | `observe.py` L2056–2070 | **LANDS (superset)** | **NONE** (one extra line is strict improvement) |
| **F** `select_mode` 0c guard | `modes.py` L1437–1452 | **MATCH** exact instructions | none |

#### A — **VERIFIED LANDED**
Standing orders open with LEARNER UPTAKE; realize bullet rewritten exactly as required. No drift.

#### B — **VERIFIED LANDED** (cosmetic only)
Shipped repair block preserves all Round-1 required clauses: UPTAKE FIRST step 0; re-ask only if intent still unanswered; language questions allowed/required; `forbid_new_topic` = no new scene/topic.

Drift (non-blocking):
- Step 2: “use it to bind the noun/meaning” vs “bind noun/meaning to it.”
- Step 3 adds “(shorter, high-frequency words).”
- Step 4 injects `simple_try` example via f-string.

**Residual prompt tension (LOW, not a B miss):** mode glossary in `AI_TUTOR_SYSTEM` still says comprehension_repair “re-ask the SAME question — NEVER a brand-new topic” without the uptake carve-out. Standing order A outranks, but long mode playbooks historically beat short glossary lines the other way. Prefer one-line glossary align in a polish PR; not a Round-3 blocker if A stays first.

#### C — **VERIFIED LANDED** (intent arithmetic OK; literal “at 0 clear” ≠ code)

**Arm (MATCH):**
```text
meta_comprehension AND NOT spanish_ok  → arm, ttl=1
help_request | topic_request           → clear, ttl=0
meta + spanish_ok                      → does not arm
```

**Eager clear (MATCH):** `conv_session.py` clears on `spanish_ok | topic_request | help_request` **before** `select_mode`.

**TTL walk (show work):**

| Event | `await` | `ttl` | `select_mode` sees hold? |
|-------|---------|-------|---------------------------|
| T2 pure “no entiendo” → arm | True | 1 | T2 repair from **meta signal** (correct) |
| T3 `note_learner`, no arm trigger | True | 1→0; clear only if `ttl < 0` → **still True** | **Yes — one following turn** |
| T4 `note_learner` | ttl 0→−1 → clear | False | No |

So shipped behavior = **exactly one following learner turn of sticky hold**, which is what Round-1 arithmetic required (“re-check once without multi-turn hijack”).  
Round-1 prose said “at 0 clear”; code clears at `ttl < 0`. **Behavior matches intent; prose was under-specified.** Severity: **LOW** (document, don’t “fix” the off-by-one into under-repair).

**Missing telemetry (LOW):** `SessionMemory.snapshot()` still omits `await_comprehension_ttl` — G metrics harder offline. Not a routing defect.

#### F — **VERIFIED LANDED** (superset of exact regex)
Exact Grok patterns present. **Extra** (safe widening):
```text
r"\bi\s+always\s+forget\s+how\s+to\b|"
```
covers T3-class “I always forget how to …” without requiring “say”. Guard order: after `topic_request`, before boredom/repair — **correct**. With hold armed + `help_request`, mode is `learner_help_request`, not repair.

**Ship gate for the original incident (code path, no LLM needed):** F+C alone closes session `20260727-231954` T3 if the regex hits. Verified by pattern inclusion of `i always forget how to say`.

---

### 2) E synthesis: shadow-default vs Patrick’s directive — explicit ruling

**Patrick (2026-07-28, mid-round, as inlined):** cheap classifier “kills regex”; “get away from regex”; regex-as-intent is smell.

**Claude shipped:** classifier **live by default in SHADOW** (parallel, zero added reply latency, ledger `classifier_shadow`, stale-hold clear); `SIGNAL_CLASSIFIER_BLOCKING=1` for pre-turn authority; measured **1.8–2.8 s/call** both providers; timeout default **2.5 s**.

#### Ruling

| Claim | Verdict |
|-------|---------|
| Shadow-default is a **faithful full implementation** of “get away from regex” for **routing** | **REJECT** |
| Shadow-default is the **correct production default given measured latency** | **COUNTERSIGN** |
| Blocking should be **default now** despite +1.8–2.8 s/turn | **REJECT** |
| “Live by default” as marketing for shadow | **AMEND language** — live for **audit + next-turn hold repair**, not for **this-turn routing** |

**Arithmetic (blocking as default — why REJECT):**

- Measured classify latency range: \(L \in [1.8, 2.8]\) s. Midpoint \(L_{mid} = (1.8+2.8)/2 = \mathbf{2.3}\) s.
- Round-1 promotion latency gate: added p95 ≤ **1.2** s.  
  \(L_{mid} - 1.2 = 1.1\) s **over budget**. Even the **floor** fails: \(1.8 - 1.2 = 0.6\) s over.
- Under uniform \(U[1.8, 2.8]\),  
  \(P(L > 2.5\text{s timeout}) = (2.8-2.5)/(2.8-1.8) = 0.3/1.0 = \mathbf{30\%}\) silent fallback to regex — so “blocking default” still routes ~30% of turns on the thing Patrick wants killed, while the other ~70% pay ~2+ s.
- Serial session tax: 40 learner turns × 2.3 s = **92 s** wall time added per session if blocking and successful every turn.
- Project already spent commits `7275bdc` / `2d160e0` removing tutor-path RTT. Re-adding ~2 s by default undoes that product work.

**On “faithful to Patrick” without product suicide:**

User override forces **E now**, not deferral. That is satisfied by: classifier **exists**, **on by default**, **instrumented**, **hold-correcting**, **one flag from authority**.  
User also implicitly requires a usable tutor (latency work is first-class). Shadow is the only synthesis that obeys **both** constraints **today**.

**What shadow does *not* do (do not overclaim):**
- Does **not** change `select_mode` inputs for the current turn (regex + hold still own routing).
- Stale-hold clear after shadow is **next-turn insurance**, not same-turn rescue. If regex misses help **and** hold is already false, shadow disagree is audit-only theater for that turn.
- Regex is **not killed** for intent; it remains authority until blocking/hybrid.

**Exact AMEND to adjudication language (replacement):**

```text
E status (2026-07-28 synthesis, Round-2 confirmed): Classifier is SHIPPED and
DEFAULT-ON in SHADOW mode only. Shadow = parallel classify + ledger audit +
optional next-turn hold clear. Shadow is NOT routing authority. Regex remains
routing authority until promotion gates fire (or SIGNAL_CLASSIFIER_BLOCKING=1
is set deliberately). This implements Patrick's "build E now" order under
measured 1.8–2.8s latency; it does NOT yet implement "kill regex for intent."
Blocking must stay opt-in until p95(classify) ≤ 1.2s (or a hybrid path lands).
```

---

### 3) Adversarial review: `tutor/signal_classifier.py`

#### What is sound
- Closed `INTENT_SIGNALS` vocabulary → keeps `select_mode` unit-testable.
- JSON-only system prompt; strip unknown labels.
- Timeout + broad `except` → `None` → regex fallback (fail-open for reply delivery).
- `non_understanding` → add `meta_comprehension`, drop `spanish_ok`, drop self: **aligns with C arm contract** (pure stuck, not grammar+production).
- Truncate learner to 2000 chars (DoS/cost bound).

#### Defects (ordered by severity)

**H1 — HIGH: default timeout (2.5 s) vs measured latency (1.8–2.8 s)**  
As above, ~30% timeout under uniform assumption → silent `None` → regex. Blocking mode then **looks** enabled while often not classifying.  
**AMEND:** set default `SIGNAL_CLASSIFIER_TIMEOUT_S` to **≥ 3.5** if any path is blocking; log timeout vs parse-fail vs empty as distinct outcomes (not one `None`).

**H2 — HIGH: module docstring false on latency**  
Doc says “~0.3–1s” and “can never block a reply.” Measured is 1.8–2.8 s; `SIGNAL_CLASSIFIER_BLOCKING` **does** block.  
**AMEND docstring** to measured range and dual-mode behavior. False latency claims will mis-set promotion decisions.

**M1 — MEDIUM: `non_understanding` forcibly discards `spanish_ok`**  
If the model emits both (mixed: “no entiendo… also *busco huevos*”), code **strips** production evidence → can arm repair / clear spanish_ok for routing. Prefer: if both present, **keep** `spanish_ok` and treat as `meta_comprehension` without arming pure non-understanding (or require mutual exclusivity in the prompt with a worked example).

**M2 — MEDIUM: shadow disagree metric is incomplete for promotion**  
```python
disagree = bool(sigs & {"help_request", "topic_request"}
                and mode in ("comprehension_repair", "form_focus"))
```
Measures only **over-repair/over-form when LLM sees help/topic**. Misses:
- false **positive** help when mode correctly stayed conversation,
- under-repair (LLM `meta`/`non_understanding`, mode conversation),
- help miss when mode conversation **and** realization failed (needs tutor-text audit, not mode alone).

**M3 — MEDIUM: same-turn blindness**  
Shadow cannot fix the ignored-help turn it audits. Hold clear helps T+1 only. Do not cite shadow as closing the incident class alone — **F does**.

**M4 — MEDIUM: silent failure**  
`except Exception: return None` / shadow `pass` — no structured fail counter in ledger. Promotion math needs `timeout_rate`, `parse_fail_rate`, `empty_rate`.

**L1 — LOW: `_call` annotated `-> set[str]` but returns `(set, usage dict)`**  
Runtime OK; type lie. Fix annotation to `tuple[set[str], dict[str, Any]]`.

**L2 — LOW: ThreadPoolExecutor per call**  
Creates/destroys a pool every classify. Prefer shared executor or `future` with timeout. Not a leak under daemon shadow threads that exit, but wasteful; rapid turns can pile daemon threads until each finishes (~2–3 s).

**L3 — LOW: double-clear race**  
Shadow `clear_comprehension_hold()` vs main-thread note/clear is boolean assign — benign. No lock needed for correctness of bool; possible lost update is still “cleared.”

**L4 — LOW: `boredom` in vocabulary, unused by `select_mode`**  
Dead signal for routing (boredom uses sheet affect). Either wire or drop to avoid false confidence in classifier coverage.

**L5 — LOW: prompt quality gaps**  
No negative examples for the incident classes:
- “I always forget how to say X” → `help_request` (not meta, not non_understanding)
- grammar Q with own Spanish → `meta_comprehension` + `spanish_ok`
- pure “huh?” / “no entiendo” → `non_understanding`  
Without few-shot, residual paraphrase errors will dominate promotion metrics.

**Prompt AMEND (exact addition to `_SYSTEM` after Definitions):**

```text
Examples (signals only):
- "I always forget how to say searching" → ["help_request"]
- "can we talk about food instead?" → ["topic_request"]
- "no entiendo" → ["non_understanding"]
- "Come esta usted. The usted makes it formal - why not estas?" → ["meta_comprehension","spanish_ok"]
- "buenas tardes. Yo busco huevos." → ["spanish_ok"]
Do NOT label help_request as non_understanding. Do NOT drop spanish_ok when they produced real Spanish and also asked a grammar question.
```

---

### 4) Shadow → blocking promotion metrics — **AMEND** (do not confirm Claude’s implied bar alone)

Round-1 pre-registered bar still stands; **expand** because shadow ledger `disagree` is not precision/recall.

**Frozen promotion rule (exact replacement):**

```text
Promote SIGNAL_CLASSIFIER_BLOCKING default (or make blocking the code default) ONLY when ALL hold on a frozen sample:

Sample
  n_shadow ≥ 100 learner turns with classifier_shadow events, AND
  n_labeled ≥ 80 of those with blind human tags (help|topic|non_understand|none),
  collected after 2026-07-28 A+B+C+F ship (not the pre-patch baseline alone).

Quality (vs human labels on the same utterance)
  P_intent = precision of LLM labels on help_request ∪ topic_request ∪ non_understanding
             ≥ 0.90
  R_resid  = recall of LLM on the subset where human∈{help,topic,non_understand}
             AND regex probe_signals lacked that intent label
             ≥ 0.90
  FPR_help = P(LLM help_request | human none) ≤ 0.05

Reliability
  timeout_rate ≤ 0.05  (must log timeouts distinct from parse fail)
  parse_fail_rate ≤ 0.02

Latency (user-perceived path)
  p95(classify wall) ≤ 1.2 s   OR   hybrid path lands where classify starts at
  turn entry and the tutor call does not wait unless regex intent is empty/ambiguous
  (hybrid still must document p95 wait ≤ 1.2 s on the wait branch).

Product safety
  With blocking on a canary (≥40 turns): ignore rate I ≤ 0.05 and no +0.05 absolute
  regression on gate fault rate or hard-break rate vs shadow-only baseline.

If any gate fails: keep shadow default; expand F lexicon / classifier few-shot from
miss logs; do NOT flip default blocking on author preference.
```

**Worked example:** 100 labeled intent-positive turns, 12 LLM misses on residual → \(R_{resid}=88/100=0.88 < 0.90\) → **no promote**.  
Latency: measured floor 1.8 s > 1.2 s → **no promote on latency alone today**, regardless of quality.

---

### 5) CONVERGED?

**NOT fully CONVERGED.** A/B/C/F + shadow-E **infra** are ready to freeze as the adaptivity baseline. E **authority** and classifier production hardness are open.

#### Round-3 items (precise; only these)

1. **Doc/claim hygiene (must):** replace false “0.3–1s / never blocks” classifier docs; adopt Round-2 E status wording (shadow ≠ routing authority).  
2. **Classifier reliability (should before any promote):** timeout default ≥ 3.5 s when blocking path used; ledger fields `timeout|parse_fail|ok|empty`; few-shot examples as above; fix `_call` return type.  
3. **`non_understanding` ⊕ `spanish_ok` policy (should):** stop blindly discarding `spanish_ok`.  
4. **Promotion sample collection (must for E authority):** start counting toward n≥100 shadow + n≥80 labeled under frozen metrics above — no early default flip.  
5. **Optional hybrid (only if latency stays >1.2 s):** start classify at turn entry in parallel with prep; wait only when regex lacks help/topic/meta — keeps Patrick’s “kill regex” trajectory without +2.3 s every turn. Spec in Round 3 if quality gates pass and latency still fails.  
6. **D remains deferred** — no change; limited `learner_priority` still metric-gated Phase-2, not Round-3 required if F+A+B hold \(I\).  
7. **Glossary polish (optional):** one-line comprehension_repair blurb in `AI_TUTOR_SYSTEM` to mention uptake-first (align with B).

#### What is CONVERGED (may stop debating)

| Decision | Status |
|----------|--------|
| Structural claim (code owns legality/budget; uptake authority needed perception) | **FROZEN** |
| Ship A+B+C+F | **FROZEN — landed** |
| Full model-chosen modes (full D) | **REJECT frozen** |
| Limited D | **Deferred, metric-gated** |
| E exists now (user override) | **FROZEN** |
| E default = shadow, not blocking | **FROZEN until promotion gates** |
| Blocking default at 1.8–2.8 s | **REJECT frozen** |

---

### Summary verdicts (append-scannable)

| # | Item | Ruling |
|---|------|--------|
| 1A | Standing order + realize bullet | **COUNTERSIGN landed** (exact) |
| 1B | Repair uptake-first | **COUNTERSIGN landed** (cosmetic drift only) |
| 1C | Arm/TTL/eager-clear | **COUNTERSIGN landed** (TTL intent OK; prose “at 0” ≠ code) |
| 1F | help_request + guard | **COUNTERSIGN landed** (regex superset OK) |
| 2 | Shadow-default vs Patrick | **COUNTERSIGN as interim production default; REJECT as full “kill regex”; REJECT blocking-default now** |
| 3 | `signal_classifier.py` | **AMEND required** (timeout math, docs, mapping, metrics, few-shot) — not a ship-stop for shadow |
| 4 | Promotion metrics | **AMEND** to full quality+reliability+latency+canary gate set above |
| 5 | Convergence | **NOT CONVERGED** on E authority; **CONVERGED** on A–C+F + shadow-E default |

**Bottom line:** The T3 ignore class is fixed on the **code** path (F+C+A+B). The classifier is correctly **not** on the critical path yet, because measured classify cost is **1.8–2.8 s** and fails the **1.2 s** promote bar by **≥0.6 s even at the floor**. Calling shadow “live routing” would be false; calling blocking default “what Patrick ordered” would be true to one sentence and false to the product. Hold the line: **shadow default until arithmetic promotes it.**

— End Countersign Round 2 —

---

## Adjudication of Round 2 (Claude, 2026-07-28) + classifier model benchmark

- **Land check — accepted as verified** (A/B exact, C intent-correct with
  TTL prose noted, F superset). No action beyond items below.
- **E language AMEND — ACCEPTED verbatim.** Adopted status wording:
  classifier is SHIPPED and DEFAULT-ON in SHADOW only; shadow is NOT
  routing authority; regex remains routing authority until promotion gates
  fire or SIGNAL_CLASSIFIER_BLOCKING=1 is set deliberately. "Live by
  default" claims are hereby scoped to audit + next-turn hold repair.
- **Round-3 must/should items — LANDED this round:**
  - H2 docstring corrected to measured latencies + dual-mode behavior.
  - L5 few-shot examples added to the classifier prompt (Grok's exact
    block, incl. the incident-class negatives).
  - M1 fixed: non_understanding no longer discards spanish_ok (mixed
    production+stuck keeps the production evidence).
  - M4/H1 telemetry: classify outcomes now distinct
    (ok/empty/timeout/error) and recorded on classifier_shadow ledger
    events; timeout default is 8s (≥3.5 required for blocking).
  - L1 type annotation fixed; snapshot() now exposes await_comprehension_ttl;
    glossary comprehension_repair line aligned with uptake-first (item 7).
- **NEW EVIDENCE (Patrick's question: "do we need a reasoning model for a
  classifier?") — NO.** Benchmark 2026-07-28, same fixtures:
  - gemini-flash-lite-latest (non-reasoning): 0.82–1.04s, 5/5 correct
    (incl. meta+spanish_ok on the mixed grammar question, help_request on
    the T3 phrasing). p95 ≈ 1.04s — UNDER the frozen 1.2s latency gate.
  - grok-3-mini: 2.4–2.7s (reasoning tokens; effort=low no help).
  - gemini-3.6-flash: 1.8–2.8s (thinking ate small budgets entirely).
  Default classifier model switched to gemini-flash-lite-latest (env
  override preserved). Consequence: the promotion latency gate now PASSES;
  promotion to blocking awaits ONLY the frozen quality sample
  (n_shadow ≥ 100, n_labeled ≥ 80, P_intent ≥ 0.90, R_resid ≥ 0.90,
  FPR_help ≤ 0.05, reliability gates) — per protocol, no default flip on
  a 5-utterance benchmark. Pricing for the lite tier added as ESTIMATE
  ($0.10/$0.40) pending verification.
- **M2 (disagree metric incompleteness) — acknowledged, deferred** to the
  labeling phase: the ledger now carries signals+routed_mode+outcome per
  turn, sufficient to compute the full confusion matrix offline once human
  labels exist.

**Round 3 asks:** verify this round's fixes (files inlined); verify or
correct the lite-tier price estimate (web); rule on the model swap
(non-reasoning lite as default classifier — consistent with Patrick's
directive?); declare the A–F + shadow-E infrastructure CONVERGED if
nothing blocking remains, leaving only the pre-registered data collection
for E authority.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 05:59 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the inlined review materials, then verify Round-3 landings against code and web-check the pricing claim.The sandbox is empty; I'll verify Round-3 claims against the live repo and pull the review's Round-2/3 sections.Next I'll verify each Round-3 must/should landing and check Gemini Flash Lite pricing.## Countersign Round 3 — adaptivity architecture (final verification)

**Date:** 2026-07-27 (write-up; proposal/adjudication dated 2026-07-28 in-file)  
**Role:** Independent final verification; code-checked against live `ml_teacher` main (`tutor/signal_classifier.py`, `tutor/config.py`, `tutor/costs.py`, `tutor/session_memory.py`, `tutor/conv_session.py`, `tutor/executor.py`, `tutor/observe.py`).  
**Pricing source:** Google Gemini Developer API pricing page, crawled 2026-07-28.

---

### 1) Round-3 must/should land check (item-by-item)

| Item | Claimed fix | Code locus | Verdict |
|------|-------------|------------|---------|
| **H2 docstring honesty** | Measured latencies + dual-mode | `signal_classifier.py` L10–17 | **LANDS** — documents gemini-flash-lite-latest 0.8–1.1s default; shadow vs `SIGNAL_CLASSIFIER_BLOCKING=1`; timeout → regex alone |
| **L5 few-shot** | Incident-class examples in prompt | `_SYSTEM` L55–61 | **LANDS** — includes T3-class `"I always forget how to say searching" → help_request`, mixed grammar+`spanish_ok`, pure production, non_understanding carve-outs |
| **M1 spanish_ok retention** | `non_understanding` must not discard production | L97–100 | **LANDS** — adds `meta_comprehension`, discards only `non_understanding`; comment + code keep `spanish_ok` |
| **M4/H1 outcome telemetry** | `ok` / `empty` / `timeout` / `error` on ledger | `classify_signals` L123–132; `conv_session._spawn_signal_shadow` L544 | **LANDS (with residual)** — shadow events record `outcome`; timeout/error distinct. Residual below |
| **Timeout default ≥ 3.5s** | Blocking-safe | `config.SIGNAL_CLASSIFIER_TIMEOUT_S` default `"8.0"` | **LANDS** — 8.0 ≥ 3.5 (8.0 − 3.5 = 4.5s headroom) |
| **TTL in snapshot** | expose `await_comprehension_ttl` | `session_memory.snapshot` L220–221 | **LANDS** |
| **Glossary align** | comprehension_repair uptake-first | `executor.py` L126–129 + standing order L133–138 | **LANDS** — glossary says answer question FIRST; standing order still outranks modes |
| **Default model swap** | `gemini-flash-lite-latest` when Gemini key present | `config._signal_classifier_default` L100–108 | **LANDS** — env override preserved; grok-3-mini only if no Gemini key |

**Arm/TTL/eager-clear re-check (not re-opened, sanity only):**

- Arm: `meta_comprehension` ∧ ¬`spanish_ok` → `ttl=1` (`session_memory.py` L87–89)  
- Eager clear: `spanish_ok | topic_request | help_request` before `select_mode` (`conv_session.py` L847–849)  
- F regex still ships incident phrasing including `i always forget how to say` (`observe.py` L109–123)

**Residual (LOW, not architecture-blocking):**

- **Parse-fail vs empty:** if the model returns non-JSON, `_call` returns empty set and `classify_signals` labels `outcome="empty"`, not a distinct `parse_fail`. Round-2 asked for `timeout|parse_fail|ok|empty`. Promotion reliability math will **under-count model/parse failures** and **over-count legitimate empty-label turns**.  
  **AMEND (exact):** in `_call`, when `_JSON_RE` fails (or `json.loads` fails), return `set(), {..., "outcome_hint": "parse_fail"}` and in `classify_signals` prefer that over the `ok if out else empty` ternary. Keep `timeout` / `error` as today.
- **Blocking latency comment stale:** `config.py` L117–118 still says blocking adds “~2–3s/turn” with grok/3.6 numbers; with the new default lite model, measured wall is ~0.8–1.1s. Docstring-only; fix when convenient.

---

### 2) Pricing verification — **AMEND (estimate was wrong)**

Claude’s ESTIMATE: **$0.10 / $0.40 per 1M** for `gemini-flash-lite-latest` / `gemini-3.1-flash-lite` (2.5-flash-lite era).

**Official paid-tier rates (ai.google.dev, as of 2026-07-28):**

| Model ID | Input / 1M | Output / 1M |
|----------|------------|-------------|
| `gemini-2.5-flash-lite` | **$0.10** | **$0.40** |
| `gemini-3.1-flash-lite` | **$0.25** (text/image/video); audio $0.50 | **$1.50** |
| `gemini-3.5-flash-lite` | **$0.30** | **$2.50** |

`gemini-flash-lite-latest` is a **hot-swapped alias** (Google: points at the latest Flash-Lite release with ~2-week notice before swaps). After **2026-07-21** GA of 3.5 Flash-Lite, treating “latest” as $0.10/$0.40 is incorrect for cost accounting.

**Arithmetic (per classify call, ~800 in + 40 out tokens):**

- Claimed $0.10/$0.40:  
  \(800 \times 0.10 / 10^6 + 40 \times 0.40 / 10^6 = 0.000080 + 0.000016 = \$0.000096\)
- Official 3.1 Flash-Lite $0.25/$1.50:  
  \(800 \times 0.25 / 10^6 + 40 \times 1.50 / 10^6 = 0.000200 + 0.000060 = \$0.000260\)  
  → **2.71×** the claimed per-call cost (\(0.000260 / 0.000096\))
- Official 3.5 Flash-Lite $0.30/$2.50:  
  \(800 \times 0.30 / 10^6 + 40 \times 2.50 / 10^6 = 0.000240 + 0.000100 = \$0.000340\)  
  → **3.54×** claimed

Still well under **$0.001/call** — **not** a product or promotion blocker. **Is** a ledger correctness bug in `tutor/costs.py` L64–68.

**Exact replacement for `tutor/costs.py` PRICING entries:**

```python
    # Intent classifier — official Gemini Developer API paid tier (2026-07-28)
    # https://ai.google.dev/gemini-api/docs/pricing
    "gemini-3.1-flash-lite": {"input": 0.25, "input_cached": 0.025, "output": 1.50},
    "gemini-3.5-flash-lite": {"input": 0.30, "input_cached": 0.03, "output": 2.50},
    # Alias hot-swaps; price at current GA lite (3.5) until pin is forced
    "gemini-flash-lite-latest": {"input": 0.30, "input_cached": 0.03, "output": 2.50},
    # Legacy 2.5 lite (if ever pinned for cost floors)
    "gemini-2.5-flash-lite": {"input": 0.10, "input_cached": 0.01, "output": 0.40},
```

Optional hardening: pin `SIGNAL_CLASSIFIER_MODEL` default to `gemini-3.1-flash-lite` or `gemini-3.5-flash-lite` (stable ID) instead of `…-latest` so latency/quality fixtures do not silently change on Google’s 2-week alias notice. **Not required for CONVERGED.**

---

### 3) Default classifier: grok-3-mini → gemini-flash-lite-latest

**COUNTERSIGN the swap for the SHADOW default.**

| Criterion | Ruling | Arithmetic / evidence |
|-----------|--------|------------------------|
| Faithful to “LLM not regex”? | **YES** | Intent still judged by a side LLM; regex remains fallback + surface-form (`observe.py` help/topic patterns). Patrick’s directive was modality (semantic classifier > regex smell), not a brand lock to Grok. |
| Needs reasoning model? | **NO** | Adjudication 5/5 fixtures on non-reasoning lite; reasoning models add wall time without required chain-of-thought for a 7-label JSON tag. |
| Latency gate (frozen p95 ≤ 1.2s) | **PASS for lite; FAIL for grok-3-mini** | Lite max 1.04 < 1.2 (margin \(1.20 - 1.04 = 0.16\)s). Grok min 2.4 > 1.2 (\(2.4 / 1.2 = 2.0\times\) over gate). |
| Authority scope | **Correct** | Default remains **shadow** (`SIGNAL_CLASSIFIER_BLOCKING` false). Routing authority still regex (+ F) until promotion gates fire. Model swap does **not** promote E. |
| 5/5 fixtures as promotion evidence? | **Insufficient alone** | Protocol still requires \(n_{shadow} \ge 100\), \(n_{labeled} \ge 80\), \(P_{intent} \ge 0.90\), \(R_{resid} \ge 0.90\), \(FPR_{help} \le 0.05\). 5 fixtures decide “which model to *measure* with,” not “flip blocking.” |

**Do not COUNTERSIGN** flipping `SIGNAL_CLASSIFIER_BLOCKING=1` by default on this evidence.

---

### 4) CONVERGED?

**YES — CONVERGED on A–F + shadow-E infrastructure.**

Nothing blocking remains on the adaptivity architecture review. E **routing authority** stays closed until pre-registered data collection passes.

#### Frozen (stop debating)

- **A** Learner-uptake standing order (outranks modes)  
- **B** Repair playbook carve-out (answer contained question first)  
- **C** Arm only pure meta; TTL=1-following-turn semantics; eager clears  
- **F** `help_request` regex + incident phrasing  
- **D** full model-chosen modes — **out of scope / not shipped** (limited-D not required given A+B+C+F+shadow-E)  
- **E infrastructure:** shadow-default LLM classifier, ledger (`signals`, `routed_mode`, `disagree`, `outcome`), next-turn hold repair on help/topic/spanish_ok, blocking opt-in via env, promotion metrics protocol  

#### Explicitly open (only these)

1. **Pre-registered E promotion sample** (sole architecture gate left):  
   \(n_{shadow} \ge 100\), \(n_{labeled} \ge 80\), \(P_{intent} \ge 0.90\), \(R_{resid} \ge 0.90\), \(FPR_{help} \le 0.05\), plus reliability (timeout/error rates). Until green: **regex remains routing authority**; shadow audits + hold repair only.  
2. **Ops polish (non-blocking):** fix `costs.py` lite pricing (exact table above); optional distinct `parse_fail` outcome; optional pin stable model ID vs `-latest`; refresh blocking-latency comment.

#### Not open / do not re-litigate without new incident data

- Whether A+B+C+F ship  
- Whether shadow-E is the right default authority posture  
- Whether a reasoning model is required for intent classification (settled: no, on 2026-07-28 fixture bench + latency arithmetic)

---

### Verdict summary

| Ask | Ruling |
|-----|--------|
| Round-3 landings | **COUNTERSIGN** (all must/should landed; 1 LOW residual on parse_fail labeling) |
| Pricing $0.10/$0.40 | **AMEND** → use official 3.1 **$0.25/$1.50** and 3.5 **$0.30/$2.50**; alias “latest” ≠ 2.5 rates |
| Default model → gemini-flash-lite-latest | **COUNTERSIGN** for shadow default; faithful to LLM-not-regex; do not auto-promote blocking |
| CONVERGED? | **YES** on A–F + shadow-E infra; open only promotion data collection (+ optional pricing/parse_fail polish) |

— End Countersign Round 3 —

---

## Final adjudication — Round 3 (Claude, 2026-07-28): CONVERGED

- **Round-3 landings — verified by Grok; accepted.**
- **Pricing AMEND — ACCEPTED; my $0.10/$0.40 estimate was ~3x low.** Grok's
  official table applied verbatim to tutor/costs.py (3.1-lite $0.25/$1.50,
  3.5-lite $0.30/$2.50, -latest priced at current GA lite, 2.5-lite legacy
  entry). Per-call cost remains < $0.001 — ledger correctness fix, not a
  product concern.
- **parse_fail outcome — LANDED** (distinct from empty/timeout/error in
  _call + classify_signals + shadow ledger events).
- **Stale blocking-latency comment — refreshed** to measured lite numbers.
- **Model-ID pin — declined for now** (alias measured fastest; ledger
  prices the alias at current-GA rates; revisit if Google's alias swap
  shifts fixtures).
- **Default classifier swap — COUNTERSIGNED** (faithful to the LLM-not-
  regex directive; "do we need a reasoning model?" settled: NO).

**FROZEN:** A, B, C, F; full-D rejection; shadow-E infrastructure and
default posture; the promotion metrics protocol.
**OPEN (only):** the pre-registered E-promotion sample (n_shadow ≥ 100,
n_labeled ≥ 80, quality + reliability gates) — accumulating automatically
in logs/costs.jsonl during normal practice.

**Review closed after 3 rounds: propose → countersign → adjudicate ×3,
two user directives incorporated on the record (E-now override; no-
reasoning-model question), one Claude pricing error caught and fixed.**
