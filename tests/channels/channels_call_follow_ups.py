"""
The channels testbed's call follow-ups: the conversation of a call, the
summary to staff (a scripted model), callers who did not get through and
their text-backs (WhatsApp over the recording Meta transport, a recording
SMS client).
"""

import threading

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.voice.zadarma_pbx_webhook_adapter import ZadarmaPbxWebhookAdapter
from app.contracts.messaging_clients import SmsMessagingClientContract
from app.orchestrators.channels.post_call_follow_ups import PostCallFollowUps
from app.orchestrators.voice.missed_call_orchestrator import MissedCallOrchestrator
from app.registries.localization.country_registry import CountryRegistry
from app.repositories.call_follow_up_repositories import (
    CallSettingsRepository,
    MissedCallRepository,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import DataRegion
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.strings import SmsMessageText
from app.transformers.notifications.call_report_brief_transformer import (
    CallReportBriefTransformer,
)
from app.transformers.notifications.call_report_text_transformer import (
    CallReportTextTransformer,
)
from app.use_cases.voice.finished_call.open_call_conversation_use_case import (
    OpenCallConversationUseCase,
)
from app.use_cases.voice.missed_calls.find_missed_voice_call_use_case import (
    FindMissedVoiceCallUseCase,
)
from app.use_cases.voice.missed_calls.notify_missed_call_use_case import (
    NotifyMissedCallUseCase,
)
from app.use_cases.voice.missed_calls.read_failed_call_start_use_case import (
    ReadFailedCallStartUseCase,
)
from app.use_cases.voice.missed_calls.read_pbx_missed_call_use_case import (
    ReadPbxMissedCallUseCase,
)
from app.use_cases.voice.missed_calls.register_missed_call_use_case import (
    RegisterMissedCallUseCase,
)
from app.use_cases.voice.missed_calls.send_text_back_use_case import (
    SendTextBackUseCase,
)
from app.use_cases.voice.recordings.schedule_recording_archive_use_case import (
    ScheduleRecordingArchiveUseCase,
)
from app.use_cases.voice.summaries.summarize_call_use_case import (
    SummarizeCallUseCase,
)
from tests.channels.channels_inbox import ChannelsInbox
from tests.notifications.staff_alert_fakes import build_staff_alerts


class RecordingSmsClient(SmsMessagingClientContract):
    """Records SMS; `failure` makes the next sends raise it."""

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self.sent: list[tuple[E164PhoneNumber, SmsMessageText]] = []
        self.failure: ApplicationError | None = None

    def send_sms(self, recipient: E164PhoneNumber, text: SmsMessageText) -> None:
        if self.failure is not None:
            raise self.failure

        with self._lock:
            self.sent.append((recipient, text))


class ChannelsCallFollowUps(ChannelsInbox):
    """What follows a call: summaries, missed calls and text-backs."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        super().__init__(settings)
        self.missed_call_collection = InMemoryDocumentCollectionAdapter(
            MissedCallDocument
        )
        self.missed_call_repo = MissedCallRepository(self.missed_call_collection)
        self.call_settings_repo = CallSettingsRepository(
            InMemoryDocumentCollectionAdapter(CallSettingsDocument)
        )
        # The summaries the scripted model writes, in order; none left: the
        # provider fails.
        self.summary_answers: list[str] = []
        self.summary_requests: list[LlmRequest] = []
        self.summary_llm = ScriptedLlmAdapter(self._answer_summary)
        self.sms_client = RecordingSmsClient()
        self.country_registry = CountryRegistry(
            self.language_registry, self.wall_clock, DataRegion.EU, []
        )
        self.call_staff_alerts = build_staff_alerts(
            self.staff_notifier, self.text_resolver, self.wall_clock
        )
        self.report_text = CallReportTextTransformer(self.text_resolver)
        self.report_brief = CallReportBriefTransformer(self.text_resolver)
        self.open_call_conversation = OpenCallConversationUseCase(
            self.business_repo,
            self.call_repo,
            self.contact_repo,
            self.conversation_repo,
            self.live_events,
            self.wall_clock,
        )
        self.summarize_call = SummarizeCallUseCase(
            self.business_repo,
            self.call_repo,
            self.contact_repo,
            self.booking_repo,
            self.call_settings_repo,
            self.summary_llm,
            self.call_staff_alerts,
            self.report_text,
            self.report_brief,
            self.phone_number_parser,
            self.settings,
            self.wall_clock,
        )
        self.register_missed_call = RegisterMissedCallUseCase(
            self.business_repo,
            self.channel_repo,
            self.contact_repo,
            self.conversation_repo,
            self.missed_call_repo,
            self.call_settings_repo,
            self.country_registry,
            self.rate_limits,
            self.job_queue,
            self.phone_number_parser,
            self.sms_client,
            self.wall_clock,
        )
        self.missed_calls = MissedCallOrchestrator(
            self.register_missed_call,
            NotifyMissedCallUseCase(
                self.business_repo,
                self.call_settings_repo,
                self.call_staff_alerts,
                self.report_text,
                self.report_brief,
                self.phone_number_parser,
            ),
        )
        self.send_text_back = SendTextBackUseCase(
            self.missed_call_repo,
            self.business_repo,
            self.call_settings_repo,
            self.channel_repo,
            self.contact_repo,
            self.conversation_repo,
            self.message_repo,
            self.channel_message_sender,
            self.sms_client,
            self.text_resolver,
            self.live_events,
            self.wall_clock,
        )
        self.read_failed_call_start = ReadFailedCallStartUseCase(
            self.voice_webhook_adapter, self.wall_clock
        )
        self.read_pbx_missed_call = ReadPbxMissedCallUseCase(
            ZadarmaPbxWebhookAdapter(self.settings), self.wall_clock
        )

    def post_call_follow_ups(self) -> PostCallFollowUps:
        """The worker's steps after a call is stored (no recording archive)."""

        return PostCallFollowUps(
            open_call_conversation=self.open_call_conversation,
            audit_call_replies=self.audit_call_replies,
            find_missed_voice_call=FindMissedVoiceCallUseCase(),
            register_missed_call=self.register_missed_call,
            summarize_call=self.summarize_call,
            send_call_confirmation=self.send_call_confirmation,
            send_call_links=self.send_call_links,
            schedule_recording_archive=ScheduleRecordingArchiveUseCase(
                self.call_repo, self.job_queue, is_archive_enabled=False
            ),
        )

    def _answer_summary(self, request: LlmRequest) -> ScriptedLlmTurn:
        self.summary_requests.append(request)
        if not self.summary_answers:
            raise ExternalServiceError("The summary model is unavailable.")

        return ScriptedLlmTurn(text=MessageText(self.summary_answers.pop(0)))
