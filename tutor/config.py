import os
from pathlib import Path


def _find_repo_root() -> Path:
    """Locate course_packs + prompts (dev tree, installed wheel, or Vercel)."""
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent,  # normal: repo_root/tutor/config.py
        Path.cwd(),
        Path(os.environ.get("VERCEL_PROJECT_ROOT", "")),
        Path("/var/task"),
        Path("/vercel/path0"),
        here,  # fallback: package dir only
    ]
    for c in candidates:
        if not c or str(c) == ".":
            continue
        if (c / "course_packs").is_dir() and (c / "prompts").is_dir():
            return c
        if (c / "tutor").is_dir() and (c / "course_packs").is_dir():
            return c
    return here.parent


REPO_ROOT = _find_repo_root()
POLICY_PATH = REPO_ROOT / "prompts" / "teaching_policy.md"
DEFAULT_PACK_DIR = REPO_ROOT / "course_packs" / "spanish_a1"

# On Vercel (and similar serverless), repo is read-only; use /tmp for runtime data.
_ON_SERVERLESS = bool(
    os.environ.get("VERCEL")
    or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    or os.environ.get("ML_TEACHER_DATA_DIR")
)
_DATA_ROOT = Path(
    os.environ.get("ML_TEACHER_DATA_DIR")
    or ("/tmp/ml_teacher" if _ON_SERVERLESS else str(REPO_ROOT / "logs"))
)
LOG_DIR = _DATA_ROOT / "sessions"
PROFILE_PATH = _DATA_ROOT / "profile.json"
CHARACTER_SHEET_PATH = _DATA_ROOT / "character_sheet.json"


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
# Default per EXP-001: best cheap-tier adherence (8/13 vs grok's 6/13).
MODEL = os.environ.get("TUTOR_MODEL", "gemini-3.6-flash")
# Plan/realize defaults (Anthropic credits tight → grok planner on xAI billing).
# Override with CONTROLLER_PLANNER / CONTROLLER_EXECUTOR or CLI flags.
CONTROLLER_PLANNER = os.environ.get("CONTROLLER_PLANNER", "grok-4.5")
CONTROLLER_EXECUTOR = os.environ.get("CONTROLLER_EXECUTOR", MODEL)
# Teacher path:
#   planned|ai (default) — AI tutor with sheet + memory + pedagogy direction
#   rules — optional PlanCard ladder (flashcard-prone; experiments only)
#   legacy — single harness LLM without structured plan notes
TEACHER_MODE = (os.environ.get("TEACHER_MODE", "planned") or "planned").strip().lower()
# Teach images: cache-first always. Generate on miss only if true + generator registered.
TEACH_IMAGE_GENERATE = (
    os.environ.get("TEACH_IMAGE_GENERATE", "false").strip().lower()
    in ("1", "true", "yes", "on")
)
# Side-rail focus/morphology enricher (cheap). "off" / "static" / "none" = templates only.
FOCUS_MODEL = os.environ.get("FOCUS_MODEL", "grok-3-mini")
FOCUS_MAX_TOKENS = int(os.environ.get("FOCUS_MAX_TOKENS", "512"))
# If true, wait for focus LLM before returning the tutor turn (slow — avoid).
# Default false: static rail immediately, FOCUS_MODEL enrich runs in background.
FOCUS_BLOCKING = (
    os.environ.get("FOCUS_BLOCKING", "false").strip().lower()
    in ("1", "true", "yes", "on")
)
# Async focus enrich after reply (default on when model is enabled).
FOCUS_ASYNC = (
    os.environ.get("FOCUS_ASYNC", "true").strip().lower()
    in ("1", "true", "yes", "on")
)
# Tool-call sheet updates add a second model round-trip; hard_observer already
# writes evidence. Default off for latency; set SHEET_TOOLS=1 to re-enable.
SHEET_TOOLS = (
    os.environ.get("SHEET_TOOLS", "false").strip().lower()
    in ("1", "true", "yes", "on")
)
# Second LLM only for critical output-gate failures (missing teach move / English wall).
GATE_REPAIR = (
    os.environ.get("GATE_REPAIR", "true").strip().lower()
    in ("1", "true", "yes", "on")
)
# Prompt size caps (tokens ≈ chars/4; keep small for speed)
PACK_PROMPT_CHARS = int(os.environ.get("PACK_PROMPT_CHARS", "1800"))
STANCE_PROMPT_CHARS = int(os.environ.get("STANCE_PROMPT_CHARS", "2200"))
HISTORY_TURNS = int(os.environ.get("HISTORY_TURNS", "8"))  # message pairs cap
# Server TTS (Gemini). Browser speechSynthesis is fallback only.
TTS_MODEL = os.environ.get("TTS_MODEL", "gemini-2.5-flash-preview-tts")
TTS_VOICE = os.environ.get("TTS_VOICE", "Sulafat")  # Warm
TTS_ENABLED = os.environ.get("TTS_ENABLED", "true")
# Prefer browser TTS for instant start (server Gemini TTS is a full extra RTT).
TTS_PREFER_BROWSER = (
    os.environ.get("TTS_PREFER_BROWSER", "true").strip().lower()
    in ("1", "true", "yes", "on")
)
MAX_TOKENS = 8192
# Tutor replies stay short for TTS + latency
TUTOR_MAX_TOKENS = int(os.environ.get("TUTOR_MAX_TOKENS", "1024"))
# Planner only emits a small JSON decision — keep this tight for latency.
PLANNER_MAX_TOKENS = int(os.environ.get("PLANNER_MAX_TOKENS", "768"))

