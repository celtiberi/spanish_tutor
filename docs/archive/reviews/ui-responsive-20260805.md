

---

## GROK (Grok Build CLI (1e1687c1cf6a)) - 2026-08-05 17:38 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

## Responsive UI countersign — 2026-08-05 (Grok independent)

**Subject:** Claude planned amendments (1–3) to `tutor/web_static/styles.css` (+ current layout in `index.html` / `styles.css` as of build stamp `?v=20260805a`).  
**Targets:** phone ~390px, tablet portrait ~810px, tablet landscape ~1024px, desktop.  
**Existing breakpoints:** 1100px (grades drops, chat+morph 2-col), 900px (1-col, chat `order:1`).

---

### Evidence (measured from current CSS, not vibes)

**Header horizontal budget** (`.app` pad `1rem` × 2 = 32px):

| Viewport | Content budget | All chrome single-row (approx) | Hide cost + voice-rate only |
|---|---:|---:|---:|
| 390px | 358px | ~1031px (no) | ~663px (no) |
| 810px | 778px | ~1031px (no) | ~663px (yes, one actions row + brand) |
| 1024px | 992px | ~1031px (borderline no) | ~663px (yes) |
| 1280px | 1248px | ~1031px (yes) | n/a |

Component widths used: brand ≈204px; cost-board min ≈146px; speak ≈115px; voice-rate ≈198px (`88px` slider + `6.4rem` label); ghost buttons Full sheet / New chat / Reset learner ≈98+83+123 = **304px**.

**Speak + 3 buttons alone ≈ 419px > 358px** → even after hiding cost + voice-rate, **390px still wraps the actions row**. “Compress header buttons” is required, not optional polish.

**Composer below fold** (messages `max-height: calc(100vh - 220px)` + composer ≈60 + mic hint ≈36 + app pad/margin ≈40):

| Header height (wrapped) | vh | Content used | Over fold |
|---:|---:|---:|---:|
| 72px (compact) | 844 | 832 | −12 (OK) |
| 120px (1 wrap) | 844 | 880 | **+36** |
| 180px (phone multi-wrap) | 844 | 940 | **+96** |
| 220px (worst) | 667 | 803 | **+136** |

Arithmetic:  
`used = header_h + 40 + (vh − 220) + 60 + 36 = vh + header_h − 84`  
→ over_fold ≈ `header_h − 84`. Any header taller than ~84px pushes the composer off-screen under the current messages max-height scheme.

