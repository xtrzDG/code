"""
A website chat visitor's address goes with the message through the inbox
to the engine (and so to the booking tools: anonymous bookings are capped
per client network). Telegram and the other channels carry none.
"""

from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.conversations.strings import ChannelUserId
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.channels.test_widget import SESSION_KEY, enable_widget
from tests.channels.testbed import ChannelsTestbed

# Starlette's test client connects from this host name.
TEST_CLIENT_HOST: str = "testclient"


def test_the_visitors_address_reaches_the_engine_through_the_inbox() -> None:
    testbed = ChannelsTestbed()
    business = enable_widget(testbed)

    response = testbed.build_http_client().post(
        f"/v1/widget/{business.id}/messages",
        json={"session_key": SESSION_KEY, "text": "A table for two, please"},
    )
    [event] = testbed.inbound_event_repo.list_by_customer(
        business.id, [ChannelUserId(SESSION_KEY)], []
    )
    testbed.run_worker()

    assert response.status_code == 202, response.text
    assert event.customer_message is not None
    assert event.customer_message.client_ip_address == TEST_CLIENT_HOST
    [inbound] = testbed.pipeline.messages
    assert inbound.channel is ChannelKind.WEB_CHAT
    assert inbound.client_ip_address == TEST_CLIENT_HOST


def test_a_messenger_message_carries_no_address() -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)

    post_update(testbed, channel, build_update("Hello"))
    testbed.run_worker()

    [inbound] = testbed.pipeline.messages
    assert inbound.channel is ChannelKind.TELEGRAM
    assert inbound.client_ip_address is None
