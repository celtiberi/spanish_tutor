"""Mechanical post-checks over a completed AI-student transcript (R4,
docs/reviews-system-review-20260730.md). No LLM judging — pure scans, the
conv_checks convention: findings prefixed WARN are advisory; any non-WARN
finding fails the session.

S11 (USER-ruled 2026-08-03, docs/reviews-full-code-audit-20260803.md):
this file is now THE home of every teaching-opinion check the runtime
output gate used to run.  The gate keeps only plumbing (gate:truncated +
gate:sheet_leak); the checks below judge whether pedagogy + prompts are
working, over transcripts, after the fact.  The teaching rules themselves
stay in PEDAGOGY §2.

Transcript row shape (tutor/ai_student.py report["transcript"]; the open
turn is row 0 with learner="(session open)"):

    {"learner": str, "reply": str, "notes": [str, ...], "parts": dict?}

Severity ledger (HARD = a non-WARN finding fails the session; decided per
check, S11 chunk-4 execution — chunk-2's HARD set minus the deleted
runtime faults, plus per-check calls for the migrated checks):

  HARD:
  - fixation: near-identical tutor try repeated across turns (R4 defect).
  - still_fail rows carrying gate:truncated (the surviving member of
    chunk-2's HARD set — cluster_veto/pedagogy:* died as runtime faults;
    their transcript-level successors are judged by their own checks).
  - cluster_intro: two same-theme table keys FIRST-appearing in one tutor
    turn (PEDAGOGY §2.2 one-new-item law; mechanical over the table).
  - teach_shape no_teach_move on a STRUCTURED turn, and a structured OPEN
    (row 0) without both model+try (contract shapes; mechanical).

  WARN (counted, never a session FAIL):
  - probe_repeat: a social-probe or topic-key try re-asked in a later turn
    (chunk-2 retune: try/continue parts ONLY; no due-exemption data exists
    transcript-side, so advisory).
  - english_wall: tutor turn mostly English (lexicon ratio; row 0 uses the
    true-zero floor since blank-open orientation is legitimately English).
  - teach_shape recast_without_try (incomplete focus-on-form).
  - exposure advisories: bare unscaffolded first appearance of a table
    key; re-gloss of a key already glossed in an earlier turn (no
    retrieval-failure data transcript-side, so advisory).
  - still_fail rows for anything but gate:truncated (incl. legacy fault
    ids in historical transcripts).
"""

from __future__ import annotations

import re

from tutor.textnorm import fold_lexical, fold_prose

FIXATION_JACCARD = 0.85
FIXATION_MIN_TOKENS = 6

# Question spans: «¿...?» pairs first, then bare ...? sentence tails.
_INVERTED_Q_RE = re.compile(r"¿[^¿?]*\?")
_TAIL_Q_RE = re.compile(r"[^.!?¿]*\?")

# Meaning-quiz shape.  The old `\bo\b` = comprehension-quiz assumption was
# DELETED (gate retune 2026-08-03): a natural alternative question («¿café
# o té?») is conversation, not a quiz — only the explicit sí-o-no check
# still counts as a probe shape.
_SI_O_NO_RE = re.compile(r"\bs[ií],?\s+o\s+no\b", re.I)

# mem_* registry notes (tutor/turn_events.py MEM_ASKED/MEM_SHOWN render:
# "mem_asked=" + ",".join(keys), "—" when empty).
_MEM_NOTE_RE = re.compile(r"^mem_(?:asked|shown)=(.*)$")

# still_fail severity split (S11, 2026-08-03): the runtime gate emits
# still_fail only for its two plumbing faults now; gate:truncated is the
# surviving HARD member of chunk-2's set (cluster_veto and the pedagogy
# contract died as runtime faults — their transcript-level successors are
# check_cluster_intro / check_teach_shape below).  Everything else in a
# still_fail note — gate:sheet_leak (chunk-2 classed it WARN here;
# conv_checks.gate_contract owns the hard leak scan) and legacy fault ids
# in historical transcripts — is counted as WARN.
HARD_STILL_FAIL_FAULTS = frozenset({
    "gate:truncated",
})

