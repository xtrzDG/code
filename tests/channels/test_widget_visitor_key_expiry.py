"""
A website chat visitor's key expires on the server after idling: after
`VISITOR_KEY_IDLE_DAYS` without a message the poll reads nothing with it,
and a key used again after the gap reads only its new conversation.
"""

from typed_time_provider import Microseconds

from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.conversations.strings import ChannelUserId
from app.use_cases.channels.widget_visitor_keys import (
    MICROSECONDS_PER_DAY,
    VISITOR_KEY_IDLE_DAYS,
    readable_conversations,
)
from tests.channels.test_widget import enable_widget
from tests.channels.testbed import ChannelsTestbed
from tests.channels.widget_polling_steps import poll, send
from tests.channels.widget_tickets import without_ticket

DAY_SECONDS: int = 24 * 60 * 60
NOW: int = 400 * MICROSECONDS_PER_DAY


def conversation(created_day: int, last_day: int) -> ConversationDocument:
    return ConversationDocument(
        business_id=BusinessId(),
        contact_id=ContactId(),
        assistant_version_id=AssistantVersionId(),
        channel=ChannelKind.WEB_CHAT,
        channel_user_id=ChannelUserId("v1_visitor_key_of_a_test_000"),
        last_message_at=Microseconds(last_day * MICROSECONDS_PER_DAY),
        created_at=Microseconds(created_day * MICROSECONDS_PER_DAY),
        updated_at=Microseconds(last_day * MICROSECONDS_PER_DAY),
    )


def test_the_readable_run_stops_at_the_first_idle_gap() -> None:
    current = conversation(398, 399)
    yesterday_week = conversation(380, 390)
    long_ago = conversation(300, 340)

    readable = readable_conversations(
        [long_ago, current, yesterday_week], Microseconds(NOW)
    )

    assert readable == [current, yesterday_week]
    assert readable_conversations([long_ago], Microseconds(NOW)) == []
    assert VISITOR_KEY_IDLE_DAYS == 30


def test_an_idle_key_reads_nothing_and_starts_afresh_when_used_again() -> None:
    testbed = ChannelsTestbed()
    business = enable_widget(testbed)
    client = testbed.build_http_client()
    first = send(testbed, business.id, "Hi")
    assert [item["id"] for item in poll(client, business.id).json()["items"]] == []
    assert poll(client, business.id, after=first["cursor"]).json()["items"] != []

    testbed.clock.advance((VISITOR_KEY_IDLE_DAYS + 1) * DAY_SECONDS)

    idle = poll(client, business.id, after=first["cursor"])
    assert idle.status_code == 200
    assert without_ticket(idle.json()) == {
        "items": [],
        "cursor": None,
        "has_more": False,
        "is_handed_off": False,
    }

    again = send(testbed, business.id, "Hello again")
    # The old answer is behind the idle gap: even from the old position only
    # the new answer comes.
    body = poll(client, business.id, after=first["cursor"]).json()
    assert [item["id"] for item in body["items"]] == [again["message_id"]]
    # Without a position the whole chat is read: still nothing from before.
    whole = poll(client, business.id).json()
    assert whole["items"] == []
    assert whole["cursor"] == again["cursor"]
