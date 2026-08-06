"""learner_text_facts — offline dictionary facts about the learner's
message, injected into the round-turn task (ENGINEERING §1.1
fact-surface clause, 2026-08-05; design + amendments:
docs/archive/reviews/pre-grading-20260805.md).

FACTS ONLY, closed field vocabulary: w, es, zipf, cands[], cls,
verb_forms[].matches[]. Forbidden forever: band, error_pattern,
teach_next, recast, severity, probe, mode, and any singleton
"nearest" (a privileged repair string is a recast prime — killed in
review on anchoring literature). Sparse emission: only invalid
tokens, verb-form hits, and name/OOV classes ship; hard cap ~80
serialized tokens. EXPERIMENT status: ships only behind TEXT_FACTS
env arms until the pre-registered A/B passes; fails → DELETE (§4.6).

Frozen numbers (do not tune without a new round): T_zipf = 3.1
(real A1 vocabulary >= 3.11 [senderismo, the closest margin], garble
<= 2.68); cands: <=3 neighbors, difflib cutoff 0.75; cap 80 tokens.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

T_ZIPF = 3.1
MAX_CANDS = 3
TOKEN_CAP = 80  # serialized JSON tokens (chars/4)

_ES_CHARS = "a-záéíóúüñ"
_TOKEN_RE = re.compile(rf"[{_ES_CHARS}A-ZÁÉÍÓÚÜÑ]+")


@lru_cache(maxsize=1)
def _inventory() -> list[str]:
    """cands vocabulary: A1 association inventory + conjugated forms."""
    from . import config
    from .conjugations import _db  # noqa: SLF001 — same package

    words: set[str] = set()
    try:
        table = json.loads(
            (config.REPO_ROOT / "domain" / "spanish_a1" /
             "association_table.json").read_text(encoding="utf-8"))
        for key in table:
            for part in str(key).lower().split():
                if len(part) > 2:
                    words.add(part)
    except (OSError, ValueError):
        pass
    for forms in _db().values():
        for f in forms:
            if " " not in f and len(f) > 2:
                words.add(f)
    return sorted(words)


def _zipf(word: str, lang: str) -> float:
    try:
        from wordfreq import zipf_frequency
    except ImportError:
        return 0.0
    return zipf_frequency(word, lang)


def _edit_distance_le2(a: str, b: str) -> bool:
    """True iff Levenshtein(a, b) <= 2 (banded DP, early exit)."""
    if abs(len(a) - len(b)) > 2:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        row_min = i
        for j, cb in enumerate(b, 1):
            v = min(prev[j] + 1, cur[j - 1] + 1,
                    prev[j - 1] + (ca != cb))
            cur.append(v)
            row_min = min(row_min, v)
        if row_min > 2:
            return False
        prev = cur
    return prev[-1] <= 2


def _neighbors(word: str) -> list[str]:
    """<=3 inventory words within edit distance 2, most frequent first
    (review rule 2: multi-candidate, no forced winner; difflib's ratio
    missed kiero->quiero, a true distance-2 pair — replaced 2026-08-05)."""
    hits = [w for w in _inventory() if _edit_distance_le2(word, w)]
    hits.sort(key=lambda w: -_zipf(w, "es"))
    return hits[:MAX_CANDS]


def build_text_facts(learner_text: str, *, mode: str = "cands") -> dict | None:
    """Facts block for the turn task, or None when there is nothing
    worth reporting (all tokens valid, no verb forms — omit entirely).
    mode="nearest" is the Arm C ablation ONLY (collapses cands to a
    singleton — the anchoring steelman the review expects to FAIL;
    forbidden in production)."""
    text = (learner_text or "").strip()
    if not text:
        return None
    from .conjugations import parses_of_surface

    seen: set[str] = set()
    tokens: list[dict] = []
    verb_forms: list[dict] = []
    for raw in _TOKEN_RE.findall(text):
        low = raw.lower()
        if len(low) <= 1 or low in seen:
            continue
        seen.add(low)

        parses = parses_of_surface(low)
        if parses:
            verb_forms.append({
                "w": low,
                "matches": [
                    {"lemma": lem, "form": form} for lem, form in parses[:4]
                ],
            })
            continue  # a real conjugated form is es-valid; nothing else to say

        z = _zipf(low, "es")
        if z >= T_ZIPF:
            continue  # valid Spanish, not a verb form — sparse emission

        entry: dict = {"w": low, "es": False, "zipf": round(z, 2)}
        if raw[:1].isupper():
            entry["cls"] = "name_or_oov"
        elif _zipf(low, "en") >= 3.5:
            entry["cls"] = "en"
        else:
            entry["cls"] = "unk"
        if entry["cls"] == "unk":
            entry["cands"] = _neighbors(low)
        else:
            entry["cands"] = []
        tokens.append(entry)

    if not tokens and not verb_forms:
        return None

    if mode == "nearest":  # Arm C ablation only
        for t in tokens:
            cands = t.pop("cands", [])
            if cands:
                t["nearest"] = cands[0]

    block = {
        "v": 1,
        "note": ("Dictionary facts only — not grades or recasts; "
                 "membership ≠ success; you judge."),
        "tokens": tokens,
        "verb_forms": verb_forms,
    }
    # Hard cap: drop es-valid verb rows first (rule 8), then oldest cands.
    while len(json.dumps(block, ensure_ascii=False)) // 4 > TOKEN_CAP:
        if verb_forms:
            verb_forms.pop()
        elif any(t.get("cands") for t in tokens):
            for t in tokens:
                if t.get("cands"):
                    t["cands"] = []
                    break
        elif len(tokens) > 1:
            tokens.pop()
        else:
            break
    return block