# Registry keys that name the historical mode router's modes, not content —
# old transcripts' mem_asked rows carry them (note_plan_try recorded the
# mode name); they must never count as a probeable known frame.
_MODE_NAME_KEYS = frozenset({
    "placement", "conversation", "cf_recast", "form_focus",
    "comprehension_check", "comprehension_repair", "association",
    "transfer",
})

# Topic-key tokens that name frames/control states, not probeable content
# (session_memory key vocabulary: ask_how, cf_recast, spanish_ok, ...).
_KEY_STOPWORDS = frozenset({
    "ask", "what", "topic", "placement", "greet", "cf", "recast",
    "spanish", "ok", "how", "name", "origin", "gusta", "si", "no", "o",
})

# The four social probes keep canonical Spanish/English surface patterns
# (the shapes the deleted runtime gate's _PROBE_PATTERNS carried — this
# file owns them now, S11).
_SOCIAL_PROBE_RES: dict[str, re.Pattern[str]] = {
    "ask_how": re.compile(r"c[oó]mo\s+est[aá]s|how\s+are\s+you", re.I),
    "ask_name": re.compile(r"c[oó]mo\s+te\s+llamas|what(?:'s|\s+is)\s+your\s+name", re.I),
    "ask_origin": re.compile(r"de\s+d[oó]nde\s+eres|where\s+(?:are\s+you|you\s+from)", re.I),
    "ask_gusta": re.compile(r"qu[eé]\s+te\s+gusta|do\s+you\s+like", re.I),
}


# ---------------------------------------------------------------------------
# English-wall lexicons + ratio (moved here from tutor/output_gate.py — S11:
# the wall is an eval opinion, not a runtime check).  Adjudicated turn-level
# wall (2026-07-26 Tier-1 #2): offending iff spanish_token_ratio <
# MIN_SPANISH_RATIO and alphabetic tokens >= MIN_ALPHA_TOKENS.  True-zero
# exemption (2026-07-28 zero-English incident): a COMPLIANT true-zero
# opening (one English framing line + glossed tiny Spanish) measures
# tl_ratio ≈ 0.32–0.40 — the OPEN row uses ZERO_MIN_SPANISH_RATIO
# (transcript-side proxy for the runtime's blank_zero register; a genuinely
# all-English open still warns).
# ---------------------------------------------------------------------------
MIN_SPANISH_RATIO = 0.50
MIN_ALPHA_TOKENS = 12
ZERO_MIN_SPANISH_RATIO = 0.25
# Short L1 sandwich in <explain>: exclude English from the ratio when explain
# has at most this many non-Spanish alphabetic tokens (A3 "≤6 words" gloss).
MAX_EXPLAIN_GLOSS_WORDS = 6

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

_ALPHA_TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")


def _strip_md_noise(text: str) -> str:
    return re.sub(r"[*_`#]+", " ", text or "")


def alphabetic_tokens(text: str) -> list[str]:
    """Learner-facing alphabetic tokens (Spanish-aware letters)."""
    return _ALPHA_TOKEN_RE.findall(text or "")


def alphabetic_token_count(text: str) -> int:
    return len(alphabetic_tokens(text))


def spanish_token_ratio(text: str) -> float:
    """Fraction of (es+en) closed-lexicon hits that look Spanish.

    Always returns a float in [0, 1]. With no lexicon hits, returns 1.0 (no
    evidence of an English wall). Pure: no I/O, no mutation. Note this is
    the closed-lexicon ratio, not a true token-level TL%.
    """
    t = _strip_md_noise(text)
    es = len(_ES_RE.findall(t))
    en = len(_EN_RE.findall(t))
    if es + en == 0:
        return 1.0
    return es / (es + en)


