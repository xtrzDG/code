"""The platform team's announcements and the status page's daily history."""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.platform_status import (
    PlatformAnnouncementDocument,
    PlatformStatusDayDocument,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.platform_status.constrained_strings import StatusDay
from app.schemas.typings.platform_status.prefixed_id import AnnouncementId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit


class PlatformAnnouncementRepoContract(RepoContract, Protocol):
    def get(
        self, announcement_id: AnnouncementId
    ) -> PlatformAnnouncementDocument | None:
        raise NotImplementedError

    def save(self, announcement: PlatformAnnouncementDocument) -> None:
        raise NotImplementedError

    def list_active(
        self, limit: DocumentQueryLimit
    ) -> list[PlatformAnnouncementDocument]:
        """The announcements not resolved yet (an indexed match on the status)."""
        raise NotImplementedError

    def list_resolved_since(
        self, since: Microseconds, limit: DocumentQueryLimit
    ) -> list[PlatformAnnouncementDocument]:
        """Announcements resolved from `since` on, the latest resolved first."""
        raise NotImplementedError

    def list_page(self, page: KeysetSlice) -> list[PlatformAnnouncementDocument]:
        """One keyset page, the newest first (`page_by` on created_at)."""
        raise NotImplementedError


class PlatformStatusDayRepoContract(RepoContract, Protocol):
    def get_many(self, days: Sequence[StatusDay]) -> list[PlatformStatusDayDocument]:
        """The recorded days among these (keyed reads; missing days are absent)."""
        raise NotImplementedError

    def save(self, day: PlatformStatusDayDocument) -> None:
        raise NotImplementedError
