from collections.abc import Sequence

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.niche_text_repositories import NicheTextRepoContract
from app.repositories.document_queries import field_equals
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.niche_texts import (
    NicheTextDraftDocument,
    NicheTextReleaseDocument,
)
from app.schemas.dto.storage_pages import DocumentLatestQuery
from app.schemas.dto.storage_queries import DocumentFieldOrder
from app.schemas.typings.niches.constrained_integers import NicheTextVersion
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.strings import DocumentFieldText
from app.utilities.niches.niche_text_identity import release_id_for

NICHE_KEY_FIELD: DocumentFieldPath = DocumentFieldPath("niche_key")
VERSION_FIELD: DocumentFieldPath = DocumentFieldPath("version")


class NicheTextRepository(NicheTextRepoContract):
    """
    The niche template editor's documents (platform collections, migration
    1221): drafts under the niche's key; versions under an id derived from
    the niche and the version, so `insert_if_absent` lets one of two
    concurrent publishes of a version through. The newest version of each
    niche is one indexed probe of (niche_key, version).
    """

    def __init__(
        self,
        draft_collection: DocumentCollectionAdapterContract[NicheTextDraftDocument],
        release_collection: DocumentCollectionAdapterContract[NicheTextReleaseDocument],
    ) -> None:
        self._drafts: DocumentCollectionAdapterContract[NicheTextDraftDocument] = (
            draft_collection
        )
        self._releases: DocumentCollectionAdapterContract[NicheTextReleaseDocument] = (
            release_collection
        )

    def get_draft(self, niche_key: NicheKey) -> NicheTextDraftDocument | None:
        return self._drafts.get(niche_key.value)

    def list_drafts(
        self, niche_keys: Sequence[NicheKey]
    ) -> list[NicheTextDraftDocument]:
        if not niche_keys:
            return []

        return self._drafts.get_many([niche_key.value for niche_key in niche_keys])

    def save_draft(self, draft: NicheTextDraftDocument) -> None:
        self._drafts.upsert(draft.niche_key.value, draft)

    def delete_draft(self, niche_key: NicheKey) -> None:
        self._drafts.delete(niche_key.value)

    def latest_releases(
        self, niche_keys: Sequence[NicheKey]
    ) -> list[NicheTextReleaseDocument]:
        if not niche_keys:
            return []

        return self._releases.latest_by(
            DocumentLatestQuery(
                group_field=NICHE_KEY_FIELD,
                groups=tuple(
                    DocumentFieldText(niche_key.value) for niche_key in niche_keys
                ),
                sort_field=VERSION_FIELD,
            )
        )

    def get_release(
        self, niche_key: NicheKey, version: NicheTextVersion
    ) -> NicheTextReleaseDocument | None:
        return self._releases.get(str(release_id_for(niche_key, version)))

    def add_release(self, release: NicheTextReleaseDocument) -> bool:
        return bool(self._releases.insert_if_absent(str(release.id), release))

    def list_releases(
        self, niche_key: NicheKey, limit: DocumentQueryLimit
    ) -> list[NicheTextReleaseDocument]:
        return self._releases.list_by_fields(
            [field_equals(NICHE_KEY_FIELD, niche_key)],
            order=DocumentFieldOrder(field=VERSION_FIELD, is_descending=True),
            limit=limit,
        )