def explain_gloss_word_count(explain: str) -> int:
    """Non-Spanish alphabetic tokens in explain (short L1 gloss budget)."""
    return sum(
        1 for tok in alphabetic_tokens(explain) if not _ES_RE.search(tok)
    )


def _strip_en_lexicon(text: str) -> str:
    """Remove closed-list English hits so they do not affect the ratio."""
    return _EN_RE.sub(" ", text or "")


def learner_facing_blob(parts: dict | None, reply: str) -> str:
    """Learner-facing text the wall measures (composed parts, reply fallback)."""
    parts = parts or {}
    blob = " ".join(
        str(parts.get(k) or "")
        for k in ("acknowledge", "recast", "explain", "model", "try", "continue")
    )
    if not blob.strip():
        blob = reply or ""
    return blob


def ratio_blob_with_sandwich_exempt(parts: dict | None, reply: str) -> str:
    """Learner-facing text for the ratio; short <explain> L1 gloss stripped."""
    parts = parts or {}
    explain = str(parts.get("explain") or "")
    exempt = (
        bool(explain.strip())
        and explain_gloss_word_count(explain) <= MAX_EXPLAIN_GLOSS_WORDS
    )
    chunks: list[str] = []
    for k in ("acknowledge", "recast", "explain", "model", "try", "continue"):
        piece = str(parts.get(k) or "")
        if k == "explain" and exempt:
            piece = _strip_en_lexicon(piece)
        chunks.append(piece)
    blob = " ".join(chunks)
    if not blob.strip():
        blob = reply or ""
    return blob


# ---------------------------------------------------------------------------
# Shared row helpers
# ---------------------------------------------------------------------------


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

    Structured parts are authoritative when present; question spans cover
    transcripts made without parts.
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


def _structured_parts(turn: dict) -> dict | None:
    """The turn's structured parts dict, or None when unstructured."""
    parts = turn.get("parts") or {}
    if not isinstance(parts, dict) or not parts.get("structured"):
        return None
    return parts


def _truthy(parts: dict, key: str) -> bool:
    return bool(str(parts.get(key) or "").strip())


def _tokens(text: str) -> set[str]:
    return set(fold_prose(text).split())


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


_TABLE_CACHE: dict | None = None


def _association_table() -> dict:
    """The real domain association table (lazy; cached).  Lazy import keeps
    run_student_smoke's env-pinning import order safe (tutor.costs binds
    ledger paths at import time)."""
    global _TABLE_CACHE
    if _TABLE_CACHE is None:
        from pathlib import Path

        from tutor.association_table import load_association_table

        root = Path(__file__).resolve().parents[1]
        _TABLE_CACHE = load_association_table(root / "domain" / "spanish_a1")
    return _TABLE_CACHE


def _content_table_keys(table: dict) -> list[str]:
    """Table keys the exposure/cluster opinions apply to (structural
    paradigms and out-of-pack rows exempt — same pragmatics the runtime
    scan keeps for its exposure map)."""
    from tutor.association_table import STRUCTURAL_KEYS, STRUCTURAL_THEMES

    out: list[str] = []
    for key, entry in (table or {}).items():
        if not isinstance(entry, dict):
            continue
        if entry.get("in_pack") is False:
            continue
        if str(entry.get("theme") or "") in STRUCTURAL_THEMES:
            continue
        if key in STRUCTURAL_KEYS:
            continue
        out.append(key)
    return out


def _keys_in_text(keys: list[str], text: str) -> list[tuple[int, int, str]]:
    """(start, end, key) hits of table keys in text, longest-over-span
    (the «muy bien» must not also count «bien» overlap filter)."""
    from tutor.textnorm import phrase_match

    hits: list[tuple[int, int, str]] = []
    for key in keys:
        m = phrase_match(key, text or "")
        if m is not None:
            hits.append((m.start(), m.end(), key))
    kept: list[tuple[int, int, str]] = []
    for s, e, key in hits:
        covered = False
        for s2, e2, key2 in hits:
            if key2 == key:
                continue
            if s2 <= s and e2 >= e and (
                (e2 - s2) > (e - s)
                or ((e2 - s2) == (e - s) and len(key2) > len(key))
            ):
                covered = True
                break
        if not covered:
            kept.append((s, e, key))
    kept.sort()
    return kept


