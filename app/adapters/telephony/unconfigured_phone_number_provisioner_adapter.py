"""Stand-in while this server rents no numbers by itself."""

from app.contracts.phone_numbers import PhoneNumberProvisionerAdapterContract
from app.schemas.dto.phone_numbers.provisioning import (
    PhoneNumberPurchase,
    PhoneNumberRelease,
    PhoneNumberSearchQuery,
    PhoneNumberSearchResult,
    ProvisionedPhoneNumber,
    VoicePlatformImport,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.telephony.strings import VoicePlatformPhoneNumberId


class UnconfiguredPhoneNumberProvisionerAdapter(PhoneNumberProvisionerAdapterContract):
    """
    Used while PHONE_NUMBER_PROVIDER, or a key the provider needs, is not
    set. The cabinet then offers the platform team's help instead of a
    search (`list_missing_settings` names what is missing); anything that
    would reach a carrier fails with ExternalServiceError, so a number
    rented before the settings were removed waits to be given back.
    """

    def __init__(self, missing_settings: list[EnvironmentVariableName]) -> None:
        self._missing_settings: list[EnvironmentVariableName] = list(missing_settings)

    def list_missing_settings(self) -> list[EnvironmentVariableName]:
        return list(self._missing_settings)

    def search_numbers(self, query: PhoneNumberSearchQuery) -> PhoneNumberSearchResult:
        del query
        raise self._not_configured()

    def buy_number(self, purchase: PhoneNumberPurchase) -> ProvisionedPhoneNumber:
        del purchase
        raise self._not_configured()

    def import_number(self, request: VoicePlatformImport) -> VoicePlatformPhoneNumberId:
        del request
        raise self._not_configured()

    def assign_agent(
        self,
        voice_platform_number_id: VoicePlatformPhoneNumberId,
        agent_id: VoiceAgentId | None,
    ) -> None:
        del voice_platform_number_id, agent_id
        raise self._not_configured()

    def release_number(self, release: PhoneNumberRelease) -> None:
        del release
        raise self._not_configured()

    def _not_configured(self) -> ExternalServiceError:
        return ExternalServiceError(
            "Phone numbers are not rented on this server: set "
            + ", ".join(str(name) for name in self._missing_settings)
            + "."
        )
