"""B0 realization context — the ten-member floor (PEDAGOGY §3.3 amended).

Dual-path, NON-DEFAULT: built only when config.TEACHER_CONTEXT == "brief"
(tutor/turn_pipeline.stage_prompt_build). The full path stays byte-identical
to today. Everything here is code-assembled, schema-validated, and logged
per turn as the ``completeness_v1`` artifact (lint:
scripts/check_completeness.py).

The floor, quoted from docs/design-planner-rounds.md (⬛ Grok round-2 A1
exact replacement, adopted verbatim in the round-2 adjudication):

    B0 executor context floor (complete list):
    (1) compact law core (in-prompt subset per law census,
        schema-versioned);
    (2) persona (+ Spanish-first stance, no second authority);
    (3) typed LessonBrief (schema v2 — no free-prose intent);
    (4) same-turn dynamic slice =
        brief.targets ∪ due ∪ introduce ∪ keys_in_last_exchange ∪
        keys_detected_in_this_learner_utterance ∪ repair_targets ∪
        active_cf_pattern_keys
        (validated against table+sheet; invalid dropped+logged);
    (5) negative + ban projection: denylist excerpt ∪ cluster-mates of
        every allowed_new key ∪ asked-frames (normalized) ∪ must_not[] ∪
        known-for-ban / no-regloss keys (sheet-known items that must not
        receive flashcard chrome or unsolicited re-gloss);
    (6) budgets (introduce_left, form_focus_cooldown, content_uptake_left,
        checker_left) as code numbers, not prose;
    (7) mechanical session manifest (introduced this session, CF targets
        active, still_fail counts, phase id, frames_seen avoid lists
        already in brief);
    (8) last K verbatim exchanges (freeze K=3; floor K≥2);
    (9) ≤1k-token pack INDEX (topic titles + lemma list for in-phase legal
        themes);
    (10) fallback: resolve_key_or_nearest on this turn; slice_miss logged
        for evals.
    All ten are code-assembled, schema-validated, logged per turn. Missing
    (5)'s cluster/known-for-ban members is a completeness fault, not a
    soft omission.

Token pressure is NEVER a legal omission reason (§3.3 predicate 4). New
event kinds deliberately NOT added — slice_miss / invalid-key drops are
recorded inside the artifact (catalog-churn avoidance, build constraint 5).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import config

SCHEMA = "completeness_v1"
# K frozen at 3 pending A/B; the floor is K≥2 (round-1 Q2 item 7 —
# "do not drop below 2"). Versioned here, checked by the lint.
K_EXCHANGES = 3
K_FLOOR = 2
# ≤1k-token pack index (round-2 floor item 9); rough 4 chars/token.
PACK_INDEX_MAX_CHARS = 4000

LAW_CORE_PATH = config.REPO_ROOT / "prompts" / "executor_law_core.md"
# Member (11), completeness_v1 amendment 2026-07-30: the FIRST live B0
# arm failed 10/12 turns on pedagogy:no_teach_move — the census listed
# LAWS but nobody named the INTERFACE, so the brief path shipped without
# the <tutor> structured-reply contract and the model answered in prose.
# The reply protocol is a floor member, not optional prose.
REPLY_PROTOCOL_PATH = (
    config.REPO_ROOT / "prompts" / "executor_reply_protocol.md"
)

FLOOR_MEMBERS = (
    "law_core", "persona", "reply_protocol", "lesson_brief",
    "dynamic_slice", "negative_projection", "budgets", "session_manifest",
    "exchange_window", "pack_index", "fallback",
)


@dataclass
class RealizationContext:
    """What stage_prompt_build ships on the brief path + the logged
    artifact the completeness lint judges."""

    system_blocks: list[dict] = field(default_factory=list)
    task: str = ""
    window_messages: list[dict] = field(default_factory=list)
    artifact: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Member builders
# ---------------------------------------------------------------------------


def load_law_core() -> str:
    """Member (1). Missing file → "" (recorded absent; the lint faults —
    never a silent fallback to the full prompt)."""
    try:
        return Path(LAW_CORE_PATH).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def load_reply_protocol() -> str:
    """Member (11) — the structured-reply interface. Same discipline as
    the law core: missing → "" → lint fault, never silent."""
    try:
        return Path(REPLY_PROTOCOL_PATH).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def table_keys_in_text(text: str, table: dict | None) -> list[str]:
    """Association-table keys surface-present in ``text`` (boundary
    discipline via textnorm.phrase_present — key SURFACE match for
    inventory pull is the legitimate §4.2 use; intent stays off regex)."""
    from .textnorm import phrase_present

    t = (text or "").strip()
    if not t:
        return []
    return [k for k in (table or {}) if phrase_present(k, t)]


def resolve_key_or_nearest(span: str, table: dict | None) -> str | None:
    """Member (10) fallback: map a learner span to a table key or the
    nearest one (accent-fold exact → simple plural strip → prefix ≥4
    chars). None = slice_miss (recorded in the artifact — §2.1a then
    directs an off-catalog micro-gloss, never free pack invention)."""
    from .textnorm import fold_lexical

    s = fold_lexical((span or "").strip())
    if not s or not table:
        return None
    folds = {k: fold_lexical(k) for k in table}
    for k, f in folds.items():
        if f == s:
            return k
    stripped = s[:-2] if s.endswith("es") else (
        s[:-1] if s.endswith("s") else s)
    if stripped != s:
        for k, f in folds.items():
            if f == stripped:
                return k
    if len(s) >= 4:
        for k, f in folds.items():
            if f.startswith(s) or s.startswith(f):
                return k
    return None


def _slice_row(key: str, table: dict, sheet: dict) -> dict | None:
    """Association-table row (gloss/cognate/keyword/theme) for a slice key;
    catalog/sheet fallback for grammar-pattern keys; None = invalid."""
    entry = (table or {}).get(key)
    if isinstance(entry, dict):
        row = {"gloss": str(entry.get("gloss_en") or ""),
               "theme": str(entry.get("theme") or "")}
        if entry.get("cognate_en") and not entry.get("false_friend"):
            row["cognate"] = str(entry["cognate_en"])
        if entry.get("keyword_en"):
            row["keyword"] = str(entry["keyword_en"])
        if entry.get("false_friend"):
            row["false_friend"] = str(entry["false_friend"])
        return row
    from .character_sheet import ERROR_PATTERN_CATALOG

    cat = ERROR_PATTERN_CATALOG.get(key)
    if isinstance(cat, dict):
        return {"gloss": str(cat.get("label") or ""),
                "hint": str(cat.get("teach_hint") or ""),
                "kind": "error_pattern"}
    for section in ("grammar", "skills", "lexicon"):
        ent = ((sheet or {}).get(section) or {}).get(key)
        if isinstance(ent, dict):
            return {"gloss": str(ent.get("label") or ent.get("name") or ""),
                    "kind": section}
    return None


def _last_exchange_text(session) -> str:
    """The previous exchange's surface: the last user+assistant history
    messages plus the remembered tutor model/try (session memory)."""
    mem = session.pedagogy_memory
    parts: list[str] = []
    history = list(getattr(session, "history", None) or [])
    for m in history[-2:]:
        c = m.get("content")
        if isinstance(c, str):
            parts.append(c)
    parts += [
        str(getattr(mem, "last_tutor_model", "") or ""),
        str(getattr(mem, "last_tutor_try", "") or ""),
    ]
    return " ".join(p for p in parts if p)


def _known_no_quiz_keys(sheet: dict) -> list[str]:
    """Member (5) known-for-ban list: sheet-known items that must never get
    a meaning quiz / unsolicited re-gloss (§6 checker direction + §2.3).
    Threshold matches introduce_router.CONFIDENT_LEXICON_CONFIDENCE."""
    out: list[str] = []
    lex = (sheet or {}).get("lexicon") or {}
    for k, e in lex.items():
        if not isinstance(e, dict):
            continue
        try:
            conf = float(e.get("confidence") or 0.0)
        except (TypeError, ValueError):
            conf = 0.0
        if conf >= 0.5 or str(e.get("status") or "").lower() == "known":
            out.append(str(k))
    for k, e in ((sheet or {}).get("skills") or {}).items():
        if isinstance(e, dict) and str(
                e.get("status") or "").lower() == "known":
            out.append(str(k))
    return sorted(set(out))


def _denylist_excerpt(pack_dir) -> str:
    """Member (5) denylist: the pack.md "Scope boundaries" section verbatim
    (§2.6 — the pack's own out-of-scope law, not a code re-list)."""
    try:
        raw = (Path(pack_dir) / "pack.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    lines = raw.splitlines()
    out: list[str] = []
    inside = False
    for ln in lines:
        if ln.startswith("## Scope boundaries"):
            inside = True
        elif inside and ln.startswith("## "):
            break
        if inside:
            out.append(ln)
    return "\n".join(out).strip()


def _pack_index(session) -> dict:
    """Member (9): unit topic titles + theme→lemma lists from the
    association table (in_pack entries; structural themes included — they
    are legal palette). The whole A1 table index fits ≤1k tokens, so the
    index is complete; if a future pack overflows, lemma lists shrink
    evenly and ``reduced`` records it (never a silent drop)."""
    from .corpus import pack_topic_titles

    titles = pack_topic_titles(Path(session.pack_dir))
    table = getattr(session, "association_table", None) or {}
    themes: dict[str, list[str]] = {}
    for k, e in table.items():
        if not isinstance(e, dict) or e.get("in_pack") is False:
            continue
        themes.setdefault(str(e.get("theme") or "other"), []).append(str(k))
    index = {"unit_topics": titles, "themes": themes, "reduced": False}
    while len(json.dumps(index, ensure_ascii=False)) > PACK_INDEX_MAX_CHARS:
        index["reduced"] = True
        longest = max(themes, key=lambda t: len(themes[t]), default=None)
        if longest is None or len(themes[longest]) <= 1:
            break
        themes[longest] = themes[longest][:-1]
    return index


# ---------------------------------------------------------------------------
# The builder
# ---------------------------------------------------------------------------


def build_realization_context(session, ctx, brief) -> RealizationContext:
    """Assemble the ten-member floor for one turn (brief path only).

    ``session``/``ctx`` are the live pipeline objects; ``brief`` is the
    already-validated LessonBrief. Pure assembly — no model call, no state
    writes; misses and drops land in the artifact, not new event kinds.
    """
    from .executor import load_persona

    table = getattr(session, "association_table", None) or {}
    sheet = session.sheet
    decision = ctx.decision
    dec = decision.as_dict() if decision is not None else {}

    # (1) + (2)
    law_core = load_law_core()
    persona = load_persona()
    persona_removed = not getattr(config, "PERSONA_ENABLED", True)

    # (4) same-turn dynamic slice — the A1 union, in declared order.
    learner_text = ctx.learner if not ctx.is_open else ""
    union: dict[str, str] = {}  # key → first source that pulled it

    def _pull(keys, source: str) -> None:
        for k in keys:
            union.setdefault(str(k), source)

    _pull([t.get("key") for t in brief.targets if t.get("key")],
          "brief_targets")
    due_keys = [d.get("key") for d in brief.due_frames if d.get("key")]
    _pull(due_keys, "due")
    intro_keys = [a.get("key") for a in brief.allowed_new if a.get("key")]
    _pull(intro_keys, "introduce")
    _pull(table_keys_in_text(_last_exchange_text(session), table),
          "last_exchange")
    learner_detected = table_keys_in_text(learner_text, table)
    _pull(learner_detected, "learner_text")
    repair_targets: list[str] = []
    if dec.get("mode") == "comprehension_repair":
        tg = dec.get("targets") or {}
        repair_text = " ".join(
            str(tg.get(k) or "") for k in ("last_model", "last_try"))
        repair_targets = table_keys_in_text(repair_text, table)
        _pull(repair_targets, "repair")
    from .character_sheet import active_error_patterns

    cf_keys: list[str] = []
    for e in active_error_patterns(sheet) or []:
        if isinstance(e, dict) and e.get("id"):
            cf_keys.append(str(e["id"]))
            if e.get("form_id"):
                cf_keys.append(str(e["form_id"]))
    _pull(cf_keys, "cf_pattern")

    # (10) fallback — runs BEFORE slice freeze so a resolved near-key joins
    # THIS turn's slice (round-1 same-turn REJECT: never "next round").
    from .observe import detect_self_flagged_token

    fallback_queries: list[str] = []
    flagged = detect_self_flagged_token(learner_text)
    if flagged:
        fallback_queries.append(flagged)
    resolved: dict[str, str] = {}
    slice_miss: list[str] = []
    for q in fallback_queries:
        hit = resolve_key_or_nearest(q, table)
        if hit:
            resolved[q] = hit
            union.setdefault(hit, "fallback")
        else:
            slice_miss.append(q)

    rows: dict[str, dict] = {}
    invalid_dropped: list[str] = []
    for k, source in union.items():
        row = _slice_row(k, table, sheet)
        if row is None:
            invalid_dropped.append(k)
            continue
        rows[k] = {**row, "source": source}

    # (5) negative + ban projection.
    from .association_table import entries_for_theme
    from .retrieval_scheduler import is_introduced

    cluster_mates: list[str] = []
    intro_plan = getattr(ctx, "intro_plan", None)
    if intro_plan is not None:
        cluster_mates = list(intro_plan.forbid_cluster_with or [])
    for k in intro_keys:
        entry = table.get(k)
        theme = str((entry or {}).get("theme") or "")
        for mate in entries_for_theme(table, theme) if theme else []:
            if mate != k and not is_introduced(sheet, mate, "lexicon") \
                    and mate not in cluster_mates:
                cluster_mates.append(mate)
    negative = {
        "denylist_excerpt": _denylist_excerpt(session.pack_dir),
        "cluster_mates_of_allowed_new": cluster_mates,
        "asked_frames": sorted(session.pedagogy_memory.asked_topics),
        "must_not": list(brief.must_not),
        "known_no_quiz": _known_no_quiz_keys(sheet),
    }

    # (8) last-K verbatim exchange window — the ONLY legal history
    # windowing, on the realization path only, K versioned here (§3.3
    # truncation-ban clarification; reuses config.history_for_model's
    # explicit pair semantics).
    window: list[dict] = []
    if not ctx.is_open:
        window = config.history_for_model(
            getattr(session, "history", None) or [], turns=K_EXCHANGES)

    # (9)
    pack_index = _pack_index(session)

    # ----- assemble the task tail (volatile) --------------------------------
    payload = {
        "turn": {
            "learner_said": (
                learner_text if not ctx.is_open
                else "(session open — they have not spoken yet)"
            ),
            "is_open": bool(ctx.is_open),
            "blank_character_sheet": bool(getattr(ctx, "blank", False)),
        },
        # Router direction rides with the brief: decision instructions are
        # code-owned direction (§1.1/§1.1a) — guard/repair/uptake shape
        # would be orphaned without them (flagged in the build report).
        "mode": {
            "name": dec.get("mode") or "conversation",
            "reason": dec.get("reason") or "",
            "hard_break": bool(dec.get("hard_break")),
            "targets": dec.get("targets") or {},
            "instructions": dec.get("instructions") or "",
        },
        "lesson_brief": brief.as_dict(),
        "dynamic_slice": rows,
        "negative_projection": negative,
        "budgets": dict(brief.budgets),
        "session_manifest": dict(brief.session_manifest),
        "pack_index": pack_index,
        "fallback": {
            "resolved": resolved,
            "slice_miss": slice_miss,
        },
        "visual": {
            "attached_this_turn": [
                {"concept": t.get("concept"), "form": t.get("form"),
                 "caption": t.get("caption")}
                for t in (getattr(ctx, "teach_images", None) or [])
            ],
        },
    }
    task = (
        "<tutor_turn_task>\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n</tutor_turn_task>\n"
    )

    # ----- system blocks (cache-stable: law core + persona only) ------------
    reply_protocol = load_reply_protocol()
    system_blocks: list[dict] = [{"type": "text", "text": law_core}]
    if reply_protocol:
        system_blocks.append({"type": "text", "text": reply_protocol})
    if persona:
        system_blocks.append({"type": "text", "text": persona})
    # Mark the end of the stable prefix (same provider-caching idiom as the
    # full path — volatility lives in the task tail).
    system_blocks[-1] = {**system_blocks[-1],
                         "cache_control": {"type": "ephemeral"}}

    # ----- the completeness_v1 artifact -------------------------------------
    artifact = {
        "schema": SCHEMA,
        "teacher_context": "brief",
        "k_exchanges": K_EXCHANGES,
        "k_floor": K_FLOOR,
        "is_open": bool(ctx.is_open),
        "floor": {
            "law_core": {
                "present": bool(law_core),
                "chars": len(law_core),
                "path": str(LAW_CORE_PATH),
            },
            "reply_protocol": {
                "present": bool(reply_protocol),
                "chars": len(reply_protocol),
                "path": str(REPLY_PROTOCOL_PATH),
            },
            "persona": {
                "present": bool(persona),
                "capability_removed": persona_removed,
                "chars": len(persona),
            },
            "lesson_brief": brief.as_dict(),
            "dynamic_slice": {
                "keys": sorted(rows),
                "rows": rows,
                "invalid_dropped": sorted(invalid_dropped),
            },
            "negative_projection": negative,
            "budgets": dict(brief.budgets),
            "session_manifest": dict(brief.session_manifest),
            "exchange_window": list(window),
            "pack_index": pack_index,
            "fallback": {
                "queries": fallback_queries,
                "resolved": resolved,
                "slice_miss": slice_miss,
            },
        },
        # The gate-critical key classes the lint's predicate 2 checks
        # membership for (elfric over-narrow-routing regret #4).
        "gate_key_classes": {
            "allowed_new": intro_keys,
            "due": due_keys,
            "repair_targets": repair_targets,
            "cf_targets": sorted(set(cf_keys)),
            "learner_detected": learner_detected,
        },
        "task_chars": len(task),
        "system_chars": sum(len(b.get("text") or "") for b in system_blocks),
    }

    return RealizationContext(
        system_blocks=system_blocks,
        task=task,
        window_messages=list(window),
        artifact=artifact,
    )
