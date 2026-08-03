"""Student character sheet — living learner model for conversational tutoring.

See docs/conversational-spanish-and-learner-model.md.
"""

from __future__ import annotations

import copy
import datetime
import json
import re
from pathlib import Path
from typing import Any, Literal

from .can_dos import (
    CAN_DOS,
    STRETCH_ACTIVITIES,
    default_grammar_block,
    default_skills_block,
    migrate_skills,
)
from .domain_data import cached_default_domain
# Phase 2 (docs/reviews-architecture-refactor.md): the fold policies live in
# textnorm. fold_prose (imported as the historical local name `fold`) is the
# NFD prose-scan fold for error-pattern/affect regexes; fold_id is the
# folding step inside normalize_error_pattern_id (ids live in sheets on
# disk — the policy is pinned byte-exact).
from .textnorm import fold_id, fold_prose as fold  # noqa: F401
# Typed turn events (Phase 3 batch 2 leaf push-down): the sheet-maintenance
# change notes are minted here as (kind, key, payload) TRIPLES; the strings
# process_turn returns are their render-table projection (byte-identical to
# the historical f-strings). turn_events is stdlib-only — no import cycle.
from .turn_events import TurnEventKind as _EVK, render_note as _render_note
# Machine A (schedule axis) owns these fields; imported as the single source
# so the two axes can never drift apart (retrieval_scheduler is stdlib-only,
# so this import can never cycle).
from .retrieval_scheduler import SCHEDULE_FIELDS

STATUSES = ("unknown", "emerging", "fragile", "known", "blocked")

# Harness honesty: models over-rate "known" after one lucky turn.
MAX_CONF_UP_PER_TURN = 0.25
MAX_CONF_DOWN_PER_TURN = 0.35
KNOWN_MIN_CONF = 0.80
KNOWN_MIN_SOLID_USES = 2
# Band boundaries inside _bump_status (Phase 1.5 batch 2: named so the
# progress-ledger projection can pin them instead of re-hardcoding).
EMERGING_MIN_CONF = 0.55
FRAGILE_MIN_CONF = 0.25

DEFAULT_COVERAGE = {
    "touched": [],
    "never_touched": [
        "greetings_time_of_day", "register_tu_usted", "introduce_self",
        "ser_basic", "estar_basic", "food", "numbers", "family", "leave_taking",
        "preferences", "roleplay_tasks", "nouns_articles_plurals",
        "question_words",
    ],
}

# Grammar form id → coverage topic(s)
_GRAMMAR_COVERAGE = {
    "present_estar_person": ["estar_basic"],
    "register_tu_usted": ["register_tu_usted"],
    "present_ser": ["ser_basic"],
    "numbers_0_100": ["numbers"],
    "tener_age_possession": ["family"],
    "present_regular_ar_er_ir": ["preferences"],
    "ser_estar_contrast": ["ser_basic", "estar_basic"],
    "gender_articles": ["nouns_articles_plurals"],
    "plural_formation": ["nouns_articles_plurals"],
    "gender_exception_nouns": ["nouns_articles_plurals"],
    "subject_pronouns_prodrop": ["introduce_self"],
    "profession_no_article": ["introduce_self"],
    "negation_questions_no_auxiliary": ["question_words"],
    "question_words_inventory": ["question_words"],
}

_SHEET_DELTA_RE = re.compile(
    r"<sheet_delta>\s*(\{.*?\})\s*</sheet_delta>", re.S)

# Regex lexicon/can-do graders RETIRED 2026-07-31 (tool-only ability).
# Empty so leftover references are obvious no-ops.
_LEXICON_PATTERNS: list[tuple[str, str, str]] = []

# Minimum evidence string for a grade tool call (ability claim).
MIN_GRADE_WHY_LEN = 12
_ABILITY_DELTA_KEYS = frozenset({
    "skills", "grammar", "lexicon", "error_patterns",
})


def today() -> str:
    return datetime.date.today().isoformat()


# Retrieval-scheduler / introduce-ledger fields (Phase 1 pedagogy engine —
# docs/build-plan-pedagogy-engine.md). Optional per-entry on lexicon /
# grammar / skills. Introduction NEVER changes confidence/status (honesty
# law) — enforced in tutor/retrieval_scheduler.py via a write allowlist.
# Phase 1.5 batch 2: derived from retrieval_scheduler.SCHEDULE_FIELDS (the
# single source; machine A owns the axis). Tuple view kept for membership
# callers; order is not load-bearing.
SCHEDULE_ENTRY_FIELDS = tuple(sorted(SCHEDULE_FIELDS))


def _normalize_schedule_entry(entry: dict) -> None:
    """Coerce optional scheduler/ledger fields in place; absent stays absent.

    Never invents fields on legacy entries and never touches ability fields
    (confidence/status/solid_uses) — migration is transparent.
    """
    if "interval_days" in entry:
        try:
            entry["interval_days"] = max(1, int(entry["interval_days"]))
        except (TypeError, ValueError):
            entry["interval_days"] = 1
    if "successive_successes" in entry:
        try:
            entry["successive_successes"] = max(
                0, int(entry["successive_successes"])
            )
        except (TypeError, ValueError):
            entry["successive_successes"] = 0
    for k in ("introduced_at", "first_seen", "next_due"):
        if k in entry and entry[k] is not None:
            v = str(entry[k]).strip()[:10]
            try:
                datetime.date.fromisoformat(v)
                entry[k] = v
            except ValueError:
                entry[k] = None
    if "scaffold" in entry and entry["scaffold"] is not None:
        entry["scaffold"] = str(entry["scaffold"])
    if "frames_seen" in entry:
        frames = entry["frames_seen"]
        if isinstance(frames, list):
            entry["frames_seen"] = [
                str(f).strip()[:60] for f in frames if str(f).strip()
            ][:32]
        else:
            entry.pop("frames_seen", None)


def normalize_schedule_fields(sheet: dict) -> dict:
    """Sanitize scheduler/ledger fields across lexicon/grammar/skills.

    Keys are used verbatim — multiword units like "hasta luego" are legal
    lexicon keys and must never be split or re-cased here.
    """
    for section in ("lexicon", "grammar", "skills"):
        block = sheet.get(section)
        if not isinstance(block, dict):
            continue
        for entry in block.values():
            if isinstance(entry, dict):
                _normalize_schedule_entry(entry)
    return sheet


def now_iso() -> str:
    """Local wall-clock timestamp for last_seen / context (date + time)."""
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


# Closed catalog of high-value recurring constructions (not full Spanish
# grammar).  Detected from learner text; count>=2 -> teach/recast priority.
# S10 (full-code-audit 2026-08-03): the catalog is DATA —
# domain/spanish_a1/misconceptions.json — loaded/validated at import by
# tutor/domain_data.py.  detect entries are (regex, note) tuples; the mined
# pack entries carry "source" (the deleted pack's M-ID) for provenance and
# keep detect/resolve EMPTY by design (regex judgment of Spanish was retired
# 2026-08-03 — the teacher diagnoses; regexes only serve bookkeeping).
# Regexes are COMPILED at load; malformed data is a startup error (no-hide).
_DOMAIN = cached_default_domain()
ERROR_PATTERN_CATALOG: dict[str, dict] = _DOMAIN.misconceptions
_DETECT_COMPILED = _DOMAIN.detect_compiled
_RESOLVE_COMPILED = _DOMAIN.resolve_compiled

ERROR_PATTERN_PRIORITY_THRESHOLD = 2  # count at/above → force teaching focus
# Consecutive correct uses before we drop form focus from next_best
ERROR_PATTERN_HEALTHY_STREAK = 3

# Tool / free-form ids that should collapse into the catalog
ERROR_PATTERN_ALIASES: dict[str, str] = {
    "estar_yo_esta": "estar_yo_estoy_vs_esta",
    "estar_person_yo_esta": "estar_yo_estoy_vs_esta",
    "yo_esta": "estar_yo_estoy_vs_esta",
    "yo_está": "estar_yo_estoy_vs_esta",
    "estoy_vs_esta": "estar_yo_estoy_vs_esta",
    "present_estar_person_error": "estar_yo_estoy_vs_esta",
    "me_llamo_es_x": "me_llamo_es",
    "me_llama_es": "me_llamo_es",
    "ser_vs_estar_feelings": "ser_estar_confuse",
    "ser_vs_estar": "ser_estar_confuse",
    "soy_nerviosa": "ser_estar_confuse",
    "gender_agreement": "gender_number_article",
    "article_agreement": "gender_number_article",
    "number_agreement": "gender_number_article",
    "hace_calor": "weather_hace",
    "esta_calor": "weather_hace",
    "está_calor": "weather_hace",
    "weather": "weather_hace",
}


def normalize_error_pattern_id(pattern_id: str) -> str:
    """Map free-form / alias ids onto ERROR_PATTERN_CATALOG keys."""
    pid = (pattern_id or "").strip()
    if not pid:
        return pid
    if pid in ERROR_PATTERN_CATALOG:
        return pid
    key = fold_id(pid)
    if key in ERROR_PATTERN_CATALOG:
        return key
    if key in ERROR_PATTERN_ALIASES:
        return ERROR_PATTERN_ALIASES[key]
    # fuzzy: contains catalog id
    for canon in ERROR_PATTERN_CATALOG:
        if canon in key or key in canon:
            return canon
    # Tool invents names like estar_person_yo_esta
    if "yo" in key and "esta" in key and (
        "estar" in key or "person" in key or key.startswith("yo_")
    ):
        return "estar_yo_estoy_vs_esta"
    if "llamo" in key or "llama_es" in key:
        return "me_llamo_es"
    if "tango" in key or ("tengo" in key and "error" in key):
        return "tengo_not_tango"
    if "ser" in key and "estar" in key:
        return "ser_estar_confuse"
    if key.startswith("soy_") and any(
        x in key for x in ("nerv", "bien", "feeling", "emoc")
    ):
        return "ser_estar_confuse"
    return pid


# Session-only energy labels — must NOT haunt the next day/session.
_SESSION_ENERGY_MARKERS = (
    "limited_time",
    "a_few_minutes",
    "few_minutes",
    "few_mins",
    "short_session",
    "short_on_time",
    "in_a_hurry",
    "in_a_rush",
    "rushed",
    "quick_session",
    "low_time",
    "time_box",
)

_SESSION_META_TIME = re.compile(
    r"\b(minute|minutes|little time|limited time|hurry|rush|gotta go|"
    r"have to go|short (on )?time|quick session|few mins)\b",
    re.I,
)


def is_session_scoped_energy(value: str | None) -> bool:
    if not value:
        return False
    s = str(value).lower().strip()
    if s in _SESSION_ENERGY_MARKERS:
        return True
    return any(m in s for m in _SESSION_ENERGY_MARKERS)


