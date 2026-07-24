"""Course-pack loading.

v0 strategy: an A1-sized pack fits comfortably in context, so the whole
structured pack is placed in the (cached) system prompt instead of vector RAG.
Swap this module for a retriever when corpora outgrow the context window
(e.g. the Phase 3 transfer subject).

Controller planner path uses `load_pack_planner_index` — a compact ID/index
view (~5–10× smaller) so plan/realize is not paying full-corpus latency.
"""

from __future__ import annotations

import re
from pathlib import Path

_ID_RE = re.compile(r"\b([MCPST]-\d+(?:\.\d+)?)\b")
_M_HEAD_RE = re.compile(r"^#{2,3}\s+(M-\d+(?:\.\d+)?\s*[—\-].+)$", re.M)


def load_pack(pack_dir: Path) -> str:
    manifest = pack_dir / "pack.md"
    if not manifest.exists():
        raise FileNotFoundError(f"No pack.md manifest in {pack_dir}")
    units = sorted(p for p in pack_dir.glob("unit*.md"))
    parts = [manifest.read_text()]
    parts += [p.read_text() for p in units]
    return "\n\n---\n\n".join(parts)


def load_pack_planner_index(pack_dir: Path) -> str:
    """Compact curriculum index for the *controller planner* only.

    Includes pack manifest skeleton + per-unit titles, item IDs, and
    misconception headings — not full dialogues, tables, or keys. The
    executor still gets `load_pack` (full) so it can teach content.
    """
    manifest = pack_dir / "pack.md"
    if not manifest.exists():
        raise FileNotFoundError(f"No pack.md manifest in {pack_dir}")
    raw = manifest.read_text()
    # Keep header + units table + scope boundaries; drop long prose middle.
    lines = raw.splitlines()
    keep: list[str] = []
    section = "head"
    for ln in lines:
        if ln.startswith("## Units"):
            section = "units"
        elif ln.startswith("## In-scope"):
            section = "inscope"
        elif ln.startswith("## Scope boundaries"):
            section = "scope"
        elif ln.startswith("## Global pronunciation"):
            section = "skip"
        elif ln.startswith("## ") and section not in ("head", "units", "scope"):
            section = "skip"
        if section == "skip":
            continue
        if section == "inscope":
            # one-line inventory only
            if ln.startswith("## ") or ln.startswith("Closed list") or not ln.strip():
                if ln.startswith("## "):
                    keep.append(ln)
                continue
            if len(ln) < 220:
                keep.append(ln)
            continue
        keep.append(ln)
    parts = ["# Planner pack index (compact — not full unit content)\n",
             "\n".join(keep).strip()]
    for p in sorted(pack_dir.glob("unit*.md")):
        text = p.read_text()
        title = next((ln for ln in text.splitlines() if ln.strip()), p.name)
        ids = sorted(set(_ID_RE.findall(text)))
        m_heads = _M_HEAD_RE.findall(text)
        block = [title, f"IDs: {', '.join(ids)}"]
        if m_heads:
            block.append("Misconceptions:")
            block.extend(f"- {h}" for h in m_heads)
        parts.append("\n".join(block))
    return "\n\n---\n\n".join(parts)
