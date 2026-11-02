from typed_time_provider import Microseconds, WallClock

from app.contracts.channels import VoiceWebhookAdapterContract
from app.contracts.localization_utilities import (
    LocalizedTextResolverContract,
    PhoneNumberParserContract,
)
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.call_follow_up_repositories import (
    CallSettingsRepoContract,
)
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import (
    ScheduleExceptionRepoContract,
)
from app.contracts.repositories.spend_guard_repositories import (
    UsageSpendRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.spend import SpendLevel
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.conversations import CallGreeting, CallGreetingRequest
from app.schemas.dto.spend_guard import SpendCheckRequest, SpendVerdict
from app.schemas.dto.voice_webhooks import (
    CallInitiationData,
    CallInitiationWebhookRequest,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.channels.strings import CallLocalTimeText, CallNextDaysText
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.use_cases.voice.call_admission import (
    find_call_transfer_number,
    refuse_blocked_caller,
    refuse_past_daily_minutes,
)
from app.utilities.calls.call_privacy_texts import CALL_PRIVACY_NOTICE_HINT
from app.utilities.channels.channel_phone_numbers import (
    parse_messaging_phone_number,
)
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.voice_service import find_voice_refusal
from app.utilities.channels.voice_webhook_auth import require_voice_webhook_access
from app.utilities.conversations.turn_context import (
    describe_local_now,
    describe_next_days,
)
from app.utilities.scheduling.opening_hours import business_day_ranges, is_open_at
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    microseconds_to_seconds,
    to_local_moment,
)


class StartVoiceCallUseCase(
    UseCaseContract[CallInitiationWebhookRequest, CallInitiationData]
):
    """
    Answer the voice platform's call-initiation webhook: the first phrase of
    the call (concept section 7: who answers, the recording notice, how to
    reach a human, where the privacy notice is) in the business's default
    language, built fresh for every call. Authenticated like the tool
    webhooks.

    A call is refused (ConflictError) while the phone assistant is off: the
    business is not live, its live version or its plan has no voice, or its
    phone number is disconnected; past its hard daily spend limit (the
    spend guard) or its daily call minutes, until its midnight; and from a
    number staff blocked (`call_admission`). A refused call goes to the
    missed-call flow. The agent learns whether the business is open now,
    the staff number a transfer may go to (only while open and allowed,
    `find_call_transfer_number`), the business-local date and time with
    the next days and the time zone; nothing about the caller, whose caller
    id proves nobody's identity.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        channel_repo: ChannelRepoContract,
        plan_registry: PlanRegistryContract,
        business_profile_repo: BusinessProfileRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        contact_repo: ContactRepoContract,
        call_settings_repo: CallSettingsRepoContract,
        usage_spend_repo: UsageSpendRepoContract,
        wall_clock: WallClock[Microseconds],
        voice_webhook_adapter: VoiceWebhookAdapterContract,
        phone_number_parser: PhoneNumberParserContract,
        build_call_greeting: UseCaseContract[CallGreetingRequest, CallGreeting],
        text_resolver: LocalizedTextResolverContract,
        app_settings: AppSettings,
        check_spend: UseCaseContract[SpendCheckRequest, SpendVerdict] | None = None,
    ) -> None:
        self._check_spend: UseCaseContract[SpendCheckRequest, SpendVerdict] | None = (
            check_spend
        )
        self._business_repo: BusinessRepoContract = business_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._channel_repo: ChannelRepoContract = channel_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )
        self._contact_repo: ContactRepoContract = contact_repo
        self._call_settings_repo: CallSettingsRepoContract = call_settings_repo
        self._usage_spend_repo: UsageSpendRepoContract = usage_spend_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._voice_webhook_adapter: VoiceWebhookAdapterContract = voice_webhook_adapter
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._build_call_greeting: UseCaseContract[
            CallGreetingRequest, CallGreeting
        ] = build_call_greeting
        self._text_resolver: LocalizedTextResolverContract = text_resolver
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: CallInitiationWebhookRequest) -> CallInitiationData:
        require_voice_webhook_access(
            self._app_settings.elevenlabs_webhook_secret,
            input_data.credentials,
            input_data.body,
        )
        business: BusinessDocument | None = self._business_repo.get(
            input_data.credentials.business_id
        )
        if business is None:
            raise NotFoundError("The business of this voice agent was not found.")

        published_version: AssistantVersionDocument | None = (
            None
            if business.published_assistant_version_id is None
            else self._assistant_version_repo.get(
                business.id, business.published_assistant_version_id
            )
        )
        refusal: str | None = find_voice_refusal(
            business,
            published_version,
            self._plan_registry.get(business.plan_key),
            find_business_channel(self._channel_repo, business.id, ChannelKind.PHONE),
        )
        if refusal is not None:
            raise ConflictError(refusal)

        self._refuse_past_hard_limit(business)
        caller_number: RawPhoneNumberInput | None = (
            self._voice_webhook_adapter.parse_call_initiation(input_data.body)
        )
        caller_phone_number: E164PhoneNumber | None = (
            None
            if caller_number is None
            else parse_messaging_phone_number(
                self._phone_number_parser,
                str(caller_number),
                business.country_code,
            )
        )
        refuse_blocked_caller(self._contact_repo, business, caller_phone_number)
        now: Microseconds = self._wall_clock.now_unix()
        refuse_past_daily_minutes(self._usage_spend_repo, business, now)
        greeting: CallGreeting = self._build_call_greeting.run(
            CallGreetingRequest(business_id=business.id)
        )
        now_seconds: int = microseconds_to_seconds(int(now))
        local_now = to_local_moment(now_seconds, load_time_zone(business.timezone))
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        is_open_now: bool = self._is_open_now(business, profile, now_seconds)
        return CallInitiationData(
            business_id=business.id,
            first_message=MessageText(
                f"{greeting.text} "
                + self._text_resolver.resolve(
                    CALL_PRIVACY_NOTICE_HINT, greeting.language
                )
            ),
            language=greeting.language,
            caller_phone_number=caller_phone_number,
            is_open_now=is_open_now,
            transfer_phone_number=find_call_transfer_number(
                business,
                profile,
                self._call_settings_repo.get_by_business(business.id),
                is_open_now,
            ),
            local_now_text=CallLocalTimeText(describe_local_now(local_now)),
            next_days_text=CallNextDaysText(describe_next_days(local_now)),
            timezone=business.timezone,
        )

    def _refuse_past_hard_limit(self, business: BusinessDocument) -> None:
        if self._check_spend is None:
            return

        verdict: SpendVerdict = self._check_spend.run(
            SpendCheckRequest(business=business, now=self._wall_clock.now_unix())
        )
        if verdict.level is SpendLevel.HARD_LIMIT:
            raise ConflictError(
                "The business reached its daily spend limit: the voice assistant "
                "takes no calls until its midnight."
            )

    def _is_open_now(
        self,
        business: BusinessDocument,
        profile: BusinessProfileDocument | None,
        now_seconds: int,
    ) -> bool:
        """Inside the business's opening hours (special days included)."""

        if profile is None or profile.hours == []:
            return False

        return is_open_at(
            now_seconds,
            load_time_zone(business.timezone),
            business_day_ranges(
                profile.hours,
                self._schedule_exception_repo.list_by_business(business.id),
            ),
        )
