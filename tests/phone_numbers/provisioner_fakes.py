"""Fakes of the carrier and the voice platform behind rented numbers."""

from dataclasses import dataclass, field

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
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.phone_number_errors import PhoneNumberUnavailableError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.schemas.typings.messaging.constrained_strings import TwilioAccountSid
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.telephony.constrained_strings import VoiceFallbackUrl
from app.schemas.typings.telephony.strings import (
    PhoneNumberLocality,
    PhoneNumberRegion,
    ProviderPhoneNumberId,
    VoicePlatformPhoneNumberId,
)

AUSTIN_NUMBERS: tuple[str, ...] = ("+15125550142", "+15125550187", "+15125550123")
US_LOCAL_COST = CostMicroUsd(1_150_000)


def austin_numbers() -> list[AvailablePhoneNumber]:
    return [
        AvailablePhoneNumber(
            phone_number=E164PhoneNumber(number),
            locality=PhoneNumberLocality("Austin"),
            region=PhoneNumberRegion("TX"),
        )
        for number in AUSTIN_NUMBERS
    ]


@dataclass
class FakePhoneNumberProvisioner(PhoneNumberProvisionerAdapterContract):
    """
    A carrier with Austin numbers at $1.15 a month and a voice platform that
    keeps imports and assignments in memory; every call is recorded and any
    step can be made to fail.
    """

    missing_settings: list[EnvironmentVariableName] = field(
        default_factory=list[EnvironmentVariableName]
    )
    offers: dict[tuple[str, PhoneNumberType], list[AvailablePhoneNumber]] = field(
        default_factory=lambda: {("US", PhoneNumberType.LOCAL): austin_numbers()}
    )
    costs: dict[tuple[str, PhoneNumberType], CostMicroUsd] = field(
        default_factory=lambda: {("US", PhoneNumberType.LOCAL): US_LOCAL_COST}
    )
    searches: list[PhoneNumberSearchQuery] = field(
        default_factory=list[PhoneNumberSearchQuery]
    )
    bought: list[ProvisionedPhoneNumber] = field(
        default_factory=list[ProvisionedPhoneNumber]
    )
    imports: list[VoicePlatformImport] = field(
        default_factory=list[VoicePlatformImport]
    )
    assignments: dict[str, VoiceAgentId | None] = field(
        default_factory=dict[str, VoiceAgentId | None]
    )
    releases: list[PhoneNumberRelease] = field(default_factory=list[PhoneNumberRelease])
    taken_numbers: set[str] = field(default_factory=set[str])
    is_import_failing: bool = False
    is_assign_failing: bool = False
    is_release_failing: bool = False
    # The call fallback: none until a test gives the platform an address.
    voice_fallback_base: str | None = None
    fallbacks: dict[str, VoiceFallbackUrl] = field(
        default_factory=dict[str, VoiceFallbackUrl]
    )
    is_fallback_failing: bool = False

    def list_missing_settings(self) -> list[EnvironmentVariableName]:
        return list(self.missing_settings)

    def search_numbers(self, query: PhoneNumberSearchQuery) -> PhoneNumberSearchResult:
        self.searches.append(query)
        key = (str(query.country_code), query.number_type)
        cost: CostMicroUsd | None = self.costs.get(key)
        if cost is None:
            return PhoneNumberSearchResult()

        numbers = [
            number
            for number in self.offers.get(key, [])
            if query.city is None or str(number.locality) == str(query.city)
        ]
        return PhoneNumberSearchResult(
            numbers=numbers[: int(query.limit)], monthly_cost_micro_usd=cost
        )

    def quote_monthly_cost(
        self, country_code: CountryCode, number_type: PhoneNumberType
    ) -> CostMicroUsd | None:
        return self.costs.get((str(country_code), number_type))

    def buy_number(self, purchase: PhoneNumberPurchase) -> ProvisionedPhoneNumber:
        if str(purchase.phone_number) in self.taken_numbers:
            raise PhoneNumberUnavailableError("This number is no longer available.")

        self.taken_numbers.add(str(purchase.phone_number))
        provisioned = ProvisionedPhoneNumber(
            provider=PhoneNumberProvider.TWILIO,
            provider_number_id=ProviderPhoneNumberId(f"PN{len(self.bought) + 1:032d}"),
            phone_number=purchase.phone_number,
        )
        self.bought.append(provisioned)
        return provisioned

    def import_number(self, request: VoicePlatformImport) -> VoicePlatformPhoneNumberId:
        if self.is_import_failing:
            raise ExternalServiceError(
                "ElevenLabs phone-numbers request returned HTTP 503."
            )

        self.imports.append(request)
        number_id = VoicePlatformPhoneNumberId(f"phnum_{len(self.imports):04d}")
        self.assignments[str(number_id)] = request.agent_id
        return number_id

    def assign_agent(
        self,
        voice_platform_number_id: VoicePlatformPhoneNumberId,
        agent_id: VoiceAgentId | None,
    ) -> None:
        if self.is_assign_failing:
            raise ExternalServiceError(
                "ElevenLabs phone-numbers request returned HTTP 503."
            )

        self.assignments[str(voice_platform_number_id)] = agent_id

    def voice_fallback_url_of(self, business_id: BusinessId) -> VoiceFallbackUrl | None:
        if self.voice_fallback_base is None:
            return None

        return VoiceFallbackUrl(
            f"{self.voice_fallback_base}/v1/telephony/twilio/voice-fallback/"
            f"{business_id}"
        )

    def route_voice_fallback(
        self, provider_number_id: ProviderPhoneNumberId, url: VoiceFallbackUrl
    ) -> None:
        if self.is_fallback_failing:
            raise ExternalServiceError(
                "Twilio phone numbers request returned HTTP 503."
            )

        self.fallbacks[str(provider_number_id)] = url

    def release_number(self, release: PhoneNumberRelease) -> None:
        if self.is_release_failing:
            raise ExternalServiceError(
                "Twilio phone numbers request returned HTTP 503."
            )

        self.releases.append(release)