if MODEL.startswith("grok"):
    PROVIDER = "xai"
elif MODEL.startswith("gemini"):
    PROVIDER = "google"
else:
    PROVIDER = "anthropic"
# Mid-conversation {"role": "system"} messages are Claude Opus 4.8-only.
SUPPORTS_MID_SYSTEM = MODEL == "claude-opus-4-8"
SUPPORTS_ADAPTIVE_THINKING = MODEL.startswith(
    ("claude-opus-4", "claude-sonnet-4", "claude-sonnet-5", "claude-fable")
)
# xAI's Anthropic-compat endpoint breaks the SDK stream accumulator.
SUPPORTS_STREAMING = PROVIDER == "anthropic"


def provider_for(model: str) -> str:
    if model.startswith("grok"):
        return "xai"
    if model.startswith("gemini"):
        return "google"
    return "anthropic"


def caps_for(model: str):
    """Per-model capability flags, for architectures that run two models at
    once (EXP-002 planner/executor). The module-level SUPPORTS_* globals stay
    as-is for the single-model path so existing gate runs are unaffected."""
    from types import SimpleNamespace
    return SimpleNamespace(
        model=model,
        provider=provider_for(model),
        mid_system=(model == "claude-opus-4-8"),
        adaptive_thinking=model.startswith(
            ("claude-opus-4", "claude-sonnet-4", "claude-sonnet-5", "claude-fable")),
        streaming=(provider_for(model) == "anthropic"),
    )


def make_client_for(model: str):
    try:
        import anthropic
    except ModuleNotFoundError as e:
        venv_py = REPO_ROOT / ".venv" / "bin" / "python"
        hint = (
            f"\nUse the project venv instead of system Python:\n"
            f"  {venv_py} -m tutor.pedagogy_controller session\n"
            f"Or:\n"
            f"  source .venv/bin/activate\n"
            f"  python -m tutor.pedagogy_controller session\n"
            f"If the venv is missing deps:  {venv_py} -m pip install -e ."
        )
        raise ModuleNotFoundError(
            f"Missing package 'anthropic' in this Python interpreter.{hint}"
        ) from e
    provider = provider_for(model)
    if provider == "xai":
        key = os.environ.get("GROK_API_KEY") or os.environ.get("XAI_API_KEY")
        if not key:
            raise RuntimeError("GROK_API_KEY not set (needed for grok models)")
        return anthropic.Anthropic(api_key=key, base_url="https://api.x.ai")
    if provider == "google":
        from .providers import GeminiClient
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY not set (needed for gemini models)")
        return GeminiClient(key)
    return anthropic.Anthropic()


def make_client():
    return make_client_for(MODEL)
