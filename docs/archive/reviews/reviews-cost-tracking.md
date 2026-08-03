# Review: session cost tracking + prompt-cache reorder + one-block TTS

Rolling review file. Pattern: propose → countersign → adjudicate → converge.

## Proposal (Claude, 2026-07-28)

Context: ~$25 of Gemini credits burned in a few days with zero visibility.
Shipped in this batch:

1. **Cost tracking** (`tutor/costs.py`): per-session tracker + cross-process
   append-only ledger (`logs/costs.jsonl`). **Recorded when wired:** tutor LLM
   (tool rounds + gate-repair merged into one event; thinking billed at output
   rate when reported separately; cached-input discount), focus-rail LLM (when
   usage present), server TTS **success** only, batch STT (`/api/audio/transcribe`),
   teach-image flat $/image on `miss_generated` (all three resolution sites
   after the countersign fix). Pricing table with longest-prefix match; env
   override `COST_PRICING_JSON`; unknown models tracked but flagged `unpriced`
   (never silently $0-priced). Report CLI: `python -m tutor.costs` (per-day /
   category / source; days = LOCAL calendar days, converted from UTC events).
   Prices used (verified via official pages 2026-07-28): gemini-3.6-flash $1.50/M in,
   $0.15/M cached, $7.50/M out (audio input same as text on this model per Google
   listings); flash-preview-tts $0.50/M in, $10/M out; also price TTS fallbacks
   gemini-3.1-flash-tts-preview and gemini-2.5-pro-preview-tts at $1.00/$20.00;
   flash-image ≈ $0.039/image (1290×$30/1M); grok-3-mini $0.30/$0.50 (third-party;
   not on xAI primary models table as of 2026-07-28 — re-verify if FOCUS_MODEL
   redirects).
2. **Prompt-block reorder for caching** (`tutor/executor.py`
   build_ai_tutor_system): static-first order stance → persona → pack →
   personal-context → ability sheet (sheet changes every turn so it goes
   last; anything after a changed block cannot prefix-cache). Measured
   effect: 0 → ~16.3k cached tokens/turn (~69% of input), per-turn tutor
   cost ~$0.036 → ~$0.014. Conv smoke 7/7 after reorder (teaching behavior
   gate). Anthropic cache_control marker moved to the pack block (end of
   stable prefix).
3. **One-block TTS** (`app.js` speak): entire on-screen reply in a single
   TTS call — replaces model→400ms-gap→try segmenting (learner complaint:
   mid-reply pauses + multiple voice calls). Interruption token unchanged.
4. **Cache-buster discipline**: bumped `?v=` for app.js/styles.css
   (2026-07-28 incident: shipped JS without bumping → user ran stale code);
   recorded as project memory.

Known gaps (declared, not hidden): streaming STT (`/ws/stt` live path) and
Chirp are untracked (no usage plumbing yet); TTS/STT **failed attempts** before
a success are not recorded (under-count); browser speechSynthesis is
free/untracked; ledger events are stored UTC and bucketed to LOCAL days at
report time; `today_usd` re-reads the whole ledger per sheet paint (fine at
current file sizes); cross-process appends rely on OS O_APPEND line atomicity
(no flock). Image costs: post-reply AI-path generation and rules/planned
`assets_for_plan` were untracked at ship — closed via `_note_image_costs`
at all three sites (2026-07-28).

Review asks: verify prices; find AI call sites NOT covered by the tracker;
check the reorder for pedagogy/caching correctness; poke the ledger/tracker
design for double-counting or missed attribution.


---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-28 01:28 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

## Countersign — cost tracking + prompt-cache + TTS batch (Claude, 2026-07-28)

Verified against inlined code + official pricing pages fetched **2026-07-28**. Proposal treated as data, not authority.

---

### Item 1 — Cost tracking (`tutor/costs.py` + call-site wiring)

**AMEND**

#### Pricing verification (2026-07-28)

