"""How the guide recognizes the owner's own message from a phone."""

from typed_time_provider import Microseconds

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.setup import SetupStateDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.utilities.setup.phone_check import (
    PHONE_CHECK_WINDOW_MICROSECONDS,
    is_listening,
    listening_window,
    owner_sender_ids,
    whatsapp_id,
)
from app.utilities.setup.setup_keys import derive_setup_state_id
from tests.setup.guide_world import business_with_contacts

STARTED = Microseconds(1_800_000_000_000_000)


def contact(channel: ManagerContactChannel, address: str) -> ManagerContact:
    return ManagerContact(
        name=ManagerName("Nino"),
        channel=channel,
        address=ManagerContactAddress(address),
        language=LanguageTag("ka"),
    )


def state(
    started: Microseconds | None, tested: Microseconds | None = None
) -> SetupStateDocument:
    business_id = BusinessId()
    return SetupStateDocument(
        id=derive_setup_state_id(business_id),
        business_id=business_id,
        phone_check_started_at=started,
        phone_tested_at=tested,
    )


def test_the_owners_numbers_and_linked_chats_are_their_own_senders() -> None:
    business = business_with_contacts(
        [
            contact(ManagerContactChannel.WHATSAPP, "+995 599 11 22 33"),
            contact(ManagerContactChannel.TELEGRAM, " 777000111 "),
            contact(ManagerContactChannel.SMS, "+995598000000"),
            contact(ManagerContactChannel.EMAIL, "owner@example.com"),
        ]
    )

    senders = owner_sender_ids(business, [E164PhoneNumber("+995555123456")])

    assert {str(sender) for sender in senders} == {
        "995555123456",
        "995599112233",
        "995598000000",
        "777000111",
    }


def test_whatsapp_names_a_sender_by_the_digits_of_the_number() -> None:
    assert whatsapp_id("+1 (415) 555-0100") == "14155550100"
    assert whatsapp_id("") == ""


def test_the_guide_listens_half_an_hour_until_the_message_arrives() -> None:
    assert listening_window(None) is None
    assert listening_window(state(None)) is None
    assert listening_window(state(STARTED)) == (
        STARTED,
        Microseconds(int(STARTED) + PHONE_CHECK_WINDOW_MICROSECONDS),
    )

    assert is_listening(state(STARTED), STARTED) is True
    assert is_listening(state(STARTED), Microseconds(int(STARTED) - 1)) is False
    later = Microseconds(int(STARTED) + PHONE_CHECK_WINDOW_MICROSECONDS)
    assert is_listening(state(STARTED), later) is False
    assert is_listening(state(STARTED, tested=STARTED), STARTED) is False
    assert is_listening(None, STARTED) is False
