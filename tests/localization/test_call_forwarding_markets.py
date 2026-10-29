"""
Forwarding guides of the first markets after Georgia: named carriers with
the GSM codes, in the owner's language (Italian or English; an owner
language the cabinet lacks reads English), each marked as not yet confirmed
with the carrier until someone checks the carrier's own documentation.
"""

import pytest

from app.registries.localization.call_forwarding_carriers import (
    CARRIER_GUIDES_BY_COUNTRY,
)
from app.registries.localization.call_forwarding_guide_registry import (
    CallForwardingGuideRegistry,
)
from app.schemas.constants.localization import TextReviewStatus
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId
from tests.localization.builders import build_business
from tests.localization.cabinet_builders import (
    add_phone_channel,
    build_cabinet_world,
)
from tests.localization.test_call_forwarding import request_instructions

UNCONFIRMED: dict[str, str] = {
    "en": "not yet confirmed with",
    "it": "non ancora confermati con",
}
DIAL_STEP: dict[str, str] = {
    "en": "Dial **61*{number}#",
    "it": "Componi **61*{number}#",
}
# Market, assistant number, the owner's language, the language of the texts
# the owner reads (ru is not a cabinet language: English), the carriers.
MARKETS: list[tuple[str, str, str, str, list[str]]] = [
    ("IT", "+390212345678", "it", "it", ["TIM", "Vodafone", "WindTre", "Iliad"]),
    ("AM", "+37477123456", "ru", "en", ["Team Telecom Armenia", "Viva", "Ucom"]),
    ("AZ", "+994501234567", "en", "en", ["Azercell", "Bakcell", "Nar"]),
    ("UA", "+380501234567", "it", "it", ["Kyivstar", "Vodafone Ukraine", "lifecell"]),
    ("TR", "+905321234567", "en", "en", ["Turkcell", "Vodafone", "Türk Telekom"]),
    ("DE", "+4915112345678", "it", "it", ["Telekom", "Vodafone", "O2"]),
    (
        "IL",
        "+972587654321",
        "en",
        "en",
        ["Partner", "Cellcom", "Pelephone", "HOT Mobile"],
    ),
]


@pytest.mark.parametrize(
    ("country", "number", "language", "texts_language", "carriers"), MARKETS
)
def test_each_market_lists_its_carriers_with_ready_to_dial_codes(
    country: str,
    number: str,
    language: str,
    texts_language: str,
    carriers: list[str],
) -> None:
    world = build_cabinet_world()
    owner_id = UserId()
    business = build_business(owner_id, country, language)
    world.business_repo.save(business)
    add_phone_channel(world, business, number)

    instructions = request_instructions(world, business, owner_id)

    assert instructions.display_language == language
    assert [str(carrier.carrier_name) for carrier in instructions.carriers] == carriers
    assert str(instructions.codes[0].dial_code) == f"**61*{number}#"
    assert DIAL_STEP[texts_language].format(number=number) in instructions.steps[1]
    for carrier in instructions.carriers:
        assert [code.dial_code for code in carrier.codes] == [
            code.dial_code for code in instructions.codes
        ]
        assert carrier.note is not None
        assert UNCONFIRMED[texts_language] in carrier.note
        assert str(carrier.carrier_name) in carrier.note
        assert "{" not in carrier.note


def test_german_carriers_explain_that_the_code_replaces_the_mailbox() -> None:
    guide = CallForwardingGuideRegistry().get(CountryCode("DE"))
    italian = LanguageTag("it")

    notes = {
        str(carrier.carrier_name): str(carrier.notes.values[italian])
        for carrier in guide.carriers
        if carrier.notes is not None
    }

    assert "3311" in notes["Telekom"]
    assert "5500" in notes["Vodafone"]
    assert "333" in notes["O2"]
    assert all("non ancora confermati" in note for note in notes.values())


def test_a_known_fact_and_the_review_note_join_in_every_language() -> None:
    guide = CallForwardingGuideRegistry().get(CountryCode("AM"))
    team_telecom = guide.carriers[0]

    assert team_telecom.review_status is TextReviewStatus.NEEDS_REVIEW
    assert team_telecom.notes is not None
    assert {str(language) for language in team_telecom.notes.values} == {"en", "it"}
    for language, note in team_telecom.notes.values.items():
        assert "30" in note
        assert UNCONFIRMED[str(language)] in note


def test_georgia_keeps_magti_confirmed_and_the_others_unconfirmed() -> None:
    guide = CallForwardingGuideRegistry().get(CountryCode("GE"))
    english = LanguageTag("en")
    notes = [carrier.notes for carrier in guide.carriers]

    assert [carrier.review_status for carrier in guide.carriers] == [
        TextReviewStatus.REVIEWED,
        TextReviewStatus.NEEDS_REVIEW,
        TextReviewStatus.NEEDS_REVIEW,
    ]
    assert notes[0] is not None and "not yet" not in notes[0].values[english]
    assert notes[1] is not None and notes[1].values[english] == (
        "Standard GSM codes, not yet confirmed with Silknet: if a code fails, "
        "ask Silknet support."
    )


def test_every_new_market_is_a_draft_awaiting_review() -> None:
    drafts = {
        str(country)
        for country, carriers in CARRIER_GUIDES_BY_COUNTRY.items()
        if all(c.review_status is TextReviewStatus.NEEDS_REVIEW for c in carriers)
    }

    assert drafts == {"AM", "AZ", "UA", "TR", "IT", "DE", "IL"}
