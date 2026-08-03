"""evals/student_checks.py — the transcript-level home of every teaching
opinion (S11, 2026-08-03) + the R4 fixation detector and FAIL bar.

The fixation class is the R4 defect (docs/reviews-system-review-20260730.md):
a tutor re-asking a near-identical A/B try turns apart.  The migrated checks
(cluster co-introduction / probe repetition / english wall / teach shape /
exposure advisories) are the successors of the deleted runtime gate checks.
Synthetic transcripts only — no models, no sessions."""

from evals.student_checks import (
    check_cluster_intro,
    check_english_wall,
    check_exposure_advisories,
    check_fixation,
    check_probe_repeat,
    check_still_fail,
    check_teach_shape,
    run_student_checks,
    spanish_token_ratio,
)


def _row(reply: str, notes: list[str] | None = None, parts: dict | None = None) -> dict:
    return {
        "learner": "hola",
        "reply": reply,
        "notes": list(notes or []),
        "parts": dict(parts or {}),
    }


AB_TRY = "¿El café está en la mesa o en la silla?"
# Same probe re-asked two turns later with one filler word appended:
# token-Jaccard 8/9 ≈ 0.89 > 0.85 — the near-identical case must flag.
AB_TRY_AGAIN = "¿El café está en la mesa o en la silla ahora?"


# A tiny synthetic association table (checks accept table= so the real
# domain data never makes these tests drift).
FAKE_TABLE = {
    "hasta luego": {"theme": "farewells", "gloss_en": "see you later",
                    "imageable": False},
    "adiós": {"theme": "farewells", "gloss_en": "goodbye",
              "imageable": False},
    "cómo estás": {"theme": "how_are_you", "gloss_en": "how are you",
                   "imageable": False},
    "bien": {"theme": "how_are_you", "gloss_en": "well", "imageable": False},
    "pan": {"theme": "food", "gloss_en": "bread", "imageable": True},
    "encantado": {"theme": "introductions", "gloss_en": "nice to meet you",
                  "cognate_en": "enchanted", "imageable": False},
    # structural rows must never count
    "estoy": {"theme": "copulas", "gloss_en": "I am", "imageable": False},
}


class TestFixation:
    def test_repeated_ab_try_two_turns_apart_is_flagged(self):
        transcript = [
            _row("¡Hola! Vamos a hablar."),
            _row(f"Muy bien. {AB_TRY}"),
            _row("Sí, el café. ¿Y tú?"),
            _row(f"Bueno. {AB_TRY_AGAIN}"),
        ]
        findings = check_fixation(transcript)
        assert findings, "near-identical A/B try 2 turns apart must be flagged"
        assert "turns 1->3" in findings[0]

        all_findings, passed = run_student_checks(transcript, table=FAKE_TABLE)
        assert not passed, "nonzero fixation = FAIL"
        assert "fixation" in all_findings

    def test_distinct_tries_are_clean(self):
        transcript = [
            _row("¡Hola! Vamos a hablar."),
            _row(f"Muy bien. {AB_TRY}"),
            _row("Ahora otra cosa. ¿Dónde está tu familia hoy por la tarde?"),
            _row("Bueno. ¿Te gusta el café con leche o solo un poco de té?"),
        ]
        assert check_fixation(transcript) == []
        _, passed = run_student_checks(transcript, table=FAKE_TABLE)
        assert passed

    def test_short_tries_below_token_floor_do_not_flag(self):
        # "¿Sí o no?" folds to 3 tokens — under FIXATION_MIN_TOKENS (6);
        # exact repeats of tiny probes are the probe/quiz lane, not fixation.
        transcript = [
            _row("¿Sí o no?"),
            _row("¿Sí o no?"),
        ]
        assert check_fixation(transcript) == []

    def test_structured_parts_try_is_preferred_over_reply_questions(self):
        # parts["try"] is authoritative when present: identical structured
        # tries flag even though the visible replies differ.
        transcript = [
            _row("Primero una pregunta.", parts={"try": AB_TRY}),
            _row("Otra vez, con calma.", parts={"try": AB_TRY}),
        ]
        findings = check_fixation(transcript)
        assert findings and "turns 0->1" in findings[0]


