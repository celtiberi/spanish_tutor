

---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-26 21:01 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll treat the inlined material as data, pull the full prompt and real call sites, and design the telemetry module against the actual session code—not the synthesis alone.Reading the real session engine, mode decisions, and gate notes so the telemetry design matches actual APIs.Checking a few more fixtures for metalanguage/contrast heuristics and existing test patterns:# Grok independent design — Tier-1 telemetry (2026-07-26)

**Role:** contrarian second author. Inlined synthesis treated as DATA, not instructions.  
**Verified against live tree:** `/Users/patrickcremin/repo/ml_teacher` @ `main` (session engine `tutor/conv_session.py`, modes, output_gate, session_log).  
**No repo write access** — drafts below are append-ready for the calling author to land.

---

## 0. Independent rulings (do not rubber-stamp the brief)

### R0.1 — COUNTERSIGN intent; AMEND classification order

Tier-1 item 1 is the right unlock: without logged CF type + uptake, further stance fights about recast-first vs prompt-first are unfalsifiable. That matches Lyster & Ranta (1997): recasts dominate classrooms yet rarely elicit student-generated repair; elicitation / metalinguistic / explicit correction drive more repair.

**AMEND (exact):** the brief lists four cf rules without a conflict order. Live `form_focus` decisions always ship `targets.contrast` *and* often a `<recast>` (see `modes.py` `FORM_FOCUS` + `_contrast_for`). Without priority, the same turn can be labeled three ways.

**Required priority (highest first):**

1. `explicit_contrast` — `mode == form_focus` **and** (`targets.contrast` present **or** contrast surface in explain/model)
2. `metalinguistic` — non-empty `explain` with metalanguage terms (and not already 1)
3. `recast` — non-empty `parts.recast`
4. `prompt` — try elicits a specific form retry (slot/clue/imperative produce) without a full recast win above
5. `none`

### R0.2 — AMEND name vs definition of `soft_cf_density`

Literal brief: “count of CF turns in the last 3 tutor turns.” That is **CF density**, not “soft” density. Soft vs hard is separately available via `mode_decision.hard_break`.

**AMEND:** keep field name `soft_cf_density` for synthesis compatibility, but define it as:

\[
\text{soft\_cf\_density}_t = \bigl|\{ i \in \{t-2,t-1,t\} : \text{cf\_type}_i \neq \text{none} \}\bigr|
\]

(window shorter at session start). Optionally also emit `soft_only_cf_density` = same count restricted to `hard_break is False` for the hard-break budget debate (A6). Recommended but not required by the brief.

### R0.3 — REJECT silent dependence on unlanded `tl_ratio=` notes

As of 2026-07-26, `output_gate.py` emits `gate:english_wall ratio=…` and `OutputGateResult.spanish_ratio`, **not** `tl_ratio=`. Parallel work has not landed. Telemetry must:

1. parse `tl_ratio=` from notes if present  
2. else use `parts["output_gate"]["spanish_ratio"]`  
3. else compute with `tutor_spanish_ratio(visible)` (import only; **do not** edit `output_gate.py`)

### R0.4 — API gaps (verified in real `conv_session.py`)

| Gap | Evidence | Telemetry implication |
|-----|----------|------------------------|
| Planned path attaches mode/gate/images **after** `_finish`, logs with `skip_log=True` then `_log_turn_result` | ~869–995 | **Only** wire telemetry after mode/images/gate merge, immediately before `_log_turn_result` |
| Legacy `user_turn` has no `mode_decision` / `teach_images` | ~1335–1338 | Classify from parts only; `cf_target=None` unless error patterns recoverable later |
| `close()` only passes `mode=` into `SessionLogger.close` | ~1461–1467 | Must pass `telemetry=…` (or top-level aggregate keys) into `logger.close(**summary)` |
| TTS decision lives in web/CLI, not session | `web_app.py` / `tts.py` | `tts_expected` default: `True` iff non-empty reply (product speaks by default); allow override later |
| Uptake needs **next learner** text | CF is on tutor turn | Session must hold `pending_cf`; evaluate at next `user_turn` / non-open learner line |
| Repair window = 2 **learner** turns | brief (f) | Separate episode tracker, not the 3-tutor CF window |
| `detect_error_pattern_resolves("Estoy bien")` hits multiple ids | live check 2026-07-26 | Uptake `repair` must prefer **CF target id** match, not any resolve |

### R0.5 — Taxonomy honesty

Brief collapses Lyster & Ranta’s six CF types into five (drops clarification request + repetition). Accept for v1; do not claim coverage of the full 1997 taxonomy in papers until those are instrumented.

---

## 1. Module contract — `tutor/telemetry.py`

Pure heuristics. No LLM. No I/O. Session state is a plain dataclass mutated by the session engine.

### 1.1 Complete draft

