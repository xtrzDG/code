"""The carrier behind rented phone numbers, chosen by the settings."""

from app.adapters.telephony.guarded_elevenlabs_phone_numbers_client import (
    GuardedElevenLabsPhoneNumbersClient,
)
from app.adapters.telephony.twilio_phone_number_provisioner_adapter import (
    TwilioPhoneNumberProvisionerAdapter,
)
from app.adapters.telephony.unconfigured_phone_number_provisioner_adapter import (
    UnconfiguredPhoneNumberProvisionerAdapter,
)
from app.clients.elevenlabs.elevenlabs_phone_numbers_client import (
    ElevenLabsPhoneNumbersClient,
)
from app.clients.twilio.twilio_phone_numbers_client import TwilioPhoneNumbersClient
from app.contracts.phone_numbers import PhoneNumberProvisionerAdapterContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.resilience import OutboundProvider
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.utilities.resilience.provider_circuits import provider_circuit


def build_phone_number_provisioner(
    settings: AppSettings,
    circuit_breaker: CircuitBreakerContract,
) -> PhoneNumberProvisionerAdapterContract:
    """
    Twilio with ElevenLabs when PHONE_NUMBER_PROVIDER=twilio and both have
    their keys (ElevenLabs behind its circuit, the call fallback at
    APP_BASE_URL); otherwise a stand-in that names what is missing (owners
    then ask the platform team for a number).
    """

    if settings.phone_numbers.provider is None:
        return UnconfiguredPhoneNumberProvisionerAdapter(
            [EnvironmentVariableName("PHONE_NUMBER_PROVIDER")]
        )

    account_sid = settings.twilio_account_sid
    auth_token = settings.twilio_auth_token
    api_key = settings.elevenlabs_api_key
    if account_sid is None or auth_token is None or api_key is None:
        return UnconfiguredPhoneNumberProvisionerAdapter(
            [
                EnvironmentVariableName(name)
                for name, value in (
                    ("TWILIO_ACCOUNT_SID", account_sid),
                    ("TWILIO_AUTH_TOKEN", auth_token),
                    ("ELEVENLABS_API_KEY", api_key),
                )
                if value is None
            ]
        )

    return TwilioPhoneNumberProvisionerAdapter(
        twilio_client=TwilioPhoneNumbersClient(account_sid, auth_token),
        # ElevenLabs' numbers behind the voice platform's circuit.
        elevenlabs_client=GuardedElevenLabsPhoneNumbersClient(
            ElevenLabsPhoneNumbersClient(api_key, settings.elevenlabs_api_base_url),
            circuit_breaker,
            provider_circuit(OutboundProvider.ELEVENLABS),
        ),
        account_sid=account_sid,
        auth_token=auth_token,
        public_base_url=settings.app_base_url,
    )
