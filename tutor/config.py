import os
from pathlib import Path

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


load_env()

# Model selection: cheap by default for development/testing; set
# TUTOR_MODEL=claude-opus-4-8 for frontier-baseline runs. Adherence results
# are model-specific — eval results record which model produced them.
MODEL = os.environ.get("TUTOR_MODEL", "grok-4-fast")
MAX_TOKENS = 8192

PROVIDER = "xai" if MODEL.startswith("grok") else "anthropic"
# Mid-conversation {"role": "system"} messages are Claude Opus 4.8-only.
SUPPORTS_MID_SYSTEM = MODEL == "claude-opus-4-8"
SUPPORTS_ADAPTIVE_THINKING = MODEL.startswith(
    ("claude-opus-4", "claude-sonnet-4", "claude-sonnet-5", "claude-fable")
)
# xAI's Anthropic-compat endpoint breaks the SDK stream accumulator.
SUPPORTS_STREAMING = PROVIDER == "anthropic"


def make_client():
    import anthropic
    if PROVIDER == "xai":
        key = os.environ.get("GROK_API_KEY") or os.environ.get("XAI_API_KEY")
        if not key:
            raise RuntimeError("GROK_API_KEY not set (needed for grok models)")
        return anthropic.Anthropic(api_key=key, base_url="https://api.x.ai")
    return anthropic.Anthropic()
