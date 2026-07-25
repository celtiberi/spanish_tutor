"""Structured multi-part tutor replies.

The teaching model should answer in labeled parts so we can:
  - force a recast before stretching the lesson
  - optionally show deeper explanation
  - keep conversation moving
  - log/analyze which moves happened

Learner-facing text is composed from parts (never dumps schema jargon).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Ordered for composition (how the student should read the turn)
PART_ORDER = (
    "acknowledge",  # meaning received / rapport
    "recast",       # clean model of what they meant (focus-on-form)
    "explain",      # optional brief/deep form note
    "continue",     # main next conversational beat / stretch
)

PART_TYPES = set(PART_ORDER)

# <recast>...</recast> or <recast brief="true">...</recast>
_PART_RE = re.compile(
    r"<(acknowledge|recast|explain|continue)"
    r"(\s[^>]*)?>"
    r"(.*?)"
    r"</\1>",
    re.S | re.I,
)
_OUTER_RE = re.compile(r"</?tutor\s*>", re.I)
_DEPTH_RE = re.compile(r'\bdepth\s*=\s*["\']?(brief|deep)["\']?', re.I)


@dataclass
class TutorParts:
    acknowledge: str = ""
    recast: str = ""
    explain: str = ""
    explain_depth: str = "brief"  # brief | deep
    continue_: str = ""  # "continue" is reserved-ish; use continue_
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
        if self.continue_.strip():
            d["continue"] = self.continue_.strip()
        d["structured"] = self.raw_had_structure
        return d

    def has_recast(self) -> bool:
        return bool(self.recast.strip())


def _clean_part_text(s: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", (s or "").strip())


def parse_tutor_response(raw: str) -> TutorParts:
    """Extract structured parts; if none found, whole text is `continue`."""
    text = (raw or "").strip()
    text = _OUTER_RE.sub("", text).strip()
    parts = TutorParts()
    matches = list(_PART_RE.finditer(text))
    if not matches:
        parts.continue_ = _clean_part_text(text)
        parts.raw_had_structure = False
        return parts

    parts.raw_had_structure = True
    consumed = []
    for m in matches:
        kind = m.group(1).lower()
        attrs = m.group(2) or ""
        body = _clean_part_text(m.group(3))
        consumed.append(m.span())
        if kind == "acknowledge":
            parts.acknowledge = body
        elif kind == "recast":
            parts.recast = body
        elif kind == "explain":
            parts.explain = body
            dm = _DEPTH_RE.search(attrs)
            if dm:
                parts.explain_depth = dm.group(1).lower()
        elif kind == "continue":
            parts.continue_ = body

    # Any leftover text outside tags (rare) → append to continue
    leftover = text
    for start, end in sorted(consumed, reverse=True):
        leftover = leftover[:start] + leftover[end:]
    leftover = _OUTER_RE.sub("", leftover)
    leftover = re.sub(r"\s+", " ", leftover).strip()
    if leftover and len(leftover) > 8:
        if parts.continue_:
            parts.continue_ = parts.continue_ + "\n\n" + leftover
        else:
            parts.continue_ = leftover

    return parts


def compose_visible(parts: TutorParts, *, for_ui: bool = False) -> str:
    """Plain learner-facing string (CLI / fallback).

    for_ui=False: natural paragraphs, no labels.
    """
    chunks: list[str] = []
    if parts.acknowledge.strip():
        chunks.append(parts.acknowledge.strip())
    if parts.recast.strip():
        chunks.append(parts.recast.strip())
    if parts.explain.strip():
        chunks.append(parts.explain.strip())
    if parts.continue_.strip():
        chunks.append(parts.continue_.strip())
    if not chunks and not for_ui:
        return ""
    return "\n\n".join(chunks)


def process_tutor_raw(raw: str) -> tuple[str, TutorParts]:
    """Parse + compose. Returns (visible_text, parts)."""
    parts = parse_tutor_response(raw)
    visible = compose_visible(parts)
    if not visible.strip():
        visible = (raw or "").strip()
        parts = TutorParts(continue_=visible, raw_had_structure=False)
    return visible, parts


# Prompt fragment injected into system + harness
STRUCTURED_REPLY_SPEC = """
## Structured reply (required shape)

Wrap learner-facing content in these tags (omit a tag if empty).  
The student never sees the tag names — the app assembles the message.

```
<tutor>
  <acknowledge>...</acknowledge>
  <recast>...</recast>
  <explain depth="brief">...</explain>
  <continue>...</continue>
</tutor>
```

| Part | When to use |
|------|-------------|
| **acknowledge** | Optional. Show you got their meaning / rapport. Do **not** call wrong Spanish “perfect” or “spot on.” |
| **recast** | **Required** when their Spanish had a clear form, word-order, register, or construction error (not mere accent/typo). Give the clean model of what they meant — short. |
| **explain** | Optional. `depth="brief"` (default): 1–2 lines focus-on-form. `depth="deep"` only if they asked “why?” / “is that correct?” or the same error repeated. Not a grammar lecture. |
| **continue** | **Almost always.** Next conversational beat or stretch. Keep the lesson moving unless they are blocked. |

### Priority when they produce imperfect Spanish

1. **Recast** (and optional brief explain) **before** advancing a new stretch.  
2. Do **not** skip correction just to chase `next_best` (e.g. leave-taking).  
3. Typos/accents alone → no recast needed; model clean form in passing if useful.  
4. Conceptual mix-ups (*va* + *está* jammed together, *me llamo es*, wrong person) → **recast required**.  
5. If they only asked for a translation of *your* Spanish, acknowledge that — still recast if they also produced a broken reply.

### Examples of bad vs good

Bad: English cheerleading (“Good job!”, “You nailed it!”, “Spot on!”) + English
frame + dual-subtitle every model, then skip form fix.  
Good (Spanish-forward; infer meaning; recast first):
```
<tutor>
  <acknowledge>¡Ah, sí! Todo va bien hoy.</acknowledge>
  <recast>Natural: **Todo va bien** — o **Todo está bien**. Una sola idea.</recast>
  <explain depth="brief">*Va bien* = how things are going; *está bien* = everything is fine. Don't mix both in one line.</explain>
  <continue>¿Y tú? ¿Cómo te va?</continue>
</tutor>
```
""".strip()