def clear_session_scoped_affect(sheet: dict) -> dict:
    """Drop ephemeral time-pressure / session notes so they don't stick forever.

    Call at the start of each new chat session. Durable skills stay; identity
    is stripped (personal-data capture disabled 2026-07-28).
    """
    s = copy.deepcopy(sheet)
    aff = s.setdefault("affect", {})
    if is_session_scoped_energy(aff.get("energy")):
        aff["energy"] = "unknown"
    # Boredom decays across sessions: a new chat is a fresh chance. One more
    # complaint re-raises it; without decay "high" locks new-topic mode forever.
    meta = aff.get("last_meta")
    if meta and _SESSION_META_TIME.search(str(meta)):
        aff["last_meta"] = None
    # If next_best reason still talks about limited time from a past session, recompute
    nb = s.get("next_best") or {}
    reason = str(nb.get("reason") or "").lower()
    avoid = str(nb.get("avoid") or "").lower()
    if "limited time" in reason or "time_limited" in avoid or "few minute" in reason:
        s = recompute_next_best(s)
    s = _preserve_identity(sheet, s)  # strips identity (capture disabled)
    s["updated_at"] = today()
    return s


def default_sheet() -> dict:
    return {
        "version": 2,
        "framework": {
            "name": "NCSSFL-ACTFL Can-Do oriented (Novice)",
            "methods": ["CLT", "TBLT", "comprehensible_input", "focus_on_form"],
            "spec": "docs/spanish-can-dos-novice.md",
        },
        "identity": {
            "preferred_name": None,
            "l1": "en",
            "goals": [],
            "engagement_notes": "",
        },
        "lexicon": {},
        "grammar": default_grammar_block(),  # supporting forms
        "skills": default_skills_block(),    # can-dos IP/IT/PR
        "receptive": {
            "needs_english_scaffold": True,
        },
        "affect": {
            "last_meta": None,
            "energy": "unknown",
        },
        "coverage": copy.deepcopy(DEFAULT_COVERAGE),
        "error_patterns": {},  # recurring construction errors (see ERROR_PATTERN_CATALOG)
        "next_best": {
            "can_do": None,
            "stretch": "open_chat_notice_abilities",
            "activity": "open_chat_notice_abilities",
            "avoid": "drill_greetings_if_already_easy",
            "reason": "little evidence yet — talk first (CLT); notice can-dos",
        },
        "updated_at": today(),
    }


def load_sheet(path: Path) -> dict:
    if not path.exists():
        return default_sheet()
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        # No-hide quarantine (full-code-audit S5.1, 2026-08-03): a corrupt
        # sheet must never be silently replaced by a blank — the next
        # save_sheet would overwrite the only evidence of the learner's
        # state. Rename the corrupt file aside, shout, start from default.
        import sys as _sys

        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        quarantine = path.with_name(f"{path.name}.corrupt-{stamp}")
        try:
            path.rename(quarantine)
            q_msg = f"quarantined to {quarantine}"
        except OSError as qe:
            q_msg = f"quarantine rename FAILED ({type(qe).__name__}: {qe})"
        print(
            f"[no-hide] load_sheet: corrupt/unreadable sheet {path} "
            f"({type(e).__name__}: {e}) — {q_msg}; starting from default "
            f"sheet", file=_sys.stderr, flush=True,
        )
        return default_sheet()
    # numbers_0_20 → numbers_0_100 migration MUST run on the RAW data:
    # after _deep_merge the default block has already seeded
    # numbers_0_100, so a post-merge check can never fire and the
    # learner's old state would be silently dropped (audit D finding 6).
    raw_gr = data.get("grammar")
    if isinstance(raw_gr, dict) and "numbers_0_20" in raw_gr:
        if "numbers_0_100" not in raw_gr:
            raw_gr["numbers_0_100"] = raw_gr.pop("numbers_0_20")
        else:
            raw_gr.pop("numbers_0_20", None)
    base = default_sheet()
    merged = _deep_merge(base, data)
    # Migrate legacy skill keys → can-do ids
    merged["skills"] = migrate_skills(data.get("skills") or merged.get("skills") or {})
    # Ensure all can-dos / forms exist
    for cid, entry in default_skills_block().items():
        merged["skills"].setdefault(cid, entry)
    gr = merged.setdefault("grammar", {})
    gr.pop("numbers_0_20", None)  # migrated pre-merge above
    for fid, entry in default_grammar_block().items():
        gr.setdefault(fid, entry)
    merged.setdefault("error_patterns", {})
    if not isinstance(merged.get("error_patterns"), dict):
        merged["error_patterns"] = {}
    merged["version"] = max(int(merged.get("version") or 1), 2)
    merged["framework"] = base["framework"]
    # Defense in depth (personal-data capture disabled 2026-07-28): legacy
    # sheet files on disk may still carry a name — strip on every load.
    ident = merged.setdefault("identity", {})
    ident["preferred_name"] = None
    ident["engagement_notes"] = ""
    merged = normalize_schedule_fields(merged)
    return recompute_next_best(merged)


