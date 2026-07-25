"""Teach assets: server-side cached images for form↔meaning association.

**Cache-first (server, not browser):**
  resolve / assets_for_plan → disk only. Never blocks on AI image generation.
  ensure_asset / warm_concept → on miss only, generate once, write cache, reuse forever.

See docs/pedagogy-contract.md § visual_image and docs/new-teacher-plan.md.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

from .plan_card import PlanCard

# Bundled + runtime cache live under static so FastAPI can serve them.
ASSETS_DIR = Path(__file__).resolve().parent / "web_static" / "teach_assets"
CACHE_DIR = ASSETS_DIR / "cache"
INDEX_PATH = ASSETS_DIR / "cache_index.json"
MANIFEST_PATH = ASSETS_DIR / "manifest.json"
STATIC_URL_PREFIX = "/static/teach_assets"

# Optional live generation on cache miss (default off — pre-seeded assets).
# Set TEACH_IMAGE_GENERATE=1 to enable generator hook when registered.
GENERATE_ON_MISS = (
    os.environ.get("TEACH_IMAGE_GENERATE", "false").strip().lower()
    in ("1", "true", "yes", "on")
)

# concept_id → seed metadata (files in ASSETS_DIR root or cache/)
DEFAULT_CATALOG: dict[str, dict[str, str]] = {
    "hola": {
        "file": "hola.jpg",
        "form": "Hola",
        "caption": "greeting — hello",
        "prompt": (
            "Friendly educational illustration: person waving hello. "
            "No text. Flat illustration, warm colors."
        ),
    },
    "estoy_bien": {
        "file": "estoy_bien.jpg",
        "form": "Estoy bien",
        "caption": "I am fine / I am well",
        "prompt": (
            "Friendly educational illustration: person looking fine / at ease. "
            "No text. Flat illustration, warm colors."
        ),
    },
    "me_llamo": {
        "file": "me_llamo.jpg",
        "form": "Me llamo…",
        "caption": "my name is… (pointing to myself)",
        "prompt": (
            "Friendly educational illustration: person pointing to own chest "
            "(this is me / my name). No text. Flat illustration, warm colors."
        ),
    },
}

_lock = threading.Lock()
_index: dict[str, Any] | None = None
# Optional: Callable[[concept, prompt, dest_path], bool]
_generator: Callable[[str, str, Path], bool] | None = None
_warm_inflight: set[str] = set()


def _norm_key(concept: str | None) -> str:
    if not concept:
        return ""
    return str(concept).strip().lower().replace(" ", "_").replace("…", "")


def _load_index() -> dict[str, Any]:
    global _index
    if _index is not None:
        return _index
    with _lock:
        if _index is not None:
            return _index
        data: dict[str, Any] = {"version": 1, "entries": {}}
        if INDEX_PATH.exists():
            try:
                raw = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and isinstance(raw.get("entries"), dict):
                    data = raw
            except (json.JSONDecodeError, OSError):
                pass
        _index = data
        return _index


def _save_index() -> None:
    idx = _load_index()
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(
        json.dumps(idx, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def register_generator(fn: Callable[[str, str, Path], bool] | None) -> None:
    """Register server-side image generator: (concept, prompt, dest) -> ok."""
    global _generator
    _generator = fn


def load_catalog() -> dict[str, dict[str, str]]:
    """Seed catalog + manifest + cache index entries (metadata only)."""
    cat = {k: dict(v) for k, v in DEFAULT_CATALOG.items()}
    if MANIFEST_PATH.exists():
        try:
            data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict) and v.get("file"):
                        cat[_norm_key(k)] = {
                            "file": str(v["file"]),
                            "form": str(v.get("form") or k),
                            "caption": str(v.get("caption") or ""),
                            "prompt": str(v.get("prompt") or cat.get(_norm_key(k), {}).get("prompt") or ""),
                        }
        except (json.JSONDecodeError, OSError):
            pass
    # Cache index can add concepts created at runtime
    idx = _load_index()
    for k, ent in (idx.get("entries") or {}).items():
        if not isinstance(ent, dict):
            continue
        key = _norm_key(k)
        if key and key not in cat:
            cat[key] = {
                "file": str(ent.get("file") or f"cache/{key}.jpg"),
                "form": str(ent.get("form") or key),
                "caption": str(ent.get("caption") or ""),
                "prompt": str(ent.get("prompt") or ""),
            }
    return cat


def _candidate_paths(key: str, meta: dict[str, str] | None = None) -> list[Path]:
    """Ordered paths to look for a cached file (server disk)."""
    paths: list[Path] = []
    # 1) Explicit cache entry
    idx = _load_index()
    ent = (idx.get("entries") or {}).get(key)
    if isinstance(ent, dict) and ent.get("file"):
        paths.append(ASSETS_DIR / str(ent["file"]))
    # 2) Canonical cache path
    paths.append(CACHE_DIR / f"{key}.jpg")
    paths.append(CACHE_DIR / f"{key}.png")
    paths.append(CACHE_DIR / f"{key}.webp")
    # 3) Bundled / manifest file at assets root
    if meta and meta.get("file"):
        f = meta["file"]
        paths.append(ASSETS_DIR / f)
        if not str(f).startswith("cache/"):
            paths.append(CACHE_DIR / Path(f).name)
    # 4) Default names
    for ext in (".jpg", ".png", ".webp"):
        paths.append(ASSETS_DIR / f"{key}{ext}")
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        s = str(p.resolve()) if p.exists() else str(p)
        if s not in seen:
            seen.add(s)
            out.append(p)
    return out


def cache_lookup(concept: str | None) -> dict[str, Any] | None:
    """**Server cache hit only.** Never generates. Never waits on AI.

    Returns public asset dict or None if not on disk.
    """
    key = _norm_key(concept)
    if not key:
        return None
    cat = load_catalog()
    meta = cat.get(key) or {}
    for path in _candidate_paths(key, meta if meta else None):
        if path.is_file() and path.stat().st_size > 0:
            # Prefer path relative to ASSETS_DIR for URL
            try:
                rel = path.relative_to(ASSETS_DIR).as_posix()
            except ValueError:
                rel = path.name
            form = meta.get("form") or key
            caption = meta.get("caption") or ""
            # Index hit for next time
            _record_hit(key, rel, form=form, caption=caption, source="disk")
            return {
                "concept": key,
                "form": form,
                "caption": caption,
                "url": f"{STATIC_URL_PREFIX}/{rel}",
                "file": rel,
                "cache": "hit",
                "path": str(path),
            }
    return None


def _record_hit(
    key: str,
    rel_file: str,
    *,
    form: str = "",
    caption: str = "",
    prompt: str = "",
    source: str = "disk",
) -> None:
    with _lock:
        idx = _load_index()
        entries = idx.setdefault("entries", {})
        prev = entries.get(key) if isinstance(entries.get(key), dict) else {}
        entries[key] = {
            "file": rel_file,
            "form": form or prev.get("form") or key,
            "caption": caption or prev.get("caption") or "",
            "prompt": prompt or prev.get("prompt") or "",
            "source": source,
            "last_access": time.time(),
            "created": prev.get("created") or time.time(),
        }
        try:
            _save_index()
        except OSError:
            pass


def cache_put(
    concept: str,
    data: bytes,
    *,
    form: str = "",
    caption: str = "",
    prompt: str = "",
    ext: str = ".jpg",
    source: str = "generated",
) -> dict[str, Any] | None:
    """Write bytes into server cache. Overwrites only if force via new write."""
    key = _norm_key(concept)
    if not key or not data:
        return None
    if not ext.startswith("."):
        ext = f".{ext}"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    rel = f"cache/{key}{ext}"
    path = ASSETS_DIR / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    _record_hit(key, rel, form=form or key, caption=caption, prompt=prompt, source=source)
    return cache_lookup(key)


def ensure_asset(
    concept: str,
    *,
    form: str = "",
    caption: str = "",
    prompt: str = "",
    generate: bool | None = None,
) -> dict[str, Any] | None:
    """Cache-first: return hit immediately. Generate **only** on miss if enabled.

    Call this from warmers / admin — **not** on the hot tutor path if generate
    can be slow. Hot path should use ``cache_lookup`` / ``assets_for_plan``.
    """
    hit = cache_lookup(concept)
    if hit:
        hit["cache"] = "hit"
        return hit

    do_gen = GENERATE_ON_MISS if generate is None else generate
    key = _norm_key(concept)
    cat = load_catalog()
    meta = cat.get(key) or {}
    form = form or meta.get("form") or key
    caption = caption or meta.get("caption") or ""
    prompt = prompt or meta.get("prompt") or _default_prompt(key, form)

    if not do_gen or _generator is None:
        return None

    dest = CACHE_DIR / f"{key}.jpg"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        ok = _generator(key, prompt, dest)
    except Exception:
        ok = False
    if ok and dest.is_file() and dest.stat().st_size > 0:
        _record_hit(
            key,
            f"cache/{key}.jpg",
            form=form,
            caption=caption,
            prompt=prompt,
            source="generated",
        )
        out = cache_lookup(key)
        if out:
            out["cache"] = "miss_generated"
        return out
    return None


def warm_concept_background(concept: str, **kwargs: Any) -> None:
    """If missing from cache, generate in a daemon thread (never blocks turn)."""
    key = _norm_key(concept)
    if not key or cache_lookup(key):
        return
    if not GENERATE_ON_MISS or _generator is None:
        return
    with _lock:
        if key in _warm_inflight:
            return
        _warm_inflight.add(key)

    def _run() -> None:
        try:
            ensure_asset(key, generate=True, **kwargs)
        finally:
            with _lock:
                _warm_inflight.discard(key)

    threading.Thread(target=_run, name=f"teach-img-{key}", daemon=True).start()


def _default_prompt(key: str, form: str) -> str:
    return (
        f"Friendly educational illustration for Spanish learning, concept '{form or key}'. "
        f"Clear visual meaning, no text, no letters, flat illustration, warm colors."
    )


def resolve_concept(concept: str | None) -> dict[str, Any] | None:
    """Public resolve = **cache lookup only** (no generation)."""
    return cache_lookup(concept)


def pick_image_concept(card: PlanCard) -> str | None:
    """Choose primary image concept for this plan (must be cacheable)."""
    candidates: list[str] = []
    if card.image_concept:
        candidates.append(_norm_key(card.image_concept))
    concepts = [_norm_key(c) for c in (card.targets.concepts or [])]
    if "hola" in concepts:
        candidates.append("hola")
    candidates.extend(concepts)
    blob = " ".join(card.models or []).lower()
    if "hola" in blob:
        candidates.append("hola")
    if "estoy bien" in blob:
        candidates.append("estoy_bien")
    if "me llamo" in blob:
        candidates.append("me_llamo")

    seen: set[str] = set()
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        if cache_lookup(c):
            return c
    # Prefer requested even if not cached (warm later)
    if card.image_concept:
        return _norm_key(card.image_concept)
    return concepts[0] if concepts else None


def assets_for_plan(card: PlanCard) -> list[dict[str, Any]]:
    """Images for this turn: **disk cache only** — never waits on AI generation.

    Missing concepts may be warmed in the background if generation is enabled.
    """
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    wanted: list[str] = []

    primary = pick_image_concept(card)
    if primary:
        wanted.append(primary)
    for c in card.targets.concepts or []:
        wanted.append(_norm_key(c))
    if card.image_concept:
        wanted.append(_norm_key(card.image_concept))

    for c in wanted:
        if not c or c in seen:
            continue
        seen.add(c)
        hit = cache_lookup(c)
        if hit:
            out.append(hit)
            if len(out) >= 2:
                break
        else:
            # Do not block the tutor turn — optional background fill
            cat = load_catalog()
            meta = cat.get(c) or {}
            warm_concept_background(
                c,
                form=meta.get("form") or c,
                caption=meta.get("caption") or "",
                prompt=meta.get("prompt") or "",
            )
    return out


def cache_stats() -> dict[str, Any]:
    """Debug / health: what the server cache knows."""
    idx = _load_index()
    entries = idx.get("entries") or {}
    hits = 0
    missing = 0
    for key in load_catalog():
        if cache_lookup(key):
            hits += 1
        else:
            missing += 1
    return {
        "assets_dir": str(ASSETS_DIR),
        "cache_dir": str(CACHE_DIR),
        "indexed": len(entries),
        "catalog_hits": hits,
        "catalog_missing": missing,
        "generate_on_miss": GENERATE_ON_MISS,
        "generator_registered": _generator is not None,
    }


def seed_index_from_disk() -> int:
    """Register existing asset files into the cache index (idempotent)."""
    n = 0
    for key, meta in load_catalog().items():
        if cache_lookup(key):
            n += 1
            continue
        # try find file and index
        for path in _candidate_paths(key, meta):
            if path.is_file():
                try:
                    rel = path.relative_to(ASSETS_DIR).as_posix()
                except ValueError:
                    rel = path.name
                _record_hit(
                    key,
                    rel,
                    form=meta.get("form") or key,
                    caption=meta.get("caption") or "",
                    prompt=meta.get("prompt") or "",
                    source="seed",
                )
                n += 1
                break
    return n


# Seed index at import so first request is a pure hit
try:
    seed_index_from_disk()
except Exception:
    pass
