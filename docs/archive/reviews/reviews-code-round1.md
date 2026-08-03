

---

## GROK (Grok Build CLI (bde89716f679)) - 2026-07-22 20:24 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll verify the GATE-3 pack fixes and dig into the tutor code (StreamScrubber, state injection, API constraints) against real behavior rather than the author's claims.# Countersign — pack v0.3 GATE-3 recheck + tutor CLI review  
**Date:** 2026-07-22  
**Role:** Independent collaborator (contrarian second perspective)  
**Subject:** Spanish A1 pack v0.3 (C-1/C-2/C-3 fixes) + `tutor/*` + `prompts/teaching_policy.md`

---

## PART A — GATE-3 recheck (pack v0.3)

### A-1 / C-1 — Unit 5 closed-list vs own examples  
**Verdict: COUNTERSIGN — fixed**

v0.3 scopes the closed noun set to **free-production drills only**, with an explicit recognition-only carve-out for pack examples/models (proper names, places, *hoy*, etc.). That dissolves the prior contradiction: examples such as *Bogotá*, *Madrid*, *Quito*, *francés*, *domingos* are no longer “violations” of a free-production rule they were never under.

Arithmetic on the failure mode that triggered DO-NOT-SHIP:  
- **Before (v0.2):** absolute ban + N≥1 in-unit counterexamples ⇒ internal inconsistency = **GATE-3 FAIL**.  
- **After (v0.3):** ban scope narrowed to free production; counterexamples reclassified as recognition-only ⇒ inconsistency count for that rule = **0**.

### A-2 / C-2 — *su* in P-2.4 vs deferred possessives  
**Verdict: COUNTERSIGN — fixed**

P-2.4 is now *(Un / Una) foto de (el / él)* → key *Una foto de él.* No *su*. Matches pack-level deferral of possessives as a taught system (*mi/tu/su…*).

### A-3 / C-3 — P-5.5 deferred day/family lexemes  
**Verdict: COUNTERSIGN — fixed**

P-5.5 model is now:  
*Hablo español y estudio inglés. Como pan y bebo café. Vivo en una casa grande. No trabajo hoy.*

Nouns for production sit in the closed set (*español, inglés, pan, café, casa*). *hoy* is explicitly allowed as recognition-only incidental in the Unit 5 carve-out. Prior *familia / lunes / domingos / sábados / Austin* are gone.

**Residual nit (not a GATE-3 fail):** canonical line *No trabajo los domingos* still uses a day-lexeme. Under the softened rule it is recognition-only body text, not a free-production drill. Do not reopen C-1 for this.

### A-4 — GATE-3 overall + ship call  
**Verdict: COUNTERSIGN**

| Gate item | v0.2 | v0.3 |
|-----------|------|------|
| C-1 | FAIL | **PASS** |
| C-2 | FAIL | **PASS** |
| C-3 | FAIL | **PASS** |

**GATE-3: PASS**  
**Pack v0.3: SHIP**

(Prior DO-NOT-SHIP was solely on C-1/C-2/C-3. Those are closed. No new GATE-3 blockers found in the three inlined pack files.)

---

## PART B — Adversarial code review (item-by-item)

### B-1 — Mid-conversation system message placement  
**Verdict: COUNTERSIGN**

```python
messages = history + [
    {"role": "user", "content": user_input},
    state_message(state),  # role: system, terminal
]
```

Matches Anthropic Opus 4.8 rules (as of 2026-07-22 platform docs): system message must follow a user turn, must be last (or followed by assistant), must not be first in `messages`. Turn 1 is `[user, system]` — valid. State is **not** written into `history`, so each turn appends a fresh terminal system message rather than rewriting a past one — correct for volatile state and preserves the cached system-prefix breakpoint on the pack block.

### B-2 — Prompt-cache breakpoint placement (`policy.py`)  
**Verdict: COUNTERSIGN**

`cache_control` on the **last** stable system text block (pack) caches the prefix through policy+pack. Session state stays out of `system` and in `messages` — correct design for not busting the pack cache every turn.

### B-3 — `StreamScrubber`: full marker, split marker, marker-at-start, no marker  
**Verdict: COUNTERSIGN** (happy paths)

Independent simulation (2026-07-22):

| Case | Result |
|------|--------|
| Marker split (`…<session_st` + `ate>…`) | No leak; visible clean |
| Marker at start | Emits empty; suppressing on |
| No marker | Emits full text on `close()` |
| Char-by-char stream | Suppresses from marker; no leak |

