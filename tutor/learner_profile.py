"""Learner personal profile — DISCONNECTED and HARD-DISABLED (2026-07-28).

Patrick: "totally remove saving personal data about the user. We need to
just get the teaching working first." Nothing in the runtime loads, captures,
or persists personal facts any more — the trigger was the name-capture regex
turning "I am searching for eggs" into preferred_name "Searching". Per the
Grok countersign (docs/reviews-personal-data-removal.md, item b), the writer
APIs in this module are hard-disabled, not merely unused: `capture_name`
always returns None, `apply_profile_updates` is a no-op, and
`save_learner_profile` raises. `load_learner_profile` never reads disk (no
resurrection path for legacy files). The module stays on disk as the
reference design for a future opt-in profile (sheet = ability only /
profile = person, separate reset lifecycles), and `profile_path_for_sheet`
is still used to DELETE stale profile files.

Storage (historical): JSON next to the sheet (`logs/learner_profile.json`).
"""

from __future__ import annotations

import copy
import datetime
from pathlib import Path

from . import config

PROFILE_VERSION = 1


def _today() -> str:
    return datetime.date.today().isoformat()


def default_profile() -> dict:
    return {
        "version": PROFILE_VERSION,
        "preferred_name": None,
        "l1": "en",
        "goals": [],
        # Conversation color: [{"fact": str, "added": iso-date}]
        "hooks": [],
        # Topics the learner asked for: ["tools/shopping", ...]
        "interests": [],
        # Facts requiring care: [{"fact": str, "guidance": str, "added": date}]
        "sensitive": [],
        "updated_at": _today(),
    }


def profile_path_for_sheet(sheet_path: Path) -> Path:
    """Profile file that belongs to a sheet file.

    The default sheet gets the canonical logs/learner_profile.json; custom
    sheet paths (evals, AI-student runs) get an isolated sibling file so
    experiments never write into the real learner's profile.

    Still fully live: reset flows use this to DELETE stale capture-era files.
    """
    sheet_path = Path(sheet_path)
    if sheet_path == Path(config.CHARACTER_SHEET_PATH):
        return Path(config.LEARNER_PROFILE_PATH)
    return sheet_path.with_name(sheet_path.stem + ".profile.json")


def load_learner_profile(path: Path) -> dict:
    """Always a fresh default profile — NEVER reads disk.

    Personal-data capture disabled 2026-07-28: reading a legacy
    learner_profile.json would resurrect stored personal data, so this
    returns default_profile() unconditionally (kept callable for tests).
    """
    return default_profile()


def save_learner_profile(path: Path, profile: dict) -> None:
    raise RuntimeError(
        "learner_profile save disabled 2026-07-28 (personal-data capture off)"
    )


# ---------------------------------------------------------------------------
# Hard observer (personal facts) — DISABLED
# ---------------------------------------------------------------------------

def capture_name(text: str) -> str | None:
    """Always None — name capture is disabled (2026-07-28).

    WHY: the old case-insensitive I-am pattern
    (r"\\bI(?:'m| am)\\s+([A-Z][a-z...]{2,})\\b" searched with re.I) nullified
    its own capitalization guard and turned "I am searching for eggs" into
    preferred_name "Searching" (2026-07-28 incident; the next session opened
    "¡Hola, Searching!"). The regex machinery has been deleted. Do not
    re-enable capture without an explicit opt-in design.
    """
    return None


def apply_profile_updates(profile: dict, learner: str) -> tuple[dict, bool]:
    """No-op observer (capture disabled 2026-07-28): never captures anything."""
    return copy.deepcopy(profile or default_profile()), False


# ---------------------------------------------------------------------------
# Prompt / instruction views (reference design; no live callers)
# ---------------------------------------------------------------------------

def profile_name(profile: dict | None) -> str:
    return ((profile or {}).get("preferred_name") or "").strip()


def hooks_text(profile: dict | None) -> str:
    facts = [
        (h.get("fact") or "").strip()
        for h in (profile or {}).get("hooks") or []
    ]
    facts += [
        f"Interested in: {i}" for i in (profile or {}).get("interests") or []
    ]
    return " ".join(f for f in facts if f)


def sensitive_guidance(profile: dict | None) -> list[str]:
    out = []
    for e in (profile or {}).get("sensitive") or []:
        g = (e.get("guidance") or e.get("fact") or "").strip()
        if g:
            out.append(g)
    return out


def personal_context_for_prompt(profile: dict | None) -> str:
    """System block: personal facts, clearly separated from ability data."""
    prof = profile or {}
    name = profile_name(prof)
    hooks = hooks_text(prof)
    sens = sensitive_guidance(prof)
    if not (name or hooks or sens):
        return ""
    lines = [
        "# Learner personal context — HANDLE WITH CARE",
        "Personal facts the learner has shared. Use for warmth and relevance, "
        "sparingly — this is color, not an agenda. Never quote this block or "
        "reveal that notes are stored.",
    ]
    if name:
        lines.append(f"Preferred name: {name}")
    if prof.get("l1"):
        lines.append(f"First language: {prof['l1']}")
    if hooks:
        lines.append(f"Conversation hooks (vary them; optional): {hooks}")
    for g in sens:
        lines.append(f"CARE RULE (obey verbatim): {g}")
    return "\n".join(lines)
