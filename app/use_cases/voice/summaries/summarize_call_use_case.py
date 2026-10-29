"""The summary of a finished call for staff (after the guard audit)."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
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
    ConversationRepoContract,
)
from app.contracts.repositories.customer_memory_repositories import (
    AssistantSettingsRepoContract,
    ConversationMemoryRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.call_summaries import CallSummary
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.dto.calls.call_summaries import (
    CallReportTextInput,
    CallSummaryDraft,
    CallSummaryOptions,
    CallSummaryOutcome,
    CallSummaryRequest,
)
from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject
from app.use_cases.voice.summaries.call_memory import CallMemory
from app.use_cases.voice.summaries.call_report_alerts import (
    call_report_alert,
    call_report_texts,
    staff_languages,
)
from app.use_cases.voice.summaries.call_report_facts import (
    CallReportSources,
    build_call_report_facts,
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
    owner keeps summaries off in Settings → Calls. The finished call is
    announced (`call.finished` for the business's webhooks) after its
    summary, or right away while summaries are off.

    The same model request writes the caller's memory (`CallMemory`): the
    call's conversation gets an English summary, so the assistant greets a
    returning caller in any channel as it greets a returning chatter
    (customer memory on, summaries to staff on or off). A caller who
    declined the recording is summarized from the transcript without
    identifiers.
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
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        conversation_repo: ConversationRepoContract,
        conversation_memory_repo: ConversationMemoryRepoContract,
        assistant_settings_repo: AssistantSettingsRepoContract,
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
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._memory: CallMemory = CallMemory(
            conversation_repo,
            conversation_memory_repo,
            contact_repo,
            assistant_settings_repo,
            wall_clock,
        )

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
        if business is None or call is None:
            return CallSummaryOutcome()

        conversation: ConversationDocument | None = self._memory.find_conversation(
            business, recorded
        )
        if not self._is_enabled(business):
            is_remembered: bool = conversation is not None and self._memory.remember(
                conversation,
                self._write(business, call, input_data, [], conversation).memory,
            )
            self._announce(call)
            return CallSummaryOutcome(is_remembered=is_remembered)

        is_generated: bool = False
        is_remembered = False
        if call.summarized_at is None:
            draft: CallSummaryDraft = self._write(
                business,
                call,
                input_data,
                summary_languages(business, staff_languages(business)),
                conversation,
            )
            call, is_generated = self._store(business, call, draft)
            is_remembered = conversation is not None and self._memory.remember(
                conversation, draft.memory
            )
        self._announce(call)

        facts: CallReportTextInput = build_call_report_facts(
            business,
            call,
            input_data,
            CallReportSources(
                self._contact_repo, self._booking_repo, self._phone_number_parser
            ),
        )
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
        return CallSummaryOutcome(
            is_generated=is_generated,
            notified_count=notified,
            is_remembered=is_remembered,
        )

    def _announce(self, call: CallDocument) -> None:
        """The finished call for the live views' observers (once per call)."""

        self._live_events.publish(
            call.business_id, LiveEventKind.CALL_FINISHED, (call.id,)
        )

    def _is_enabled(self, business: BusinessDocument) -> bool:
        settings: CallSettingsDocument | None = (
            self._call_settings_repo.get_by_business(business.id)
        )
        return settings is None or settings.is_summary_enabled

    def _write(
        self,
        business: BusinessDocument,
        call: CallDocument,
        input_data: CallSummaryRequest,
        languages: list[LanguageTag],
        conversation: ConversationDocument | None,
    ) -> CallSummaryDraft:
        """The staff's summaries and, for a call to remember, the memory."""

        return self._writer.write(
            business,
            call.outcome,
            input_data.transcript,
            languages,
            CallSummaryOptions(
                wants_memory=conversation is not None,
                is_recording_declined=input_data.call.is_recording_declined,
            ),
        )

    def _store(
        self,
        business: BusinessDocument,
        call: CallDocument,
        draft: CallSummaryDraft,
    ) -> tuple[CallDocument, bool]:
        """Store the summary once; a call summarized meanwhile keeps its own."""

        summaries: list[CallSummary] = draft.summaries
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
