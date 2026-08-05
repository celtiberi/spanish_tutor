"""XP — journey volume, derived from evidence ledgers (never stored).

Design law: docs/design-xp-progression.md (converged with Grok
2026-08-05; day cap removed by USER adjudication). The two truths:
the character sheet is ABILITY (can go down); XP is the JOURNEY — a
code-owned, recomputable, monotone sum over ledger events that each
carry evidence. The model never writes XP; nothing pays without an
event; exposure, seat-time and echo pay zero.

Payers (only kinds that EXIST in the ledgers):
- grade ledger band crossings, sections lexicon/grammar only:
  unknown→emerging 10, →fragile +15, →known +25; paid once per
  (item, band) per epoch — a jump pays the path, a re-earn after a
  down-grade pays only bands above the highest already paid.
- progress ledger: taking_root 25 (first ≥3d retrieval), rooted 40
  (14d — "holding at the 2-week check"), error_recovered 30 (ledger's
  own shipped gate), can_do_known 50 (skills pay ONLY here — no band
  money, so a can-do never double-pays).
- `retracted` rows SUBTRACT the voided milestone's payment: a retracted
  event never happened, which is different from ability regression
  (regressions subtract nothing — practice that happened, happened).
- Games: NO ledger event exists yet for game results → games pay 0 in
  v1 (no event, no points — the honest gap, not a fake weight).
"""

from __future__ import annotations

from typing import Any

# The one weights table — mirrors the design doc exactly.
BAND_XP = {"emerging": 10, "fragile": 15, "known": 25}
BAND_ORDER = ["unknown", "emerging", "fragile", "known"]
MILESTONE_XP = {
    "taking_root": 25,
    "rooted": 40,
    "error_recovered": 30,
    "can_do_known": 50,
}
# Sections whose grade-ledger band crossings pay; skills pay only via
# the can_do_known milestone (no double pay).
BAND_SECTIONS = ("lexicon", "grammar")

# Level thresholds: 0/100/250/500/900 then ~1.6x band growth.
def level_thresholds(n: int = 12) -> list[int]:
    t = [0, 100, 250, 500, 900]
    while len(t) < n:
        t.append(t[-1] + int(round((t[-1] - t[-2]) * 1.6 / 10) * 10))
    return t[:n]


# Gated domain-echo names: a level carries its can-do name ONLY if that
# family's skill is >= emerging on the sheet at render time; otherwise
# plain «Nivel N». XP alone never grants a name.
LEVEL_NAMES = {
    1: ("«Hola»", "IP-01"),
    2: ("«Me llamo…»", "IP-03"),
    3: ("«¿Cómo estás?»", "IP-04"),
    4: ("«Mi vida»", "IP-07"),
    5: ("«Cuéntame»", "IP-08"),
}


def _band_index(status: str | None) -> int:
    s = str(status or "unknown").lower()
    return BAND_ORDER.index(s) if s in BAND_ORDER else 0


def _evidence_shows(section: str, item: str, evidence: str) -> bool:
    """Mechanical evidence audit (code = auditor, §1.1): a lexicon
    crossing pays only if the credited word appears, correctly spelled
    (accent-lenient), in the quoted evidence — 'esta bein' mints nothing
    for «bien» (2026-08-05 gate: the lite teacher credited garble; the
    sheet grade is teaching judgment and may stand, but XP demands the
    evidence literally show the item). Grammar rows are audited against
    the form's paradigm when MORPHOLOGY_BY_FORM knows it; unknown form
    ids pay unaudited (benefit of doubt, recorded here honestly). No
    evidence quote → no pay."""
    from .textnorm import phrase_present

    if not evidence.strip():
        return False
    if section == "lexicon":
        word = item.replace("_", " ")
        if len(word) <= 2:
            return False  # bare function words (de, el, y) are not XP events
        return phrase_present(word, evidence)
    if section == "grammar":
        from .can_dos import MORPHOLOGY_BY_FORM

        block = MORPHOLOGY_BY_FORM.get(item)
        if not block:
            return True  # unauditable form id — benefit of the doubt
        return any(
            phrase_present(str(row.get("form") or ""), evidence)
            for row in (block.get("paradigm") or [])
        )
    return True


