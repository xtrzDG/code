"""
Call initiation gives the voice agent the call's date and time and nothing
about the caller (a caller id proves nobody's identity); a blocked number
and a business past its day's call minutes are refused.
"""

from typing import Any

import pytest

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.bookings import BookingStatus, ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import (
    ChannelIdentity,
    ContactBlock,
    ContactDocument,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.billing.constrained_integers import UsageQuantity
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
    ResourceCapacity,
)
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.channels.voice_service import MAX_DAILY_CALL_MINUTES
from tests.channels.channels_payloads import HttpResponse, to_json_bytes
from tests.channels.channels_settings import UNITED_STATES
from tests.channels.voice_setup import (
    ASSISTANT_LINE,
    CALLER,
    VoiceSetup,
    build_voice_setup,
    tool_secret,
)

HOUR: int = 60 * 60


def post_start(setup: VoiceSetup, caller: str | None = CALLER) -> HttpResponse:
    body: dict[str, Any] = {"agent_id": "agent_1", "called_number": ASSISTANT_LINE}
    if caller is not None:
        body["caller_id"] = caller

    return setup.testbed.build_http_client().post(
        "/v1/voice/webhooks/conversation-initiation",
        content=to_json_bytes(body),
        headers={
            "X-Assistant-Business-Id": str(setup.business.id),
            "X-Assistant-Tool-Secret": tool_secret(setup.business.id),
        },
    )


def start_call(setup: VoiceSetup, caller: str | None = CALLER) -> dict[str, Any]:
    response = post_start(setup, caller)
    assert response.status_code == 200, response.text
    variables: dict[str, Any] = response.json()["dynamic_variables"]
    return variables


def known_caller_with_a_booking(setup: VoiceSetup) -> None:
    """The caller's number is proved for a named contact with a booking."""

    testbed = setup.testbed
    setup.contact.verified_phone_number = E164PhoneNumber(CALLER)
    setup.contact.name = ContactName("Nino")
    testbed.contact_repo.save(setup.contact)
    resource = ResourceDocument(
        business_id=setup.business.id,
        kind=ResourceKind.ARENA,
        name=ResourceName("Arena 2"),
        capacity=ResourceCapacity(6),
    )
    testbed.resource_repo.save(resource)
    starts_at = testbed.clock.now_microseconds() // 1_000_000 + 28 * HOUR
    testbed.booking_repo.save(
        BookingDocument(
            business_id=setup.business.id,
            resource_id=resource.id,
            contact_id=setup.contact.id,
            starts_at=BookingStartsAtUnixSeconds(starts_at),
            ends_at=BookingEndsAtUnixSeconds(starts_at + HOUR),
            party_size=PartySize(4),
            status=BookingStatus.CONFIRMED,
            source_channel=ChannelKind.TELEGRAM,
        )
    )


def test_the_agent_learns_the_local_date_time_and_the_next_days() -> None:
    variables = start_call(build_voice_setup())

    assert variables["local_now"] == "Thursday 2026-10-01 16:00"
    assert variables["next_days"].startswith("Fri 2026-10-02, Sat 2026-10-03")
    assert variables["next_days"].endswith("Thu 2026-10-08")
    assert variables["timezone"] == "Asia/Tbilisi"


def test_the_local_time_follows_the_business_time_zone() -> None:
    variables = start_call(build_voice_setup(country=UNITED_STATES))

    assert variables["local_now"] == "Thursday 2026-10-01 08:00"
    assert variables["timezone"] == "America/New_York"


@pytest.mark.parametrize("caller", [CALLER, None])
def test_nothing_about_the_caller_comes_from_the_caller_id(caller: str | None) -> None:
    setup = build_voice_setup()
    known_caller_with_a_booking(setup)

    response = post_start(setup, caller)

    assert response.status_code == 200, response.text
    assert set(response.json()["dynamic_variables"]) == {
        "is_open_now",
        "can_transfer",
        "transfer_number",
        "local_now",
        "next_days",
        "timezone",
    }
    assert "Nino" not in response.text and "Arena 2" not in response.text


@pytest.mark.parametrize("by_verified_phone", [True, False])
def test_a_blocked_number_is_refused(by_verified_phone: bool) -> None:
    setup = build_voice_setup()
    if by_verified_phone:
        setup.contact.verified_phone_number = E164PhoneNumber(CALLER)
        setup.testbed.contact_repo.save(setup.contact)
    block = ContactBlock(
        blocked_at=setup.testbed.clock.now_microseconds(), blocked_by=UserId()
    )

    def blocked_by_staff(contact: ContactDocument) -> None:
        contact.block = block

    setup.testbed.contact_repo.change_card(
        setup.business.id, setup.contact.id, blocked_by_staff
    )

    blocked = post_start(setup)
    withheld = post_start(setup, caller=None)

    assert blocked.status_code == 409, blocked.text
    assert "blocked" in blocked.text
    assert withheld.status_code == 200, withheld.text
    assert setup.testbed.call_greeting.requests[-1:] != []


def test_a_blocked_call_only_contact_is_refused_beside_a_proved_one() -> None:
    # A WhatsApp customer proved the number; calls from it share a contact
    # of their own (a caller id never joins a proved contact), and staff
    # blocked that one: both hold the number, the block still counts.
    setup = build_voice_setup()
    whatsapp = ChannelIdentity(
        channel=ChannelKind.WHATSAPP, channel_user_id=ChannelUserId(CALLER[1:])
    )
    setup.contact.verified_phone_number = E164PhoneNumber(CALLER)
    setup.contact.channel_identities = [whatsapp]
    setup.testbed.contact_repo.save(setup.contact)
    now = setup.testbed.clock.now_microseconds()
    setup.testbed.contact_repo.save(
        ContactDocument(
            business_id=setup.business.id,
            phone_number=E164PhoneNumber(CALLER),
            channel_identities=[
                ChannelIdentity(
                    channel=ChannelKind.PHONE, channel_user_id=ChannelUserId(CALLER)
                )
            ],
            block=ContactBlock(blocked_at=now, blocked_by=UserId()),
            created_at=now,
            updated_at=now,
        )
    )

    blocked = post_start(setup)

    assert blocked.status_code == 409, blocked.text
    assert "blocked" in blocked.text


@pytest.mark.parametrize(
    ("minutes", "status"),
    [(MAX_DAILY_CALL_MINUTES - 1, 200), (MAX_DAILY_CALL_MINUTES, 409)],
)
def test_a_day_of_call_minutes_is_capped(minutes: int, status: int) -> None:
    setup = build_voice_setup()
    now = setup.testbed.clock.now_microseconds()
    setup.testbed.usage_event_repo.append(
        UsageEventDocument(
            business_id=setup.business.id,
            kind=UsageKind.VOICE_SECONDS,
            quantity=UsageQuantity(minutes * 60),
            occurred_at=now,
            created_at=now,
            updated_at=now,
        )
    )

    response = post_start(setup)

    assert response.status_code == status, response.text


def test_the_greeting_is_said_as_built_with_nothing_appended() -> None:
    # The greeting itself ends with where the privacy notice is
    # (tests/brain/test_call_greeting_without_recording.py), so the call
    # start adds nothing: the caller hears it once.
    response = post_start(build_voice_setup())

    first_message = response.json()["conversation_config_override"]["agent"][
        "first_message"
    ]
    assert first_message == "[ka] AI assistant of Funicular VR."
