"""Cheap-model enricher for the Focus + Morphology side rail.

Static templates (can_dos.build_focus_panel) are always the base.
FOCUS_MODEL (default grok-3-mini) optionally personalizes:
  - one-line focus blurb for this learner
  - watch note from their last production
  - which forms to highlight

Never invents can-do scores; never blocks teaching if the call fails.
"""

from __future__ import annotations

import json
import re
from typing import Any

from . import config
from .can_dos import build_focus_panel

FOCUS_SYSTEM = """You help a Spanish tutor UI. Given the learner sheet stretch and the
latest exchange, return a SMALL JSON object to personalize the side rail.

Rules:
- Novice A1 only. No advanced grammar lectures.
- Be conservative; ground "watch" in what they actually said this turn.
- Prefer 3–6 high-value forms, not a full conjugation table dump.
- English OK for glosses; Spanish for forms.
- Return ONLY JSON (no markdown fences, no commentary).

Schema:
{
  "focus_blurb": "one plain sentence: what to work on now for THIS learner",
  "watch": "one surface form error or risk from this turn (or empty string)",
  "highlight_forms": ["form1", "form2"],
  "extra_rows": [
    {"form": "…", "person": "yo|tú|—", "gloss": "short English"}
  ]
}
extra_rows max 4; omit if static paradigm is enough.
If turn_morph_target is set, code already picked the form in focus: extra_rows
must be natural A1 example cells for THAT lemma only (present tense), never a
different verb or an untaught tense.
"""


def focus_model_enabled(model: str | None = None) -> bool:
    m = (model if model is not None else config.FOCUS_MODEL) or ""
    m = m.strip().lower()
    return m not in ("", "off", "none", "static", "false", "0")