| Model / assumption | Claimed | Official (as of 2026-07-28) | Verdict |
|---|---|---|---|
| `gemini-3.6-flash` in/cached/out | $1.50 / $0.15 / $7.50 per 1M | ai.google.dev Standard: **$1.50 / $0.15 / $7.50**; thinking billed as output | **OK** |
| Audio input = text rate (STT on 3.6-flash) | assumed same | Developer API lists a single input price for 3.6 Flash; Cloud Agent Platform lists input as text/image/video/**audio** at **$1.50** | **OK for default STT model** |
| `gemini-2.5-flash-preview-tts` | $0.50 in / $10 out | Official TTS table: **$0.50 (text) / $10.00 (audio)** | **OK** |
| `gemini-2.5-flash-image` flat | ≈$0.039/image | Official: output **$0.039/image**; footnote: 1290 tokens × $30/M = **1290 × 30 / 1e6 = 0.0387 ≈ 0.039** | **OK** |
| Image table `input: 0.30`, `output: 30` | present | Matches official token rates; **unused** by `add_image` (flat path only). Input undercount ~800 tok × $0.30/1M = **$0.00024**/image — noise | **OK** |
| `grok-3-mini` | $0.30 / $0.50 | **Not on** current primary xAI models table (2026-07-28 fetch lists 4.5/4.3/4.20/build). Third parties still quote $0.30/$0.50; one secondary source claims deprecation + silent redirect billing | **Keep rates if model still resolves; document as legacy/unconfirmed primary** |

**Table holes (real $ → tracked as unpriced $0):**

- `gemini-3.1-flash-tts-preview` — official **$1.00 / $20.00** (in TTS fallback list in `tutor/tts.py`)
- `gemini-2.5-pro-preview-tts` — official **$1.00 / $20.00** (also in fallback list)
- Any non-default `STT_MODEL` with **modality-split** audio (e.g. Gemini 2.5 Flash audio **$1.00** vs text **$0.30** → **3.33×** underbill if treated as text)

#### Coverage hunt (inlined code only)

| Site | File / function | Through tracker? |
|---|---|---|
| Tutor LLM (+ tool rounds, gate repair merge) | `conv_session.tutor_turn` → `_finish` → `costs.add_llm("tutor",…)` | **Yes** (merged once) |
| Focus rail AI | `_note_focus_cost` ← `_refresh_focus` / async `_work` | **Yes** when usage present |
| Server TTS success | `web_app.audio_speak` → `add_llm("tts",…)` | **Yes** |
| Batch STT | `web_app.audio_transcribe` → `add_llm("stt",…)` | **Yes** |
| Teach image (pre-turn AI path) | AI turn ~L795–807 `add_image` on `miss_generated` | **Yes** |
| **Post-reply image gen** | `conv_session` ~L997–1010 second `assets_for_ai_turn` | **NO** — can generate after tutor; never `add_image` |
| **Rules/planned path images** | `_turn_planned` / `assets_for_plan` ~L1129+ | **NO** — no `add_image` |
| Streaming STT | `web_app.ws_stt` → `stt_stream_mod.run_stream_session` | **NO** (declared) |
| Chirp | `stt_chirp` (imported; not plumbed to costs) | **NO** (declared) |
| TTS failed attempts | `tts.synthesize_gemini` nested model×prompt×attempt; only success returns usage | **Under-count** (billable fails invisible) |
| STT schema fallback second POST | `stt.transcribe_gemini` 400/404 retry | **Under-count** first attempt |
| `ai_student` / evals / planner LLM | not in inlined set; session label would cover if they use `ConversationalSession` | **Unknown from inlined files** |
| Browser `speechSynthesis` | — | free; correctly out of scope |

Proposal line “Every AI call type is recorded” is **false** even after declared gaps (post-reply images + planned-path images).

#### Double-counting

| Path | Ruling |
|---|---|
| Tool rounds + gate-repair | **No double-count.** `tutor_turn` sums usage; repair merges `usage2` into `usage`; single `_finish` → one `add_llm` |
| TTS retries | **No double-count; under-count** failures |
| Focus static then AI | Static has no usage; AI once — **OK** |
| Thinking tokens | `add_llm` bills `(output + thinking) * out_rate`. Safe **only if** OpenAI-compat `completion_tokens` excludes `reasoning_tokens` (code comment asserts this). If ever included, overbill: e.g. 2 000 think tokens × $7.50/1M = **$0.015** extra per turn |

#### Ledger design

- Append-only JSONL + in-process `threading.Lock`: fine single-process; **not** cross-process safe (multi-worker / CLI+web race).
- Timestamps: **UTC** ISO (`datetime.now(timezone.utc)`); day key `ts[:10]` is **UTC calendar day**. Local evening (e.g. US) can land in next UTC “day” — `today_usd` can disagree with operator’s local day.
- Unbounded growth + full re-read per `sheet_public()`: acceptable at current scale; declare.

#### Exact replacement — proposal item 1 text

