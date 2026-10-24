"""The ambient storage scope: fail-closed, per context, nested, restored on errors."""

import asyncio
import contextvars
import threading

import pytest
from pydantic import ValidationError

from app.schemas.constants.storage import StorageScopeKind
from app.schemas.dto.storage import StorageScope
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.storage.storage_scope_context import StorageScopeContext


def test_default_scope_is_unscoped() -> None:
    scope = StorageScopeContext().current()

    assert scope.kind is StorageScopeKind.UNSCOPED
    assert scope.business_id is None
    assert scope == StorageScope.unscoped()


def test_scopes_nest_and_restore() -> None:
    storage_scope = StorageScopeContext()
    first_business_id, second_business_id = BusinessId(), BusinessId()

    with storage_scope.scoped_to_business(first_business_id) as entered:
        assert entered == StorageScope.for_business(first_business_id)
        assert storage_scope.current().business_id == first_business_id
        with storage_scope.scoped_to_business(second_business_id):
            assert storage_scope.current().business_id == second_business_id
            with storage_scope.platform_wide() as platform_scope:
                assert platform_scope.kind is StorageScopeKind.PLATFORM
                assert storage_scope.current().business_id is None
            assert storage_scope.current().business_id == second_business_id
        assert storage_scope.current().business_id == first_business_id

    assert storage_scope.current().kind is StorageScopeKind.UNSCOPED


def test_scope_is_restored_after_an_error() -> None:
    storage_scope = StorageScopeContext()

    with (
        pytest.raises(RuntimeError, match="boom"),
        storage_scope.scoped_to_business(BusinessId()),
    ):
        raise RuntimeError("boom")

    assert storage_scope.current().kind is StorageScopeKind.UNSCOPED


def test_instances_do_not_share_their_scope() -> None:
    first_context, second_context = StorageScopeContext(), StorageScopeContext()

    with first_context.platform_wide():
        assert second_context.current().kind is StorageScopeKind.UNSCOPED


def test_new_threads_start_unscoped_and_copied_contexts_inherit() -> None:
    storage_scope = StorageScopeContext()
    business_id = BusinessId()
    seen_in_thread: list[StorageScope] = []

    with storage_scope.scoped_to_business(business_id):
        thread = threading.Thread(
            target=lambda: seen_in_thread.append(storage_scope.current())
        )
        thread.start()
        thread.join()
        copied_context = contextvars.copy_context()

    assert seen_in_thread == [StorageScope.unscoped()]
    assert copied_context.run(storage_scope.current).business_id == business_id
    assert storage_scope.current().kind is StorageScopeKind.UNSCOPED


def test_concurrent_asyncio_tasks_keep_their_own_scope() -> None:
    storage_scope = StorageScopeContext()
    business_ids = [BusinessId() for _ in range(5)]

    async def read_scope(business_id: BusinessId) -> BusinessId | None:
        with storage_scope.scoped_to_business(business_id):
            await asyncio.sleep(0.01)
            return storage_scope.current().business_id

    async def run_all() -> list[BusinessId | None]:
        return list(
            await asyncio.gather(
                *(read_scope(business_id) for business_id in business_ids)
            )
        )

    assert asyncio.run(run_all()) == business_ids


def test_scope_value_requires_a_business_id_only_for_a_business() -> None:
    with pytest.raises(ValidationError, match="business id"):
        StorageScope(kind=StorageScopeKind.BUSINESS)

    with pytest.raises(ValidationError, match="business id"):
        StorageScope(kind=StorageScopeKind.PLATFORM, business_id=BusinessId())

    with pytest.raises(ValidationError, match="business id"):
        StorageScope(kind=StorageScopeKind.UNSCOPED, business_id=BusinessId())
