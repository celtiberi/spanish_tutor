"""LLM intent classifier for learner utterances — regex retirement, phase E.

Patrick's directive (2026-07-28): "a cheap grok classifier kills regex…
if you see regex it is a smell." Routing INTENT (help requests, topic
requests, confusion, grammar questions) is judged by a cheap side model;
regex remains only as (a) fallback when this call fails/times out and
(b) surface-form spotting (did they literally use «estoy»), where pattern
matching is the correct tool rather than a smell.

MEASURED latency (2026-07-28, this machine): gemini-flash-lite-latest
0.8–1.1s (non-reasoning; default); grok-3-mini 2.4–2.7s; gemini-3.6-flash
1.8–2.8s (reasoning overhead). Two run modes (config):
- SHADOW (default): runs parallel to the tutor call — zero added reply
  latency; audits routing, corrects stale holds for the next turn.
- SIGNAL_CLASSIFIER_BLOCKING=1: classifies BEFORE routing and DOES add
  its wall time to every turn. Timeout-bounded either way; on timeout the
  turn proceeds on regex signals alone.
"""

from __future__ import annotations

import concurrent.futures
import json
import re
from typing import Any

from . import config

# Routing-intent vocabulary the mode runtime consumes. The classifier may
# ONLY emit these (anything else is dropped) — keeps select_mode testable.
INTENT_SIGNALS = frozenset({
    "help_request",       # asks how to say a word/phrase ("how do I say…", "cómo se dice…")
    "topic_request",      # asks to change topic/activity ("can we talk about…", "algo nuevo")
    "meta_comprehension", # asks what the tutor's Spanish means / grammar question
    "non_understanding",  # did not understand and is stuck (maps to meta w/o spanish_ok)
    "spanish_ok",         # produced their OWN Spanish content (not just echoing ours)
    "english_only",       # message is essentially English
    # §2.1a (BINDING, 2026-07-28) — OBSERVATIONAL, shadow-only:
    "content_offer",      # volunteers off-script meaning (not an answer to the outstanding try)
    "self_flagged_form",  # marks one of their OWN forms as uncertain («uvia (rain)», quotes)
})

# §2.1a architecture clause: these labels are measured in SHADOW only — they
# must NOT change select_mode routing until the pre-registered promotion
# gates pass (§4.3). conv_session strips them from blocking-path signals.
OBSERVATIONAL_SIGNALS = frozenset({"content_offer", "self_flagged_form"})

_SYSTEM = """You label ONE message from an adult A1 Spanish learner to their tutor.
Return STRICT JSON only: {"signals": [..]} — a subset of:
help_request, topic_request, meta_comprehension, non_understanding, spanish_ok, english_only, content_offer, self_flagged_form

Definitions:
- help_request: they ask how to say/write a word or phrase (any phrasing, any language).
- topic_request: they ask to change topic/activity or complain of repetition.
- meta_comprehension: they ask what tutor Spanish meant, or ask a grammar question.
- non_understanding: they signal they did not understand and are stuck (no real attempt).
- spanish_ok: the message contains their OWN attempted Spanish content (imperfect is fine;
  quoting the tutor's words back does not count).
- english_only: essentially all English.
- content_offer: they volunteer their OWN meaning — a description, personal fact, or new
  subject beyond a minimal answer to the tutor's question (off-script content they chose
  to attempt).
- self_flagged_form: they mark one of their OWN Spanish forms as uncertain — quotes around
  their own word, a "(english)?" gloss-guess like "uvia (rain)", or "not sure that's right".
  Asking what the TUTOR's word means is meta_comprehension, not this.

Examples (signals only):
- "I always forget how to say searching" → ["help_request"]
- "can we talk about food instead?" → ["topic_request"]
- "no entiendo" → ["non_understanding"]
- "Come esta usted. The usted makes it formal - why not estas?" → ["meta_comprehension","spanish_ok"]
- "buenas tardes. Yo busco huevos." → ["spanish_ok"]
- "estoy en mi casa. Afruera (outside?) esta muy bien. No uvia (rain) hoy" → ["spanish_ok","content_offer","self_flagged_form"]
- "yo no tengo cafe. Yo hacer (I am making?) deysayunas. Papas y savoyes (onions)" → ["spanish_ok","content_offer","self_flagged_form"]
- "Mi amigo Paul esta en su bote hoy" → ["spanish_ok","content_offer"]
- "Estoy bien. no se si «bien» es correcto aqui" → ["spanish_ok","self_flagged_form"]
Do NOT label help_request as non_understanding. Do NOT drop spanish_ok when they produced real Spanish and also asked a grammar question. content_offer is NOT a plain direct answer to the tutor's question.

Multiple labels allowed. Empty list is valid. JSON only, no prose."""