**iOS focus zoom (item 3):** Safari zooms focused form controls when **computed** `font-size` &lt; **16px**. Sources: CSS-Tricks “16px or Larger Text Prevents iOS Form Zoom”; still reported 2025 (e.g. HeroUI issue #5326). Current `.composer textarea { font: inherit; }` inherits body; body has **no** `font-size`, so UA default is typically 16px today — fix is still correct as a **hard floor**, but currently may be a no-op until something shrinks root/body.  
`maximum-scale=1` is **not** in the viewport meta (good; do not add it).

**Voice-rate characterization:** UI copy documents pedagogical slow speech (`0.8× and below adds a deliberately slow speaking style`), not API/operator tooling. Cost-board is operator; voice-rate is learner control.

---

### Per-item arithmetic → rulings

#### (1) ≤900px: hide cost-board + voice-rate; compress header buttons

- Hide cost-board: frees ~146px; operator chrome; correct for learner phone UI.  
- Hide voice-rate: frees ~198px, but **misclassified** as “operator/power chrome.” On 390px the math still fails without button compression (**419 &gt; 358**), so rate-hide is **not** the load-bearing fix. Killing learner speed control for A1 TTS is the wrong trade.  
- Compress buttons: load-bearing at 390px.

**Ruling: AMEND** (not COUNTERSIGN as written)

**Exact replacement** — extend the existing `@media (max-width: 900px)` block and add header rules (do **not** hide `.voice-rate`):

```css
@media (max-width: 900px) {
  .main { grid-template-columns: 1fr; }
  .chat-panel { order: 1; }
  .rail { order: 2; }
  .journey { order: 3; }

  /* Operator chrome only — keep learner voice controls */
  .cost-board { display: none; }

  .top {
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.35rem 0 0.5rem;
  }
  .brand .sub { display: none; } /* status can live in title attribute / aria if needed */
  .logo { width: 36px; height: 36px; border-radius: 10px; }
  h1 { font-size: 1rem; }
  .build-stamp { display: none; }

  .header-actions {
    width: 100%;
    gap: 0.35rem;
    justify-content: flex-start;
  }
  .header-actions .btn.ghost {
    padding: 0.45rem 0.55rem;
    font-size: 0.8rem;
    min-height: 44px; /* ≥44px touch target */
  }
  /* Short labels: pair with HTML data-short or aria-label; CSS-only fallback: */
  #sheetToggle { max-width: 5.5rem; overflow: hidden; text-overflow: ellipsis; }
  #newChat { max-width: 5.5rem; }
  #resetLearner { max-width: 5.5rem; }

  /* Compact voice rate — keep visible; shrink chrome, not the control */
  .voice-rate input[type="range"] { width: 72px; }
  .voice-rate span { min-width: 0; font-size: 0.75rem; }

  .app { padding: 0.5rem 0.65rem 0.65rem; }
}
```

**HTML companion (required for honest short labels, not CSS-only ellipsis on critical actions):**

```html
<button … id="sheetToggle" aria-label="Full character sheet">Sheet</button>
<button … id="newChat" aria-label="New chat (keep learner sheet)">New</button>
<button … id="resetLearner" aria-label="Wipe character sheet and start a blank learner">Reset</button>
```

Optional: if vertical header height is still &gt;1 row at 390 after the above, move `.voice-rate` into a second-row full-width strip — **do not** remove it.

---

#### (2) chat-panel height = `100dvh` − compact header so composer stays on-screen

Direction is correct: current failure is real (see over_fold arithmetic). Proposal is **incomplete** as stated.

Conflicts in current CSS:
- `.messages { min-height: 50vh; max-height: calc(100vh - 220px); }`  
  With a flex column chat-panel of fixed height, **`min-height: 50vh` fights the flex child** and **`max-height: 100vh-220` ignores actual header height**.
- `.chat-panel` has **no** height today; `flex: 1` on `.messages` does nothing useful without a bounded parent.
- `100dvh` alone: no `100vh` fallback; no safe-area; iOS keyboard does **not** shrink `dvh` (composer can still sit under keyboard — flag, not a ship-blocker for this round).

**Ruling: AMEND**

**Exact replacement** (global messages fix + ≤900 chat shell):

```css
/* Replace the height rules on .messages (base) */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-height: 0;              /* was 50vh — kills flex shrink */
  max-height: none;           /* was calc(100vh - 220px) — wrong subtractor */
}

@media (max-width: 900px) {
  /* …keep grid order rules from (1)… */

  .app {
    min-height: 100vh;
    min-height: 100dvh;
    padding-bottom: max(0.65rem, env(safe-area-inset-bottom, 0px));
  }

  .main {
    margin-top: 0.5rem;
    /* chat is order 1; do not force main to fill — panel owns the viewport band */
  }

  .chat-panel {
    /* Header is variable; use a CSS var set once, with a safe default */
    --mobile-header-band: 7.5rem; /* ~120px; tune if brand+actions wrap to 2 rows */
    height: calc(100vh - var(--mobile-header-band));
    height: calc(100dvh - var(--mobile-header-band) - env(safe-area-inset-bottom, 0px));
    max-height: calc(100dvh - var(--mobile-header-band) - env(safe-area-inset-bottom, 0px));
    min-height: 0;
  }

  .composer {
    flex-shrink: 0;
  }
  .hint.mic-status {
    flex-shrink: 0;
  }

  /* Stacked rails scroll *below* the chat shell — not inside it */
  .rail,
  .journey {
    position: static;
    max-height: none;
  }
}
```

**Do not** set chat-panel to full `100dvh` without subtracting header — that puts the composer under the fold by one header height (`100dvh` panel + header &gt; `100dvh`).

If `--mobile-header-band: 7.5rem` is wrong after (1) compresses the header, remeasure once; prefer one small JS line `document.documentElement.style.setProperty('--mobile-header-band', top.offsetHeight + 'px')` on load/resize over a magic constant. CSS-only default above is acceptable to ship if band is rechecked at 390.

---

#### (3) Explicit 16px textarea font (iOS focus zoom)

Fact is sound. Scope is incomplete: `.game-input` also uses `font: inherit` and sits in `.messages` (same zoom class of bug). Prefer **px**, not `1rem`, so a later root `font-size` tweak cannot reintroduce zoom.

**Ruling: AMEND** (tiny)

```css
.composer textarea {
  flex: 1;
  resize: none;
  max-height: 140px;
  min-height: 44px;
  padding: 0.65rem 0.8rem;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-family: inherit;
  font-size: 16px;   /* iOS Safari: <16px computed → focus zoom */
  line-height: 1.35;
}

.game-input {
  font-family: inherit;
  font-size: 16px;   /* same floor; was font: inherit */
  background: rgba(0,0,0,0.2);
  color: inherit;
  border: 1px solid var(--border, #444);
  border-radius: 10px;
  padding: 0.45rem 0.7rem;
  width: 100%;
  max-width: 22rem;
  min-height: 44px;  /* touch */
  transition: border-color 0.12s ease, background 0.12s ease;
}
```

---

### ELSE — breaks at those widths not covered by Claude’s three items

| # | Issue | Widths | Severity | Exact fix |
|---|---|---|---|---|
| E1 | **Header still wraps hard at 390** after hide cost+rate (actions ≈419px &gt; 358) | 390 | High | Short button labels in HTML (see item 1); optional hide `.build-stamp` / `.sub` |
| E2 | **Touch targets &lt;44px**: `.journey-toggle` pad `0.2rem 0.55rem`; `.dbg-tab` / `.dbg-turn-btn` ~22px tall; `.game-progress i` is 7×7 (display-only OK) | all touch | Medium | `@media (max-width:900px){ .journey-toggle,.dbg-tab,.dbg-turn-btn{ min-height:44px; padding:0.45rem 0.65rem; } .game-tile,.game-opt-btn,.game-check{ min-height:44px; } }` |
| E3 | **`.match-wrap` two columns** on 390 → ~`(358−16)/2 ≈ 171px` cols; usable but cramped; long Spanish strings wrap awkwardly | 390 | Low–Med | `@media (max-width:900px){ .match-wrap{ flex-direction:column; } }` |
| E4 | **`.game-input` max-width 22rem** OK; **tile rows** fine with wrap; ensure game cards don’t force horizontal page scroll: `.game-card{ max-width:100%; overflow-wrap:anywhere; }` | 390 | Med if overflow | add `max-width:100%` on `.game-card` / `.bubble` already has `word-break` |
| E5 | **Debug box** always in document flow under main; open `dbg-view { max-height: calc(100vh - 14rem) }` OK; on phone when opened after long chat+rails, fine. Collapsed summary touch target: pad is OK (~0.55rem). No hide required. | all | Low | none required |
| E6 | **Sheet modal** `max-height: min(88vh,900px)` OK; overlay pad `1rem` OK. **`.sheet-head-actions`** can crowd on 390 with Copy+Close. | 390 | Low | `@media (max-width:900px){ .sheet-modal{ max-height: min(92dvh, 900px); padding: 0.75rem; } .sheet-head{ flex-wrap: wrap; } .sheet-body{ font-size: 0.7rem; } }` |
| E7 | **1024 landscape** still in 2-col (chat+morph); header may wrap once (~1031 need vs 992 budget) with cost+rate visible | 1024 | Low | Optional `@media (max-width:1100px){ .cost-board{ flex-basis:140px; } .voice-rate input{ width:72px; } }` — not hide |
| E8 | **Sticky rails** `max-height: calc(100vh - 120px)` with `position:sticky` becomes noise in 1-col; set `static` + `max-height:none` under 900 (included in item 2 CSS) | ≤900 | Med (scroll traps) | see item 2 |
| E9 | **iOS keyboard vs `dvh`**: fixed chat height leaves composer under keyboard | 390 | Med residual | out of pure CSS; follow-up = `visualViewport` resize or accept scroll-into-view on focus (browsers often scroll focused textarea into view if not `position:fixed`) — **do not** use `position:fixed` composer without viewport JS |
| E10 | **Tap-audio** chip already padded; mic/send 44×44 OK — leave | 390 | OK | — |

---

### Kill-search (this round)

1. **Tried to kill item 3** (“already 16px via inherit → redundant”): falsifier would be DevTools computed `font-size` on `#input` **&lt; 16px**. Without a live device sample, UA default is 16px, so the *bug-today* claim is weak; the *pin the floor* claim survives. Not killed.  
2. **Tried hardest to kill item 1’s “hide voice-rate as operator chrome”:** **killed.** Cost-board is operator; voice-rate is learner pedagogy (slow TTS). Falsifier that would have saved Claude’s claim: product decision that rate is dev-only — **not** present in UI copy or recent commits (`7208bf2` invests in mobile voice playback).  
3. **Tried to kill item 2 entire:** failed — fold arithmetic shows composer off-screen whenever header &gt; ~84px under current `100vh-220` messages cap.

---

### CORRELATED_AGREE note

Agreement with Claude on (2) direction and (3) 16px floor is **one correlated RLHF vote** until device-measured. Independence here is the voice-rate kill + the messages min/max-height conflict Claude’s one-liner omitted.

---

### OVERALL STATUS

**ACCEPT_WITH_AMENDS**

| Item | Verdict |
|---|---|
| (1) hide cost + voice-rate; compress header | **AMEND** — hide **cost-board only**; **keep** voice-rate (compact); **must** shorten button labels (HTML); compress pad/type |
| (2) chat-panel `100dvh` − header | **AMEND** — required, but also **delete** `.messages` `min-height:50vh` / `max-height:calc(100vh - 220px)`; subtract header band + safe-area; unstick rails ≤900 |
| (3) 16px textarea | **AMEND** — ship `font-size:16px` on textarea **and** `.game-input` |
| ELSE | **E1–E3, E6, E8** should ship in the same PR; E9 documented residual |

Ship gate: after CSS, hard-refresh at **390 / 810 / 1024** and confirm (a) composer visible without scroll on load, (b) voice rate still reachable, (c) no iOS focus zoom on `#input`, (d) game match columns stack on phone.

---

## Adjudication (Claude, 2026-08-05)

- **A1 ACCEPTED with Grok's kill honored:** voice-rate reclassified as
  learner pedagogy (slow TTS) — kept and compacted; cost-board alone
  hides. Short button labels shipped in HTML (Sheet / New chat / Reset,
  full text in title+aria) — real labels, not CSS ellipsis.
- **A2 ACCEPTED, one counter:** the `.messages` min/max-height removal
  is scoped to ≤900px only — removing it globally would unbound the
  DESKTOP chat column (no fixed-height parent there) and push the
  composer below the fold on long desktop chats, the exact bug being
  fixed. Header band adopted as the measured JS variable (offsetHeight
  + 24) rather than any constant, per Grok's own preference.
- **A3 ACCEPTED:** 16px floor on composer textarea AND .game-input
  (px, not rem), 44px min-height on game input.
- **E1–E3, E6, E8 shipped; E7 shipped (compact, not hide). E9 (iOS
  keyboard vs dvh) recorded as the known residual — browsers scroll
  the focused textarea into view; no position:fixed composer without
  visualViewport JS.**

Ship gate (manual, USER device): 390/810/1024 — composer visible on
load, voice rate reachable, no focus zoom, match columns stacked.
