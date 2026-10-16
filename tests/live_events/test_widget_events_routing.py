"""
The website chat's own live events: published for website visitors only,
heard by their widget streams, never by cabinets and never replayed.
"""

from app.adapters.events.in_memory_live_event_bus_adapter import (
    InMemoryLiveEventBusAdapter,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.dto.conversation_feed.conversation_actions import (
    SendStaffMessageCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_strings import StaffReplyText
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.utilities.channels.widget_visitors import widget_visitor_id
from tests.brain.brain_world import build_world
from tests.brain.scripted_turns import say, scripted
from tests.channels.test_staff_reply_delivery import staff_replies
from tests.channels.test_widget import SESSION_KEY, enable_widget
from tests.channels.testbed import ChannelsTestbed
from tests.channels.widget_polling_steps import send
from tests.channels.widget_stream_api import widget_event
from tests.live_events.live_api import LiveApi, parse_stream
from tests.live_events.live_event_builders import (
    RecordingSubscriber,
    make_event,
)

VISITOR: str = "v1_9f2c4e1b7a3d48c6"


def test_a_website_answer_is_announced_to_its_visitor_and_others_are_not() -> None:
    world = build_world(scripted(say("Hello!"), say("Hello on WhatsApp!")))

    web = world.send("Hi", channel=ChannelKind.WEB_CHAT, user_id=VISITOR, phone=None)
    world.send("Hi")

    widget_events = [
        event
        for event in world.live_events.events
        if event.event is LiveEventKind.WIDGET_REPLY
    ]
    [conversation] = [
        item for item in world.conversations() if item.channel is ChannelKind.WEB_CHAT
    ]
    [reply] = [
        message
        for message in world.messages(conversation.id)
        if message.author.value == "assistant"
    ]
    assert web.text is not None
    assert [event.ids for event in widget_events] == [
        (str(widget_visitor_id(VISITOR)), str(reply.id))
    ]


def test_a_staff_reply_in_a_website_chat_reaches_the_visitors_stream() -> None:
    testbed = ChannelsTestbed()
    business = enable_widget(testbed)
    asked = send(testbed, business.id, "Hi")
    before = len(testbed.live_events.events)

    sent = staff_replies(testbed).run(
        SendStaffMessageCommand(
            user_id=testbed.add_user("staff"),
            business_id=business.id,
            conversation_id=ConversationId(asked["conversation_id"]),
            text=StaffReplyText("Dana here, the terrace is open."),
        )
    )

    announced = testbed.live_events.events[before:]
    assert [event.event for event in announced] == [
        LiveEventKind.CONVERSATION_MESSAGE,
        LiveEventKind.WIDGET_REPLY,
    ]
    assert announced[1].ids == (
        str(widget_visitor_id(SESSION_KEY)),
        str(sent.message.id),
    )


def test_cabinet_streams_never_carry_widget_events() -> None:
    api = LiveApi()
    business_id = api.business.id
    own = make_event(business_id, LiveEventKind.HANDOFF_CREATED, "handoff_1234abcd")

    response = api.stream(
        publish=[
            widget_event(business_id, LiveEventKind.WIDGET_TYPING, VISITOR),
            own,
            widget_event(business_id, LiveEventKind.WIDGET_REPLY, VISITOR),
        ]
    )

    assert [message.event for message in parse_stream(response.text)] == [
        "stream.ready",
        "handoff.created",
    ]


def test_widget_events_are_not_kept_for_a_cabinets_replay() -> None:
    bus = InMemoryLiveEventBusAdapter()
    business_id = BusinessId()
    seen = make_event(business_id)
    typing = widget_event(business_id, LiveEventKind.WIDGET_TYPING, VISITOR)
    later = make_event(business_id, LiveEventKind.BOOKING_CHANGED)
    stream = RecordingSubscriber()
    bus.subscribe(business_id, stream)

    for event in (seen, typing, later):
        bus.publish(event)

    assert stream.events == [seen, typing, later]
    assert bus.replay_after(business_id, seen.id) == [later]
    assert bus.replay_after(business_id, typing.id) is None
