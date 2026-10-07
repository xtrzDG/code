"""Factories of the data-subject rights' providers that read the settings."""

from app.adapters.privacy.elevenlabs_conversation_erasure_adapter import (
    ElevenLabsConversationErasureAdapter,
)
from app.adapters.privacy.langfuse_trace_erasure_adapter import (
    LangfuseTraceErasureAdapter,
)
from app.adapters.privacy.messaging_platform_erasure_adapter import (
    MessagingPlatformErasureAdapter,
)
from app.clients.langfuse.langfuse_traces_client import LangfuseTracesClient
from app.contracts.channel_clients import ElevenLabsApiClientContract
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.processor_erasure import ProcessorErasureAdapterContract
from app.contracts.repositories.privacy_repositories import (
    SuppressionEntryRepoContract,
)
from app.facilitators.privacy.processor_erasure_facilitator import (
    ProcessorErasureFacilitator,
)
from app.facilitators.privacy.suppression_list_facilitator import (
    SuppressionListFacilitator,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.privacy import SubProcessor
from app.utilities.privacy.suppression_digests import derive_suppression_key


def build_suppression_list(
    settings: AppSettings,
    suppression_entry_repo: SuppressionEntryRepoContract,
) -> SuppressionListFacilitator:
    """The list keyed by SUPPRESSION_LIST_KEY (or its fallbacks)."""

    return SuppressionListFacilitator(
        suppression_entry_repo=suppression_entry_repo,
        suppression_key=derive_suppression_key(
            settings.privacy.suppression_list_key, settings.encryption_key
        ),
    )


def build_processor_erasure(
    settings: AppSettings,
    elevenlabs_client: ElevenLabsApiClientContract,
    job_queue: JobQueueFacilitatorContract,
) -> ProcessorErasureFacilitator:
    """
    The deletions at the sub-processors this platform is set up with:
    Langfuse with both LANGFUSE_* keys, ElevenLabs with ELEVENLABS_API_KEY;
    Meta and Telegram as the documented no-op (their copy is the customer's
    own chat).
    """

    adapters: list[ProcessorErasureAdapterContract] = []
    if (
        settings.langfuse_public_key is not None
        and settings.langfuse_secret_key is not None
    ):
        adapters.append(
            LangfuseTraceErasureAdapter(
                LangfuseTracesClient(
                    host=settings.langfuse_host,
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                )
            )
        )

    if settings.elevenlabs_api_key is not None:
        adapters.append(ElevenLabsConversationErasureAdapter(elevenlabs_client))

    adapters.extend(
        MessagingPlatformErasureAdapter(processor)
        for processor in (SubProcessor.META, SubProcessor.TELEGRAM)
    )
    return ProcessorErasureFacilitator(adapters=adapters, job_queue=job_queue)
