"""IntroducePlan router (r7 S2) — code decides HOW a new item enters.

Runtime half of Phase 3 (docs/build-plan-pedagogy-engine.md): executes the
r7 §5 decision tree THIN over the pack association table (S4) and the
introduce ledger (S1, tutor/retrieval_scheduler.py). The router NEVER calls
the model — it emits an IntroducePlan; the tutor model only realizes it.

Rules shipped (docs/pedagogy-research-r7-association-intro.md §5 + the
Adjudication: profile-hook anchors are STRUCK — anchors come from the
association table, images, and the learner's own sheet lexicon):
- R-G budget first: ≤2 introductions per session, else no plan.
- One primary target per move; R-F cluster ban lists the other UNintroduced
  same-theme entries as forbidden this turn (introduced ones are fair
  natural re-use per R-I).
- Scaffold order: R-A cognate → R-B image → R-E keyword → R-D single
  ≤6-word L1 micro-gloss. R-C (engineered ≥95%-coverage context) is
  DEFERRED in this thin ship — deviation noted in the build plan.

Laws: introduction never bumps confidence (retrieval_scheduler enforces the
honesty law on every ledger write); no personal data; single purpose —
imports only sibling pure modules + stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .association_table import entries_for_theme, is_false_friend
from .observe import word_present
from .retrieval_scheduler import is_introduced

# Mirrors tutor/session_memory.INTRO_BUDGET_PER_SESSION (r7 §5 precondition:
# max 2 new-item introductions per A1 session).
SESSION_INTRO_BUDGET = 2

# A lexicon entry at/above this confidence needs no introduction — the
# learner's own sheet already shows use evidence.
CONFIDENT_LEXICON_CONFIDENCE = 0.5

# Openers taught first when next_best gives no steer (unit01 palette).
PRIORITY_THEMES = ("greetings", "farewells", "courtesy")


@dataclass
class IntroducePlan:
    """One code-decided introduction: the item, the rule, the scaffold."""

    key: str
    rule_id: str
    scaffold_type: str  # "cognate" | "image" | "keyword" | "gloss"
    scaffold_payload: dict
    forbid_cluster_with: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "rule_id": self.rule_id,
            "scaffold_type": self.scaffold_type,
            "scaffold_payload": dict(self.scaffold_payload),
            "forbid_cluster_with": list(self.forbid_cluster_with),
        }


def _lexicon_confidence(sheet: dict, key: str) -> float:
    entry = ((sheet or {}).get("lexicon") or {}).get(key)
    if not isinstance(entry, dict):
        return 0.0
    try:
        return float(entry.get("confidence") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _next_best_blob(sheet: dict) -> str:
    nb = (sheet or {}).get("next_best")
    if not isinstance(nb, dict):
        return ""
    return " ".join(str(v) for v in nb.values() if isinstance(v, str)).lower()


def _eligible(sheet: dict, table: dict, key: str) -> bool:
    """Introducible: in the table, in the pack, unintroduced, not confident."""
    entry = table.get(key)
    if not isinstance(entry, dict):
        return False
    if entry.get("in_pack") is False:
        return False
    if is_introduced(sheet, key, "lexicon"):
        return False
    if _lexicon_confidence(sheet, key) >= CONFIDENT_LEXICON_CONFIDENCE:
        return False
    return True


def candidate_keys(
    sheet: dict,
    table: dict,
    *,
    pack_topics: list[str] | None = None,
) -> list[str]:
    """Introducible table keys, teach-order first.

    Order: keys related to the sheet's next_best (key or theme named in its
    text) first, then the greetings/farewells/courtesy openers, then the
    rest — each bucket in table order. ``pack_topics`` is accepted for API
    stability (future in-topic filtering); the thin ship orders from
    next_best + themes only.
    """
    blob = _next_best_blob(sheet)
    related: list[str] = []
    priority: list[str] = []
    rest: list[str] = []
    for key, entry in table.items():
        if not _eligible(sheet, table, key):
            continue
        theme = str(entry.get("theme") or "")
        if blob and (
            word_present(key, blob) or (theme and word_present(theme, blob))
        ):
            related.append(key)
        elif theme in PRIORITY_THEMES:
            priority.append(key)
        else:
            rest.append(key)
    return related + priority + rest


def plan_introduction(
    sheet: dict,
    table: dict,
    session_snapshot: dict,
    *,
    key: str | None = None,
) -> IntroducePlan | None:
    """r7 §5 decision tree, thin. None = introduce nothing this turn.

    R-G budget check first; then one primary target (given ``key`` or the
    first candidate); R-F forbids the other unintroduced same-theme entries;
    scaffold routed R-A → R-B → R-E → R-D (R-C deferred).
    """
    snap = session_snapshot or {}
    introduced = list(snap.get("introduced_this_session") or [])
    try:
        remaining = int(snap.get("intro_budget_remaining"))
    except (TypeError, ValueError):
        remaining = SESSION_INTRO_BUDGET - len(introduced)
    # R-G: session budget exhausted → no plan.
    if remaining <= 0 or len(introduced) >= SESSION_INTRO_BUDGET:
        return None

    if key is not None:
        if not _eligible(sheet, table, key):
            return None
    else:
        candidates = candidate_keys(sheet, table)
        if not candidates:
            return None
        key = candidates[0]

    entry = table[key]
    theme = str(entry.get("theme") or "")
    # R-F cluster ban: the other UNintroduced same-theme entries must not be
    # introduced this turn (near-synonym interference). Already-introduced
    # same-theme keys are legal natural re-use (R-I) and are NOT listed.
    forbid = [
        k
        for k in entries_for_theme(table, theme)
        if k != key and not is_introduced(sheet, k, "lexicon")
    ]

    gloss = str(entry.get("gloss_en") or "")
    # R-A cognate anchor — never for a listed false friend (trap ≠ anchor).
    if entry.get("cognate_en") and not is_false_friend(table, key):
        return IntroducePlan(
            key=key,
            rule_id="R-A",
            scaffold_type="cognate",
            scaffold_payload={
                "anchor": entry["cognate_en"],
                "note": "false-friend-free",
            },
            forbid_cluster_with=forbid,
        )
    # R-B image dual-code — caption is the Spanish form (r5 contiguity).
    if entry.get("imageable"):
        return IntroducePlan(
            key=key,
            rule_id="R-B",
            scaffold_type="image",
            scaffold_payload={"image_concept": key, "caption": key},
            forbid_cluster_with=forbid,
        )
    # R-E curated keyword mnemonic (pack-owned, never model-improvised).
    if entry.get("keyword_en"):
        return IntroducePlan(
            key=key,
            rule_id="R-E",
            scaffold_type="keyword",
            scaffold_payload={"keyword": entry["keyword_en"]},
            forbid_cluster_with=forbid,
        )
    # R-D fallback: single ≤6-word L1 micro-gloss, first exposure only.
    return IntroducePlan(
        key=key,
        rule_id="R-D",
        scaffold_type="gloss",
        scaffold_payload={"gloss": gloss, "format": f"**{key}** ({gloss})"},
        forbid_cluster_with=forbid,
    )


def plan_instructions(plan: IntroducePlan) -> str:
    """Teacher-facing INTRODUCE block realizing the plan (model performs)."""
    p = plan.scaffold_payload or {}
    if plan.scaffold_type == "cognate":
        core = (
            f"INTRODUCE (one item, rule {plan.rule_id}): present "
            f"**{plan.key}** anchored to the English cognate "
            f"'{p.get('anchor')}' (≤6 English words for the anchor; no other "
            "English)."
        )
    elif plan.scaffold_type == "image":
        core = (
            f"INTRODUCE (one item, rule {plan.rule_id}): present "
            f"**{plan.key}** — an image of {plan.key} is attached; the "
            "caption is the Spanish form. No L1 unless the learner fails."
        )
    elif plan.scaffold_type == "keyword":
        core = (
            f"INTRODUCE (one item, rule {plan.rule_id}): present "
            f"**{plan.key}** with the memory keyword '{p.get('keyword')}' "
            "(≤6 English words; no other English)."
        )
    else:
        core = (
            f"INTRODUCE (one item, rule {plan.rule_id}): present "
            f"**{plan.key}** — give the gloss format {p.get('format')} "
            "exactly once, then Spanish only."
        )
    lines = [
        core,
        "Model it in one short sentence, then a simple comprehension check "
        "or try.",
    ]
    if plan.forbid_cluster_with:
        lines.append(
            "Do NOT also introduce: "
            + ", ".join(plan.forbid_cluster_with)
            + "."
        )
    lines.append("Introduce NOTHING else new this turn.")
    return " ".join(lines)
