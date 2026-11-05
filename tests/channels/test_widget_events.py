"""
GET /v1/widget/{business_id}/events: a visitor's widget hears its own
typing and answers, in order; the ticket (never the visitor key) decides
whose; a model reply's text comes only after the guard passed it CLEAN.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor, ReplyGuardVerdict
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.test_widget import SESSION_KEY, enable_widget
from tests.channels.testbed import ChannelsTestbed
from tests.channels.widget_polling_steps import OTHER_VISITOR
from tests.channels.widget_stream_api import WidgetStreamApi, widget_event
from tests.live_events.live_api import parse_stream


def visitor_conversation(
    testbed: ChannelsTestbed, business_id: BusinessId, visitor_key: str = SESSION_KEY
) -> ConversationDocument:
    now = Microseconds(testbed.clock.now_microseconds())
    conversation = ConversationDocument(
        business_id=business_id,
        contact_id=ContactId(),
        assistant_version_id=AssistantVersionId(),
        channel=ChannelKind.WEB_CHAT,
        channel_user_id=ChannelUserId(visitor_key),
        last_message_at=now,
        created_at=now,
        updated_at=now,
    )
    testbed.conversation_repo.save(conversation)
    return conversation


def stored_answer(
    testbed: ChannelsTestbed,
    conversation: ConversationDocument,
    text: str,
    verdict: ReplyGuardVerdict | None = ReplyGuardVerdict.CLEAN,
    author: MessageAuthor = MessageAuthor.ASSISTANT,
) -> MessageDocument:
    now = Microseconds(testbed.clock.now_microseconds())
    message = MessageDocument(
        conversation_id=conversation.id,
        business_id=conversation.business_id,
        direction=MessageDirection.OUTBOUND,
        author=author,
        text=MessageText(text),
        language=LanguageTag("he"),
        model_id=None
        if author is not MessageAuthor.ASSISTANT
        else LlmModelId("claude-sonnet-4-5"),
        guard_verdict=verdict,
        created_at=now,
        updated_at=now,
    )
    testbed.message_repo.save(message)
    return message


def test_typing_comes_first_then_the_answer_with_its_cleared_text() -> None:
    testbed = ChannelsTestbed()
    business = enable_widget(testbed)
    api = WidgetStreamApi(testbed)
    answer = stored_answer(
        testbed, visitor_conversation(testbed, business.id), "כן, יש חניה"
    )

    response = api.stream(
        business.id,
        api.ticket(business.id, SESSION_KEY),
        script=[
            widget_event(business.id, LiveEventKind.WIDGET_TYPING, SESSION_KEY),
            widget_event(
                business.id, LiveEventKind.WIDGET_REPLY, SESSION_KEY, str(answer.id)
            ),
        ],
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    messages = parse_stream(response.text)
    assert [message.event for message in messages] == [
        "stream.ready",
        "typing_started",
        "answer_ready",
    ]
    assert messages[1].data == {}
    assert messages[2].data == {
        "message_id": str(answer.id),
        "author": "assistant",
        "direction": "rtl",
        "text": "כן, יש חניה",
    }
    assert all(message.id is None for message in messages)


def test_no_draft_text_before_the_guard_passed_it_clean() -> None:
    testbed = ChannelsTestbed()
    business = enable_widget(testbed)
    api = WidgetStreamApi(testbed)
    conversation = visitor_conversation(testbed, business.id)
    rewritten = stored_answer(
        testbed, conversation, "Rewritten", ReplyGuardVerdict.REWRITTEN
    )
    held = stored_answer(testbed, conversation, "Held", ReplyGuardVerdict.HANDED_OFF)
    unchecked = stored_answer(testbed, conversation, "Platform text", None)
    staff = stored_answer(
        testbed, conversation, "Staff here", None, author=MessageAuthor.STAFF
    )
    script = [
        widget_event(business.id, LiveEventKind.WIDGET_REPLY, SESSION_KEY, str(m.id))
        for m in (rewritten, held, unchecked, staff)
    ]

    messages = parse_stream(
        api.stream(business.id, api.ticket(business.id, SESSION_KEY), script).text
    )

    answers = [message.data for message in messages if message.event == "answer_ready"]
    assert [answer.get("message_id") for answer in answers] == [
        str(rewritten.id),
        str(held.id),
        str(unchecked.id),
        str(staff.id),
    ]
    assert all("text" not in answer for answer in answers)
    assert answers[3]["author"] == "staff"


def test_a_turn_without_a_message_and_a_foreign_message_say_only_poll() -> None:
    testbed = ChannelsTestbed()
    business = enable_widget(testbed)
    api = WidgetStreamApi(testbed)
    foreign = stored_answer(
        testbed, visitor_conversation(testbed, business.id, OTHER_VISITOR), "Not yours"
    )

    messages = parse_stream(
        api.stream(
            business.id,
            api.ticket(business.id, SESSION_KEY),
            script=[
                widget_event(business.id, LiveEventKind.WIDGET_REPLY, SESSION_KEY),
                # A forged event naming this visitor but another's message.
                widget_event(
                    business.id,
                    LiveEventKind.WIDGET_REPLY,
                    SESSION_KEY,
                    str(foreign.id),
                ),
            ],
        ).text
    )

    assert [(message.event, message.data) for message in messages[1:]] == [
        ("answer_ready", {}),
        ("answer_ready", {}),
    ]


def test_a_stream_hears_its_own_visitor_only() -> None:
    testbed = ChannelsTestbed()
    business = enable_widget(testbed)
    api = WidgetStreamApi(testbed)

    messages = parse_stream(
        api.stream(
            business.id,
            api.ticket(business.id, SESSION_KEY),
            script=[
                widget_event(business.id, LiveEventKind.WIDGET_TYPING, OTHER_VISITOR),
                widget_event(business.id, LiveEventKind.HANDOFF_CREATED, SESSION_KEY),
                widget_event(business.id, LiveEventKind.WIDGET_TYPING, SESSION_KEY),
            ],
        ).text
    )

    assert [message.event for message in messages] == [
        "stream.ready",
        "typing_started",
    ]


def test_the_ticket_decides_who_listens_and_the_key_is_never_in_the_address() -> None:
    testbed = ChannelsTestbed()
    business = enable_widget(testbed)
    other = enable_widget(testbed)
    api = WidgetStreamApi(testbed)
    ticket = str(api.ticket(business.id, SESSION_KEY))
    # One character of the signature changed; the one before the last always
    # carries six bits of it (a fixed "AA" tail was a valid ticket now and
    # then: when the signature happened to end that way).
    tampered = ticket[:-2] + ("B" if ticket[-2] == "A" else "A") + ticket[-1]

    refused = [
        api.stream(business.id, None),
        api.stream(business.id, "not a ticket"),
        api.stream(business.id, SESSION_KEY),
        api.stream(business.id, api.ticket(other.id, SESSION_KEY)),
        api.stream(business.id, api.expired_ticket(business.id, SESSION_KEY)),
        api.stream(business.id, tampered),
    ]

    assert [response.status_code for response in refused] == [401] * 6
    assert {response.json()["error"] for response in refused} == {
        "authentication_required"
    }
    assert SESSION_KEY not in str(api.ticket(business.id, SESSION_KEY))


def test_a_chat_switched_off_has_no_stream() -> None:
    testbed = ChannelsTestbed()
    owner_id = testbed.add_user("owner")
    business = testbed.add_business(owner_id, name="No chat")
    api = WidgetStreamApi(testbed)

    response = api.stream(business.id, api.ticket(business.id, SESSION_KEY))

    assert response.status_code == 404


def test_a_finished_stream_gives_its_place_back() -> None:
    testbed = ChannelsTestbed()
    business = enable_widget(testbed)
    api = WidgetStreamApi(testbed)

    for _ in range(5):
        assert api.stream(business.id, api.ticket(business.id, SESSION_KEY)).is_success

    assert api.streams.open_stream_count(business.id) == 0
