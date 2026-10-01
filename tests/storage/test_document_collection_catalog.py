"""Catalog, container wiring and migrations name the same collections."""

import re

import pytest
from base_pydantic_schemas import PersistentDocument
from dependency_injector import providers

from app.containers.adapters import AdaptersContainer
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.storage import CollectionIsolation
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import LlmTurnDocument
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.storage.document_collection_catalog import (
    DOCUMENT_COLLECTIONS,
    DocumentCollectionDefinition,
    collection_name_for,
)
from app.utilities.storage.document_tenancy import (
    infer_collection_isolation,
    read_document_business_id,
)
from tests.storage.builders import (
    COUNTRY_SAMPLES,
    build_business,
    build_contact,
    build_owner,
)
from tests.storage.storage_testing import MIGRATIONS_DIRECTORY

CREATED_COLLECTION_PATTERN: re.Pattern[str] = re.compile(
    r"workshop\.create_document_collection\('([a-z][a-z0-9_]*)'\)"
)
PLATFORM_DOCUMENT_TYPES: frozenset[type[PersistentDocument]] = frozenset(
    {
        UserDocument,
        OtpChallengeDocument,
        UserSessionDocument,
        BusinessDocument,
        AuditLogEntryDocument,
        LlmTurnDocument,
        QueuedJobDocument,
    }
)


def container_document_types() -> list[type[PersistentDocument]]:
    document_types: list[type[PersistentDocument]] = []
    for provider in AdaptersContainer.providers.values():
        if not isinstance(provider, providers.Singleton):
            continue

        document_type: object = provider.kwargs.get("document_type")
        assert isinstance(document_type, type)
        assert issubclass(document_type, PersistentDocument)
        document_types.append(document_type)

    return document_types


def migrated_collection_names() -> set[str]:
    names: set[str] = set()
    for migration_path in MIGRATIONS_DIRECTORY.glob("*.sql"):
        names.update(
            CREATED_COLLECTION_PATTERN.findall(
                migration_path.read_text(encoding="utf-8")
            )
        )

    return names


def test_every_container_collection_has_a_catalog_entry() -> None:
    catalog_types = {definition.document_type for definition in DOCUMENT_COLLECTIONS}

    assert set(container_document_types()) <= catalog_types


def test_catalog_names_and_types_are_unique() -> None:
    names = [str(definition.name) for definition in DOCUMENT_COLLECTIONS]
    document_types = [definition.document_type for definition in DOCUMENT_COLLECTIONS]

    assert len(names) == len(set(names))
    assert len(document_types) == len(set(document_types))


def test_migrations_create_a_table_for_every_catalog_entry() -> None:
    catalog_names = {str(definition.name) for definition in DOCUMENT_COLLECTIONS}

    assert catalog_names <= migrated_collection_names()


def test_collection_name_lookup() -> None:
    assert collection_name_for(UserDocument) == "users"
    assert collection_name_for(BusinessProfileDocument) == "business_profiles"

    with pytest.raises(NotFoundError, match="BusinessMember"):
        collection_name_for(BusinessMember)


@pytest.mark.parametrize(
    "definition",
    DOCUMENT_COLLECTIONS,
    ids=[str(definition.name) for definition in DOCUMENT_COLLECTIONS],
)
def test_isolation_of_every_collection(
    definition: DocumentCollectionDefinition,
) -> None:
    expected = (
        CollectionIsolation.PLATFORM
        if definition.document_type in PLATFORM_DOCUMENT_TYPES
        else CollectionIsolation.TENANT
    )

    assert infer_collection_isolation(definition.document_type) is expected


def test_business_id_of_tenant_business_and_platform_documents() -> None:
    owner = build_owner(COUNTRY_SAMPLES[0])
    business = build_business(COUNTRY_SAMPLES[0], owner.id)
    contact = build_contact(COUNTRY_SAMPLES[1], business.id)
    platform_entry = AuditLogEntryDocument(
        action=AuditAction.LOGIN,
        entity=AuditEntityName("user"),
        actor_id=UserId(),
    )
    business_entry = platform_entry.model_copy(update={"business_id": business.id})

    assert read_document_business_id(contact) == business.id
    assert read_document_business_id(business) == business.id
    assert read_document_business_id(owner) is None
    assert read_document_business_id(platform_entry) is None
    assert read_document_business_id(business_entry) == business.id
    assert isinstance(read_document_business_id(contact), BusinessId)


def test_isolation_inference_on_shapes_outside_the_catalog() -> None:
    assert infer_collection_isolation(ContactDocument) is CollectionIsolation.TENANT
    assert (
        infer_collection_isolation(AssistantVersionDocument)
        is CollectionIsolation.TENANT
    )
    assert infer_collection_isolation(BusinessMember) is CollectionIsolation.PLATFORM
