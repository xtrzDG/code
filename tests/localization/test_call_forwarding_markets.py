"""
Forwarding guides of the first markets after Georgia: named carriers with
the GSM codes, in the owner's language, each marked as not yet confirmed
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
    "ru": "ещё не подтверждены",
    "ka": "ჯერ არ არის დადასტურებული",
    "he": "עדיין לא אושרו מול",
    "de": "noch nicht bestätigt",
}
MARKETS: list[tuple[str, str, str, list[str], str]] = [
    (
        "AM",
        "+37477123456",
        "ru",
        ["Team Telecom Armenia", "Viva", "Ucom"],
        "Наберите **61*+37477123456#",
    ),
    (
        "AZ",
        "+994501234567",
        "ru",
        ["Azercell", "Bakcell", "Nar"],
        "Наберите **61*+994501234567#",
    ),
    (
        "UA",
        "+380501234567",
        "ka",
        ["Kyivstar", "Vodafone Ukraine", "lifecell"],
        "აკრიფეთ **61*+380501234567#",
    ),
    (
        "TR",
        "+905321234567",
        "en",
        ["Turkcell", "Vodafone", "Türk Telekom"],
        "Dial **61*+905321234567#",
    ),
    (
        "DE",
        "+4915112345678",
        "de",
        ["Telekom", "Vodafone", "O2"],
        "Wählen Sie **61*+4915112345678#",
    ),
    (
        "IL",
        "+972587654321",
        "he",
        ["Partner", "Cellcom", "Pelephone", "HOT Mobile"],
        "חייגו **61*+972587654321#",
    ),
]


@pytest.mark.parametrize(
    ("country", "number", "language", "carriers", "dial_step"), MARKETS
)
def test_each_market_lists_its_carriers_with_ready_to_dial_codes(
    country: str,
    number: str,
    language: str,
    carriers: list[str],
    dial_step: str,
) -> None:
    world = build_cabinet_world()
    owner_id = UserId()
    business = build_business(owner_id, country, language)
    world.business_repo.save(business)
    add_phone_channel(world, business, number)

    instructions = request_instructions(world, business, owner_id)

    assert [str(carrier.carrier_name) for carrier in instructions.carriers] == carriers
    assert str(instructions.codes[0].dial_code) == f"**61*{number}#"
    assert dial_step in instructions.steps[1]
    for carrier in instructions.carriers:
        assert [code.dial_code for code in carrier.codes] == [
            code.dial_code for code in instructions.codes
        ]
        assert carrier.note is not None
        assert UNCONFIRMED[language] in carrier.note
        assert str(carrier.carrier_name) in carrier.note
        assert "{" not in carrier.note


def test_german_carriers_explain_that_the_code_replaces_the_mailbox() -> None:
    guide = CallForwardingGuideRegistry().get(CountryCode("DE"))
    german = LanguageTag("de")

    notes = {
        str(carrier.carrier_name): str(carrier.notes.values[german])
        for carrier in guide.carriers
        if carrier.notes is not None
    }

    assert "3311" in notes["Telekom"]
    assert "5500" in notes["Vodafone"]
    assert "333" in notes["O2"]
    assert all("noch nicht bestätigt" in note for note in notes.values())


def test_a_known_fact_and_the_review_note_join_in_every_language() -> None:
    guide = CallForwardingGuideRegistry().get(CountryCode("AM"))
    team_telecom = guide.carriers[0]

    assert team_telecom.review_status is TextReviewStatus.NEEDS_REVIEW
    assert team_telecom.notes is not None
    assert len(team_telecom.notes.values) == 5
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

    assert drafts == {"AM", "AZ", "UA", "TR", "DE", "IL"}
