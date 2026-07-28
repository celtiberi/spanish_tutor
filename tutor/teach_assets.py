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
# Image-worthy lexicon (concrete referents / gestures — not abstract grammar)
# ---------------------------------------------------------------------------

# visual: how strongly a picture helps (0–1). Used for ranking + rate limits.
# kind: gesture | state | person | place | object | food | activity
CONCEPT_LEXICON: dict[str, dict[str, Any]] = {
    "hola": {
        "form": "Hola",
        "caption": "greeting — hello / wave",
        "visual": 0.95,
        "kind": "gesture",
        "aliases": ("hola", "hello", "hi ", "buenos dias", "buenas"),
        "prompt": (
            "Friendly educational illustration: person waving hello. "
            "No text, no letters. Flat illustration, warm colors."
        ),
        "file": "hola.jpg",
    },
    "estoy_bien": {
        "form": "Estoy bien",
        "caption": "I am fine / feeling well",
        "visual": 0.85,
        "kind": "state",
        "aliases": ("estoy bien", "estoy muy bien", "todo bien"),
        "prompt": (
            "Friendly educational illustration: person looking fine and at ease, "
            "thumbs up or calm smile. No text. Flat illustration, warm colors."
        ),
        "file": "estoy_bien.jpg",
    },
    "me_llamo": {
        "form": "Me llamo…",
        "caption": "my name is… (this is me)",
        "visual": 0.9,
        "kind": "person",
        "aliases": ("me llamo", "como te llamas", "cómo te llamas", "my name"),
        "prompt": (
            "Friendly educational illustration: person pointing to own chest "
            "(this is me / my name). No text. Flat illustration, warm colors."
        ),
        "file": "me_llamo.jpg",
    },
    "soy_de": {
        "form": "Soy de…",
        "caption": "I am from… (origin / place)",
        "visual": 0.8,
        "kind": "place",
        "aliases": ("soy de", "de donde eres", "dónde eres", "donde eres", "from"),
        "prompt": (
            "Friendly educational illustration: simple world map with a person "
            "pointing to a place (I am from here). No text, no country names. "
            "Flat illustration, warm colors."
        ),
    },
    "cafe": {
        "form": "el café",
        "caption": "coffee",
        "visual": 0.95,
        "kind": "food",
        "aliases": ("café", "cafe", "coffee"),
        "prompt": (
            "Friendly educational illustration: a cup of coffee on a table. "
            "No text. Flat illustration, warm colors."
        ),
    },
    "bote": {
        "form": "el bote",
        "caption": "boat",
        "visual": 0.95,
        "kind": "object",
        "aliases": ("bote", "barco", "boat"),
        "prompt": (
            "Friendly educational illustration: a small boat on calm water. "
            "No text. Flat illustration, warm colors."
        ),
    },
    "musica": {
        "form": "la música",
        "caption": "music",
        "visual": 0.85,
        "kind": "activity",
        "aliases": ("música", "musica", "music"),
        "prompt": (
            "Friendly educational illustration: person listening to music with "
            "notes floating nearby. No text. Flat illustration, warm colors."
        ),
    },
    "comida": {
        "form": "la comida",
        "caption": "food / meal",
        "visual": 0.9,
        "kind": "food",
        "aliases": ("comida", "food", "comer"),
        "prompt": (
            "Friendly educational illustration: a simple tasty meal on a plate. "
            "No text. Flat illustration, warm colors."
        ),
    },
    "me_gusta": {
        "form": "Me gusta…",
        "caption": "I like… (preference)",
        "visual": 0.7,
        "kind": "state",
        "aliases": ("me gusta", "te gusta", "qué te gusta"),
        "prompt": (
            "Friendly educational illustration: person smiling happily at something "
            "they like (heart or warm expression). No text. Flat illustration."
        ),
    },
    "rio": {
        "form": "el río",
        "caption": "river",
        "visual": 0.9,
        "kind": "place",
        "aliases": ("río", "rio", "river"),
        "prompt": (
            "Friendly educational illustration: a calm river landscape. "
            "No text. Flat illustration, warm colors."
        ),
    },
}

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