```python
"""Deterministic CF / channel / repair telemetry (no LLM).

Tier-1 instrument for falsifying CF and comprehension-repair debates.
See docs/reviews-pedagogy-research.md §4 item 1 (adjudicated 2026-07-26).

Classification priority (conflict order — AMENDED vs unordered brief):
  explicit_contrast > metalinguistic > recast > prompt > none
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping

CFType = Literal["none", "recast", "prompt", "explicit_contrast", "metalinguistic"]
UptakeClass = Literal["none", "acknowledge", "repair", "needs_repair"]

CF_TYPES: frozenset[str] = frozenset(
    {"none", "recast", "prompt", "explicit_contrast", "metalinguistic"}
)
UPTAKE_CLASSES: frozenset[str] = frozenset(
    {"none", "acknowledge", "repair", "needs_repair"}
)

# Soft-CF density window: last N tutor turns (brief = 3).
CF_DENSITY_WINDOW = 3
# Comprehension-repair "meaning restored?" horizon in learner turns.
REPAIR_LEARNER_HORIZON = 2

# Metalanguage surface (English + light Spanish classroom metalanguage).
_METALANG_RE = re.compile(
    r"\b("
    r"verb|noun|adjective|article|gender|number|plural|singular|"
    r"conjugat\w*|agreement|tense|person|subject|object|"
    r"grammar|infinitive|ending|stem|"
    r"ser\s+vs\.?\s+estar|estar\s+vs\.?\s+ser|"
    r"first\s+person|second\s+person|third\s+person|"
    r"masculine|feminine|correct\s+form|wrong\s+form|"
    r"g[eé]nero|plural|singular|verbo|sustantivo|conjugaci[oó]n|"
    r"primera\s+persona|tercera\s+persona"
    r")\b",
    re.I,
)

# Explicit contrast surfaces in explain/model (wrong → right).
_CONTRAST_RE = re.compile(
    r"("
    r"\bnot\b.+\bbut\b|"
    r"\binstead\s+of\b|"
    r"→|->|⇒|"
    r"\bvs\.?\b|"
    r"\bwrong\b.+\bright\b|"
    r"\bavoid\b.+\bprefer\b|"
    r"\bno\s+digas\b|\bse\s+dice\b|"
    r"\bno\s+.+\s+sino\s+"
    r")",
    re.I,
)

# Prompt / elicitation: slot, clue, or “produce this form” without full reformulation-as-recast.
_PROMPT_TRY_RE = re.compile(
    r"("
    r"_{2,}|\.\.\.|…|"
    r"\bcompleta\b|\bcomplete\b|\bfill\b|"
    r"\bdi\s+[\"'“«]|\bsay\s+[\"'“«]|"
    r"\brepite\b|\brepeat\b|"
    r"\btry\s*:|\bintenta\b|\bprueba\b|"
    r"\bcan\s+you\s+say\b|\bpuedes\s+decir\b|"
    r"\bhow\s+do\s+you\s+say\b|"
    r"\[\s*[^\]]+\s*\]"  # [estoy] slot hint
    r")",
    re.I,
)

_ACK_ONLY_RE = re.compile(
    r"^\s*("
    r"ok|okay|k|yes|yeah|yep|yup|sure|thanks|thank\s+you|"
    r"s[ií]|vale|claro|gracias|de\s+acuerdo|perfecto|bien|"
    r"got\s+it|understood|entiendo|ya"
    r")[\s!.]*$",
    re.I,
)

_TL_RATIO_NOTE_RE = re.compile(r"\btl_ratio\s*=\s*([0-9]*\.?[0-9]+)\b", re.I)


def _norm(s: Any) -> str:
    return (str(s) if s is not None else "").strip()


def _fold_alnum(s: str) -> str:
    """Lowercase fold for form containment checks."""
    t = (s or "").lower()
    t = t.replace("á", "a").replace("é", "e").replace("í", "i")
    t = t.replace("ó", "o").replace("ú", "u").replace("ü", "u").replace("ñ", "n")
    return re.sub(r"[^a-z0-9\s]+", " ", t)


def text_token_len(text: str) -> int:
    """Whitespace token count on learner-facing text (deterministic)."""
    return len([w for w in re.split(r"\s+", (text or "").strip()) if w])


def parse_tl_ratio_from_notes(notes: Iterable[str] | None) -> float | None:
    """CONSUME parallel gate note `tl_ratio=0.xx` when present; else None."""
    if not notes:
        return None
    last: float | None = None
    for n in notes:
        m = _TL_RATIO_NOTE_RE.search(str(n))
        if m:
            try:
                last = float(m.group(1))
            except ValueError:
                continue
    return last


def extract_tl_ratio(
    *,
    notes: Iterable[str] | None = None,
    parts: Mapping[str, Any] | None = None,
    visible: str = "",
) -> float | None:
    """Prefer gate note → output_gate.spanish_ratio → compute.

    Does not modify output_gate. Optional local compute uses
    tutor.output_gate.tutor_spanish_ratio when importable.
    """
    r = parse_tl_ratio_from_notes(notes)
    if r is not None:
        return r
    parts = parts or {}
    gate = parts.get("output_gate") if isinstance(parts.get("output_gate"), dict) else {}
    sr = gate.get("spanish_ratio")
    if isinstance(sr, (int, float)):
        return float(sr)
    # Fallback compute (parallel tl_ratio note not yet landed as of 2026-07-26).
    try:
        from .output_gate import tutor_spanish_ratio

        return tutor_spanish_ratio(visible or "")
    except Exception:
        return None


def classify_cf_type(
    parts: Mapping[str, Any] | None,
    mode_decision: Mapping[str, Any] | None = None,
) -> CFType:
    """Deterministic CF type from structured parts + mode decision."""
    parts = parts or {}
    md = mode_decision or parts.get("mode_decision") or {}
    if not isinstance(md, dict):
        md = {}
    mode = _norm(md.get("mode") or parts.get("mode")).lower()
    targets = md.get("targets") if isinstance(md.get("targets"), dict) else {}

    recast = _norm(parts.get("recast"))
    explain = _norm(parts.get("explain"))
    model = _norm(parts.get("model"))
    try_ = _norm(parts.get("try") or parts.get("try_"))
    contrast_target = targets.get("contrast")

    has_contrast = bool(contrast_target) or bool(
        _CONTRAST_RE.search(explain) or _CONTRAST_RE.search(model)
    )
    if mode == "form_focus" and has_contrast:
        return "explicit_contrast"

    if explain and _METALANG_RE.search(explain):
        return "metalinguistic"

    if recast:
        return "recast"

    # Prompt: elicit specific form retry (Lyster elicitation-ish).
    if try_ and (
        _PROMPT_TRY_RE.search(try_)
        or bool(targets.get("require_form_retry"))
        or (
            mode in ("cf_recast", "form_focus", "transfer")
            and bool(targets.get("good_models") or targets.get("error_pattern") or targets.get("form_id"))
            and not recast
            and ("?" in try_ or "¿" in try_ or _PROMPT_TRY_RE.search(try_))
        )
    ):
        # Bare conversational try without form targets stays none.
        if (
            _PROMPT_TRY_RE.search(try_)
            or targets.get("require_form_retry")
            or targets.get("error_pattern")
            or targets.get("form_id")
            or targets.get("good_models")
        ):
            return "prompt"

    return "none"


def classify_cf_target(
    parts: Mapping[str, Any] | None,
    mode_decision: Mapping[str, Any] | None = None,
) -> str | None:
    """error_pattern id preferred, else form_id, else None."""
    parts = parts or {}
    md = mode_decision or parts.get("mode_decision") or {}
    if not isinstance(md, dict):
        md = {}
    targets = md.get("targets") if isinstance(md.get("targets"), dict) else {}
    for key in ("error_pattern", "form_id", "form"):
        v = targets.get(key)
        if v:
            return str(v)
    # Soft fallback: plan observations
    plan = parts.get("plan") if isinstance(parts.get("plan"), dict) else {}
    obs = plan.get("observations") if isinstance(plan.get("observations"), dict) else {}
    hits = obs.get("error_hit_ids") or []
    if hits:
        return str(hits[0])
    return None


def _target_forms(
    *,
    cf_target: str | None,
    mode_decision: Mapping[str, Any] | None,
    parts: Mapping[str, Any] | None,
) -> list[str]:
    """Surface forms that count as successful repair / uptake."""
    forms: list[str] = []
    md = mode_decision or {}
    targets = md.get("targets") if isinstance(md.get("targets"), dict) else {}
    for g in targets.get("good_models") or []:
        if g:
            forms.append(str(g))
    contrast = targets.get("contrast")
    if isinstance(contrast, dict) and contrast.get("prefer"):
        forms.append(str(contrast["prefer"]))
    parts = parts or {}
    if parts.get("recast"):
        forms.append(str(parts["recast"]))
    if parts.get("model"):
        forms.append(str(parts["model"]))
    # Dedup preserve order
    seen: set[str] = set()
    out: list[str] = []
    for f in forms:
        k = _fold_alnum(f)
        if k and k not in seen:
            seen.add(k)
            out.append(f)
    return out


def _learner_has_form(learner: str, forms: list[str]) -> bool:
    low = _fold_alnum(learner)
    if not low.strip():
        return False
    for f in forms:
        # Take first 2–4 content tokens from the model form
        toks = [t for t in _fold_alnum(f).split() if len(t) > 1][:4]
        if not toks:
            continue
        # Require at least the head content word (e.g. estoy, hace, llamo)
        head = toks[0]
        if head in low.split() or re.search(rf"\b{re.escape(head)}\b", low):
            # If multi-token prefer phrase snip
            if len(toks) >= 2:
                phrase = " ".join(toks[:2])
                if phrase in low or head in low.split():
                    return True
            else:
                return True
    return False


def classify_learner_uptake(
    learner: str,
    *,
    prior_cf_type: CFType | str | None,
    prior_cf_target: str | None = None,
    prior_mode_decision: Mapping[str, Any] | None = None,
    prior_parts: Mapping[str, Any] | None = None,
) -> UptakeClass:
    """Evaluate THIS learner turn against the previous tutor turn's CF.

    repair       = produces corrected form (target resolve / good model / recast head)
    acknowledge  = ok/sí/gracias-class without the form
    needs_repair = same error pattern again (when target is an error_pattern id)
    none         = no prior CF, or unrelated content
    """
    if not prior_cf_type or prior_cf_type == "none":
        return "none"
    text = _norm(learner)
    if not text:
        return "none"

    forms = _target_forms(
        cf_target=prior_cf_target,
        mode_decision=prior_mode_decision,
        parts=prior_parts,
    )

    # Prefer catalog resolve for the *target* pattern id when available.
    repaired = False
    if prior_cf_target:
        try:
            from .character_sheet import detect_error_pattern_resolves

            resolves = detect_error_pattern_resolves(text)
            if prior_cf_target in resolves:
                repaired = True
        except Exception:
            pass
    if not repaired and forms:
        repaired = _learner_has_form(text, forms)
    if repaired:
        return "repair"

    # Same error again?
    if prior_cf_target:
        try:
            from .character_sheet import detect_error_pattern_hits

            hits = [pid for pid, _ in detect_error_pattern_hits(text)]
            if prior_cf_target in hits:
                return "needs_repair"
        except Exception:
            pass

    if _ACK_ONLY_RE.match(text):
        return "acknowledge"

    # Non-empty, no form, not pure ack, not same error → still "none"
    # (topic change / partial attempt without target form).
    return "none"


def soft_cf_density(cf_types: list[str], *, window: int = CF_DENSITY_WINDOW) -> int:
    """Count of CF turns (cf_type != none) in the last `window` tutor turns.

    Arithmetic example: types=[none, recast, recast] → window 3 → 2.
    """
    w = list(cf_types)[-window:]
    return sum(1 for t in w if t and t != "none")


def channel_stack(
    *,
    has_teach_image: bool,
    visible: str,
    tts_expected: bool = True,
) -> dict[str, Any]:
    return {
        "has_teach_image": bool(has_teach_image),
        "text_token_len": text_token_len(visible),
        "tts_expected": bool(tts_expected and bool(_norm(visible))),
    }


def is_non_comprehension_signal(learner: str) -> bool:
    """Reuse observe.probe_signals when available; else light regex."""
    text = _norm(learner)
    if not text:
        return True  # empty counts as not-restored for episode logic
    try:
        from .observe import probe_signals

        sig = probe_signals(text)
        if "meta_comprehension" in sig:
            return True
        if "english_only" in sig:
            return True
        return False
    except Exception:
        if re.search(
            r"\bi\s+don'?t\s+understand\b|\bno\s+entiendo\b|\bwhat\s+does\b|\bmeans?\b",
            text,
            re.I,
        ):
            return True
        return False


def is_english_escape(learner: str) -> bool:
    try:
        from .observe import probe_signals

        return "english_only" in probe_signals(learner or "")
    except Exception:
        return False


def meaning_restored_on_learner(learner: str) -> bool:
    """True if this learner turn counts as comprehension restored.

    Restored := non-empty AND not meta_comprehension AND not english_only escape.
    (Brief: not another non-comprehension signal and not empty/English-escape.)
    """
    text = _norm(learner)
    if not text:
        return False
    if is_english_escape(text):
        return False
    if is_non_comprehension_signal(text):
        return False
    return True


@dataclass
class RepairEpisode:
    opened_on_tutor_turn: int
    learner_turns_seen: int = 0
    restored: bool | None = None  # None = open; True/False when closed
    closed: bool = False


@dataclass
class TelemetryState:
    """Session-scoped rolling state for density, uptake, repair, aggregates."""

    tutor_cf_types: list[str] = field(default_factory=list)
    density_samples: list[int] = field(default_factory=list)
    tl_ratios: list[float] = field(default_factory=list)

    # Pending CF awaiting next learner uptake evaluation
    pending_cf_type: str = "none"
    pending_cf_target: str | None = None
    pending_mode_decision: dict[str, Any] = field(default_factory=dict)
    pending_parts_snippet: dict[str, Any] = field(default_factory=dict)

    # Uptake tallies: cf_type → {uptake_class → count}
    uptake_by_cf: dict[str, dict[str, int]] = field(default_factory=dict)

    repair_episodes: list[RepairEpisode] = field(default_factory=list)
    tutor_turn_index: int = 0

    def note_uptake(self, cf_type: str, uptake: str) -> None:
        if not cf_type or cf_type == "none":
            return
        bucket = self.uptake_by_cf.setdefault(
            cf_type, {u: 0 for u in sorted(UPTAKE_CLASSES)}
        )
        if uptake not in bucket:
            bucket[uptake] = 0
        bucket[uptake] += 1


def build_turn_telemetry(
    *,
    parts: Mapping[str, Any] | None,
    mode_decision: Mapping[str, Any] | None,
    visible: str,
    notes: Iterable[str] | None,
    learner: str = "",
    has_teach_image: bool = False,
    tts_expected: bool = True,
    is_open: bool = False,
    state: TelemetryState | None = None,
) -> tuple[dict[str, Any], TelemetryState]:
    """Build per-turn telemetry dict and update session state.

    Call once per completed tutor turn (after mode/gate/images attached).

    learner_uptake on this dict = uptake of the *previous* CF on *this*
    learner line (empty on open / first turn).
    """
    state = state or TelemetryState()
    parts = dict(parts or {})
    md = dict(mode_decision or parts.get("mode_decision") or {})

    # --- (c) uptake of prior CF against this learner turn ---
    if is_open or not _norm(learner):
        uptake: UptakeClass = "none"
    else:
        uptake = classify_learner_uptake(
            learner,
            prior_cf_type=state.pending_cf_type,  # type: ignore[arg-type]
            prior_cf_target=state.pending_cf_target,
            prior_mode_decision=state.pending_mode_decision,
            prior_parts=state.pending_parts_snippet,
        )
        state.note_uptake(state.pending_cf_type, uptake)

        # --- (f) repair episode progress on learner turns ---
        for ep in state.repair_episodes:
            if ep.closed:
                continue
            ep.learner_turns_seen += 1
            if meaning_restored_on_learner(learner):
                ep.restored = True
                ep.closed = True
            elif ep.learner_turns_seen >= REPAIR_LEARNER_HORIZON:
                ep.restored = False
                ep.closed = True

    # --- (a)(b) CF for this tutor turn ---
    cf_type = classify_cf_type(parts, md)
    cf_target = classify_cf_target(parts, md)

    state.tutor_turn_index += 1
    state.tutor_cf_types.append(cf_type)
    density = soft_cf_density(state.tutor_cf_types)
    state.density_samples.append(density)

    tl = extract_tl_ratio(notes=notes, parts=parts, visible=visible)
    if tl is not None:
        state.tl_ratios.append(float(tl))

    # Open repair episode when this tutor turn is comprehension_repair
    mode = _norm(md.get("mode") or parts.get("mode")).lower()
    if mode == "comprehension_repair":
        state.repair_episodes.append(
            RepairEpisode(opened_on_tutor_turn=state.tutor_turn_index)
        )

    # Stash CF for next learner uptake
    state.pending_cf_type = cf_type
    state.pending_cf_target = cf_target
    state.pending_mode_decision = md
    state.pending_parts_snippet = {
        k: parts.get(k)
        for k in ("recast", "model", "explain", "try", "acknowledge")
        if parts.get(k)
    }

    channels = channel_stack(
        has_teach_image=has_teach_image,
        visible=visible,
        tts_expected=tts_expected,
    )

    # Open repair status for this turn (if any still open / just opened)
    repair_outcome: dict[str, Any] | None = None
    open_eps = [e for e in state.repair_episodes if not e.closed]
    closed_this = [
        e
        for e in state.repair_episodes
        if e.closed and e.opened_on_tutor_turn == state.tutor_turn_index
    ]
    # Per-turn: if we are a repair mode turn, report episode open; if a
    # prior episode closed on this learner beat, report that outcome.
    just_closed = [
        e
        for e in state.repair_episodes
        if e.closed
        and e.learner_turns_seen > 0
        and e.learner_turns_seen <= REPAIR_LEARNER_HORIZON
    ]
    # Prefer the most recently closed on this learner evaluation
    if not is_open and _norm(learner):
        for e in reversed(state.repair_episodes):
            if e.closed and e.restored is not None:
                # only attach once — use learner_turns_seen match on last tick
                if e.learner_turns_seen <= REPAIR_LEARNER_HORIZON:
                    repair_outcome = {
                        "opened_on_tutor_turn": e.opened_on_tutor_turn,
                        "meaning_restored": bool(e.restored),
                        "learner_turns_to_resolve": e.learner_turns_seen,
                    }
                    break
    if mode == "comprehension_repair" and repair_outcome is None:
        repair_outcome = {
            "opened_on_tutor_turn": state.tutor_turn_index,
            "meaning_restored": None,
            "learner_turns_to_resolve": 0,
        }

    tel = {
        "cf_type": cf_type,
        "cf_target": cf_target,
        "learner_uptake": uptake,  # of *prior* CF
        "soft_cf_density": density,
        "channel": channels,
        "tl_ratio": tl,
        "repair_episode": repair_outcome,
        "mode": mode or None,
        "hard_break": bool(md.get("hard_break")) if md else None,
        "tutor_turn_index": state.tutor_turn_index,
    }
    return tel, state


def session_aggregate(state: TelemetryState) -> dict[str, Any]:
    """Session-close aggregates (g)."""
    # Spanish token ratio: mean of observed per-turn ratios
    # (macro-average; micro needs token counts gate does not yet emit).
    if state.tl_ratios:
        session_tl = sum(state.tl_ratios) / len(state.tl_ratios)
    else:
        session_tl = None

    if state.density_samples:
        density_mean = sum(state.density_samples) / len(state.density_samples)
    else:
        density_mean = 0.0

    # Close any still-open repair episodes as not restored
    for ep in state.repair_episodes:
        if not ep.closed:
            ep.restored = False
            ep.closed = True

    total_rep = len(state.repair_episodes)
    restored = sum(1 for e in state.repair_episodes if e.restored)

    # Uptake rates by cf_type: repair_rate = repair / (repair+ack+needs+none_with_cf)
    uptake_rates: dict[str, dict[str, float | int]] = {}
    for cf_t, counts in state.uptake_by_cf.items():
        total = sum(counts.values()) or 0
        rates: dict[str, float | int] = {"n": total}
        for u, c in counts.items():
            rates[f"count_{u}"] = c
            rates[f"rate_{u}"] = (c / total) if total else 0.0
        uptake_rates[cf_t] = rates

    return {
        "session_spanish_token_ratio": session_tl,
        "tl_ratio_n": len(state.tl_ratios),
        "soft_cf_density_mean": density_mean,
        "soft_cf_density_samples": list(state.density_samples),
        "uptake_by_cf_type": uptake_rates,
        "repair_episodes_restored": restored,
        "repair_episodes_total": total_rep,
        "repair_restore_rate": (restored / total_rep) if total_rep else None,
        "tutor_turns": state.tutor_turn_index,
        "cf_type_histogram": {
            t: state.tutor_cf_types.count(t) for t in sorted(set(state.tutor_cf_types))
        },
    }
```