def _post_epoch(rows: list[dict]) -> list[dict]:
    epoch_i = -1
    for i, r in enumerate(rows):
        if r.get("kind") == "epoch":
            epoch_i = i
    return rows[epoch_i + 1:]


def compute_xp(
    grade_rows: list[dict],
    progress_rows: list[dict],
    *,
    sheet: dict | None = None,
) -> dict[str, Any]:
    """Pure XP computation. Rows are OLDEST-FIRST full ledger dumps
    (epoch rows included — the last epoch scopes each list). Returns
    {total, level, level_name, to_next, next_threshold, events} where
    events maps ledger rows to the points they paid (for UI gluing).
    """
    grade_rows = _post_epoch(list(grade_rows or []))
    progress_rows = _post_epoch(list(progress_rows or []))

    total = 0
    events: list[dict] = []

    # --- grade-ledger band crossings (lexicon/grammar only) ---
    paid_band: dict[tuple[str, str], int] = {}  # (section,item) -> max band idx paid
    for r in grade_rows:
        if r.get("kind") != "grade":
            continue
        section = str(r.get("section") or "")
        if section not in BAND_SECTIONS:
            continue
        item = str(r.get("field_id") or "")
        if not _evidence_shows(section, item, str(r.get("evidence") or "")):
            continue  # audit failed: quoted evidence does not show the item
        to_i = _band_index(r.get("to_status"))
        key = (section, item)
        prev_paid = paid_band.get(key, 0)
        if to_i <= prev_paid:
            continue  # down-grade, repeat, or already-paid band
        pts = sum(
            BAND_XP[BAND_ORDER[b]] for b in range(prev_paid + 1, to_i + 1)
        )
        paid_band[key] = to_i
        total += pts
        events.append({
            "source": "grade", "key": item, "section": section,
            "ts": r.get("ts"), "xp": pts,
        })

    # --- progress-ledger milestones (ledger already dedupes per kind,key) ---
    paid_ms: dict[tuple[str, str], int] = {}
    for r in progress_rows:
        kind = str(r.get("kind") or "")
        key = str(r.get("key") or "")
        if kind == "retracted":
            # Voids a milestone that should never have paid.
            target = str(r.get("retracts") or "")
            pts = paid_ms.pop((target, key), 0)
            if pts:
                total -= pts
                events.append({
                    "source": "retracted", "key": key, "kind": target,
                    "ts": r.get("ts"), "xp": -pts,
                })
            continue
        pts = MILESTONE_XP.get(kind, 0)
        if not pts or (kind, key) in paid_ms:
            continue
        paid_ms[(kind, key)] = pts
        total += pts
        events.append({
            "source": "milestone", "key": key, "kind": kind,
            "ts": r.get("ts"), "xp": pts,
        })

    total = max(0, total)

    # --- level ---
    thresholds = level_thresholds()
    level = 1
    for i, th in enumerate(thresholds, start=0):
        if total >= th:
            level = i + 1
    level = min(level, len(thresholds))
    next_threshold = (
        thresholds[level] if level < len(thresholds) else None
    )

    name = f"Nivel {level}"
    gated = LEVEL_NAMES.get(level)
    if gated and sheet:
        label, family = gated
        sk = (sheet.get("skills") or {}).get(family) or {}
        if _band_index(sk.get("status")) >= _band_index("emerging"):
            name = f"Nivel {level} {label}"

    return {
        "total": total,
        "level": level,
        "level_name": name,
        "level_floor": thresholds[level - 1],
        "to_next": (next_threshold - total) if next_threshold else None,
        "next_threshold": next_threshold,
        "events": events,
    }


def read_ledger(path, *, session_suffix: str | None = None) -> list[dict]:
    """Oldest-first rows from a jsonl ledger; optionally filtered to
    session ids ending in ``-<session_suffix>`` (multi-user scoping on
    the shared progress ledger). Epoch rows always pass the filter so
    scoping never un-scopes a reset."""
    import json
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if session_suffix and r.get("kind") != "epoch":
            sid = str(r.get("session_id") or "")
            if not sid.endswith(f"-{session_suffix}"):
                continue
        rows.append(r)
    return rows
