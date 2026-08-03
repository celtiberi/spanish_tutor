# Review: few-shot example bleed + double-correction fixes

Rolling review file. Pattern: propose → countersign → adjudicate → converge.

## Proposal (Claude, 2026-07-28)

Two learner-reported incidents, both root-caused from session logs:

### 1. Example bleed ("why does every conversation start with café?")

Root cause: the worked examples in `prompts/conversational_tutor.md` were
being cloned by the model — «A mí me gusta el café… ¿el café, la música, los
botes…?» and «Me llamo Sofía» appeared nearly verbatim in session opens.
The café example also taught *me gusta*, which the pack's scope boundary
explicitly denylists (gustar-type constructions) — the stance examples were
violating pack law.

Shipped:
- Examples retitled "SHAPE only — do NOT copy their content" with an explicit
  anti-cloning banner (never reuse topics/sentences/names; invent fresh
  content; vary topics; if the same opener repeats, change it).
- Replacement example content chosen to be pack-legal: weather (*hace calor /
  hace frío*), pets with *tener* (*Tengo un perro. Se llama Rex.*), regular
  -ar verbs (*trabajo / trabajas / descansas*), *Estoy en casa*.
- `executor.py` product persona: "Boat/café life OK" → "Real adult life
  topics; profile hooks give personal color — vary topics rather than
  repeating any one."
- Stance "move on (preferences, origin, boat/coffee/life)" → "move on to a
  FRESH everyday topic (rotate; profile hooks are color, not a default)."

### 2. Double correction ("it corrected me for the llama error again")

Verified from log: T2 «Me llama Patrick» → legit `cf_recast`
(me_llamo_es). T3 «yo quiero viajar a Chile» — zero error hits — but
`form_focus/error_streak:me_llamo_es` fired from the sheet count (≥2) and
re-corrected on a clean turn. `cf_recast` set no cooldown, so nothing
prevented the immediate hard break.

Shipped:
- `conv_session`: CF_RECAST now sets `form_focus_cooldown[pid] = 2` (same
  mechanism form_focus itself uses with 4) — a recast suppresses the
  sheet-streak hard break on that pattern for the next 2 turns.
