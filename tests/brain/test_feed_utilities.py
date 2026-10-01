"""Pure helpers of the conversation feed: search, previews, staff replies."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import StaffMessageDelivery, StaffReplyBlock
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.utilities.conversations.conversation_search import (
    digits_of,
    looks_like_phone,
    matches_search,
    normalize_search_text,
)
from app.utilities.conversations.message_previews import (
    PREVIEW_LENGTH,
    build_message_preview,
)
from app.utilities.conversations.staff_replies import (
    CUSTOMER_SERVICE_WINDOW_MICROSECONDS,
    assess_staff_reply,
    describe_block,
)

NOW: Microseconds = Microseconds(1_790_000_000_000_000)
HOUR: int = 60 * 60 * 1_000_000


def test_normalization_ignores_case_accents_and_spacing_in_any_script() -> None:
    assert normalize_search_text("  José   GARCÍA ") == "jose garcia"
    assert normalize_search_text("Ёлка") == "елка"
    assert normalize_search_text("İstanbul") == "istanbul"
    assert normalize_search_text("ნინო") == "ნინო"
    assert digits_of("+995 (599) ١٢٣") == "995599123"


@pytest.mark.parametrize(
    ("search", "expected"),
    [
        ("599 12-34-56", True),
        ("+995 599 123456", True),
        ("0599123456", True),
        ("00995599123456", True),
        ("٥٩٩١٢٣", True),
        ("12", False),
        ("599 000", False),
    ],
)
def test_phone_search_by_digits_in_any_format(search: str, expected: bool) -> None:
    assert matches_search(search, None, "+995599123456", []) is expected


def test_word_search_needs_every_word_in_the_name_or_the_messages() -> None:
    texts = ["Здравствуйте, есть столик на субботу?", "Да, на 20:00."]

    assert matches_search("нино столик", "Нино", None, texts)
    assert matches_search("СУББОТУ", "Нино", None, texts)
    assert not matches_search("нино банкет", "Нино", None, texts)
    assert matches_search("nino 599", "Nino", "+995599123456", [])
    assert not looks_like_phone("nino 599")
    assert matches_search("   ", None, None, [])


def test_preview_keeps_short_messages_and_cuts_long_ones_at_a_word() -> None:
    assert build_message_preview(MessageText("Hello\n\nthere")) == "Hello there"
    long_text = MessageText(" ".join(["word"] * 100))
    preview = str(build_message_preview(long_text))
    assert preview.endswith("word…")
    assert len(preview) <= PREVIEW_LENGTH + 1
    unbroken = str(build_message_preview(MessageText("x" * 500)))
    assert unbroken == "x" * PREVIEW_LENGTH + "…"


def conversation(
    channel: ChannelKind, is_sandbox: bool = False
) -> ConversationDocument:
    return ConversationDocument(
        business_id=BusinessId(),
        contact_id=ContactId(),
        assistant_version_id=AssistantVersionId(),
        channel=channel,
        channel_user_id=ChannelUserId("customer"),
        is_sandbox=is_sandbox,
        last_message_at=NOW,
    )


@pytest.mark.parametrize(
    ("channel", "is_sandbox", "connected", "block"),
    [
        (ChannelKind.PHONE, False, True, StaffReplyBlock.VOICE_CALL),
        (ChannelKind.OWNER_TEST, True, True, StaffReplyBlock.TEST_CONVERSATION),
        (ChannelKind.TELEGRAM, True, True, StaffReplyBlock.TEST_CONVERSATION),
        (ChannelKind.VIBER, False, True, StaffReplyBlock.UNSUPPORTED_CHANNEL),
        (ChannelKind.TELEGRAM, False, False, StaffReplyBlock.CHANNEL_DISCONNECTED),
        (ChannelKind.WEB_CHAT, False, False, StaffReplyBlock.CHANNEL_DISCONNECTED),
    ],
)
def test_blocked_replies(
    channel: ChannelKind,
    is_sandbox: bool,
    connected: bool,
    block: StaffReplyBlock,
) -> None:
    view = assess_staff_reply(conversation(channel, is_sandbox), connected, NOW, NOW)

    assert (view.is_available, view.block, view.delivery) == (False, block, None)
    assert describe_block(block)


def test_open_channels_and_the_24_hour_window() -> None:
    telegram = assess_staff_reply(conversation(ChannelKind.TELEGRAM), True, None, NOW)
    widget = assess_staff_reply(conversation(ChannelKind.WEB_CHAT), True, None, NOW)
    wrote_at = Microseconds(int(NOW) - 23 * HOUR)
    instagram = assess_staff_reply(
        conversation(ChannelKind.INSTAGRAM), True, wrote_at, NOW
    )
    late = assess_staff_reply(
        conversation(ChannelKind.MESSENGER),
        True,
        Microseconds(int(NOW) - CUSTOMER_SERVICE_WINDOW_MICROSECONDS),
        NOW,
    )
    never = assess_staff_reply(conversation(ChannelKind.WHATSAPP), True, None, NOW)

    assert telegram.delivery is StaffMessageDelivery.SENT
    assert telegram.window_closes_at is None
    assert widget.delivery is StaffMessageDelivery.STORED_FOR_WIDGET
    assert instagram.is_available
    assert instagram.window_closes_at == int(wrote_at) + 24 * HOUR
    assert (late.is_available, late.block) == (False, StaffReplyBlock.WINDOW_CLOSED)
    assert (never.is_available, never.block) == (False, StaffReplyBlock.WINDOW_CLOSED)
