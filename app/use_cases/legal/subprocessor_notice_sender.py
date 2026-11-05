import logging

from typed_time_provider import Microseconds

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.legal_repositories import (
    SubprocessorNoticeRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.legal import SubprocessorNoticeDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.legal import SubprocessorChange, SubprocessorEntry
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.legal.constrained_integers import NoticeRecipientCount
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject
from app.use_cases.legal.subprocessor_notice_texts import compose_subprocessor_notice
from app.use_cases.shared.owner_contacts import owner_contacts
from app.utilities.legal.legal_keys import derive_subprocessor_notice_id
from app.utilities.legal.subprocessor_dates import is_late_notice, utc_day

logger: logging.Logger = logging.getLogger(__name__)
SUBPROCESSOR_NOTICE_ENTITY: AuditEntityName = AuditEntityName("subprocessor_notice")


class SubprocessorNoticeSender:
    """
    Tells one business's owners about one change, once: the messages go to
    the outbox first (each address once per change, so a run that died
    before recording queues nothing twice), then the notice is recorded
    and the business's audit log names the change. A business whose owners
    have no address still gets its record (nobody could be told), so it is
    not tried every day.
    """

    def __init__(
        self,
        notice_repo: SubprocessorNoticeRepoContract,
        user_repo: UserRepoContract,
        audit_log_repo: AuditLogRepoContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._notice_repo: SubprocessorNoticeRepoContract = notice_repo
        self._user_repo: UserRepoContract = user_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._resolver: LocalizedTextResolverContract = localized_text_resolver

    def notify(
        self,
        change: SubprocessorChange,
        entry: SubprocessorEntry,
        business: BusinessDocument,
        now: Microseconds,
    ) -> int | None:
        """How many addresses were queued; None when the business was told before."""

        if self._notice_repo.find(business.id, change.key) is not None:
            return None

        is_late: bool = is_late_notice(change, utc_day(now))
        subject = StaffAlertSubject(f"subprocessor:{change.key}")
        contacts: list[ManagerContact] = owner_contacts(business, self._user_repo)
        if not contacts:
            logger.warning(
                "No owner of %s has an address for the notice of %s.",
                business.id,
                change.key,
            )

        queued: int = 0
        for contact in contacts:
            text = compose_subprocessor_notice(
                change, entry, business, contact.language, is_late, self._resolver
            )
            queued += int(
                self._manager_notifier.notify(
                    StaffNotification(
                        business_id=business.id,
                        contact=contact,
                        text=text,
                        subject=subject,
                    )
                )
            )

        recorded: bool = self._notice_repo.record_once(
            SubprocessorNoticeDocument(
                id=derive_subprocessor_notice_id(business.id, change.key),
                business_id=business.id,
                change_key=change.key,
                kind=change.kind,
                subprocessor=change.subprocessor,
                effective_on=change.effective_on,
                recipient_count=NoticeRecipientCount(queued),
                is_late=is_late,
                notified_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        if not recorded:
            return None

        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=None,
                action=AuditAction.CREATE,
                entity=SUBPROCESSOR_NOTICE_ENTITY,
                entity_id=AuditEntityReference(str(change.key)),
                created_at=now,
                updated_at=now,
            )
        )
        return queued