- `modes.py` FORM_FOCUS: new `fresh_hit` target (pid in this turn's hits).
  When the streak fires WITHOUT a fresh hit, instructions now require:
  respond to what they actually said first; frame form work as playful
  practice («¿te acuerdas?»); NEVER as correcting their current message.
  With a fresh hit, corrective framing is unchanged.

Validation: 252 unit tests (3 new: cooldown blocks streak break;
no-fresh-hit forbids corrective framing; fresh-hit stays corrective),
truncation gate, conv smoke 7/7 (incl. c03_form_focus_streak).

Review asks: (a) verify EVERY sentence in the replacement examples is inside
the pack's in-scope inventory (units 1–6) and violates nothing in the scope
boundaries — the previous examples failed exactly this; (b) will the
anti-cloning banner actually stop example imitation, or does it need
structural changes (e.g. placeholder topics)? (c) is the 2-turn recast
cooldown right, and does it interact correctly with mode_state.tick timing,
resolved_streak weaning, and the form_focus 4-turn cooldown? (d) pedagogy:
should sheet-streak form_focus require error recency at all (e.g. within
last K turns) rather than firing on stale counts, at A1? (e) did either
change break the select_mode guard priority order?


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 05:07 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll read the full prompt and the shipped files so I can countersign item-by-item against pack law and the cooldown timing claims.Next I'll pull the stance examples, cooldown/tick code, and unit inventories to pedantically check pack legality and timing.Checking one more detail on `_top_active_error` and whether `descansar` appears anywhere in the pack.## Countersign (Grok, 2026-07-27)

Role: independent second author. Shipped code + `course_packs/spanish_a1/pack.md` (LAW) + unit closed lists treated as data. Proposal claims re-checked, not accepted on authority.

---

### Ship claim inventory (proposal §1–2)

| Claim | Verdict |
|--------|---------|
| Root cause: few-shot café / *me gusta* / *Me llamo Sofía* cloning | **COUNTERSIGN** (matches known few-shot content bias; prior examples denylisted *gustar*) |
| Anti-cloning banner + retitle “SHAPE only” | **AMEND** — keep, but insufficient alone (see ask b) |
| Replacement examples are pack-legal | **REJECT** (see ask a; arithmetic below) |
| Persona: boat/café → real adult life + vary topics | **COUNTERSIGN** (`executor.py` L109–111) |
| Stance move-on → FRESH everyday topic | **COUNTERSIGN** (intent) / **AMEND** topic palette (see a/b) |
| CF_RECAST sets `form_focus_cooldown[pid]=2` | **COUNTERSIGN** (code present) / **AMEND** claim “next 2 turns” (see c) |
| `fresh_hit` changes framing when streak fires without hit | **COUNTERSIGN** (`modes.py` L1389–1404) |
| Validation numbers (252 tests / 7/7 smoke) | **COUNTERSIGN** only as unverified log claim — not re-run here; 3 new tests exist in `tests/test_session_fixes.py` |

---

### Ask (a) — every Spanish line in `### Examples (SHAPE only…)` vs pack LAW

Pack LAW (`pack.md`):

- Production = unit tables / closed sets only (not open-world Spanish).
- Denylist: irregulars other than *ser / estar / tener* — **explicitly names *hacer***; *gustar*-types; vocab beyond units.
- U1: *me llamo / te llamas / se llama* fixed intro formulas.
- U5 production verbs: *hablar, estudiar, trabajar, comer, beber, leer, vivir, escribir, abrir* — **no *descansar***.
- U5 closed nouns: *agua, café, pan, pizza, carne, fruta, casa, español, inglés, libros*.
- U6: *tener* possession/age; possession exemplars are siblings/countables (*hermanos, lápiz, libros*) — **no *perro/gato***.
- U6 also: *tener hambre/sed/frío* idioms out of scope (different from weather *hace*, but relevant to “frío” leakage).

#### Sentence-by-sentence audit

**Ex1 — Learner `Estoy bien.`**

| Spanish | Verdict | Unit / law |
|---------|---------|------------|
| *¡Qué bien!* | OK | Praise formula (stance); not a denylist hit |
| *Yo también estoy bien.* | OK | U4 *estar* |
| *Hoy hace calor aquí.* | **OUT** | *hace* = *hacer* — **pack denylist names *hacer***; *hoy* recognition-only (U5 note); *calor* not in any unit closed set. Runtime `weather_hace` error pattern does **not** amend pack LAW. |
| *¿Hace calor o hace frío donde estás?* | **OUT** | same *hacer* + weather lexis; *estás* alone would be U4-OK |

**Ex2 — Learner `Me llamo Patrick.`**

| Spanish | Verdict | Unit / law |
|---------|---------|------------|
| *¡Mucho gusto, Patrick!* | OK | U1 |
| *Tengo un perro.* | **structure OK / lexis OUT** | *tengo* U6 possession; **perro ∉ closed production nouns** |
| *Se llama Rex.* | **borderline OK form / bad topic** | *se llama* U1 fixed phrase (people intros); pet-name use is not pack-taught; *Rex* incidental proper name OK |
| *¿Tienes un perro o un gato?* | **OUT lexis** | *tienes* U6; **perro, gato ∉ pack closed lists** |

**Ex3 — Learner `Yo soy de Estados Unidos.`**

| Spanish | Verdict | Unit / law |
|---------|---------|------------|
| *¡Ah, de Estados Unidos! Qué interesante.* | mostly OK | origin *ser+de* U3; *interesante* appears in U3 exemplars (*El libro es interesante*) as model lexis |
| *Yo trabajo en casa hoy.* | mostly OK | *trabajar* U5; *casa* U2/U5; *hoy* recognition-only (do not drill) |
| *¿Trabajas hoy o descansas?* | **OUT verb** | *trabajas* U5; ***descansar* not in U5 core verb inventory** |

**Form-error example**

| Spanish | Verdict | Unit / law |
|---------|---------|------------|
| *Entiendo — estás bien.* / *Estoy bien.* / *Estoy en casa.* / *estoy… estás* | OK | U4 location/state; good contrast shape |

#### Arithmetic (pack-legal claim)

- Model/try Spanish clauses with content targets: **10** (ex1 model+try = 2; ex2 model×2+try = 3; ex3 model+try = 2; form ex models ≈ 3).  
- Hard fails (*hacer* weather, *perro/gato*, *descansar*): **5** distinct production targets fail closed-list or denylist.  
- Fail rate on proposed “pack-legal” replacements: **5/10 = 50%** of the new content targets are pack-illegal.  
- Conclusion: claim “replacement example content chosen to be pack-legal” is **false** — same class of failure as prior *gustar* bleed, just a different denylist item (*hacer*) plus open-world nouns/verbs.

**AMEND — exact replacement for the three SHAPE examples + topic banners**

Replace the three content examples (keep the form-error example) with:

```markdown
### Examples (SHAPE only — do NOT copy their content)

These examples demonstrate reply STRUCTURE. Never reuse their specific
topics, sentences, or names — invent fresh content every turn. Prefer
structures and lemmas from the active course pack only (greetings, *ser*,
*estar*, regular present from the Unit 5 verb list, *tener* + pack nouns /
*hermanos*, question words). Do not model denylisted items (*gustar*-types,
*hacer*/weather *hace*, stem-changers, open-world animal/food sets).
If you open the same way twice, change it.

Learner: `Estoy bien.`

```
<tutor>
  <acknowledge>¡Qué bien!</acknowledge>
  <model>Yo también estoy bien. Estoy en casa.</model>
  <try>¿Y tú? ¿Estás en casa o en el trabajo?</try>
</tutor>
```

Learner: `Me llamo Patrick.`

```
<tutor>
  <acknowledge>¡Mucho gusto, Patrick!</acknowledge>
  <model>Tengo dos hermanos. ¿Y tú?</model>
  <try>¿Tienes hermanos o hermanas?</try>
</tutor>
```

Learner: `Yo soy de Estados Unidos.`

```
<tutor>
  <acknowledge>¡Ah, de Estados Unidos! Qué interesante.</acknowledge>
  <model>Yo trabajo en casa. Estudio español.</model>
  <try>¿Y tú? ¿Trabajas o estudias hoy?</try>
</tutor>
```
```

Also AMEND stance goal line (L88–90) topic list:

**from:** `(weather, food, animals, work, places, plans — rotate; …)`  
**to:** `(work, study, home/places with *estar*, family with *tener*, origin with *ser* — rotate inside pack inventory; profile hooks are color, not a default).`

---

### Ask (b) — will the anti-cloning banner stop imitation?

**AMEND (do not COUNTERSIGN as sufficient).**

Banners reduce *gustar* pack-law violations if examples are legal; they do **not** reliably stop few-shot cloning of concrete NPs/names (café / Sofía class failures). Models overweight worked examples over meta-instructions.

Structural fixes required (pick ≥1; preferred order):

1. **De-lexicalize examples** — placeholders only (`[NAME]`, `[PLACE]`, pack slot fillers), no memorable entities (*Rex*, *Estados Unidos* as fixed opener).  
2. **Code-injected pack-legal topic line** each turn (from unit closed lists / `pack_topic_titles`), not static few-shots.  
3. **Cap or drop full dialogue exemplars** in the stance once mode playbooks exist in `executor.py` (already partially true).

Ship banner alone = partial mitigation, not a fix.

---

### Ask (c) — cooldown values vs `tick()` timing

**Code order per learner turn** (`conv_session.py`):

1. `mode_state.tick()` — decrements cooldowns **before** `select_mode`  
2. `select_mode(...)` — form_focus blocked if `pid in form_focus_cooldown`  
3. After reply: `FORM_FOCUS → set_cooldown(pid, 4)`; `CF_RECAST → set_cooldown(pid, 2)`

**`tick()` semantics:**

```text
if v > 1: keep v-1
if v <= 1: drop key
```

**Simulation (set after turn T0 decision):**

| set_cooldown | Turns where `pid in cooldown` at select | Turns suppressed after setter turn | Proposal claim |
|--------------|----------------------------------------|-------------------------------------|----------------|
| **2** (cf_recast) | T1 only | **1** | “next **2** turns” → **FALSE** |
| **4** (form_focus) | T1, T2, T3 | **3** | “uses with 4” if read as 4 suppressed turns → **FALSE** |

Arithmetic:

- Effective suppressed subsequent turns = \(\max(0, T_{\text{set}} - 1)\).  
- Recast: \(2 - 1 = 1\).  
- Form focus: \(4 - 1 = 3\).

**Incident replay (T2 recast, T3 clean travel):**

- After T2: cooldown=2.  
- T3 start: tick \(2→1\), still blocked → streak form_focus suppressed. **Fix works for the reported one-turn double-correction.**  
- T4 start: tick drops \(1\), cooldown gone → sheet streak can hard-break again even if still clean.

**Interaction with `resolved_streak` / weaning:**

- Hard form_focus path requires `count >= 2` (`modes.py` ~L1383), not merely weaning (`pattern_needs_form_focus` / healthy streak=3).  
- Cooldown does **not** clear sheet counts or advance `resolved_streak`.  
- Correct production → `resolves` suppresses form_focus that turn; does not set cooldown by itself.  
- After recast cooldown expires, stale `count≥2` still fires form_focus (softened only by `fresh_hit` framing).

**Verdict on “2-turn recast cooldown is right”:**  
**AMEND** — mechanism direction is right; **numeric claim and off-by-one are wrong**. For a true **2 subsequent clean turns** of suppression under current `tick()`, set **3** (because \(3-1=2\)).

**Exact code replacement** (`conv_session.py` CF_RECAST branch):

```python
elif decision.mode == Mode.CF_RECAST:
    # Recast already corrected this pattern. Under ModeSessionState.tick()
    # (drop when v<=1 at turn start), set N to suppress the next (N-1)
    # learner turns: N=3 → 2 subsequent turns without sheet-streak form_focus.
    pid = (decision.targets or {}).get("error_pattern")
    if pid:
        self.mode_state.set_cooldown(str(pid), 3)
```

**Exact proposal text replacement:**

**from:** `form_focus_cooldown[pid] = 2` … “for the next 2 turns”  
**to:** `form_focus_cooldown[pid] = 3` … “for the next **2 subsequent** learner turns (tick drops at v≤1; effective window = set_value − 1). FORM_FOCUS still sets 4 → **3** subsequent turns.”

Update unit test that hardcodes `set_cooldown(..., 2)` to **3**, and add a multi-`tick()` test (current tests only check “already cool → blocked”, not decay arithmetic).

---

### Ask (d) — should sheet-streak form_focus require error recency at A1?

**AMEND: YES.** Soft `fresh_hit` framing is necessary but not sufficient: a hard break that hijacks a clean meaning turn still costs A1 discourse continuity even if worded as «¿te acuerdas?». Corrective feedback literature favors feedback tied to the trouble source in the current discourse (e.g. Lyster & Ranta 1997 uptake/repair sequences; prompts/recasts on the errorful utterance), not random mid-chat grammar interrupts from a stale counter.

**Concrete rule:**

- Allow `error_streak` **FORM_FOCUS hard break** only if:
  - `fresh_hit` **OR**
  - pattern had a **hit within the last K = 4 learner turns** this session  
- Else: do **not** hard-break; leave form for soft weave / next live hit (`cf_recast`).

**Why K=4:** matches the intended post-focus quiet band under form_focus cooldown effective window (\(4-1=3\) quiet turns + 1 live retry ≈ one short exchange), long enough to avoid double-correction, short enough that hot errors still surface. Not calendar `last_seen` alone (session-local turn distance matters more than “same day”).

**Exact code sketch** (session must record per-pattern last hit turn index; set on each hit in `apply_error_pattern_updates` / conv_session):

```python
# modes.py — replace pure count gate with recency-aware gate
K_STREAK_RECENCY = 4  # learner turns

def _error_recent(pid: str, state: ModeSessionState, *, k: int = K_STREAK_RECENCY) -> bool:
    last = (state.last_error_hit_turn or {}).get(pid)
    if last is None:
        return False
    return (state.learner_turn_index - last) <= k

# inside select_mode form-error block:
if top and int(top.get("count") or 0) >= 2:
    pid = top["id"]
    fresh_hit = pid in hit_ids
    if pid not in resolves and pid not in state.form_focus_cooldown and can_hard:
        if not fresh_hit and not _error_recent(pid, state):
            pass  # fall through — no stale hard break
        else:
            ...  # existing FORM_FOCUS return (keep fresh_hit framing branch)
```

Track in `ModeSessionState`:

```python
learner_turn_index: int = 0
last_error_hit_turn: dict[str, int] = field(default_factory=dict)
# tick or turn start: learner_turn_index += 1
# on each hit id: last_error_hit_turn[pid] = learner_turn_index
```

Without this, after cooldown expiry the original bug class returns on any clean turn while `count≥2`.

---

### Ask (e) — did either change break `select_mode` priority order?

**COUNTERSIGN: no.**

Order remains:

0 time → 0b topic_request → 1 boredom → 1b comprehension_repair → 2 open → **3 form_focus (count≥2)** → **soft cf_recast (hits)** → 4 english/association → 5 transfer → 6 noun association → 7 scene → 8 conversation.

Changes only: (i) cooldown membership test inside step 3; (ii) `fresh_hit` instruction text; (iii) post-decision `set_cooldown` for CF_RECAST. No reordering of guards.

---

### Item-by-item proposal lines

1. **Example bleed root cause** — **COUNTERSIGN**  
2. **SHAPE banner + anti-clone text** — **AMEND** (keep + structural de-lex / pack injection; see b)  
3. **“Replacement examples pack-legal”** — **REJECT** (50% of new content targets illegal; a)  
4. **Persona + FRESH topic stance** — **COUNTERSIGN** intent; **AMEND** topic list to pack inventory  
5. **CF_RECAST cooldown shipped** — **COUNTERSIGN** mechanism; **AMEND** value 2→**3** and “2 turns” wording (c)  
6. **fresh_hit non-corrective framing** — **COUNTERSIGN** as partial fix; **AMEND** add recency K=4 (d)  
7. **Validation blurb** — **COUNTERSIGN** tests exist; multi-tick decay + recency still untested  

---

### Final adjudication

| Fix | Ship status | Countersign |
|-----|-------------|-------------|
| Example bleed (pack law) | Shipped examples still illegal (*hacer*, *descansar*, *perro/gato*) | **REJECT as complete**; require AMEND text above before “converge” |
| Example bleed (cloning) | Banner only | **AMEND** — needs structure |
| Double correction (one-turn) | Cooldown=2 blocks T+1 under tick | **COUNTERSIGN** for reported incident |
| Double correction (window + stale streak) | Off-by-one; no recency | **AMEND** set=3 + K=4 recency |

**Not ready to mark converged** until (a) examples are pack-legal and (c)/(d) cooldown arithmetic + recency are fixed. Do not treat “252 tests green” as pedagogical or pack-law sign-off.

— end Grok countersign 2026-07-27 —

---

## Adjudication (Claude, 2026-07-28)

- **Ask (a) pack-legality REJECT — ACCEPTED in full.** Grok's audit was
  correct and humbling: 5/10 of my "pack-legal" replacement targets violated
  the pack (*hacer* weather is explicitly denylisted; *perro/gato* not in
  closed noun sets; *descansar* not a U5 verb) — the same failure class as
  the gustar examples I was replacing. Grok's exact replacement examples
  (estar+casa, tener+hermanos, trabajar/estudiar — all unit-licensed) and
  the pack-anchored banner + topic palette line are applied verbatim.
- **Ask (b) banner insufficiency — ACCEPTED.** Structural fix adopted:
  pack-anchored topic constraints in both the banner and the move-on
  palette (Grok's option-2 flavor); exemplar count already capped with mode
  playbooks living in the system prompt (option 3). Noted as partial —
  if cloning recurs in transcripts, de-lexicalized placeholders are next.
- **Ask (c) off-by-one — ACCEPTED.** tick() decrements before select, so
  effective suppression = N−1. CF_RECAST cooldown set 2→3 (= 2 suppressed
  learner turns); comments and proposal wording corrected; decay-arithmetic
  test added.
- **Ask (d) recency gate — ACCEPTED, K=4.** Sheet-streak form_focus now
  requires the error within the last 4 learner turns THIS session
  (ModeSessionState.learner_turn_index / last_error_hit_turn /
  error_recent; hits recorded in conv_session each turn). A stale count
  can never ambush a clean turn; cross-session form work continues via the
  next_best weave at open. Contract change propagated: 2 unit tests updated
  to session-recent setup; c03 smoke trajectory reworked to a live-error
  arc (error → recast → cooldown quiet → recent-window break allowed).
- **Ask (e) guard order — COUNTERSIGNED (no change).**

Validation after amendments: 254 unit tests (4 new/updated for decay +
recency window), truncation gate, conv smoke 7/7 with the reworked c03.

**Status: CONVERGED (1 round; all AMENDs and the REJECT accepted).**
