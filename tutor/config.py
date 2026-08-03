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
# Tutor persona (voice/character layer, e.g. Marisol). File is the persona
# spec; TUTOR_PERSONA=off disables without deleting the file. Persona is HOW
# the tutor talks — modes/gate/pack always outrank it.
PERSONA_PATH = REPO_ROOT / "prompts" / "tutor_persona.md"

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
# Personal facts (name, hooks, sensitive notes) — separate lifecycle from the
# ability sheet: resetting Spanish progress never forgets who the learner is.
LEARNER_PROFILE_PATH = _DATA_ROOT / "learner_profile.json"


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
# Persona toggle (see PERSONA_PATH above): TUTOR_PERSONA=off disables.
TUTOR_PERSONA = (os.environ.get("TUTOR_PERSONA", "on") or "on").strip().lower()
PERSONA_ENABLED = TUTOR_PERSONA not in ("off", "0", "false", "no", "none")
# Plan/realize defaults (Anthropic credits tight → grok planner on xAI billing).
# Override with CONTROLLER_PLANNER / CONTROLLER_EXECUTOR or CLI flags.
CONTROLLER_PLANNER = os.environ.get("CONTROLLER_PLANNER", "grok-4.5")
CONTROLLER_EXECUTOR = os.environ.get("CONTROLLER_EXECUTOR", MODEL)
# Teacher path: planned|plan|new|ai (aliases of the ONE runtime — AI tutor
# with sheet + memory + pedagogy direction). The former "rules" PlanCard
# ladder and "legacy" harness were DELETED (E4/E4b,
# docs/reviews-architecture-refactor.md, 2026-07-28); any other value is a
# hard ValueError at session construction.
TEACHER_MODE = (os.environ.get("TEACHER_MODE", "planned") or "planned").strip().lower()

# r9 falsifier arm selector (docs/design-planner-rounds.md, USER-ratified
# 2026-07-30): legacy | p1_reorder | p2_structured. Position/structure
# controls only — same content, never truncation (SS3.3).
TEACHER_PROMPT_ORDER = (
    os.environ.get("TEACHER_PROMPT_ORDER", "legacy") or "legacy"
).strip().lower()

# B0 dual-path realization context (PEDAGOGY SS3.3 AMENDED 2026-07-30,
# USER-ratified "ratify, run P1/P2, build B0 in parallel";
# docs/design-planner-rounds.md round-2 CONVERGED):
#   full  (default) — today's teacher path, byte-identical (build_ai_tutor_*)
#   brief           — B0 floor: law core + persona + LessonBrief + same-turn
#                     slice + negative projection + budgets + manifest +
#                     last-K exchange window + pack index + fallback
#                     (tutor/realization_context.py; completeness_v1 lint:
#                     scripts/check_completeness.py)
# Non-default until the pre-registered referee (arms A/P1/P2/B0/B1) passes.
# Orthogonal to TEACHER_PROMPT_ORDER (the P1/P2 falsifier knob above).
TEACHER_CONTEXT = (
    os.environ.get("TEACHER_CONTEXT", "full") or "full"
).strip().lower()

PLANNED_TEACHER_MODES = ("planned", "plan", "new", "ai")
# Teach images: cache-first; on miss generate same-turn when enabled + generator.
# Empty/unset = auto-on when GEMINI_API_KEY or GOOGLE_API_KEY is present.
def _teach_image_generate_default() -> bool:
    explicit = (os.environ.get("TEACH_IMAGE_GENERATE") or "").strip().lower()
    if explicit in ("0", "false", "off", "no"):
        return False
    if explicit in ("1", "true", "yes", "on"):
        return True
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


TEACH_IMAGE_GENERATE = _teach_image_generate_default()
# LLM intent classifier for learner utterances (regex retirement — Patrick
# 2026-07-28: "a cheap grok classifier kills regex"). Routing intent comes
# from this model; regex is fallback + surface-form spotting only.
# "off" disables (CI/unit tests run regex-only for determinism).
def _signal_classifier_default() -> str:
    # Non-reasoning lite model: measured 0.8-1.1s and 5/5 on incident
    # fixtures vs grok-3-mini's 2.4-2.7s (reasoning overhead a classifier
    # does not need — Patrick 2026-07-28). Meets the 1.2s promotion gate.
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini-flash-lite-latest"
    if os.environ.get("GROK_API_KEY") or os.environ.get("XAI_API_KEY"):
        return "grok-3-mini"
    return "off"


