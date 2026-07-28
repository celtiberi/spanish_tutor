

---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-26 20:41 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll research TBLT, WTC/anxiety, and conversational-AI engagement evidence, then independently adjudicate the four product choices against that literature—not against the inlined author's framing.# Independent review — TASK DESIGN, MOTIVATION, AND AFFECT  
**Author:** Grok (independent second author)  
**Date pinned:** 2026-07-26  
**Project:** ml_teacher  
**Dimension:** Task design, motivation, and affect (A1 adult 1:1 conversational Spanish tutor)  
**Stance:** Contrarian second perspective. Inlined docs treated as *data*, not authority. Claims checked against SLA/TBLT/WTC literature and recent chatbot meta-evidence.

---

## 1. My own picture (dated pins)

**Pin A — What a “task” is (canonical, not product-local).**  
As of the literature state I am using (Ellis 2003/2009; Long TBLT; Nunan pedagogic vs real-world), a **task** is meaning-primary work with a non-linguistic outcome, gap-driven language use, and evaluable completion. An **exercise** is form display without communicative outcome. Spot-the-difference / info-gap can be *interactionally* authentic without being *situationally* authentic; restaurant ordering is both. Opinion chat without a shared outcome is the *weakest* of the classic Pica–Kanagy–Falodun task types for acquisition pressure.

**Pin B — A1 adults in 1:1.**  
True beginners and false beginners need **input-based and tightly scaffolded tasks** before free production-heavy “conversation as vehicle” (Ellis / Shintani line: TBLT works at beginner level when tasks do not *require* production). A1 is not “small talk until forms appear.” Production without lexis and formulaic frames predictably raises **foreign language anxiety** and drops **willingness to communicate (WTC)**.

**Pin C — Affect that actually predicts speaking.**  
MacIntyre’s WTC model (1998 → dynamic extensions): readiness to enter L2 discourse is multi-layered. Empirically, **anxiety is the strongest negative predictor of WTC**; **enjoyment / interesting topics / perceived competence** are positive levers. Boredom (FLB) is a real, measurable construct with a **small negative** link to achievement in recent meta-analytic work—not a vibes label. “Energy / limited time” is product ops, not SLA core.

**Pin D — Conversational AI tutors (2024–2025 evidence band).**  
Lyu et al. (2025) meta-analysis of chatbots for L2: **overall Hedges’ *g* = 0.608** (medium); affective outcomes **g = 0.645**; learning outcomes **g = 0.590** (medium). That supports *some* chatbot benefit on both affect and learning—not proof that open chat with opportunistic scene exits is optimal, nor that two affect labels suffice. Product/community reports of pure conversational AI also flag **novelty decay** (days to ~30 days) when pedagogy is thin and goals are invisible.

**Pin E — ml_teacher’s shipped design (from inlined `docs/system-overview.md`, status as of 2026-07-26).**  
Conversation-default + budgeted hard modes (`form_focus` / hard `association` blocked while `turns_since_hard_break < 3`) + scenes as open goals with exit predicates + affect = `{energy, boredom_risk}` + adult boat/café persona + identity hooks (sister, Río Dulce) + every turn must carry model/try/recast. That is a **task-supported conversational system with reactive FonF**, not full Long-style TBLT syllabus from needs analysis.

---

## 2. Verify / refute table (load-bearing claims in the inlined overview + the four choices)

