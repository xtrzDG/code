"""Periodic job: owners hear of sub-processor changes the notice period ahead."""

import logging
from collections.abc import Iterator
from datetime import date

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.legal_repositories import (
    SubprocessorAnnouncementRepoContract,
    SubprocessorNoticeRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.subprocessor_registries import SubprocessorRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.legal import SubprocessorAnnouncementDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.legal import SubprocessorChange, SubprocessorEntry
from app.schemas.typings.legal.constrained_integers import (
    NoticeRecipientCount,
    NotifiedBusinessCount,
)
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.legal.subprocessor_notice_sender import SubprocessorNoticeSender
from app.use_cases.shared.business_walk import walk_businesses
from app.utilities.legal.legal_keys import derive_subprocessor_announcement_id
from app.utilities.legal.subprocessor_dates import is_notice_due, utc_day

logger: logging.Logger = logging.getLogger(__name__)


class SendSubprocessorNoticesUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Daily job (DPA section 8.3): every announced addition or removal of a
    sub-processor reaches the owners of every business the notice period
    (30 days) before it takes effect, by e-mail to the owner's sign-in
    address, else by SMS, through the outbox, in the owner's language.

    A change is announced once: the announcement starts when its notice
    period opens and is complete once every business that existed then was
    told (`subprocessor_announcements`); a completed change is not walked
    again, and a business created later reads the change in the DPA's
    sub-processor table instead. Each business is told once
    (`subprocessor_notices`, the id derives from the business and the
    change) and its audit log records the notice. A job that could not run
    in time still tells the owners up to the notice period after the
    change, marked late; one failing business never stops the others, and
    the announcement stays open until it got its notice.
    """

    def __init__(
        self,
        subprocessor_registry: SubprocessorRegistryContract,
        announcement_repo: SubprocessorAnnouncementRepoContract,
        notice_repo: SubprocessorNoticeRepoContract,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        audit_log_repo: AuditLogRepoContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        localized_text_resolver: LocalizedTextResolverContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._registry: SubprocessorRegistryContract = subprocessor_registry
        self._announcement_repo: SubprocessorAnnouncementRepoContract = (
            announcement_repo
        )
        self._business_repo: BusinessRepoContract = business_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._sender: SubprocessorNoticeSender = SubprocessorNoticeSender(
            notice_repo,
            user_repo,
            audit_log_repo,
            manager_notifier,
            localized_text_resolver,
        )

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        today: date = utc_day(now)
        entries: dict[str, SubprocessorEntry] = {
            str(entry.key): entry for entry in self._registry.list_entries()
        }
        told: int = 0
        for change in self._registry.list_changes():
            if not is_notice_due(change, self._registry.notice_days(), today):
                continue

            announcement: SubprocessorAnnouncementDocument = self._announcement(
                change, now
            )
            if announcement.completed_at is None:
                told += self._announce(
                    change, entries[str(change.subprocessor)], announcement, now
                )

        return JobReport(processed_count=ProcessedItemCount(told))

    def _announce(
        self,
        change: SubprocessorChange,
        entry: SubprocessorEntry,
        announcement: SubprocessorAnnouncementDocument,
        now: Microseconds,
    ) -> int:
        """Tells every business that existed when the announcement started."""

        told: int = 0
        recipients: int = 0
        is_complete: bool = True
        for business in self._businesses():
            if int(business.created_at) >= int(announcement.started_at):
                continue

            try:
                queued: int | None = self._sender.notify(change, entry, business, now)
            except Exception:
                is_complete = False
                logger.exception(
                    "The notice of %s to business %s failed.", change.key, business.id
                )
                continue

            if queued is not None:
                told += 1
                recipients += queued

        announcement.notified_business_count = NotifiedBusinessCount(
            int(announcement.notified_business_count) + told
        )
        announcement.recipient_count = NoticeRecipientCount(
            int(announcement.recipient_count) + recipients
        )
        if is_complete:
            announcement.completed_at = now
        announcement.updated_at = now
        self._announcement_repo.save(announcement)
        return told

    def _announcement(
        self, change: SubprocessorChange, now: Microseconds
    ) -> SubprocessorAnnouncementDocument:
        """The change's announcement, started now if its notice period just opened."""

        existing: SubprocessorAnnouncementDocument | None = self._announcement_repo.get(
            change.key
        )
        if existing is not None:
            return existing

        started = SubprocessorAnnouncementDocument(
            id=derive_subprocessor_announcement_id(change.key),
            change_key=change.key,
            kind=change.kind,
            subprocessor=change.subprocessor,
            effective_on=change.effective_on,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        self._announcement_repo.save(started)
        return started

    def _businesses(self) -> Iterator[BusinessDocument]:
        # Every business on the platform, a keyset batch at a time.
        return walk_businesses(self._business_repo)