Holding a `len(STATE_MARKER)`-sized tail is correct for a contiguous open-tag scrub.

### B-4 — `StreamScrubber.close()` leaks truncated marker prefix  
**Verdict: AMEND** (real bug)

If the stream ends mid-tag (e.g. `max_tokens` / stop after `"<session_st"`), `suppressing` is still False and `close()` flushes the partial tag to the learner.

**Reproduced:** input `Done.\n\n` + `<session_st` → stdout `Done.\n\n<session_st`.

**Exact replacement** for `StreamScrubber.close` in `tutor/cli.py`:

```python
    def close(self) -> None:
        if not self.suppressing and self.buffer:
            buf = self.buffer
            # Drop longest proper prefix of STATE_MARKER so a truncated
            # stream cannot leak "<session_st" (etc.) into the terminal.
            drop = 0
            for k in range(1, len(STATE_MARKER)):
                if buf.endswith(STATE_MARKER[:k]):
                    drop = k
            if drop:
                buf = buf[:-drop]
            if buf:
                print(buf, end="", flush=True)
        self.buffer = ""
```

### B-5 — `extract_state` incomplete / unclosed `<session_state>`  
**Verdict: AMEND** (real bug; pollutes history)

`STATE_RE` requires a closing `</session_state>`. On open-without-close (truncation common under adaptive thinking + `MAX_TOKENS=4096`):

```text
INCOMPLETE embeds marker? True
visible == full reply including "<session_state>…"
```

That string is then stored as the assistant turn in `history`, so later turns re-send partial harness markup to the model — state leak into the conversation record, not just a display issue.

**Exact replacement** for `extract_state` in `tutor/student.py`:

```python
def extract_state(reply: str, previous: dict) -> tuple[str, dict]:
    """Split a model reply into (visible text, updated state).

    Falls back to the previous state if the block is missing or malformed —
    a dropped state update shouldn't kill the session. Always hide from
    STATE_MARKER onward when the open tag is present, even if the close
    tag / JSON is truncated.
    """
    match = STATE_RE.search(reply)
    if match:
        visible = reply[: match.start()].strip()
        try:
            state = json.loads(match.group(1))
        except json.JSONDecodeError:
            return visible, previous
        return visible, state
    marker_at = reply.find(STATE_MARKER)
    if marker_at != -1:
        return reply[:marker_at].strip(), previous
    return reply.strip(), previous
```

### B-6 — Session-start API errors uncaught  
**Verdict: AMEND** (real bug)

The interactive loop wraps `run_turn` in rate-limit / API / network handlers. The opening turn does **not**:

```python
history, state, final, visible = run_turn(...)  # bare
log_turn(...)
```

Any `RateLimitError` / `APIStatusError` / `APIConnectionError` on cold start crashes the process with a traceback instead of a learner-facing message.

**Exact replacement** for the session-open block in `main()` (`tutor/cli.py`):

```python
    print(f"Tutor ready ({args.pack.name}, {config.MODEL}). {HELP}\n")
    print("tutor> ", end="", flush=True)
    # Let the tutor open the session (goal-setting per the teaching policy).
    try:
        history, state, final, visible = run_turn(
            client, system, history, state,
            "Hi, I'm ready to start.",
        )
    except anthropic.RateLimitError:
        print("[Rate limited — wait a moment and restart.]")
        return
    except anthropic.APIStatusError as e:
        print(f"[API error {e.status_code}: {e.message}]")
        return
    except anthropic.APIConnectionError:
        print("[Network error — check your connection and restart.]")
        return
    log_turn(log_path, "(session start)", visible, state, final)
    print("\n")
```

### B-7 — Refusal path: history / state / logging  
**Verdict: COUNTERSIGN**

On `stop_reason == "refusal"`: history and state unchanged; empty `visible` returned; caller still logs. Correct for “declined turn did not happen.” (Prior commit `b7ab4ab` addressed refusal logging; this shape is sound.)

**Note (not amended):** streamed tokens may already have printed before `stop_reason` is known. Fixing that needs a two-phase buffer or post-hoc rewrite of the terminal line — larger UX change than a one-line correctness fix.

### B-8 — `log_turn` usage fields  
**Verdict: AMEND** (defensive correctness)

