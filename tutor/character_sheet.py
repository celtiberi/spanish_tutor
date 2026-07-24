"""Student character sheet — living learner model for conversational tutoring.

See docs/conversational-spanish-and-learner-model.md.
"""

from __future__ import annotations

import copy
import datetime
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from .can_dos import (
    CAN_DOS,
    STRETCH_ACTIVITIES,
    default_grammar_block,
    default_skills_block,
    migrate_skills,
)

STATUSES = ("unknown", "emerging", "fragile", "known", "blocked")

# Harness honesty: models over-rate "known" after one lucky turn.
MAX_CONF_UP_PER_TURN = 0.25
MAX_CONF_DOWN_PER_TURN = 0.35
KNOWN_MIN_CONF = 0.80
KNOWN_MIN_SOLID_USES = 2

DEFAULT_COVERAGE = {
    "touched": [],
    "never_touched": [
        "greetings_time_of_day", "register_tu_usted", "introduce_self",
        "ser_basic", "estar_basic", "food", "numbers", "family", "leave_taking",
        "preferences", "roleplay_tasks",
    ],
}

# Grammar form id → coverage topic(s)
_GRAMMAR_COVERAGE = {
    "present_estar_person": ["estar_basic"],
    "register_tu_usted": ["register_tu_usted"],
    "present_ser": ["ser_basic"],
    "numbers_0_20": ["numbers"],
    "tener_age_possession": ["family"],
    "present_regular_ar_er_ir": ["preferences"],
}

_SHEET_DELTA_RE = re.compile(
    r"<sheet_delta>\s*(\{.*?\})\s*</sheet_delta>", re.S)
_SURFACE_NOISE = re.compile(r"[\u0300-\u036f]|[¿¡\?\.!,;:\"']+")

# Rough token → lexicon lemma + can-do id
_LEXICON_PATTERNS = [
    (r"\bhola\b", "hola", "IP-01"),
    (r"\bbuenos\s+d[ií]as\b", "buenos días", "IP-01"),
    (r"\bbuenas\s+tardes\b", "buenas tardes", "IP-01"),
    (r"\bbuenas\s+noches\b", "buenas noches", "IP-01"),
    (r"\bme\s+llamo\b", "me llamo", "IP-03"),
    (r"\bmucho\s+gusto\b", "mucho gusto", "IP-03"),
    (r"\bc[oó]mo\s+te\s+llamas\b", "cómo te llamas", "IP-03"),
    (r"\bestoy\b", "estoy", "IP-04"),
    (r"\bgracias\b", "gracias", "IP-01"),
    (r"\badi[oó]s\b|\bhasta\s+luego\b|\bhasta\s+mañana\b", "leave-taking", "IP-05"),
    (r"\busted\b", "usted", "IP-02"),
    (r"\bme\s+gusta\b|\bprefiero\b", "preference", "IP-06"),
]


def today() -> str:
    return datetime.date.today().isoformat()


def now_iso() -> str:
    """Local wall-clock timestamp for last_seen / context (date + time)."""
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


