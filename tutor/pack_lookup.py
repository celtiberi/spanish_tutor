"""Pull pack item / misconception text by ID for executor briefs."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

# Headings like: ### M-1.2 — title
# Items like: **P-1.1** — prompt...
_HEAD_RE = re.compile(
    r"^(#{2,3}\s+|(?:\*\*)?)([MCPST]-\d+(?:\.\d+)?)(?:\*\*)?"
    r"\s*[—\-:]?\s*(.+)$",
    re.M,
)


@lru_cache(maxsize=8)
def _pack_blob(pack_dir: str) -> str:
    root = Path(pack_dir)
    parts = []
    for p in sorted(root.glob("unit*.md")):
        parts.append(p.read_text())
    man = root / "pack.md"
    if man.exists():
        parts.insert(0, man.read_text())
    return "\n\n".join(parts)


def lookup_entry(pack_dir: Path | str, ref: str) -> str | None:
    """Return the pack section for an ID (M/P/SI/C/T), or None."""
    if not ref or not re.match(r"^[MCPST]-\d+", ref):
        # SI-1.1 style
        if not ref or not re.match(r"^SI-\d+", ref or ""):
            if not (ref and re.match(r"^[A-Z]{1,2}-\d+", ref)):
                return None
    blob = _pack_blob(str(pack_dir))
    # Prefer block from heading/item line through next blank+heading or next ID
    # Normalize SI and others
    pat = re.compile(
        rf"(?:^|\n)((?:###?\s+|\*\*)?{re.escape(ref)}\b.*?)(?=\n(?:###?\s+|\*\*)[MCPST]I?-\d|\n##\s|\Z)",
        re.S,
    )
    # Fix SI: IDs are SI-1.1
    pat = re.compile(
        rf"(?:^|\n)((?:###?\s+|\*\*)?{re.escape(ref)}\b.*?)(?=\n(?:###?\s+|\*\*)[A-Z]{{1,2}}-\d|\n##\s|\Z)",
        re.S,
    )
    m = pat.search(blob)
    if not m:
        return None
    text = m.group(1).strip()
    # Cap so briefs stay short
    if len(text) > 900:
        text = text[:900] + "…"
    return text


def seed_dialogue_excerpt(pack_dir: Path | str, unit: int | str | None = 1) -> str | None:
    """First seed dialogue block from unit file for input-first opens."""
    root = Path(pack_dir)
    if unit is None:
        unit = 1
    try:
        n = int(unit)
    except (TypeError, ValueError):
        n = 1
    path = root / f"unit{n:02d}_" 
    matches = list(root.glob(f"unit{n:02d}_*.md"))
    if not matches:
        matches = sorted(root.glob("unit*.md"))
        if not matches:
            return None
    text = matches[0].read_text()
    # From "## Seed input" through next ##
    m = re.search(
        r"## Seed input.*?\n(.*?)(?=\n## )",
        text,
        re.S | re.I,
    )
    if not m:
        return None
    block = m.group(1).strip()
    if len(block) > 1200:
        block = block[:1200] + "…"
    return block
