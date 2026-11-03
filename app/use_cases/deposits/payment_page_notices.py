"""Telling the owners that the pages guests pay deposits on changed."""

import logging
from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.owner_emails import OwnerAccountEmailFacilitatorContract
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.deposits.payment_page_changes import PaymentPageChange
from app.schemas.dto.notifications.staff_alerts import StaffAlert
from app.schemas.typings.notifications.constrained_strings import (
    PushNotificationTag,
    StaffAlertSubject,
)
from app.use_cases.deposits.payment_page_notice_texts import PaymentPageNoticeTexts

logger: logging.Logger = logging.getLogger(__name__)


class PaymentPageNotices:
    """
    Every owner of the business (their devices with notifications on and
    the e-mail address of their account, PAY-06) and the business's staff
    contacts hear, urgently, that a page guests pay deposits on was added,
    removed, made the default or given to a rule: money goes to these
    pages, so a change nobody of the team made is a takeover. The link
    opens the person's Account → Security, where unknown sessions are
    ended. Never raises.
    """

    def __init__(
        self,
        staff_alerts: StaffAlertFacilitatorContract,
        resolver: LocalizedTextResolverContract,
        owner_emails: OwnerAccountEmailFacilitatorContract,
    ) -> None:
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._resolver: LocalizedTextResolverContract = resolver
        self._owner_emails: OwnerAccountEmailFacilitatorContract = owner_emails

    def notify(
        self,
        business: BusinessDocument,
        changes: Sequence[PaymentPageChange],
        now: Microseconds,
    ) -> None:
        if not changes:
            return

        alert = StaffAlert(
            business_id=business.id,
            target=StaffLinkTarget.ACCOUNT_SECURITY,
            tag=PushNotificationTag(f"deposit_pages:{business.id}"),
            subject=StaffAlertSubject(f"deposit_pages:{business.id}-{int(now)}"),
            is_urgent=True,
            member_roles=[BusinessMemberRole.OWNER],
        )
        texts = PaymentPageNoticeTexts(self._resolver, business.name, changes)
        try:
            self._staff_alerts.alert(business, alert, texts)
        except Exception:
            logger.exception(
                "The payment page notice of business %s failed.", business.id
            )

        try:
            self._owner_emails.email_owners(business, alert, texts)
        except Exception:
            logger.exception(
                "The payment page notice of business %s failed.", business.id
            )
