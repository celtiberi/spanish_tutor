import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO_ROOT / "prompts" / "teaching_policy.md"
DEFAULT_PACK_DIR = REPO_ROOT / "course_packs" / "spanish_a1"
LOG_DIR = REPO_ROOT / "logs" / "sessions"
PROFILE_PATH = REPO_ROOT / "logs" / "profile.json"
CHARACTER_SHEET_PATH = REPO_ROOT / "logs" / "character_sheet.json"


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
# New teacher: "planned" = rules PlanCard + executor; "legacy" = single harness LLM.
TEACHER_MODE = (os.environ.get("TEACHER_MODE", "planned") or "planned").strip().lower()
# Side-rail focus/morphology enricher (cheap). "off" / "static" / "none" = templates only.
FOCUS_MODEL = os.environ.get("FOCUS_MODEL", "grok-3-mini")
FOCUS_MAX_TOKENS = int(os.environ.get("FOCUS_MAX_TOKENS", "512"))
# Server TTS (Gemini). Browser speechSynthesis is fallback only.
TTS_MODEL = os.environ.get("TTS_MODEL", "gemini-2.5-flash-preview-tts")
TTS_VOICE = os.environ.get("TTS_VOICE", "Sulafat")  # Warm
TTS_ENABLED = os.environ.get("TTS_ENABLED", "true")
MAX_TOKENS = 8192
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
