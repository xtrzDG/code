from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.adapters.voice.elevenlabs_voice_agent_provisioner import (
    ElevenLabsVoiceAgentProvisioner,
)
from app.adapters.voice.elevenlabs_voice_webhook_adapter import (
    ElevenLabsVoiceWebhookAdapter,
)
from app.adapters.voice.zadarma_pbx_webhook_adapter import ZadarmaPbxWebhookAdapter
from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.missed_calls import MissedCallDocument


class CallAdaptersContainer(containers.DeclarativeContainer):
    """
    The adapters of what follows a phone call: its document collections
    (migration 1051: callers who did not get through with their
    text-backs, each business's call settings; a sibling of
    DocumentCollectionsContainer with the same storage factory, Postgres
    with DATABASE_URL, else in memory), the call notifications of the
    telephony line (Zadarma PBX) and the voice platform (ElevenLabs Agents:
    its webhooks and the agent of each business).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

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
    voice_webhook_adapter: Singleton[ElevenLabsVoiceWebhookAdapter] = Singleton(
        ElevenLabsVoiceWebhookAdapter,
        app_settings=config.app_settings,
    )
    voice_agent_provisioner: Singleton[ElevenLabsVoiceAgentProvisioner] = Singleton(
        ElevenLabsVoiceAgentProvisioner,
        elevenlabs_client=clients.elevenlabs_client,
        app_settings=config.app_settings,
    )
