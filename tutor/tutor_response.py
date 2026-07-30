"""Structured multi-part tutor replies.

The teaching model should answer in labeled parts so we can:
  - force a recast before stretching the lesson
  - surface model + try (teaching, not chat-buddy)
  - optionally show deeper explanation
  - keep conversation moving
  - log/analyze which moves happened

Learner-facing text is composed from parts (never dumps schema jargon).

Sheet JSON / tool dumps in the model output are a **model/prompt fault**,
not something to silently scrub into a successful turn. Detection lives in
`output_gate.detect_sheet_leak` → repair. This module only parses tags.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .textnorm import SPANISH_LETTERS

# Ordered for composition (how the student should read the turn)
PART_ORDER = (
    "acknowledge",  # meaning received / rapport
    "recast",       # clean model of what they meant (focus-on-form)
    "explain",      # optional brief/deep form note
    "model",        # input: target phrases to hear/use
    "try",          # one clear production task
    "continue",     # optional extra beat after try
)

PART_TYPES = set(PART_ORDER)

_PART_RE = re.compile(
    r"<(acknowledge|recast|explain|model|try|continue)"
    r"(\s[^>]*)?>"
    r"(.*?)"
    r"</\1>",
    re.S | re.I,
)
# Unclosed part when the model cuts off before </try>
_PART_OPEN_RE = re.compile(
    r"<(acknowledge|recast|explain|model|try|continue)"
    r"(\s[^>]*)?>"
    r"(.*?)(?=</?(?:acknowledge|recast|explain|model|try|continue|tutor)\b|$)",
    re.S | re.I,
)
_OUTER_RE = re.compile(r"</?tutor\s*>", re.I)
# Optional tutor-declared teach image: <image concept="sol"/> or
# <image>sol</image>. The MODEL decides if a picture helps this teaching
# moment (replaces regex noun-scanning, which put a sun on «Hola Marisol»).
# Concept token FAILS CLOSED (Grok countersign 2026-07-28): full-token match
# only — 'sol2', 'el-sol', 'http://…' must not silently truncate into a
# billable generate. Quoted attr required; body form may join two words.
# Letter class from textnorm (Phase 2) + underscore for concept ids.
_CONCEPT_TOKEN = rf"[{SPANISH_LETTERS}_]{{1,24}}"
_IMAGE_SELF_RE = re.compile(
    rf"<image\b[^>]*\bconcept\s*=\s*[\"']({_CONCEPT_TOKEN})[\"'][^>]*/?>"
    rf"(?:\s*</image>)?",
    re.I,
)
_IMAGE_BODY_RE = re.compile(
    rf"<image\b[^>]*>\s*({_CONCEPT_TOKEN}(?:\s{_CONCEPT_TOKEN})?)\s*</image>",
    re.I,
)
_IMAGE_ANY_RE = re.compile(r"</?image\b[^>]*/?>", re.I)


def _extract_image_concept(text: str) -> str:
    """First well-formed image tag in DOCUMENT order; empty if none."""
    candidates: list[tuple[int, str]] = []
    for rx in (_IMAGE_SELF_RE, _IMAGE_BODY_RE):
        m = rx.search(text or "")
        if m:
            candidates.append((m.start(), (m.group(1) or "").strip()))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1].lower().replace(" ", "_")
_DEPTH_RE = re.compile(r'\bdepth\s*=\s*["\']?(brief|deep)["\']?', re.I)
_ANY_PART_TAG_RE = re.compile(
    r"</?(?:tutor|acknowledge|recast|explain|model|try|continue)(?:\s[^>]*)?>",
    re.I,
)


@dataclass
class TutorParts:
    acknowledge: str = ""
    recast: str = ""
    explain: str = ""
    explain_depth: str = "brief"  # brief | deep
    model: str = ""
    try_: str = ""  # try is reserved in some contexts
    continue_: str = ""
    # Tutor-declared teach image (optional — the model's pedagogical DECISION;
    # empty means no image this turn, which is always a valid choice)
    image_concept: str = ""
    raw_had_structure: bool = False
    extras: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.acknowledge.strip():
            d["acknowledge"] = self.acknowledge.strip()
        if self.recast.strip():
            d["recast"] = self.recast.strip()
        if self.explain.strip():
            d["explain"] = self.explain.strip()
            d["explain_depth"] = self.explain_depth
        if self.model.strip():
            d["model"] = self.model.strip()
        if self.try_.strip():
            d["try"] = self.try_.strip()
        if self.continue_.strip():
            d["continue"] = self.continue_.strip()
        if self.image_concept.strip():
            d["image_concept"] = self.image_concept.strip()
        d["structured"] = self.raw_had_structure
        return d

    def has_recast(self) -> bool:
        return bool(self.recast.strip())

    def has_teach_move(self) -> bool:
        """At least one of model / try / recast (actual teaching)."""
        return bool(
            self.model.strip() or self.try_.strip() or self.recast.strip()
        )


def _clean_part_text(s: str) -> str:
    """Whitespace only — do not strip model faults here."""
    return re.sub(r"\n{3,}", "\n\n", (s or "").strip())


def _assign_part(parts: TutorParts, kind: str, body: str, attrs: str = "") -> None:
    body = _clean_part_text(body)
    if not body:
        return
    if kind == "acknowledge":
        parts.acknowledge = body
    elif kind == "recast":
        parts.recast = body
    elif kind == "explain":
        parts.explain = body
        dm = _DEPTH_RE.search(attrs or "")
        if dm:
            parts.explain_depth = dm.group(1).lower()
    elif kind == "model":
        parts.model = body
    elif kind == "try":
        parts.try_ = body
    elif kind == "continue":
        parts.continue_ = body


def parse_tutor_response(raw: str) -> TutorParts:
    """Extract structured parts; if none found, whole text is `continue`."""
    text = (raw or "").strip()
    text = _OUTER_RE.sub("", text).strip()
    parts = TutorParts()
    # Capture the optional tutor-declared image (first tag in document
    # order), then strip ALL image tags so they can never leak into visible
    # text (even inside a part body)
    parts.image_concept = _extract_image_concept(text)
    text = _IMAGE_SELF_RE.sub(" ", text)
    text = _IMAGE_BODY_RE.sub(" ", text)
    text = _IMAGE_ANY_RE.sub(" ", text).strip()
    matches = list(_PART_RE.finditer(text))
    consumed: list[tuple[int, int]] = []

    if matches:
        parts.raw_had_structure = True
        for m in matches:
            kind = m.group(1).lower()
            attrs = m.group(2) or ""
            body = m.group(3)
            consumed.append(m.span())
            _assign_part(parts, kind, body, attrs)
    else:
        # Unclosed tags only (stream cut off)
        open_matches = list(_PART_OPEN_RE.finditer(text))
        if open_matches:
            parts.raw_had_structure = True
            for m in open_matches:
                _assign_part(parts, m.group(1).lower(), m.group(3), m.group(2) or "")
                consumed.append(m.span())
        else:
            parts.continue_ = _clean_part_text(text)
            parts.raw_had_structure = False
            return parts

    # Closed parts present: also take unclosed trailing tags (e.g. open <try>)
    for m in _PART_OPEN_RE.finditer(text):
        span = m.span()
        if any(span[0] >= a and span[1] <= b for a, b in consumed):
            continue
        if any(span[0] == a for a, _b in consumed):
            continue
        kind = m.group(1).lower()
        already = {
            "acknowledge": parts.acknowledge,
            "recast": parts.recast,
            "explain": parts.explain,
            "model": parts.model,
            "try": parts.try_,
            "continue": parts.continue_,
        }.get(kind, "")
        if already:
            continue
        _assign_part(parts, kind, m.group(3), m.group(2) or "")
        consumed.append(span)

    # Leftover outside tags: only keep if it looks like more learner speech.
    # Sheet dumps / fences are a gate fault on *raw* — do not promote them to continue.
    leftover = text
    for start, end in sorted(consumed, reverse=True):
        leftover = leftover[:start] + leftover[end:]
    leftover = _OUTER_RE.sub("", leftover)
    leftover = _ANY_PART_TAG_RE.sub(" ", leftover)
    leftover = re.sub(r"\s+", " ", leftover).strip()
    if leftover and len(leftover) > 8 and not _leftover_is_internal(leftover):
        if parts.continue_:
            parts.continue_ = parts.continue_ + "\n\n" + leftover
        else:
            parts.continue_ = leftover

    return parts


def _leftover_is_internal(s: str) -> bool:
    """True if text outside tags is not learner-facing speech (parser discard only).

    Detection of the fault still happens on full raw via output_gate.
    """
    t = (s or "").strip()
    if not t:
        return True
    low = t.lower()
    if t.lstrip().startswith("```") or t.lstrip().startswith("{"):
        return True
    if any(
        k in low
        for k in (
            "active_error_focus",
            "resolved_streak",
            "solid_uses",
            "error_patterns",
            "update_character_sheet",
            '"confidence"',
        )
    ):
        return True
    if t.count("{") >= 2 and t.count('"') >= 4:
        return True
    return False


def compose_visible(parts: TutorParts, *, for_ui: bool = False) -> str:
    """Plain learner-facing string (CLI / fallback / TTS)."""
    chunks: list[str] = []
    if parts.acknowledge.strip():
        chunks.append(parts.acknowledge.strip())
    if parts.recast.strip():
        chunks.append(parts.recast.strip())
    # Model BEFORE explain (2026-07-29 encantado incident: the fixed
    # order put the "why" of a new word ahead of the word itself — the
    # learner read an anchor with no referent). Meet the form, then
    # anchor it; for recasts the corrected sentence already precedes.
    if parts.model.strip():
        chunks.append(parts.model.strip())
    if parts.explain.strip():
        chunks.append(parts.explain.strip())
    if parts.try_.strip():
        chunks.append(parts.try_.strip())
    if parts.continue_.strip():
        chunks.append(parts.continue_.strip())
    if not chunks and not for_ui:
        return ""
    return "\n\n".join(chunks)


def compose_raw(parts: dict) -> str:
    """Rebuild a minimal <tutor> raw from a parts dict — the still_fail
    floor's part-surgery primitive (docs/reviews-system-review-20260730.md:
    a repeated probe lives in the try/continue parts; dropping them and
    re-gating the remainder beats shipping a known-bad question). Only the
    six learner-facing part tags are reconstructed; image/tool markup does
    not survive surgery (an image alongside a stripped turn is settled
    separately, §1.1b)."""
    chunks: list[str] = []
    for k in ("acknowledge", "recast", "model", "explain", "try", "continue"):
        v = str(parts.get(k) or "").strip()
        if v:
            chunks.append(f"<{k}>{v}</{k}>")
    return "<tutor>" + "\n".join(chunks) + "</tutor>"


def process_tutor_raw(raw: str) -> tuple[str, TutorParts]:
    """Parse + compose. Returns (visible_text, parts)."""
    parts = parse_tutor_response(raw)
    visible = compose_visible(parts)
    if not visible.strip():
        # Never re-inject `raw`: a tag-only reply (e.g. just <image …/>) must
        # not leak markup to the learner, and the parsed image_concept must
        # survive (Grok countersign 2026-07-28: leaked tag + lost concept).
        # Plain unstructured prose never lands here — the parser routes it
        # into `continue` and compose keeps it.
        visible = ""
    return visible, parts