| # | Claim / choice (as data) | Ruling | Evidence / arithmetic | Implication |
|---|---|---|---|---|
| 1 | “Conversation is the vehicle; teaching is knowing when to break…” | **Partial support** | Aligns with Long **focus-on-form** (form inside meaning) and CLT meaning primacy. Overstates if “vehicle” means free chat substitutes for tasks with outcomes. | Keep vehicle metaphor; do not treat it as TBLT completion. |
| 2 | Scenes = open goals + exit predicates, satisfied opportunistically (not scripted cutscenes) — **choice (a)** | **Partial support / partial reject** | Exit predicates ≈ task *outcome* (good). Opportunistic multi-goal without sequencing rejects **Robinson Cognition Hypothesis / SSARC** (sequence simple → complex on resource-directing dimensions). Free talk ≈ opinion-gap (Pica et al.: least acquisition-promoting vs jigsaw/info-gap). | Scenes need *convergent* sub-goals and complexity order, not only open predicates. |
| 3 | Conversation default + budgeted hard breaks (`turns_since_hard_break < 3`) — **choice (b)** | **Mostly support; number is ad hoc** | FonF reactive breaks are well-supported. **Budget = 3 turns** has no cited SLA pin: 3 is a product constant, not a retrieval/spacing result. Bypass for `comprehension_repair` / `placement` is pedagogically sound. | Keep budget idea; treat *3* as hypothesis to A/B, not theory. |
| 4 | Hard modes blocked after hard break; soft `cf_recast` / time-pressure → conversation | **Support** | Protects meaning primacy; matches “brief form attention then return to communication.” | Good. Watch over-frequent soft recasts still raising anxiety if every turn is corrected. |
| 5 | Teach-move contract: every turn needs model / try / recast; bare hangout forbidden | **Partial support / affect risk** | Prevents chat-buddy failure mode. Conflicts with **WTC**: forced elicit every turn without prep can raise FL speaking anxiety; A1 often needs input-only turns. | Soften contract for true zeros / high anxiety / limited energy: allow input-heavy turns without obligatory try. |
| 6 | Affect = energy + boredom_risk only — **choice (c)** | **Reject as sufficient; boredom half-support** | Boredom (Pawlak / Li / Dewaele line) is real; Huang et al. (2025) multilevel meta: FL boredom → **small negative** achievement effect. **Missing FLA and FLE** (Dewaele: anxiety strongest negative WTC predictor). “Energy” ≠ anxiety, enjoyment, or confidence. | Two labels under-determine mode policy for adults. |
| 7 | Adult boat/café life OK; not kids flashcards — **choice (d) part 1** | **Support** | Correct market/persona vs gamified child UX. Situational authenticity of *boat/café* is optional, not universal (Long: needs analysis → target tasks). | Keep adult tone; do not freeze scenery as the identity. |
| 8 | Interest personalization (sister, Río Dulce) as engagement lever — **choice (d) part 2** | **Support** | Topic match / self-related content raises WTC and enjoyment (Dewaele 2019 and related WTC work). | Strongest cheap engagement lever you already have—use it as *task content*, not only sheet flavor text. |
| 9 | Blank sheet = Unknown (placement), not “proven beginner Hola ladder” | **Support** | Avoids false low placement; fits false-beginner adults. Placement still needs **low-threat** first tasks (high anxiety risk on first open production). | Keep; pair with input-first placement tasks. |
| 10 | Spanish-forward; English = lifeline not dual-subtitle wallpaper | **Support with dose control** | CI + L2 use frequency help enjoyment/WTC; English wall kills CI. Over-strict Spanish under high anxiety can freeze WTC. | Lifeline already in design; wire it to affect (not only comprehension_repair). |
| 11 | Modes realize CLT / CI / FonF / transfer trajectory | **Partial support** | Transfer after success is good spacing/transfer practice. System is closer to **task-supported instruction** than pure TBLT (tasks not primary syllabus unit). | Name it honestly in docs: task-supported + FonF, not full TBLT. |
| 12 | Progress score 0–100 ≈ mean confidence over 11 can-dos × 100 + up to +5 error-streak resolution | **Neutral for motivation; weak for task design** | Arithmetic: if mean conf = 0.40 → 0.40 × 100 = **40**; + resolved streaks up to **+5** → max display **45** in that case. Gamification literature (product, not SLA) links visible progress to return; **no evidence this formula predicts retention**. | Useful UI; do not claim it is a validated motivation instrument. |
| 13 | Chatbots / conversational AI help L2 learning & affect (implied product bet) | **Support (medium effects), not design-specific** | Lyu 2025: *g* = **0.608** overall; affective *g* = **0.645**; outcomes *g* = **0.590**. Difference affective vs cognitive non-significant (Q = 0.063, p = 0.803). | Medium effect ≠ your scene model is optimal. |
| 14 | “Time pressure” = `affect.energy == "limited_time"` forces soft modes | **Support as product heuristic** | Ecological for adults; not an SLA construct. Risk: conflates schedule constraint with cognitive load / anxiety. | OK if labeled ops, not “affect science complete.” |

### Direct adjudication of the four choices

| Choice | Verdict (2026-07-26) | One-line reason |
|--------|----------------------|-----------------|
| **(a)** Open-goal scenes, opportunistic exit | **AMEND** | Outcomes good; free multi-goal chat weak as *task*; missing complexity sequencing and info-gap structure. |
| **(b)** Conversation vehicle + budgeted breaks | **COUNTERSIGN with amendment** | FonF budget idea sound; fixed `3` and mandatory try every turn need empirical + affect-aware exceptions. |
| **(c)** Affect = energy + boredom_risk | **REJECT as complete model** | Boredom is on-trend and useful; omitting anxiety/enjoyment/confidence is a load-bearing miss for adult WTC. |
| **(d)** Adult boat/café + interest personalization | **COUNTERSIGN personalization; AMEND fixed scenery** | Interest tags are high-value; boat/café is optional flavor, not the engagement engine. |

