"""Teach assets: images bound to forms/concepts for association learning.

Pedagogy: show a referent (wave → Hola) same turn as the Spanish model.
See docs/pedagogy-contract.md § visual_image and docs/new-teacher-plan.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .plan_card import PlanCard

ASSETS_DIR = Path(__file__).resolve().parent / "web_static" / "teach_assets"
MANIFEST_PATH = ASSETS_DIR / "manifest.json"
# URL path served by FastAPI StaticFiles mount /static
STATIC_URL_PREFIX = "/static/teach_assets"

# concept_id → metadata (also loadable from manifest.json)
DEFAULT_CATALOG: dict[str, dict[str, str]] = {
    "hola": {
        "file": "hola.jpg",
        "form": "Hola",
        "caption": "greeting — hello",
    },
    "estoy_bien": {
        "file": "estoy_bien.jpg",
        "form": "Estoy bien",
        "caption": "I am fine / I am well",
    },
}


def load_catalog() -> dict[str, dict[str, str]]:
    cat = dict(DEFAULT_CATALOG)
    if MANIFEST_PATH.exists():
        try:
            data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict) and v.get("file"):
                        cat[str(k)] = {
                            "file": str(v["file"]),
                            "form": str(v.get("form") or k),
                            "caption": str(v.get("caption") or ""),
                        }
        except (json.JSONDecodeError, OSError):
            pass
    return cat


def resolve_concept(concept: str | None) -> dict[str, Any] | None:
    """Return public teach asset for a concept id, or None if missing."""
    if not concept:
        return None
    key = str(concept).strip().lower().replace(" ", "_")
    cat = load_catalog()
    meta = cat.get(key)
    if not meta:
        return None
    path = ASSETS_DIR / meta["file"]
    if not path.is_file():
        return None
    return {
        "concept": key,
        "form": meta.get("form") or key,
        "caption": meta.get("caption") or "",
        "url": f"{STATIC_URL_PREFIX}/{meta['file']}",
        "file": meta["file"],
    }


def pick_image_concept(card: PlanCard) -> str | None:
    """Choose primary image concept for this plan (association priority)."""
    if card.image_concept:
        if resolve_concept(card.image_concept):
            return card.image_concept
    # Prefer greeting on diagnostic / hola in concepts
    concepts = list(card.targets.concepts or [])
    for c in concepts:
        if resolve_concept(c):
            # Prefer hola when both present (user request: wave = greeting)
            pass
    if "hola" in concepts and resolve_concept("hola"):
        return "hola"
    for c in concepts:
        if resolve_concept(c):
            return c
    # Infer from models text
    blob = " ".join(card.models or []).lower()
    if "hola" in blob and resolve_concept("hola"):
        return "hola"
    if "estoy bien" in blob and resolve_concept("estoy_bien"):
        return "estoy_bien"
    return None


def assets_for_plan(card: PlanCard) -> list[dict[str, Any]]:
    """List of teach images for UI (primary first)."""
    primary = pick_image_concept(card)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    if primary:
        a = resolve_concept(primary)
        if a:
            out.append(a)
            seen.add(a["concept"])
    # Optional second asset for multi-model turns (estoy after hola)
    for c in card.targets.concepts or []:
        if c in seen:
            continue
        a = resolve_concept(c)
        if a:
            out.append(a)
            seen.add(a["concept"])
            if len(out) >= 2:
                break
    return out
