from typed_time_provider import Microseconds, WallClock

from app.contracts.channels import VoiceWebhookAdapterContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories import (
    AssistantVersionRepoContract,
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ChannelRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.conversations import CallGreeting, CallGreetingRequest
from app.schemas.dto.voice_webhooks import (
    CallInitiationData,
    CallInitiationWebhookRequest,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.utilities.channels.channel_phone_numbers import (
    parse_messaging_phone_number,
)
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.voice_service import find_voice_refusal
from app.utilities.channels.voice_webhook_auth import require_voice_webhook_access
from app.utilities.scheduling.opening_hours import business_day_ranges, is_open_at
from app.utilities.scheduling.zoned_time import load_time_zone, microseconds_to_seconds


class StartVoiceCallUseCase(
    UseCaseContract[CallInitiationWebhookRequest, CallInitiationData]
):
    """
    Answer the voice platform's call-initiation webhook: the first phrase of
    the call (concept section 7: who answers, that the call is recorded, how
    to reach a human) in the business's default language, built fresh for
    every call. Authenticated like the tool webhooks.

    A call is refused (ConflictError) while the phone assistant is off: the
    business is not live, its live version or its plan has no voice, or its
    phone number is disconnected. The agent also learns whether the business
    is open now: only then may it put a caller through to staff.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        channel_repo: ChannelRepoContract,
        plan_registry: PlanRegistryContract,
        business_profile_repo: BusinessProfileRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        wall_clock: WallClock[Microseconds],
        voice_webhook_adapter: VoiceWebhookAdapterContract,
        phone_number_parser: PhoneNumberParserContract,
        build_call_greeting: UseCaseContract[CallGreetingRequest, CallGreeting],
        app_settings: AppSettings,
    ) -> None:
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
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._voice_webhook_adapter: VoiceWebhookAdapterContract = voice_webhook_adapter
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._build_call_greeting: UseCaseContract[
            CallGreetingRequest, CallGreeting
        ] = build_call_greeting
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

        caller_number: RawPhoneNumberInput | None = (
            self._voice_webhook_adapter.parse_call_initiation(input_data.body)
        )
        greeting: CallGreeting = self._build_call_greeting.run(
            CallGreetingRequest(business_id=business.id)
        )
        return CallInitiationData(
            business_id=business.id,
            first_message=greeting.text,
            language=greeting.language,
            caller_phone_number=(
                None
                if caller_number is None
                else parse_messaging_phone_number(
                    self._phone_number_parser,
                    str(caller_number),
                    business.country_code,
                )
            ),
            is_open_now=self._is_open_now(business),
        )

    def _is_open_now(self, business: BusinessDocument) -> bool:
        """Inside the business's opening hours (special days included)."""

        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        if profile is None or profile.hours == []:
            return False

        return is_open_at(
            microseconds_to_seconds(int(self._wall_clock.now_unix())),
            load_time_zone(business.timezone),
            business_day_ranges(
                profile.hours,
                self._schedule_exception_repo.list_by_business(business.id),
            ),
        )
