"""Teach assets: intelligent visual association + server-side image cache.

**When to show an image (not every turn):**
  Only when a concrete form/meaning pair is being *introduced* and a picture
  would bind referent ↔ Spanish better than English gloss. Free chat, recasts
  of abstract grammar, and already-shown concepts usually get no image.

**Cache-first, generate-on-miss when wanted:**
  Hit = disk lookup (fast). When the decision says we want an image and the
  file is missing, generate once (Gemini), write to cache, serve same-turn.
  No more "only if we pre-seeded it".

See docs/pedagogy-contract.md § visual_image and docs/new-teacher-plan.md.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .plan_card import PlanCard, PlanTargets
# Phase 2 (docs/reviews-architecture-refactor.md): the old local _norm_key is
# now the NAMED policy textnorm.fold_asset_key (5-vowel fold, ñ→n, space→_,
# el_/la_ strip). Aliased to keep the ~15 historical call sites readable;
# the byte-exact semantics are pinned — changing them orphans cached images.
from .textnorm import fold_asset_key as _norm_key

# Bundled + runtime cache live under static so FastAPI can serve them.
ASSETS_DIR = Path(__file__).resolve().parent / "web_static" / "teach_assets"
CACHE_DIR = ASSETS_DIR / "cache"
INDEX_PATH = ASSETS_DIR / "cache_index.json"
MANIFEST_PATH = ASSETS_DIR / "manifest.json"
STATIC_URL_PREFIX = "/static/teach_assets"

def _generate_on_miss_flag() -> bool:
    explicit = (os.environ.get("TEACH_IMAGE_GENERATE") or "").strip().lower()
    if explicit in ("0", "false", "off", "no"):
        return False
    if explicit in ("1", "true", "yes", "on"):
        return True
    # Auto when Gemini key present (generator still required)
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


GENERATE_ON_MISS = _generate_on_miss_flag()

# ---------------------------------------------------------------------------
# Pack asset sidecar (Phase 5, docs/reviews-architecture-refactor.md;
# PEDAGOGY §1.1a).  Asset metadata lives in <pack>/asset_sidecar.json keyed
# by association-table keys — the sidecar may attach metadata to pack
# concepts but must NOT invent a second concept list: every sidecar key is
# validated against the association table plus the checked-in migration
# deprecation list.  Since batch 2 (2026-07-29) the sidecar is the SOLE
# asset-metadata source — the in-code CONCEPT_LEXICON is deleted (batch 1
# proved the sidecar byte-identical to it before the flip).
#
# Imageable-vs-sidecar ruling (batch 2, adjudicated): the association
# table's `imageable` field answers "can THIS concept be dual-coded for
# MEANING" and governs image SELECTION (the introduce R-B list derives
# from imageable:true entries; the guard-6/association mode lists died
# with the mode router, 2026-08-03).  The sidecar answers the different
# question "do we have an ASSET" — it may carry assets for
# imageable:false concepts (hola's greeting illustration) without ever
# widening selection.  Those assets reach the learner only through code-
# owned channels with their own justification — the blank-open «hola»
# image is SCENE-SETTING for a true-zero learner
# (turn_pipeline.stage_fallback_image), not R-B meaning-binding.
# ---------------------------------------------------------------------------

SIDECAR_FILENAME = "asset_sidecar.json"
DEPRECATIONS_FILENAME = "migration_deprecations.json"

_SIDECAR_REQUIRED = ("form", "caption", "visual", "kind", "aliases", "image_prompt")
_SIDECAR_ALLOWED = frozenset(_SIDECAR_REQUIRED) | {"file"}


def load_migration_deprecations(pack_dir: Path | str) -> dict[str, dict[str, Any]]:
    """``<pack_dir>/migration_deprecations.json`` — §1.1a migration escape
    hatch: concepts deliberately NOT (yet) association-table keys, each with
    a recorded reason.  Missing file → {} (nothing deprecated).  Keys
    starting with "_" are file-level comments, skipped."""
    path = Path(pack_dir) / DEPRECATIONS_FILENAME
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{DEPRECATIONS_FILENAME}: top level must be an object")
    return {
        k: v
        for k, v in raw.items()
        if isinstance(k, str) and not k.startswith("_") and isinstance(v, dict)
    }


def load_asset_sidecar(pack_dir: Path | str) -> dict[str, dict[str, Any]]:
    """Load and validate ``<pack_dir>/asset_sidecar.json`` (raw, table-key
    keyed).  Raises ValueError listing ALL problems when an entry violates
    the schema, or when a key is neither an association-table key nor on the
    migration deprecation list (a sidecar must never mint concepts).  Keys
    starting with "_" are file-level comments, skipped."""
    from .association_table import load_association_table

    path = Path(pack_dir) / SIDECAR_FILENAME
    if not path.exists():
        raise FileNotFoundError(f"No {SIDECAR_FILENAME} in {pack_dir}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{SIDECAR_FILENAME}: top level must be an object")
    table = load_association_table(pack_dir)
    deprecated = load_migration_deprecations(pack_dir)

    problems: list[str] = []
    out: dict[str, dict[str, Any]] = {}
    for key, entry in raw.items():
        if isinstance(key, str) and key.startswith("_"):
            continue
        if not isinstance(key, str) or not key.strip():
            problems.append(f"{key!r}: key must be a non-empty string")
            continue
        if key not in table and key not in deprecated:
            problems.append(
                f"{key}: not an association-table key and not on the "
                f"{DEPRECATIONS_FILENAME} list (sidecars attach metadata; "
                "they never mint concepts)"
            )
        if not isinstance(entry, dict):
            problems.append(f"{key}: entry must be an object")
            continue
        for field_name in ("form", "caption", "kind", "image_prompt"):
            v = entry.get(field_name)
            if not isinstance(v, str) or not v.strip():
                problems.append(f"{key}: {field_name} must be a non-empty string")
        visual = entry.get("visual")
        if not isinstance(visual, (int, float)) or isinstance(visual, bool) or not (
            0.0 <= float(visual) <= 1.0
        ):
            problems.append(f"{key}: visual must be a number in [0, 1]")
        aliases = entry.get("aliases")
        if not isinstance(aliases, list) or not all(
            isinstance(a, str) and a for a in aliases
        ):
            problems.append(f"{key}: aliases must be a list of non-empty strings")
        file_v = entry.get("file")
        if file_v is not None and (not isinstance(file_v, str) or not file_v.strip()):
            problems.append(f"{key}: file must be a non-empty string when present")
        unknown = set(entry) - _SIDECAR_ALLOWED
        if unknown:
            problems.append(f"{key}: unknown fields {sorted(unknown)}")
        out[key] = entry
    if problems:
        raise ValueError(
            f"{SIDECAR_FILENAME} schema errors ({len(problems)}):\n"
            + "\n".join(f"- {p}" for p in problems)
        )
    return out


def sidecar_lexicon(pack_dir: Path | str) -> dict[str, dict[str, Any]]:
    """Sidecar as a lexicon-shaped dict (the deleted CONCEPT_LEXICON's
    shape) keyed by fold_asset_key of the table key (= the legacy asset id,
    so cached image filenames keep resolving).  ``image_prompt`` maps to the
    historical ``prompt`` slot; aliases become tuples; ``file`` rides only
    when present."""
    out: dict[str, dict[str, Any]] = {}
    for key, entry in load_asset_sidecar(pack_dir).items():
        meta: dict[str, Any] = {
            "form": entry["form"],
            "caption": entry["caption"],
            "visual": float(entry["visual"]),
            "kind": entry["kind"],
            "aliases": tuple(entry["aliases"]),
            "prompt": entry["image_prompt"],
        }
        if entry.get("file"):
            meta["file"] = entry["file"]
        out[_norm_key(key)] = meta
    return out


_sidecar_overlay: dict[str, dict[str, Any]] | None = None


def _lexicon() -> dict[str, dict[str, Any]]:
    """Effective asset lexicon = the pack sidecar, loaded once (SOLE source
    since Phase 5 batch 2 — the in-code CONCEPT_LEXICON is deleted).  A
    missing/invalid sidecar degrades to {} — never a crash (association-
    table posture): images lose curated metadata and fall back to
    is_image_worthy's bare-token heuristic + _default_prompt, while cached
    files keep resolving through the manifest / cache index."""
    global _sidecar_overlay
    if _sidecar_overlay is None:
        try:
            from .config import DEFAULT_PACK_DIR

            _sidecar_overlay = sidecar_lexicon(DEFAULT_PACK_DIR)
        except Exception:
            _sidecar_overlay = {}
    return dict(_sidecar_overlay)


# Forms that look like concepts but should NOT get images alone.
ABSTRACT_SKIP = frozenset({
    "present_estar_person",
    "present_ser",
    "error",
    "natural spanish",
    "(natural spanish)",
})

# Minimum visual score to bother generating/showing
MIN_VISUAL = 0.65

# Don't show another image the very next turn unless new highly-visual concept
RATE_LIMIT_TURNS = 1
HIGHLY_VISUAL = 0.9

_lock = threading.Lock()
_index: dict[str, Any] | None = None
_generator: Callable[[str, str, Path], bool] | None = None
_warm_inflight: set[str] = set()


@dataclass
class ImageDecision:
    """Result of intelligent 'should we show an image this turn?'"""

    want: bool
    concept: str | None = None
    reason: str = ""
    candidates: list[str] = field(default_factory=list)
    visual_score: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "want": self.want,
            "concept": self.concept,
            "reason": self.reason,
            "candidates": list(self.candidates),
            "visual_score": self.visual_score,
        }


def concept_meta(concept: str | None) -> dict[str, Any]:
    key = _norm_key(concept)
    if not key:
        return {}
    lexicon = _lexicon()
    if key in lexicon:
        return dict(lexicon[key])
    # alias reverse lookup
    for k, meta in lexicon.items():
        if key == k:
            return dict(meta)
        for a in meta.get("aliases") or ():
            if _norm_key(a) == key or key in _norm_key(a):
                return dict(meta) | {"_key": k}
    return {}


def is_image_worthy(concept: str | None) -> bool:
    key = _norm_key(concept)
    if not key or key in ABSTRACT_SKIP:
        return False
    meta = concept_meta(key)
    if not meta:
        # unknown dynamic concept: only if looks like a concrete token
        if re.fullmatch(r"[a-z][a-z0-9_]{1,24}", key) and "_" not in key[:2]:
            # bare unknown noun — allow with medium visual if short
            return len(key) >= 3 and not key.startswith("ip_")
        return False
    return float(meta.get("visual") or 0) >= MIN_VISUAL


def visual_score(concept: str | None) -> float:
    meta = concept_meta(concept)
    if meta:
        return float(meta.get("visual") or 0)
    key = _norm_key(concept)
    if is_image_worthy(key):
        return 0.7  # unknown but plausible concrete
    return 0.0


def resolve_concept_id(raw: str | None) -> str | None:
    """Map free text / alias → canonical concept id, or None if not worthy."""
    key = _norm_key(raw)
    if not key or key in ABSTRACT_SKIP:
        return None
    lexicon = _lexicon()
    if key in lexicon:
        return key
    for k, meta in lexicon.items():
        for a in meta.get("aliases") or ():
            an = _norm_key(a)
            if key == an or key in an or an in key:
                return k
    if is_image_worthy(key):
        return key
    return None


def concept_in_text(concept: str | None, text: str) -> bool:
    """Surface-form relevance: does this concept actually appear in text?

    Code-owned check (textnorm.word_present is boundary-safe for words and
    MWUs alike; no LLM). Used to guarantee an image can only bind a concept
    the current exchange actually contains. Incident 2026-07-28: a stale
    repair-target «hola» image attached to a digo/dices grammar question —
    an absent image beats a wrong one (r5 multimodal law).
    """
    from .textnorm import word_present

    key = _norm_key(concept)
    if not key or not (text or "").strip():
        return False
    needles = {key.replace("_", " ")}
    meta = _lexicon().get(key) or {}
    for a in meta.get("aliases") or ():
        a = (a or "").strip()
        if a:
            needles.add(a)
    form = str(meta.get("form") or "").strip(" …._")
    if form:
        needles.add(form)
    return any(word_present(n, text) for n in needles)


def extract_concept_candidates(card: PlanCard) -> list[str]:
    """Pull image-worthy concept ids from the plan (order = preference).

    Recasts only use *explicit* targets/image_concept — not incidental nouns
    in model example lines (e.g. "Estoy en el bote" must not force a boat pic
    on a person-agreement recast).
    """
    found: list[str] = []
    seen: set[str] = set()
    move = (card.move or "").lower()

    def add(raw: str | None) -> None:
        cid = resolve_concept_id(raw)
        if cid and cid not in seen and is_image_worthy(cid):
            seen.add(cid)
            found.append(cid)

    add(card.image_concept)
    for c in card.targets.concepts or []:
        add(c)

    # Recast / form repair: stick to explicit targets only
    if move == "recast_retry":
        return found

    blob = " ".join(
        [
            *(card.models or []),
            card.try_prompt or "",
            card.english_frame or "",
            card.reason or "",
        ]
    ).lower()
    for k, meta in _lexicon().items():
        for a in meta.get("aliases") or ():
            if a.lower() in blob:
                add(k)
                break
        if k.replace("_", " ") in blob:
            add(k)
    return found


def decide_teach_image(
    card: PlanCard,
    *,
    images_shown: set[str] | list[str] | None = None,
    turns_since_image: int | None = None,
    session_turns: int = 0,
) -> ImageDecision:
    """Intelligent gate: do we attach a teach image this turn?

    Principles:
    - Image = form↔meaning association for a *concrete* referent, not wallpaper.
    - Prefer first introduction of a concept this session.
    - Skip free chat / loop recovery / pure recast of abstract person agreement.
    - Rate-limit: avoid an image every single turn.
    """
    shown = set(images_shown or [])
    since = 0 if turns_since_image is None else int(turns_since_image)
    candidates = extract_concept_candidates(card)
    reason_l = (card.reason or "").lower()
    move = (card.move or "").lower()
    phase = (card.phase or "").lower()

    # Hard no: loop recovery, praise-only energy
    if "loop" in reason_l:
        return ImageDecision(False, reason="skip_loop_recovery", candidates=candidates)
    if move == "praise_continue":
        return ImageDecision(False, reason="skip_praise", candidates=candidates)

    if not candidates:
        return ImageDecision(False, reason="no_image_worthy_concept", candidates=[])

    # Planner primary suggestion wins: don't auto-substitute a secondary
    # concept (hola already shown → shouldn't wallpaper estoy_bien).
    primary = resolve_concept_id(card.image_concept)
    if primary and move != "associate" and phase != "associate":
        candidates = [primary] + [c for c in candidates if c != primary]
        # Decision only considers primary unless it is not image-worthy
        if is_image_worthy(primary):
            candidates = [primary]

    # Prefer concepts not yet shown this session
    fresh = [c for c in candidates if c not in shown]
    pool = list(fresh)

    # Re-show only for explicit associate of same concept (rare)
    if not pool and move == "associate" and primary:
        pool = [primary]

    if not pool:
        return ImageDecision(
            False,
            reason="concepts_already_shown",
            candidates=candidates,
        )

    # Rank by visual score
    pool_sorted = sorted(pool, key=lambda c: visual_score(c), reverse=True)
    best = pool_sorted[0]
    score = visual_score(best)

    if score < MIN_VISUAL:
        return ImageDecision(
            False,
            concept=best,
            reason="visual_score_low",
            candidates=candidates,
            visual_score=score,
        )

    # Pedagogical triggers
    want = False
    why = ""

    if move == "recast_retry":
        # Person-agreement fixes are not picture moments; only concrete nouns
        if score >= HIGHLY_VISUAL and fresh:
            want, why = True, "recast_highly_visual"
        else:
            want, why = False, "recast_no_visual_need"
    elif move == "associate":
        want, why = True, "move_associate"
    elif phase == "associate":
        want, why = True, "phase_associate"
    elif reason_l in ("comm_open",) or (phase == "diagnostic" and "open" in reason_l):
        # First open: wave hello helps meaning without English walls
        want, why = True, "diagnostic_open"
    elif reason_l in ("english_lifeline",) or move == "english_frame":
        want, why = True, "english_lifeline_scaffold"
    elif phase == "teach_form" and fresh and score >= 0.8:
        want, why = True, "new_form_intro"
    elif move == "model_try" and fresh and score >= 0.8:
        # Strong concrete intro (name gesture, coffee cup, boat…)
        want, why = True, "new_concrete_model"
    elif "chat_ask_name" in reason_l or "chat_ask_how" in reason_l:
        want, why = True, "first_social_form"
    elif any(x in reason_l for x in ("gusta", "cafe", "bote", "origin", "soy")) and fresh:
        if score >= 0.8:
            want, why = True, "topic_concrete_intro"
        else:
            want, why = False, "topic_weak_visual"
    else:
        want, why = False, "no_pedagogy_trigger"

    # Rate limit: avoid an image every consecutive turn (unless associate /
    # highly visual new concept). since = turns since last image was shown.
    if want and session_turns > 0 and since <= RATE_LIMIT_TURNS:
        if score < HIGHLY_VISUAL and move != "associate":
            return ImageDecision(
                False,
                concept=best,
                reason="skip_rate_limit",
                candidates=candidates,
                visual_score=score,
            )

    if not want:
        return ImageDecision(
            False,
            concept=best,
            reason=why,
            candidates=candidates,
            visual_score=score,
        )

    return ImageDecision(
        True,
        concept=best,
        reason=why,
        candidates=candidates,
        visual_score=score,
    )


# ---------------------------------------------------------------------------
# Disk cache (unchanged contract)
# ---------------------------------------------------------------------------

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


def generation_ready() -> bool:
    """A generator is registered — explicit generate=True calls can produce
    images. Same fact cache_stats exposes as generator_registered; callers
    use it to note WHY a miss produced no image (never silently)."""
    return _generator is not None


def load_catalog() -> dict[str, dict[str, str]]:
    """Seed lexicon + manifest + cache index (metadata only)."""
    cat: dict[str, dict[str, str]] = {}
    for k, meta in _lexicon().items():
        cat[k] = {
            "file": str(meta.get("file") or f"cache/{k}.jpg"),
            "form": str(meta.get("form") or k),
            "caption": str(meta.get("caption") or ""),
            "prompt": str(meta.get("prompt") or ""),
        }
    if MANIFEST_PATH.exists():
        try:
            data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict) and v.get("file"):
                        key = _norm_key(k)
                        cat[key] = {
                            "file": str(v["file"]),
                            "form": str(v.get("form") or k),
                            "caption": str(v.get("caption") or ""),
                            "prompt": str(
                                v.get("prompt")
                                or cat.get(key, {}).get("prompt")
                                or ""
                            ),
                        }
        except (json.JSONDecodeError, OSError):
            pass
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
    paths: list[Path] = []
    idx = _load_index()
    ent = (idx.get("entries") or {}).get(key)
    if isinstance(ent, dict) and ent.get("file"):
        paths.append(ASSETS_DIR / str(ent["file"]))
    paths.append(CACHE_DIR / f"{key}.jpg")
    paths.append(CACHE_DIR / f"{key}.png")
    paths.append(CACHE_DIR / f"{key}.webp")
    if meta and meta.get("file"):
        f = meta["file"]
        paths.append(ASSETS_DIR / f)
        if not str(f).startswith("cache/"):
            paths.append(CACHE_DIR / Path(f).name)
    for ext in (".jpg", ".png", ".webp"):
        paths.append(ASSETS_DIR / f"{key}{ext}")
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        s = str(p.resolve()) if p.exists() else str(p)
        if s not in seen:
            seen.add(s)
            out.append(p)
    return out


def cache_lookup(concept: str | None) -> dict[str, Any] | None:
    """**Server cache hit only.** Never generates. Never waits on AI."""
    key = _norm_key(concept)
    if not key:
        return None
    cat = load_catalog()
    meta = cat.get(key) or {}
    # merge lexicon form/caption
    lex = _lexicon().get(key) or {}
    for path in _candidate_paths(key, meta if meta else None):
        if path.is_file() and path.stat().st_size > 0:
            try:
                rel = path.relative_to(ASSETS_DIR).as_posix()
            except ValueError:
                rel = path.name
            form = meta.get("form") or lex.get("form") or key
            caption = meta.get("caption") or lex.get("caption") or ""
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
    lex = _lexicon().get(key) or {}
    _record_hit(
        key,
        rel,
        form=form or lex.get("form") or key,
        caption=caption or lex.get("caption") or "",
        prompt=prompt,
        source=source,
    )
    return cache_lookup(key)


def _default_prompt(key: str, form: str) -> str:
    lex = _lexicon().get(key) or {}
    if lex.get("prompt"):
        return str(lex["prompt"])
    return (
        f"Friendly educational illustration for Spanish learning, concept "
        f"'{form or key}'. Clear visual meaning, no text, no letters, "
        f"flat illustration, warm colors."
    )


def ensure_asset(
    concept: str,
    *,
    form: str = "",
    caption: str = "",
    prompt: str = "",
    generate: bool | None = None,
) -> dict[str, Any] | None:
    """Cache-first; on miss generate same-turn when enabled + generator registered.

    Pedagogy path (association / comprehension_repair): pass generate=True so
    the image appears *this* turn, not after a background warm.
    """
    hit = cache_lookup(concept)
    if hit:
        hit["cache"] = "hit"
        return hit

    do_gen = GENERATE_ON_MISS if generate is None else bool(generate)
    key = _norm_key(concept)
    if not key:
        return None
    cat = load_catalog()
    meta = cat.get(key) or {}
    lex = _lexicon().get(key) or {}
    form = form or meta.get("form") or lex.get("form") or key
    caption = caption or meta.get("caption") or lex.get("caption") or form
    prompt = prompt or meta.get("prompt") or lex.get("prompt") or _default_prompt(key, form)

    if not do_gen or _generator is None:
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # Generator may rewrite suffix (.png vs .jpg); check all after.
    dest = CACHE_DIR / f"{key}.png"
    try:
        ok = bool(_generator(key, prompt, dest))
    except Exception:
        ok = False
    if not ok:
        return None

    # Find whatever file the generator actually wrote
    written: Path | None = None
    for cand in (dest, dest.with_suffix(".jpg"), dest.with_suffix(".webp"), CACHE_DIR / f"{key}.png", CACHE_DIR / f"{key}.jpg"):
        if cand.is_file() and cand.stat().st_size > 0:
            written = cand
            break
    if written is None:
        return None

    try:
        rel = written.relative_to(ASSETS_DIR).as_posix()
    except ValueError:
        rel = f"cache/{written.name}"
    _record_hit(
        key,
        rel,
        form=form,
        caption=caption,
        prompt=prompt,
        source="generated",
    )
    out = cache_lookup(key)
    if out:
        out["cache"] = "miss_generated"
    return out


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


def resolve_concept(concept: str | None) -> dict[str, Any] | None:
    return cache_lookup(concept)


def assets_for_ai_turn(
    *,
    is_open: bool = False,
    blank_sheet: bool = False,
    learner: str = "",
    tutor_models: list[str] | None = None,
    tutor_try: str = "",
    tutor_ack: str = "",
    signals: list[str] | set[str] | None = None,
    images_shown: set[str] | list[str] | None = None,
    turns_since_image: int | None = None,
    session_turns: int = 0,
    require_relevant_to: str | None = None,
    generate: bool = True,
) -> tuple[list[dict[str, Any]], ImageDecision]:
    """Post-hoc image decision for AI-first path (no rules PlanCard agenda).

    Uses what the tutor *actually said* + open/blank/session facts — not a
    flashcard ladder. Returns (assets, decision).

    tutor_models contract (Proposal B, 2026-07-29 — CHAR-BUG-006): only the
    tutor's ACTUAL prior output may ride here.  Authored scene scripts
    (scene input suggested lines / the scene decision's targets copy) are
    BANNED — they are direction for the model, not evidence of the turn's
    content.  The reply-path caller (stage_fallback_image) passes no
    tutor_models at all: its base is decision.image_concept (primary, owned
    by mode attach) + learner text (secondary).

    require_relevant_to: when not None, HARD relevance gate — any decided
    concept must be surface-present (concept_in_text) in that exchange text
    or NO image is served. Callers pass it on comprehension_repair / meta
    turns so the system can never serve SOME image when none is relevant
    (incident 2026-07-28: hola image on a digo/dices grammar question).

    generate=False (audit (e) 2026-07-28, latency law): cache lookup only on
    the reply path — a miss returns no assets instantly; the session owns
    the async warm + generation-miss visibility.
    """
    models = [m for m in (tutor_models or []) if m]
    sig = set(signals or [])
    concepts: list[str] = []
    image_concept = None
    phase = "chat_stretch"
    move = "model_try"
    reason = "ai_turn"

    if is_open or (blank_sheet and not (learner or "").strip()):
        phase, move, reason = "diagnostic", "model_try", "comm_open"
        image_concept = "hola"
        concepts = ["hola", "estoy_bien"]
    elif "loop_complaint" in sig:
        phase, move, reason = "chat_stretch", "model_try", "loop_recovery"
    else:
        # Infer from tutor output + light signals (association only)
        blob = " ".join(models + [tutor_try or "", tutor_ack or "", learner or ""])
        soft = PlanCard(
            phase="chat_stretch",
            move="model_try",
            models=models or [blob[:80]],
            try_prompt=tutor_try or "",
            targets=PlanTargets(concepts=[]),
            reason="ai_turn_infer",
        )
        concepts = extract_concept_candidates(soft)
        # First-time social forms in tutor text
        low = blob.lower()
        if "me llamo" in low or "cómo te llamas" in low or "como te llamas" in low:
            concepts = ["me_llamo"] + [c for c in concepts if c != "me_llamo"]
            image_concept = "me_llamo"
            move, reason = "associate", "ai_name_form"
        elif concepts:
            # Prefer highest-visual concrete noun the tutor actually used
            concepts = sorted(concepts, key=lambda c: visual_score(c), reverse=True)
            image_concept = concepts[0]
            if visual_score(image_concept) >= 0.8:
                move, reason = "model_try", "ai_concrete_model"
            else:
                move, reason = "model_try", "ai_weak_visual"
        elif "estoy" in low and "hola" not in (images_shown or set()):
            pass  # wellbeing chat — no forced image

    card = PlanCard(
        phase=phase,
        move=move,
        models=models or ["…"],
        try_prompt=tutor_try or "continue",
        targets=PlanTargets(concepts=concepts),
        image_concept=image_concept,
        reason=reason,
        allow_new_topic=True,
    )
    decision = decide_teach_image(
        card,
        images_shown=images_shown,
        turns_since_image=turns_since_image,
        session_turns=session_turns,
    )
    if (
        require_relevant_to is not None
        and decision.want
        and not concept_in_text(decision.concept, require_relevant_to)
    ):
        decision = ImageDecision(
            False,
            concept=decision.concept,
            reason="skip_irrelevant_concept",
            candidates=decision.candidates,
            visual_score=decision.visual_score,
        )
    assets = _resolve_decision_assets(
        decision, images_shown=images_shown, generate=generate
    )
    return assets, decision


def _resolve_decision_assets(
    decision: ImageDecision,
    *,
    images_shown: set[str] | list[str] | None = None,
    generate: bool = True,
) -> list[dict[str, Any]]:
    if not decision.want or not decision.concept:
        # Pre-warm likely next concepts in background only
        for c in decision.candidates[:2]:
            if c not in (images_shown or set()) and not cache_lookup(c):
                meta = _lexicon().get(c) or {}
                warm_concept_background(
                    c,
                    form=meta.get("form") or c,
                    caption=meta.get("caption") or "",
                    prompt=meta.get("prompt") or "",
                )
        return []

    meta = _lexicon().get(decision.concept) or {}
    # generate=True: cache hit or generate on miss (same-turn). The reply
    # hot path passes generate=False (audit (e) 2026-07-28) — miss returns
    # [] instantly and the session warms the concept asynchronously.
    hit = ensure_asset(
        decision.concept,
        form=str(meta.get("form") or decision.concept),
        caption=str(meta.get("caption") or ""),
        prompt=str(meta.get("prompt") or ""),
        generate=generate,
    )
    if hit:
        return [{
            **hit,
            "decision_reason": decision.reason,
            "visual_score": decision.visual_score,
        }]
    return []


def cache_stats() -> dict[str, Any]:
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
        "lexicon_size": len(_lexicon()),
        "generate_on_miss": GENERATE_ON_MISS,
        "generator_registered": _generator is not None,
    }


def seed_index_from_disk() -> int:
    n = 0
    for key, meta in load_catalog().items():
        if cache_lookup(key):
            n += 1
            continue
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


try:
    seed_index_from_disk()
except Exception:
    pass
