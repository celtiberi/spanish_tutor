# Teaching system design (v0)

**Status:** design lock from dual-AI spar (Grok + Claude), 2026-07-25  
**Provenance:** `docs/reviews-teaching-system-spar.md` (Claude) + Grok adjudication  
**Persona:** adult conversational A1 / false-beginner friendly (`docs/product-persona.md`)

---

## One-line thesis

**Conversation is the outer loop (vehicle). Teaching is knowing when to break, what goal is open, and whether the form landed.**  
A scene is an **open goal with a code-checkable done-test** — not a linear cutscene and not free chat with tags.

---

## Why we failed before

| Approach | Unit of design | Failure |
|----------|----------------|---------|
| Rules ladder / flashcards | Form queue | No meaning, adult-hostile |
| AI free chat + model/try | Single turn | Local “teach moves,” no trajectory |
| Output gate alone | Turn validity | Floor, not curriculum |

Teaching is a property of a **trajectory**: input → notice → production → feedback → **transfer** (later, unprompted, new context).

---

## Three layers every turn

```text
observe(learner, sheet)
    → select_mode(sheet, observe, session, open_scenes)   # CODE — must not fail
    → AI realize(mode, targets, scene_hints)              # AI — voice & contingency
    → output_gate(turn, mode_contract)                    # CODE — one repair
    → hard sheet update                                   # CODE — evidence
```

| Concern | Owner |
|---------|--------|
| Mode selection (when to break) | **Code** |
| Realization (how it sounds) | **AI** |
| Verification (well-formed turn) | **Code** |
| Student model | **Code** (hard observer + optional soft tool notes) |

**Kill product TEACHER_MODE sprawl.** One runtime. Keep `rules_planner` only as eval control arm if needed.

---

## Mode catalog (v1)

| Mode | Purpose | Enter (code) | Exit | Learner |
|------|---------|--------------|------|---------|
| `placement` | Locate ceiling | blank sheet + open | ≥1 skill evidence or 3 turns | Shows range |
| `conversation` | Meaning vehicle + transfer surface | default | higher-priority guard | Communicates |
| `cf_recast` | Soft FonF in meaning | error count 1 this turn | same turn | Re-produces |
| `form_focus` | **Hard break** — pedagogical grammar | active error count ≥2, not on cooldown | 1 turn → transfer try | Choice / short produce |
| `comprehension_check` | Did input land? | after model beat; or English-stuck | answered | Yes/no / choice |
| `association` | Form↔referent (image) | new concrete noun; or English wall | image + produce about it | Names / uses form |

**Later (not v1):** `cf_prompt`, controlled practice (structured input), input_flood (listening), full TBLT task, cross-session spacing scheduler.

### Break budget (code meta-rules)

- ≤ **1 hard break per 3 turns**
- **Never two consecutive** hard breaks
- Hard break always **exits to a transfer try** in conversation
- Time-pressure / limited_time → **no hard break** (recast only)
- Boredom → new topic conversation / task, **never drill**

---

## Break-from-conversation policy (first match wins)

```text
0. limited_time / session energy → conversation (inline recast OK)
1. boredom_risk high → conversation new topic (no drill)
2. blank + open → placement
3. english_only streak ≥2 or “no entiendo” → association (picture carries meaning)
4. active_error top count ≥2 and not cooldown → form_focus once, then transfer
5. just resolved focus form → conversation with transfer try (new micro-context)
6. new concrete noun not in lexicon → conversation + inline association image
7. open scene needs first model of target → model/form_focus once, then production
8. else → conversation (output-gated)
```

**Soft FonF** = stay in conversation, recast + same-form try.  
**Hard break** = UI/tutor leaves free chat shape (contrast, choice, image-led, short focus).

---

## Scenes = open goals (quest log, not cutscenes)

Multiple scenes may be **open**. Conversation + opportunistic breaks **satisfy whichever goal the utterance touches**. Learner can wander; system still closes goals when evidence appears.

