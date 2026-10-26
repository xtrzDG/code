from app.contracts.resilience import CircuitBreakerContract
from app.contracts.telephony_clients import ElevenLabsPhoneNumbersClientContract
from app.schemas.dto.phone_numbers.provisioning import VoicePlatformImport
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.messaging.constrained_strings import TwilioAccountSid
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.schemas.typings.telephony.strings import VoicePlatformPhoneNumberId
from app.utilities.resilience.circuit_calls import call_through_circuit


class GuardedElevenLabsPhoneNumbersClient(ElevenLabsPhoneNumbersClientContract):
    """
    ElevenLabs' phone numbers (importing a rented number, assigning it to
    an agent, removing it) through the voice platform's circuit breaker
    (`provider:elevenlabs`, the same as its agents and voice checks):
    while ElevenLabs is down a call fails at once with
    ProviderCircuitOpenError, and the phone numbers' maintenance job tries
    again later. Otherwise it behaves like the wrapped client.
    """

    def __init__(
        self,
        inner_client: ElevenLabsPhoneNumbersClientContract,
        circuit_breaker: CircuitBreakerContract,
        circuit: CircuitName,
    ) -> None:
        self._inner: ElevenLabsPhoneNumbersClientContract = inner_client
        self._circuit_breaker: CircuitBreakerContract = circuit_breaker
        self._circuit: CircuitName = circuit

    def import_twilio_number(
        self,
        request: VoicePlatformImport,
        account_sid: TwilioAccountSid,
        auth_token: PlatformSecret,
    ) -> VoicePlatformPhoneNumberId:
        return call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.import_twilio_number(request, account_sid, auth_token),
        )

    def assign_agent(
        self,
        phone_number_id: VoicePlatformPhoneNumberId,
        agent_id: VoiceAgentId | None,
    ) -> None:
        call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.assign_agent(phone_number_id, agent_id),
        )

    def delete_number(self, phone_number_id: VoicePlatformPhoneNumberId) -> None:
        call_through_circuit(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.delete_number(phone_number_id),
        )
