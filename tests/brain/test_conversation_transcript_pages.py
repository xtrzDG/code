"""A long transcript: the card shows the newest messages, earlier ones page back."""

from typing import Any

from typed_time_provider import Microseconds

from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.cabinet_http import bearer
from tests.brain.conversation_feed_helpers import cabinet
from tests.brain.scripted_turns import say, scripted

LONG_TRANSCRIPT: int = 230


def long_conversation(world: BrainWorld) -> ConversationId:
    """A conversation of 2 + LONG_TRANSCRIPT messages, one second apart."""

    reply = world.send("Добрый вечер")
    start: int = 1_800_000_000_000_000
    for index in range(LONG_TRANSCRIPT):
        is_customer: bool = index % 2 == 0
        moment = Microseconds(start + index * 1_000_000)
        world.message_repo.save(
            MessageDocument(
                conversation_id=reply.conversation_id,
                business_id=world.business.id,
                direction=(
                    MessageDirection.INBOUND
                    if is_customer
                    else MessageDirection.OUTBOUND
                ),
                author=MessageAuthor.CUSTOMER
                if is_customer
                else MessageAuthor.ASSISTANT,
                text=MessageText(f"Message {index}"),
                input_tokens=LlmTokenCount(0 if is_customer else 10),
                output_tokens=LlmTokenCount(0 if is_customer else 3),
                cost_micro_usd=CostMicroUsd(0 if is_customer else 7),
                created_at=moment,
                updated_at=moment,
            )
        )

    return reply.conversation_id


def test_the_card_pages_back_through_a_long_transcript() -> None:
    world = build_world(scripted(say("Здравствуйте!")))
    conversation_id = long_conversation(world)
    client = cabinet(world)
    base_url = f"/v1/businesses/{world.business.id}/conversations/{conversation_id}"

    card: dict[str, Any] = client.get(base_url, headers=bearer("staff")).json()
    shown: list[str] = [message["text"] for message in card["messages"]]
    pages: list[list[str]] = []
    cursor: str | None = card["earlier_messages_cursor"]
    while cursor is not None:
        page = client.get(
            f"{base_url}/messages",
            headers=bearer("staff"),
            params={"cursor": cursor, "limit": "60"},
        ).json()
        pages.append([message["text"] for message in page["items"]])
        cursor = page["next_cursor"]

    transcript = [text for page in reversed(pages) for text in page] + shown
    assert len(shown) == 100
    assert shown[-1] == f"Message {LONG_TRANSCRIPT - 1}"
    assert [len(page) for page in pages] == [60, 60, 12]
    assert transcript[0] == "Добрый вечер"
    assert transcript[1].endswith("Здравствуйте!")
    assert transcript[2:] == [f"Message {index}" for index in range(LONG_TRANSCRIPT)]
    assert card["conversation"]["message_count"] == LONG_TRANSCRIPT + 2
    assert card["conversation"]["customer_message_count"] == LONG_TRANSCRIPT // 2 + 1
    assert card["usage"]["cost_micro_usd"] >= 7 * (LONG_TRANSCRIPT // 2)
    assert card["usage"]["input_tokens"] >= 10 * (LONG_TRANSCRIPT // 2)
    views = [
        entry
        for entry in world.audit_log_repo.list_by_business(world.business.id)
        if entry.action is AuditAction.VIEW and str(entry.entity) == "conversation"
    ]
    assert len(views) == 1 + len(pages)


def test_earlier_messages_need_a_conversation_of_the_business() -> None:
    world = build_world(scripted(say("Здравствуйте!")))
    reply = world.send("Добрый вечер")
    client = cabinet(world)
    base_url = f"/v1/businesses/{world.business.id}/conversations"

    unknown = client.get(
        f"{base_url}/{ConversationId()}/messages", headers=bearer("owner")
    )
    stranger = client.get(
        f"{base_url}/{reply.conversation_id}/messages", headers=bearer("stranger")
    )
    broken = client.get(
        f"{base_url}/{reply.conversation_id}/messages",
        headers=bearer("owner"),
        params={"cursor": "bm9wZQ"},
    )
    first = client.get(
        f"{base_url}/{reply.conversation_id}/messages", headers=bearer("owner")
    )

    assert unknown.status_code == 404
    assert stranger.status_code in (403, 404)
    assert broken.status_code == 422
    texts = [message["text"] for message in first.json()["items"]]
    assert texts[0] == "Добрый вечер" and texts[1].endswith("Здравствуйте!")
    assert len(texts) == 2
    assert first.json()["next_cursor"] is None
