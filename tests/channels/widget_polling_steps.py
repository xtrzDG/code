"""Steps of the widget polling tests: send, poll and add a staff message."""

from typing import Any

from fastapi.testclient import TestClient

from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.channels_payloads import HttpResponse
from tests.channels.test_widget import SESSION_KEY
from tests.channels.testbed import ChannelsTestbed

OTHER_VISITOR: str = "v1_someone_else_entirely_42"


def send(client: TestClient, business_id: BusinessId, text: str) -> dict[str, Any]:
    response = client.post(
        f"/v1/widget/{business_id}/messages",
        json={"session_key": SESSION_KEY, "text": text},
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


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
