"""
The sub-processor change notices (migration 1124): the announcement of each
change to the platform, and each business's notice, both keyed by derived
ids, so each exists once.
"""

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.legal_repositories import (
    SubprocessorAnnouncementRepoContract,
    SubprocessorNoticeRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.legal import (
    SubprocessorAnnouncementDocument,
    SubprocessorNoticeDocument,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.legal.constrained_strings import SubprocessorChangeKey
from app.utilities.legal.legal_keys import (
    derive_subprocessor_announcement_id,
    derive_subprocessor_notice_id,
)


class SubprocessorNoticeRepository(
    BusinessScopedRepository[SubprocessorNoticeDocument],
    SubprocessorNoticeRepoContract,
):
    """Notices keyed by their derived id: one per business and change."""

    def find(
        self, business_id: BusinessId, change_key: SubprocessorChangeKey
    ) -> SubprocessorNoticeDocument | None:
        return self._load(
            business_id, str(derive_subprocessor_notice_id(business_id, change_key))
        )

    def record_once(self, notice: SubprocessorNoticeDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(notice.id), notice))


class SubprocessorAnnouncementRepository(SubprocessorAnnouncementRepoContract):
    """Announcements keyed by their derived id: one per change (platform)."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[SubprocessorAnnouncementDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            SubprocessorAnnouncementDocument
        ] = collection

    def get(
        self, change_key: SubprocessorChangeKey
    ) -> SubprocessorAnnouncementDocument | None:
        return self._collection.get(
            str(derive_subprocessor_announcement_id(change_key))
        )

    def save(self, announcement: SubprocessorAnnouncementDocument) -> None:
        self._collection.upsert(str(announcement.id), announcement)