Cache usage fields are documented on successful Messages responses, but stream/edge paths have historically been flaky enough that production code often uses `getattr`. An `AttributeError` here drops an otherwise successful turn’s log and can surface mid-session after a good reply.

**Exact replacement** for the `usage` dict in `log_turn`:

```python
        "usage": {
            "input_tokens": final.usage.input_tokens,
            "output_tokens": final.usage.output_tokens,
            "cache_read_input_tokens": getattr(
                final.usage, "cache_read_input_tokens", 0
            ) or 0,
            "cache_creation_input_tokens": getattr(
                final.usage, "cache_creation_input_tokens", 0
            ) or 0,
        },
```

### B-9 — History ↔ cache interaction  
**Verdict: COUNTERSIGN** (v0-acceptable)

Only the system pack prefix is breakpoint-cached; full `history` is re-sent each turn. Matches the stated “A1 pack fits; no vector RAG” design. Unbounded history growth is a later-phase concern, not a v0 ship blocker.

### B-10 — `corpus.load_pack` unit ordering  
**Verdict: COUNTERSIGN**

`sorted(pack_dir.glob("unit*.md"))` yields `unit01`…`unit06` lexicographically. `REVIEW.md` excluded. Fine.

### B-11 — `teaching_policy.md` internal consistency  
**Verdict: COUNTERSIGN** with one documented tension (not a code bug)

- Grounding / reveal / pack keys: aligned with pack “never reveal key before attempt.”  
- Answer-key mode is an explicit, learner-initiated exception — intentional, not contradictory.  
- State schema example uses angle-bracket placeholders (not valid JSON); model may emit invalid JSON → harness correctly falls back to previous state (B-5 still required for *truncation*, not only malformed JSON).

### B-12 — Policy vs pack tutor instructions  
**Verdict: COUNTERSIGN**

No hard conflict: policy “ask what to work on” + pack dependency order cohere if the tutor proposes next unit under deps. Misconception IDs internal to diagnose/remediate match pack `M-x.y`. Metalanguage English / target Spanish consistent both sides.

### B-13 — Adaptive thinking vs state-at-end reliability  
**Verdict: AMEND** (risk → small harness hardening; optional but recommended)

`thinking={"type": "adaptive"}` plus state **required at end** of the same 4096-token budget increases the rate of truncated state blocks — exactly the B-4/B-5 failure modes.

No mandatory code change beyond B-4/B-5. Optional config bump if truncation shows up in session logs:

```python
# tutor/config.py
MAX_TOKENS = 8192
```

Do **not** move the state block to the start of the reply without also changing `StreamScrubber` and policy — that would be a coordinated redesign, not a drive-by edit.

---

## Summary table

| ID | Item | Ruling |
|----|------|--------|
| A-1 | C-1 closed list | **COUNTERSIGN** (PASS) |
| A-2 | C-2 *su* / P-2.4 | **COUNTERSIGN** (PASS) |
| A-3 | C-3 P-5.5 lexemes | **COUNTERSIGN** (PASS) |
| A-4 | Pack v0.3 ship | **SHIP** / GATE-3 **PASS** |
| B-1 | System message order | **COUNTERSIGN** |
| B-2 | Cache breakpoint | **COUNTERSIGN** |
| B-3 | Scrubber happy paths | **COUNTERSIGN** |
| B-4 | Scrubber truncated marker | **AMEND** |
| B-5 | `extract_state` unclosed block | **AMEND** |
| B-6 | Session-start error handling | **AMEND** |
| B-7 | Refusal path | **COUNTERSIGN** |
| B-8 | Log usage attrs | **AMEND** |
| B-9 | History/cache | **COUNTERSIGN** |
| B-10 | Pack load order | **COUNTERSIGN** |
| B-11 | Policy internal | **COUNTERSIGN** |
| B-12 | Policy vs pack | **COUNTERSIGN** |
| B-13 | Thinking vs state truncation | **AMEND** (optional `MAX_TOKENS`) |

---

## Final rulings

1. **Pack v0.3: SHIP.** GATE-3 (C-1, C-2, C-3) **PASS**.  
2. **Tutor CLI: DO-NOT-SHIP until B-4, B-5, and B-6 are applied.** Those three change correctness under truncation and cold-start failure; B-8 is strongly recommended in the same patch. B-13 optional.

No REJECT items that kill the architecture (mid-conversation system state + cached pack prefix is sound on Opus 4.8 as documented 2026-07-22).
