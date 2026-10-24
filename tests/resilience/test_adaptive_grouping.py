"""
When a burst of a customer's messages is answered: at once after a
finished sentence of more than 12 characters, after the fragment wait
otherwise (MESSAGE_COALESCE_SECONDS; 1.5 s on Telegram), and never later
than three fragment waits after the first message.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.domain.inbound_events import (
    InboundCustomerMessage,
    InboundEventDocument,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.constrained_integers import (
    MessageCoalesceSeconds,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.utilities.deliveries.delivery_keys import derive_inbound_event_id
from app.utilities.deliveries.inbound_bursts import burst_answer_at, fragment_wait
from app.utilities.deliveries.message_completeness import is_complete_message

SECOND: int = 1_000_000
START: int = 1_790_000_000 * SECOND
THREE_SECONDS: MessageCoalesceSeconds = MessageCoalesceSeconds(3)
BUSINESS: BusinessId = BusinessId()


@pytest.mark.parametrize(
    "text",
    [
        "Do you have a table for 4 tonight?",
        "Are you open today?",
        "Tomorrow at 8?",
        "I would like to book a haircut.",
        "Great, see you then!",
        "  Do you have a table tonight?  ",
        "Is parking free?)",
        'She said "see you at eight."',
        "У вас есть парковка?",
        "გაქვთ თავისუფალი მაგიდა?",
        "هل لديكم طاولة متاحة الليلة؟",
        "今夜8時に4人の席はありますか？",
        "Կարո՞ղ եմ ամրագրել սեղան։",
    ],
)
def test_a_finished_sentence_is_complete(text: str) -> None:
    assert is_complete_message(MessageText(text))


@pytest.mark.parametrize(
    "text",
    [
        "Hi",
        "Hi there!",
        "Ok, thanks.",
        "Tomorrow?",
        "Do you have a table for 4",
        "and one more thing...",
        "and one more thing…",
        "Thanks for the help)",
        "",
        "             ?",
    ],
)
def test_a_fragment_is_not_complete(text: str) -> None:
    assert not is_complete_message(MessageText(text))


def message(
    seconds: float, text: str, channel: ChannelKind = ChannelKind.WHATSAPP
) -> InboundEventDocument:
    created_at = Microseconds(START + int(seconds * SECOND))
    provider_message_id = ProviderMessageId(f"wamid.{int(seconds * 10)}")
    return InboundEventDocument(
        id=derive_inbound_event_id(BUSINESS, channel, provider_message_id),
        business_id=BUSINESS,
        kind=InboundEventKind.CUSTOMER_MESSAGE,
        channel=channel,
        provider_message_id=provider_message_id,
        customer_message=InboundCustomerMessage(
            channel_user_id=ChannelUserId("995599000111"), text=MessageText(text)
        ),
        created_at=created_at,
        updated_at=created_at,
    )


def at(seconds: float) -> Microseconds:
    return Microseconds(START + int(seconds * SECOND))


def test_a_fragment_waits_for_the_coalescing_time() -> None:
    burst = [message(0, "Hi"), message(1, "table for 4")]

    assert burst_answer_at(burst, THREE_SECONDS) == at(4)


def test_a_finished_newest_message_is_answered_at_once() -> None:
    burst = [message(0, "Hi"), message(1, "Do you have a table for 4 tonight?")]

    assert burst_answer_at(burst, THREE_SECONDS) == at(1)


def test_telegram_fragments_wait_a_second_and_a_half() -> None:
    burst = [message(0, "Hi", ChannelKind.TELEGRAM)]

    assert fragment_wait(ChannelKind.TELEGRAM, THREE_SECONDS) == 1_500_000
    assert fragment_wait(ChannelKind.WHATSAPP, THREE_SECONDS) == 3 * SECOND
    assert burst_answer_at(burst, THREE_SECONDS) == at(1.5)
    # Never longer than the coalescing time itself.
    assert fragment_wait(ChannelKind.TELEGRAM, MessageCoalesceSeconds(1)) == SECOND


def test_a_customer_who_keeps_writing_waits_three_fragment_waits_at_most() -> None:
    burst = [message(seconds, "and") for seconds in range(0, 9, 2)]

    assert burst_answer_at(burst, THREE_SECONDS) == at(9)


def test_without_coalescing_nothing_waits() -> None:
    burst = [message(0, "Hi")]

    assert burst_answer_at(burst, MessageCoalesceSeconds(0)) == at(0)
