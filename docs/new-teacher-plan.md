# Plan: New teacher (structured pedagogical control)

**Status:** design — not implemented  
**Date:** 2026-07-25  
**Builds on:** character sheet, pedagogy contract v1.1, diagnostic open, conversational session, research on ITS / multi-agent tutors / Duolingo-style splits

---

## 1. Product stance (ours, not Khanmigo’s)

### What we optimize for

Language is learned by **associating form with meaning in use** — hearing/seeing models, trying, getting clean input again, transferring. That is CI + focus-on-form + (later) visual dual-coding.

### Explicit non-priority: “no answer dump”

Many math/homework tutors treat “never show the answer” as core (Socratic, anti-cheating). **We do not.**

| Domain | “Show the answer” |
|--------|-------------------|
| Math homework | Often bad — skips thinking |
| **Our Spanish tutor** | **Often good** — the model *is* the input |

Showing **Estoy bien** / a short dialogue / a picture of *el bote* is **teaching**, not spoiling. Withholding the form forces guesswork without association.

**Policy:** Prefer **model + try** over pure Socratic withholding.  
Socratic only when it serves *production* (“you try first”) — never as a moral rule against revealing Spanish.

---

## 2. Problem with the current teacher

| Layer | Today | Failure mode |
|-------|--------|----------------|
| Student model | Character sheet | Good, but updates often optional |
| Domain | Pack + can-dos | Softly used |
| Pedagogy | Prompt + harness + contract notes | LLM may ignore; monologue opens |
| Voice | Same call as judgment | Decide + speak mixed |

Research (classic ITS, Duolingo Birdbrain+Max, GenMentor multi-agent) converges on:

> **Decide the pedagogical move as data first; generate learner language second.**

We already have sheet + contract. We lack a **hard plan object**.

---

## 3. Target architecture

```text
                    ┌──────────────────────┐
 Learner turn  ───► │  OBSERVE             │  text (+ STT meta)
                    │  rules + light LLM   │  errors, intent, level signals
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │  STUDENT MODEL       │  character sheet (always written)
                    │  hard update path    │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │  PLANNER             │  outputs PlanCard (JSON)
                    │  rules ± small LLM   │  phase + move + targets
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │  GATE                │  reject incomplete / off-policy cards
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │  EXECUTOR            │  fills <model>/<try>/… only for the card
                    │  voice LLM           │  Spanish-forward, association-first
                    └──────────┬───────────┘
                               ▼
                    UI / TTS (+ later image assets bound to card.concept)
```

**Two LLM roles max at first** (GenMentor has many; we stay small):

1. **Planner** — may be mostly **deterministic rules** + optional LLM only when ambiguous  
2. **Executor** — always LLM, tightly constrained by the card  

Sheet updates: **prefer code + observer**, not “hope the executor tools.”

---

## 4. Session phases (state machine)

Phases are **first-class** (not prompt suggestions).

| Phase | When | Goal |
|-------|------|------|
| `diagnostic` | Blank sheet / insufficient evidence | Feel-out; tiny models; English frame OK |
| `teach_form` | Known weak form / active error | Recast + model + try on one form |
| `associate` | New noun/concept / later images | Form + meaning (+ visual) bound together |
| `transfer` | Form emerging/usable | Same form, new micro-context |
| `chat_stretch` | Form stable enough | next_best can-do stretch still with model+try |
| `review` | Spaced / resolved-streak weaning | Light re-probe of recent form |

**Transitions (sketch):**

- Reset / no evidence → `diagnostic`  
- First production evidence → leave diagnostic when ≥1 skill has real evidence **or** N successful probes  
- Active error_pattern / form_focus → `teach_form`  
- Clean streak / high conf → `transfer` then `chat_stretch`  
- Planner never jumps `diagnostic` → free intermediate monologue  

---

## 5. Pedagogical move catalog

Small closed set (AutoTutor-style acts, language-specific):

| Move | Meaning | Answer dump? |
|------|---------|--------------|
| `model_try` | Show 1–3 forms, one try | **Models are required** |
| `recast_retry` | Clean form + same-form try | **Show correct form** |
| `comprehension_check` | Yes/no or choice on meaning | May show Spanish options |
| `associate` | Bind form to referent (text now; image later) | Show form + referent |
| `transfer_try` | Same form, new context | Model still OK |
| `english_frame` | Meta goal in English (diagnostic / stuck) | Then model Spanish |
| `praise_continue` | Short ES praise + next beat | Only after real success |

**Forbidden as standalone:** `open_chat_only` (bare ¿cómo estás? with no model).

---

## 6. PlanCard schema (v0)

Machine-readable decision object. Executor may not invent a new agenda.

```json
{
  "version": "0.1",
  "phase": "diagnostic | teach_form | associate | transfer | chat_stretch | review",
  "move": "model_try | recast_retry | comprehension_check | associate | transfer_try | english_frame | praise_continue",
  "targets": {
    "form_id": "present_estar_person | null",
    "error_pattern": "estar_yo_estoy_vs_esta | null",
    "can_do": "IP-04 | null",
    "concepts": ["hola", "estoy_bien"]
  },
  "models": ["Estoy bien.", "Hola."],
  "try_prompt": "Say Hola — or try Estoy bien if you can.",
  "english_frame": "Hi — I'm your Spanish tutor. We'll start tiny…",
  "recast_of": null,
  "scaffold": "en_rescue | es_forward | mostly_es",
  "max_sentences": 6,
  "allow_new_topic": false,
  "sheet_updates": {
    "required": true,
    "hints": ["observe_greeting", "observe_estoy"]
  },
  "assets": {
    "image_concept": null
  }
}
```