---

## 2. Exact wiring — `tutor/conv_session.py`

### 2.1 Imports + session fields

**Insertion A — imports (near other local imports, ~line 31–33):**

```python
from .telemetry import TelemetryState, build_turn_telemetry, session_aggregate
```

**Insertion B — `ConversationalSession.__init__` after `self.last_mode_decision = None` (~371):**

```python
        self.telemetry_state = TelemetryState()
        self.last_telemetry: dict | None = None
```

**Insertion C — `reset_sheet` after mode_state reset (~1376):**

```python
        self.telemetry_state = TelemetryState()
        self.last_telemetry = None
```

### 2.2 Planned AI path (primary) — **the real call site**

After `result.parts` merge of plan/mode/gate/images (~969–988) and **before** `_log_turn_result` (~989).

```python
        # --- Tier-1 telemetry (deterministic; no LLM) ---
        try:
            teach_imgs = (result.parts or {}).get("teach_images") or teach_images or []
            tel, self.telemetry_state = build_turn_telemetry(
                parts=result.parts,
                mode_decision=decision.as_dict(),
                visible=result.reply or "",
                notes=result.notes,
                learner="" if is_open else (learner or ""),
                has_teach_image=bool(teach_imgs),
                tts_expected=True,  # product default; web may ignore
                is_open=is_open,
                state=self.telemetry_state,
            )
            if result.parts is not None:
                result.parts = {**result.parts, "telemetry": tel}
            self.last_telemetry = tel
            result.notes = list(result.notes or []) + [
                f"cf_type={tel.get('cf_type')}",
                f"soft_cf_density={tel.get('soft_cf_density')}",
            ]
            if tel.get("tl_ratio") is not None:
                result.notes = list(result.notes or []) + [
                    f"tl_ratio={tel['tl_ratio']:.3f}"
                ]
            if tel.get("learner_uptake") and tel["learner_uptake"] != "none":
                result.notes = list(result.notes or []) + [
                    f"learner_uptake={tel['learner_uptake']}"
                ]
        except Exception as te:
            result.notes = list(result.notes or []) + [
                f"telemetry_error:{type(te).__name__}"
            ]
```