SIGNAL_CLASSIFIER_MODEL = (
    os.environ.get("SIGNAL_CLASSIFIER_MODEL") or _signal_classifier_default()
).strip()
SIGNAL_CLASSIFIER_TIMEOUT_S = float(
    os.environ.get("SIGNAL_CLASSIFIER_TIMEOUT_S", "8.0")
)
# Blocking = classify BEFORE routing. Measured wall (2026-07-28): default
# gemini-flash-lite-latest 0.8-1.1s; grok-3-mini 2.4-2.7s (reasoning).
# Default: shadow mode — classifier runs PARALLEL to the tutor call (zero
# latency), audits routing disagreements to the ledger, and corrects stale
# holds for the next turn. Promotion to blocking default is gated on the
# pre-registered metrics in docs/reviews-adaptivity-architecture.md.
SIGNAL_CLASSIFIER_BLOCKING = (
    os.environ.get("SIGNAL_CLASSIFIER_BLOCKING", "false").strip().lower()
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
# Sheet ability grades come from the teaching model via update_character_sheet
# (tool-only path; regex hard-observer ability writes removed 2026-07-31).
# Default ON so live sessions can grade. Set SHEET_TOOLS=0 to disable tools
# (ability then freezes — no silent regex bumps).
SHEET_TOOLS = (
    os.environ.get("SHEET_TOOLS", "true").strip().lower()
    in ("1", "true", "yes", "on")
)
# Gate model-rewrite DELETED 2026-08-01 (user: never hide problems).
# Env GATE_REPAIR is ignored — kept only so old shells don't crash on import.
GATE_REPAIR = False
# --- Teacher context to the AI model ---
# Testing default: FULL context (no char / history caps). Latency optimisations
# that slice sheet/pack/stance/history broke teaching quality before. Only re-enable
# caps when we are deliberately optimising for prod.
#   TEACHER_CONTEXT_TRUNCATE=1  → apply PACK/STANCE/SHEET/HISTORY caps below
#   0 or unset                  → unlimited (testing mode)
TEACHER_CONTEXT_TRUNCATE = (
    os.environ.get("TEACHER_CONTEXT_TRUNCATE", "false").strip().lower()
    in ("1", "true", "yes", "on")
)


def _prompt_cap(env_name: str, default_when_truncate: int) -> int:
    """0 = unlimited. Explicit env wins; else default only if truncate mode on."""
    raw = (os.environ.get(env_name) or "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    if TEACHER_CONTEXT_TRUNCATE:
        return default_when_truncate
    return 0  # unlimited


PACK_PROMPT_CHARS = _prompt_cap("PACK_PROMPT_CHARS", 1800)
STANCE_PROMPT_CHARS = _prompt_cap("STANCE_PROMPT_CHARS", 2200)
SHEET_PROMPT_CHARS = _prompt_cap("SHEET_PROMPT_CHARS", 6000)
# History: number of past *turns* (user+assistant pair ≈ 2 messages). 0 = full.
HISTORY_TURNS = _prompt_cap("HISTORY_TURNS", 8)


def clip_prompt(text: str | None, cap: int | None) -> str:
    """Slice prompt text only when cap > 0. Testing mode uses cap=0."""
    t = text or ""
    if not cap or int(cap) <= 0:
        return t
    return t[: int(cap)]


def history_for_model(history: list | None, *, turns: int | None = None) -> list:
    """Chat history window for the teacher model.

    Default testing: full history (HISTORY_TURNS=0). Never mutates `history`.
    When turns/HISTORY_TURNS > 0, returns last N *pairs* (2 messages each).
    """
    h = list(history or [])
    t = HISTORY_TURNS if turns is None else int(turns)
    if not t or t <= 0:
        return h
    return h[-max(2, int(t) * 2) :]


# Server TTS (Gemini). Browser speechSynthesis is fallback only.
TTS_MODEL = os.environ.get("TTS_MODEL", "gemini-2.5-flash-preview-tts")
TTS_VOICE = os.environ.get("TTS_VOICE", "Sulafat")  # Warm
TTS_ENABLED = os.environ.get("TTS_ENABLED", "true")
# Client defaults to server Gemini TTS (AI teach voice). Set true only to force
# browser speechSynthesis first (faster but flaky; used as fallback anyway).
TTS_PREFER_BROWSER = (
    os.environ.get("TTS_PREFER_BROWSER", "false").strip().lower()
    in ("1", "true", "yes", "on")
)


def _clamped_rate(env: str, default: str) -> float:
    try:
        r = float((os.environ.get(env) or default).strip())
    except ValueError:
        r = float(default)
    return max(0.7, min(1.2, r))


# Server default playback rate. Browser speechSynthesis.rate and
# HTMLAudioElement.playbackRate apply the exact rate; Gemini TTS has no
# numeric rate field (tts.py adds a slow-style prefix only at rate <= 0.8).
# Default 1.0 — "Normal" must mean native speed (user complaint 2026-07-28:
# 0.9 default × slow-styled audio stacked into a double slowdown). The user
# picks their own speed with the client Voice slider (0.7–1.2).
TTS_RATE = _clamped_rate("TTS_RATE", "1.0")
# Legacy "Slower" absolute rate; kept for /api/health compat readers.
TTS_SLOWER_RATE = _clamped_rate("TTS_SLOWER_RATE", "0.8")
# Client pause (ms) after <model> audio before <try> audio.
TTS_MODEL_TRY_GAP_MS = int(os.environ.get("TTS_MODEL_TRY_GAP_MS", "400"))
MAX_TOKENS = 8192
# Tutor reply budget. Gemini thinking models spend this SAME budget on hidden
# reasoning tokens before visible text — 1024 truncated real answers mid-word
# (session 20260726-155600 turns 4+8). Replies stay short via prompt, not cap.
TUTOR_MAX_TOKENS = int(os.environ.get("TUTOR_MAX_TOKENS", "4096"))
# Optional reasoning-effort hint for Gemini thinking models ("low"/"medium"/
# "high"). Unset = provider default. Sent only by GeminiClient.
GEMINI_REASONING_EFFORT = (
    os.environ.get("GEMINI_REASONING_EFFORT") or ""
).strip().lower() or None
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
            f"  {venv_py} -m tutor.web_app\n"
            f"Or:\n"
            f"  source .venv/bin/activate\n"
            f"  python -m tutor.web_app\n"
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
