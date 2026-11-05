"""
The deposit world: the assistant's send_payment_link, "Paid" in the
cabinet, the minute's sweep and the report over the deposit store.
"""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.gateways.worker.periodic.growth_jobs import SWEEP_DEPOSITS_JOB
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.deposits import DepositRequestDocument
from app.schemas.dto.deposits.deposit_report import DepositReport, DepositReportQuery
from app.schemas.dto.deposits.deposit_views import (
    DepositRequestView,
    MarkDepositPaidCommand,
)
from app.schemas.dto.deposits.payment_link_requests import (
    PaymentLinkReceipt,
    SendPaymentLinkCommand,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.deposits.constrained_integers import DepositReportDays
from app.schemas.typings.deposits.prefixed_id import DepositRequestId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.deposits.deposit_hold_release import DepositHoldRelease
from app.use_cases.deposits.deposit_issuing import DepositIssuing
from app.use_cases.deposits.deposit_notice_texts import DepositNoticeTexts
from app.use_cases.deposits.deposit_notices import DepositNotices
from app.use_cases.deposits.deposit_subjects import DepositSubjects
from app.use_cases.deposits.get_deposit_report_use_case import GetDepositReportUseCase
from app.use_cases.deposits.mark_deposit_paid_use_case import MarkDepositPaidUseCase
from app.use_cases.deposits.send_payment_link_use_case import SendPaymentLinkUseCase
from app.use_cases.deposits.sweep_deposits_use_case import SweepDepositsUseCase
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.deposits.deposit_store import DepositStore
from tests.foundation.access_support import ACCESS_SETTINGS
from tests.foundation.support_access_builders import build_authorize_business_access


class DepositWorld(DepositStore):
    """The restaurant takes deposits; its guests write in Telegram."""

    # The use cases -----------------------------------------------------

    def send_payment_link(self) -> SendPaymentLinkUseCase:
        return SendPaymentLinkUseCase(
            business_repo=self.business_repo,
            deposit_settings_repo=self.deposit_settings_repo,
            deposit_request_repo=self.deposit_request_repo,
            subjects=DepositSubjects(
                booking_repo=self.booking_repo, lead_repo=self.lead_repo
            ),
            issuing=DepositIssuing(
                request_repo=self.deposit_request_repo,
                booking_repo=self.booking_repo,
                lead_repo=self.lead_repo,
                lines=self.lines,
            ),
            lock_registry=self.lock_registry,
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
        )

    def mark_deposit_paid(self) -> MarkDepositPaidUseCase:
        return MarkDepositPaidUseCase(
            authorize_business_access=self.authorize(),
            deposit_request_repo=self.deposit_request_repo,
            deposit_settings_repo=self.deposit_settings_repo,
            booking_repo=self.booking_repo,
            lead_repo=self.lead_repo,
            lock_registry=self.lock_registry,
            audit_log_repo=self.audit_repo,
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
        )

    def sweep_deposits(self) -> SweepDepositsUseCase:
        return SweepDepositsUseCase(
            business_repo=self.business_repo,
            deposit_request_repo=self.deposit_request_repo,
            deposit_settings_repo=self.deposit_settings_repo,
            booking_repo=self.booking_repo,
            hold_release=DepositHoldRelease(
                request_repo=self.deposit_request_repo,
                booking_repo=self.booking_repo,
                lead_repo=self.lead_repo,
                lock_registry=self.lock_registry,
            ),
            notices=DepositNotices(
                routing=self.routing,
                sender=self.sender,
                contact_repo=self.contact_repo,
                conversation_repo=self.conversation_repo,
                message_repo=self.message_repo,
                suppression_list=self.suppression_list,
                live_events=self.live_events,
            ),
            notice_texts=DepositNoticeTexts(
                lines=self.lines, text_resolver=self.resolver
            ),
            settlement=self.settlement,
            growth=self.growth,
            calendar_sync=self.calendar_sync,
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
        )

    def deposit_report(self) -> GetDepositReportUseCase:
        return GetDepositReportUseCase(
            authorize_business_access=self.authorize(),
            deposit_settings_repo=self.deposit_settings_repo,
            deposit_request_repo=self.deposit_request_repo,
            booking_outcome_repo=self.booking_outcome_repo,
            wall_clock=self.clock.wall_clock,
        )

    def authorize(self) -> AuthorizeBusinessAccessUseCase:
        return build_authorize_business_access(
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_repo,
            wall_clock=self.clock.wall_clock,
            session_assurance=SessionAssuranceContext(),
            app_settings=ACCESS_SETTINGS,
        )

    # What the tests do -------------------------------------------------

    def ask_deposit(
        self,
        guest: ContactDocument,
        chat: ConversationDocument,
        booking_id: BookingId | None = None,
    ) -> PaymentLinkReceipt:
        """The assistant calls send_payment_link in the guest's chat."""

        return self.send_payment_link().run(
            SendPaymentLinkCommand(
                business_id=self.business.id,
                contact_id=guest.id,
                conversation_id=chat.id,
                source_channel=chat.channel,
                language=chat.language or self.business.default_language,
                booking_id=booking_id,
            )
        )

    def mark_paid(
        self, request_id: DepositRequestId, user_id: UserId | None = None
    ) -> DepositRequestView:
        return self.mark_deposit_paid().run(
            MarkDepositPaidCommand(
                user_id=user_id or self.owner_id,
                business_id=self.business.id,
                request_id=request_id,
            )
        )

    def sweep(self) -> JobReport:
        """One run of the minute's deposit sweep."""

        return self.sweep_deposits().run(
            JobTick(
                job_name=SWEEP_DEPOSITS_JOB,
                scheduled_at=self.clock.now_microseconds(),
            )
        )

    def report(self, days: int = 90) -> DepositReport:
        return self.deposit_report().run(
            DepositReportQuery(
                user_id=self.owner_id,
                business_id=self.business.id,
                days=DepositReportDays(days),
            )
        )

    def pass_minutes(self, minutes: int) -> None:
        self.now_at = self.now_at + timedelta(minutes=minutes)
        self.clock.move_to(self.now_at)

    def request(self, request_id: DepositRequestId) -> DepositRequestDocument:
        found = self.deposit_request_repo.get(self.business.id, request_id)
        assert found is not None
        return found

    def booking(self, booking_id: BookingId) -> BookingDocument:
        found = self.booking_repo.get(self.business.id, booking_id)
        assert found is not None
        return found

    def now(self) -> Microseconds:
        return self.clock.now_microseconds()