Also extend `_log_turn_result` `extra` / `state` to surface telemetry:

```python
                "telemetry": parts.get("telemetry"),
```

in both the `state={...}` and `extra={...}` dicts (~572–597).

### 2.3 Rules + legacy paths

- `_execute_rules_planned`: same block after images attach (~1110+), using `card` mode if any (`result.parts.get("mode")` / plan), else `mode_decision=None`.
- Legacy `user_turn` / `open_session`: after `_finish`, call `build_turn_telemetry` with `mode_decision=self.last_mode_decision`, `has_teach_image=False`.

### 2.4 `close()` — session aggregates in logs

Replace (~1461–1467):

```python
    def close(self, *, persist_sheet: bool = True) -> str | None:
        """End session. If persist_sheet is False (hard reset), do not write sheet."""
        if persist_sheet:
            save_sheet(self.sheet_path, self.sheet)
        agg = session_aggregate(self.telemetry_state)
        self.last_telemetry_session = agg  # optional attribute
        if self.logger:
            return str(
                self.logger.close(
                    mode="conversational",
                    telemetry=agg,
                )
            )
        return None
```

`SessionLogger.close(**summary)` already dumps kwargs into `session_end` JSONL + md summary — **no session_log API change required**.

### 2.5 Flagged non-gaps / non-goals

