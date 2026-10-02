"""Every stored document of the application, to prove a request changed nothing."""

from typing import Protocol, cast

from base_pydantic_schemas import PersistentDocument
from dependency_injector.providers import Provider

from app.containers.app import AppContainer
from app.contracts.storage import StorageScopeContract

type StorageSnapshot = dict[str, list[str]]


class ListableCollection(Protocol):
    def list_all(self) -> list[PersistentDocument]: ...


def take_storage_snapshot(
    container: AppContainer,
    storage_scope: StorageScopeContract,
) -> StorageSnapshot:
    """Each document collection's documents as sorted JSON, read platform-wide."""

    snapshot: StorageSnapshot = {}
    collection_providers = cast(
        dict[str, Provider[object]],
        container.adapters.collections.providers,
    )
    with storage_scope.platform_wide():
        for name, provider in sorted(collection_providers.items()):
            if not name.endswith("_collection"):
                continue

            collection = cast(ListableCollection, provider())
            snapshot[name] = sorted(
                document.model_dump_json() for document in collection.list_all()
            )

    return snapshot


def describe_changes(before: StorageSnapshot, after: StorageSnapshot) -> list[str]:
    """The collections whose documents differ, with how many were added."""

    return [
        f"{name}: {len(after.get(name, [])) - len(documents):+d} documents"
        for name, documents in before.items()
        if after.get(name, []) != documents
    ]
