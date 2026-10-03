"""A caller who did not get through: stored once, and texted back when allowed."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.messaging_clients import SmsMessagingClientContract
from app.contracts.registries import (
    CountryRegistryContract,
    RequestRateLimitRegistryContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.call_follow_up_repositories import (
    CallSettingsRepoContract,
    MissedCallRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.calls import (
    TextBackChannel,
    TextBackSkipReason,
    TextBackStatus,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.calls.missed_calls import MissedCallReport, RegisteredMissedCall
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.voice.missed_calls.missed_call_business import (
    find_missed_call_business,
    read_caller_number,
)
from app.use_cases.voice.missed_calls.text_back_conversation import (
    find_caller_contact,
)
from app.use_cases.voice.missed_calls.text_back_rules import (
    DAY_WINDOW,
    choose_text_back_channel,
    choose_text_back_language,
    is_in_conversation,
    is_too_late,
    refusal_reason,
    text_back_counters,
)
from app.utilities.calls.call_follow_up_keys import (
    call_settings_id_of,
    missed_call_id_of,
)
from app.utilities.calls.text_back_jobs import (
    SEND_TEXT_BACK_JOB,
    encode_text_back_payload,
)
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.opt_out import is_opted_out


class RegisterMissedCallUseCase(
    UseCaseContract[MissedCallReport, RegisteredMissedCall | None]
):
    """
    Store a caller who did not get through (no answer, busy, hung up
    before the assistant, a failed start, a transfer nobody picked up) and
    decide the text-back: a message on WhatsApp (the owner's approved
    template from the business's number), else by SMS, in the caller's
    language, queued at once so it arrives within a minute or two.

    Not texted (SKIPPED, with the reason): text-backs off, a hidden
    number, an assistant that is not live, a report hours late, no
    channel, a customer who opted out (STOP) or already writes with the
    business in a messenger, and a caller texted in the last day (one per
    caller per day, at most 200 per business per day, and within the
    customer's shared daily cap of unrequested messages, counted for every
    API instance together). A report of the same call again changes nothing; None when
    no business has the line.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        missed_call_repo: MissedCallRepoContract,
        call_settings_repo: CallSettingsRepoContract,
        country_registry: CountryRegistryContract,
        rate_limits: RequestRateLimitRegistryContract,
        job_queue: JobQueueFacilitatorContract,
        phone_number_parser: PhoneNumberParserContract,
        sms_client: SmsMessagingClientContract | None,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._missed_call_repo: MissedCallRepoContract = missed_call_repo
        self._call_settings_repo: CallSettingsRepoContract = call_settings_repo
        self._country_registry: CountryRegistryContract = country_registry
        self._rate_limits: RequestRateLimitRegistryContract = rate_limits
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._sms_client: SmsMessagingClientContract | None = sms_client
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: MissedCallReport) -> RegisteredMissedCall | None:
        business: BusinessDocument | None = find_missed_call_business(
            self._business_repo,
            self._channel_repo,
            self._phone_number_parser,
            input_data,
        )
        if business is None:
            return None

        missed_call_id = missed_call_id_of(
            business.id, input_data.source, input_data.provider_call_id
        )
        stored: MissedCallDocument | None = self._missed_call_repo.get(
            business.id, missed_call_id
        )
        if stored is not None:
            return RegisteredMissedCall(missed_call=stored, is_new=False)

        now: Microseconds = self._wall_clock.now_unix()
        caller: E164PhoneNumber | None = read_caller_number(
            self._phone_number_parser, business, input_data
        )
        missed_call = MissedCallDocument(
            id=missed_call_id,
            business_id=business.id,
            source=input_data.source,
            provider_call_id=input_data.provider_call_id,
            reason=input_data.reason,
            caller_phone_number=caller,
            called_at=input_data.called_at,
            language=choose_text_back_language(
                business,
                input_data.language,
                caller,
                self._phone_number_parser,
                self._country_registry,
            ),
            call_id=input_data.call_id,
            status=TextBackStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )
        decision: TextBackChannel | TextBackSkipReason = self._decide(
            business, caller, input_data, now
        )
        if isinstance(decision, TextBackSkipReason):
            missed_call.status = TextBackStatus.SKIPPED
            missed_call.skip_reason = decision
        else:
            missed_call.channel = decision

        if not self._missed_call_repo.insert_if_new(missed_call):
            current: MissedCallDocument | None = self._missed_call_repo.get(
                business.id, missed_call_id
            )
            return RegisteredMissedCall(
                missed_call=current or missed_call, is_new=False
            )

        if missed_call.status is TextBackStatus.QUEUED:
            self._job_queue.enqueue(
                SEND_TEXT_BACK_JOB,
                encode_text_back_payload(missed_call.id),
                business.id,
                lane=JobLane.OUTBOUND,
            )

        return RegisteredMissedCall(missed_call=missed_call, is_new=True)

    def _decide(
        self,
        business: BusinessDocument,
        caller: E164PhoneNumber | None,
        report: MissedCallReport,
        now: Microseconds,
    ) -> TextBackChannel | TextBackSkipReason:
        """The channel of the text-back, or why there is none (in this order)."""

        settings: CallSettingsDocument = self._call_settings_repo.get_by_business(
            business.id
        ) or CallSettingsDocument(
            id=call_settings_id_of(business.id),
            business_id=business.id,
            created_at=now,
            updated_at=now,
        )
        if not settings.is_text_back_enabled:
            return TextBackSkipReason.TURNED_OFF

        if caller is None:
            return TextBackSkipReason.NO_CALLER_NUMBER

        if business.status is not BusinessStatus.LIVE:
            return TextBackSkipReason.NOT_LIVE

        if is_too_late(report.called_at, now):
            return TextBackSkipReason.TOO_LATE

        channel: TextBackChannel | None = choose_text_back_channel(
            settings,
            find_business_channel(
                self._channel_repo, business.id, ChannelKind.WHATSAPP
            ),
            self._sms_client is not None,
        )
        if channel is None:
            return TextBackSkipReason.NO_CHANNEL

        contact: ContactDocument | None = find_caller_contact(
            self._contact_repo, business, caller
        )
        if is_opted_out(contact):
            return TextBackSkipReason.OPTED_OUT

        if is_in_conversation(self._conversation_repo, business, contact, now):
            return TextBackSkipReason.IN_CONVERSATION

        refused: RateLimitKey | None = self._rate_limits.try_acquire_all(
            text_back_counters(business, caller, contact), DAY_WINDOW, now
        )
        if refused is not None:
            return refusal_reason(business, caller, refused)

        return channel
