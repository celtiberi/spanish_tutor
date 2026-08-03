"""Domain-model data loader — ``domain/<level>/`` is the source of truth.

S10 (docs/reviews-full-code-audit-20260803.md, USER-flagged smell 2026-08-03:
"the sheet is being built at runtime instead of being the source of truth"):
the ENTIRE domain model for a level slice lives as DATA in
``domain/spanish_a1/`` — can-dos, grammar forms + paradigms, scope, and the
misconception catalog — alongside the association table.  Code keeps
mechanics only (transitions, thresholds, grading, formatting).  A new level
= a new data dir, zero code edits.

Mirrors ``association_table.py``: a validating loader that raises loudly and
completely (ALL problems listed, not the first) on malformed data, plus one
module-level cache for the default pack.  A missing or corrupt domain file
is a STARTUP error (the consuming modules bind at import), never a silent
default — no-hide.  Sessions with a custom ``pack_dir`` can call
``load_domain`` directly, exactly like ``load_association_table``.

Misconception ``detect`` entries are (regex, note) pairs — serialized as
2-element arrays in ``misconceptions.json``, loaded back as tuples (the
historical in-memory shape).  ``detect``/``resolve`` regexes are COMPILED at
load (case-insensitive, the runtime flag) into ``detect_compiled`` /
``resolve_compiled``; a pattern that does not compile is malformed data.

Code-owned: the model never edits these files.  Stdlib only.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CAN_DOS_FILENAME = "can_dos.json"
GRAMMAR_FORMS_FILENAME = "grammar_forms.json"
DOMAIN_SCOPE_FILENAME = "domain_scope.json"
MISCONCEPTIONS_FILENAME = "misconceptions.json"

DOMAIN_FILENAMES = (
    CAN_DOS_FILENAME,
    GRAMMAR_FORMS_FILENAME,
    DOMAIN_SCOPE_FILENAME,
    MISCONCEPTIONS_FILENAME,
)

# grammar_forms.json records are the flat merge of the two historical
# structures; the loader splits them back by field name (no collisions).
FORM_INVENTORY_FIELDS = ("supports", "priority", "error_example")
MORPHOLOGY_FIELDS = ("label", "lemma", "pos", "paradigm", "note", "watch")

_CAN_DO_SECTIONS = (
    "can_dos", "can_do_themes", "morphology_by_can_do", "stretch_activities",
)
_PRIORITIES = ("high", "medium", "low")
_SCOPE_LIST_FIELDS = (
    "deferred_do_not_introduce", "out_of_scope_decline_briefly",
    "recognition_only",
)
_MISCONCEPTION_REQUIRED = ("label", "form_id", "can_dos", "teach_hint",
                           "detect", "resolve")


@dataclass(frozen=True)
class DomainData:
    """One level slice, loaded and validated. Treat every field read-only."""

    can_dos: dict[str, dict]
    can_do_themes: dict[str, tuple[str, ...]]
    morphology_by_cando: dict[str, dict]
    stretch_activities: dict[str, dict]
    form_inventory: dict[str, dict]
    morphology_by_form: dict[str, dict]
    domain_scope: dict
    misconceptions: dict[str, dict]
    detect_compiled: dict[str, list[tuple[re.Pattern, str]]] = field(
        default_factory=dict)
    resolve_compiled: dict[str, list[re.Pattern]] = field(
        default_factory=dict)


def _read_json_object(pack_dir: Path, name: str) -> dict:
    path = pack_dir / name
    if not path.exists():
        raise FileNotFoundError(f"No {name} in {pack_dir}")
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"{name}: invalid JSON ({e})") from e
    if not isinstance(raw, dict):
        raise ValueError(f"{name}: top level must be an object")
    return raw


def _is_str(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _str_list(v: Any) -> bool:
    return isinstance(v, list) and all(_is_str(x) for x in v)


def _validate_can_dos(doc: dict, problems: list[str]) -> None:
    missing = [s for s in _CAN_DO_SECTIONS if not isinstance(doc.get(s), dict)]
    if missing:
        problems.append(
            f"{CAN_DOS_FILENAME}: missing/invalid sections {missing}")
        return
    for cid, meta in doc["can_dos"].items():
        if not isinstance(meta, dict):
            problems.append(f"can_dos[{cid}]: entry must be an object")
            continue
        for f in ("mode", "band", "statement", "activity"):
            if not _is_str(meta.get(f)):
                problems.append(f"can_dos[{cid}]: {f} must be a non-empty string")
        if meta.get("priority") not in _PRIORITIES:
            problems.append(f"can_dos[{cid}]: priority must be one of {_PRIORITIES}")
        for f in ("form_hooks", "coverage_topics"):
            v = meta.get(f)
            if not isinstance(v, list) or not all(_is_str(x) for x in v):
                problems.append(f"can_dos[{cid}]: {f} must be a list of strings")
    claimed: dict[str, str] = {}
    for cid, themes in doc["can_do_themes"].items():
        if cid not in doc["can_dos"]:
            problems.append(f"can_do_themes[{cid}]: unknown can-do id")
        if not _str_list(themes):
            problems.append(f"can_do_themes[{cid}]: must be a list of strings")
            continue
        for theme in themes:
            if theme in claimed:
                problems.append(
                    f"can_do_themes: theme {theme!r} routed to both "
                    f"{claimed[theme]} and {cid} (a theme may serve at most "
                    "ONE can-do)")
            claimed[theme] = cid
    for cid, block in doc["morphology_by_can_do"].items():
        if cid not in doc["can_dos"]:
            problems.append(f"morphology_by_can_do[{cid}]: unknown can-do id")
        _validate_morph_block(f"morphology_by_can_do[{cid}]", block, problems)
    stretch = doc["stretch_activities"]
    if "open_chat_and_notice" not in stretch:
        problems.append(
            "stretch_activities: 'open_chat_and_notice' is required "
            "(recompute_next_best's fallback)")
    for key, act in stretch.items():
        if not isinstance(act, dict):
            problems.append(f"stretch_activities[{key}]: entry must be an object")
            continue
        for f in ("activity", "description"):
            if not _is_str(act.get(f)):
                problems.append(
                    f"stretch_activities[{key}]: {f} must be a non-empty string")
        if key not in doc["can_dos"]:
            if "can_do" not in act:
                problems.append(
                    f"stretch_activities[{key}]: non-can-do key needs an "
                    "explicit can_do field (may be null)")
            elif act["can_do"] is not None and act["can_do"] not in doc["can_dos"]:
                problems.append(
                    f"stretch_activities[{key}]: can_do {act['can_do']!r} unknown")


def _validate_morph_block(where: str, block: Any, problems: list[str]) -> None:
    if not isinstance(block, dict):
        problems.append(f"{where}: must be an object")
        return
    for f in ("label", "lemma", "pos"):
        if not _is_str(block.get(f)):
            problems.append(f"{where}: {f} must be a non-empty string")
    for f in ("note", "watch"):
        if not isinstance(block.get(f), str):
            problems.append(f"{where}: {f} must be a string")
    paradigm = block.get("paradigm")
    if not isinstance(paradigm, list) or not paradigm:
        problems.append(f"{where}: paradigm must be a non-empty list")
        return
    for i, row in enumerate(paradigm):
        if not isinstance(row, dict) or not all(
            _is_str(row.get(f)) for f in ("form", "person", "gloss")
        ):
            problems.append(
                f"{where}: paradigm[{i}] needs form/person/gloss strings")


def _validate_grammar_forms(
    doc: dict, can_do_ids: set[str], problems: list[str]
) -> None:
    allowed = set(FORM_INVENTORY_FIELDS) | set(MORPHOLOGY_FIELDS)
    for fid, rec in doc.items():
        if not isinstance(rec, dict):
            problems.append(f"grammar_forms[{fid}]: entry must be an object")
            continue
        unknown = set(rec) - allowed
        if unknown:
            problems.append(f"grammar_forms[{fid}]: unknown fields {sorted(unknown)}")
        if not _str_list(rec.get("supports")):
            problems.append(
                f"grammar_forms[{fid}]: supports must be a list of strings")
        else:
            for cid in rec["supports"]:
                if cid not in can_do_ids:
                    problems.append(
                        f"grammar_forms[{fid}]: supports unknown can-do {cid!r}")
        if rec.get("priority") not in _PRIORITIES:
            problems.append(
                f"grammar_forms[{fid}]: priority must be one of {_PRIORITIES}")
        if not _is_str(rec.get("error_example")):
            problems.append(
                f"grammar_forms[{fid}]: error_example must be a non-empty string")
        morph_present = [f for f in MORPHOLOGY_FIELDS if f in rec]
        if morph_present and set(morph_present) != set(MORPHOLOGY_FIELDS):
            problems.append(
                f"grammar_forms[{fid}]: partial morphology — has "
                f"{sorted(morph_present)}, needs all of {sorted(MORPHOLOGY_FIELDS)}")
        elif morph_present:
            _validate_morph_block(f"grammar_forms[{fid}]", rec, problems)


def _validate_domain_scope(doc: dict, problems: list[str]) -> None:
    if not _is_str(doc.get("level")):
        problems.append(f"{DOMAIN_SCOPE_FILENAME}: level must be a non-empty string")
    for f in _SCOPE_LIST_FIELDS:
        if not _str_list(doc.get(f)):
            problems.append(
                f"{DOMAIN_SCOPE_FILENAME}: {f} must be a list of strings")
    unknown = set(doc) - {"level", *_SCOPE_LIST_FIELDS}
    if unknown:
        problems.append(f"{DOMAIN_SCOPE_FILENAME}: unknown fields {sorted(unknown)}")


def _validate_misconceptions(
    doc: dict, form_ids: set[str], can_do_ids: set[str], problems: list[str]
) -> tuple[dict[str, list[tuple[re.Pattern, str]]], dict[str, list[re.Pattern]]]:
    detect_compiled: dict[str, list[tuple[re.Pattern, str]]] = {}
    resolve_compiled: dict[str, list[re.Pattern]] = {}
    sources: dict[str, str] = {}
    for pid, rec in doc.items():
        if not isinstance(rec, dict):
            problems.append(f"misconceptions[{pid}]: entry must be an object")
            continue
        missing = [f for f in _MISCONCEPTION_REQUIRED if f not in rec]
        if missing:
            problems.append(f"misconceptions[{pid}]: missing fields {missing}")
            continue
        if not _is_str(rec.get("label")):
            problems.append(f"misconceptions[{pid}]: label must be a non-empty string")
        fid = rec.get("form_id")
        if fid is not None:
            if not _is_str(fid):
                problems.append(
                    f"misconceptions[{pid}]: form_id must be a string or null")
            elif fid not in form_ids:
                problems.append(
                    f"misconceptions[{pid}]: form_id {fid!r} not in "
                    f"{GRAMMAR_FORMS_FILENAME}")
        if not isinstance(rec.get("can_dos"), list) or not all(
            _is_str(c) for c in rec["can_dos"]
        ):
            problems.append(
                f"misconceptions[{pid}]: can_dos must be a list of strings")
        else:
            for cid in rec["can_dos"]:
                if cid not in can_do_ids:
                    problems.append(
                        f"misconceptions[{pid}]: unknown can-do {cid!r}")
        if not isinstance(rec.get("teach_hint"), str):
            problems.append(f"misconceptions[{pid}]: teach_hint must be a string")
        src = rec.get("source")
        if src is not None:
            if not _is_str(src):
                problems.append(
                    f"misconceptions[{pid}]: source must be a string when present")
            elif src in sources:
                problems.append(
                    f"misconceptions[{pid}]: duplicate source {src!r} "
                    f"(also on {sources[src]})")
            else:
                sources[src] = pid
        det: list[tuple[re.Pattern, str]] = []
        detect = rec.get("detect")
        if not isinstance(detect, list):
            problems.append(f"misconceptions[{pid}]: detect must be a list")
        else:
            for i, pair in enumerate(detect):
                if (
                    not isinstance(pair, (list, tuple))
                    or len(pair) != 2
                    or not all(isinstance(x, str) for x in pair)
                ):
                    problems.append(
                        f"misconceptions[{pid}]: detect[{i}] must be a "
                        "[pattern, note] pair of strings")
                    continue
                try:
                    det.append((re.compile(pair[0], re.I), pair[1]))
                except re.error as e:
                    problems.append(
                        f"misconceptions[{pid}]: detect[{i}] regex does not "
                        f"compile ({e})")
        res: list[re.Pattern] = []
        resolve = rec.get("resolve")
        if not isinstance(resolve, list) or not all(
            isinstance(x, str) for x in resolve
        ):
            problems.append(
                f"misconceptions[{pid}]: resolve must be a list of strings")
        else:
            for i, pat in enumerate(resolve):
                try:
                    res.append(re.compile(pat, re.I))
                except re.error as e:
                    problems.append(
                        f"misconceptions[{pid}]: resolve[{i}] regex does not "
                        f"compile ({e})")
        detect_compiled[pid] = det
        resolve_compiled[pid] = res
    return detect_compiled, resolve_compiled


def load_domain(pack_dir: Path | str) -> DomainData:
    """Load + validate the four domain files in ``pack_dir``.

    Raises FileNotFoundError for a missing file, ValueError listing ALL
    schema/cross-reference problems for malformed data.  Never returns a
    partial or defaulted domain.
    """
    pack = Path(pack_dir)
    can_dos_doc = _read_json_object(pack, CAN_DOS_FILENAME)
    grammar_doc = _read_json_object(pack, GRAMMAR_FORMS_FILENAME)
    scope_doc = _read_json_object(pack, DOMAIN_SCOPE_FILENAME)
    misc_doc = _read_json_object(pack, MISCONCEPTIONS_FILENAME)

    problems: list[str] = []
    _validate_can_dos(can_dos_doc, problems)
    can_do_ids = set(
        can_dos_doc.get("can_dos") or {}
    ) if isinstance(can_dos_doc.get("can_dos"), dict) else set()
    _validate_grammar_forms(grammar_doc, can_do_ids, problems)
    # form_hooks cross-ref (needs both files, so it lives here)
    if isinstance(can_dos_doc.get("can_dos"), dict):
        for cid, meta in can_dos_doc["can_dos"].items():
            if not isinstance(meta, dict):
                continue
            for fid in meta.get("form_hooks") or []:
                if fid not in grammar_doc:
                    problems.append(
                        f"can_dos[{cid}]: form_hook {fid!r} not in "
                        f"{GRAMMAR_FORMS_FILENAME}")
    _validate_domain_scope(scope_doc, problems)
    detect_compiled, resolve_compiled = _validate_misconceptions(
        misc_doc, set(grammar_doc), can_do_ids, problems)
    if problems:
        raise ValueError(
            f"domain data schema errors in {pack} ({len(problems)}):\n"
            + "\n".join(f"- {p}" for p in problems)
        )

    form_inventory = {
        fid: {f: rec[f] for f in FORM_INVENTORY_FIELDS}
        for fid, rec in grammar_doc.items()
    }
    morphology_by_form = {
        fid: {f: rec[f] for f in MORPHOLOGY_FIELDS}
        for fid, rec in grammar_doc.items()
        if any(f in rec for f in MORPHOLOGY_FIELDS)
    }
    misconceptions = {
        pid: {**rec, "detect": [tuple(p) for p in rec["detect"]]}
        for pid, rec in misc_doc.items()
    }
    return DomainData(
        can_dos=can_dos_doc["can_dos"],
        can_do_themes={
            cid: tuple(themes)
            for cid, themes in can_dos_doc["can_do_themes"].items()
        },
        morphology_by_cando=can_dos_doc["morphology_by_can_do"],
        stretch_activities=can_dos_doc["stretch_activities"],
        form_inventory=form_inventory,
        morphology_by_form=morphology_by_form,
        domain_scope=scope_doc,
        misconceptions=misconceptions,
        detect_compiled=detect_compiled,
        resolve_compiled=resolve_compiled,
    )


_default_domain_cache: DomainData | None = None


def cached_default_domain() -> DomainData:
    """Validated domain data for ``config.DEFAULT_PACK_DIR``, loaded once
    per process.  ``can_dos.py`` / ``character_sheet.py`` bind their public
    names from this at import — so a broken default domain dir fails the
    process at STARTUP (import error), never a silent default.  Sessions
    with a custom pack dir call ``load_domain`` themselves, exactly like
    ``association_table.load_association_table``."""
    global _default_domain_cache
    if _default_domain_cache is None:
        from .config import DEFAULT_PACK_DIR

        _default_domain_cache = load_domain(DEFAULT_PACK_DIR)
    return _default_domain_cache