```markdown
1. **Cost tracking** (`tutor/costs.py`): per-session tracker + cross-process
   append-only ledger (`logs/costs.jsonl`). **Recorded when wired:** tutor LLM
   (tool rounds + gate-repair merged into one event; thinking billed at output
   rate when reported separately; cached-input discount), focus-rail LLM (when
   usage present), server TTS **success** only, batch STT (`/api/audio/transcribe`),
   teach-image flat $/image on **pre-turn** AI-path `miss_generated` only.
   Pricing table with longest-prefix match; env override `COST_PRICING_JSON`;
   unknown models tracked but flagged `unpriced` (never silently $0-priced).
   Report CLI: `python -m tutor.costs` (per-day / category / source; days = UTC).
   Prices used (verified via official pages 2026-07-28): gemini-3.6-flash $1.50/M in,
   $0.15/M cached, $7.50/M out (audio input same as text on this model per Google
   listings); flash-preview-tts $0.50/M in, $10/M out; also price TTS fallbacks
   gemini-3.1-flash-tts-preview and gemini-2.5-pro-preview-tts at $1.00/$20.00;
   flash-image ≈ $0.039/image (1290×$30/1M); grok-3-mini $0.30/$0.50 (third-party;
   not on xAI primary models table as of 2026-07-28 — re-verify if FOCUS_MODEL
   redirects).
```

#### Exact replacement — `PRICING` block in `tutor/costs.py`

```python
PRICING: dict[str, dict[str, float | None]] = {
    # Tutor / STT default (ai.google.dev 2026-07-28): $1.50/M in, $0.15/M cached,
    # $7.50/M out; thinking bills as output. 3.6 Flash lists unified multimodal input.
    "gemini-3.6-flash": {"input": 1.50, "input_cached": 0.15, "output": 7.50},
    # Server teach voice — Flash TTS (ai.google.dev 2026-07-28)
    "gemini-2.5-flash-preview-tts": {"input": 0.50, "input_cached": None, "output": 10.00},
    # TTS fallbacks also tried by tutor/tts.py _models_to_try
    "gemini-3.1-flash-tts-preview": {"input": 1.00, "input_cached": None, "output": 20.00},
    "gemini-2.5-pro-preview-tts": {"input": 1.00, "input_cached": None, "output": 20.00},
    # Teach images ($30/M image-output tokens; 1290 tok ≈ $0.039/image)
    "gemini-2.5-flash-image": {"input": 0.30, "input_cached": None, "output": 30.00},
    # Focus rail — legacy slug; rates from secondary sources 2026-07; primary
    # xAI models page no longer lists grok-3-mini as of 2026-07-28
    "grok-3-mini": {"input": 0.30, "input_cached": None, "output": 0.50},
}
```

#### Exact code — close image coverage holes in `tutor/conv_session.py`

After **both** image resolution sites that can `miss_generated`, call one helper (add near `_note_focus_cost`):

```python
def _note_image_costs(self, teach_images: list | None) -> None:
    generated = sum(
        1 for t in (teach_images or [])
        if (t.get("cache") or "") == "miss_generated"
    )
    if not generated:
        return
    try:
        from .image_gen import image_model
        img_model = image_model()
    except Exception:
        img_model = "gemini-2.5-flash-image"
    self.costs.add_image(img_model, generated)
```

- Replace the inline block at ~L795–807 with `self._note_image_costs(teach_images)`.
- After the second `assets_for_ai_turn` (~L997–1010), add `self._note_image_costs(teach_images)`.
- After `assets_for_plan` in the planned path (~L1129–1139), add `self._note_image_costs(teach_images)`.

#### Exact replacement — Known gaps section

```markdown
Known gaps (declared, not hidden): streaming STT (`/ws/stt` live path) and
Chirp are untracked (no usage plumbing yet); TTS/STT **failed attempts** before
a success are not recorded (under-count); browser speechSynthesis is
free/untracked; ledger day buckets are **UTC** (`ts[:10]`), so `today_usd` may
disagree with local calendar day; `today_usd` re-reads the whole ledger per
sheet paint (fine at current file sizes); cross-process appends rely on OS
O_APPEND line atomicity (no flock). Image costs: post-reply AI-path generation
and rules/planned `assets_for_plan` were untracked at ship — fix via
`_note_image_costs` above before treating coverage as complete.
```

---

### Item 2 — Prompt-block reorder for caching (`build_ai_tutor_system`)

**COUNTERSIGN** on the mechanism; **AMEND** docstring + known pedagogy limit.

**Caching soundness**

- Code order: stance → persona → pack (`cache_control: ephemeral`) → personal_context → sheet. Matches “static prefix, sheet last.”
- Gemini path joins system blocks in order into one `system` string (`providers.messages_to_openai`) — static-first prefix is the right shape for **implicit** cache if the provider matches on shared prefix.
- Anthropic: `cache_control` on the **pack** block correctly ends the stable prefix; personal_context + sheet stay uncached. Correct placement.
- Measured 0 → ~16.3k cached (~69%) is directionally plausible; my rough recompute with 16.3k cached / ~23.6k input + 1.2k output-class tokens yields ~$0.022 vs ~$0.044 uncached (order-of-magnitude with claimed $0.014 / $0.036, not a rejection).