def _first_appearance_turns(
    rows: list[dict], keys: list[str]
) -> dict[int, list[str]]:
    """{turn index: [keys first appearing in that tutor reply]}.

    Transcript-level "new": a key is new on the first tutor turn whose
    visible reply carries it AND no earlier LEARNER utterance carried it
    (the learner using it themselves is their exposure, not the tutor's —
    same pragmatics as the runtime exposure scan)."""
    from tutor.textnorm import phrase_match

    seen: set[str] = set()
    by_turn: dict[int, list[str]] = {}
    for i, turn in enumerate(rows):
        reply = str(turn.get("reply") or "")
        learner = str(turn.get("learner") or "")
        # The learner's utterance precedes the tutor reply within a row.
        for key in keys:
            if key in seen:
                continue
            if learner and phrase_match(key, learner) is not None:
                seen.add(key)
        for _s, _e, key in _keys_in_text(
            [k for k in keys if k not in seen], reply
        ):
            by_turn.setdefault(i, []).append(key)
            seen.add(key)
    return by_turn


# A question-formula surface (for the UNRESOLVED Q&A-pair policy below).
_QUESTION_FORMULA_RE = re.compile(
    r"^(?:¿|c[oó]mo\b|qu[eé]\b|d[oó]nde\b|de\s+d[oó]nde\b|qui[eé]n\b|"
    r"cu[aá]l\b|cu[aá]ndo\b|y\s+t[uú]\b)",
    re.I,
)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


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
    """output_gate_still_fail notes, split by rule (S11 severity ledger).

    A still_fail note whose fault list touches HARD_STILL_FAIL_FAULTS
    (gate:truncated) is a HARD finding; any other still_fail note — the
    sheet-leak class and legacy fault ids in historical transcripts — is
    reported as WARN, counted, never a FAIL here.
    """
    findings: list[str] = []
    for i, turn in enumerate(_turn_rows(transcript)):
        for n in turn.get("notes") or []:
            s = str(n)
            if "output_gate_still_fail" not in s:
                continue
            tail = s.split("output_gate_still_fail", 1)[1].lstrip(":")
            faults = {f.strip() for f in tail.split(",") if f.strip()}
            if faults & HARD_STILL_FAIL_FAULTS:
                findings.append(f"turn {i}: {s}")
            else:
                findings.append(f"WARN turn {i}: {s}")
    return findings


def check_cluster_intro(
    transcript: list[dict],
    *,
    table: dict | None = None,
    exempt_qa_pairs: bool = False,
) -> list[str]:
    """PEDAGOGY §2.2 one-new-item law as a transcript check → HARD finding.

    Two or more same-theme association-table keys FIRST-appearing in one
    tutor turn is near-synonym/antonym interference (r7 R-F): the extras
    beyond the first are flagged.  This is the transcript-level successor
    of the deleted runtime gate:cluster_veto (S11).

    ``exempt_qa_pairs`` — UNRESOLVED policy (see the S11 stamp in
    docs/reviews-full-code-audit-20260803.md): whether a question formula
    plus its answer formula from one theme («¿cómo estás?» + «bien») is a
    legitimate co-introduction or an interference pair.  Default False
    (the pair FLAGS) until the policy is adjudicated; True exempts a
    two-key theme pair where exactly one key has a question-formula
    surface.
    """
    rows = _turn_rows(transcript)
    table = table if table is not None else _association_table()
    keys = _content_table_keys(table)
    findings: list[str] = []
    for i, new_keys in sorted(_first_appearance_turns(rows, keys).items()):
        by_theme: dict[str, list[str]] = {}
        for key in new_keys:
            theme = str((table.get(key) or {}).get("theme") or "")
            by_theme.setdefault(theme, []).append(key)
        for theme, theme_keys in sorted(by_theme.items()):
            if len(theme_keys) < 2:
                continue
            if exempt_qa_pairs and len(theme_keys) == 2:
                q_like = [
                    k for k in theme_keys
                    if _QUESTION_FORMULA_RE.match(k or "")
                ]
                if len(q_like) == 1:
                    continue
            extras = theme_keys[1:]
            findings.append(
                f"turn {i}: cluster co-introduction theme={theme!r} "
                f"keys={theme_keys} (extras {extras} — one new item per "
                "turn, PEDAGOGY §2.2)"
            )
    return findings


