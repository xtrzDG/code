"""The summary of a finished call for staff (after the guard audit)."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.llm import LlmAdapterContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.call_follow_up_repositories import (
    CallSettingsRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    CallRepoContract,
    ContactRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import CallDocument, CallSummary
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.calls.call_summaries import (
    CallBookingNote,
    CallReportTextInput,
    CallSummaryOutcome,
    CallSummaryRequest,
    TextBackNote,
)
from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject
from app.use_cases.shared.operations_support import display_phone
from app.use_cases.voice.summaries.call_report_alerts import (
    call_report_alert,
    call_report_texts,
    staff_languages,
)
from app.use_cases.voice.summaries.call_summary_writer import (
    CallSummaryWriter,
    summary_languages,
)


class SummarizeCallUseCase(UseCaseContract[CallSummaryRequest, CallSummaryOutcome]):
    """
    After a call is stored and audited, staff get its summary (concept
    section 7): who called and when, for how long, what the caller wanted
    (a short text a cheap model writes in the owner's and the staff's
    languages, kept on the call for its card), how it ended with the
    booking it made, the values the phone assistant said that the business
    data does not back, and the link to the conversation with the
    recording and transcript. A caller who did not get through is reported
    with why, and whether they were written to.

    Idempotent per provider call id: the summary is written once (a call
    already summarized keeps its text) and every recipient gets the alert
    once, however often the post-call step runs. Nothing is sent while the
    owner keeps summaries off in Settings → Calls.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        call_repo: CallRepoContract,
        contact_repo: ContactRepoContract,
        booking_repo: BookingRepoContract,
        call_settings_repo: CallSettingsRepoContract,
        llm_adapter: LlmAdapterContract,
        staff_alerts: StaffAlertFacilitatorContract,
        report_text_transformer: TransformerContract[CallReportTextInput, MessageText],
        report_brief_transformer: TransformerContract[
            CallReportTextInput, StaffAlertBrief
        ],
        phone_number_parser: PhoneNumberParserContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._call_repo: CallRepoContract = call_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._call_settings_repo: CallSettingsRepoContract = call_settings_repo
        self._writer: CallSummaryWriter = CallSummaryWriter(llm_adapter, app_settings)
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._report_text_transformer: TransformerContract[
            CallReportTextInput, MessageText
        ] = report_text_transformer
        self._report_brief_transformer: TransformerContract[
            CallReportTextInput, StaffAlertBrief
        ] = report_brief_transformer
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CallSummaryRequest) -> CallSummaryOutcome:
        recorded: RecordedCall = input_data.call
        if (
            recorded.status is PostCallEventStatus.IGNORED
            or recorded.business_id is None
            or recorded.call_id is None
        ):
            return CallSummaryOutcome()

        business: BusinessDocument | None = self._business_repo.get(
            recorded.business_id
        )
        call: CallDocument | None = self._call_repo.get(
            recorded.business_id, recorded.call_id
        )
        if business is None or call is None or not self._is_enabled(business):
            return CallSummaryOutcome()

        is_generated: bool = False
        if call.summarized_at is None:
            call, is_generated = self._summarize(business, call, input_data)

        facts: CallReportTextInput = self._facts(business, call, input_data)
        notified = self._staff_alerts.alert(
            business,
            call_report_alert(
                business,
                StaffAlertSubject(f"call:{call.id}"),
                call.conversation_id,
                call.outcome,
                is_missed=input_data.missed_call is not None,
            ),
            call_report_texts(
                facts,
                list(call.summaries),
                self._report_text_transformer,
                self._report_brief_transformer,
            ),
        )
        return CallSummaryOutcome(is_generated=is_generated, notified_count=notified)

    def _is_enabled(self, business: BusinessDocument) -> bool:
        settings: CallSettingsDocument | None = (
            self._call_settings_repo.get_by_business(business.id)
        )
        return settings is None or settings.is_summary_enabled

    def _summarize(
        self,
        business: BusinessDocument,
        call: CallDocument,
        input_data: CallSummaryRequest,
    ) -> tuple[CallDocument, bool]:
        """Write the summary once; a call summarized meanwhile keeps its own."""

        summaries: list[CallSummary] = self._writer.write(
            business,
            call.outcome,
            input_data.transcript,
            summary_languages(business, staff_languages(business)),
        )
        now: Microseconds = self._wall_clock.now_unix()

        def store(current: CallDocument) -> CallDocument | None:
            if current.summarized_at is not None:
                return None

            current.summaries = summaries
            current.summarized_at = now
            current.updated_at = now
            return current

        stored: CallDocument | None = self._call_repo.update(
            business.id, call.id, store
        )
        if stored is not None:
            return stored, bool(summaries)

        return self._call_repo.get(business.id, call.id) or call, False

    def _facts(
        self,
        business: BusinessDocument,
        call: CallDocument,
        input_data: CallSummaryRequest,
    ) -> CallReportTextInput:
        recorded: RecordedCall = input_data.call
        missed: MissedCallDocument | None = input_data.missed_call
        contact: ContactDocument | None = (
            None
            if recorded.contact_id is None
            else self._contact_repo.get(business.id, recorded.contact_id)
        )
        booking: BookingDocument | None = (
            None
            if not recorded.booking_ids
            else self._booking_repo.get(business.id, recorded.booking_ids[-1])
        )
        return CallReportTextInput(
            business_name=business.name,
            language=business.owner_language,
            timezone=business.timezone,
            started_at=call.started_at,
            caller_phone=display_phone(
                self._phone_number_parser, call.from_phone_number
            ),
            caller_name=None if contact is None else contact.name,
            duration_seconds=call.duration_seconds,
            outcome=call.outcome,
            booking=(
                None
                if booking is None
                else CallBookingNote(
                    starts_at=booking.starts_at, party_size=booking.party_size
                )
            ),
            unverified_values=list(call.unverified_values),
            missed_reason=None if missed is None else missed.reason,
            text_back=(
                None
                if missed is None
                else TextBackNote(
                    status=missed.status,
                    channel=missed.channel,
                    skip_reason=missed.skip_reason,
                )
            ),
        )
