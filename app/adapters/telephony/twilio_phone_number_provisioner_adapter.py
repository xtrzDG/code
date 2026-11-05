"""Numbers rented from Twilio and answered by ElevenLabs agents."""

from app.contracts.phone_numbers import PhoneNumberProvisionerAdapterContract
from app.contracts.telephony_clients import (
    ElevenLabsPhoneNumbersClientContract,
    TwilioPhoneNumbersClientContract,
)
from app.schemas.constants.phone_numbers import PhoneNumberProvider, PhoneNumberType
from app.schemas.dto.phone_numbers.provisioning import (
    AvailablePhoneNumber,
    PhoneNumberPurchase,
    PhoneNumberRelease,
    PhoneNumberSearchQuery,
    PhoneNumberSearchResult,
    ProvisionedPhoneNumber,
    VoicePlatformImport,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.messaging.constrained_strings import TwilioAccountSid
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.telephony.constrained_strings import VoiceFallbackUrl
from app.schemas.typings.telephony.strings import (
    ProviderPhoneNumberId,
    VoicePlatformPhoneNumberId,
)
from app.utilities.calls.twilio_voice_webhooks import build_voice_fallback_path
from app.utilities.channels.channel_endpoints import join_public_url


class TwilioPhoneNumberProvisionerAdapter(PhoneNumberProvisionerAdapterContract):
    """
    Twilio sells the numbers, ElevenLabs answers them: a search reads
    Twilio's price list first and offers numbers only of a kind it prices;
    a rented number is imported into ElevenLabs as a Twilio number (the
    account's SID and token let ElevenLabs set the number's voice webhook
    and check Twilio's signatures) and assigned to the business's agent.
    Its VoiceFallbackUrl points at the business's call fallback on this
    server (APP_BASE_URL), so a call the voice platform cannot take is put
    through to the staff mobile.
    Giving a number back removes it from ElevenLabs first, so no call
    reaches a number Twilio no longer routes to the agent, then returns it
    to Twilio.
    """

    def __init__(
        self,
        twilio_client: TwilioPhoneNumbersClientContract,
        elevenlabs_client: ElevenLabsPhoneNumbersClientContract,
        account_sid: TwilioAccountSid,
        auth_token: PlatformSecret,
        public_base_url: PublicBaseUrl | None = None,
    ) -> None:
        self._twilio_client: TwilioPhoneNumbersClientContract = twilio_client
        self._elevenlabs_client: ElevenLabsPhoneNumbersClientContract = (
            elevenlabs_client
        )
        self._account_sid: TwilioAccountSid = account_sid
        self._auth_token: PlatformSecret = auth_token
        self._public_base_url: PublicBaseUrl | None = public_base_url

    def list_missing_settings(self) -> list[EnvironmentVariableName]:
        return []

    def search_numbers(self, query: PhoneNumberSearchQuery) -> PhoneNumberSearchResult:
        monthly_cost: CostMicroUsd | None = self._twilio_client.get_monthly_price(
            query.country_code, query.number_type
        )
        if monthly_cost is None:
            return PhoneNumberSearchResult()

        numbers: list[AvailablePhoneNumber] = (
            self._twilio_client.list_available_numbers(query)
        )
        return PhoneNumberSearchResult(
            numbers=numbers[: int(query.limit)],
            monthly_cost_micro_usd=monthly_cost,
        )

    def quote_monthly_cost(
        self, country_code: CountryCode, number_type: PhoneNumberType
    ) -> CostMicroUsd | None:
        return self._twilio_client.get_monthly_price(country_code, number_type)

    def buy_number(self, purchase: PhoneNumberPurchase) -> ProvisionedPhoneNumber:
        provider_number_id: ProviderPhoneNumberId = self._twilio_client.buy_number(
            purchase
        )
        return ProvisionedPhoneNumber(
            provider=PhoneNumberProvider.TWILIO,
            provider_number_id=provider_number_id,
            phone_number=purchase.phone_number,
        )

    def import_number(self, request: VoicePlatformImport) -> VoicePlatformPhoneNumberId:
        return self._elevenlabs_client.import_twilio_number(
            request, self._account_sid, self._auth_token
        )

    def assign_agent(
        self,
        voice_platform_number_id: VoicePlatformPhoneNumberId,
        agent_id: VoiceAgentId | None,
    ) -> None:
        self._elevenlabs_client.assign_agent(voice_platform_number_id, agent_id)

    def voice_fallback_url_of(self, business_id: BusinessId) -> VoiceFallbackUrl | None:
        if self._public_base_url is None:
            return None

        return VoiceFallbackUrl(
            join_public_url(
                str(self._public_base_url), build_voice_fallback_path(business_id)
            )
        )

    def route_voice_fallback(
        self, provider_number_id: ProviderPhoneNumberId, url: VoiceFallbackUrl
    ) -> None:
        self._twilio_client.set_voice_fallback(provider_number_id, url)

    def release_number(self, release: PhoneNumberRelease) -> None:
        if release.voice_platform_number_id is not None:
            self._elevenlabs_client.delete_number(release.voice_platform_number_id)

        self._twilio_client.release_number(release.provider_number_id)