def check_probe_repeat(transcript: list[dict]) -> list[str]:
    """A try/continue probe re-asked in a later turn → WARN.

    Transcript-level successor of the deleted runtime gate:probe_loop
    (S11), at the chunk-2 retune: the scan reads the TRY and CONTINUE
    parts ONLY (model/acknowledge text is roleplay dialogue, not an ask —
    the T2–T4 false-positive class); rows without structured parts are
    covered by check_fixation instead.  Two arms:

    - the four social probes (canonical surface patterns);
    - the semantic topic key of the composed try
      (session_memory.topic_key_for_try / compose_topic_key — the SAME
      extractor the runtime registry uses).

    WARN-only: the runtime's retrieval-due exemption (P3 spacing outranks
    anti-repeat) needs sheet state a transcript does not carry — a repeat
    here may be a legitimate due re-elicit.
    """
    from tutor.session_memory import compose_topic_key, topic_key_for_try

    rows = _turn_rows(transcript)
    findings: list[str] = []
    asked_probes: dict[str, int] = {}
    asked_topics: dict[str, int] = {}
    for i, turn in enumerate(rows):
        parts = _structured_parts(turn)
        if parts is None:
            continue
        probe_blob = " ".join(
            str(parts.get(k) or "") for k in ("try", "continue")
        )
        if not probe_blob.strip():
            continue
        for probe_key, pat in _SOCIAL_PROBE_RES.items():
            if not pat.search(probe_blob):
                continue
            if probe_key in asked_probes:
                findings.append(
                    f"WARN turn {i}: social probe {probe_key} re-asked "
                    f"(first asked turn {asked_probes[probe_key]})"
                )
            else:
                asked_probes[probe_key] = i
        try_txt = str(parts.get("try") or parts.get("continue") or "")
        frame, concept = topic_key_for_try(try_txt)
        topic_key = compose_topic_key(frame, concept)
        if topic_key:
            if topic_key in asked_topics:
                findings.append(
                    f"WARN turn {i}: topic {topic_key} re-asked "
                    f"(first asked turn {asked_topics[topic_key]})"
                )
            else:
                asked_topics[topic_key] = i
    return findings


def check_english_wall(transcript: list[dict]) -> list[str]:
    """Mostly-English tutor turn → WARN finding per offending turn.

    S11: the ratio is computed HERE now (the runtime gate:english_wall
    died) — offending iff closed-lexicon ratio < the floor AND >= 12
    alphabetic tokens; the short <explain> L1 sandwich is exempt from the
    ratio; row 0 (the open) uses the true-zero floor (a compliant blank
    open is legitimately English-oriented — 2026-07-28 incident).
    Historical transcripts' gate:english_wall notes also WARN (replay).
    """
    findings: list[str] = []
    for i, turn in enumerate(_turn_rows(transcript)):
        parts = turn.get("parts") or {}
        reply = str(turn.get("reply") or "")
        full_blob = learner_facing_blob(parts, reply)
        ratio = spanish_token_ratio(
            ratio_blob_with_sandwich_exempt(parts, reply)
        )
        n_alpha = alphabetic_token_count(full_blob)
        min_ratio = ZERO_MIN_SPANISH_RATIO if i == 0 else MIN_SPANISH_RATIO
        # §2.8 carve-out (2026-08-04): when the LEARNER's turn showed
        # struggle (mostly-English text or explicit confusion), heavy
        # English support is the LAW, not a wall.
        if _learner_struggling(turn):
            continue
        if n_alpha >= MIN_ALPHA_TOKENS and ratio < min_ratio:
            findings.append(
                f"WARN turn {i}: english wall ratio={ratio:.2f}<{min_ratio} "
                f"alpha={n_alpha}"
            )
        for n in turn.get("notes") or []:
            if "gate:english_wall" in str(n):  # historical replay only
                findings.append(f"WARN turn {i}: {n}")
    return findings


