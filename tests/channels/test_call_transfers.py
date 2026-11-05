"""
A call is put through to staff only while the business is open, once the
owner confirmed the staff notice of transfers, and only to an ordinary
mobile or landline of the business's country or the EU.
"""

import pytest

from app.schemas.constants.businesses import Weekday
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.profiles import (
    BusinessContacts,
    BusinessProfileDocument,
    OpeningInterval,
)
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.utilities.calls.call_follow_up_keys import call_settings_id_of
from tests.channels.channels_payloads import to_json_bytes
from tests.channels.voice_setup import (
    CALLER,
    VoiceSetup,
    build_voice_setup,
    tool_secret,
)

STAFF_MOBILE: str = "+995599777888"


def open_with_staff(
    setup: VoiceSetup,
    *,
    is_open: bool = True,
    is_confirmed: bool = True,
    staff_number: str = STAFF_MOBILE,
) -> None:
    testbed = setup.testbed
    testbed.profile_repo.save(
        BusinessProfileDocument(
            business_id=setup.business.id,
            niche_key=NicheKey.ENTERTAINMENT,
            answers_language=LanguageTag("ka"),
            contacts=BusinessContacts(
                handoff_phone_number=E164PhoneNumber(staff_number)
            ),
            hours=[
                OpeningInterval(
                    weekday=weekday,
                    opens_at=OpeningMinuteOfDay(0),
                    closes_at=ClosingMinuteOfDay(1440 if is_open else 1),
                )
                for weekday in Weekday
            ],
        )
    )
    now = testbed.clock.now_microseconds()
    testbed.call_settings_repo.save(
        CallSettingsDocument(
            id=call_settings_id_of(setup.business.id),
            business_id=setup.business.id,
            is_staff_transfer_confirmed=is_confirmed,
            created_at=now,
            updated_at=now,
        )
    )


def transfer_number(setup: VoiceSetup) -> str:
    """The call's transfer destination; can_transfer says the same to the prompt."""

    response = setup.testbed.build_http_client().post(
        "/v1/voice/webhooks/conversation-initiation",
        content=to_json_bytes({"caller_id": CALLER, "agent_id": "agent_1"}),
        headers={
            "X-Assistant-Business-Id": str(setup.business.id),
            "X-Assistant-Tool-Secret": tool_secret(setup.business.id),
        },
    )
    assert response.status_code == 200, response.text
    variables: dict[str, str] = response.json()["dynamic_variables"]
    number: str = variables["transfer_number"]
    assert variables["can_transfer"] == ("no" if number == "none" else "yes")
    return number


def test_while_open_and_confirmed_the_staff_mobile_is_the_destination() -> None:
    setup = build_voice_setup()
    open_with_staff(setup)

    assert transfer_number(setup) == STAFF_MOBILE


def test_while_closed_there_is_no_destination() -> None:
    setup = build_voice_setup()
    open_with_staff(setup, is_open=False)

    assert transfer_number(setup) == "none"


def test_without_the_owner_s_confirmation_there_is_no_destination() -> None:
    setup = build_voice_setup()
    open_with_staff(setup, is_confirmed=False)

    assert transfer_number(setup) == "none"


@pytest.mark.parametrize(
    ("staff_number", "expected"),
    [
        # Another EU country's mobile: allowed.
        ("+393471234567", "+393471234567"),
        # Italian premium rate, shared cost, a satellite phone, outside the EU.
        ("+39899123456", "none"),
        ("+39848123456", "none"),
        ("+8816212345678", "none"),
        ("+12025550123", "none"),
    ],
)
def test_only_ordinary_numbers_of_the_country_or_the_eu_are_dialled(
    staff_number: str, expected: str
) -> None:
    setup = build_voice_setup()
    open_with_staff(setup, staff_number=staff_number)

    assert transfer_number(setup) == expected