### Scene schema (JSON)

```json
{
  "id": "boat_greet_wellbeing",
  "goal": {
    "can_do": "IP-04",
    "target_forms": ["present_estar_person"],
    "exit_predicate": "unprompted_form:present_estar_person:min=2"
  },
  "input": {
    "model_lines": ["Hola, ¿cómo estás?", "Estoy bien.", "Estoy en el bote."],
    "image_concept": "bote",
    "listening_ok": true
  },
  "notice": {
    "misconception_ids": ["M-4.1"],
    "error_patterns": ["estar_yo_estoy_vs_esta", "ser_estar_confuse"]
  },
  "production": {
    "elicit": "¿Y tú? ¿Cómo estás hoy?",
    "success_signals": ["estoy"]
  },
  "transfer": {
    "elicit": "¿Y tu amigo? ¿Cómo está?"
  },
  "scope": { "pack": "spanish_a1" },
  "spacing": { "resurface_after_days": [1, 3, 7] }
}
```

**Load-bearing rules**

- `exit_predicate` is a **query over the sheet** (no forked scene-state learner model)
- `notice` binds pack **M-IDs** + `ERROR_PATTERN_CATALOG` (reuse best content)
- Scene completion ≠ learning until falsifier shows transfer correlation

### First three boat scenes

1. **Meet the captain** — IP-01/IP-04, *estoy*, image bote/café; central `estar_yo_estoy_vs_esta`
2. **Where’s the boat** — location *estoy* + *soy de*; ser/estar contrast (M-4.x); interleaves with #1
3. **What do you like** — *me gusta* + concrete nouns + association; open transfer / autonomy

---

## Contract evolution

| v1.1 (today) | v2 (this system) |
|--------------|------------------|
| Every turn: model and/or try and/or recast | Every **arc**: input → notice → try → transfer |
| Turn pedagogy notes | + `mode`, `open_scenes`, `exit_predicate` hits |
| Floor metrics | **Transfer rate** is the north star |

Output gate remains: Spanish ratio, probe loops, teach-move, plus **per-mode** checks (e.g. association requires image+form).

---

## Success metrics (teaching vs chat-with-tags)

1. **Unprompted transfer rate** (primary): learner produces target form correctly when it was **not** in the immediately preceding tutor `<model>`  
2. **Error-resolution slope** after `form_focus`  
3. **Break precision** (should-break vs did-break on labeled turns)  
4. **Exit-predicate validity**: completion predicts later unprompted use  

Ablation: chat+gate → +modes → +scenes. **If scenes don’t beat modes on transfer, kill scenes.**

---

## Implementation order (1 week)

1. `select_mode()` + Mode enum + unit tests (pure function)  
2. Wire `mode` into executor prompt + per-mode output_gate  
3. Scene JSON loader + 3 boat scenes (dual-AI fact-check)  
4. Realize `form_focus` + `association` + `comprehension_check` in UI/parts  
5. Spacing-lite on open (due forms from `last_seen`)  
6. Falsifier harness on transfer metric  

**Do not** author a large scene library before step 1–2 prove break policy helps.

---

## Standing agreements (Grok ↔ Claude)

| Point | Ruling |
|-------|--------|
| Conversation is vehicle, not pedagogy | **Agree** |
| Scene as linear runtime | **Reject** — open goals only |
| Mode selection in code | **Agree** |
| AI realizes turn | **Agree** |
| Sheet code-authoritative | **Agree** |
| Bind scenes to M-IDs / error patterns | **Agree** |
| Prove transfer gap before big content | **Agree** |

---

## Open product calls (still yours)

1. Image budget: cache-only allowlist vs generate-on-miss for association  
2. How aggressive is `form_focus` at count ≥2 vs ≥3 for adults  
3. Whether placement is allowed to *feel* like assessment for 2–3 turns  

---

*Full spar transcript: `docs/reviews-teaching-system-spar.md`*
