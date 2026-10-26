"""APIs behind rented phone numbers: Twilio's numbers and ElevenLabs' imports."""

from typing import Protocol

from app.contracts.client_contract import ClientContract
from app.schemas.constants.phone_numbers import PhoneNumberType
from app.schemas.dto.phone_numbers.provisioning import (
    AvailablePhoneNumber,
    PhoneNumberPurchase,
    PhoneNumberSearchQuery,
    VoicePlatformImport,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.messaging.constrained_strings import TwilioAccountSid
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.telephony.constrained_strings import VoiceFallbackUrl
from app.schemas.typings.telephony.strings import (
    ProviderPhoneNumberId,
    VoicePlatformPhoneNumberId,
)


class TwilioPhoneNumbersClientContract(ClientContract, Protocol):
    """
    Twilio's phone numbers: what is on offer, its price, renting, the call
    fallback of a rented number, returning.
    """

    def list_available_numbers(
        self, query: PhoneNumberSearchQuery
    ) -> list[AvailablePhoneNumber]:
        """
        Numbers that take calls and need no address or bundle; an empty list
        where Twilio sells none of the kind. Raises ExternalServiceError.
        """
        raise NotImplementedError

    def get_monthly_price(
        self, country_code: CountryCode, number_type: PhoneNumberType
    ) -> CostMicroUsd | None:
        """
        Twilio's current monthly price of the kind in the country (None
        when it publishes none). Raises ExternalServiceError.
        """
        raise NotImplementedError

    def buy_number(self, purchase: PhoneNumberPurchase) -> ProviderPhoneNumberId:
        """
        Rent exactly this number. Raises PhoneNumberUnavailableError when it
        is gone, ExternalServiceError otherwise.
        """
        raise NotImplementedError

    def release_number(self, provider_number_id: ProviderPhoneNumberId) -> None:
        """Return a rented number; one Twilio no longer has is not an error."""
        raise NotImplementedError

    def set_voice_fallback(
        self, provider_number_id: ProviderPhoneNumberId, url: VoiceFallbackUrl
    ) -> None:
        """
        Where Twilio asks what to do with a call to the number when its voice
        webhook (the voice platform) fails or does not answer in time.
        Raises ExternalServiceError.
        """
        raise NotImplementedError


class ElevenLabsPhoneNumbersClientContract(ClientContract, Protocol):
    """ElevenLabs Agents' phone numbers (numbers imported from Twilio)."""

    def import_twilio_number(
        self,
        request: VoicePlatformImport,
        account_sid: TwilioAccountSid,
        auth_token: PlatformSecret,
    ) -> VoicePlatformPhoneNumberId:
        """
        Import a Twilio number (ElevenLabs points its voice webhook at
        itself). Raises ExternalServiceError.
        """
        raise NotImplementedError

    def assign_agent(
        self,
        phone_number_id: VoicePlatformPhoneNumberId,
        agent_id: VoiceAgentId | None,
    ) -> None:
        """
        Calls to the number reach this agent (None: none). Raises
        ExternalServiceError.
        """
        raise NotImplementedError

    def delete_number(self, phone_number_id: VoicePlatformPhoneNumberId) -> None:
        """Remove an imported number; a missing one is not an error."""
        raise NotImplementedError
