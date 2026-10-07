"""Customers see "typing…" in their messenger while the reply is written."""

from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.channels.typing_signals import TypingRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ChannelUserId
from tests.platform.lane_fakes import wait_until
from tests.resilience.typing_world import BOT_TOKEN, PAGE_TOKEN, TypingWorld


def test_telegram_shows_typing_with_send_chat_action() -> None:
    world = TypingWorld()
    bot = world.connect(ChannelKind.TELEGRAM, "my_bot", BOT_TOKEN)

    world.facilitator.signal_once(world.request(bot, user_id="777"))

    [request] = world.telegram.requests
    assert request.path == f"/bot{BOT_TOKEN}/sendChatAction"
    assert request.json() == {"chat_id": "777", "action": "typing"}


def test_whatsapp_shows_typing_with_the_read_receipt_of_the_message() -> None:
    world = TypingWorld()
    number = world.connect(ChannelKind.WHATSAPP, "106540352242922")

    world.facilitator.signal_once(
        world.request(number, user_id="995599123456", replying_to="wamid.HBgL")
    )

    [request] = world.meta.requests
    assert request.path == "/v23.0/106540352242922/messages"
    assert request.json() == {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": "wamid.HBgL",
        "typing_indicator": {"type": "text"},
    }
    assert request.headers["Authorization"].startswith("Bearer ")


def test_whatsapp_without_the_customers_message_id_shows_nothing() -> None:
    world = TypingWorld()
    number = world.connect(ChannelKind.WHATSAPP, "106540352242922")

    world.facilitator.signal_once(world.request(number))

    assert world.meta.requests == []


def test_messenger_and_instagram_send_typing_on() -> None:
    world = TypingWorld()
    page = world.connect(ChannelKind.MESSENGER, "1001", PAGE_TOKEN)
    instagram = world.connect(ChannelKind.INSTAGRAM, "1784", PAGE_TOKEN)

    world.facilitator.signal_once(world.request(page, user_id="psid-1"))
    world.facilitator.signal_once(world.request(instagram, user_id="igsid-1"))

    assert [request.path for request in world.meta.requests] == [
        "/v23.0/me/messages",
        "/v23.0/me/messages",
    ]
    assert [request.json() for request in world.meta.requests] == [
        {"recipient": {"id": "psid-1"}, "sender_action": "typing_on"},
        {"recipient": {"id": "igsid-1"}, "sender_action": "typing_on"},
    ]
    assert world.meta.requests[0].headers["Authorization"] == f"Bearer {PAGE_TOKEN}"


def test_typing_is_shown_again_until_the_reply_is_ready() -> None:
    world = TypingWorld()
    bot = world.connect(ChannelKind.TELEGRAM, "my_bot", BOT_TOKEN)

    with world.facilitator.keep_typing(world.request(bot)):
        assert wait_until(lambda: len(world.telegram.requests) >= 3)

    # Leaving the block stops the signals: their thread ends, so nothing
    # more comes once the reply is written.
    assert wait_until(world.facilitator_threads_stopped)
    assert len(world.telegram.requests) >= 3


def test_a_refused_signal_ends_the_typing_quietly() -> None:
    world = TypingWorld()
    world.telegram.respond(
        "POST",
        r"/sendChatAction$",
        {"ok": False, "error_code": 403, "description": "bot was blocked"},
        status_code=403,
    )
    bot = world.connect(ChannelKind.TELEGRAM, "my_bot", BOT_TOKEN)

    with world.facilitator.keep_typing(world.request(bot)):
        # The first signal is refused; no second one follows it.
        assert wait_until(lambda: len(world.telegram.requests) >= 1)
        assert wait_until(world.facilitator_threads_stopped)

    assert len(world.telegram.requests) == 1


def test_channels_without_typing_or_another_business_are_left_alone() -> None:
    world = TypingWorld()
    foreign = world.connect(
        ChannelKind.TELEGRAM, "their_bot", BOT_TOKEN, business_id=BusinessId()
    )
    unreadable = world.connect(ChannelKind.TELEGRAM, "my_bot")
    unreadable.encrypted_secret = None
    world.channels.save(unreadable)

    for request in (
        world.request(foreign),
        world.request(unreadable),
        TypingRequest(
            business_id=world.business_id,
            channel=ChannelKind.WEB_CHAT,
            channel_user_id=ChannelUserId("visitor"),
        ),
        TypingRequest(
            business_id=world.business_id,
            channel=ChannelKind.TELEGRAM,
            channel_user_id=ChannelUserId("42"),
        ),
    ):
        with world.facilitator.keep_typing(request):
            pass
        world.facilitator.signal_once(request)

    assert world.telegram.requests == []