def check_teach_shape(transcript: list[dict]) -> list[str]:
    """Contract-v1 shape checks over structured parts (ported from the
    deleted pedagogy_contract judgment — S11).

    - no teach move (no model/try/recast on a structured turn) → HARD.
    - structured OPEN (row 0) without both model AND try → HARD.
    - recast without a try (incomplete focus-on-form) → WARN.

    Rows without structured parts are skipped (nothing mechanical to
    verify; the blind rubric owns unstructured judgment).
    """
    findings: list[str] = []
    for i, turn in enumerate(_turn_rows(transcript)):
        parts = _structured_parts(turn)
        if parts is None:
            continue
        has_model = _truthy(parts, "model")
        has_try = _truthy(parts, "try")
        has_recast = _truthy(parts, "recast")
        if not (has_model or has_try or has_recast):
            findings.append(f"turn {i}: no teach move (model/try/recast all empty)")
        if i == 0 and not (has_model and has_try):
            findings.append(f"turn {i}: open without both model and try")
        if has_recast and not has_try:
            findings.append(
                f"WARN turn {i}: recast without a try (incomplete "
                "focus-on-form)"
            )
    return findings


def check_exposure_advisories(
    transcript: list[dict], *, table: dict | None = None
) -> list[str]:
    """Bare-first-exposure + re-gloss advisories → WARN.

    Transcript-level successors of the deleted soft runtime faults
    (gate:unscaffolded_new_item / gate:regloss — S11):

    - a table key FIRST-appearing in a tutor turn with no in-reply
      scaffold (no ≤6-word gloss, no same-line cognate/keyword anchor);
    - a key glossed in an earlier tutor turn re-glossed later (r7 E2 —
      no retrieval-failure data transcript-side, so advisory only).
    """
    from tutor.output_gate import anchor_in_reply, gloss_after_key

    rows = _turn_rows(transcript)
    table = table if table is not None else _association_table()
    keys = _content_table_keys(table)
    findings: list[str] = []
    first_at = _first_appearance_turns(rows, keys)
    glossed_before: set[str] = set()
    new_at: dict[int, set[str]] = {
        i: set(ks) for i, ks in first_at.items()
    }
    for i, turn in enumerate(rows):
        reply = str(turn.get("reply") or "")
        bare: list[str] = []
        for key in sorted(new_at.get(i, ())):
            entry = table.get(key) or {}
            if gloss_after_key(key, reply):
                glossed_before.add(key)
                continue
            if anchor_in_reply(entry, reply, key=key):
                continue
            bare.append(key)
        if bare:
            findings.append(
                f"WARN turn {i}: bare first exposure {bare} (no gloss/"
                "anchor in reply)"
            )
        regl = [
            key for key in sorted(glossed_before)
            if key not in new_at.get(i, ()) and gloss_after_key(key, reply)
        ]
        if regl:
            findings.append(f"WARN turn {i}: re-gloss of {regl}")
    return findings


