"""Twilio's phone number API behind its circuit (REL-04)."""

from app.contracts.resilience import CircuitBreakerContract
from app.contracts.telephony_clients import TwilioPhoneNumbersClientContract
from app.schemas.constants.phone_numbers import PhoneNumberType
from app.schemas.dto.phone_numbers.provisioning import (
    AvailablePhoneNumber,
    PhoneNumberPurchase,
    PhoneNumberSearchQuery,
)
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.schemas.typings.telephony.constrained_strings import VoiceFallbackUrl
from app.schemas.typings.telephony.strings import ProviderPhoneNumberId
from app.utilities.resilience.integration_outages import call_integration


class GuardedTwilioPhoneNumbersClient(TwilioPhoneNumbersClientContract):
    """
    Twilio's phone numbers (the offer, its price, renting, the call
    fallback, returning) through their own circuit
    (`provider:twilio_numbers`, apart from Twilio's SMS): after repeated
    calls Twilio did not answer or answered with a 5xx, a call fails at
    once with ProviderCircuitOpenError, which the owner sees as "try again
    later" and the phone numbers' maintenance job retries; after the
    circuit's wait one trial call goes through (half-open). A refusal
    Twilio answered (a number that is gone, wrong credentials) never
    counts. Otherwise it behaves like the wrapped client.
    """

    def __init__(
        self,
        inner_client: TwilioPhoneNumbersClientContract,
        circuit_breaker: CircuitBreakerContract,
        circuit: CircuitName,
    ) -> None:
        self._inner: TwilioPhoneNumbersClientContract = inner_client
        self._circuit_breaker: CircuitBreakerContract = circuit_breaker
        self._circuit: CircuitName = circuit

    def list_available_numbers(
        self, query: PhoneNumberSearchQuery
    ) -> list[AvailablePhoneNumber]:
        return call_integration(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.list_available_numbers(query),
        )

    def get_monthly_price(
        self, country_code: CountryCode, number_type: PhoneNumberType
    ) -> CostMicroUsd | None:
        return call_integration(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.get_monthly_price(country_code, number_type),
        )

    def buy_number(self, purchase: PhoneNumberPurchase) -> ProviderPhoneNumberId:
        return call_integration(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.buy_number(purchase),
        )

    def release_number(self, provider_number_id: ProviderPhoneNumberId) -> None:
        call_integration(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.release_number(provider_number_id),
        )

    def set_voice_fallback(
        self, provider_number_id: ProviderPhoneNumberId, url: VoiceFallbackUrl
    ) -> None:
        call_integration(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.set_voice_fallback(provider_number_id, url),
        )