- Do **not** touch `english_wall` thresholds or `check_output_gate` body.
- Do **not** require FOCUS_MODEL / planner RTT.
- Telemetry errors must never fail the learner-facing turn (try/except as above).

---

## 3. Tests — `tests/test_telemetry.py`

```python
"""Unit tests for deterministic CF / uptake / density / repair telemetry."""

from __future__ import annotations

import unittest

from tutor.telemetry import (
    CF_DENSITY_WINDOW,
    TelemetryState,
    build_turn_telemetry,
    channel_stack,
    classify_cf_target,
    classify_cf_type,
    classify_learner_uptake,
    extract_tl_ratio,
    parse_tl_ratio_from_notes,
    session_aggregate,
    soft_cf_density,
)


class TestCfType(unittest.TestCase):
    def test_recast_tag(self):
        parts = {"recast": "Estoy bien.", "try": "¿Y tú?", "structured": True}
        self.assertEqual(classify_cf_type(parts, {"mode": "cf_recast"}), "recast")

    def test_explicit_contrast_form_focus(self):
        parts = {
            "recast": "Estoy bien.",
            "explain": "With yo use estoy.",
            "model": "Estoy bien.",
            "try": "Di: Estoy…",
            "structured": True,
        }
        md = {
            "mode": "form_focus",
            "hard_break": True,
            "targets": {
                "error_pattern": "estar_yo_estoy_vs_esta",
                "contrast": {
                    "avoid": "Yo está bien",
                    "prefer": "Estoy bien",
                },
                "good_models": ["Estoy bien."],
            },
        }
        # Priority: explicit_contrast wins over recast + metalinguistic
        self.assertEqual(classify_cf_type(parts, md), "explicit_contrast")
        self.assertEqual(classify_cf_target(parts, md), "estar_yo_estoy_vs_esta")

    def test_metalinguistic_explain(self):
        parts = {
            "explain": "This verb agrees with first person.",
            "try": "¿Cómo estás?",
            "structured": True,
        }
        self.assertEqual(classify_cf_type(parts, {"mode": "conversation"}), "metalinguistic")

    def test_prompt_slot_try(self):
        parts = {
            "try": "Completa: Yo _____ bien.",
            "model": "Estoy",
            "structured": True,
        }
        md = {
            "mode": "cf_recast",
            "targets": {"error_pattern": "estar_yo_estoy_vs_esta", "good_models": ["Estoy bien."]},
        }
        self.assertEqual(classify_cf_type(parts, md), "prompt")

    def test_none_chat(self):
        parts = {
            "acknowledge": "¡Hola!",
            "model": "Me llamo Ana.",
            "try": "¿Cómo te llamas?",
            "structured": True,
        }
        self.assertEqual(classify_cf_type(parts, {"mode": "conversation"}), "none")


class TestUptake(unittest.TestCase):
    def test_repair_produces_form(self):
        u = classify_learner_uptake(
            "Estoy bien",
            prior_cf_type="recast",
            prior_cf_target="estar_yo_estoy_vs_esta",
            prior_mode_decision={
                "targets": {
                    "error_pattern": "estar_yo_estoy_vs_esta",
                    "good_models": ["Estoy bien."],
                }
            },
            prior_parts={"recast": "Estoy bien."},
        )
        self.assertEqual(u, "repair")

    def test_acknowledge_without_form(self):
        u = classify_learner_uptake(
            "ok",
            prior_cf_type="recast",
            prior_cf_target="estar_yo_estoy_vs_esta",
            prior_parts={"recast": "Estoy bien."},
        )
        self.assertEqual(u, "acknowledge")

    def test_needs_repair_same_error(self):
        u = classify_learner_uptake(
            "Yo está bien",
            prior_cf_type="recast",
            prior_cf_target="estar_yo_estoy_vs_esta",
            prior_parts={"recast": "Estoy bien."},
        )
        self.assertEqual(u, "needs_repair")

    def test_none_without_prior_cf(self):
        u = classify_learner_uptake(
            "Hola",
            prior_cf_type="none",
        )
        self.assertEqual(u, "none")


class TestDensity(unittest.TestCase):
    def test_window_arithmetic(self):
        # Window = 3. After [none, recast, recast] density = 2
        # 0 + 1 + 1 = 2  (count, not fraction)
        self.assertEqual(CF_DENSITY_WINDOW, 3)
        self.assertEqual(soft_cf_density(["none", "recast", "recast"]), 2)
        self.assertEqual(soft_cf_density(["recast"]), 1)
        self.assertEqual(soft_cf_density(["recast", "recast", "recast", "none"]), 2)
        # mean of densities [1, 2, 2] = 5/3 ≈ 1.666…
        samples = [1, 2, 2]
        mean = sum(samples) / len(samples)
        self.assertAlmostEqual(mean, 5 / 3)


class TestTlRatio(unittest.TestCase):
    def test_parse_note(self):
        self.assertEqual(parse_tl_ratio_from_notes(["gate:ok", "tl_ratio=0.91"]), 0.91)

    def test_extract_prefers_note_over_gate(self):
        r = extract_tl_ratio(
            notes=["tl_ratio=0.95"],
            parts={"output_gate": {"spanish_ratio": 0.40}},
            visible="Hello friend please try",
        )
        self.assertEqual(r, 0.95)

    def test_extract_falls_back_to_gate(self):
        r = extract_tl_ratio(
            notes=["output_gate_ok"],
            parts={"output_gate": {"spanish_ratio": 0.80}},
            visible="",
        )
        self.assertEqual(r, 0.80)


class TestChannel(unittest.TestCase):
    def test_stack(self):
        ch = channel_stack(
            has_teach_image=True,
            visible="Hola estoy bien hoy",
            tts_expected=True,
        )
        self.assertTrue(ch["has_teach_image"])
        self.assertEqual(ch["text_token_len"], 4)
        self.assertTrue(ch["tts_expected"])


class TestBuildTurnAndSession(unittest.TestCase):
    def test_sequence_cf_uptake_repair(self):
        st = TelemetryState()

        # Turn 1 open: no uptake
        parts1 = {
            "model": "Hola. Estoy bien.",
            "try": "Di: Hola",
            "structured": True,
            "mode": "placement",
        }
        tel1, st = build_turn_telemetry(
            parts=parts1,
            mode_decision={"mode": "placement", "hard_break": True, "targets": {}},
            visible="Hola. Estoy bien. Di: Hola",
            notes=["tl_ratio=0.90"],
            learner="",
            is_open=True,
            state=st,
        )
        self.assertEqual(tel1["cf_type"], "none")
        self.assertEqual(tel1["learner_uptake"], "none")
        self.assertEqual(tel1["soft_cf_density"], 0)

        # Turn 2: recast CF
        parts2 = {
            "recast": "Estoy bien.",
            "try": "¿Cómo estás?",
            "structured": True,
        }
        md2 = {
            "mode": "cf_recast",
            "hard_break": False,
            "targets": {
                "error_pattern": "estar_yo_estoy_vs_esta",
                "good_models": ["Estoy bien."],
                "require_recast_tag": True,
            },
        }
        tel2, st = build_turn_telemetry(
            parts=parts2,
            mode_decision=md2,
            visible="Estoy bien. ¿Cómo estás?",
            notes=["tl_ratio=1.0", "mode=cf_recast"],
            learner="Yo está bien",
            has_teach_image=False,
            is_open=False,
            state=st,
        )
        self.assertEqual(tel2["cf_type"], "recast")
        self.assertEqual(tel2["cf_target"], "estar_yo_estoy_vs_esta")
        # prior CF was none → uptake none
        self.assertEqual(tel2["learner_uptake"], "none")
        self.assertEqual(tel2["soft_cf_density"], 1)

        # Turn 3: learner repaired; tutor continues
        parts3 = {
            "acknowledge": "¡Muy bien!",
            "model": "Estoy en el bote.",
            "try": "¿Dónde estás?",
            "structured": True,
        }
        tel3, st = build_turn_telemetry(
            parts=parts3,
            mode_decision={"mode": "conversation", "hard_break": False, "targets": {}},
            visible="¡Muy bien! Estoy en el bote. ¿Dónde estás?",
            notes=["tl_ratio=1.0"],
            learner="Estoy bien",
            is_open=False,
            state=st,
        )
        self.assertEqual(tel3["learner_uptake"], "repair")
        self.assertEqual(tel3["cf_type"], "none")
        # CF history: none, recast, none → density in last 3 = 1
        self.assertEqual(tel3["soft_cf_density"], 1)

        # Comprehension repair episode
        parts4 = {
            "explain": "Saludarte means to greet you.",
            "model": "Hola.",
            "try": "¿Cómo estás?",
            "structured": True,
        }
        tel4, st = build_turn_telemetry(
            parts=parts4,
            mode_decision={
                "mode": "comprehension_repair",
                "hard_break": True,
                "targets": {"last_try": "¿Cómo estás?", "require_same_topic": True},
            },
            visible="Saludarte means to greet you. Hola. ¿Cómo estás?",
            notes=["tl_ratio=0.55"],
            learner="what does that mean",
            is_open=False,
            state=st,
        )
        self.assertEqual(tel4["mode"], "comprehension_repair")
        self.assertIsNotNone(tel4["repair_episode"])

        # Next learner restores meaning
        parts5 = {
            "acknowledge": "¡Bien!",
            "try": "¿Te gusta el bote?",
            "structured": True,
        }
        tel5, st = build_turn_telemetry(
            parts=parts5,
            mode_decision={"mode": "conversation", "targets": {}},
            visible="¡Bien! ¿Te gusta el bote?",
            notes=["tl_ratio=1.0"],
            learner="Estoy bien",
            is_open=False,
            state=st,
        )
        self.assertTrue(
            tel5.get("repair_episode")
            and tel5["repair_episode"].get("meaning_restored") is True
        )

        agg = session_aggregate(st)
        self.assertIsNotNone(agg["session_spanish_token_ratio"])
        # ratios: 0.90, 1.0, 1.0, 0.55, 1.0 → sum=4.45 / 5 = 0.89
        self.assertAlmostEqual(
            agg["session_spanish_token_ratio"],
            (0.90 + 1.0 + 1.0 + 0.55 + 1.0) / 5,
            places=5,
        )
        self.assertEqual(agg["repair_episodes_total"], 1)
        self.assertEqual(agg["repair_episodes_restored"], 1)
        self.assertIn("recast", agg["uptake_by_cf_type"])
        self.assertEqual(
            agg["uptake_by_cf_type"]["recast"]["count_repair"],
            1,
        )

    def test_all_cf_types_fixture_table(self):
        cases = [
            ("none", {"model": "Hola", "try": "¿Cómo te llamas?"}, {"mode": "conversation"}),
            ("recast", {"recast": "Hace calor."}, {"mode": "cf_recast", "targets": {"error_pattern": "weather_hace"}}),
            (
                "explicit_contrast",
                {"recast": "Hace calor.", "explain": "not está"},
                {
                    "mode": "form_focus",
                    "targets": {
                        "error_pattern": "weather_hace",
                        "contrast": {"avoid": "Está calor", "prefer": "Hace calor"},
                    },
                },
            ),
            (
                "metalinguistic",
                {"explain": "Gender agreement: el vs la."},
                {"mode": "conversation"},
            ),
            (
                "prompt",
                {"try": "Completa: Hace _____."},
                {"mode": "cf_recast", "targets": {"error_pattern": "weather_hace", "good_models": ["Hace calor."]}},
            ),
        ]
        for expected, parts, md in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify_cf_type(parts, md), expected)


if __name__ == "__main__":
    unittest.main()
```

