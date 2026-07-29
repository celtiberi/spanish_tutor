"""On-demand teach images via Gemini (generate once, cache forever).

Used when association / comprehension_repair needs a concept that is not yet
on disk. Hot path: cache_lookup first; miss → generate → cache_put.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from . import config
# Phase 5 batch 2: CONCEPT_LEXICON is deleted — the pack asset sidecar is
# the sole metadata source, read through teach_assets._lexicon().
from .teach_assets import _default_prompt, _lexicon, register_generator

log = logging.getLogger(__name__)

# Working Gemini image model (AI Studio generate_content path)
DEFAULT_IMAGE_MODEL = "gemini-2.5-flash-image"


def image_model() -> str:
    return (os.environ.get("TEACH_IMAGE_MODEL") or DEFAULT_IMAGE_MODEL).strip()


def image_gen_enabled() -> bool:
    """Default ON when a Gemini key is present; override with TEACH_IMAGE_GENERATE."""
    explicit = (os.environ.get("TEACH_IMAGE_GENERATE") or "").strip().lower()
    if explicit in ("0", "false", "off", "no"):
        return False
    if explicit in ("1", "true", "yes", "on"):
        return True
    # Auto: generate if we have Gemini credentials
    return bool(
        os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    )


def _api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def generate_image_bytes(prompt: str, *, model: str | None = None) -> bytes | None:
    """Call Gemini image model; return PNG/JPEG bytes or None."""
    key = _api_key()
    if not key:
        log.warning("image_gen: no GEMINI_API_KEY")
        return None
    prompt = (prompt or "").strip()
    if not prompt:
        return None
    try:
        from google import genai
    except ImportError:
        log.warning("image_gen: google-genai not installed")
        return None

    mid = model or image_model()
    try:
        client = genai.Client(api_key=key)
        r = client.models.generate_content(
            model=mid,
            contents=(
                prompt
                + " Style: friendly educational flat illustration, warm colors, "
                "clear single subject, NO text, NO letters, NO watermarks."
            ),
        )
        for cand in getattr(r, "candidates", None) or []:
            content = getattr(cand, "content", None)
            for part in getattr(content, "parts", None) or []:
                inline = getattr(part, "inline_data", None)
                if not inline:
                    continue
                data = getattr(inline, "data", None)
                if data:
                    if isinstance(data, str):
                        import base64
                        return base64.b64decode(data)
                    return bytes(data)
        log.warning("image_gen: no image parts in response model=%s", mid)
        return None
    except Exception as e:
        log.warning("image_gen failed model=%s: %s", mid, e)
        return None


def gemini_teach_generator(concept: str, prompt: str, dest: Path) -> bool:
    """teach_assets.register_generator callback: (concept, prompt, dest) -> ok."""
    meta = _lexicon().get(concept) or {}
    form = meta.get("form") or concept
    p = prompt or meta.get("prompt") or _default_prompt(concept, form)
    data = generate_image_bytes(str(p))
    if not data or len(data) < 100:
        return False
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Match extension to payload so ensure_asset can find the file
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        dest = dest.with_suffix(".png")
    elif data[:2] == b"\xff\xd8":
        dest = dest.with_suffix(".jpg")
    dest.write_bytes(data)
    ok = dest.is_file() and dest.stat().st_size > 0
    if ok:
        log.info("image_gen: wrote %s (%d bytes) concept=%s", dest, len(data), concept)
    return ok


def install_teach_image_generator() -> bool:
    """Register generator + enable generate-on-miss when Gemini key is present."""
    if not image_gen_enabled():
        register_generator(None)
        log.info("image_gen: disabled (no key or TEACH_IMAGE_GENERATE=off)")
        return False
    register_generator(gemini_teach_generator)
    os.environ["TEACH_IMAGE_GENERATE"] = "true"
    try:
        from . import teach_assets as ta

        ta.GENERATE_ON_MISS = True
    except Exception:
        pass
    log.info(
        "image_gen: registered generator model=%s generate_on_miss=on",
        image_model(),
    )
    return True
