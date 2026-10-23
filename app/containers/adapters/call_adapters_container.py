from dependency_injector import containers
from dependency_injector.providers import (
    Callable,
    DependenciesContainer,
    Dependency,
    Singleton,
)

from app.adapters.monitoring.bucket_signal_counter_adapter import (
    BucketSignalCounterAdapter,
)
from app.adapters.telephony.twilio_call_fallback_adapter import (
    TwilioCallFallbackAdapter,
)
from app.adapters.voice.elevenlabs_voice_agent_provisioner import (
    ElevenLabsVoiceAgentProvisioner,
)
from app.adapters.voice.elevenlabs_voice_check_adapter import (
    ElevenLabsVoiceCheckAdapter,
)
from app.adapters.voice.elevenlabs_voice_webhook_adapter import (
    ElevenLabsVoiceWebhookAdapter,
)
from app.adapters.voice.guarded_elevenlabs_client import GuardedElevenLabsClient
from app.adapters.voice.zadarma_pbx_webhook_adapter import ZadarmaPbxWebhookAdapter
from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.phone_number_factories import build_phone_number_provisioner
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.phone_numbers import PhoneNumberProvisionerAdapterContract
from app.schemas.constants.resilience import OutboundProvider
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.domain.phone_numbers import (
    PhoneNumberDocument,
    PhoneNumberRequestDocument,
)
from app.utilities.resilience.provider_circuits import provider_circuit


class CallAdaptersContainer(containers.DeclarativeContainer):
    """
    The adapters of what follows a phone call: its document collections
    (migration 1051: callers who did not get through with their
    text-backs, each business's call settings; a sibling of
    DocumentCollectionsContainer with the same storage factory, Postgres
    with DATABASE_URL, else in memory), the call notifications of the
    telephony line (Zadarma PBX) and the voice platform (ElevenLabs Agents:
    its webhooks and the agent of each business); and the numbers rented
    for businesses (1213: the numbers, the requests the platform team
    arranges, the carrier that sells them).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # The RateLimitBucketAdapterContract of the platform's signal counters.
    rate_limit_buckets: Dependency[object] = Dependency()
    # The process's CircuitBreakerContract (the provider resilience).
    circuit_breaker: Dependency[object] = Dependency()

    # Every ElevenLabs API call through its circuit, counted with its
    # failures (voice_health).
    elevenlabs_client: Singleton[GuardedElevenLabsClient] = Singleton(
        GuardedElevenLabsClient,
        inner_client=clients.elevenlabs_client,
        signal_counter=Singleton(
            BucketSignalCounterAdapter,
            buckets=rate_limit_buckets,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
        circuit_breaker=circuit_breaker,
        circuit=Callable(provider_circuit, OutboundProvider.ELEVENLABS),
    )

    missed_call_collection = document_collection(
        MissedCallDocument,
        "missed_calls",
        config,
        clients,
        utilities,
        time_provider,
    )
    call_settings_collection = document_collection(
        CallSettingsDocument,
        "call_settings",
        config,
        clients,
        utilities,
        time_provider,
    )
    pbx_webhook_adapter: Singleton[ZadarmaPbxWebhookAdapter] = Singleton(
        ZadarmaPbxWebhookAdapter, app_settings=config.app_settings
    )
    # The call fallback of rented numbers (Twilio's VoiceFallbackUrl).
    call_fallback_adapter: Singleton[TwilioCallFallbackAdapter] = Singleton(
        TwilioCallFallbackAdapter, app_settings=config.app_settings
    )
    voice_webhook_adapter: Singleton[ElevenLabsVoiceWebhookAdapter] = Singleton(
        ElevenLabsVoiceWebhookAdapter,
        app_settings=config.app_settings,
    )
    voice_agent_provisioner: Singleton[ElevenLabsVoiceAgentProvisioner] = Singleton(
        ElevenLabsVoiceAgentProvisioner,
        elevenlabs_client=elevenlabs_client,
        app_settings=config.app_settings,
    )
    # The voice checks of autotests (ElevenLabs agent testing).
    voice_check_adapter: Singleton[ElevenLabsVoiceCheckAdapter] = Singleton(
        ElevenLabsVoiceCheckAdapter,
        elevenlabs_client=elevenlabs_client,
        app_settings=config.app_settings,
        monotonic_clock=time_provider.monotonic_clock,
    )
    phone_number_collection = document_collection(
        PhoneNumberDocument,
        "phone_numbers",
        config,
        clients,
        utilities,
        time_provider,
    )
    phone_number_request_collection = document_collection(
        PhoneNumberRequestDocument,
        "phone_number_requests",
        config,
        clients,
        utilities,
        time_provider,
    )
    # PHONE_NUMBER_PROVIDER=twilio with the Twilio and ElevenLabs keys; a
    # stand-in naming what is missing otherwise.
    phone_number_provisioner: Singleton[PhoneNumberProvisionerAdapterContract] = (
        Singleton(
            build_phone_number_provisioner,
            settings=config.app_settings,
            circuit_breaker=circuit_breaker,
        )
    )
