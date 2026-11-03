from collections.abc import Sequence

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.feature_flags import FeatureFlagRepoContract
from app.schemas.domain.feature_flags import FeatureFlagDocument
from app.schemas.typings.feature_flags.constrained_strings import FeatureFlagName


class FeatureFlagRepository(FeatureFlagRepoContract):
    """One row per feature flag, stored under its name; every read is keyed."""

    def __init__(
        self, collection: DocumentCollectionAdapterContract[FeatureFlagDocument]
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[FeatureFlagDocument] = (
            collection
        )

    def get(self, name: FeatureFlagName) -> FeatureFlagDocument | None:
        return self._collection.get(str(name))

    def get_many(self, names: Sequence[FeatureFlagName]) -> list[FeatureFlagDocument]:
        return self._collection.get_many([str(name) for name in names])

    def save(self, flag: FeatureFlagDocument) -> None:
        self._collection.upsert(str(flag.name), flag)
