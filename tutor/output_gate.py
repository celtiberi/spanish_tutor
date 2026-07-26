"""Generate-then-verify: gate the *tutor output*, not a topic ladder.

After the model speaks, code checks for failures that prompts cannot self-guarantee:
  - no teach move (model/try/recast)
  - English wall (tutor turn mostly English when it should be Spanish-forward)
  - probe loop (re-asking something session memory already covered)

On failure the session may do **one** bounded re-ask with a specific fault.
See docs/reviews-claude-idea-spar.md (Claude: gate output, not decision).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .pedagogy_contract import evaluate_turn

# Tutor turn should be mostly Spanish after open; open may frame in English.
MIN_SPANISH_RATIO = 0.35
MIN_SPANISH_RATIO_OPEN = 0.15  # allow English frame on placement open

# Tokens that count as Spanish-ish (novice chat)
_ES_RE = re.compile(
    r"\b(hola|buenos|buenas|estoy|estás|estas|está|esta|somos|soy|eres|es|"
    r"llamo|llamas|llaman|gracias|adiós|adios|hasta|luego|mañana|manana|"
    r"cómo|como|dónde|donde|qué|que|quién|quien|por|favor|sí|si|no|"
    r"bien|mal|más|mas|menos|muy|también|tambien|aquí|aqui|allí|alli|"
    r"me|te|se|nos|gusto|gusta|gustan|tengo|tiene|quiero|prefiero|"
    r"café|cafe|bote|barco|música|musica|comida|río|rio|de|"
    r"perdón|perdon|claro|vale|bueno|mucho|poco|hoy|ahora|"
    r"usted|señor|senor|señora|senora|amigo|amiga)\b",
    re.I,
)
_EN_RE = re.compile(
    r"\b(the|and|you|your|are|is|am|how|what|where|when|why|this|that|"
    r"with|from|have|has|will|would|should|could|please|try|say|means|"
    r"name|hello|good|fine|well|right|already|asked|sorry|english|"
    r"spanish|tutor|practice|sentence|word|phrase)\b",
    re.I,
)

_PROBE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ask_how", re.compile(r"c[oó]mo\s+est[aá]s|how\s+are\s+you", re.I)),
    ("ask_name", re.compile(r"c[oó]mo\s+te\s+llamas|what(?:'s|\s+is)\s+your\s+name", re.I)),
    ("ask_origin", re.compile(r"de\s+d[oó]nde\s+eres|where\s+(?:are\s+you|you\s+from)", re.I)),
    ("ask_gusta", re.compile(r"qu[eé]\s+te\s+gusta|do\s+you\s+like", re.I)),
]


@dataclass
class OutputGateResult:
    ok: bool
    faults: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    spanish_ratio: float | None = None
    repair_instruction: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "faults": list(self.faults),
            "notes": list(self.notes),
            "spanish_ratio": self.spanish_ratio,
            "repair_instruction": self.repair_instruction,
        }


def tutor_spanish_ratio(text: str) -> float | None:
    """Fraction of (es+en) content tokens that look Spanish. None if too short."""
    t = text or ""
    # Drop markdown bold/italics noise
    t = re.sub(r"[*_`#]+", " ", t)
    es = len(_ES_RE.findall(t))
    en = len(_EN_RE.findall(t))
    if es + en < 3:
        return None
    return es / (es + en)


def detect_tutor_probe_keys(text: str) -> set[str]:
    """Which social probes the tutor turn is asking."""
    low = text or ""
    found: set[str] = set()
    for key, pat in _PROBE_PATTERNS:
        if pat.search(low):
            found.add(key)
    return found


def check_output_gate(
    parts: dict | None,
    visible: str,
    *,
    is_open: bool = False,
    already_asked: set[str] | list[str] | None = None,
    already_shown: set[str] | list[str] | None = None,
    mode: str | None = None,
    image_present: bool = False,
    require_recast: bool = False,
) -> OutputGateResult:
    """Hard checks on the composed tutor turn (+ optional per-mode contracts)."""
    parts = parts or {}
    asked = set(already_asked or [])
    shown = set(already_shown or [])
    faults: list[str] = []
    notes: list[str] = []
    mode_l = (mode or "").strip().lower()

    ped = evaluate_turn(
        parts,
        is_open=is_open or mode_l == "placement",
        structured=bool(parts.get("structured")),
        visible=visible,
    )
    for v in ped.violations:
        faults.append(v)
    notes.extend(ped.notes)

    # Form error this turn → must expose a short recast (not only soft rewrite in ack)
    if require_recast or mode_l in ("cf_recast", "form_focus"):
        has_recast = bool((parts.get("recast") or "").strip())
        if not has_recast:
            faults.append("gate:missing_recast")
            notes.append("gate:missing_recast")

    # Per-mode contracts (teaching system v2)
    if mode_l == "association" and not image_present:
        # Soft: prefer image; do not hard-fail if cache miss (warm later)
        notes.append("mode:association_no_image_cache")
    if mode_l == "form_focus":
        has_contrast = bool(
            (parts.get("explain") or "").strip()
            or (parts.get("recast") or "").strip()
            or (parts.get("model") or "").strip()
        )
        if not has_contrast:
            faults.append("gate:form_focus_needs_model")
            notes.append("gate:form_focus_needs_model")
    if mode_l == "comprehension_check":
        try_t = (parts.get("try") or parts.get("continue") or "").lower()
        if not any(x in try_t for x in ("?", "¿", " o ", "sí", "si", "no")):
            faults.append("gate:comprehension_needs_check")
            notes.append("gate:comprehension_needs_check")

    # English wall on learner-facing text (model+try+ack+recast+explain)
    blob = " ".join(
        str(parts.get(k) or "")
        for k in ("acknowledge", "recast", "explain", "model", "try", "continue")
    )
    if not blob.strip():
        blob = visible or ""
    ratio = tutor_spanish_ratio(blob)
    min_r = MIN_SPANISH_RATIO_OPEN if is_open else MIN_SPANISH_RATIO
    if ratio is not None and ratio < min_r:
        faults.append("gate:english_wall")
        notes.append(f"gate:english_wall ratio={ratio:.2f}<{min_r}")

    # Loop: tutor re-asks a probe we already asked OR they already answered
    probe_blob = " ".join(
        str(parts.get(k) or "") for k in ("try", "continue", "model", "acknowledge")
    )
    probes = detect_tutor_probe_keys(probe_blob)
    loop_hits: list[str] = []
    for p in probes:
        if p in asked:
            loop_hits.append(p)
        # They already showed the skill this session
        skill_map = {
            "ask_how": "estoy",
            "ask_name": "name",
            "ask_origin": "origin",
            "ask_gusta": "gusta",
        }
        sk = skill_map.get(p)
        if sk and sk in shown:
            loop_hits.append(f"{p}/shown:{sk}")
    if loop_hits:
        faults.append("gate:probe_loop")
        notes.append("gate:probe_loop " + ",".join(sorted(set(loop_hits))))

    ok = not faults
    repair = ""
    if not ok:
        bits = []
        if any(f.startswith("pedagogy:") for f in faults):
            bits.append(
                "Include a clear Spanish <model> and a real <try> (question or invite)."
            )
        if "gate:english_wall" in faults:
            bits.append(
                "Rewrite Spanish-forward: most words in Spanish. English only as a short lifeline."
            )
        if "gate:probe_loop" in faults:
            bits.append(
                "Do NOT re-ask how they are / their name / origin / likes if already covered. "
                "Apologize briefly if needed and advance to new ground."
            )
        if "gate:form_focus_needs_model" in faults:
            bits.append(
                "Form focus: show clear correct Spanish model (and brief contrast if helpful)."
            )
        if "gate:missing_recast" in faults:
            bits.append(
                "REQUIRED: add a short <recast>…</recast> with the clean Spanish form "
                "(one line). Then continue the chat — do not only fix it silently in acknowledge."
            )
        if "gate:comprehension_needs_check" in faults:
            bits.append("Ask a yes/no or A/B meaning check, not a free open question only.")
        repair = " ".join(bits) or "Fix the listed gate faults and reply again."

    return OutputGateResult(
        ok=ok,
        faults=faults,
        notes=notes,
        spanish_ratio=ratio,
        repair_instruction=repair,
    )


def repair_user_message(gate: OutputGateResult, previous_raw: str) -> str:
    """One-shot repair prompt after a failed gate."""
    return (
        "(harness) OUTPUT GATE FAILED — rewrite your full <tutor> reply once.\n"
        f"Faults: {', '.join(gate.faults)}\n"
        f"Fix: {gate.repair_instruction}\n"
        "Do not mention the gate, harness, or faults to the learner.\n"
        "Previous attempt (do not repeat its mistakes):\n"
        f"{(previous_raw or '')[:2000]}\n"
    )
