from pathlib import Path

MODEL = "claude-opus-4-8"
MAX_TOKENS = 8192  # headroom so adaptive thinking can't truncate the trailing state block

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO_ROOT / "prompts" / "teaching_policy.md"
DEFAULT_PACK_DIR = REPO_ROOT / "course_packs" / "spanish_a1"
LOG_DIR = REPO_ROOT / "logs" / "sessions"