**Run (when landed):**

```sh
cd /Users/patrickcremin/repo/ml_teacher
PYTHONPATH=. python -m unittest tests.test_telemetry -v
```

---

## 4. Quantitative acceptance (pre-register)

| Metric | Formula | Gate for later CF debates |
|--------|---------|---------------------------|
| Uptake repair rate by type | \(\frac{n_{\text{repair}}}{n_{\text{cf turns of type}}}\) | Prompt-first (Tier 2 #4) wins if \(\text{rate}_{\text{prompt}} > \text{rate}_{\text{recast}} + 0.10\) at \(n \ge 30\) CF events/type |
| Soft CF density mean | \(\frac{1}{T}\sum_t \text{density}_t\), density \(\in \{0,1,2,3\}\) | Hard-break budget A6: compare sessions with mean density \(> 2.0\) vs \(\le 1.0\) on boredom/WTC proxies |
| Session TL ratio | \(\frac{1}{k}\sum_{i=1}^{k} r_i\) for \(k\) turns with ratio | Target \(\ge 0.90\) (synthesis A3); wall still rewrites majority-English turns |
| Repair restore rate | \(\frac{\text{restored}}{\text{total episodes}}\) | Graduated repair ladder (Tier 2 #6) must beat baseline restore rate |

Arithmetic check used in tests:

- densities \([1,2,2]\): mean \(= (1+2+2)/3 = 5/3 \approx 1.6667\)
- TL ratios \([0.90, 1.0, 1.0, 0.55, 1.0]\): mean \(= 4.45/5 = 0.89\)

---

## 5. What I refuse / defer

| Item | Ruling |
|------|--------|
| Editing `output_gate.py` / english_wall | **REJECT** (brief forbids; parallel owner) |
| Claiming Lyster 6-type coverage | **REJECT** until clarification + repetition instrumented |
| SM-2 / flashcard surface | **REJECT** (already persona-hostile per A4; out of scope) |
| Logging raw full sheet into telemetry | **REJECT** (PII/noise; ids only) |
| Making telemetry failures fail the turn | **REJECT** |
| Retro-writing prior JSONL turns with delayed uptake | **DEFER** — current design puts uptake on the *next* tutor turn’s `learner_uptake`; sufficient for session aggregates. Optional later: patch previous JSONL event |

---

## 6. Minimal PR checklist for the implementing author

1. Add `tutor/telemetry.py` as drafted (priority order + `tl_ratio` fallback).  
2. Wire `TelemetryState` on `ConversationalSession`; planned path before `_log_turn_result`; `close()` → `logger.close(telemetry=agg)`.  
3. Add `tests/test_telemetry.py`; green under `python -m unittest tests.test_telemetry`.  
4. Do **not** mark CF policy “improved” until trajectories show uptake rates in real `logs/sessions/*.jsonl` (`session_end.telemetry`).  
5. When parallel `tl_ratio=` note lands, tests already prefer it over `spanish_ratio`.

---

## 7. Bottom line

**COUNTERSIGN** Tier-1 telemetry as the correct first instrument, with **AMENDs** on (1) cf_type conflict priority, (2) `tl_ratio` three-step consume because the note is not in tree yet, (3) uptake attached to the next tutor turn via `pending_cf`, (4) repair episodes tracked across 2 learner turns, (5) wire **only** after mode/gate/images merge on the planned path.

This is enough to make recast-vs-prompt and repair-ladder debates falsifiable without another prose round.