**Gate rules (code):**

- `models` non-empty unless move is pure comprehension with options  
- `try_prompt` non-empty for production moves  
- `phase=diagnostic` ⇒ `scaffold` allows English; models ⊆ {hola, estoy…} level  
- `move=recast_retry` ⇒ `models` includes clean form; `try` retries same form  
- `allow_new_topic=false` ⇒ executor prompt forbids café/pets tangents  

---

## 7. Hard student-model path

Do **not** rely only on `update_character_sheet` tool compliance.

| Signal | Handler |
|--------|---------|
| Greeting / hola | Bump IP-01 evidence |
| *yo está* / person error | error_patterns + form conf |
| Successful *estoy* | resolve streak / conf up |
| English-only reply | keep scaffold true; note receptive |
| Name given | identity + IP-03 |

Pipeline:

1. **Observer** (regex + optional small classify) on learner text  
2. **Merge** into sheet (deterministic)  
3. **Recompute** next_best / phase eligibility  
4. Planner reads updated sheet  
5. Executor may still tool-call for soft notes, but **core evidence is not optional**

This matches industry: Duolingo updates ability every item; classic ITS always updates the student model.

---

## 8. Executor (voice) constraints

Executor prompt is **thin**:

- Realize this PlanCard only  
- Structured tags: acknowledge / recast / model / try / continue  
- Spanish-forward when `scaffold` says so; English frame when card provides it  
- **Association-first:** prefer clear models over withholding  
- Short (TTS)  
- Never invent phase/move  

Pedagogy contract checks still run on the **composed** turn (model/try present).

---

## 9. Modalities (in contract, staged)

| Stage | Modality |
|-------|----------|
| Now | text model/try, recast, STT/TTS |
| Next | hard observer + PlanCard + executor |
| Later | `assets.image_concept` → generate/cache image same turn as form (**association**, not wallpaper) |

Visual rules stay as in `pedagogy-contract.md`: target-linked, same-turn, logged teach move.

---

## 10. What we deliberately skip (for now)

| Idea | Why skip / defer |
|------|------------------|
| Strict no-answer-dump / homework anti-cheat | Wrong fit for language association |
| 10+ multi-agents (SimClass-scale) | Cost/complexity; 2 roles enough |
| Full RL sequencing (Birdbrain-scale) | Need more data; start rule phase machine |
| Replacing character sheet | Sheet stays; becomes true student model |
| Killing conversational path overnight | Shadow then switch |

---

## 11. Implementation sequence (PR plan)

### PR1 — PlanCard + gate (no LLM planner yet)

- `tutor/plan_card.py`: schema, validate, serialize  
- Rules-only planner: `sheet + last utterance → PlanCard`  
  - blank → diagnostic `english_frame` + `model_try`  
  - hot error → `recast_retry`  
  - else next_best `model_try` / `transfer_try`  
- Unit tests for transitions  

### PR2 — Executor bound to card

- `build_executor_prompt(card)`  
- `conv_session` path: observe → plan → gate → execute → contract check  
- Log `plan` + `parts` every turn  
- Feature flag: `TEACHER_MODE=legacy|planned`  

### PR3 — Hard observer / sheet writer

- Deterministic detectors for top error patterns + can-do probes  
- Always merge before next plan  
- Reduce dependence on tool_update  

### PR4 — UI / notes

- Show phase + move in focus rail (“Phase: diagnostic · Move: model_try”)  
- Optional debug: PlanCard JSON for us  

### PR5 — Association assets (images)

- When `move=associate` and concept in allowlist, attach image  
- Same-turn as model  

### PR6 — Optional LLM planner assist

- Only when rules return `confidence=low`  
- Still must emit PlanCard; gate rejects free prose  

---

## 12. Success metrics (experiments)

| Metric | Target |
|--------|--------|
| % turns with teach move | ≥ 90% (contract) |
| Blank open = diagnostic | 100% of resets |
| Executor off-card new topic | near 0 (manual + sim) |
| Form conf / error resolve | improve vs legacy in 5–10 min sim |
| Learner association | later: concept+image co-occurrence |

AI student sim gains a check: `plan.phase` / `plan.move` present when `TEACHER_MODE=planned`.

---

## 13. Mapping research → us

| Source | We take | We leave |
|--------|---------|----------|
| Classic ITS 4 models | Domain / student / tutor / UI split | Heavy rule authoring for all domains |
| AutoTutor dialogue acts | Closed move catalog | Full speech-act NLP stack |
| Duolingo Birdbrain + Max | Sequence ≠ chat | Billion-scale RL |
| GenMentor multi-agent | Gap → schedule → tutor | 5+ chatty agents |
| Khanmigo Socratic | Optional later | Anti-answer-dump as default |
| Our contract + sheet | Keep and harden | Soft-only enforcement |

---

## 14. One-sentence north star

**The new teacher always knows its phase and move as structured data; it shows Spanish freely so learners associate meaning with form; the sheet is updated by code; the voice only performs the plan.**

---

## 15. Open decisions (for you)

1. **Planner default:** rules-only first (recommended) vs LLM planner from day one?  
2. **Legacy flag duration:** how long keep `TEACHER_MODE=legacy`?  
3. **Images:** PR5 soon after planner, or after executor is stable?  
4. **Diagnostic exit:** N turns vs first solid Spanish vs first skill conf > 0.3?  

Recommend: **rules planner first**, **legacy flag ≥ 2 weeks**, **images after executor**, **exit diagnostic on first real skill evidence or 3 probes**.
