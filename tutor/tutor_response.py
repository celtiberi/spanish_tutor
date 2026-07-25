"""Structured multi-part tutor replies.

The teaching model should answer in labeled parts so we can:
  - force a recast before stretching the lesson
  - surface model + try (teaching, not chat-buddy)
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
_OUTER_RE = re.compile(r"</?tutor\s*>", re.I)
_DEPTH_RE = re.compile(r'\bdepth\s*=\s*["\']?(brief|deep)["\']?', re.I)


@dataclass
class TutorParts:
    acknowledge: str = ""
    recast: str = ""
    explain: str = ""
    explain_depth: str = "brief"  # brief | deep
    model: str = ""
    try_: str = ""  # try is reserved in some contexts
    continue_: str = ""
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
        elif kind == "model":
            parts.model = body
        elif kind == "try":
            parts.try_ = body
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
    """Plain learner-facing string (CLI / fallback / TTS)."""
    chunks: list[str] = []
    if parts.acknowledge.strip():
        chunks.append(parts.acknowledge.strip())
    if parts.recast.strip():
        chunks.append(parts.recast.strip())
    if parts.explain.strip():
        chunks.append(parts.explain.strip())
    if parts.model.strip():
        chunks.append(parts.model.strip())
    if parts.try_.strip():
        chunks.append(parts.try_.strip())
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
  <model>...</model>
  <try>...</try>
  <continue>...</continue>
</tutor>
```

| Part | When |
|------|------|
| **acknowledge** | Meaning / rapport. Not “perfect” on wrong Spanish. |
| **recast** | Required on form/register/construction error. Clean model. |
| **explain** | Optional 1–2 lines; deep only if they asked why. |
| **model** | Usually required: 1–3 short Spanish targets. |
| **try** | Almost always: one clear production task. |
| **continue** | Optional extra beat after try. |

### Teaching (not chat-buddy)

Every turn needs a teach move: **model**, **try**, and/or **recast+retry**.
A lone open question with no model is wrong.

Bad: only “¡Hola! ¿Cómo estás?” with no models.
Good: model **Estoy bien / Estoy más o menos** then try “¿Cómo estás?”

After a recast, **try** = same form again — do not jump topics.

### Example

```
<tutor>
  <acknowledge>¡Ah, sí! Todo bien hoy.</acknowledge>
  <recast>Natural: **Todo va bien** — o **Todo está bien**.</recast>
  <explain depth="brief">Pick one pattern — don't mix va + está.</explain>
  <model>**Todo va bien.** / **Estoy bien.**</model>
  <try>Di una: **Todo va bien** o **Estoy bien**.</try>
</tutor>
```
""".strip()
