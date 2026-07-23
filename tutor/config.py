import os
from pathlib import Path

MODEL = "claude-opus-4-8"
MAX_TOKENS = 8192  # headroom so adaptive thinking can't truncate the trailing state block

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO_ROOT / "prompts" / "teaching_policy.md"
DEFAULT_PACK_DIR = REPO_ROOT / "course_packs" / "spanish_a1"
LOG_DIR = REPO_ROOT / "logs" / "sessions"
PROFILE_PATH = REPO_ROOT / "logs" / "profile.json"


def load_env() -> None:
    """Load KEY=VALUE pairs from repo-root .env into the environment
    (existing environment variables win)."""
    env = REPO_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