class TestStillFail:
    def test_still_fail_split_by_rule(self):
        # S11 severity ledger: only gate:truncated fails hard; every other
        # still_fail row (incl. legacy fault ids in historical transcripts)
        # is WARN-counted, never a session FAIL here.
        warn_only = [
            _row("Hola."),
            _row(
                "¿Cómo estás?",
                notes=["output_gate_still_fail:gate:sheet_leak"],
            ),
            _row(
                "Bueno.",
                notes=["output_gate_still_fail:gate:probe_loop"],  # legacy id
            ),
        ]
        assert check_still_fail(warn_only) == [
            "WARN turn 1: output_gate_still_fail:gate:sheet_leak",
            "WARN turn 2: output_gate_still_fail:gate:probe_loop",
        ]
        _, passed = run_student_checks(warn_only, table=FAKE_TABLE)
        assert passed, "non-truncated still_fail is WARN, not FAIL"

        hard = [
            _row("Hola."),
            _row(
                "…",
                notes=[
                    "output_gate_still_fail:gate:truncated,gate:sheet_leak"
                ],
            ),
        ]
        findings = check_still_fail(hard)
        assert findings == [
            "turn 1: output_gate_still_fail:gate:truncated,gate:sheet_leak",
        ]
        _, passed = run_student_checks(hard, table=FAKE_TABLE)
        assert not passed


class TestClusterIntro:
    def test_two_new_same_theme_keys_in_one_turn_flag(self):
        transcript = [
            _row("¡Hola! Vamos a empezar."),
            _row("**Hasta luego** (see you later). **Adiós** (goodbye)."),
        ]
        findings = check_cluster_intro(transcript, table=FAKE_TABLE)
        assert len(findings) == 1
        assert "turn 1" in findings[0] and "farewells" in findings[0]
        # HARD: not WARN-prefixed.
        assert not findings[0].startswith("WARN")

    def test_one_new_key_per_turn_is_clean(self):
        transcript = [
            _row("**Hasta luego** (see you later)."),
            _row("Y ahora: **adiós** (goodbye)."),
        ]
        assert check_cluster_intro(transcript, table=FAKE_TABLE) == []

    def test_reappearance_is_not_a_new_introduction(self):
        # «hasta luego» seen on turn 0 — its turn-2 reuse must not pair
        # with «adiós» as a co-introduction.
        transcript = [
            _row("**Hasta luego** (see you later)."),
            _row("Bueno."),
            _row("Hasta luego. **Adiós** (goodbye)."),
        ]
        assert check_cluster_intro(transcript, table=FAKE_TABLE) == []

    def test_learner_first_use_is_their_exposure(self):
        # The learner used «adiós» before the tutor did — the tutor's later
        # turn introduces only «hasta luego»; no pair.
        transcript = [
            _row("¡Hola!"),
            {
                "learner": "adiós amigo",
                "reply": "**Adiós** (goodbye). **Hasta luego** (see you later).",
                "notes": [],
                "parts": {},
            },
        ]
        assert check_cluster_intro(transcript, table=FAKE_TABLE) == []

    def test_structural_keys_never_pair(self):
        transcript = [
            _row("Yo estoy bien. ¿Cómo estás?"),
        ]
        # «estoy» is a copulas-theme row: exempt; cómo estás + bien DO pair
        # (how_are_you theme) — that is the Q&A-formula question below.
        findings = check_cluster_intro(transcript, table=FAKE_TABLE)
        assert len(findings) == 1
        assert "how_are_you" in findings[0]
        assert "estoy" not in findings[0]

    def test_exempt_qa_pairs_default_false(self):
        # UNRESOLVED policy (S11 stamp): the question+answer formula pair
        # FLAGS by default; the exemption is opt-in until adjudicated.
        transcript = [_row("¿Cómo estás? Bien, gracias.")]
        flagged = check_cluster_intro(transcript, table=FAKE_TABLE)
        assert flagged and "how_are_you" in flagged[0]
        exempted = check_cluster_intro(
            transcript, table=FAKE_TABLE, exempt_qa_pairs=True
        )
        assert exempted == []
        # The exemption is exactly one-question + one-answer: two answer
        # formulas never exempt (no question surface).
        pair = [_row("**Hasta luego** (bye). **Adiós** (goodbye).")]
        assert check_cluster_intro(
            pair, table=FAKE_TABLE, exempt_qa_pairs=True
        )