_TIMEOUT_S = float(getattr(config, "SIGNAL_CLASSIFIER_TIMEOUT_S", 2.5))
_JSON_RE = re.compile(r"\{.*\}", re.S)


def classifier_enabled(model: str | None = None) -> bool:
    m = (model if model is not None else getattr(config, "SIGNAL_CLASSIFIER_MODEL", "off"))
    return bool(m) and str(m).strip().lower() not in ("off", "0", "false", "none", "")


def _call(model: str, learner: str) -> tuple[set[str], dict[str, Any]]:
    client = config.make_client_for(model)
    caps = config.caps_for(model)
    resp = client.messages.create(
        model=caps.model,
        max_tokens=100,
        system=_SYSTEM,
        messages=[{"role": "user", "content": (learner or "")[:2000]}],
    )
    text = "".join(
        getattr(b, "text", "") for b in (resp.content or [])
        if getattr(b, "type", "") == "text"
    )
    m = _JSON_RE.search(text or "")
    if not m:
        # Distinct from a legitimate empty label set — promotion reliability
        # math must not count model failures as "no intent" (Grok round-3)
        return set(), {"input_tokens": 0, "output_tokens": 0,
                       "outcome_hint": "parse_fail"}
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return set(), {"input_tokens": 0, "output_tokens": 0,
                       "outcome_hint": "parse_fail"}
    raw = data.get("signals") or []
    out = {str(s).strip().lower() for s in raw if str(s).strip()}
    out &= INTENT_SIGNALS
    # non_understanding maps onto the meta-without-spanish_ok arming contract.
    # Mixed case (Grok round-2 M1): "no entiendo… also *busco huevos*" — keep
    # the production evidence; treat as a grammar/meta moment, NOT pure stuck.
    if "non_understanding" in out:
        out.add("meta_comprehension")
        out.discard("non_understanding")
        # keep spanish_ok if the model also saw real production
    usage = getattr(resp, "usage", None)
    return out, {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
    }


def classify_signals(
    learner: str, *, model: str | None = None
) -> tuple[set[str], dict[str, Any]] | None:
    """Intent signals for one learner utterance, or None (disabled/failed).

    None → caller proceeds on regex signals alone. Never raises, never
    exceeds the timeout: the classifier must not block or break a turn.
    """
    m = model if model is not None else getattr(config, "SIGNAL_CLASSIFIER_MODEL", "off")
    if not classifier_enabled(m) or not (learner or "").strip():
        return None
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_call, str(m), learner)
            out, usage = fut.result(timeout=_TIMEOUT_S)
        if usage.get("outcome_hint") == "parse_fail":
            outcome = "parse_fail"
        else:
            outcome = "ok" if out else "empty"
        return out, {"model": str(m), "usage": usage, "outcome": outcome}
    except concurrent.futures.TimeoutError:
        # Promotion metrics need timeout distinct from parse/transport failure
        return set(), {"model": str(m), "usage": {}, "outcome": "timeout"}
    except Exception as e:
        return set(), {
            "model": str(m), "usage": {},
            "outcome": "error", "error": type(e).__name__,
        }
