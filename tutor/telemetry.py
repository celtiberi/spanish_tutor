"""Deterministic CF / channel / repair telemetry (no LLM).

Tier-1 instrument for falsifying CF and comprehension-repair debates.
See docs/reviews-pedagogy-research.md §4 item 1 (adjudicated 2026-07-26).

Classification priority (conflict order):
  explicit_contrast > metalinguistic > recast > prompt > none

Covers five CF types, not Lyster & Ranta's full six — clarification
requests and repetition are not instrumented yet.
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

# Soft-CF density window: last N tutor turns.
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
    r"g[eé]nero|verbo|sustantivo|conjugaci[oó]n|"
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

# Prompt / elicitation: slot, clue, or "produce this form" ask.
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
    """Consume the gate note `tl_ratio=0.xx` when present; else None."""
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
    """Prefer gate note → output_gate.spanish_ratio → local compute."""
    r = parse_tl_ratio_from_notes(notes)
    if r is not None:
        return r
    parts = parts or {}
    gate = parts.get("output_gate") if isinstance(parts.get("output_gate"), dict) else {}
    sr = gate.get("spanish_ratio")
    if isinstance(sr, (int, float)):
        return float(sr)
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

    has_contrast = bool(targets.get("contrast")) or bool(
        _CONTRAST_RE.search(explain) or _CONTRAST_RE.search(model)
    )
    if mode == "form_focus" and has_contrast:
        return "explicit_contrast"

    if explain and _METALANG_RE.search(explain):
        return "metalinguistic"

    if recast:
        return "recast"

    # Prompt: elicit a specific form retry (Lyster elicitation-ish).
    if try_ and (
        _PROMPT_TRY_RE.search(try_)
        or (
            bool(
                targets.get("require_form_retry")
                or targets.get("error_pattern")
                or targets.get("form_id")
                or targets.get("good_models")
            )
            and mode in ("cf_recast", "form_focus", "transfer")
            and ("?" in try_ or "¿" in try_)
        )
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
    plan = parts.get("plan") if isinstance(parts.get("plan"), dict) else {}
    obs = plan.get("observations") if isinstance(plan.get("observations"), dict) else {}
    hits = obs.get("error_hit_ids") or []
    if hits:
        return str(hits[0])
    return None


def _target_forms(
    *,
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
    words = set(low.split())
    for f in forms:
        toks = [t for t in _fold_alnum(f).split() if len(t) > 1][:4]
        if not toks:
            continue
        head = toks[0]
        if head in words or re.search(rf"\b{re.escape(head)}\b", low):
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

    repair       = produces corrected form (target resolve / good model head)
    acknowledge  = ok/sí/gracias-class without the form
    needs_repair = same error pattern again (when target is a pattern id)
    none         = no prior CF, or unrelated content
    """
    if not prior_cf_type or prior_cf_type == "none":
        return "none"
    text = _norm(learner)
    if not text:
        return "none"

    repaired = False
    if prior_cf_target:
        try:
            from .character_sheet import detect_error_pattern_resolves

            if prior_cf_target in set(detect_error_pattern_resolves(text)):
                repaired = True
        except Exception:
            pass
    if not repaired:
        forms = _target_forms(
            mode_decision=prior_mode_decision, parts=prior_parts
        )
        if forms:
            repaired = _learner_has_form(text, forms)
    if repaired:
        return "repair"

    if prior_cf_target:
        try:
            from .character_sheet import detect_error_pattern_hits

            if prior_cf_target in {pid for pid, _ in detect_error_pattern_hits(text)}:
                return "needs_repair"
        except Exception:
            pass

    if _ACK_ONLY_RE.match(text):
        return "acknowledge"

    # Non-empty, no form, not pure ack, not same error → still "none"
    # (topic change / partial attempt without the target form).
    return "none"


def soft_cf_density(cf_types: list[str], *, window: int = CF_DENSITY_WINDOW) -> int:
    """Count of CF turns (cf_type != none) in the last `window` tutor turns."""
    return sum(1 for t in list(cf_types)[-window:] if t and t != "none")


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
        return "meta_comprehension" in sig or "english_only" in sig
    except Exception:
        return bool(
            re.search(
                r"\bi\s+don'?t\s+understand\b|\bno\s+entiendo\b|\bwhat\s+does\b",
                text,
                re.I,
            )
        )


def is_english_escape(learner: str) -> bool:
    try:
        from .observe import probe_signals

        return "english_only" in probe_signals(learner or "")
    except Exception:
        return False


def meaning_restored_on_learner(learner: str) -> bool:
    """Non-empty AND not meta-comprehension AND not an English escape."""
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
    reported: bool = False  # outcome attached to a turn's telemetry once


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
        bucket[uptake] = bucket.get(uptake, 0) + 1


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
    learner line (none on open / first turn).
    """
    state = state or TelemetryState()
    parts = dict(parts or {})
    md = dict(mode_decision or parts.get("mode_decision") or {})

    # --- uptake of prior CF against this learner turn ---
    if is_open or not _norm(learner):
        uptake: UptakeClass = "none"
    else:
        uptake = classify_learner_uptake(
            learner,
            prior_cf_type=state.pending_cf_type,
            prior_cf_target=state.pending_cf_target,
            prior_mode_decision=state.pending_mode_decision,
            prior_parts=state.pending_parts_snippet,
        )
        state.note_uptake(state.pending_cf_type, uptake)

        # --- repair episode progress on learner turns ---
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

    # --- CF for this tutor turn ---
    cf_type = classify_cf_type(parts, md)
    cf_target = classify_cf_target(parts, md)

    state.tutor_turn_index += 1
    state.tutor_cf_types.append(cf_type)
    density = soft_cf_density(state.tutor_cf_types)
    state.density_samples.append(density)

    tl = extract_tl_ratio(notes=notes, parts=parts, visible=visible)
    if tl is not None:
        state.tl_ratios.append(float(tl))

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

    # Attach each closed episode's outcome exactly once; else report an
    # open episode when this turn is the repair turn itself.
    repair_outcome: dict[str, Any] | None = None
    for e in reversed(state.repair_episodes):
        if e.closed and e.restored is not None and not e.reported:
            e.reported = True
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
    """Session-close aggregates."""
    # Macro-average of per-turn ratios (micro needs token counts the gate
    # does not yet emit).
    session_tl = (
        sum(state.tl_ratios) / len(state.tl_ratios) if state.tl_ratios else None
    )
    density_mean = (
        sum(state.density_samples) / len(state.density_samples)
        if state.density_samples
        else 0.0
    )

    # Close any still-open repair episodes as not restored
    for ep in state.repair_episodes:
        if not ep.closed:
            ep.restored = False
            ep.closed = True

    total_rep = len(state.repair_episodes)
    restored = sum(1 for e in state.repair_episodes if e.restored)

    uptake_rates: dict[str, dict[str, float | int]] = {}
    for cf_t, counts in state.uptake_by_cf.items():
        total = sum(counts.values())
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
