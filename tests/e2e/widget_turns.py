"""
A website visitor's message in the end-to-end journeys: the API accepts it
(202) and the worker answers it; the answer is read back from the inbox
event the 202 names, as the widget would show it.
"""

from collections.abc import Mapping

import httpx2

from app.schemas.constants.conversations import ConversationStatus
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.prefixed_id import InboundEventId
from tests.e2e.harness import Workshop
from tests.e2e.harness_settings import JsonObject


def post_widget_message(
    workshop: Workshop,
    business_id: str,
    session_key: str,
    text: str,
    contact_name: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> httpx2.Response:
    """The widget's POST: accepted at once (202) or refused."""

    body: JsonObject = {"session_key": session_key, "text": text}
    if contact_name is not None:
        body["contact_name"] = contact_name

    return workshop.client.post(
        f"/v1/widget/{business_id}/messages",
        json=body,
        headers=dict(headers or {}),
    )


def answer_of(workshop: Workshop, accepted: httpx2.Response) -> JsonObject:
    """
    Let the worker answer an accepted message (and send what it queues),
    then read the answer: `text` is None while staff own the conversation.
    """

    assert accepted.status_code == 202, accepted.text
    workshop.run_queued_jobs()
    business_id = BusinessId(accepted.url.path.split("/")[3])
    return read_answer(
        workshop, business_id, InboundEventId(accepted.json()["event_id"])
    )


def ask_widget(
    workshop: Workshop,
    business_id: str,
    session_key: str,
    text: str,
    contact_name: str | None = None,
) -> JsonObject:
    """Send a widget message and return the worker's answer."""

    return answer_of(
        workshop,
        post_widget_message(workshop, business_id, session_key, text, contact_name),
    )


def read_answer(
    workshop: Workshop, business_id: BusinessId, event_id: InboundEventId
) -> JsonObject:
    container = workshop.container
    with container.utilities.storage_scope().scoped_to_business(business_id):
        event: InboundEventDocument | None = (
            container.repositories.inbound_event_repo().get(business_id, event_id)
        )
        assert event is not None and event.conversation_id is not None, event
        reply: MessageDocument | None = container.repositories.message_repo().get(
            business_id, event.reply_message_id
        )
        conversation: ConversationDocument | None = (
            container.repositories.conversation_repo().get(
                business_id, event.conversation_id
            )
        )

    assert conversation is not None
    return {
        "event_status": event.status.value,
        "conversation_id": str(event.conversation_id),
        "message_id": None if reply is None else str(reply.id),
        "text": None if reply is None else str(reply.text),
        "language": None
        if reply is None or reply.language is None
        else str(reply.language),
        "is_handed_off": conversation.status is ConversationStatus.HANDOFF,
    }