---

## 3. What the other author / system docs MISSED

1. **WTC is not a side topic—it is the adult speaking bottleneck.** Inlined overview centers mode/gate/sheet and barely models *whether the learner will attempt*. Anxiety and perceived competence dominate that decision; you do not track them.

2. **TBLT at A1 ≠ open conversation.** Ellis/Shintani: input-based tasks for beginners. Your default production elicit (`try` every turn) is adult-false-beginner friendly and true-zero hostile.

3. **Best task types for interaction quality.** Pica et al.: jigsaw / info-gap > decision > opinion. Opportunistic scene chat sits near the weak end unless exit predicates encode *information exchange* and a single shared outcome.

4. **Task sequencing theory is absent.** Robinson SSARC / Cognition Hypothesis: increase complexity along resource-directing dimensions after success. Your modes sequence *pedagogic interventions*, not *task complexity*. Different problem.

5. **Authenticity split is underspecified.** Boat/café can be situational authenticity; pedagogic tasks with interactional authenticity are enough for acquisition. Docs imply lifestyle scenery does engagement work that **personal goals and task progress** should do.

6. **Affect → control loop is one-way and thin.** `limited_time` softens mode; `boredom_risk` is mentioned but the overview does not state a deterministic policy (topic switch? shorter try? image? agency choice?). Labels without actuators are museum pieces.

7. **Retention for AI tutors ≠ session pedagogy alone.** Chatbot meta shows medium effects; product reality is novelty decay and invisible goals. You have a progress score and sheet but no **session-level task card** the learner can finish (“today: get the captain to understand where the boat is”).

8. **1:1 AI anxiety advantage is unused.** Non-judgmental AI can lower FLA relative to classrooms—but only if the system does not *feel* like constant graded production (gate + try every turn can recreate evaluation threat).

9. **No needs-analysis path.** Long’s TBLT starts from target tasks for *this* adult. Sister / Río Dulce are identity, not a task inventory derived from learner goals (travel, family calls, boat logistics).

10. **Quantitative evaluation gap.** No published (even internal) A/B on: break budget 2 vs 3 vs 5; open scenes vs scripted task cycles; affect-aware vs current 2-label policy. Medium chatbot *g* does not substitute.

---

## 4. Standing questions (from this round) — answers

**Q: Are open-goal scenes with opportunistic exits justified for A1 1:1?**  
**A:** Justified as *anti-script rigidity* and as outcome-bearing structure. **Not** justified as a substitute for designed tasks with convergent goals and complexity order. For A1, prefer **narrow open goals** (one exit at a time) over multi-goal opportunity soup.

**Q: Is conversation-as-vehicle + budgeted teaching breaks sound?**  
**A:** Yes as the default architecture for adult false beginners and for Long-style FonF. Amend: (i) make break budget data-driven; (ii) allow input-only turns; (iii) do not let the teach-move contract recreate continuous evaluation anxiety.

**Q: Is energy + boredom_risk enough affect tracking?**  
**A:** **No.** Sufficient for a v0 ops flag; insufficient for adult motivation/WTC. Minimum viable upgrade: add **anxiety** (or speaking_threat) and **engagement/enjoyment** (or reuse boredom inverse carefully)—or a single **WTC_proxy** from behavior (latency, English escape, one-word replies, mic abandonment).

**Q: Are boat/café + sister/Río Dulce good engagement levers?**  
**A:** **Interest personalization: yes (high confidence).** Fixed boat/café world: optional, adult-appropriate, but **not** load-bearing. Engagement follows *self-relevance + completable goals + non-humiliating difficulty*, not nautical wallpaper.

---

## 5. Ranking / critique (product-local)

**Strengths (do not throw out):**  
- Meaning-primary default + gated form breaks is the right family of theories (CLT + FonF).  
- Scenes with exit predicates are a real step above pure chat.  
- Adult persona and identity hooks are correct direction.  
- Session-scoped affect (cleared on new open) matches state-like FLA/WTC better than trait-only models.

**Weaknesses (do not paper over):**  
- “TBLT-flavored conversation” without task typology or sequencing.  
- Affect model missing the two strongest WTC emotions (anxiety, enjoyment).  
- Production pressure every turn at A1.  
- No learner-visible task success (only internal exit predicates + can-do confidences).

**Overall grade for this dimension (adjudicable, not vibes):**  
**B− / 6.5–7.0 out of 10** for a research prototype as of **2026-07-26**. Architecture family is sound; task design and affect instrumentation are underbuilt relative to the claim of pedagogy-first adult tutoring.