def _mem_keys(turn: dict) -> set[str]:
    keys: set[str] = set()
    for n in turn.get("notes") or []:
        m = _MEM_NOTE_RE.match(str(n))
        if not m:
            continue
        for k in m.group(1).split(","):
            k = k.strip()
            # Mode names are router telemetry, not probeable frames
            # (mem_asked pollution — gate retune 2026-08-03).
            if k and k != "—" and k not in _MODE_NAME_KEYS:
                keys.add(k)
    return keys


def _key_content_tokens(key: str) -> set[str]:
    """Lexical content of a registry key (location:bote → {bote, location})."""
    raw = re.split(r"[:_\s]+", fold_lexical(key))
    return {t for t in raw if len(t) >= 3 and t not in _KEY_STOPWORDS}


def _probes(reply: str) -> list[str]:
    """Explicit quiz questions: «¿Sí o no?» shapes only (the `\\bo\\b`
    any-alternative assumption was deleted — gate retune 2026-08-03)."""
    out: list[str] = []
    for q in _question_spans(reply):
        folded = fold_lexical(q)
        if _SI_O_NO_RE.search(folded):
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


CHECKS = {
    "fixation": check_fixation,
    "still_fail": check_still_fail,
    "cluster_intro": check_cluster_intro,
    "probe_repeat": check_probe_repeat,
    "probe_on_known": check_probe_on_known,
    "english_wall": check_english_wall,
    "teach_shape": check_teach_shape,
    "exposure": check_exposure_advisories,
}

# Checks that read the association table (table=None → the real domain
# table; tests pass a synthetic one for determinism).
_TABLE_AWARE = {"cluster_intro", "exposure"}


_CONFUSION_MARKERS = (
    "don't understand", "dont understand", "no understand", "i don't get",
    "no entiendo", "what does", "what is", "confused", "lost", "help",
)


def _learner_struggling(turn: dict) -> bool:
    """Did THIS turn's learner text show struggle? (mostly English, or an
    explicit confusion marker.) §2.8: tutor English support is then legal."""
    learner = str(turn.get("learner") or "")
    if not learner.strip():
        return False
    low = learner.lower()
    if any(m in low for m in _CONFUSION_MARKERS):
        return True
    return spanish_token_ratio(learner) < 0.35


def check_grade_inflation(
    transcript: list[dict], *, grades: list[dict] | None = None
) -> list[str]:
    """WARN: an UP ability grade whose evidence quote contains no
    interpretable Spanish (garble/English). §2.8 honesty pressure gauge —
    LLM judges are lenient; this keeps the leniency measured.
    Needs the per-run grade ledger rows (run_student_smoke passes them);
    without them it reports nothing."""
    findings: list[str] = []
    for g in grades or []:
        if g.get("kind") != "grade" or g.get("direction") != "up":
            continue
        ev = str(g.get("evidence") or "").strip()
        if not ev:
            findings.append(
                f"WARN: up-grade with NO evidence quote ({g.get('ability') or g.get('label')})"
            )
            continue
        if spanish_token_ratio(ev) < 0.3:
            findings.append(
                "WARN: up-grade on garble/English evidence "
                f"({g.get('ability') or g.get('label')}: \"{ev[:50]}\")"
            )
    return findings


def run_student_checks(
    transcript: list[dict], *, table: dict | None = None,
    grades: list[dict] | None = None,
) -> tuple[dict, bool]:
    """(findings-by-check, passed). Fail bar: any non-WARN finding — see
    the severity ledger in the module docstring (HARD: fixation,
    truncated still_fail, cluster co-introduction, structured teach-shape
    misses; everything else WARN-only counters)."""
    findings: dict[str, list[str]] = {}
    gi = check_grade_inflation(transcript, grades=grades)
    if gi:
        findings["grade_inflation"] = gi
    for name, fn in CHECKS.items():
        out = (
            fn(transcript, table=table)
            if name in _TABLE_AWARE
            else fn(transcript)
        )
        if out:
            findings[name] = out
    hard = {
        k: v
        for k, v in findings.items()
        if any(not str(f).startswith("WARN") for f in v)
    }
    return findings, not hard
