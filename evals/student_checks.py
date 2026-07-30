"""Mechanical post-checks over a completed AI-student transcript (R4,
docs/reviews-system-review-20260730.md). No LLM judging — pure scans, the
conv_checks convention: findings prefixed WARN are advisory; any non-WARN
finding fails the session.

Transcript row shape (tutor/ai_student.py report["transcript"]; the open
turn is row 0 with learner="(session open)"):

    {"learner": str, "reply": str, "notes": [str, ...], "parts": dict?}

Checks:
  - fixation (HARD): a tutor try/question repeated near-identically across
    turns — the probe_loop failure class the gate is supposed to kill
    (2026-07-30 session chain, R4). Token-Jaccard > FIXATION_JACCARD on
    fold_prose tokens, tries >= FIXATION_MIN_TOKENS tokens.
  - still_fail (HARD): turns whose notes carry output_gate_still_fail —
    a reply shipped with unrepaired critical faults (gate obligation, R1).
  - probe_on_known (WARN): comprehension-check questions (A/B «... o ...»
    or «¿Sí o no?») re-probing a frame session memory already recorded as
    asked/shown (mem_asked=/mem_shown= notes) — the R2 checker-budget
    signal, advisory until R2 lands a law paragraph.
  - english_wall (WARN): turns whose notes carry gate:english_wall — the
    gate already repairs/escalates these; here we only count drift.
"""

from __future__ import annotations

import re

from tutor.textnorm import fold_lexical, fold_prose

FIXATION_JACCARD = 0.85
FIXATION_MIN_TOKENS = 6

# Question spans: «¿...?» pairs first, then bare ...? sentence tails.
_INVERTED_Q_RE = re.compile(r"¿[^¿?]*\?")
_TAIL_Q_RE = re.compile(r"[^.!?¿]*\?")

# Comprehension-check shapes (mirrors the gate's comprehension_check
# contract, tutor/output_gate.py: try must contain ?/¿/« o »/sí/no).
_AB_PROBE_RE = re.compile(r"\bo\b", re.I)  # applied inside a question span
_SI_O_NO_RE = re.compile(r"\bs[ií],?\s+o\s+no\b", re.I)

# mem_* registry notes (tutor/turn_events.py MEM_ASKED/MEM_SHOWN render:
# "mem_asked=" + ",".join(keys), "—" when empty).
_MEM_NOTE_RE = re.compile(r"^mem_(?:asked|shown)=(.*)$")

# Topic-key tokens that name frames/control states, not probeable content
# (session_memory key vocabulary: ask_how, cf_recast, spanish_ok, ...).
_KEY_STOPWORDS = frozenset({
    "ask", "what", "topic", "placement", "greet", "cf", "recast",
    "spanish", "ok", "how", "name", "origin", "gusta", "si", "no", "o",
})

# The four social probes keep canonical Spanish/English surface patterns
# (same shapes as tutor/output_gate.py _PROBE_PATTERNS — inlined; that
# table is module-private and gate-owned).
_SOCIAL_PROBE_RES: dict[str, re.Pattern[str]] = {
    "ask_how": re.compile(r"c[oó]mo\s+est[aá]s|how\s+are\s+you", re.I),
    "ask_name": re.compile(r"c[oó]mo\s+te\s+llamas|what(?:'s|\s+is)\s+your\s+name", re.I),
    "ask_origin": re.compile(r"de\s+d[oó]nde\s+eres|where\s+(?:are\s+you|you\s+from)", re.I),
    "ask_gusta": re.compile(r"qu[eé]\s+te\s+gusta|do\s+you\s+like", re.I),
}


def _turn_rows(transcript: list[dict]) -> list[dict]:
    return [t for t in (transcript or []) if isinstance(t, dict)]


def _question_spans(reply: str) -> list[str]:
    """Every question in a tutor reply, «¿...?» pairs preferred."""
    text = reply or ""
    spans = [m.group(0).strip() for m in _INVERTED_Q_RE.finditer(text)]
    rest = _INVERTED_Q_RE.sub(" ", text)
    for m in _TAIL_Q_RE.finditer(rest):
        s = m.group(0).strip()
        if s and len(s) > 1:
            spans.append(s)
    return [s for s in spans if s]


def _tries(turn: dict) -> list[str]:
    """Candidate tutor tries: structured parts first, else reply questions.

    Structured parts are authoritative when present (the gate itself reads
    parts["try"]/parts["continue"]); question spans cover transcripts made
    without parts.
    """
    out: list[str] = []
    parts = turn.get("parts") or {}
    for k in ("try", "continue"):
        v = str(parts.get(k) or "").strip()
        if v:
            out.append(v)
    if not out:
        out = _question_spans(str(turn.get("reply") or ""))
    return out