@dataclass
class FakeTwilioNumbersClient(TwilioPhoneNumbersClientContract):
    numbers: list[AvailablePhoneNumber] = field(default_factory=austin_numbers)
    price: CostMicroUsd | None = US_LOCAL_COST
    calls: list[str] = field(default_factory=list[str])

    def list_available_numbers(
        self, query: PhoneNumberSearchQuery
    ) -> list[AvailablePhoneNumber]:
        self.calls.append(f"search {query.country_code} {query.number_type.value}")
        return list(self.numbers)

    def get_monthly_price(
        self, country_code: CountryCode, number_type: PhoneNumberType
    ) -> CostMicroUsd | None:
        self.calls.append(f"price {country_code} {number_type.value}")
        return self.price

    def buy_number(self, purchase: PhoneNumberPurchase) -> ProviderPhoneNumberId:
        self.calls.append(f"buy {purchase.phone_number}")
        return ProviderPhoneNumberId("PN" + "0" * 30 + "42")

    def release_number(self, provider_number_id: ProviderPhoneNumberId) -> None:
        self.calls.append(f"release {provider_number_id}")

    def set_voice_fallback(
        self, provider_number_id: ProviderPhoneNumberId, url: VoiceFallbackUrl
    ) -> None:
        self.calls.append(f"fallback {provider_number_id} {url}")


@dataclass
class FakeElevenLabsNumbersClient(ElevenLabsPhoneNumbersClientContract):
    calls: list[str] = field(default_factory=list[str])

    def import_twilio_number(
        self,
        request: VoicePlatformImport,
        account_sid: TwilioAccountSid,
        auth_token: PlatformSecret,
    ) -> VoicePlatformPhoneNumberId:
        self.calls.append(
            f"import {request.phone_number} {account_sid} {request.agent_id}"
        )
        del auth_token
        return VoicePlatformPhoneNumberId("phnum_0042")

    def assign_agent(
        self,
        phone_number_id: VoicePlatformPhoneNumberId,
        agent_id: VoiceAgentId | None,
    ) -> None:
        self.calls.append(f"assign {phone_number_id} {agent_id}")

    def delete_number(self, phone_number_id: VoicePlatformPhoneNumberId) -> None:
        self.calls.append(f"delete {phone_number_id}")