def save_sheet(path: Path, sheet: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet = dict(sheet)
    sheet["updated_at"] = today()
    path.write_text(json.dumps(sheet, ensure_ascii=False, indent=2))


def _deep_merge(base: dict, overlay: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (overlay or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def compute_progress_score(sheet: dict | None) -> dict:
    """Simple 0–100 learner score from the character sheet (can-do confidences).

    Crude but visible “you are advancing” signal for the web UI. Refine later.
    """
    sheet = sheet if isinstance(sheet, dict) else {}
    skills = sheet.get("skills") or {}
    # Track core A1 interpersonal + a few others
    track = [f"IP-{i:02d}" for i in range(1, 9)] + ["IT-01", "IT-02", "PR-01"]
    total_conf = 0.0
    known = 0
    emerging = 0
    for cid in track:
        sk = skills.get(cid) if isinstance(skills.get(cid), dict) else {}
        try:
            conf = float(sk.get("confidence") or 0)
        except (TypeError, ValueError):
            conf = 0.0
        conf = max(0.0, min(1.0, conf))
        total_conf += conf
        status = str(sk.get("status") or "unknown").lower()
        if status == "known" or conf >= 0.7:
            known += 1
        elif status in ("emerging", "fragile") or conf > 0.05:
            emerging += 1
    n = len(track)
    score = int(round((total_conf / max(n, 1)) * 100))
    score = max(0, min(100, score))

    # Light bonus for resolved error work (capped)
    err_bonus = 0
    for _pid, ent in (sheet.get("error_patterns") or {}).items():
        if not isinstance(ent, dict):
            continue
        streak = int(ent.get("resolved_streak") or 0)
        if streak >= 2:
            err_bonus += 1
    score = min(100, score + min(5, err_bonus))

    if score < 12:
        level = "Just starting"
    elif score < 30:
        level = "Emerging"
    elif score < 50:
        level = "Building"
    elif score < 70:
        level = "Solid core"
    else:
        level = "Strong A1"

    return {
        "total": score,
        "level": level,
        "known": known,
        "emerging": emerging,
        "tracked": n,
        # Personal-data capture disabled 2026-07-28: never emit a name.
        "name": None,
        "label": f"{score}",
    }


# Domain scope absorbed from the deleted prose pack (2026-08-03).  The
# sheet is a composite artifact: DOMAIN MODEL (what exists at this level
# slice — targets, scope, misconception vocabulary) co-located with the
# LEARNER MODEL (measured state per item).  It is NOT a curriculum: the
# sheet carries content SELECTION; sequence/path belongs solely to the
# teacher model's session plan (vocabulary ruling 2026-08-03,
# docs/reviews-sheet-vocabulary.md).  Rides in the sheet payload so the
# model can plan from one artifact — without it, nothing stops
# out-of-scope drift (past tense etc.).
# S10: the scope is DATA — domain/spanish_a1/domain_scope.json.
DOMAIN_SCOPE: dict = _DOMAIN.domain_scope


def format_sheet_for_prompt(sheet: dict, *, max_lex: int | None = None) -> str:
    """Full character sheet for the tutor model (testing: no silent slimming).

    When TEACHER_CONTEXT_TRUNCATE is later enabled, callers may still clip the
    string via config.clip_prompt — this function itself does not drop fields.
    max_lex=None means entire lexicon.
    """
    skills = sheet.get("skills") or {}
    grammar = {
        k: dict(v) if isinstance(v, dict) else v
        for k, v in (sheet.get("grammar") or {}).items()
    }
    errors = {
        k: dict(v) if isinstance(v, dict) else v
        for k, v in (sheet.get("error_patterns") or {}).items()
    }
    lex = sheet.get("lexicon") or {}
    if max_lex is not None and max_lex > 0:
        lex = dict(list(lex.items())[:max_lex])

    # §1.1a purge (full-code-audit S1b/S1c, 2026-08-03): the MODEL-facing
    # projection ships FACTS only.  next_best (code's agenda) is dropped —
    # the sheet FILE keeps it for the UI rail/telemetry.  teach_hint
    # imperatives ("Recast X → Y") are stripped from error entries — the
    # catalog keeps them for any UI/telemetry use; the model gets label +
    # source + example evidence and decides the move itself.
    active_focus = []
    for e in active_error_patterns(sheet):
        proj = {k: v for k, v in e.items() if k != "teach_hint"}
        src = (ERROR_PATTERN_CATALOG.get(e.get("id")) or {}).get("source")
        if src:
            proj["source"] = src
        active_focus.append(proj)
    for ent in errors.values():
        if isinstance(ent, dict):
            ent.pop("teach_hint", None)

    payload = {
        "now": now_iso(),
        # Personal-data capture disabled 2026-07-28: identity is omitted.
        # The word-inventory payload is GONE (USER 2026-08-03: "Why are we
        # telling this smart ai what spanish words to use?") — a closed
        # word list was machinery-era scaffolding. The model teaches
        # level-appropriate vocabulary under domain_scope's rules; the
        # sheet records whatever was actually taught (open lexicon). The
        # association table remains internal data: image assets, glosses,
        # exposure bookkeeping — never prompt content.
        "domain_scope": DOMAIN_SCOPE,
        "active_error_focus": active_focus,
        "error_patterns": errors,
        "skills": skills,
        "grammar": grammar,
        "affect": sheet.get("affect"),
        "coverage": sheet.get("coverage"),
        "receptive": sheet.get("receptive"),
        "lexicon": lex,
        "updated_at": sheet.get("updated_at"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def format_sheet_human(sheet: dict) -> str:
    lines = ["# Student character sheet", ""]
    # Personal-data capture disabled 2026-07-28: no Name / Goals lines.
    lines.append(f"**Updated:** {sheet.get('updated_at')}")
    lines.append(f"**Now (context):** {now_iso()}")
    nb = sheet.get("next_best") or {}
    lines.append("")
    lines.append("## Next best")
    lines.append(f"- stretch: {nb.get('stretch')}")
    lines.append(f"- avoid: {nb.get('avoid')}")
    lines.append(f"- reason: {nb.get('reason')}")
    if nb.get("error_pattern"):
        lines.append(f"- error_pattern: {nb.get('error_pattern')}")
        lines.append(f"- form_focus: {nb.get('form_focus')}")
    lines.append("")
    lines.append("## Error patterns (recurring)")
    eps = sheet.get("error_patterns") or {}
    if not eps:
        lines.append("- (none tracked)")
    else:
        for pid, ent in sorted(
            eps.items(),
            key=lambda kv: -int((kv[1] or {}).get("count") or 0),
        ):
            if not isinstance(ent, dict):
                continue
            cat = ERROR_PATTERN_CATALOG.get(pid) or {}
            lines.append(
                f"- **{pid}** ×{ent.get('count', 0)} "
                f"[{ent.get('priority', '?')}] last={ent.get('last_seen')}"
            )
            lines.append(f"  - {cat.get('label') or pid}")
            ex = ent.get("last_examples") or []
            if ex:
                lines.append(f"  - e.g. {ex[-1]}")
    lines.append("")
    lines.append("## Can-dos (ACTFL-oriented)")
    for k, v in (sheet.get("skills") or {}).items():
        stmt = v.get("statement") or CAN_DOS.get(k, {}).get("statement", "")
        lines.append(
            f"- **{k}** [{v.get('mode', '?')}/{v.get('band', '?')}]: "
            f"{v.get('status')} ({v.get('confidence', 0):.2f})"
        )
        if stmt:
            lines.append(f"  - *{stmt}*")
    lines.append("")
    lines.append("## Supporting forms (focus-on-form, not the goal)")
    for k, v in (sheet.get("grammar") or {}).items():
        lines.append(
            f"- {k}: {v.get('status')} conf={v.get('confidence', 0):.2f} "
            f"priority={v.get('priority')}"
        )
    aff = sheet.get("affect") or {}
    lines.append("")
    lines.append("## Affect")
    lines.append(f"- last_meta: {aff.get('last_meta')}")
    cov = sheet.get("coverage") or {}
    lines.append("")
    lines.append(f"**Touched:** {', '.join(cov.get('touched') or []) or '—'}")
    lines.append(
        f"**Never touched:** {', '.join(cov.get('never_touched') or []) or '—'}"
    )
    lex = sheet.get("lexicon") or {}
    if lex:
        lines.append("")
        lines.append("## Lexicon (sample)")
        for i, (w, meta) in enumerate(lex.items()):
            if i >= 25:
                lines.append(f"- … +{len(lex) - 25} more")
                break
            lines.append(
                f"- {w}: {meta.get('status')} ({meta.get('confidence', 0):.2f})"
            )
    return "\n".join(lines)


# --- Ability state machine (Phase 1.5 batch 2, machine B) --------------------
#
# docs/reviews-architecture-refactor.md, adjudicated round-1 (b): this is the
# ABILITY axis of the two-axis item-lifecycle design — bands + confidence +
# solid_uses, orthogonal to machine A (retrieval_scheduler schedule axis).
# Introduction transitions MUST NOT write this axis (honesty law, enforced by
# the scheduler's _write allowlist); ability transitions MUST NOT move
# SCHEDULE_FIELDS (the mirror guard, enforced here in ability_transition).
#
# REAL band vocabulary, derived from the writers (not the round-1 sketch
# "unknown/fragile/emerging/known"):
#
#   unknown    — no evidence, or a missing/invalid status (ability_band maps
#                absent entries and out-of-vocabulary strings here; the
#                honest-zero shells machine A creates land here too).
#   emerging   — positive-evidence band. _bump_status on success goes
#                unknown → emerging DIRECTLY (never through fragile): the
#                bands below known are SIBLINGS colored by evidence
#                direction, not ordered rungs of a ladder.
#   fragile    — negative-evidence band at conf >= FRAGILE_MIN_CONF (a
#                failure with less residual confidence lands on unknown).
#                REAL (the sketch had it), but only ever entered on failure
#                or by tool/model claim — never by a success bump.
#   known      — gated band: conf >= KNOWN_MIN_CONF and solid_uses >=
#                KNOWN_MIN_SOLID_USES. The gate arithmetic LIVES IN THE
#                WRITERS (adjudication: "KNOWN-gate evidence stays a gate,
#                not an enum") — the machine validates edges only, because
#                legacy/seeded sheets legally hold known with solid_uses 0
#                and _clamp_skill_entry preserves that claim (prev-known +
#                conf >= gate keeps known without uses).
#   blocked    — in the vocabulary (STATUSES, tool schema enum) but NOT
#                producible by any code writer: only a tool/model delta can
#                enter it; _bump_status ESCAPES it (success → emerging,
#                fail → fragile/unknown). Divergence from the sketch, which
#                omitted it.
#
# DOWN edges are real and everywhere: known → emerging (_cap_turn_confidence
# re-gate demotion), known → fragile/unknown (_bump_status failure),
# emerging → unknown, etc. known → known survives failure while conf/uses
# hold the gate. The UNION graph is COMPLETE (every band reaches every
# band, via "bump" evidence) — but the per-via tables below are where the
# machine has real teeth: "cap" and "normalize" are narrow, "bump" cannot
# mint blocked, the tool vias ("tool_merge"/"delta_lexicon") cannot land
# unknown → known or blocked → known (CHAR-BUG-008/009 fix, 2026-07-29),
# and EVERY via rejects cross-axis (schedule-field) writes.

ABILITY_BANDS = STATUSES

Band = Literal["unknown", "emerging", "fragile", "known", "blocked"]

# Ability-axis fields (mirror of retrieval_scheduler._PROTECTED_FIELDS —
# kept in sync by test, not import, so the scheduler stays stdlib-only).
ABILITY_FIELDS = ("confidence", "status", "solid_uses")


class IllegalAbilityTransition(ValueError):
    """An ability-band move outside the legal edge set (rejected at write)."""


def ability_band(entry: dict | None) -> Band:
    """Ability band of one sheet entry (ability axis only; strict vocabulary).

    Missing entries and out-of-vocabulary statuses are band "unknown" — the
    ability axis has no "absent": an item never used is simply unknown.
    """
    if not isinstance(entry, dict):
        return "unknown"
    status = entry.get("status")
    return status if status in STATUSES else "unknown"


# Bands a code writer (_bump_status) can produce — blocked is tool-only.
_CODE_BANDS = ("unknown", "emerging", "fragile", "known")

# Edges a clamped tool/model claim can land (CHAR-BUG-008/009 fix,
# 2026-07-29). Claims may move freely into the ungated bands (honest
# demotion, blocked flags, evidence-direction siblings); promotion to
# `known` requires prior known (legacy claim preserved) or a sub-known
# EVIDENCE band with code-observed uses + conf at the gate — so
# unknown → known and blocked → known are not writer-producible: routine
# inflation is CLAMPED to emerging in the writer (the _cap_turn_confidence
# philosophy); the machine raising on these two edges is the
# production-unreachable regression backstop (mirror of the batch-1
# double-introduce ruling).
_TOOL_CLAIM_EDGES = frozenset(
    {(f, t) for f in STATUSES
     for t in ("unknown", "emerging", "fragile", "blocked")}
    | {(f, "known") for f in ("emerging", "fragile", "known")}
)

# Per-operation legal edges. As in machine A, `to` alone under-determines
# the write set, so legality is (via, from, to); ABILITY_TRANSITIONS is the
# union view of the same graph.
_ABILITY_VIA_EDGES: dict[str, frozenset] = {
    # _bump_status: heuristic observer evidence (apply_rule_updates sites +
    # note_error_pattern grammar mirror). Any band → any CODE band; blocked
    # is escapable here, never enterable.
    "bump": frozenset(
        (f, t) for f in STATUSES for t in _CODE_BANDS
    ),
    # _clamp_skill_entry: tool/model delta merge for skills/grammar.
    # TIGHTENED from edge-complete (CHAR-BUG-008 fix, 2026-07-29): the
    # solid_uses claim is no longer trusted — code-observed evidence is the
    # only source that increments uses, so the known gate (conf + observed
    # uses) is uncrossable by claim alone. See _TOOL_CLAIM_EDGES.
    "tool_merge": _TOOL_CLAIM_EDGES,
    # apply_delta lexicon branches (dict merge + bare-string status): since
    # the CHAR-BUG-009 fix (2026-07-29) BOTH route through
    # _clamp_skill_entry (via="delta_lexicon") — no branch mints
    # band/confidence unclamped; a new-word known-claim at conf 1.0 lands
    # emerging at the +0.25 first-appearance ceiling. Same edge set as
    # tool_merge.
    "delta_lexicon": _TOOL_CLAIM_EDGES,
    # _cap_turn_confidence: per-turn ceiling clips + the known re-gate.
    # The genuinely narrow via: band self-loops (clips) plus the ONE
    # demotion edge known → emerging.
    "cap": frozenset(
        {(s, s) for s in STATUSES} | {("known", "emerging")}
    ),
    # normalize_sheet: coercion of an AI full rewrite. Band self-loops only
    # (an invalid status already IS band unknown, so coercing the string to
    # "unknown" does not move the band).
    "normalize": frozenset((s, s) for s in STATUSES),
}

# Union graph over all operations (the machine's band-level view). COMPLETE
# — documented finding, not an oversight: see the block comment above.
ABILITY_TRANSITIONS: dict[str, set[str]] = {
    s: set(STATUSES) for s in STATUSES
}


def _check_ability_graph_sync() -> None:
    derived: dict[str, set[str]] = {}
    for edges in _ABILITY_VIA_EDGES.values():
        for f, t in edges:
            derived.setdefault(f, set()).add(t)
    if derived != ABILITY_TRANSITIONS:
        raise RuntimeError(
            "character_sheet: ABILITY_TRANSITIONS out of sync with "
            "_ABILITY_VIA_EDGES"
        )


_check_ability_graph_sync()


def ability_transition(
    entry: dict | None,
    staged: dict,
    *,
    via: str,
    evidence: dict | None = None,
) -> dict:
    """Central ability-axis write: validate the band edge, guard cross-axis.

    Every band/confidence/solid_uses writer routes its result through here
    (the writers stay the places that COMPUTE field values — same
    signatures, same outcomes; this validates and returns `staged`
    unchanged). Divergence from the sketched `(entry, *, evidence, via)`
    signature: the pre-write entry is needed to know the from-band, so the
    call is (pre, staged) — mirror of machine A's added `via` discriminator.

    Rejections:
    - unknown `via` → ValueError (programmer error);
    - a band move outside _ABILITY_VIA_EDGES[via] → IllegalAbilityTransition;
    - any move of a SCHEDULE_FIELDS member (added, removed, or changed
      relative to the pre-write entry) → ValueError — the mirror image of
      the scheduler `_write` allowlist: ability writers may never touch the
      schedule axis (honesty law, both directions).

    `evidence` is OPAQUE context for error messages — evidence QUALITY
    stays with the gates (known gate, per-turn caps), never validated here.
    """
    if via not in _ABILITY_VIA_EDGES:
        raise ValueError(f"unknown ability transition via {via!r}")
    prev = entry if isinstance(entry, dict) else {}
    from_band = ability_band(prev)
    to_band = ability_band(staged)
    if (
        to_band not in ABILITY_TRANSITIONS.get(from_band, set())
        or (from_band, to_band) not in _ABILITY_VIA_EDGES[via]
    ):
        raise IllegalAbilityTransition(
            f"illegal {via!r} ability transition {from_band} -> {to_band} "
            f"(evidence: {evidence!r})"
        )
    moved = [
        f for f in sorted(SCHEDULE_FIELDS)
        if (f in prev) != (f in staged) or prev.get(f) != staged.get(f)
    ]
    if moved:
        raise ValueError(
            f"ability writer may not move {moved} (honesty law; "
            f"via {via!r}, evidence: {evidence!r})"
        )
    return staged


def _bump_status(entry: dict, *, success: bool, amount: float = 0.15) -> dict:
    """Heuristic status bump with per-call cap and known-gate.

    The net per-turn ceiling is enforced in process_turn via
    _cap_turn_confidence — stacked calls here may not exceed it.
    Thin wrapper over `ability_transition` (via="bump"; Phase 1.5 batch 2):
    the band ladder below is unchanged; the machine validates the edge and
    rejects cross-axis (schedule-field) writes.
    """
    e = dict(entry)
    prev_c = float(e.get("confidence") or 0.0)
    if success:
        conf = min(1.0, prev_c + min(amount, MAX_CONF_UP_PER_TURN))
    else:
        conf = max(0.0, prev_c - min(amount * 0.7, MAX_CONF_DOWN_PER_TURN))
    e["confidence"] = round(conf, 3)
    e["last_seen"] = today()
    uses = int(e.get("solid_uses") or 0)
    if success and conf > prev_c + 0.02:
        uses += 1
    e["solid_uses"] = uses

    if (
        conf >= KNOWN_MIN_CONF
        and uses >= KNOWN_MIN_SOLID_USES
        and success
    ) or (e.get("status") == "known" and conf >= KNOWN_MIN_CONF and uses >= KNOWN_MIN_SOLID_USES):
        e["status"] = "known"
    elif conf >= EMERGING_MIN_CONF:
        e["status"] = "emerging" if success else "fragile"
    elif conf >= FRAGILE_MIN_CONF:
        e["status"] = "fragile" if not success else "emerging"
    else:
        e["status"] = "emerging" if success else "unknown"
    # Never label known without enough solid uses
    if e["status"] == "known" and uses < KNOWN_MIN_SOLID_USES:
        e["status"] = "emerging"
        e["confidence"] = min(float(e["confidence"]), 0.75)
    return ability_transition(
        entry, e, via="bump",
        evidence={"success": success, "amount": amount},
    )


def _cap_turn_confidence(start: dict, staged: dict, final: dict) -> dict:
    """Enforce a net per-turn confidence (and solid_uses) ceiling after stacking.

    _bump_status caps a single call, but tool credit plus stacked observer
    bumps double-count one utterance (empirically conf 0→0.5 and solid_uses
    0→2). Final conf for a key may not exceed
    max(start_c + MAX_CONF_UP_PER_TURN, staged_c). Final solid_uses may not
    exceed max(start_uses + 1, staged_uses). After clipping conf, re-gate
    status so 'known' cannot remain with conf < KNOWN_MIN_CONF or uses
    < KNOWN_MIN_SOLID_USES.

    staged is the sheet after tool/AI merge and before apply_rule_updates.
    Observer-only paths pass start as staged (ceiling = start + cap only).
    Note: the AI full-rewrite path has no +0.25 honesty clamp of its own —
    staged values from it are preserved as-is (closing that is a separate
    change; see docs/reviews-system-overview.md countersign 2026-07-26).
    """
    for section in ("skills", "grammar", "lexicon"):
        fin = final.get(section)
        if not isinstance(fin, dict):
            continue
        st = start.get(section) if isinstance(start.get(section), dict) else {}
        stg = staged.get(section) if isinstance(staged.get(section), dict) else {}
        for key, entry in fin.items():
            if not isinstance(entry, dict):
                continue
            pre_entry = dict(entry)  # machine B: pre-write snapshot
            st_e = st.get(key) if isinstance(st.get(key), dict) else {}
            stg_e = stg.get(key) if isinstance(stg.get(key), dict) else {}
            start_c = float(st_e.get("confidence") or 0.0)
            staged_c = float(stg_e.get("confidence") or 0.0)
            try:
                start_u = int(st_e.get("solid_uses") or 0)
            except (TypeError, ValueError):
                start_u = 0
            try:
                staged_u = int(stg_e.get("solid_uses") or 0)
            except (TypeError, ValueError):
                staged_u = 0

            cur = None
            if entry.get("confidence") is not None:
                try:
                    cur = float(entry["confidence"])
                except (TypeError, ValueError):
                    cur = None
                if cur is not None:
                    ceiling = max(start_c + MAX_CONF_UP_PER_TURN, staged_c)
                    if cur > ceiling:
                        entry["confidence"] = round(ceiling, 3)
                        cur = float(entry["confidence"])

            try:
                cur_u = int(entry.get("solid_uses") or 0)
            except (TypeError, ValueError):
                cur_u = 0
            u_ceiling = max(start_u + 1, staged_u)
            if cur_u > u_ceiling:
                entry["solid_uses"] = u_ceiling
                cur_u = u_ceiling

            # Re-gate known after any clip (conf and/or uses).
            if entry.get("status") == "known":
                conf_now = cur if cur is not None else float(entry.get("confidence") or 0.0)
                if conf_now < KNOWN_MIN_CONF or cur_u < KNOWN_MIN_SOLID_USES:
                    entry["status"] = "emerging"
            # Machine B (via="cap"): the narrow via — self-loops (clips)
            # plus the one demotion edge known → emerging; in-place
            # mutation retained, the machine validates the write.
            ability_transition(
                pre_entry, entry, via="cap",
                evidence={"section": section, "key": key},
            )
    return final


def _clamp_skill_entry(
    prev: dict, incoming: dict, *, via: str = "tool_merge"
) -> dict:
    """Merge a tool/model skills, grammar, or lexicon claim with honesty clamps.

    CHAR-BUG-008/009 (2026-07-29) + tool-only ability (2026-07-31) — the model
    cannot inflate the diagnosis by claim alone (ENGINEERING §3.2/§4.5;
    P7 theory in PEDAGOGY §0):

    - confidence is rate-limited around prev (±MAX_CONF_UP/DOWN_PER_TURN);
    - solid_uses: a tool conf **rise** mints at most +1 use this merge
      (tool-confirmed success). An incoming solid_uses claim may only
      **lower** the count (honest demotion), never raise past observed.
      Known still needs conf ≥ KNOWN_MIN_CONF and uses ≥ KNOWN_MIN_SOLID_USES;
    - known promotion requires prior known, or emerging/fragile with uses
      + conf at the gate. Over-claims clamp to emerging (conf capped 0.75).
    """
    prev = prev or {}
    incoming = incoming or {}
    merged = {**prev, **incoming}
    prev_c = float(prev.get("confidence") or 0.0)
    if "confidence" in incoming:
        try:
            new_c = float(incoming["confidence"])
        except (TypeError, ValueError):
            new_c = prev_c
        new_c = max(0.0, min(1.0, new_c))
        if new_c > prev_c + MAX_CONF_UP_PER_TURN:
            new_c = round(prev_c + MAX_CONF_UP_PER_TURN, 3)
        elif new_c < prev_c - MAX_CONF_DOWN_PER_TURN:
            new_c = round(prev_c - MAX_CONF_DOWN_PER_TURN, 3)
        merged["confidence"] = new_c
    else:
        new_c = prev_c

    # solid_uses: code-owned counter of tool-confirmed successes.
    # Regex observer no longer increments this (2026-07-31). A conf rise from
    # the teacher tool counts as one solid use this turn; claimed solid_uses
    # may only lower the count (honest demotion), never raise past observed.
    uses = int(prev.get("solid_uses") or 0)
    status_in = incoming.get("status")
    if "confidence" in incoming and new_c > prev_c + 0.02:
        uses = uses + 1
    if "solid_uses" in incoming:
        try:
            uses = min(uses, max(0, int(incoming["solid_uses"])))
        except (TypeError, ValueError):
            pass
    merged["solid_uses"] = uses

    status = merged.get("status") if merged.get("status") in STATUSES else (
        prev.get("status") or "unknown"
    )
    prev_band = ability_band(prev)
    # Gate known: prior known, OR an evidence band with observed uses + conf.
    if status == "known":
        if prev_band == "known" and new_c >= KNOWN_MIN_CONF:
            pass
        elif (
            prev_band in ("emerging", "fragile")
            and uses >= KNOWN_MIN_SOLID_USES
            and new_c >= KNOWN_MIN_CONF
        ):
            pass
        else:
            # Over-claim → emerging (positive evidence), not fragile
            status = "emerging"
            if new_c > 0.75:
                merged["confidence"] = 0.75
                new_c = 0.75
    if status == "known" and new_c < KNOWN_MIN_CONF:
        status = "emerging"
    if status not in STATUSES:
        status = "unknown"
    merged["status"] = status
    # Machine B: the tool vias are TIGHTENED (see _TOOL_CLAIM_EDGES) — the
    # clamps above are the protection; the machine adds the cross-axis
    # guard (apply_delta strips SCHEDULE_ENTRY_FIELDS before this call, so
    # a schedule-field move here is unreachable in production and raises at
    # function level) and rejects the two impossible promotions.
    return ability_transition(
        prev, merged, via=via,
        evidence={"status_in": status_in},
    )


def _touch_coverage(sheet: dict, topic: str) -> None:
    cov = sheet.setdefault("coverage", {"touched": [], "never_touched": []})
    touched = list(cov.get("touched") or [])
    never = list(cov.get("never_touched") or [])
    if topic not in touched:
        touched.append(topic)
    if topic in never:
        never.remove(topic)
    cov["touched"] = touched
    cov["never_touched"] = never


def _auto_coverage_from_evidence(sheet: dict, *, skill_ids=None, grammar_ids=None) -> None:
    """Mark coverage topics from can-dos / forms that moved this turn."""
    for cid in skill_ids or []:
        meta = CAN_DOS.get(cid) or {}
        for topic in meta.get("coverage_topics") or []:
            _touch_coverage(sheet, topic)
    for fid in grammar_ids or []:
        for topic in _GRAMMAR_COVERAGE.get(fid) or []:
            _touch_coverage(sheet, topic)


def _preserve_identity(before: dict, after: dict) -> dict:
    """Personal-data capture disabled 2026-07-28: identity is stripped, never preserved."""
    s = after
    ident = dict(s.get("identity") or {})
    ident["preferred_name"] = None
    ident["engagement_notes"] = ""
    s["identity"] = ident
    return s


def _note_evidence(grammar_entry: dict, note: str, *, limit: int = 5) -> None:
    ev = list(grammar_entry.get("evidence") or [])
    if note and note not in ev:
        ev.append(note)
    grammar_entry["evidence"] = ev[-limit:]


def detect_error_pattern_hits(learner: str) -> list[tuple[str, str]]:
    """Return [(pattern_id, example_snippet), ...] for known error constructions.

    S10: patterns are compiled at load (domain_data) — same catalog order,
    same case-insensitive match over folded-then-raw text as the historical
    per-call ``re.search``.
    """
    text = learner or ""
    if not text.strip() or text.startswith("🎤") or text.startswith("⏳"):
        return []
    f = fold(text)
    hits: list[tuple[str, str]] = []
    for pid, pats in _DETECT_COMPILED.items():
        for rx, note in pats:
            if rx.search(f) or rx.search(text):
                # Prefer a short raw span as example
                m = rx.search(text) or rx.search(f)
                snippet = (m.group(0) if m else note)[:80]
                hits.append((pid, snippet))
                break
    return hits


def detect_error_pattern_resolves(learner: str) -> list[str]:
    """Pattern ids that look correctly used this turn."""
    text = learner or ""
    f = fold(text)
    out: list[str] = []
    for pid, pats in _RESOLVE_COMPILED.items():
        for rx in pats:
            if rx.search(f) or rx.search(text):
                out.append(pid)
                break
    return out


def note_error_pattern(
    sheet: dict,
    pattern_id: str,
    example: str,
    *,
    resolved: bool = False,
) -> dict:
    """Increment or ease a recurring error pattern on the sheet."""
    s = sheet  # mutate in place when already a copy
    pattern_id = normalize_error_pattern_id(pattern_id)
    eps = s.setdefault("error_patterns", {})
    # Merge any pre-normalization alias entry into the canonical id
    for alias, canon in ERROR_PATTERN_ALIASES.items():
        if canon == pattern_id and alias in eps and alias != pattern_id:
            old = eps.pop(alias) or {}
            if isinstance(old, dict):
                base = eps.get(pattern_id) or {}
                if not base:
                    eps[pattern_id] = old
                else:
                    base["count"] = int(base.get("count") or 0) + int(
                        old.get("count") or 0
                    )
                    ex = list(base.get("last_examples") or [])
                    for e in old.get("last_examples") or []:
                        if e not in ex:
                            ex.append(e)
                    base["last_examples"] = ex[-5:]
                    eps[pattern_id] = base
    cat = ERROR_PATTERN_CATALOG.get(pattern_id) or {}
    ent = dict(eps.get(pattern_id) or {
        "count": 0,
        "priority": "low",
        "last_examples": [],
        "label": cat.get("label") or pattern_id,
        "form_id": cat.get("form_id"),
        "can_dos": list(cat.get("can_dos") or []),
        "teach_hint": cat.get("teach_hint") or "",
        "last_seen": None,
        "resolved_streak": 0,
        "correct_uses": 0,
    })
    # stamp catalog fields
    ent["label"] = cat.get("label") or ent.get("label") or pattern_id
    ent["form_id"] = cat.get("form_id")
    ent["can_dos"] = list(cat.get("can_dos") or ent.get("can_dos") or [])
    ent["teach_hint"] = cat.get("teach_hint") or ent.get("teach_hint") or ""
    ent.setdefault("correct_uses", 0)
    ent.setdefault("resolved_streak", 0)

    if resolved:
        streak = int(ent.get("resolved_streak") or 0) + 1
        ent["resolved_streak"] = streak
        ent["correct_uses"] = int(ent.get("correct_uses") or 0) + 1
        c0 = int(ent.get("count") or 0)
        # Progressive ease: each clean use chips the error count (faster when
        # the learner is on a roll of correct forms).
        if c0 > 0:
            if streak >= 5:
                drop = c0  # long clean streak → clear residual
            elif streak >= 3:
                drop = min(c0, 2)
            else:
                drop = 1
            ent["count"] = max(0, c0 - drop)
        ent["last_seen"] = now_iso()
        # Keep a short trail of correct evidence
        ex = list(ent.get("last_examples") or [])
        if example and example not in ex and example != "correct use":
            ex.append(f"✓{example[:90]}")
            ent["last_examples"] = ex[-5:]
    else:
        ent["count"] = int(ent.get("count") or 0) + 1
        ent["resolved_streak"] = 0  # break the clean streak
        ent["last_seen"] = now_iso()
        ex = list(ent.get("last_examples") or [])
        if example and example not in ex:
            ex.append(example[:100])  # truncation-ok: sheet storage example cap
        ent["last_examples"] = ex[-5:]

    c = int(ent.get("count") or 0)
    streak = int(ent.get("resolved_streak") or 0)
    if c == 0 and streak >= ERROR_PATTERN_HEALTHY_STREAK:
        ent["priority"] = "low"  # recovered
    elif c >= 4:
        ent["priority"] = "high"
    elif c >= ERROR_PATTERN_PRIORITY_THRESHOLD:
        ent["priority"] = "high"
    elif c == 1:
        ent["priority"] = "medium"
    else:
        ent["priority"] = "low"

    eps[pattern_id] = ent

    # Mirror into supporting grammar form when linked
    fid = ent.get("form_id")
    if fid and not resolved:
        g = s.setdefault("grammar", default_grammar_block())
        prev = g.get(fid) or {}
        g[fid] = _bump_status(prev, success=False, amount=0.15)
        _note_evidence(g[fid], f"error_pattern:{pattern_id}:{example[:40]}")
        g[fid]["last_seen"] = today()
    elif fid and resolved:
        g = s.setdefault("grammar", default_grammar_block())
        prev = g.get(fid) or {}
        g[fid] = _bump_status(prev, success=True, amount=0.12)
        _note_evidence(g[fid], f"resolved:{pattern_id}")
        g[fid]["last_seen"] = today()

    return s


def apply_error_pattern_updates(sheet: dict, learner: str) -> dict:
    """Detect recurring constructions from this learner turn."""
    s = copy.deepcopy(sheet)
    s.setdefault("error_patterns", {})
    hits = detect_error_pattern_hits(learner)
    hit_ids = {pid for pid, _ in hits}
    for pid, snippet in hits:
        note_error_pattern(s, pid, snippet, resolved=False)
    for pid in detect_error_pattern_resolves(learner):
        # Same-turn error beats resolve (e.g. "yo está… estoy?" still an error turn)
        if pid in hit_ids:
            continue
        # Only count resolve if pattern already known / was an issue
        if pid in (s.get("error_patterns") or {}):
            note_error_pattern(s, pid, "correct use", resolved=True)
    return s


def pattern_needs_form_focus(ent: dict) -> bool:
    """True while the form still needs weaving — not only when count is hot.

    Keep focus until residual count is gone *and* resolved_streak is healthy,
    so one lucky *estoy* doesn't abandon the form.
    """
    if not isinstance(ent, dict):
        return False
    c = int(ent.get("count") or 0)
    streak = int(ent.get("resolved_streak") or 0)
    correct = int(ent.get("correct_uses") or 0)
    examples = ent.get("last_examples") or []
    ever = c >= 1 or correct >= 1 or bool(examples)
    if not ever:
        return False
    # Fully recovered
    if c == 0 and streak >= ERROR_PATTERN_HEALTHY_STREAK:
        return False
    # Hot errors
    if c >= ERROR_PATTERN_PRIORITY_THRESHOLD:
        return True
    # Residual errors or still weaning (need consecutive correct uses)
    if c >= 1:
        return True
    # count cleared but streak not healthy yet
    if c == 0 and streak < ERROR_PATTERN_HEALTHY_STREAK and correct >= 1:
        return True
    return False


def active_error_patterns(
    sheet: dict,
    *,
    min_count: int = ERROR_PATTERN_PRIORITY_THRESHOLD,
) -> list[dict]:
    """Patterns that should drive teaching (hot count or still weaning)."""
    out: list[dict] = []
    for pid, ent in (sheet.get("error_patterns") or {}).items():
        if not isinstance(ent, dict):
            continue
        c = int(ent.get("count") or 0)
        # Hot (count ≥ threshold) or still needs form focus (residual / recovering)
        if c < min_count and not pattern_needs_form_focus(ent):
            continue
        cat = ERROR_PATTERN_CATALOG.get(pid) or {}
        streak = int(ent.get("resolved_streak") or 0)
        out.append({
            "id": pid,
            "count": c,
            "resolved_streak": streak,
            "correct_uses": int(ent.get("correct_uses") or 0),
            "priority": ent.get("priority") or "high",
            "label": ent.get("label") or cat.get("label") or pid,
            "form_id": ent.get("form_id") or cat.get("form_id"),
            "can_dos": ent.get("can_dos") or cat.get("can_dos") or [],
            "teach_hint": ent.get("teach_hint") or cat.get("teach_hint") or "",
            "last_examples": list(ent.get("last_examples") or [])[-3:],
            "last_seen": ent.get("last_seen"),
        })
    # Hottest errors first; among equals, lower streak (needs more practice) first
    out.sort(key=lambda x: (-x["count"], x.get("resolved_streak", 0), x["id"]))
    return out


def apply_rule_updates(
    sheet: dict,
    learner: str,
    tutor_visible: str = "",
    *,
    preferred_name: str | None = None,
    store_identity: bool = True,
) -> dict:
    """DEPRECATED 2026-07-31 — regex ability grading removed.

    Ability (skills / grammar / lexicon / error_patterns conf) changes only
    via ``update_character_sheet`` tool + ``process_turn``. This function is a
    no-op identity kept for callers/tests that still import it: it deep-copies,
    recomputes ``next_best`` from existing sheet state, and stamps
    ``updated_at``. Learner text is ignored for ability.

    ``store_identity`` / ``preferred_name`` remain accepted for compatibility
    and are ignored (personal-data capture disabled 2026-07-28).
    """
    del learner, tutor_visible, store_identity  # ability no longer from text
    s = copy.deepcopy(sheet)
    s = recompute_next_best(s, preferred_name=preferred_name)
    s["updated_at"] = today()
    return s


def grade_why_ok(delta: dict | None) -> bool:
    """True when delta carries a non-trivial why/reason for a grade."""
    if not isinstance(delta, dict):
        return False
    why = delta.get("reason") or delta.get("why") or delta.get("notes")
    return isinstance(why, str) and len(why.strip()) >= MIN_GRADE_WHY_LEN


def delta_claims_ability(delta: dict | None) -> bool:
    """True when delta tries to change skills/grammar/lexicon/error_patterns."""
    if not isinstance(delta, dict):
        return False
    return any(k in delta for k in _ABILITY_DELTA_KEYS)


def sanitize_tool_delta(delta: dict | None) -> dict:
    """Keep only trusted top-level keys from a tool / model delta."""
    if not isinstance(delta, dict):
        return {}
    # "identity" is intentionally NOT allowed — personal-data capture is
    # disabled (2026-07-28); no tool/model delta may carry names or notes.
    allowed = {
        "affect", "next_best", "lexicon", "skills", "grammar",
        "coverage", "receptive", "error_patterns", "reason", "notes",
        "why", "evidence",
    }
    return {k: v for k, v in delta.items() if k in allowed}


def apply_delta(sheet: dict, delta: dict) -> dict:
    """Merge a model-proposed partial delta (trusted fields only).

    Used by tool-call updates and legacy <sheet_delta> blocks.
    Prefers a well-formed delta next_best; otherwise recomputes.
    Applies confidence caps, known-gates, name preservation, coverage auto-touch.
    """
    delta = sanitize_tool_delta(delta)
    if not delta:
        return sheet
    before = sheet
    s = copy.deepcopy(sheet)

    # Personal-data capture disabled 2026-07-28: never merge an "identity"
    # key from any delta (sanitize already drops it; belt and braces).
    delta.pop("identity", None)

    if "affect" in delta and isinstance(delta["affect"], dict):
        aff = {**s.get("affect", {}), **delta["affect"]}
        s["affect"] = aff

    if "receptive" in delta and isinstance(delta["receptive"], dict):
        rec = {**s.get("receptive", {}), **delta["receptive"]}
        if "needs_english_scaffold" in delta["receptive"]:
            rec["needs_english_scaffold"] = bool(
                delta["receptive"]["needs_english_scaffold"])
        s["receptive"] = rec

    had_next = isinstance(delta.get("next_best"), dict) and bool(
        delta["next_best"].get("activity")
        or delta["next_best"].get("stretch")
        or delta["next_best"].get("can_do")
        or delta["next_best"].get("reason")
    )
    if "next_best" in delta and isinstance(delta["next_best"], dict):
        s["next_best"] = {**s.get("next_best", {}), **delta["next_best"]}
        nb = s["next_best"]
        if not nb.get("method"):
            nb["method"] = "CLT/TBLT + CI + focus_on_form"
        if nb.get("can_do") in CAN_DOS and not nb.get("statement"):
            nb["statement"] = CAN_DOS[nb["can_do"]]["statement"]
        if nb.get("activity") and not nb.get("stretch"):
            nb["stretch"] = nb["activity"]
        if nb.get("stretch") and not nb.get("activity"):
            nb["activity"] = nb["stretch"]

    touched_skills: list[str] = []
    touched_grammar: list[str] = []
    for section in ("lexicon", "skills", "grammar"):
        if section in delta and isinstance(delta[section], dict):
            base = s.setdefault(section, {})
            for k, v in delta[section].items():
                if not isinstance(v, dict):
                    if section == "lexicon" and isinstance(v, str):
                        prev = base.get(k) or {}
                        # CHAR-BUG-009 fix (2026-07-29): bare-string status
                        # claims route through the same clamp as every other
                        # claim (an out-of-vocabulary string claims nothing).
                        merged = _clamp_skill_entry(
                            prev,
                            {"status": v} if v in STATUSES else {},
                            via="delta_lexicon",
                        )
                        merged["last_seen"] = today()
                        base[k] = merged
                    continue
                # Scheduler/ledger fields are CODE-owned (retrieval_scheduler):
                # no tool/model delta may set due dates or introduce facts.
                v = {
                    kk: vv for kk, vv in v.items()
                    if kk not in SCHEDULE_ENTRY_FIELDS
                }
                prev = base.get(k) or {}
                if section in ("skills", "grammar"):
                    merged = _clamp_skill_entry(prev, v)
                    merged["last_seen"] = today()
                    base[k] = merged
                    if section == "skills":
                        touched_skills.append(k)
                    else:
                        touched_grammar.append(k)
                else:
                    # CHAR-BUG-009 fix (2026-07-29): the lexicon dict merge
                    # routes through _clamp_skill_entry exactly like
                    # skills/grammar — no branch mints band/confidence
                    # unclamped. A new-word known-claim at conf 1.0 lands
                    # emerging at the +0.25 first-appearance ceiling, and
                    # uses claims cannot raise the observed count
                    # (CHAR-BUG-008). Schedule fields were stripped from
                    # `v` above, so they cannot move here.
                    base[k] = _clamp_skill_entry(
                        prev, v, via="delta_lexicon"
                    )

    if "coverage" in delta and isinstance(delta["coverage"], dict):
        for topic in delta["coverage"].get("touched") or []:
            if isinstance(topic, str):
                _touch_coverage(s, topic)

    # Tool error_patterns: one harness count bump per tool call (not per
    # example) via note_error_pattern — no regex auto-detect (2026-07-31).
    if "error_patterns" in delta and isinstance(delta["error_patterns"], dict):
        for pid, v in delta["error_patterns"].items():
            if not isinstance(v, dict):
                continue
            pid = normalize_error_pattern_id(pid)
            if pid not in ERROR_PATTERN_CATALOG and not v.get("last_examples"):
                continue
            if v.get("resolved") or v.get("resolved_streak"):
                note_error_pattern(s, pid, "tool:resolved", resolved=True)
                continue
            examples = [
                item.strip()[:100]  # truncation-ok: sheet storage example cap
                for item in (v.get("last_examples") or [])
                if isinstance(item, str) and item.strip()
            ]
            snippet = examples[-1] if examples else "tool:noted"
            note_error_pattern(s, pid, snippet, resolved=False)
            # Keep extra examples on the entry without further count bumps.
            if examples:
                ent = (s.get("error_patterns") or {}).get(pid)
                if isinstance(ent, dict):
                    ex = list(ent.get("last_examples") or [])
                    for item in examples:
                        if item not in ex:
                            ex.append(item)
                    ent["last_examples"] = ex[-5:]

    _auto_coverage_from_evidence(
        s, skill_ids=touched_skills, grammar_ids=touched_grammar,
    )

    s = _preserve_identity(before, s)
    s["updated_at"] = today()
    # Always recompute if active error patterns should override a weak next_best
    if had_next and not active_error_patterns(s):
        return s
    if had_next and active_error_patterns(s):
        # Keep AI activity but stamp form focus
        s = recompute_next_best(s)
        return s
    return recompute_next_best(s)


# Anthropic-style tool definition (Gemini adapter converts to OpenAI tools).
UPDATE_CHARACTER_SHEET_TOOL = {
    "name": "update_character_sheet",
    "description": (
        "Grade the learner's Spanish ability when THIS turn gives clear NEW "
        "evidence (solo success, repeated failure, recovery after repair, "
        "durable re-use). Partial delta only.\n"
        "USE when: you can quote what they produced (or failed to produce) "
        "and ability should move up or down.\n"
        "DO NOT use when: you only modeled the form, they only echoed you, "
        "you are unsure, or you are tidying the sheet. Prefer no call.\n"
        "REQUIRED: reason (why, evidence-based, ≥12 chars) whenever you "
        "change skills, grammar, lexicon, or error_patterns. Strongly "
        "preferred: evidence (short quote from the LEARNER, not you). "
        "Calls without a real reason are rejected — ability does not change.\n"
        "Be conservative: prefer emerging/fragile over known; one good turn "
        "is not mastery. Do not claim solid_uses (code counts tool-confirmed "
        "successes). Do not record names or personal facts. "
        "Student never sees this tool."
    ),
    "input_schema": {
        "type": "object",
        "required": ["reason"],
        "properties": {
            "reason": {
                "type": "string",
                "description": (
                    "Why this grade changes: what they did in Spanish "
                    "(or failed to do). Min ~12 chars. Required for ability."
                ),
            },
            "evidence": {
                "type": "string",
                "description": (
                    "Short quote from the LEARNER's message that justifies "
                    "the grade (not your model line)."
                ),
            },
            "error_patterns": {
                "type": "object",
                "description": (
                    "Recurring construction errors. Keys e.g. "
                    "estar_yo_estoy_vs_esta, me_llamo_es, tengo_not_tango, soy_de_origin. "
                    "Pass last_examples: [\"yo está en…\"]."
                ),
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "last_examples": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "resolved": {"type": "boolean"},
                    },
                },
            },
            "skills": {
                "type": "object",
                "description": (
                    "Can-do ids (IP-01…IP-08, IT-01, PR-01) → "
                    "{status, confidence}. status: unknown|emerging|fragile|known|blocked. "
                    "Never solid_uses."
                ),
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": list(STATUSES),
                        },
                        "confidence": {"type": "number"},
                    },
                },
            },
            "grammar": {
                "type": "object",
                "description": "Supporting forms → {status, confidence, evidence?}",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "confidence": {"type": "number"},
                        "evidence": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "lexicon": {
                "type": "object",
                "description": (
                    "Lemma → {status, confidence} for words they used. "
                    "Never solid_uses."
                ),
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                },
            },
            "receptive": {
                "type": "object",
                "properties": {
                    "needs_english_scaffold": {"type": "boolean"},
                },
            },
            "affect": {
                "type": "object",
                "properties": {
                    "last_meta": {"type": "string"},
                    "energy": {"type": "string"},
                },
            },
            "coverage": {
                "type": "object",
                "properties": {
                    "touched": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            "next_best": {
                "type": "object",
                "properties": {
                    "can_do": {"type": ["string", "null"]},
                    "activity": {"type": "string"},
                    "stretch": {"type": "string"},
                    "avoid": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        },
    },
}


def extract_sheet_delta(reply: str) -> tuple[str, dict | None]:
    """Strip optional <sheet_delta>{...}</sheet_delta> from tutor reply."""
    m = _SHEET_DELTA_RE.search(reply or "")
    if not m:
        return (reply or "").strip(), None
    visible = (reply[: m.start()] + reply[m.end():]).strip()
    try:
        delta = json.loads(m.group(1))
    except json.JSONDecodeError:
        return visible, None
    return visible, delta if isinstance(delta, dict) else None


def recompute_next_best(sheet: dict, *, preferred_name: str | None = None) -> dict:
    """Pick next can-do + CLT/TBLT activity from sheet (docs/spanish-can-dos-novice.md §7).

    `preferred_name` comes from the learner profile; legacy sheets that still
    carry an identity block are read as fallback.
    """
    s = copy.deepcopy(sheet)
    known_name = (
        preferred_name or (s.get("identity") or {}).get("preferred_name") or ""
    ).strip()
    skills = s.get("skills") or {}
    grammar = s.get("grammar") or {}
    affect = s.get("affect") or {}
    coverage = s.get("coverage") or {}
    never = list(coverage.get("never_touched") or [])

    def conf(block: dict, key: str) -> float:
        return float((block.get(key) or {}).get("confidence") or 0.0)

    def status(block: dict, key: str) -> str:
        return (block.get(key) or {}).get("status") or "unknown"

    def is_known(cid: str) -> bool:
        return status(skills, cid) == "known" or conf(skills, cid) >= 0.8

    evidence_mass = sum(conf(skills, k) for k in skills) + sum(
        conf(grammar, k) for k in grammar
    )

    can_do = None
    avoid = "worksheet_drills_and_form_only_units"
    reason = "default exploratory talk (CLT)"

    if evidence_mass < 0.35:
        can_do = None
        stretch_key = "open_chat_and_notice"
        avoid = "drill_greetings_if_already_easy"
        reason = "little evidence — talk first; notice can-dos (CLT/CI)"
    else:
        # Prefer weakest high-priority interpersonal can-do that is not known
        candidates = []
        for cid, meta in CAN_DOS.items():
            if meta["mode"] != "interpersonal":
                continue
            if is_known(cid):
                continue
            # Don't push IP-02 formal if informal greet still unknown
            if cid == "IP-02" and conf(skills, "IP-01") < 0.35:
                continue
            # Name exchange is blocked once we know their name (the open guard
            # forbids «¿Cómo te llamas?») — pinning IP-03 as next_best made the
            # agenda unadvanceable. Skip it and take the next weakest can-do.
            if cid == "IP-03" and known_name and conf(skills, "IP-03") >= 0.4:
                continue
            # Don't grind IP-01 after any real greeting evidence — open other can-dos
            if cid == "IP-01" and (
                conf(skills, "IP-01") >= 0.25
                or status(skills, "IP-01") in ("emerging", "fragile", "known")
            ):
                continue
            # Same for leave-taking once shown
            if cid == "IP-05" and conf(skills, "IP-05") >= 0.35:
                continue
            pri = {"high": 0, "medium": 1, "low": 2}.get(meta.get("priority"), 3)
            candidates.append((pri, conf(skills, cid), cid))
        candidates.sort()
        if candidates:
            can_do = candidates[0][2]
            stretch_key = can_do
            reason = (
                f"weakest open interpersonal can-do {can_do}: "
                f"{CAN_DOS[can_do]['statement']}"
            )
            if can_do in ("IP-01", "IP-02"):
                avoid = "endless_greeting_variants_and_spelling_loops"
            else:
                avoid = "return_to_greetings_when_already_emerging"
        elif "food" in never or "preferences" in never:
            can_do = "IP-06"
            stretch_key = "IP-06"
            avoid = "unit1_greeting_trap"
            reason = "basics covered; open preferences/new domain (palette)"
        else:
            can_do = "IP-08"
            stretch_key = "IP-08"
            avoid = "form_drills"
            reason = "interpersonal can-dos mostly known — freer task talk"

        # Form fragility can color activity but not replace can-do goal
        if can_do == "IP-04" and conf(grammar, "present_estar_person") < 0.45:
            avoid = "spelling_focus_on_estoy"
            reason += " | recast estar person in talk (focus on form)"
        if can_do == "IP-02" and conf(grammar, "register_tu_usted") < 0.45:
            avoid = "three_retries_on_usted_spelling"
            reason += " | one formal exchange, then move on"

    act = STRETCH_ACTIVITIES.get(stretch_key) or STRETCH_ACTIVITIES["open_chat_and_notice"]
    # Only when energy was set *this session* (session open clears stale labels)
    if is_session_scoped_energy(affect.get("energy")):
        avoid = "dragging_out_session_when_time_limited"
        if "limited time" not in reason.lower():
            reason = f"limited time — keep it short | {reason}"

    # Recurring construction errors outrank pure can-do stretch while hot *or*
    # still weaning (need healthy resolved_streak before dropping form focus).
    form_focus = None
    error_pattern = None
    active = active_error_patterns(s)
    if active:
        top = active[0]
        error_pattern = top["id"]
        form_focus = top.get("form_id")
        streak = int(top.get("resolved_streak") or 0)
        # Prefer a can-do that the pattern supports, if open
        for cid in top.get("can_dos") or []:
            if cid in CAN_DOS and not is_known(cid):
                can_do = cid
                stretch_key = cid
                act = STRETCH_ACTIVITIES.get(cid) or act
                break
        # Even if can-do is already "known", keep weaving the form in talk
        if form_focus and can_do is None:
            for cid in top.get("can_dos") or []:
                if cid in CAN_DOS:
                    can_do = cid
                    stretch_key = cid
                    act = STRETCH_ACTIVITIES.get(cid) or act
                    break
        weaning = (
            int(top.get("count") or 0) < ERROR_PATTERN_PRIORITY_THRESHOLD
            and streak < ERROR_PATTERN_HEALTHY_STREAK
        )
        if weaning:
            reason = (
                f"form focus (weaning ×{top['count']}, clean streak {streak}/"
                f"{ERROR_PATTERN_HEALTHY_STREAK}): {top['label']} — "
                f"keep weaving correct form | {reason}"
            )
        else:
            reason = (
                f"recurring error ×{top['count']}: {top['label']} "
                f"(e.g. {', '.join(top.get('last_examples') or [])}) — "
                f"recast/weave before new stretch | {reason}"
            )
        avoid = "ignore_repeated_form_error_and_only_chat"

    # Headline: when form work is active, don't title the stretch as a different
    # can-do (e.g. IP-03 names) — that made "Focus now" contradict the chat.
    if form_focus and error_pattern:
        ep_label = (ERROR_PATTERN_CATALOG.get(error_pattern) or {}).get("label") or error_pattern
        statement = f"Form in talk: {ep_label}"
        activity = "weave_form_in_conversation"
        stretch = activity
        related_can_do = can_do if can_do is not None else act.get("can_do")
    else:
        statement = (
            CAN_DOS[can_do]["statement"]
            if can_do in CAN_DOS
            else act.get("description")
        )
        activity = act.get("activity") or stretch_key
        stretch = act.get("activity") or stretch_key
        related_can_do = can_do if can_do is not None else act.get("can_do")

    s["next_best"] = {
        "can_do": related_can_do,
        "stretch": stretch,
        "activity": activity,
        "statement": statement,
        "avoid": avoid,
        "reason": reason,
        "method": "CLT/TBLT + CI + focus_on_form",
        "form_focus": form_focus,
        "error_pattern": error_pattern,
        "primary": "form" if (form_focus and error_pattern) else "can_do",
        "teach_hint": (
            (ERROR_PATTERN_CATALOG.get(error_pattern) or {}).get("teach_hint")
            if error_pattern else None
        ),
    }
    return s


def summarize_sheet_change_events(
    before: dict, after: dict
) -> list[tuple]:
    """Typed (kind, key, payload) triples for the console change notes.

    Phase 3 batch 2 leaf push-down: this is the native emitter —
    ``summarize_sheet_changes`` (the string surface) is its render-table
    projection, and conv_session emits TurnEvents from these triples.
    """
    events: list[tuple] = []
    # Personal-data capture disabled 2026-07-28: never note a captured name.
    bumped = []
    for k, v in (after.get("skills") or {}).items():
        prev = (before.get("skills") or {}).get(k) or {}
        pc = round(float(prev.get("confidence") or 0), 2)
        ac = round(float(v.get("confidence") or 0), 2)
        if ac > pc + 0.05 or (
            prev.get("status") != v.get("status") and v.get("status") != "unknown"
        ):
            bumped.append(f"{k}:{pc:.2f}→{ac:.2f}/{v.get('status')}")
    if bumped:
        events.append((_EVK.SHEET_CAN_DOS, ", ".join(bumped[:6]), {}))
    if json.dumps(before.get("next_best"), sort_keys=True) != json.dumps(
            after.get("next_best"), sort_keys=True):
        nb = after.get("next_best") or {}
        events.append((
            _EVK.SHEET_NEXT_BEST,
            f"{nb.get('can_do') or '—'} / {nb.get('activity')}",
            {},
        ))
    rec = after.get("receptive") or {}
    events.append((
        _EVK.SHEET_SCAFFOLD,
        "ES-forward+EN-rescue"
        if rec.get("needs_english_scaffold", True)
        else "mostly_ES",
        {},
    ))
    return events


def summarize_sheet_changes(before: dict, after: dict) -> list[str]:
    """Short human notes for the console (render of the typed triples)."""
    return [
        _render_note(kind, key=key, payload=payload)
        for kind, key, payload in summarize_sheet_change_events(before, after)
    ]


def normalize_sheet(sheet: dict) -> dict:
    """Ensure required keys/can-dos exist after an AI rewrite."""
    base = default_sheet()
    if not isinstance(sheet, dict):
        return base
    merged = _deep_merge(base, sheet)
    merged["skills"] = migrate_skills(merged.get("skills") or {})
    for cid, entry in default_skills_block().items():
        merged["skills"].setdefault(cid, entry)
        pre_entry = dict(merged["skills"][cid])  # machine B snapshot
        # re-stamp can-do metadata so AI can't drop statements
        meta = CAN_DOS[cid]
        merged["skills"][cid]["mode"] = meta["mode"]
        merged["skills"][cid]["band"] = meta["band"]
        merged["skills"][cid]["statement"] = meta["statement"]
        if merged["skills"][cid].get("status") not in STATUSES:
            merged["skills"][cid]["status"] = "unknown"
        try:
            c = float(merged["skills"][cid].get("confidence") or 0)
            merged["skills"][cid]["confidence"] = max(0.0, min(1.0, c))
        except (TypeError, ValueError):
            merged["skills"][cid]["confidence"] = 0.0
        # Machine B (via="normalize"): band self-loops only — an invalid
        # status already IS band unknown, so the coercion never moves it.
        ability_transition(
            pre_entry, merged["skills"][cid], via="normalize",
            evidence={"section": "skills", "key": cid},
        )
    for fid, entry in default_grammar_block().items():
        g = merged.setdefault("grammar", {})
        g.setdefault(fid, entry)
        pre_entry = dict(g[fid]) if isinstance(g[fid], dict) else {}
        if g[fid].get("status") not in STATUSES:
            g[fid]["status"] = "unknown"
        ability_transition(
            pre_entry, g[fid], via="normalize",
            evidence={"section": "grammar", "key": fid},
        )
    merged["version"] = max(int(merged.get("version") or 2), 2)
    merged["framework"] = base["framework"]
    # Defense in depth (personal-data capture disabled 2026-07-28): an AI
    # rewrite may not (re)introduce identity data — strip on normalize.
    ident = merged.setdefault("identity", {})
    ident["preferred_name"] = None
    ident["engagement_notes"] = ""
    merged = normalize_schedule_fields(merged)
    merged["updated_at"] = today()
    # Prefer AI next_best if well-formed; else recompute
    nb = merged.get("next_best") or {}
    if not nb.get("activity") and not nb.get("stretch"):
        merged = recompute_next_best(merged)
    else:
        # fill missing fields lightly
        if not nb.get("method"):
            nb["method"] = "CLT/TBLT + CI + focus_on_form"
        if nb.get("can_do") in CAN_DOS and not nb.get("statement"):
            nb["statement"] = CAN_DOS[nb["can_do"]]["statement"]
        merged["next_best"] = nb
    return merged


def process_turn(
    sheet: dict,
    learner: str,
    tutor_reply: str,
    *,
    tool_delta: dict | None = None,
    revised_sheet: dict | None = None,
    profile: dict | None = None,
    event_sink: list | None = None,
    session_id: str = "",
    grade_log_path: str | None = None,
) -> tuple[dict, str, list[str]]:
    """Apply post-turn sheet maintenance (tool-only ability, 2026-07-31).

    Priority:
      1. `tool_delta` — teaching AI called update_character_sheet (primary).
         Ability claims require a non-trivial ``reason``/``why``; otherwise
         the **entire** tool_delta is rejected and the sheet holds.
      2. `revised_sheet` — legacy full AI rewrite (no regex observer).
      3. No tool — ability frozen; optional inline <sheet_delta> only with why.

    Scaffold (``receptive.needs_english_scaffold``) remains code-owned via
    ``update_scaffold_flag`` on every path (not ability grading).

    No regex hard-observer ability writes. ``profile`` is IGNORED (ability-only
    sheet; personal-data capture disabled 2026-07-28).
    Returns (sheet, visible_tutor_text, change_notes).

    Phase 3 batch 2 leaf push-down: the change notes are minted as typed
    (kind, key, payload) triples; the returned strings are their render-table
    projection. When ``event_sink`` (a list) is given, the deduped triples are
    appended to it 1:1 with the returned notes.
    """
    visible, inline_delta = extract_sheet_delta(tutor_reply)
    before = copy.deepcopy(sheet)

    def _stamp_can_dos(s: dict) -> None:
        for cid, entry in default_skills_block().items():
            sk = s.setdefault("skills", {})
            sk.setdefault(cid, entry)
            if cid in CAN_DOS:
                sk[cid]["mode"] = CAN_DOS[cid]["mode"]
                sk[cid]["band"] = CAN_DOS[cid]["band"]
                sk[cid]["statement"] = CAN_DOS[cid]["statement"]

    if tool_delta:
        td = sanitize_tool_delta(tool_delta)
        if delta_claims_ability(td) and not grade_why_ok(td):
            s = copy.deepcopy(sheet)
            _stamp_can_dos(s)
            s = _preserve_identity(sheet, s)
            events: list[tuple] = [
                (_EVK.SHEET_WHY, "rejected:need_reason", {}),
            ]
            s = recompute_next_best(s, preferred_name=None)
        else:
            s = apply_delta(sheet, td)
            _stamp_can_dos(s)
            s = _preserve_identity(sheet, s)
            events = [(_EVK.SHEET_TOOL_UPDATE, "", {})]
            reason = (
                td.get("reason") or td.get("why") or td.get("notes") or ""
            )
            if isinstance(reason, str) and reason.strip():
                # Full why for grade feed (cap for note render only).
                events.append(
                    (_EVK.SHEET_WHY, reason.strip()[:200], {})  # truncation-ok: note render cap
                )
            evidence = td.get("evidence")
            if isinstance(evidence, str) and evidence.strip():
                events.append(
                    # truncation-ok: note render cap
                    (_EVK.SHEET_WHY, f"evidence:{evidence.strip()[:80]}", {})
                )
            staged = copy.deepcopy(s)
            s = _cap_turn_confidence(before, staged, s)
            # Learner-visible grade feed (Phase 3): one log row per ability field
            # that actually moved under this tool call.
            try:
                from .grade_log import (
                    ability_grade_diffs,
                    record_grades_from_diff,
                )

                why_txt = (
                    (td.get("reason") or td.get("why") or td.get("notes") or "")
                    if isinstance(td, dict) else ""
                )
                ev_txt = (
                    td.get("evidence") if isinstance(td, dict) else ""
                ) or ""
                if isinstance(why_txt, str) and why_txt.strip():
                    record_grades_from_diff(
                        before,
                        s,
                        why=why_txt.strip(),
                        evidence=str(ev_txt).strip() if ev_txt else "",
                        session_id=session_id or "",
                        ledger_path=grade_log_path,
                    )
                elif ability_grade_diffs(before, s):
                    # Ability moved but the delta carried no reason — the
                    # grade feed records nothing. Say so as a typed note
                    # instead of skipping silently (full-code-audit S5.2).
                    events.append(
                        (_EVK.SHEET_WHY, "grade_unrecorded:no_reason", {})
                    )
            except Exception as e:
                # Grade feed must never break the teaching turn — but a
                # broken side-channel is VISIBLE, never silent (no-hide,
                # full-code-audit S5.2, 2026-08-03).
                import sys as _sys

                print(
                    f"[no-hide] grade_log write failed (teaching turn "
                    f"continues; grade feed row LOST): "
                    f"{type(e).__name__}: {e}", file=_sys.stderr, flush=True,
                )
    elif revised_sheet is not None:
        s = normalize_sheet(revised_sheet)
        s = _preserve_identity(sheet, s)
        events = [(_EVK.SHEET_AI_UPDATE, "", {})]
        staged = copy.deepcopy(s)
        s = _cap_turn_confidence(before, staged, s)
    else:
        # No tool: ability frozen. Inline delta only if it has why for ability.
        s = copy.deepcopy(sheet)
        events = [(_EVK.SHEET_RULES_BACKUP, "", {})]
        if inline_delta:
            idelta = sanitize_tool_delta(inline_delta)
            if delta_claims_ability(idelta) and not grade_why_ok(idelta):
                events.append((_EVK.SHEET_WHY, "rejected:need_reason", {}))
            elif idelta:
                s = apply_delta(s, idelta)
                events.append((_EVK.SHEET_INLINE_DELTA, "", {}))
                s = _cap_turn_confidence(before, before, s)
        s = recompute_next_best(s, preferred_name=None)
        s = _preserve_identity(sheet, s)

    # Scaffold is not ability: keep code-owned English-scaffold flag from
    # learner text (tool may also set receptive explicitly earlier).
    s = update_scaffold_flag(s, learner)

    # Surface hot error patterns in console notes
    for ep in active_error_patterns(s):
        events.append(
            (_EVK.SHEET_ERROR_PATTERN, ep["id"], {"count": ep["count"]})
        )

    events.extend(summarize_sheet_change_events(before, s))
    # de-dupe while preserving order (historical rule: on the rendered string)
    seen = set()
    out_notes: list[str] = []
    for kind, key, payload in events:
        n = _render_note(kind, key=key, payload=payload)
        if n not in seen:
            seen.add(n)
            out_notes.append(n)
            if event_sink is not None:
                event_sink.append((kind, key, payload))
    return s, visible, out_notes


SHEET_UPDATE_SYSTEM = """You maintain a learner CHARACTER SHEET for a Spanish tutor.

The sheet is CONTEXT about what the student can do — not a gradebook for its own sake.
After each exchange, revise it so the tutor can choose appropriate Spanish and
what to weave in next (CLT/TBLT: conversation first; can-dos from ACTFL-style
Novice list IP-01…IP-08, IT-01, PR-01).

Rules for updates:
- Base changes on EVIDENCE in this turn (what they said / understood).
- Do not invent mastery. Prefer conservative confidence.
- Surface typos/accents ≠ weak grammar. Conceptual errors (wrong person/register) matter more.
- If they used English to ask "what does X mean?", keep needs_english_scaffold true.
- Update next_best: one stretch can_do + activity + avoid + reason (plain language).
- Preserve identity fields unless you have new evidence (e.g. name).
- skills keys must stay the can-do ids already on the sheet.
- Return ONLY a full JSON object for the entire sheet (no markdown fences, no commentary).
"""


def build_sheet_update_messages(
    sheet: dict, learner: str, tutor_visible: str
) -> list[dict]:
    return [
        {
            "role": "user",
            "content": (
                "CURRENT CHARACTER SHEET:\n"
                + json.dumps(sheet, ensure_ascii=False, indent=2)
                + "\n\nLATEST LEARNER MESSAGE:\n"
                + (learner or "(session open / no learner text)")
                + "\n\nTUTOR REPLY (what the student just saw):\n"
                + (tutor_visible or "")
                + "\n\nTask: Given how this exchange went, return the UPDATED "
                "full character sheet JSON. Keep the same overall structure."
            ),
        }
    ]


def parse_sheet_json(text: str) -> dict | None:
    """Parse a model sheet rewrite from raw text."""
    t = (text or "").strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) >= 2:
            t = parts[1]
            if t.lstrip().lower().startswith("json"):
                t = t.lstrip()[4:].lstrip()
    try:
        data = json.loads(t)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    start = t.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(t)):
        if t[i] == "{":
            depth += 1
        elif t[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    data = json.loads(t[start : i + 1])
                    return data if isinstance(data, dict) else None
                except json.JSONDecodeError:
                    return None
    return None


def update_scaffold_flag(sheet: dict, learner: str) -> dict:
    """Keep English scaffold on until learner shows sustained Spanish readiness.

    Signals for reducing scaffold (all soft): mostly Spanish turns, few English
    meta-questions, emerging confidence on core can-dos.
    """
    s = copy.deepcopy(sheet)
    rec = s.setdefault("receptive", {})
    text = (learner or "").strip()
    if not text:
        rec.setdefault("needs_english_scaffold", True)
        rec.setdefault("spanish_turn_streak", 0)
        return s

    # Rough: fraction of letters that look Spanish content words vs English
    f = fold(text)
    en_meta = bool(re.search(
        r"\b(what|why|how|does|mean|would|another|from|the|united|states|"
        r"captain|comes|this|that|should|think)\b",
        text.lower(),
    ))
    has_es = bool(re.search(
        r"\b(hola|estoy|est[aá]s|soy|me|llamo|mucho|gusto|en|pero|aqui|"
        r"buenas|como|se|llama|gracias|bien)\b",
        f,
    ))
    streak = int(rec.get("spanish_turn_streak") or 0)
    if has_es and not en_meta and len(text.split()) <= 12:
        streak += 1
    elif en_meta:
        streak = 0
    else:
        streak = max(0, streak - 1)
    rec["spanish_turn_streak"] = streak

    # Default ON. Only turn off after several short Spanish-forward turns
    # and some can-do evidence — never on turn 1–2 of a session alone.
    conf_core = sum(
        float((s.get("skills") or {}).get(k, {}).get("confidence") or 0)
        for k in ("IP-01", "IP-03", "IP-04")
    )
    if streak >= 4 and conf_core >= 1.2 and not en_meta:
        rec["needs_english_scaffold"] = False
    else:
        rec["needs_english_scaffold"] = True
    return s
