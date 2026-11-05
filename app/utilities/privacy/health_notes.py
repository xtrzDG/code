"""
Booking notes that hold health data (PRIV-10, GDPR art. 9): an allergy or
intolerance, a diet for a medical reason, a pregnancy, a condition, a
medication or a disability. The assistant writes only what the staff need
("nut allergy", `health_data_rule`), and such a note is Restricted
(docs/security/data-classification.md): it never leaves the platform in a
Google Calendar event, a staff e-mail, SMS, chat or push message ("see the
booking" instead), a public API or webhook payload, and only the owner and
the staff who serve customers see it in the cabinet.

The words are matched without case and accents at the start of a word, in
the languages businesses write in (English and Italian first, then German,
French, Spanish, Russian and Georgian). A false match only hides a note
behind "see the booking", so the list leans to more words, not fewer; a
word it misses is a note that stays as before.
"""

import re

from app.schemas.typings.bookings.strings import BookingNote
from app.utilities.conversations.conversation_search import normalize_search_text

HEALTH_WORD_STEMS: tuple[str, ...] = (
    # Allergies, intolerances and diets for a medical reason.
    "allerg",
    "alerg",
    "аллерг",
    "ალერგ",
    "intoller",
    "intoler",
    "unvertrag",
    "непереносим",
    "anaphyla",
    "anafila",
    "epipen",
    "celiac",
    "coeliac",
    "celiach",
    "zoliak",
    "gluten",
    "glutine",
    "lactos",
    "lattosio",
    "laktose",
    # Conditions, pregnancy, disability.
    "diabet",
    "диабет",
    "დიაბეტ",
    "insulin",
    "pregnan",
    "incinta",
    "gravid",
    "schwanger",
    "enceinte",
    "embarazad",
    "беремен",
    "ორსულ",
    "epilep",
    "asthm",
    "pacemaker",
    "wheelchair",
    "sedia a rotelle",
    "carrozzin",
    "deambul",
    "stampell",
    "crutch",
    "rollstuhl",
    "fauteuil roulant",
    "silla de ruedas",
    "disabil",
    "handicap",
    "medic",
    "medizin",
    "medikament",
    "farmac",
    "pharma",
    "illness",
    "malatti",
    "krankheit",
    "maladie",
    "enfermedad",
    "patolog",
    "patholog",
    "eczem",
    "psoria",
    "dermatit",
    "surgery",
    "chirurg",
    "cirug",
    "cardiac",
    "cardiopat",
    "heart condition",
    "ipertens",
    "hypertens",
    "pressione alta",
    "high blood pressure",
    "cancer",
    "cancro",
    "tumor",
    "tumour",
    "chemio",
    "chemo",
    "trombos",
    "thrombos",
    "dialys",
    "dialisi",
    "trapiant",
    "transplant",
    "autis",
    "dement",
    "alzheimer",
    "parkinson",
    # Senses and the body's devices.
    "deaf",
    "sordo",
    "sorda",
    "non udente",
    "non vedente",
    "ipovedent",
    "blind",
    "cieco",
    "cieca",
    "hearing aid",
    "apparecchio acustico",
    "latex",
)
HEALTH_WORDS: re.Pattern[str] = re.compile(
    r"(?<!\w)(?:" + "|".join(re.escape(stem) for stem in HEALTH_WORD_STEMS) + r")"
)


def is_health_note(notes: BookingNote | None) -> bool:
    """Whether a booking's notes hold health data, and so are Restricted."""

    if notes is None:
        return False

    return HEALTH_WORDS.search(normalize_search_text(str(notes))) is not None
