"""Per-session API cost tracking — where the money actually goes.

Every provider call a session makes (tutor LLM, focus rail LLM, server TTS,
teach-image generation) is recorded with its token usage and priced from the
table below. The web header shows the running total; the breakdown rides on
sheet_public()["session_cost"].

Prices are USD per 1M tokens, verified 2026-07-27 (ai.google.dev pricing +
provider pages). They WILL drift — override any entry without a code change:
    COST_PRICING_JSON='{"gemini-3.6-flash": {"input": 2.0, "output": 8.0}}'
Unknown models are tracked with tokens but $0 and flagged `unpriced` so a new
model never silently reads as free money.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any

from . import config

# Cross-process append-only ledger: every priced event from every entry point
# (web session, evals, AI-student, CLI) lands here. This is the "where did the
# $25 go" file — the per-session tracker only covers one chat.
LEDGER_PATH = Path(
    os.environ.get("COST_LEDGER_PATH")
    or (Path(getattr(config, "LOG_DIR", Path("logs/sessions"))).parent / "costs.jsonl")
)
_LEDGER_LOCK = threading.Lock()


def record_event(event: dict[str, Any]) -> None:
    """Append one priced event to the ledger (best-effort, never raises —
    but a lost row is VISIBLE on stderr: no-hide, full-code-audit S5.5)."""
    try:
        e = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(), **event}
        line = json.dumps(e, ensure_ascii=False)
        with _LEDGER_LOCK:
            LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(LEDGER_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as exc:
        print(
            f"[no-hide] cost ledger append failed ({LEDGER_PATH}) — this "
            f"spend is UNTRACKED: {type(exc).__name__}: {exc}",
            file=sys.stderr, flush=True,
        )

# model-name prefix → USD per 1M tokens. Longest prefix wins.
# input_cached: rate for implicit-cache hits (None = provider has no cache tier).
PRICING: dict[str, dict[str, float | None]] = {
    # Tutor / STT default (ai.google.dev 2026-07-28): $1.50/M in, $0.15/M cached,
    # $7.50/M out; thinking bills as output. 3.6 Flash lists unified multimodal input.
    "gemini-3.6-flash": {"input": 1.50, "input_cached": 0.15, "output": 7.50},
    # Server teach voice — Flash TTS (ai.google.dev 2026-07-28)
    "gemini-2.5-flash-preview-tts": {"input": 0.50, "input_cached": None, "output": 10.00},
    # TTS fallbacks also tried by tutor/tts.py _models_to_try
    "gemini-3.1-flash-tts-preview": {"input": 1.00, "input_cached": None, "output": 20.00},
    "gemini-2.5-pro-preview-tts": {"input": 1.00, "input_cached": None, "output": 20.00},
    # Teach images ($30/M image-output tokens; 1290 tok ≈ $0.039/image)
    "gemini-2.5-flash-image": {"input": 0.30, "input_cached": None, "output": 30.00},
    # Focus rail — legacy slug; rates from secondary sources 2026-07; primary
    # xAI models page no longer lists grok-3-mini as of 2026-07-28
    "grok-3-mini": {"input": 0.30, "input_cached": None, "output": 0.50},
    # xAI Grok 4.20 family (docs.x.ai via pricing trackers, 2026-08-04 —
    # found UNPRICED after a day of $0 rows, §3.4 violation): reasoning
    # output includes hidden thinking tokens (billed at output rate).
    "grok-4.20-0309": {"input": 1.25, "input_cached": 0.20, "output": 2.50},
    "grok-4.20-0309-non-reasoning": {"input": 1.25, "input_cached": 0.20, "output": 2.50},
    # Intent classifier — official Gemini Developer API paid tier (2026-07-28)
    # https://ai.google.dev/gemini-api/docs/pricing (Grok round-3 verified;
    # Claude's earlier $0.10/$0.40 estimate was 2.5-lite-era and ~3x low)
    "gemini-3.1-flash-lite": {"input": 0.25, "input_cached": 0.025, "output": 1.50},
    # Cheaper-model trial 2026-08-05 (USER "prices are too high"):
    # web-verified $0.30/$2.50; cached at the standard 10% convention.
    "gemini-3.5-flash-lite": {"input": 0.30, "input_cached": 0.03, "output": 2.50},
    # DeepSeek trial 2026-08-05 (api-docs.deepseek.com/quick_start/pricing):
    # cache-hit input is their $/M "cache hit" rate; NOTE peak hours
    # (Beijing 9-12 & 14-18) may bill 2x once their announcement lands.
    "deepseek-v4-flash": {"input": 0.14, "input_cached": 0.0028, "output": 0.28},
    "deepseek-v4-pro": {"input": 0.435, "input_cached": 0.003625, "output": 0.87},
    "gemini-3.5-flash-lite": {"input": 0.30, "input_cached": 0.03, "output": 2.50},
    # Alias hot-swaps; price at current GA lite (3.5) until pin is forced
    "gemini-flash-lite-latest": {"input": 0.30, "input_cached": 0.03, "output": 2.50},
    # Legacy 2.5 lite (if ever pinned for cost floors)
    "gemini-2.5-flash-lite": {"input": 0.10, "input_cached": 0.01, "output": 0.40},
}

# Flat per-image fallback when the image API gives no token usage.
IMAGE_FLAT_USD: dict[str, float] = {
    "gemini-2.5-flash-image": 0.039,
}
DEFAULT_IMAGE_FLAT_USD = 0.039


# One-shot flag: _pricing() runs on every priced call — a malformed
# COST_PRICING_JSON is announced once, not per call (still never silent).
_pricing_override_warned = False


def _pricing() -> dict[str, dict[str, float | None]]:
    global _pricing_override_warned
    table = {k: dict(v) for k, v in PRICING.items()}
    raw = (os.environ.get("COST_PRICING_JSON") or "").strip()
    if raw:
        try:
            override = json.loads(raw)
            for model, rates in override.items():
                if isinstance(rates, dict):
                    table.setdefault(model, {}).update(rates)
        except (json.JSONDecodeError, AttributeError) as exc:
            if not _pricing_override_warned:
                _pricing_override_warned = True
                print(
                    f"[no-hide] COST_PRICING_JSON ignored (parse failed) — "
                    f"built-in PRICING table in effect: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr, flush=True,
                )
    return table


def price_for(model: str) -> dict[str, float | None] | None:
    """Longest-prefix match so dated variants inherit the family price."""
    table = _pricing()
    best: tuple[int, dict] | None = None
    m = (model or "").lower()
    for prefix, rates in table.items():
        if m.startswith(prefix.lower()) and (best is None or len(prefix) > best[0]):
            best = (len(prefix), rates)
    return best[1] if best else None


class SessionCostTracker:
    """Accumulates priced usage events for one chat session (thread-safe).

    Every event is ALSO appended to the cross-process ledger with `source`
    so offline runs (evals, AI-student) show up in the money report.
    """

    def __init__(self, source: str = "session") -> None:
        self._lock = threading.Lock()
        self.source = source
        self.reset()

    def reset(self) -> None:
        with getattr(self, "_lock", threading.Lock()):
            self._by_category: dict[str, dict[str, Any]] = {}
            self._unpriced: set[str] = set()

    def _bucket(self, category: str) -> dict[str, Any]:
        return self._by_category.setdefault(category, {
            "usd": 0.0,
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "thinking_tokens": 0,
            "cached_input_tokens": 0,
            "images": 0,
            "models": set(),
        })

    def add_llm(
        self,
        category: str,
        model: str,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        thinking_tokens: int = 0,
        cached_input_tokens: int = 0,
    ) -> float:
        """Record one LLM/TTS call. Thinking tokens bill at the output rate;
        cached input bills at the cache rate when the model has one."""
        inp = max(0, int(input_tokens or 0))
        out = max(0, int(output_tokens or 0))
        think = max(0, int(thinking_tokens or 0))
        cached = min(max(0, int(cached_input_tokens or 0)), inp)
        rates = price_for(model)
        usd = 0.0
        if rates:
            in_rate = float(rates.get("input") or 0.0)
            cache_rate = rates.get("input_cached")
            out_rate = float(rates.get("output") or 0.0)
            fresh = inp - cached
            usd += fresh * in_rate / 1e6
            usd += cached * float(cache_rate if cache_rate is not None else in_rate) / 1e6
            usd += (out + think) * out_rate / 1e6
        with self._lock:
            b = self._bucket(category)
            b["usd"] += usd
            b["calls"] += 1
            b["input_tokens"] += inp
            b["output_tokens"] += out
            b["thinking_tokens"] += think
            b["cached_input_tokens"] += cached
            b["models"].add(model)
            if not rates and model:
                self._unpriced.add(model)
        record_event({
            "source": self.source, "category": category, "model": model,
            "input_tokens": inp, "output_tokens": out,
            "thinking_tokens": think, "cached_input_tokens": cached,
            "usd": round(usd, 6), "priced": bool(rates),
        })
        return usd

    def add_image(self, model: str, count: int = 1) -> float:
        """Flat per-image pricing (no reliable token usage from the API path)."""
        n = max(0, int(count or 0))
        if not n:
            return 0.0
        flat = IMAGE_FLAT_USD.get((model or "").lower())
        if flat is None:
            for prefix, v in IMAGE_FLAT_USD.items():
                if (model or "").lower().startswith(prefix):
                    flat = v
                    break
        if flat is None:
            flat = DEFAULT_IMAGE_FLAT_USD
        usd = flat * n
        with self._lock:
            b = self._bucket("image")
            b["usd"] += usd
            b["calls"] += n
            b["images"] += n
            b["models"].add(model)
        record_event({
            "source": self.source, "category": "image", "model": model,
            "images": n, "usd": round(usd, 6), "priced": True,
        })
        return usd

    def summary(self) -> dict[str, Any]:
        with self._lock:
            cats = {}
            total = 0.0
            for cat, b in self._by_category.items():
                cats[cat] = {**b, "models": sorted(b["models"]),
                             "usd": round(b["usd"], 6)}
                total += b["usd"]
            return {
                "total_usd": round(total, 6),
                "by_category": cats,
                "unpriced_models": sorted(self._unpriced),
            }


def _local_day(ts: str) -> str:
    """UTC ISO timestamp → LOCAL calendar day for reporting.

    Events are stored UTC; bucketing by ts[:10] put evening practice (UTC-6)
    on the next day's line (Grok countersign 2026-07-28 — fixed, not just
    documented)."""
    try:
        dt = datetime.datetime.fromisoformat(ts)
        return dt.astimezone().date().isoformat()
    except (ValueError, TypeError):
        return (ts or "")[:10]


def ledger_report(days: int = 14) -> dict[str, Any]:
    """Aggregate the cross-process ledger: per-LOCAL-day / category / source USD."""
    by_day: dict[str, dict[str, Any]] = {}
    total = 0.0
    unpriced: set[str] = set()
    if LEDGER_PATH.exists():
        for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            day = _local_day(e.get("ts") or "")
            usd = float(e.get("usd") or 0.0)
            d = by_day.setdefault(day, {"usd": 0.0, "by_category": {}, "by_source": {}})
            d["usd"] += usd
            cat = e.get("category") or "?"
            src = e.get("source") or "?"
            d["by_category"][cat] = d["by_category"].get(cat, 0.0) + usd
            d["by_source"][src] = d["by_source"].get(src, 0.0) + usd
            total += usd
            if not e.get("priced") and e.get("model"):
                unpriced.add(e["model"])
    days_sorted = sorted(by_day)[-max(1, days):]
    return {
        "total_usd": round(total, 4),
        "days": {
            d: {
                "usd": round(by_day[d]["usd"], 4),
                "by_category": {k: round(v, 4) for k, v in by_day[d]["by_category"].items()},
                "by_source": {k: round(v, 4) for k, v in by_day[d]["by_source"].items()},
            }
            for d in days_sorted
        },
        "unpriced_models": sorted(unpriced),
        "ledger": str(LEDGER_PATH),
    }


def main() -> None:
    """`python -m tutor.costs` — where the money is going."""
    rep = ledger_report()
    print(f"Ledger: {rep['ledger']}")
    print(f"Total tracked: ${rep['total_usd']:.4f}")
    for day, d in rep["days"].items():
        cats = ", ".join(f"{k} ${v:.4f}" for k, v in sorted(
            d["by_category"].items(), key=lambda kv: -kv[1]))
        srcs = ", ".join(f"{k} ${v:.4f}" for k, v in sorted(
            d["by_source"].items(), key=lambda kv: -kv[1]))
        print(f"{day}  ${d['usd']:.4f}   [{cats}]   ({srcs})")
    if rep["unpriced_models"]:
        print("UNPRICED (tracked but $0 — add to PRICING):",
              ", ".join(rep["unpriced_models"]))


if __name__ == "__main__":
    main()
