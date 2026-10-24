"""
The storage scope is fail-closed: code that entered no scope cannot touch
a tenant collection; operators enter the business's scope, or explicitly
the platform's, before their pipeline runs.
"""

import pytest
from base_pydantic_schemas import ImmutableDTO

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.pipeline_contract import PipelineContract
from app.operators.business_scoped_pipeline_operator import (
    BusinessScopedPipelineOperator,
)
from app.operators.platform_wide_pipeline_operator import (
    PlatformWidePipelineOperator,
)
from app.schemas.constants.storage import StorageScopeKind
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.storage import StorageScope
from app.schemas.exceptions.storage_errors import UnscopedStorageAccessError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.storage.storage_scope_context import StorageScopeContext
from app.utilities.storage.storage_scoping import (
    find_operation_business_id,
    require_tenant_scope,
)
from tests.storage.builders import COUNTRY_SAMPLES, build_contact, build_owner


class BusinessQuestion(ImmutableDTO):
    business_id: BusinessId


class PlatformQuestion(ImmutableDTO):
    """An input that names no business."""


class RecordingPipeline[InputData](PipelineContract[InputData, StorageScope]):
    """Answers with the scope it ran in."""

    def __init__(self, storage_scope: StorageScopeContext) -> None:
        self._storage_scope: StorageScopeContext = storage_scope

    def start(self, input_data: InputData) -> StorageScope:
        del input_data
        return self._storage_scope.current()


def test_unscoped_code_cannot_touch_a_tenant_collection_in_memory() -> None:
    storage_scope = StorageScopeContext()
    contacts = InMemoryDocumentCollectionAdapter(
        ContactDocument, tenant_scope=storage_scope
    )
    contact = build_contact(COUNTRY_SAMPLES[0], BusinessId())

    with pytest.raises(UnscopedStorageAccessError, match="outside a storage scope"):
        contacts.upsert(str(contact.id), contact)
    for read in (
        lambda: contacts.get(str(contact.id)),
        contacts.list_all,
        lambda: contacts.delete(str(contact.id)),
    ):
        with pytest.raises(UnscopedStorageAccessError):
            read()

    with storage_scope.scoped_to_business(contact.business_id):
        contacts.upsert(str(contact.id), contact)
    with storage_scope.platform_wide():
        assert contacts.list_all() == [contact]


def test_platform_collections_and_plain_test_collections_are_not_guarded() -> None:
    users = InMemoryDocumentCollectionAdapter(UserDocument)
    owner = build_owner(COUNTRY_SAMPLES[3])

    users.upsert(str(owner.id), owner)

    assert users.get(str(owner.id)) == owner


def test_the_scope_check_lets_business_and_platform_scopes_through() -> None:
    business_scope = StorageScope.for_business(BusinessId())

    assert require_tenant_scope(business_scope, "contacts") == business_scope
    assert require_tenant_scope(StorageScope.platform_wide(), "contacts").kind is (
        StorageScopeKind.PLATFORM
    )
    with pytest.raises(UnscopedStorageAccessError, match="contacts"):
        require_tenant_scope(StorageScope.unscoped(), "contacts")


def test_business_operators_run_in_the_scope_of_their_input() -> None:
    storage_scope = StorageScopeContext()
    business_id = BusinessId()

    by_field = BusinessScopedPipelineOperator(
        RecordingPipeline[BusinessQuestion](storage_scope), storage_scope
    ).operate(BusinessQuestion(business_id=business_id))
    by_id = BusinessScopedPipelineOperator(
        RecordingPipeline[BusinessId](storage_scope), storage_scope
    ).operate(business_id)
    without_business = BusinessScopedPipelineOperator(
        RecordingPipeline[PlatformQuestion](storage_scope), storage_scope
    ).operate(PlatformQuestion())

    assert by_field == StorageScope.for_business(business_id)
    assert by_id == StorageScope.for_business(business_id)
    # No business named: the caller's scope stays, unscoped by default.
    assert without_business == StorageScope.unscoped()
    assert storage_scope.current() == StorageScope.unscoped()


def test_platform_operators_escalate_explicitly_and_restore() -> None:
    storage_scope = StorageScopeContext()

    seen = PlatformWidePipelineOperator(
        RecordingPipeline[PlatformQuestion](storage_scope), storage_scope
    ).operate(PlatformQuestion())

    assert seen == StorageScope.platform_wide()
    assert storage_scope.current() == StorageScope.unscoped()


def test_the_business_of_an_operation_comes_from_its_input() -> None:
    business_id = BusinessId()

    assert find_operation_business_id(business_id) == business_id
    assert find_operation_business_id(BusinessQuestion(business_id=business_id)) == (
        business_id
    )
    assert find_operation_business_id(PlatformQuestion()) is None
    assert find_operation_business_id("business_not-typed") is None