def _parse_json_object(text: str) -> dict | None:
    t = (text or "").strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) >= 2:
            t = parts[1]
            if t.lstrip().lower().startswith("json"):
                t = t.lstrip()[4:].lstrip()
    try:
        data = json.loads(t)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    start = t.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(t)):
        if t[i] == "{":
            depth += 1
        elif t[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    data = json.loads(t[start : i + 1])
                    return data if isinstance(data, dict) else None
                except json.JSONDecodeError:
                    return None
    return None


def _call_focus_model(
    model: str,
    sheet: dict,
    base: dict,
    learner: str,
    tutor_reply: str,
) -> tuple[dict | None, dict]:
    """Returns (parsed_json_or_None, usage)."""
    usage = {"input_tokens": 0, "output_tokens": 0, "model": model}
    client = config.make_client_for(model)
    caps = config.caps_for(model)
    slim = {
        "name": (sheet.get("identity") or {}).get("preferred_name"),
        "next_best": sheet.get("next_best"),
        "scaffold": (sheet.get("receptive") or {}).get("needs_english_scaffold"),
        "energy": (sheet.get("affect") or {}).get("energy"),
        "skill_focus": base.get("focus"),
        "static_morphology_labels": [
            b.get("label") for b in (base.get("morphology") or [])
        ],
        "static_forms": [
            p.get("form")
            for b in (base.get("morphology") or [])
            for p in (b.get("paradigm") or [])[:6]
        ],
        # Code-chosen turn form (if any) — LLM only decorates it.
        "turn_morph_target": next(
            (
                {"lemma": b.get("lemma"), "label": b.get("label"),
                 "engaged_by": b.get("engaged_by")}
                for b in (base.get("morphology") or [])
                if str(b.get("id") or "").startswith("turn:")
            ),
            None,
        ),
    }
    user = (
        "SHEET SLICE:\n"
        + json.dumps(slim, ensure_ascii=False, indent=2)
        + "\n\nLATEST LEARNER:\n"
        + (learner or "(none)")[:500]
        + "\n\nTUTOR REPLY (excerpt):\n"
        + (tutor_reply or "")[:400]
        + "\n\nReturn the JSON personalization object."
    )
    final = client.messages.create(
        model=caps.model,
        max_tokens=config.FOCUS_MAX_TOKENS,
        system=[{"type": "text", "text": FOCUS_SYSTEM}],
        messages=[{"role": "user", "content": user}],
    )
    usage["input_tokens"] = getattr(final.usage, "input_tokens", 0) or 0
    usage["output_tokens"] = getattr(final.usage, "output_tokens", 0) or 0
    text = "".join(
        getattr(b, "text", "") or ""
        for b in (final.content or [])
        if getattr(b, "type", None) == "text"
    )
    return _parse_json_object(text), usage


def _merge_enrichment(base: dict, enrich: dict) -> dict:
    out = {
        "focus": dict(base.get("focus") or {}),
        "morphology": [dict(b) for b in (base.get("morphology") or [])],
        "lexicon_focus": list(base.get("lexicon_focus") or []),
    }
    blurb = enrich.get("focus_blurb") or enrich.get("blurb")
    if isinstance(blurb, str) and blurb.strip():
        out["focus"]["blurb"] = blurb.strip()[:240]
        # Prefer AI blurb as the card subtitle reason when present
        if not out["focus"].get("reason_ai"):
            out["focus"]["reason_ai"] = blurb.strip()[:240]

    watch = enrich.get("watch")
    if isinstance(watch, str) and watch.strip():
        w = watch.strip()[:160]
        out["focus"]["watch"] = w
        # stamp onto first morphology block if empty
        if out["morphology"]:
            if not (out["morphology"][0].get("watch") or "").strip():
                out["morphology"][0]["watch"] = w
            else:
                out["morphology"][0]["watch"] = (
                    out["morphology"][0]["watch"] + " · " + w
                )[:200]

    highlights = enrich.get("highlight_forms") or enrich.get("highlights") or []
    if isinstance(highlights, list):
        hl = [str(x).strip() for x in highlights if str(x).strip()][:8]
        out["focus"]["highlight_forms"] = hl
        # mark paradigm rows that match
        for block in out["morphology"]:
            for row in block.get("paradigm") or []:
                form = (row.get("form") or "").lower()
                row["highlight"] = any(
                    h.lower() in form or form in h.lower() for h in hl
                )

    extra = enrich.get("extra_rows") or enrich.get("extra_paradigm") or []
    if isinstance(extra, list) and extra and out["morphology"]:
        rows = []
        for item in extra[:4]:
            if not isinstance(item, dict):
                continue
            form = str(item.get("form") or "").strip()
            if not form:
                continue
            rows.append({
                "form": form[:80],
                "person": str(item.get("person") or "—")[:40],
                "gloss": str(item.get("gloss") or "")[:120],
                "highlight": True,
            })
        if rows:
            out["morphology"][0].setdefault("paradigm", [])
            # prepend unique extra rows
            existing = {
                (r.get("form") or "").lower()
                for r in out["morphology"][0]["paradigm"]
            }
            for r in reversed(rows):
                if r["form"].lower() not in existing:
                    out["morphology"][0]["paradigm"].insert(0, r)
                    existing.add(r["form"].lower())
            out["morphology"][0]["paradigm"] = out["morphology"][0]["paradigm"][:8]

    return out


def enrich_focus_panel(
    sheet: dict,
    *,
    learner: str = "",
    tutor_reply: str = "",
    model: str | None = None,
    force_static: bool = False,
) -> tuple[dict, dict]:
    """Build focus panel; optionally enrich with FOCUS_MODEL.

    Returns (panel, meta) where meta has source, usage, error.
    """
    # mode_decision optional: enricher usually runs after a turn; caller may
    # pass via sheet["_last_mode_decision"] without changing the public API.
    # §1.1b (2026-07-29): the _turn_morph stash is DEAD — the live card
    # arrives via sheet["_last_turn_render"] (settled at stage_settle_chrome,
    # synchronously, from exchange_render.card_engagement). The enricher is
    # an OVERLAY: it fills presentation cells on the panel it builds and may
    # never change which form is engaged or which images were confirmed.
    mode_decision = None
    if isinstance(sheet, dict):
        mode_decision = sheet.get("_last_mode_decision")
    base = build_focus_panel(sheet, mode_decision=mode_decision)
    meta: dict[str, Any] = {
        "source": "static",
        "model": None,
        "usage": {},
        "error": None,
    }
    model = model if model is not None else config.FOCUS_MODEL
    if force_static or not focus_model_enabled(model):
        base["source"] = "static"
        return base, meta

    try:
        parsed, usage = _call_focus_model(
            model, sheet, base, learner, tutor_reply,
        )
        meta["usage"] = usage
        meta["model"] = model
        if not parsed:
            meta["error"] = "parse_failed"
            base["source"] = "static_fallback"
            return base, meta
        merged = _merge_enrichment(base, parsed)
        merged["source"] = f"focus_model:{model}"
        meta["source"] = merged["source"]
        return merged, meta
    except Exception as e:
        meta["error"] = f"{type(e).__name__}: {e}"
        base["source"] = "static_fallback"
        return base, meta


def focus_cache_key(sheet: dict) -> str:
    """When this changes, re-run the enricher."""
    nb = sheet.get("next_best") or {}
    rec = sheet.get("receptive") or {}
    return "|".join([
        str(nb.get("can_do") or ""),
        str(nb.get("activity") or nb.get("stretch") or ""),
        "scaffold" if rec.get("needs_english_scaffold") else "es",
        str((sheet.get("identity") or {}).get("preferred_name") or ""),
    ])
