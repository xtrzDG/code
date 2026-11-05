"""Version 5 conversations read with who rated them (version 6): the team."""

import json

from app.adapters.storage.document_upgrades import (
    CURRENT_SCHEMA_VERSION,
    StoredJsonObject,
    upcasters_of,
    upgrade_stored_json,
)
from app.schemas.constants.conversations import ConversationRating, ConversationRatingBy
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.schemas.typings.users.prefixed_id import UserId

CONVERSATIONS = DocumentCollectionName("conversations")
AT: int = 1_790_000_000_000_000


def stored_v5(**fields: object) -> StoredJsonObject:
    return {
        "schema_version": "5",
        "business_id": str(BusinessId()),
        "contact_id": str(ContactId()),
        "assistant_version_id": str(AssistantVersionId()),
        "channel": "web_chat",
        "channel_user_id": "v1_9f2c4e1b7a3d48c6",
        "status": "open",
        "last_message_at": AT,
        "created_at": AT,
        "updated_at": AT,
        **fields,
    }


def read(document: StoredJsonObject) -> tuple[StoredJsonObject, ConversationDocument]:
    upgraded = upgrade_stored_json(
        document, upcasters_of(CONVERSATIONS), CURRENT_SCHEMA_VERSION[CONVERSATIONS]
    )
    return upgraded, ConversationDocument.model_validate_json(json.dumps(upgraded))


def test_a_rated_conversation_was_rated_by_the_team() -> None:
    upgraded, conversation = read(
        stored_v5(rating="bad", rated_by=str(UserId()), rated_at=AT)
    )

    assert upgraded["schema_version"] == str(int(CURRENT_SCHEMA_VERSION[CONVERSATIONS]))
    assert conversation.rating is ConversationRating.BAD
    assert conversation.rating_by is ConversationRatingBy.TEAM


def test_an_unrated_conversation_was_rated_by_nobody() -> None:
    upgraded, conversation = read(stored_v5(rating=None))

    assert "rating_by" not in upgraded
    assert conversation.rating_by is None


def test_who_rated_is_kept_when_already_stored() -> None:
    _, conversation = read(stored_v5(rating="good", rating_by="customer"))

    assert conversation.rating_by is ConversationRatingBy.CUSTOMER
