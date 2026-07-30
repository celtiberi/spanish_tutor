# Best practices for AI-agent systems — earned, not aspirational

**Written 2026-07-30** from one week of building ml_teacher (conversational
Spanish tutor: LLM realization under code authority) and a deep survey of
the sibling repo **elfric** (planner + small-rounds pipeline; measured
94% call / 97% cost / 83% latency reduction on its own fixture). Every
practice below has an incident, a commit, or a measured number behind it.
Sibling notes: docs/from-the-stocks-repo-2026-07-28.md (their method,
which seeded several of ours); this file is the return letter's long form.

---

## 1. Architecture: who decides, who performs, who verifies

1.1 **Code owns decisions; the model owns performance; the gate owns
truth.** (PEDAGOGY §1.1/§1.1a.) The LLM never chooses the syllabus, the
budgets, or the schedule — it realizes one move under declared
constraints. Every incident this week where "the AI did something weird"
traced to a place where authority had silently leaked to the model or to
stale agenda state, never to the model being insufficiently instructed.

1.2 **An enforcement layer that cannot refuse is telemetry.** Our output
gate detected a repeated-probe defect twice, repaired once, failed, and
shipped the bad turn anyway with a log note — "fail open" was an
unexamined policy. The fix is a FLOOR: strip the offending structured
part and re-verify the remainder; if still illegal, ship NOTHING plus an
honest non-teaching hold. Never launder a known-bad payload because the
retry budget ran out. Corollary: make the fail-open/fail-closed decision
explicitly for every verifier you build.

1.3 **Peripherals render the exchange, never the agenda.** Anything
user-visible that claims to be "about now" (images, side panels, status
cards) must be confirmed against a projection of what ACTUALLY happened
— pure functions of (inputs, realized output, typed events) — not
against what some planner intended. Pre-computed artifacts are
candidates; a settlement/commit phase confirms or drops them (drops
logged, never silent). Incidents: a scene agenda attached a coffee image
while the learner discussed their house; a "next best" pointer pinned a
card to me-llamo through a gender-agreement exchange.

1.4 **Derived state, not shared state.** The user's veto of a shared
context object was right: shared bags accrete writers and precedence
rules (our one stashed field had grown both within a day). The modern
shape: per-consumer PROJECTIONS (narrow frozen views, one derive
function each), a single-assignment render record replaced whole each
cycle, and an INPUT LAW enforced by signature pins + AST lint — the
projection module literally cannot reference agenda state, and a test
walks its AST to prove it. Prior art named: CQRS read models, Elm/React
commit phase, ECS simulate→resolve→render.

1.5 **Two state machines beat one clever dict.** Schedule axis and
ability axis (or any two concerns that must never write each other) get
separate allowlists with a MIRROR guard: A's writer restores B's fields
even on attempted writes, and B's writer raises if A's fields moved.
One-direction protection is half a lock.

---

## 2. Context engineering (the elfric findings + our replication)

2.1 **Declare, don't re-discover.** The planner (LLM or code) emits a
typed artifact whose inputs are DECLARED (keys, docs, prior outputs);
plain code resolves the declarations; nothing else enters the round.
elfric: one ~2.5k-token planning call replaced three downstream
inference passes; 49% of production work then ran as single zero-tool
calls chosen by a four-line deterministic strategy function.

2.2 **Context rot is real and measured.** elfric's compressor doctrine:
"focused prompts (~300 tokens) significantly outperform full prompts;
models degrade with irrelevant context." Our replication: a tutor
receiving ~50k tokens/turn failed its own compliance gate on 4/6 turns;
the ~4.5k-token brief-context arm failed 2/12 — best of all arms at 0.1×
the tokens. And the pure-position control (same 50k, constraints moved
to the tail) did NOT help, while a compact STRUCTURED constraints block
at the tail halved failures: legibility beats both volume and position.

2.3 **Budget premier-model tokens, not call count.** elfric relearned
this explicitly (commit cbdccce): cheap-model calls are effectively
free; spend unlimited cheap calls (compression, curation, filtering,
scoring) to shrink expensive-model input. "Minimize LLM calls" is the
wrong metric and will steer you to worse architectures.

2.4 **Fresh context per round; facts, not transcripts, across rounds.**
Rebuild a two-message payload every round: byte-stable system prefix
(cache-shaped: all volatility at the tail, explicit cache breakpoints) +
task + compacted findings (last-3 full, older one-sentence summaries,
hard cap). Durable memory is curated FACTS with TTLs and
pointers-to-canonical-source — never replayed transcripts, and no
raw-transcript fallback path at all.

2.5 **Constrain output SHAPE, never output tokens.** Hard token caps
truncate legitimate answers (elfric rejected them after trying); a
format/schema directive limits size naturally. Our version: structured
reply parts + a parser, with the part-contract enforced by the gate.

2.6 **Caps and stopping belong to the orchestrator.** Typed round caps
by task class, virtual tool budgets with escalating urgency, repetition
hashing (identical call+args blocked after N), one cheap extension vote
— the model never decides when it is done trying.

2.7 **Over-narrow context fails silently and confidently.** elfric's
routing once skipped a data source and answered beautifully anyway; the
fix was a new DECLARED input kind, not a wider prompt. Make narrow
context safe with machine-checked provenance (citations validated
against resolved blocks; unresolved inputs rendered as explicit
<UNRESOLVED>, forbidden to cite) — or in our stack, with a gate that
judges the behavior itself.