Arithmetic for the grade (explicit):  
- Theory alignment (CLT/FonF/vehicle): **+3.0 / 3**  
- Task construct (scenes vs full TBLT): **+1.5 / 3**  
- Affect / WTC coverage: **+1.0 / 2**  
- AI engagement/retention specifics: **+1.0 / 2**  
**Sum = 6.5 / 10.**

---

## 6. Concrete adjudicable improvement proposals  
*(ranked by expected impact ÷ implementation cost; citations pin the “why”)*

### P1 — Expand affect to drive policy (not only labels)  
**What:** Add `affect.anxiety` ∈ {low, mid, high} and `affect.enjoyment` ∈ {low, mid, high} (or a single behavioral `wtc_proxy`). Wire: high anxiety → prefer input/model, shorter try, earlier English lifeline, fewer hard breaks; high boredom → topic pivot from `identity` interests / new scene micro-goal; high enjoyment + success → allow transfer.  
**Impact / cost:** **High / Medium.**  
**Why:** Anxiety strongest negative WTC predictor; enjoyment positive; boredom already partially tracked but under-actuated.  
**Adjudication:** Within 20 pilot sessions, compare mean learner Spanish tokens / turn and English-escape rate: high-anxiety policy ON vs OFF. Pass if Spanish tokens **≥ +15%** or escape rate **≤ −20%** relative under high-anxiety flag without drop in form accuracy of recasts.

### P2 — Convert scenes from multi-open goals to **one primary convergent task** with info-gap structure  
**What:** Each scene: single exit predicate + required information roles (tutor holds X, learner must supply/request Y). Optional secondary goals only after primary exit. Sequence scenes by complexity (here-and-now, few elements → displaced, more elements) per Cognition Hypothesis spirit.  
**Impact / cost:** **High / High.**  
**Why:** Info-gap / jigsaw > free opinion chat for useful interaction; sequencing is a core TBLT claim.  
**Adjudication:** Same can-do window: scripted single-exit scenes vs current opportunistic multi-goal. Pass if exit completion rate **≥ +25%** and mean turns-to-exit **≤ −20%** without worse gate fault rate.

### P3 — Input-based task mode for true zeros / high anxiety / limited energy  
**What:** New or reused mode: meaning-first listen/point/choose (image + Spanish), **no obligatory try**; still allows model; teach-move contract exception documented.  
**Impact / cost:** **High for A1 zeros / Medium cost.**  
**Why:** Beginner TBLT evidence favors input-based tasks; forced output raises anxiety.  
**Adjudication:** Placement first 5 turns: input-based path vs current open+try. Pass if drop-off (session abandon before turn 5) **≤ −30%** and self-report “I could follow” **≥ +1 Likert point**.

### P4 — Learner-visible micro-goal + “task done” moment  
**What:** UI line: “Today’s task: …” mapped from active scene exit; celebrate completion in Spanish (brief) then transfer. Reuse progress header but bind it to **task completion events**, not only mean can-do confidence.  
**Impact / cost:** **Medium–High / Low.**  
**Why:** Completable goals and progress visibility drive return more reliably than scenery; chatbot medium effects do not replace goal structure; novelty decay reports emphasize empty chat.  
**Adjudication:** D1→D7 return rate or second-session start rate with visible goals ON vs OFF. Pass if second-session rate **≥ +10 percentage points** (e.g. 40% → 50%: absolute +10 pp).

### P5 — Make interest tags **task content**, not only sheet flavor  
**What:** Scheduler: when `boredom_risk` mid/high or every N conversation turns, force next_best micro-task built from identity (sister, Río Dulce, boat logistics) with explicit vocab pre-task (2–4 items) then use.  
**Impact / cost:** **Medium / Low.**  
**Why:** Interest-matched topics boost WTC; you already store the tags.  
**Adjudication:** Turns containing identity-derived content vs generic café: mean turn length and positive affect proxy. Pass if mean learner words **≥ +20%** on identity-derived turns.

---

## 7. Bottom line (append-ready)

I **do not countersign** “open scenes + two affect labels + lifestyle persona” as a complete scientific story of task design and motivation. I **do countersign** the skeleton: **conversation as meaning vehicle, budgeted reactive form breaks, adult stance, interest personalization, exit-bearing scenes.**  

The highest-leverage gap is **not** more Spanish scenery—it is (1) **WTC-critical affect (anxiety/enjoyment) with mode actuators**, (2) **real tasks (convergent outcomes + sequencing) instead of opportunistic chat goals**, and (3) **input-safe paths at A1**. Until those are measurable, claims of pedagogy-first task design for adult beginners remain **partially evidenced, partially product folklore**.

— End Grok independent review, 2026-07-26 —