def _norm_key(concept: str | None) -> str:
    if not concept:
        return ""
    s = str(concept).strip().lower()
    s = (
        s.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    s = s.replace(" ", "_").replace("…", "").replace(".", "")
    # strip el_/la_ prefix noise
    if s.startswith("el_"):
        s = s[3:]
    if s.startswith("la_"):
        s = s[3:]
    return s


def concept_meta(concept: str | None) -> dict[str, Any]:
    key = _norm_key(concept)
    if not key:
        return {}
    if key in CONCEPT_LEXICON:
        return dict(CONCEPT_LEXICON[key])
    # alias reverse lookup
    for k, meta in CONCEPT_LEXICON.items():
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
    if key in CONCEPT_LEXICON:
        return key
    for k, meta in CONCEPT_LEXICON.items():
        for a in meta.get("aliases") or ():
            an = _norm_key(a)
            if key == an or key in an or an in key:
                return k
    if is_image_worthy(key):
        return key
    return None


def concept_in_text(concept: str | None, text: str) -> bool:
    """Surface-form relevance: does this concept actually appear in text?

    Code-owned check (observe.word_present is boundary-safe for words and
    MWUs alike; no LLM). Used to guarantee an image can only bind a concept
    the current exchange actually contains. Incident 2026-07-28: a stale
    repair-target «hola» image attached to a digo/dices grammar question —
    an absent image beats a wrong one (r5 multimodal law).
    """
    from .observe import word_present

    key = _norm_key(concept)
    if not key or not (text or "").strip():
        return False
    needles = {key.replace("_", " ")}
    meta = CONCEPT_LEXICON.get(key) or {}
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
    for k, meta in CONCEPT_LEXICON.items():
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
    for k, meta in CONCEPT_LEXICON.items():
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
    lex = CONCEPT_LEXICON.get(key) or {}
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
    lex = CONCEPT_LEXICON.get(key) or {}
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
    lex = CONCEPT_LEXICON.get(key) or {}
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
    lex = CONCEPT_LEXICON.get(key) or {}
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


def pick_image_concept(card: PlanCard) -> str | None:
    """Legacy helper: best candidate ignoring session policy."""
    cands = extract_concept_candidates(card)
    return cands[0] if cands else None


def assets_for_plan(
    card: PlanCard,
    *,
    images_shown: set[str] | list[str] | None = None,
    turns_since_image: int | None = None,
    session_turns: int = 0,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Images for this turn after intelligent decision. Disk only on hot path.

    Returns [] when the decision is "no image this turn".
    """
    decision = _decision_for_card(
        card,
        images_shown=images_shown,
        turns_since_image=turns_since_image,
        session_turns=session_turns,
        force=force,
    )
    try:
        setattr(card, "_image_decision", decision)
    except Exception:
        pass
    return _resolve_decision_assets(decision, images_shown=images_shown)


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
) -> tuple[list[dict[str, Any]], ImageDecision]:
    """Post-hoc image decision for AI-first path (no rules PlanCard agenda).

    Uses what the tutor *actually said* + open/blank/session facts — not a
    flashcard ladder. Returns (assets, decision).

    require_relevant_to: when not None, HARD relevance gate — any decided
    concept must be surface-present (concept_in_text) in that exchange text
    or NO image is served. Callers pass it on comprehension_repair / meta
    turns so the system can never serve SOME image when none is relevant
    (incident 2026-07-28: hola image on a digo/dices grammar question).
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
    assets = _resolve_decision_assets(decision, images_shown=images_shown)
    return assets, decision


def _decision_for_card(
    card: PlanCard,
    *,
    images_shown: set[str] | list[str] | None = None,
    turns_since_image: int | None = None,
    session_turns: int = 0,
    force: bool = False,
) -> ImageDecision:
    if force and card.image_concept:
        return ImageDecision(
            True,
            concept=_norm_key(card.image_concept),
            reason="forced",
            candidates=[_norm_key(card.image_concept)],
        )
    return decide_teach_image(
        card,
        images_shown=images_shown,
        turns_since_image=turns_since_image,
        session_turns=session_turns,
    )


def _resolve_decision_assets(
    decision: ImageDecision,
    *,
    images_shown: set[str] | list[str] | None = None,
) -> list[dict[str, Any]]:
    if not decision.want or not decision.concept:
        # Pre-warm likely next concepts in background only
        for c in decision.candidates[:2]:
            if c not in (images_shown or set()) and not cache_lookup(c):
                meta = CONCEPT_LEXICON.get(c) or {}
                warm_concept_background(
                    c,
                    form=meta.get("form") or c,
                    caption=meta.get("caption") or "",
                    prompt=meta.get("prompt") or "",
                )
        return []

    meta = CONCEPT_LEXICON.get(decision.concept) or {}
    # Same-turn: cache hit or generate on miss (no "if we have one")
    hit = ensure_asset(
        decision.concept,
        form=str(meta.get("form") or decision.concept),
        caption=str(meta.get("caption") or ""),
        prompt=str(meta.get("prompt") or ""),
        generate=True,
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
        "lexicon_size": len(CONCEPT_LEXICON),
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