# Closed catalog of high-value recurring constructions (not full Spanish grammar).
# Detected from learner text; count≥2 → teach/recast priority.
ERROR_PATTERN_CATALOG: dict[str, dict] = {
    "estar_yo_estoy_vs_esta": {
        "label": "yo + estoy (not está) for self",
        "form_id": "present_estar_person",
        "can_dos": ["IP-04", "IP-07"],
        "teach_hint": (
            "Learner confuses *estoy* (I am) with *está* (he/she/it/usted is). "
            "Recast *Yo está…* → *Estoy…* / *Yo estoy…*; weave first-person location "
            "and wellbeing with *estoy*."
        ),
        # (regex, example_note) — any match hits the pattern
        "detect": [
            (r"\byo\s+est[aá]\b", "yo está"),
            (r"\best[aá]\s+bien\b(?!.*\bestoy\b)", "está bien for self?"),
            (r"\best[aá]\s+en\s+(mi|el|la|rio|río)\b", "está en … for self location?"),
        ],
        # Success signal that this pattern is improving
        "resolve": [
            r"\byo\s+estoy\b",
            r"\bestoy\s+(bien|en|aquí|aca|acá)\b",
        ],
    },
    "me_llamo_es": {
        "label": "me llamo (not me llama es)",
        "form_id": None,
        "can_dos": ["IP-03"],
        "teach_hint": "Recast *Me llama es X* / *Me llamo es X* → *Me llamo X*.",
        "detect": [
            (r"\bme\s+llam[oa]\s+es\b", "me llamo/llama es"),
            (r"\bme\s+llama\s+[A-Za-zÁÉÍÓÚáéíóúñÑ]{2,}\b", "me llama Name"),
        ],
        "resolve": [r"\bme\s+llamo\s+[A-Za-zÁÉÍÓÚáéíóúñÑ]{2,}\b"],
    },
    "tengo_not_tango": {
        "label": "tengo (not tango)",
        "form_id": "tener_age_possession",
        "can_dos": ["IP-07"],
        "teach_hint": "Recast *tango* → *tengo* (I have).",
        "detect": [(r"\btango\b", "tango→tengo")],
        "resolve": [r"\btengo\b"],
    },
    "soy_de_origin": {
        "label": "soy de + place",
        "form_id": "present_ser",
        "can_dos": ["IP-07"],
        "teach_hint": "Origin needs *de*: *Soy de Estados Unidos* (not *Soy Estados Unidos*).",
        "detect": [
            (r"\bsoy\s+(estados|ee\.?uu\.?|usa|guatemala|mexico|méxico)\b",
             "soy Place without de"),
        ],
        "resolve": [r"\bsoy\s+de\b"],
    },
}

ERROR_PATTERN_PRIORITY_THRESHOLD = 2  # count at/above → force teaching focus

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
}