2.8 **The INTERFACE is part of the completeness schema.** Our diet's
first live run failed 10/12 turns because the reply-format contract
lived in the prose we cut — the law census listed laws; nobody listed
the interface, and the completeness lint blessed the hole because the
schema itself was missing the member. When you diet a context, enumerate
floor members including every protocol/format contract, version the
schema, and lint against it. "Token pressure is never a legal omission
reason" belongs in the law text.

2.9 **Same-cycle dynamic resolution.** When live input mentions
something outside the prepared slice, resolve it into THIS cycle's
context (code-side detection + injection), not the next one — deferring
violates whatever your uptake/responsiveness contract is.

2.10 **The planner must not name what it cannot know.** elfric's top
live failure: plans referencing downstream output fields that never
existed (output_shape was prose, not schema). Validate every planner
artifact against the real inventory before any round runs.

---

## 3. Verification culture

3.1 **An adversarial AI counterpart is the discovery engine; scripted
tests are only the regression engine.** Our AI-student harness (an LLM
playing the learner against the real system, plus MECHANICAL post-checks
on transcripts: repetition/fixation Jaccard, ship-failure counts,
probe-on-known) caught three distinct defect classes in one night — a
fixation loop the user had to find manually before the harness existed,
the missing-interface hole above, and the baseline proof that full
context wasn't buying compliance. Keep such harnesses alive; ours had
been deleted in a refactor sweep as "legacy" and the gap cost us. Run on
every behavior-touching change + nightly; wire regressions into the
promotion bar.

3.2 **Pre-register or you are rationalizing.** Freeze metrics, N,
promotion AND kill bounds, and the falsifier ORDER before data. Label
small-N results DIRECTIONAL with the arithmetic shown (our "P2 halved
failures" was z≈0.9 — noise); never drop a control arm after seeing
data; cheap isolating controls (position-at-same-tokens) run BEFORE
expensive rebuilds so wins are attributable.

3.3 **Characterization goldens make refactors safe.** Byte-pinned golden
artifacts + a fake model client; every regeneration individually audited
and justified in the change; known-bug pins flip only WITH the fix.
Census tests (pinned counts of stages/events/fields) turn silent drift
into conscious decisions.

3.4 **Executed proofs beat prose.** In dual-AI review, claims get
settled by running code (our incident replays, Grok's probe of a
status-string loophole, our replay showing Grok's own acceptance test
failing). "I ran it and here is the output" ends debates that paragraphs
prolong.

3.5 **Dual-AI countersign, with teeth.** Propose → adversarial
countersign (exact-replacement AMENDs only) → adjudicate with reasons →
converge; append every round to one rolling document so the debate is
auditable. Expect and want a nonzero rejection rate — all-countersigns
means steered prompts. The reviewer catching YOUR sophistry (our
"re-role, not truncation" branding) is the system working. And an
aborted round is a feature: a reviewer that refuses to review an empty
subject rather than inventing one is protecting the trail's integrity.

3.6 **Silence records nothing; unknown is not neutral.** Evidence-gated
promotions only; a crashed check reports UNCHECKED, not clean; unpriced
costs are FLAGGED, not $0; display bands never trust status strings —
re-derive from the gate arithmetic every time.

---

## 4. Governance

4.1 **A constitution with an enforcement map.** One law file; every law
carries its incident and its enforcement (mechanical column + judgment
column); a law with an empty mechanical column is itself a reportable
defect. Reviews that change behavior are not CLOSED until the law
paragraph lands (promotion gate). Debts are registered with dated
revisit bounds, not remembered.

4.2 **Reserve USER-ONLY powers and honor them.** Some laws (privacy,
context completeness) only the human may reopen; dual-AI agreement
explicitly cannot. This kept our biggest architecture change honest: the
analysis converged, then STOPPED for ratification.

4.3 **Fix generators, not instances** (a stocks law we now hold as
proven): a patch to the symptom leaves the machine that produced it.
The repeated-probe bug got a gate floor (instance class) AND a context
architecture (generator) — in that order, both countersigned.

4.4 **Check for an existing mechanism before proposing a new one**
(elfric's standing rule, learned by deleting 4,300 lines of shadow
pipeline). Our version: the "planner" we almost added already existed
as code routers; the build became a packaging format instead of a second
authority.

---

## 5. Operational hygiene for agent-running machines

5.1 **Never content-match pkill while agent processes run.** An agent's
argv contains your prompts, file listings, and docs — we SIGTERM-killed
a live review round twice: once via a regex-dot wildcard, once because
the bracket-escaped pattern matched the literal restart command quoted
in the agent's own briefing. Kill by pidfile written from `$!` at spawn;
verify with `ps -p` before killing; never derive pidfiles from pgrep
(it matched the running agent's argv too).

5.2 **Isolate every harness's ledgers.** Simulation/eval traffic writes
to per-run sheet/progress/cost paths, never production files — our
progress rail once celebrated an operator's verification chat as learner
milestones, and append-only ledgers made the cleanup honest (retraction
rows, not deletions).

5.3 **Long experiments: detach + incremental persistence.** nohup +
pidfile + a driver that persists per-arm results as it goes, so a crash
keeps completed arms. Cache-bust versioned static assets on every edit;
health endpoints report code staleness.

---

## 6. The one-paragraph version

Give code the decisions, the model the performance, and the verifier a
floor it can actually enforce. Feed the model a small, legible,
schema-complete context assembled per-cycle from declared inputs — and
lint completeness, because the hole you didn't name is the one that
ships. Let an adversarial AI counterpart hammer the system continuously,
pre-register every experiment, prove claims by execution, and put a
second AI in the review loop with permission to call your best framing
sophistry. Write the laws down with their incidents, map each law to its
enforcement, reserve the biggest levers for the human — and never, ever
pkill by pattern while your colleagues' argv is full of your own
documentation.
