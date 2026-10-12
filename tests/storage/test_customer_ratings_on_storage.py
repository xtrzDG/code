"""
A website visitor's rating on storage (version 6): written in one step that
never replaces the team's rating (a row lock on Postgres), so a visitor
racing the team never wins; another business's scope sees nothing; the
same on in-memory and on Postgres.
"""

import threading

import pytest
from typed_time_provider import Microseconds

from app.repositories.conversation_repositories import ConversationRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationRating, ConversationRatingBy
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.conversation_feed.answer_reviews import (
    ConversationRatingChange,
    CustomerRatingChange,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import CollectionFactory

BUSINESS: BusinessId = BusinessId()
OTHER_BUSINESS: BusinessId = BusinessId()
NOW: int = 1_790_000_000_000_000
PAGE: KeysetSlice = KeysetSlice(limit=KeysetReadLimit(10))
ROUNDS: int = 6


def conversations(collections: CollectionFactory) -> ConversationRepository:
    return ConversationRepository(collections(ConversationDocument, "conversations"))


def stored_conversation(repo: ConversationRepository) -> ConversationDocument:
    conversation = ConversationDocument(
        business_id=BUSINESS,
        contact_id=ContactId(),
        assistant_version_id=AssistantVersionId(),
        channel=ChannelKind.WEB_CHAT,
        channel_user_id=ChannelUserId("v1_9f2c4e1b7a3d48c6"),
        last_message_at=Microseconds(NOW),
    )
    repo.save(conversation)
    return conversation


def customer_bad(at: int) -> CustomerRatingChange:
    return CustomerRatingChange(
        rating=ConversationRating.BAD,
        rated_message_id=MessageId(),
        at=Microseconds(at),
    )


def test_a_thumbs_down_waits_for_improvement_and_stays_in_its_business(
    collections: CollectionFactory, storage_scope: StorageScopeContext
) -> None:
    repo = conversations(collections)
    with storage_scope.scoped_to_business(BUSINESS):
        conversation = stored_conversation(repo)
        rated = repo.set_customer_rating(
            BUSINESS, conversation.id, customer_bad(NOW + 1)
        )
        [waiting] = repo.page_awaiting_improvement(BUSINESS, PAGE)

    assert rated is not None and rated.rating_by is ConversationRatingBy.CUSTOMER
    assert waiting.id == conversation.id and waiting.rated_by is None
    with storage_scope.scoped_to_business(OTHER_BUSINESS):
        foreign = repo.set_customer_rating(
            OTHER_BUSINESS, conversation.id, customer_bad(NOW + 2)
        )
        assert repo.page_awaiting_improvement(OTHER_BUSINESS, PAGE) == []
    assert foreign is None


@pytest.mark.parametrize("round_index", range(ROUNDS))
def test_a_visitor_racing_the_team_never_replaces_its_rating(
    collections: CollectionFactory,
    storage_scope: StorageScopeContext,
    round_index: int,
) -> None:
    repo = conversations(collections)
    with storage_scope.scoped_to_business(BUSINESS):
        conversation = stored_conversation(repo)
    start = threading.Barrier(2)
    errors: list[BaseException] = []
    lock = threading.Lock()

    def visitor() -> None:
        start.wait()
        try:
            with storage_scope.scoped_to_business(BUSINESS):
                repo.set_customer_rating(
                    BUSINESS, conversation.id, customer_bad(NOW + round_index)
                )
        except BaseException as error:  # noqa: BLE001 - reported below
            with lock:
                errors.append(error)

    def team() -> None:
        start.wait()
        try:
            with storage_scope.scoped_to_business(BUSINESS):
                repo.set_rating(
                    BUSINESS,
                    conversation.id,
                    ConversationRatingChange(
                        rating=ConversationRating.GOOD,
                        rated_by=UserId(),
                        at=Microseconds(NOW + round_index),
                    ),
                )
        except BaseException as error:  # noqa: BLE001 - reported below
            with lock:
                errors.append(error)

    threads = [threading.Thread(target=visitor), threading.Thread(target=team)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    with storage_scope.scoped_to_business(BUSINESS):
        stored = repo.get(BUSINESS, conversation.id)
        assert repo.page_awaiting_improvement(BUSINESS, PAGE) == []
    assert stored is not None
    assert (stored.rating, stored.rating_by) == (
        ConversationRating.GOOD,
        ConversationRatingBy.TEAM,
    )
    assert stored.rated_message_id is None