def normalize_error_pattern_id(pattern_id: str) -> str:
    """Map free-form / alias ids onto ERROR_PATTERN_CATALOG keys."""
    pid = (pattern_id or "").strip()
    if not pid:
        return pid
    if pid in ERROR_PATTERN_CATALOG:
        return pid
    key = pid.lower().replace(" ", "_").replace("-", "_")
    key = key.replace("á", "a").replace("é", "e").replace("í", "i")
    key = key.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
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

    Call at the start of each new chat session. Durable skills/identity stay.
    """
    s = copy.deepcopy(sheet)
    aff = s.setdefault("affect", {})
    if is_session_scoped_energy(aff.get("energy")):
        aff["energy"] = "unknown"
    meta = aff.get("last_meta")
    if meta and _SESSION_META_TIME.search(str(meta)):
        aff["last_meta"] = None
    # If next_best reason still talks about limited time from a past session, recompute
    nb = s.get("next_best") or {}
    reason = str(nb.get("reason") or "").lower()
    avoid = str(nb.get("avoid") or "").lower()
    if "limited time" in reason or "time_limited" in avoid or "few minute" in reason:
        s = recompute_next_best(s)
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
            "boredom_risk": "unknown",
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
    except (json.JSONDecodeError, OSError):
        return default_sheet()
    base = default_sheet()
    merged = _deep_merge(base, data)
    # Migrate legacy skill keys → can-do ids
    merged["skills"] = migrate_skills(data.get("skills") or merged.get("skills") or {})
    # Ensure all can-dos / forms exist
    for cid, entry in default_skills_block().items():
        merged["skills"].setdefault(cid, entry)
    for fid, entry in default_grammar_block().items():
        merged.setdefault("grammar", {}).setdefault(fid, entry)
    merged.setdefault("error_patterns", {})
    if not isinstance(merged.get("error_patterns"), dict):
        merged["error_patterns"] = {}
    merged["version"] = max(int(merged.get("version") or 1), 2)
    merged["framework"] = base["framework"]
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


def fold(s: str) -> str:
    s = (s or "").lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = _SURFACE_NOISE.sub("", s)
    return re.sub(r"\s+", " ", s)


def format_sheet_for_prompt(sheet: dict, *, max_lex: int = 40) -> str:
    """Compact JSON-ish summary for the tutor system context.

    Always includes wall-clock `now` so last_seen dates are interpretable.
    """
    slim = {
        "now": now_iso(),  # current local date+time for last_seen comparisons
        "identity": sheet.get("identity"),
        "skills": sheet.get("skills"),
        "grammar": {
            k: {kk: vv for kk, vv in v.items() if kk != "evidence"}
            for k, v in (sheet.get("grammar") or {}).items()
        },
        "error_patterns": sheet.get("error_patterns") or {},
        "active_error_focus": active_error_patterns(sheet),
        "affect": sheet.get("affect"),
        "coverage": sheet.get("coverage"),
        "next_best": sheet.get("next_best"),
        "lexicon_sample": dict(
            list((sheet.get("lexicon") or {}).items())[:max_lex]
        ),
    }
    return json.dumps(slim, ensure_ascii=False, indent=2)


def format_sheet_human(sheet: dict) -> str:
    lines = ["# Student character sheet", ""]
    ident = sheet.get("identity") or {}
    lines.append(f"**Name:** {ident.get('preferred_name') or '(unknown)'}")
    lines.append(f"**Goals:** {', '.join(ident.get('goals') or []) or '(none)'}")
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
    lines.append(f"- boredom_risk: {aff.get('boredom_risk')}")
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


def _bump_status(entry: dict, *, success: bool, amount: float = 0.15) -> dict:
    """Heuristic status bump with per-turn caps and known-gate."""
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
    elif conf >= 0.55:
        e["status"] = "emerging" if success else "fragile"
    elif conf >= 0.25:
        e["status"] = "fragile" if not success else "emerging"
    else:
        e["status"] = "emerging" if success else "unknown"
    # Never label known without enough solid uses
    if e["status"] == "known" and uses < KNOWN_MIN_SOLID_USES:
        e["status"] = "emerging"
        e["confidence"] = min(float(e["confidence"]), 0.75)
    return e


def _clamp_skill_entry(prev: dict, incoming: dict) -> dict:
    """Merge tool/model skill or grammar entry with honesty clamps."""
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

    uses = int(prev.get("solid_uses") or 0)
    rose = new_c > prev_c + 0.02
    status_in = incoming.get("status")
    promoted = (
        status_in in ("emerging", "fragile", "known")
        and (prev.get("status") or "unknown") in ("unknown", None)
    )
    # At most +1 solid use per merge
    if rose or promoted or (
        status_in == "known" and prev.get("status") != "known"
    ):
        uses = uses + 1
    if "solid_uses" in incoming:
        try:
            uses = max(uses, int(incoming["solid_uses"]))
        except (TypeError, ValueError):
            pass
    merged["solid_uses"] = uses

    status = merged.get("status") if merged.get("status") in STATUSES else (
        prev.get("status") or "unknown"
    )
    # Gate known: need prior known OR (enough uses + conf)
    if status == "known":
        if prev.get("status") == "known" and new_c >= KNOWN_MIN_CONF:
            pass
        elif uses >= KNOWN_MIN_SOLID_USES and new_c >= KNOWN_MIN_CONF:
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
    return merged


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
    """Never drop preferred_name once known."""
    s = after
    prev = (before.get("identity") or {}).get("preferred_name")
    cur = (s.get("identity") or {}).get("preferred_name")
    if prev and (not cur or str(cur).strip().lower() in ("null", "none", "")):
        s.setdefault("identity", {})["preferred_name"] = prev
    return s


def _note_evidence(grammar_entry: dict, note: str, *, limit: int = 5) -> None:
    ev = list(grammar_entry.get("evidence") or [])
    if note and note not in ev:
        ev.append(note)
    grammar_entry["evidence"] = ev[-limit:]


def detect_error_pattern_hits(learner: str) -> list[tuple[str, str]]:
    """Return [(pattern_id, example_snippet), ...] for known error constructions."""
    text = learner or ""
    if not text.strip() or text.startswith("🎤") or text.startswith("⏳"):
        return []
    f = fold(text)
    hits: list[tuple[str, str]] = []
    for pid, cat in ERROR_PATTERN_CATALOG.items():
        for pat, note in cat.get("detect") or []:
            if re.search(pat, f, re.I) or re.search(pat, text, re.I):
                # Prefer a short raw span as example
                m = re.search(pat, text, re.I) or re.search(pat, f, re.I)
                snippet = (m.group(0) if m else note)[:80]
                hits.append((pid, snippet))
                break
    return hits


def detect_error_pattern_resolves(learner: str) -> list[str]:
    """Pattern ids that look correctly used this turn."""
    text = learner or ""
    f = fold(text)
    out: list[str] = []
    for pid, cat in ERROR_PATTERN_CATALOG.items():
        for pat in cat.get("resolve") or []:
            if re.search(pat, f, re.I) or re.search(pat, text, re.I):
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
    })
    # stamp catalog fields
    ent["label"] = cat.get("label") or ent.get("label") or pattern_id
    ent["form_id"] = cat.get("form_id")
    ent["can_dos"] = list(cat.get("can_dos") or ent.get("can_dos") or [])
    ent["teach_hint"] = cat.get("teach_hint") or ent.get("teach_hint") or ""

    if resolved:
        ent["resolved_streak"] = int(ent.get("resolved_streak") or 0) + 1
        # After two clean uses, ease priority/count slightly
        if ent["resolved_streak"] >= 2 and int(ent.get("count") or 0) > 0:
            ent["count"] = max(0, int(ent["count"]) - 1)
            ent["resolved_streak"] = 0
        ent["last_seen"] = now_iso()
    else:
        ent["count"] = int(ent.get("count") or 0) + 1
        ent["resolved_streak"] = 0
        ent["last_seen"] = now_iso()
        ex = list(ent.get("last_examples") or [])
        if example and example not in ex:
            ex.append(example[:100])
        ent["last_examples"] = ex[-5:]

    c = int(ent.get("count") or 0)
    if c >= 4:
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
    for pid, snippet in detect_error_pattern_hits(learner):
        note_error_pattern(s, pid, snippet, resolved=False)
    for pid in detect_error_pattern_resolves(learner):
        # Only count resolve if pattern already known / was an issue
        if pid in (s.get("error_patterns") or {}):
            note_error_pattern(s, pid, "correct use", resolved=True)
    return s


def active_error_patterns(
    sheet: dict,
    *,
    min_count: int = ERROR_PATTERN_PRIORITY_THRESHOLD,
) -> list[dict]:
    """Patterns that should drive teaching (count ≥ min_count, not fully cleared)."""
    out: list[dict] = []
    for pid, ent in (sheet.get("error_patterns") or {}).items():
        if not isinstance(ent, dict):
            continue
        c = int(ent.get("count") or 0)
        if c < min_count:
            continue
        cat = ERROR_PATTERN_CATALOG.get(pid) or {}
        out.append({
            "id": pid,
            "count": c,
            "priority": ent.get("priority") or "high",
            "label": ent.get("label") or cat.get("label") or pid,
            "form_id": ent.get("form_id") or cat.get("form_id"),
            "can_dos": ent.get("can_dos") or cat.get("can_dos") or [],
            "teach_hint": ent.get("teach_hint") or cat.get("teach_hint") or "",
            "last_examples": list(ent.get("last_examples") or [])[-3:],
            "last_seen": ent.get("last_seen"),
        })
    out.sort(key=lambda x: (-x["count"], x["id"]))
    return out


def apply_rule_updates(sheet: dict, learner: str, tutor_visible: str = "") -> dict:
    """Heuristic updates from one learner turn (no extra API call)."""
    s = copy.deepcopy(sheet)
    text = learner or ""
    f = fold(text)
    low = text.lower()

    # Affect: boredom vs limited time (not the same)
    aff = s.setdefault("affect", {})
    if re.search(
        r"\b(what are we|why are we|boring|stuck|better way|this again|"
        r"same thing|too hard|hate this)\b",
        low,
    ):
        aff["last_meta"] = text[:200]
        aff["boredom_risk"] = "high"
        aff["energy"] = "frustrated_or_bored"
    elif re.search(
        r"\b(little time|only have|don'?t have (much|a lot of) time|"
        r"gotta go|have to go|in a hurry|in a rush|quick session|"
        r"limited time|solo tengo|un poco de tiempo|pequito tiemp)\b",
        low,
    ):
        aff["last_meta"] = text[:200]
        aff["energy"] = "limited_time"
        # Do NOT treat time pressure as boredom
        if aff.get("boredom_risk") != "high":
            aff["boredom_risk"] = "low"

    # Name capture
    skills = s.setdefault("skills", default_skills_block())

    # Name capture — learners often approximate *me llamo*
    name = None
    for pat in (
        r"\bme\s+llamo\s+(?:es\s+)?([A-Za-zÁÉÍÓÚáéíóúñÑ]+)",
        r"\bme\s+llama\s+(?:es\s+)?([A-Za-zÁÉÍÓÚáéíóúñÑ]+)",  # common error
        r"\bmy\s+name\s+is\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)",
        r"\bI(?:'m| am)\s+([A-Z][a-zÁÉÍÓÚáéíóúñÑ]{2,})\b",
    ):
        m = re.search(pat, text, re.I)
        if m:
            cand = m.group(1)
            if cand.lower() not in {
                "from", "the", "very", "fine", "good", "here", "just",
            }:
                name = cand
                break
    if name:
        s.setdefault("identity", {})["preferred_name"] = name.capitalize()
        skills["IP-03"] = _bump_status(
            skills.get("IP-03") or {}, success=True, amount=0.25)
        _touch_coverage(s, "introduce_self")

    # Lexicon + can-dos from successful-looking use
    for pat, lemma, can_do in _LEXICON_PATTERNS:
        if re.search(pat, f, re.I) or re.search(pat, low, re.I):
            lex = s.setdefault("lexicon", {})
            prev = lex.get(lemma) or {"status": "unknown", "confidence": 0.0}
            lex[lemma] = _bump_status(prev, success=True, amount=0.12)
            if can_do in skills:
                skills[can_do] = _bump_status(
                    skills[can_do], success=True, amount=0.1)

    # Conceptual signals (supporting forms + related can-dos)
    g = s.setdefault("grammar", default_grammar_block())
    if re.search(r"\besta\s+bien\b", f) and not re.search(r"\bestoy\b", f):
        g["present_estar_person"] = _bump_status(
            g.get("present_estar_person") or {}, success=False, amount=0.2)
        _note_evidence(g["present_estar_person"], "esta bien (wanted estoy?)")
        skills["IP-04"] = _bump_status(skills.get("IP-04") or {}, success=False, amount=0.1)
        _touch_coverage(s, "estar_basic")
    if re.search(r"\bestoy\b", f):
        g["present_estar_person"] = _bump_status(
            g.get("present_estar_person") or {}, success=True, amount=0.18)
        _note_evidence(g["present_estar_person"], "used estoy")
        skills["IP-04"] = _bump_status(skills.get("IP-04") or {}, success=True)
        _touch_coverage(s, "estar_basic")

    # Register: informal to formal addressee
    if re.search(r"\b(senora|senor|profesor|maestr)\b", f):
        if re.search(r"\b(como estas|te llamas|y tu)\b", f) and not re.search(
                r"\busted\b", f):
            g["register_tu_usted"] = _bump_status(
                g.get("register_tu_usted") or {}, success=False, amount=0.2)
            _note_evidence(g["register_tu_usted"], "tú form with formal addressee")
            skills["IP-02"] = _bump_status(skills.get("IP-02") or {}, success=False, amount=0.12)
            _touch_coverage(s, "register_tu_usted")
        elif re.search(r"\b(como esta|usted)\b", f):
            g["register_tu_usted"] = _bump_status(
                g.get("register_tu_usted") or {}, success=True, amount=0.15)
            skills["IP-02"] = _bump_status(skills.get("IP-02") or {}, success=True)
            _touch_coverage(s, "register_tu_usted")

    if re.search(r"\b(hola|buenos|buenas)\b", f):
        _touch_coverage(s, "greetings_time_of_day")
        if re.search(r"\b(usted|senor|senora)\b", f):
            skills["IP-02"] = _bump_status(
                skills.get("IP-02") or {}, success=True, amount=0.12)
        else:
            skills["IP-01"] = _bump_status(
                skills.get("IP-01") or {}, success=True, amount=0.12)

    if re.search(r"\b(soy|eres|es)\b", f):
        g["present_ser"] = _bump_status(
            g.get("present_ser") or {}, success=True, amount=0.12)
        skills["IP-07"] = _bump_status(skills.get("IP-07") or {}, success=True, amount=0.08)
        _touch_coverage(s, "ser_basic")

    # Recurring construction errors (yo está, me llamo es, …)
    s = apply_error_pattern_updates(s, learner)

    s = recompute_next_best(s)
    s["updated_at"] = today()
    return s


def sanitize_tool_delta(delta: dict | None) -> dict:
    """Keep only trusted top-level keys from a tool / model delta."""
    if not isinstance(delta, dict):
        return {}
    allowed = {
        "identity", "affect", "next_best", "lexicon", "skills", "grammar",
        "coverage", "receptive", "error_patterns", "reason", "notes",
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

    if "identity" in delta and isinstance(delta["identity"], dict):
        ident = {**s.get("identity", {}), **delta["identity"]}
        prev_name = (s.get("identity") or {}).get("preferred_name")
        new_name = ident.get("preferred_name")
        if prev_name and (
            new_name is None
            or str(new_name).strip() == ""
            or str(new_name).strip().lower() in ("null", "none")
        ):
            ident["preferred_name"] = prev_name
        s["identity"] = ident

    if "affect" in delta and isinstance(delta["affect"], dict):
        aff = {**s.get("affect", {}), **delta["affect"]}
        # Normalize mistaken "boredom" for time-only notes
        meta = str(aff.get("last_meta") or "").lower()
        energy = str(aff.get("energy") or "").lower()
        if aff.get("boredom_risk") == "high" and (
            "time" in meta or "time" in energy or energy == "limited_time"
        ):
            if not re.search(
                r"\b(bor(ed|ing)|stuck|what are we|why are we|hate)\b", meta
            ):
                aff["boredom_risk"] = "low"
                aff["energy"] = aff.get("energy") or "limited_time"
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
        # Soften bogus boredom reasons when energy is limited_time
        reason = str(nb.get("reason") or "").lower()
        if "boredom" in reason and (s.get("affect") or {}).get("energy") == "limited_time":
            nb["reason"] = (
                "limited time — keep tasks short; "
                + (nb.get("reason") or "").replace(
                    "learner signalled boredom/plan confusion — new task (TBLT)",
                    "short stretch",
                )
            )

    touched_skills: list[str] = []
    touched_grammar: list[str] = []
    for section in ("lexicon", "skills", "grammar"):
        if section in delta and isinstance(delta[section], dict):
            base = s.setdefault(section, {})
            for k, v in delta[section].items():
                if not isinstance(v, dict):
                    if section == "lexicon" and isinstance(v, str):
                        prev = base.get(k) or {}
                        base[k] = {
                            **prev,
                            "status": v if v in STATUSES else prev.get(
                                "status", "emerging"),
                            "last_seen": today(),
                        }
                    continue
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
                    merged = {**prev, **v}
                    if "confidence" in v:
                        try:
                            merged["confidence"] = max(
                                0.0, min(1.0, float(v["confidence"])))
                        except (TypeError, ValueError):
                            pass
                    if merged.get("status") not in STATUSES and "status" in merged:
                        merged["status"] = prev.get("status", "unknown")
                    base[k] = merged

    if "coverage" in delta and isinstance(delta["coverage"], dict):
        for topic in delta["coverage"].get("touched") or []:
            if isinstance(topic, str):
                _touch_coverage(s, topic)

    # Tool error_patterns: normalize ids; store examples only (no multi-count).
    # Counts come from harness apply_error_pattern_updates on learner text —
    # otherwise one tool call with 4 examples inflated count by +4.
    if "error_patterns" in delta and isinstance(delta["error_patterns"], dict):
        eps = s.setdefault("error_patterns", {})
        for pid, v in delta["error_patterns"].items():
            if not isinstance(v, dict):
                continue
            pid = normalize_error_pattern_id(pid)
            if pid not in ERROR_PATTERN_CATALOG and not v.get("last_examples"):
                continue
            if v.get("resolved") or v.get("resolved_streak"):
                note_error_pattern(s, pid, "tool:resolved", resolved=True)
                continue
            cat = ERROR_PATTERN_CATALOG.get(pid) or {}
            ent = dict(eps.get(pid) or {
                "count": 0,
                "priority": "low",
                "last_examples": [],
                "label": cat.get("label") or pid,
                "form_id": cat.get("form_id"),
                "can_dos": list(cat.get("can_dos") or []),
                "teach_hint": cat.get("teach_hint") or "",
                "last_seen": None,
                "resolved_streak": 0,
            })
            ex = list(ent.get("last_examples") or [])
            for item in v.get("last_examples") or []:
                if isinstance(item, str) and item.strip() and item not in ex:
                    ex.append(item.strip()[:100])
            ent["last_examples"] = ex[-5:]
            if cat:
                ent["label"] = cat.get("label") or ent.get("label")
                ent["form_id"] = cat.get("form_id")
                ent["can_dos"] = list(cat.get("can_dos") or [])
                ent["teach_hint"] = cat.get("teach_hint") or ""
            eps[pid] = ent

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
        "Update your working model of this Spanish learner when you have NEW "
        "evidence from the latest exchange (name, can-do use, scaffold need, "
        "affect, error patterns, next stretch). Skip if nothing meaningful changed. "
        "Partial delta only — not the full sheet. Be conservative: prefer "
        "emerging/fragile over known; one good turn is not mastery. "
        "Limited time ≠ boredom (use energy=limited_time). "
        "For repeated construction errors (e.g. yo está), set error_patterns "
        "examples. Always keep preferred_name once known. Student never sees this tool."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "One line: why this update (evidence-based).",
            },
            "identity": {
                "type": "object",
                "properties": {
                    "preferred_name": {"type": "string"},
                    "engagement_notes": {"type": "string"},
                },
            },
            "error_patterns": {
                "type": "object",
                "description": (
                    "Recurring construction errors. Keys e.g. "
                    "estar_yo_estoy_vs_esta, me_llamo_es, tengo_not_tango, soy_de_origin. "
                    "Pass last_examples: [\"yo está en…\"]. Harness increments counts."
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
                    "{status, confidence}. status: unknown|emerging|fragile|known|blocked"
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
                "description": "Lemma → {status, confidence} for words they used",
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
                    "boredom_risk": {"type": "string"},
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


def recompute_next_best(sheet: dict) -> dict:
    """Pick next can-do + CLT/TBLT activity from sheet (docs/spanish-can-dos-novice.md §7)."""
    s = copy.deepcopy(sheet)
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

    # Boredom only when explicitly high — last_meta alone is not boredom
    # (e.g. "I only have a little time" is limited_time, not boredom).
    if affect.get("boredom_risk") == "high":
        can_do = "IP-08"
        stretch_key = "change_activity"
        avoid = "another_greeting_or_register_retry"
        reason = "learner signalled boredom/plan confusion — new task (TBLT)"
    elif evidence_mass < 0.35:
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
            # Don't grind IP-01 if already emerging+ and others lag
            if cid == "IP-01" and conf(skills, "IP-01") >= 0.55:
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
    if (
        is_session_scoped_energy(affect.get("energy"))
        and affect.get("boredom_risk") != "high"
    ):
        avoid = "dragging_out_session_when_time_limited"
        if "limited time" not in reason.lower():
            reason = f"limited time — keep it short | {reason}"

    # Recurring construction errors outrank pure can-do stretch when hot
    form_focus = None
    error_pattern = None
    active = active_error_patterns(s)
    if active and affect.get("boredom_risk") != "high":
        top = active[0]
        error_pattern = top["id"]
        form_focus = top.get("form_id")
        # Prefer a can-do that the pattern supports, if open
        for cid in top.get("can_dos") or []:
            if cid in CAN_DOS and not is_known(cid):
                can_do = cid
                stretch_key = cid
                act = STRETCH_ACTIVITIES.get(cid) or act
                break
        reason = (
            f"recurring error ×{top['count']}: {top['label']} "
            f"(e.g. {', '.join(top.get('last_examples') or [])}) — "
            f"recast/weave before new stretch | {reason}"
        )
        avoid = "ignore_repeated_form_error_and_only_chat"

    s["next_best"] = {
        "can_do": can_do if can_do is not None else act.get("can_do"),
        "stretch": act.get("activity") or stretch_key,
        "activity": act.get("activity") or stretch_key,
        "statement": CAN_DOS[can_do]["statement"] if can_do in CAN_DOS else act.get("description"),
        "avoid": avoid,
        "reason": reason,
        "method": "CLT/TBLT + CI + focus_on_form",
        "form_focus": form_focus,
        "error_pattern": error_pattern,
        "teach_hint": (
            (ERROR_PATTERN_CATALOG.get(error_pattern) or {}).get("teach_hint")
            if error_pattern else None
        ),
    }
    return s


def summarize_sheet_changes(before: dict, after: dict) -> list[str]:
    """Short human notes for the console."""
    notes = []
    bn = (before.get("identity") or {}).get("preferred_name")
    an = (after.get("identity") or {}).get("preferred_name")
    if an and an != bn:
        notes.append(f"name={an}")
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
        notes.append("can-dos " + ", ".join(bumped[:6]))
    if json.dumps(before.get("next_best"), sort_keys=True) != json.dumps(
            after.get("next_best"), sort_keys=True):
        nb = after.get("next_best") or {}
        notes.append(f"next={nb.get('can_do') or '—'} / {nb.get('activity')}")
    rec = after.get("receptive") or {}
    notes.append(
        "scaffold=EN+ES" if rec.get("needs_english_scaffold", True)
        else "scaffold=more_ES"
    )
    return notes


def normalize_sheet(sheet: dict) -> dict:
    """Ensure required keys/can-dos exist after an AI rewrite."""
    base = default_sheet()
    if not isinstance(sheet, dict):
        return base
    merged = _deep_merge(base, sheet)
    merged["skills"] = migrate_skills(merged.get("skills") or {})
    for cid, entry in default_skills_block().items():
        merged["skills"].setdefault(cid, entry)
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
    for fid, entry in default_grammar_block().items():
        g = merged.setdefault("grammar", {})
        g.setdefault(fid, entry)
        if g[fid].get("status") not in STATUSES:
            g[fid]["status"] = "unknown"
    merged["version"] = max(int(merged.get("version") or 2), 2)
    merged["framework"] = base["framework"]
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
) -> tuple[dict, str, list[str]]:
    """Apply post-turn sheet maintenance.

    Priority:
      1. `tool_delta` — teaching AI called update_character_sheet (primary)
      2. `revised_sheet` — legacy full AI rewrite (optional)
      3. rules + optional inline <sheet_delta> (backup)

    Returns (sheet, visible_tutor_text, change_notes).
    """
    visible, inline_delta = extract_sheet_delta(tutor_reply)
    before = copy.deepcopy(sheet)

    if tool_delta:
        s = apply_delta(sheet, tool_delta)
        # Keep can-do statements stamped even if the tool omitted them
        for cid, entry in default_skills_block().items():
            sk = s.setdefault("skills", {})
            sk.setdefault(cid, entry)
            if cid in CAN_DOS:
                sk[cid]["mode"] = CAN_DOS[cid]["mode"]
                sk[cid]["band"] = CAN_DOS[cid]["band"]
                sk[cid]["statement"] = CAN_DOS[cid]["statement"]
        # Harness always re-detects patterns from learner text (tool may miss)
        s = apply_error_pattern_updates(s, learner)
        # Recompute when recurring errors must steer, or next_best incomplete
        nb = s.get("next_best") or {}
        if active_error_patterns(s) or not (nb.get("activity") or nb.get("stretch")):
            s = recompute_next_best(s)
        s = _preserve_identity(sheet, s)
        notes = ["tool_update"]
        reason = tool_delta.get("reason") or tool_delta.get("notes")
        if isinstance(reason, str) and reason.strip():
            notes.append(f"why={reason.strip()[:80]}")
    elif revised_sheet is not None:
        s = normalize_sheet(revised_sheet)
        s = apply_error_pattern_updates(s, learner)
        nb = s.get("next_best") or {}
        if active_error_patterns(s) or not (nb.get("activity") or nb.get("stretch")):
            s = recompute_next_best(s)
        s = _preserve_identity(sheet, s)
        notes = ["ai_update"]
    else:
        # Backup: rules + optional inline delta (no second model call)
        s = apply_rule_updates(sheet, learner, visible)
        notes = ["rules_backup"]
        if inline_delta:
            s = apply_delta(s, inline_delta)
            notes.append("inline_delta")
        s = update_scaffold_flag(s, learner)
        s = recompute_next_best(s)
        s = _preserve_identity(sheet, s)

    # Surface hot error patterns in console notes
    for ep in active_error_patterns(s):
        notes.append(f"err×{ep['count']}:{ep['id']}")

    notes.extend(summarize_sheet_changes(before, s))
    # de-dupe while preserving order
    seen = set()
    out_notes = []
    for n in notes:
        if n not in seen:
            seen.add(n)
            out_notes.append(n)
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
