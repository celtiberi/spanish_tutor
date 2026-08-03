"""Two-phase teaching context: the TEACHER plans, then teaches small.

USER architecture (2026-08-03, legal under the rewritten §1.1 — the model
owns every teaching decision): "The pedagogy is handed to the teacher.
The teacher gets the character sheet so it knows where the student is.
The teacher creates a plan for this session. Now we have a smaller
context that is fed for the future rounds unless something changes and
we need a new plan."

PLAN turns (session open, or whenever a re-plan is needed) get the FULL
picture: the PEDAGOGY.md rules (NOTES/INTERNAL spans cut — see
load_pedagogy), the
character sheet — domain model + learner state in one artifact: targets,
scope, per-item evidence — and history. The model writes its own session
plan in a private <plan> block before its normal <tutor> reply.

ROUND turns get the small context: the model's OWN plan + the character
sheet + session facts + due data + a recent history window. No pedagogy
file — the plan already digested it.

The model revises its plan any turn by emitting a new <plan> block, and
requests a full-context re-plan with <replan/> when it needs the
teaching rules again (learner steered somewhere the plan didn't cover, plan
exhausted, etc.). Code never writes or edits a plan (§1.1: facts,
honesty, audit only).

This replaces the retired B0 code-assembled brief (blind-grade failure:
a code brief carried the curriculum but lost the learner's world —
responsiveness −0.93). Here the plan is the teacher's own words.
"""

from __future__ import annotations

import re

from . import config

PEDAGOGY_PATH = config.REPO_ROOT / "PEDAGOGY.md"

# History window for ROUND turns (messages, i.e. 2 per exchange). Plan
# turns get full history. Generous on purpose: the B0 blind grade proved
# that losing the learner's established world kills responsiveness.
ROUND_HISTORY_MESSAGES = 12

PLAN_INSTRUCTIONS = """## Your session plan (required on this turn)

You have the full teaching guide in this request — later turns will NOT
include it, only the plan you write now. The character sheet carries
everything you need: `skills` + `grammar` + `coverage` are the abilities
this learner is building and where they stand; `domain_scope` is the
level's limits (what to defer or decline). Vocabulary is YOURS to
choose — level-appropriate words that serve the abilities and the
conversation. The path is YOURS too — the sheet never sequences.
Before your normal `<tutor>` reply, write a session plan the future you
can teach from:

<plan>
LEARNER — where they are, with the evidence you're reading it from.
GOALS — what THIS session should accomplish.
ARC — how you expect the session to flow, beat by beat.
TARGETS — due items to weave in and how; new items with the exact
anchor/gloss you'll introduce each with.
CONTINGENCIES — if X stalls or confuses them, you'll do Y (write
several; sessions rarely follow the happy path).
EVIDENCE — which productions would earn a sheet grade, and for what.
AVOID — already-answered questions, known-material quizzes,
out-of-scope items.
</plan>

Write real content under every heading, as long as it needs to be —
this is the ONE turn with everything in front of you; later turns get
only this plan, so invest here.

The learner NEVER sees the plan. On any later turn you may revise it by
emitting a new <plan> block, and if you need the full teaching guide
again (the conversation left your plan behind), emit <replan/> and the
next turn will include everything.
"""

ROUND_NOTE = """## Working from your plan
Your session plan (you wrote it, learner never sees it) is in the turn
task as `your_session_plan`. Teach from it and from what the learner just
said — the plan serves the learner, never the reverse. Revise it with a
new <plan> block whenever you want; emit <replan/> if you need the full
teaching guide again."""

_PLAN_RE = re.compile(r"<plan>\s*(.*?)\s*</plan>", re.S | re.I)
_REPLAN_RE = re.compile(r"<replan\s*/?>", re.I)


# Marked spans: INTERNAL (bookkeeping) and NOTES (§0 theory & evidence)
# stay in the FILE for us; the teacher receives only the rules.
_CUT_SPANS_RE = re.compile(
    r"<!--\s*(?:INTERNAL|NOTES):BEGIN\b.*?(?:INTERNAL|NOTES):END\s*-->",
    re.S,
)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def load_pedagogy() -> str:
    """PEDAGOGY.md for the teacher: NOTES/INTERNAL spans and every HTML
    comment cut (USER 2026-08-03: "one THEORY AND NOTES file and one
    HERE ARE THE RULES file" — realized with markers; the sent copy IS
    the rules file). A missing/unreadable file returns "" AND shouts on
    stderr — the earlier docstring claimed the absence was visible when
    nothing surfaced it (audit C top offender #1)."""
    try:
        raw = PEDAGOGY_PATH.read_text(encoding="utf-8")
    except OSError as e:
        import sys as _sys

        print(f"[no-hide] PEDAGOGY.md load FAILED — plan turn ships "
              f"WITHOUT the teaching guide: {type(e).__name__}: {e}",
              file=_sys.stderr, flush=True)
        return ""
    cut = _CUT_SPANS_RE.sub("", raw)
    cut = _HTML_COMMENT_RE.sub("", cut)
    # Collapse the blank runs the cuts leave behind.
    return re.sub(r"\n{3,}", "\n\n", cut).strip()


def extract_plan(raw: str) -> tuple[str | None, bool, str]:
    """(plan_text | None, replan_requested, cleaned_raw).

    Strips <plan> and <replan/> from the raw reply so plan text can never
    leak into the learner-visible message (the parser routes stray prose
    into `continue`). Always safe to call — no-ops when tags are absent.
    """
    text = raw or ""
    plan: str | None = None
    m = _PLAN_RE.search(text)
    if m:
        plan = m.group(1).strip() or None
        text = _PLAN_RE.sub(" ", text)
    replan = bool(_REPLAN_RE.search(text))
    if replan:
        text = _REPLAN_RE.sub(" ", text)
    return plan, replan, text.strip()
