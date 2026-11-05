"""
The website chat's live stream against the whole API: widget answers
carry a stream ticket for the visitor, a worker's turn is heard as typing
and then the answer, and a widget that gave up waiting hands the chat to
staff.
"""

from typing import Any

from app.schemas.constants.live_events import LiveEventKind
from app.schemas.dto.channels.widget_streams import (
    WidgetStreamClaims,
    WidgetStreamMessageQuery,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.utilities.channels.widget_visitors import widget_visitor_id
from tests.e2e.harness import Workshop
from tests.e2e.widget_turns import post_widget_message
from tests.live_events.live_event_builders import RecordingSubscriber
from tests.sharing.test_widget_handoff_api import handoffs, open_web_chat

VISITOR: str = "visitor_live_0123456789"


def read_ticket(workshop: Workshop, ticket: str) -> WidgetStreamClaims:
    claims = workshop.container.utilities.widget_stream_ticket_signer().read(
        WidgetStreamTicket(ticket)
    )
    assert claims is not None
    return claims


def test_answers_to_the_visitor_key_carry_a_ticket_for_that_visitor(
    workshop: Workshop,
) -> None:
    restaurant = open_web_chat(workshop)

    accepted = post_widget_message(
        workshop, restaurant.business_id, VISITOR, "Есть ли парковка?"
    )
    polled = workshop.client.get(
        f"/v1/widget/{restaurant.business_id}/messages",
        headers={"X-Widget-Session-Key": VISITOR},
    )

    assert accepted.status_code == 202
    for body in (accepted.json(), polled.json()):
        claims = read_ticket(workshop, body["stream_ticket"])
        assert str(claims.business_id) == restaurant.business_id
        assert claims.visitor_id == widget_visitor_id(VISITOR)
        assert VISITOR not in body["stream_ticket"]


def test_the_worker_is_heard_typing_then_answering_with_the_cleared_text(
    workshop: Workshop,
) -> None:
    restaurant = open_web_chat(workshop)
    business_id = BusinessId(restaurant.business_id)
    heard = RecordingSubscriber()
    workshop.container.facilitators.widget_stream_facilitator().open(
        business_id, widget_visitor_id(VISITOR), None, heard
    )
    other = RecordingSubscriber()
    workshop.container.facilitators.widget_stream_facilitator().open(
        business_id, widget_visitor_id("visitor_live_9876543210"), None, other
    )

    post_widget_message(workshop, restaurant.business_id, VISITOR, "Здравствуйте!")
    workshop.run_queued_jobs()

    assert [event.event for event in heard.events] == [
        LiveEventKind.WIDGET_TYPING,
        LiveEventKind.WIDGET_REPLY,
    ]
    assert other.events == []
    reply = heard.events[1]
    assert reply.ids[0] == str(widget_visitor_id(VISITOR))
    read = workshop.container.operators.sharing.read_widget_stream_message_operator()
    view = read.operate(
        WidgetStreamMessageQuery(
            business_id=business_id,
            visitor_id=widget_visitor_id(VISITOR),
            message_id=MessageId(str(reply.ids[1])),
        )
    )
    assert view is not None
    assert view.author.value == "assistant"
    polled: dict[str, Any] = workshop.client.get(
        f"/v1/widget/{restaurant.business_id}/messages",
        headers={"X-Widget-Session-Key": VISITOR},
        params={"after": str(reply.ids[1])},
    ).json()
    assert polled["items"] == []
    assert view.text is not None


def test_a_widget_that_gave_up_waiting_hands_the_chat_to_staff_at_once(
    workshop: Workshop,
) -> None:
    restaurant = open_web_chat(workshop)
    post_widget_message(workshop, restaurant.business_id, VISITOR, "Вы здесь?")

    response = workshop.client.post(
        f"/v1/widget/{restaurant.business_id}/handoff",
        json={"session_key": VISITOR, "language": "ru", "reason": "no_answer"},
        headers={"Origin": "https://salobie.example"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_handed_off"] is True
    [handoff] = handoffs(workshop, restaurant)
    assert handoff["reason"] == "non_standard_request"
    assert handoff["urgency"] == "high"
    assert handoff["summary_code"] == "model_unavailable"
    # The queued message waits for staff: the assistant stays silent.
    calls = workshop.model.assistant_calls
    workshop.run_queued_jobs()
    assert workshop.model.assistant_calls == calls
