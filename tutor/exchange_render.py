"""Exchange settlement — peripherals render projections, never the agenda.

ENGINEERING §1.1b (2026-07-29, café/me-llamo incidents;
docs/design-exchange-settlement.md, Grok-countersigned): every
learner-visible artifact outside the chat text that claims to be about
THIS turn must be confirmed against a projection of the REALIZED
exchange. Projections here are PURE functions of
``(learner_text, tutor_reply[, allowlisted turn events])``.

INPUT LAW (signature + closure enforced; tests pin both): this module
must never import or read session/sheet/mode/scene/phase/agenda state.
The event log is a smuggling channel — projections may read only
PROJECTION_EVENT_ALLOWLIST kinds. Settlement (settle_images) is the only
function allowed to take agenda-shaped CANDIDATES, and only to confirm
or drop them.

Timing (the converged split — a single settlement stage was internally
contradictory, Grok round 2026-07-29):

    raw0 -> settle_pixels0 -> gate0 -> (repair? raw1 -> settle_pixels1
    -> gate1) -> recorders -> settle_chrome -> assemble

``settle_pixels`` confirms image candidates pre-gate (GateContext
image_present must see truth; <=2 settlements per turn).
``settle_chrome`` derives the card/panel views post-recorders (the
INTRODUCED / FIRST_SEEN events it needs exist only there) and freezes
the TurnRender.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Event kinds a projection may read. NEVER mode/phase/due-offer/plan
# payloads — those are agenda (Grok input-law AMEND: allowlist, not
# habit, closes the smuggling channel).
PROJECTION_EVENT_ALLOWLIST = frozenset({
    "introduced",
    "first_seen",
})


@dataclass(frozen=True)
class ExchangeSurface:
    """The realized exchange — the ONLY ground truth peripherals may
    render against. learner is "" on a session-open turn (confirmation
    then rests on the reply alone)."""

    learner: str
    reply: str


def exchange_surface(learner: str, reply: str) -> ExchangeSurface:
    return ExchangeSurface(learner=str(learner or ""), reply=str(reply or ""))


def concept_present(surface: ExchangeSurface, concept: str) -> bool:
    """ONE text-presence primitive for all projections (Grok drift AMEND:
    duplicate fold/boundary logic is a future café-class bug). Delegates
    to teach_assets.concept_in_text — boundary-safe, alias/accent-aware,
    the same matcher the declared-image path always used."""
    from .teach_assets import concept_in_text

    return concept_in_text(concept, surface.learner) or concept_in_text(
        concept, surface.reply
    )


def settle_images(
    images: list[dict], surface: ExchangeSurface
) -> tuple[list[dict], list[tuple[str, str]]]:
    """Confirm image candidates against the exchange; drop the rest.

    Returns (confirmed, drops) where drops are (concept, reason) pairs.
    Candidates are agenda-shaped inputs — legal HERE only (input law).
    Nothing may lead pixels: a candidate whose concept the realized
    exchange never surfaces does not render (OQ1 resolution — the model
    may be led by instructions; the learner may not be shown orphans).
    """
    confirmed: list[dict] = []
    drops: list[tuple[str, str]] = []
    for img in images or []:
        concept = str((img or {}).get("concept") or "")
        if concept and concept_present(surface, concept):
            confirmed.append(img)
        else:
            drops.append((concept or "?", "unconfirmed"))
    return confirmed, drops


@dataclass(frozen=True)
class ExchangeSurface:
    """The realized exchange — the ONLY ground truth peripherals may
    render against. learner is "" on a session-open turn (confirmation
    then rests on the reply alone)."""

    learner: str
    reply: str


def exchange_surface(learner: str, reply: str) -> ExchangeSurface:
    return ExchangeSurface(learner=str(learner or ""), reply=str(reply or ""))


def concept_present(surface: ExchangeSurface, concept: str) -> bool:
    """ONE text-presence primitive for all projections (Grok drift AMEND:
    duplicate fold/boundary logic is a future café-class bug). Delegates
    to teach_assets.concept_in_text — boundary-safe, alias/accent-aware,
    the same matcher the declared-image path always used."""
    from .teach_assets import concept_in_text

    return concept_in_text(concept, surface.learner) or concept_in_text(
        concept, surface.reply
    )


def settle_images(
    images: list[dict], surface: ExchangeSurface
) -> tuple[list[dict], list[tuple[str, str]]]:
    """Confirm image candidates against the exchange; drop the rest.

    Returns (confirmed, drops) where drops are (concept, reason) pairs.
    Candidates are agenda-shaped inputs — legal HERE only (input law).
    Nothing may lead pixels: a candidate whose concept the realized
    exchange never surfaces does not render (OQ1 resolution — the model
    may be led by instructions; the learner may not be shown orphans).
    """
    confirmed: list[dict] = []
    drops: list[tuple[str, str]] = []
    for img in images or []:
        concept = str((img or {}).get("concept") or "")
        if concept and concept_present(surface, concept):
            confirmed.append(img)
        else:
            drops.append((concept or "?", "unconfirmed"))
    return confirmed, drops


def card_engagement(
    learner: str,
    reply: str,
    events: tuple[tuple[str, str], ...] = (),
) -> dict | None:
    """The form THIS exchange engages — the morphology card's only lawful
    live master. Priority: learner engagement (error / attempted
    conjugation / meta question / how-say — detect_turn_morph) beats
    tutor-side introduction (allowlisted INTRODUCED / FIRST_SEEN keys).
    None = no live engagement (the card may then show only LABELED
    "up next" chrome, never agenda-as-live — §1.1b honesty carve-out).

    ``events`` are (kind, key) pairs; non-allowlisted kinds are ignored
    here even if a caller leaks them (defense in depth).
    """
    from .turn_morph import detect_intro_morph, detect_turn_morph

    block = detect_turn_morph(learner)
    if block is not None:
        return block
    keys = [
        key for kind, key in events
        if kind in PROJECTION_EVENT_ALLOWLIST and key
    ]
    if keys:
        return detect_intro_morph(keys)
    return None


@dataclass(frozen=True)
class TurnRender:
    """The settled render record for ONE turn — a RESULT, not shared
    state: written once at settle_chrome, single-assignment fields,
    replaced whole next turn, dies with the session turn cycle. The
    async focus enricher may overlay presentation cells downstream but
    never mutates confirmed images or the engaged card (OQ5)."""

    images: tuple = ()

    drops: tuple = ()

    def as_dict(self) -> dict:
        return {
            "images": [dict(i) for i in self.images],

            "drops": [list(d) for d in self.drops],
        }
