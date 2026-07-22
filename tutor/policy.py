"""Builds the system prompt: teaching policy + course pack, with prompt caching.

The policy and pack are stable for a whole session, so they form the cached
prefix (cache_control on the last block covers both). Volatile per-turn
context (session state) goes into `messages`, never here.
"""

from pathlib import Path

from .corpus import load_pack


def build_system(policy_path: Path, pack_dir: Path) -> list[dict]:
    policy = policy_path.read_text()
    pack = load_pack(pack_dir)
    return [
        {"type": "text", "text": policy},
        {
            "type": "text",
            "text": f"# Course pack (your only source of subject truth)\n\n{pack}",
            "cache_control": {"type": "ephemeral"},
        },
    ]
