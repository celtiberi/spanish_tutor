"""Course-pack loading.

v0 strategy: an A1-sized pack fits comfortably in context, so the whole
structured pack is placed in the (cached) system prompt instead of vector RAG.
Swap this module for a retriever when corpora outgrow the context window
(e.g. the Phase 3 transfer subject).
"""

from pathlib import Path


def load_pack(pack_dir: Path) -> str:
    manifest = pack_dir / "pack.md"
    if not manifest.exists():
        raise FileNotFoundError(f"No pack.md manifest in {pack_dir}")
    units = sorted(p for p in pack_dir.glob("unit*.md"))
    parts = [manifest.read_text()]
    parts += [p.read_text() for p in units]
    return "\n\n---\n\n".join(parts)