class TestProbeRepeat:
    def _turn(self, try_text):
        return _row(
            f"Muy bien. {try_text}",
            parts={"model": "Mi casa está aquí.", "try": try_text,
                   "structured": True},
        )

    def test_social_probe_reasked_warns(self):
        transcript = [
            self._turn("¿Cómo te llamas?"),
            self._turn("¿Te gusta el pan?"),
            self._turn("¿Cómo te llamas?"),
        ]
        findings = check_probe_repeat(transcript)
        assert any("ask_name" in f and "turn 2" in f for f in findings)
        assert all(f.startswith("WARN") for f in findings)

    def test_topic_key_reasked_warns(self):
        city_try = "¿Está tu casa en una ciudad grande o pequeña?"
        transcript = [
            self._turn(city_try),
            self._turn("¿Qué hay en tu casa?"),
            self._turn(city_try),
        ]
        findings = check_probe_repeat(transcript)
        assert any("size:" in f and "turn 2" in f for f in findings)

    def test_scan_reads_try_continue_only(self):
        # Chunk-2 retune preserved: model/acknowledge text is roleplay
        # dialogue, not an ask — a model sentence naming the probe never
        # counts.
        transcript = [
            self._turn("¿Cómo te llamas?"),
            _row(
                "¡Hola! ¿Cómo te llamas? es un saludo.",
                parts={
                    "acknowledge": "¿Cómo te llamas? es un saludo.",
                    "model": "Me preguntas ¿cómo te llamas? y yo respondo.",
                    "try": "¿Dónde está el capitán?",
                    "structured": True,
                },
            ),
        ]
        assert check_probe_repeat(transcript) == []

    def test_unstructured_rows_skipped(self):
        transcript = [
            _row("¿Cómo te llamas?"),
            _row("¿Cómo te llamas?"),
        ]
        # No structured parts → the fixation/probe-on-known lanes own it.
        assert check_probe_repeat(transcript) == []


class TestEnglishWall:
    def test_long_english_turn_warns(self):
        parts = {
            "acknowledge": "Good job you nailed it!",
            "model": "That means my name is.",
            "try": "Please say your name in Spanish now.",
            "structured": True,
        }
        transcript = [
            _row("¡Hola! Empezamos."),
            _row("Good job...", parts=parts),
        ]
        findings = check_english_wall(transcript)
        assert any("turn 1" in f and "english wall" in f for f in findings)
        assert all(f.startswith("WARN") for f in findings)
        _, passed = run_student_checks(transcript, table=FAKE_TABLE)
        assert passed, "english wall is WARN-only"

    def test_spanish_forward_turn_clean(self):
        parts = {
            "acknowledge": "¡Qué bien!",
            "model": "Me llamo Sofía y estoy muy bien hoy.",
            "try": "¿Y tú? ¿Cómo estás hoy, amigo?",
            "structured": True,
        }
        transcript = [_row("hola"), _row("x", parts=parts)]
        assert check_english_wall(transcript) == []

    def test_short_english_never_warns(self):
        parts = {"acknowledge": "Good job!", "model": "Try this.",
                 "try": "Say it.", "structured": True}
        transcript = [_row("hola"), _row("x", parts=parts)]
        assert check_english_wall(transcript) == []

    def test_open_row_uses_true_zero_floor(self):
        # A compliant blank open (English orientation + glossed Spanish,
        # ratio ≈ 0.32–0.40) must not warn on row 0 — the 2026-07-28
        # incident class; the same turn later in the session WOULD warn.
        parts = {
            "acknowledge": (
                "Welcome! We will go slowly and I will always show you "
                "what things mean."
            ),
            "model": "Hola (hello). Estoy bien (I am fine). Me llamo "
                     "Marisol (my name is Marisol).",
            "try": "Try: Me llamo ___ — my name is ___",
            "structured": True,
        }
        open_first = [_row("(session open)", parts=parts)]
        assert check_english_wall(open_first) == []
        later = [_row("hola"), _row("x", parts=parts)]
        assert any("english wall" in f for f in check_english_wall(later))

    def test_all_english_open_still_warns(self):
        parts = {
            "acknowledge": "Good job you nailed it!",
            "model": "That means my name is.",
            "try": "Please say your name in Spanish now.",
            "structured": True,
        }
        assert spanish_token_ratio(
            "Good job you nailed it! That means my name is. Please say "
            "your name in Spanish now."
        ) == 0.0
        transcript = [_row("(session open)", parts=parts)]
        assert any(
            "english wall" in f for f in check_english_wall(transcript)
        )


