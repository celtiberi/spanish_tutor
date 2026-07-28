"""Pre-warm the teach-image cache: generate every never-created concept ONCE.

The cache already guarantees a concept is only ever generated once — but the
FIRST request for each concept costs $0.039 + several seconds of mid-lesson
latency. This batch job moves all of those first-misses offline so no live
session ever pays them. Re-running is free: cache hits generate nothing.

Usage:  .venv/bin/python scripts/prewarm_teach_images.py [--dry-run]
Costs land in logs/costs.jsonl with source=prewarm.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tutor.image_gen import install_teach_image_generator  # noqa: E402
from tutor.costs import SessionCostTracker  # noqa: E402
from tutor.modes import _form_for_concept  # noqa: E402
from tutor.teach_assets import (  # noqa: E402
    CONCEPT_LEXICON,
    cache_lookup,
    ensure_asset,
    seed_index_from_disk,
)

# Concepts modes.py can request beyond the image lexicon (_noun_from_text pairs)
EXTRA_CONCEPTS = (
    "edificio", "casa", "playa", "perro", "gato", "agua", "sol", "calor", "frio",
)


def main() -> int:
    dry = "--dry-run" in sys.argv
    seed_index_from_disk()
    if not dry and not install_teach_image_generator():
        print("Image generator unavailable (no GEMINI_API_KEY?) — aborting.")
        return 1
    concepts = sorted(set(CONCEPT_LEXICON) | set(EXTRA_CONCEPTS))
    tracker = SessionCostTracker(source="prewarm")
    hit = missing = generated = failed = 0
    for c in concepts:
        if cache_lookup(c):
            hit += 1
            continue
        missing += 1
        if dry:
            print(f"MISS (would generate): {c}")
            continue
        try:
            asset = ensure_asset(c, form=_form_for_concept(c), generate=True)
        except Exception as e:
            print(f"FAIL {c}: {type(e).__name__}: {e}")
            failed += 1
            continue
        if asset and (asset.get("cache") or "").startswith("miss"):
            generated += 1
            usd = tracker.add_image(
                "gemini-2.5-flash-image", 1
            )
            print(f"GENERATED {c} → {asset.get('file')} (${usd:.3f})")
        elif asset:
            hit += 1
        else:
            print(f"FAIL {c}: generator returned nothing")
            failed += 1
    print(
        f"\ncached-already={hit} missing={missing} generated={generated} "
        f"failed={failed} total_usd=${tracker.summary()['total_usd']:.3f}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