def _tokens(text: str) -> set[str]:
    return set(fold_prose(text).split())


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def check_fixation(transcript: list[dict]) -> list[str]:
    """Near-identical tutor try repeated in a later turn → HARD finding."""
    rows = _turn_rows(transcript)
    seen: list[tuple[int, str, set[str]]] = []
    findings: list[str] = []
    flagged: set[tuple[int, int]] = set()
    for j, turn in enumerate(rows):
        for try_text in _tries(turn):
            toks = _tokens(try_text)
            if len(toks) < FIXATION_MIN_TOKENS:
                continue
            for i, earlier_text, earlier_toks in seen:
                if i == j or (i, j) in flagged:
                    continue
                sim = _jaccard(earlier_toks, toks)
                if sim > FIXATION_JACCARD:
                    flagged.add((i, j))
                    findings.append(
                        f"turns {i}->{j}: repeated try (jaccard={sim:.2f}) "
                        f"{earlier_text!r} ~ {try_text!r}"
                    )
            seen.append((j, try_text, toks))
    return findings


def check_still_fail(transcript: list[dict]) -> list[str]:
    """output_gate_still_fail notes → HARD finding per offending turn."""
    findings: list[str] = []
    for i, turn in enumerate(_turn_rows(transcript)):
        for n in turn.get("notes") or []:
            s = str(n)
            if "output_gate_still_fail" in s:
                findings.append(f"turn {i}: {s}")
    return findings


def _mem_keys(turn: dict) -> set[str]:
    keys: set[str] = set()
    for n in turn.get("notes") or []:
        m = _MEM_NOTE_RE.match(str(n))
        if not m:
            continue
        for k in m.group(1).split(","):
            k = k.strip()
            if k and k != "—":
                keys.add(k)
    return keys


def _key_content_tokens(key: str) -> set[str]:
    """Lexical content of a registry key (location:bote → {bote, location})."""
    raw = re.split(r"[:_\s]+", fold_lexical(key))
    return {t for t in raw if len(t) >= 3 and t not in _KEY_STOPWORDS}


def _probes(reply: str) -> list[str]:
    """Comprehension-check questions: A/B alternatives or sí-o-no."""
    out: list[str] = []
    for q in _question_spans(reply):
        folded = fold_lexical(q)
        if _SI_O_NO_RE.search(folded) or _AB_PROBE_RE.search(folded):
            out.append(q)
    return out


def check_probe_on_known(transcript: list[dict]) -> list[str]:
    """Probe question re-testing a mem_asked/mem_shown frame → WARN."""
    rows = _turn_rows(transcript)
    findings: list[str] = []
    known: set[str] = set()
    for i, turn in enumerate(rows):
        for probe in _probes(str(turn.get("reply") or "")):
            folded = fold_lexical(probe)
            probe_tokens = set(re.split(r"[^a-zñ]+", folded)) - {""}
            hits: list[str] = []
            for key in sorted(known):
                pat = _SOCIAL_PROBE_RES.get(key)
                if pat is not None and pat.search(folded):
                    hits.append(key)
                    continue
                if _key_content_tokens(key) & probe_tokens:
                    hits.append(key)
            if hits:
                findings.append(
                    f"WARN turn {i}: probe on known {hits} — {probe!r}"
                )
        # Keys become "known" only for LATER turns: this turn's registry
        # notes describe state after its own reply was allowed through.
        known |= _mem_keys(turn)
    return findings


def check_english_wall(transcript: list[dict]) -> list[str]:
    """gate:english_wall notes → WARN finding per offending turn."""
    findings: list[str] = []
    for i, turn in enumerate(_turn_rows(transcript)):
        for n in turn.get("notes") or []:
            s = str(n)
            if "gate:english_wall" in s:
                findings.append(f"WARN turn {i}: {s}")
    return findings


CHECKS = {
    "fixation": check_fixation,
    "still_fail": check_still_fail,
    "probe_on_known": check_probe_on_known,
    "english_wall": check_english_wall,
}


def run_student_checks(transcript: list[dict]) -> tuple[dict, bool]:
    """(findings-by-check, passed). Fail bar: any non-WARN finding —
    i.e. nonzero fixation or still_fail (probe_on_known / english_wall
    are WARN-only counters)."""
    findings: dict[str, list[str]] = {}
    for name, fn in CHECKS.items():
        out = fn(transcript)
        if out:
            findings[name] = out
    hard = {
        k: v
        for k, v in findings.items()
        if any(not str(f).startswith("WARN") for f in v)
    }
    return findings, not hard
