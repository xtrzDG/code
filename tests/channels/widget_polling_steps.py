"""Steps of the widget polling tests: send, poll and add a staff message."""

from typing import Any

from fastapi.testclient import TestClient

from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.channels_payloads import HttpResponse
from tests.channels.outbox_reads import inbox
from tests.channels.test_widget import SESSION_KEY
from tests.channels.testbed import ChannelsTestbed

OTHER_VISITOR: str = "v1_someone_else_entirely_42"


def send(
    testbed: ChannelsTestbed, business_id: BusinessId, text: str
) -> dict[str, Any]:
    """
    A visitor's message: accepted at once (202), answered by the worker.
    Returns the answer as the widget comes to know it: its id and text, the
    visitor's own message as the polling position (`cursor`) and whether
    staff handle the conversation.
    """

    response = testbed.build_http_client().post(
        f"/v1/widget/{business_id}/messages",
        json={"session_key": SESSION_KEY, "text": text},
    )
    assert response.status_code == 202, response.text
    testbed.run_worker()
    [event] = [
        stored
        for stored in inbox(testbed)
        if str(stored.id) == response.json()["event_id"]
    ]
    assert event.conversation_id is not None, event
    reply = testbed.message_repo.get(business_id, event.reply_message_id)
    conversation = testbed.conversation_repo.get(business_id, event.conversation_id)
    return {
        "conversation_id": str(event.conversation_id),
        "text": None if reply is None else str(reply.text),
        "message_id": None if reply is None else str(reply.id),
        "cursor": str(event.customer_message_id),
        "is_handed_off": conversation is not None
        and conversation.status is ConversationStatus.HANDOFF,
    }


def poll(
    client: TestClient,
    business_id: BusinessId,
    after: str | None = None,
    session_key: str = SESSION_KEY,
) -> HttpResponse:
    params: dict[str, str] = {} if after is None else {"after": after}
    return client.get(
        f"/v1/widget/{business_id}/messages",
        params=params,
        headers={"X-Widget-Session-Key": session_key},
    )


def add_staff_message(
    testbed: ChannelsTestbed,
    business_id: BusinessId,
    conversation_id: ConversationId,
    text: str,
    language: str = "he",
) -> MessageDocument:
    testbed.clock.advance(5)
    now = testbed.clock.now_microseconds()
    message = MessageDocument(
        conversation_id=conversation_id,
        business_id=business_id,
        direction=MessageDirection.OUTBOUND,
        author=MessageAuthor.STAFF,
        text=MessageText(text),
        language=LanguageTag(language),
        created_at=now,
        updated_at=now,
    )
    testbed.message_repo.save(message)
    return message
