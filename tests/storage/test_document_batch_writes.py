"""`upsert_many`: a bulk load writes a batch in one transaction, all or none."""

import pytest

from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.strings import ContactName
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import build_contact
from tests.storage.conftest import CollectionFactory, PostgresCollectionFactory
from tests.storage.rls_contacts import EMIRATES, JAPAN
from tests.storage.test_document_pages import conversation


@pytest.mark.usefixtures("platform_scope")
def test_a_batch_writes_and_overwrites_every_document(
    collections: CollectionFactory,
) -> None:
    conversations = collections(ConversationDocument, "conversations")
    business_id = BusinessId()
    first = [conversation(business_id, at) for at in (10, 20, 30)]
    conversations.upsert_many([(str(document.id), document) for document in first])
    changed = conversation(business_id, 99)
    changed.id = first[1].id
    later = [conversation(business_id, at) for at in (40, 50)]

    conversations.upsert_many(
        [(str(document.id), document) for document in [changed, *later]]
    )
    conversations.upsert_many([])

    stored = conversations.get_many([str(document.id) for document in first + later])
    assert sorted(int(document.last_message_at) for document in stored) == [
        10,
        30,
        40,
        50,
        99,
    ]


def test_a_batch_with_another_business_row_writes_nothing(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    contacts = postgres_collections(ContactDocument, "contacts")
    own_business_id, other_business_id = BusinessId(), BusinessId()
    own = build_contact(JAPAN, own_business_id)
    foreign = build_contact(EMIRATES, other_business_id)

    with storage_scope.scoped_to_business(own_business_id):
        with pytest.raises(AccessDeniedError):
            contacts.upsert_many([(str(own.id), own), (str(foreign.id), foreign)])

        assert contacts.get(str(own.id)) is None
        renamed = own.model_copy(update={"name": ContactName("Hanako")})
        contacts.upsert_many([(str(own.id), own), (str(own.id), renamed)])
        stored = contacts.get(str(own.id))

    assert stored is not None and stored.name == ContactName("Hanako")