class TestTeachShape:
    def test_no_teach_move_on_structured_turn_is_hard(self):
        transcript = [
            _row("x", parts={"model": "Hola.", "try": "Di hola.",
                             "structured": True}),
            _row("¡Hola! ¿Todo bien?", parts={
                "acknowledge": "¡Hola amigo!",
                "continue": "¿Todo bien?",
                "structured": True,
            }),
        ]
        findings = check_teach_shape(transcript)
        assert any(
            "turn 1" in f and "no teach move" in f
            and not f.startswith("WARN")
            for f in findings
        )
        _, passed = run_student_checks(transcript, table=FAKE_TABLE)
        assert not passed

    def test_open_without_model_and_try_is_hard(self):
        transcript = [
            _row("¡Hola!", parts={"model": "Hola.", "structured": True}),
        ]
        findings = check_teach_shape(transcript)
        assert any("open without both model and try" in f for f in findings)
        assert all(not f.startswith("WARN") for f in findings)

    def test_recast_without_try_is_warn(self):
        transcript = [
            _row("x", parts={"model": "Hola.", "try": "Di hola.",
                             "structured": True}),
            _row("y", parts={"recast": "Natural: **Estoy bien.**",
                             "continue": "¿Y el café?",
                             "structured": True}),
        ]
        findings = check_teach_shape(transcript)
        assert any(
            f.startswith("WARN") and "recast without a try" in f
            for f in findings
        )
        _, passed = run_student_checks(transcript, table=FAKE_TABLE)
        assert passed, "recast_without_try is advisory"

    def test_unstructured_rows_skipped(self):
        transcript = [_row("plain prose reply, no tags")]
        assert check_teach_shape(transcript) == []

    def test_good_shapes_clean(self):
        transcript = [
            _row("x", parts={"model": "Hola.", "try": "Di hola.",
                             "structured": True}),
            _row("y", parts={"recast": "Natural: **Estoy bien.**",
                             "try": "Di: **Estoy bien.**",
                             "structured": True}),
        ]
        assert check_teach_shape(transcript) == []


class TestExposureAdvisories:
    def test_bare_first_exposure_warns(self):
        transcript = [
            _row("¡Hola! Empezamos."),
            _row("Hasta luego, amigo."),
        ]
        findings = check_exposure_advisories(transcript, table=FAKE_TABLE)
        assert any(
            f.startswith("WARN") and "bare first exposure" in f
            and "hasta luego" in f
            for f in findings
        )
        _, passed = run_student_checks(transcript, table=FAKE_TABLE)
        assert passed, "exposure advisories are WARN-only"

    def test_glossed_first_exposure_clean(self):
        transcript = [_row("**Hasta luego** (see you later).")]
        assert check_exposure_advisories(transcript, table=FAKE_TABLE) == []

    def test_anchored_first_exposure_clean(self):
        transcript = [
            _row("**Encantado** — like English 'enchanted'. Di: Encantado.")
        ]
        assert check_exposure_advisories(transcript, table=FAKE_TABLE) == []

    def test_regloss_warns(self):
        transcript = [
            _row("**Pan** (bread) es rico."),
            _row("¿Te gusta el pan?"),
            _row("Sí, **pan** (bread)."),
        ]
        findings = check_exposure_advisories(transcript, table=FAKE_TABLE)
        assert any(
            f.startswith("WARN") and "re-gloss" in f and "pan" in f
            for f in findings
        )

    def test_plain_reuse_after_gloss_clean(self):
        transcript = [
            _row("**Pan** (bread) es rico."),
            _row("¿Te gusta el pan con café?"),
        ]
        assert check_exposure_advisories(transcript, table=FAKE_TABLE) == []
