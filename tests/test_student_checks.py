"""evals/student_checks.py — repetition/fixation detector + FAIL bar.

The fixation class is the R4 defect (docs/reviews-system-review-20260730.md):
a tutor re-asking a near-identical A/B try turns apart. Synthetic
transcripts only — no models, no sessions."""

from evals.student_checks import (
    check_fixation,
    check_still_fail,
    run_student_checks,
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


def test_repeated_ab_try_two_turns_apart_is_flagged():
    transcript = [
        _row("¡Hola! Vamos a hablar."),
        _row(f"Muy bien. {AB_TRY}"),
        _row("Sí, el café. ¿Y tú?"),
        _row(f"Bueno. {AB_TRY_AGAIN}"),
    ]
    findings = check_fixation(transcript)
    assert findings, "near-identical A/B try 2 turns apart must be flagged"
    assert "turns 1->3" in findings[0]

    all_findings, passed = run_student_checks(transcript)
    assert not passed, "nonzero fixation = FAIL"
    assert "fixation" in all_findings


def test_distinct_tries_are_clean():
    transcript = [
        _row("¡Hola! Vamos a hablar."),
        _row(f"Muy bien. {AB_TRY}"),
        _row("Ahora otra cosa. ¿Dónde está tu familia hoy por la tarde?"),
        _row("Bueno. ¿Te gusta el café con leche o solo un poco de té?"),
    ]
    assert check_fixation(transcript) == []
    _, passed = run_student_checks(transcript)
    assert passed


def test_short_tries_below_token_floor_do_not_flag():
    # "¿Sí o no?" folds to 3 tokens — under FIXATION_MIN_TOKENS (6); exact
    # repeats of tiny probes are the checker-budget lane (probe_on_known /
    # R2), not fixation.
    transcript = [
        _row("¿Sí o no?"),
        _row("¿Sí o no?"),
    ]
    assert check_fixation(transcript) == []


def test_structured_parts_try_is_preferred_over_reply_questions():
    # parts["try"] is authoritative when present: identical structured
    # tries flag even though the visible replies differ.
    transcript = [
        _row("Primero una pregunta.", parts={"try": AB_TRY}),
        _row("Otra vez, con calma.", parts={"try": AB_TRY}),
    ]
    findings = check_fixation(transcript)
    assert findings and "turns 0->1" in findings[0]


def test_still_fail_note_is_hard_fail():
    transcript = [
        _row("Hola."),
        _row(
            "¿Cómo estás?",
            notes=["output_gate_still_fail:gate:probe_loop"],
        ),
    ]
    assert check_still_fail(transcript) == [
        "turn 1: output_gate_still_fail:gate:probe_loop"
    ]
    _, passed = run_student_checks(transcript)
    assert not passed