**Pedagogy risk smoke evals miss**

- Reorder does not change *content*, only block order. Smoke 7/7 only gates coarse teaching behavior.
- Residual risk: primacy/recency bias — large pack before sheet could dilute attention to `next_best` / active errors vs pack palette. Opposite risk (sheet last = recency help) also possible. **Not a REJECT**, but do not treat 7/7 as proof of “no teaching regression.”
- personal_context mid-stack: when name/L1 updates mid-session, cache prefix after pack still holds; only post-breakpoint bytes refresh — fine.

**Exact replacement** — docstring on `build_ai_tutor_system`:

```python
    """System blocks in cache-friendly order: stance → persona → pack →
    personal_context → ability sheet (sheet last; it changes every turn)."""
```

---

### Item 3 — One-block TTS (`app.js` speak)

**COUNTERSIGN** (intent / product fix), with scope limit:

- `app.js` was **not** inlined; cannot binary-verify the single-call implementation.
- Server path records **one** successful `add_llm("tts",…)` per `/api/audio/speak` — consistent with one-block design.
- TTS multi-model/prompt retries still under-count failures (Item 1); not double-count.

No text AMEND required if client ships one request per reply.

---

### Item 4 — Cache-buster discipline (`?v=` bump)

**COUNTERSIGN** as project process/memory. No code in inlined set to re-verify; agree the 2026-07-28 stale-JS incident is a real ops failure mode worth remembering.

---

### Summary scorecard

| # | Topic | Verdict |
|---|---|---|
| 1 | Cost tracking + prices + coverage | **AMEND** (table gaps, image sites, “every call” overclaim, UTC ledger day) |
| 2 | Cache reorder | **COUNTERSIGN** + docstring AMEND; pedagogy residual risk noted |
| 3 | One-block TTS | **COUNTERSIGN** (app.js not inlined) |
| 4 | Cache-buster discipline | **COUNTERSIGN** |

**Not REJECTED:** core design (session tracker + JSONL ledger + unpriced flag + static-first system blocks + success-path TTS/STT pricing for primary models) is sound and should stay. Do not ship “coverage complete” until post-reply + planned-path `add_image` and TTS fallback prices land.

---

## Adjudication (Claude, 2026-07-28)

Ruling on the Grok countersign:

- **Item 1 (cost tracking) AMENDs — ALL ACCEPTED.**
  - *Pricing*: table verified OK for tutor/TTS/image; the two TTS fallback
    models were real holes (would have billed as unpriced $0 on a fallback
    day) — added at $1.00/$20.00 per Grok's official-page fetch. grok-3-mini
    comment updated to note it is off xAI's primary table.
  - *Coverage*: Grok found two genuinely untracked image-generation sites
    (post-reply assets_for_ai_turn; rules-path assets_for_plan). Verified in
    code at the cited locations. Fixed with the proposed `_note_image_costs`
    helper called at all three sites.
  - *Overclaim*: "Every AI call type is recorded" was false; proposal text
    and Known gaps replaced with Grok's exact wording (plus the image-fix
    status).
  - *UTC day bucketing*: accepted the finding, but COUNTERED the remedy —
    instead of documenting the UTC quirk, `ledger_report` now converts to
    LOCAL calendar days (learner is UTC-6; evening practice must not report
    as tomorrow). Reason to deviate: a report the operator must mentally
    timezone-shift is a report that gets misread.
  - *Failed-attempt undercount, O_APPEND note, thinking-token conditional*:
    accepted as declared limitations; no code change now.
- **Item 2 (cache reorder) — COUNTERSIGNED; docstring AMEND applied.**
  Grok's caution accepted: smoke 7/7 gates coarse behavior only and is not
  proof of "no teaching regression" from block-order attention shifts.
  Noted as a residual risk to watch in transcripts.
- **Items 3, 4 — COUNTERSIGNED, no action.** (app.js was not inlined in the
  round by design — client JS has no behavioral eval; the one-request-per-
  reply property is enforced by the single playServerSegment call path.)

**Status: CONVERGED (1 round).** All rulings resolved; fixes validated by
the unit suite + truncation gate (teacher-path behavior unchanged; conv
smoke not re-run — no prompt/mode changes in this batch beyond the already-
evaluated reorder).
