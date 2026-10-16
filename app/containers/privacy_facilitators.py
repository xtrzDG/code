from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Dependency, Singleton

from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.privacy_factories import (
    build_processor_erasure,
    build_suppression_list,
)
from app.containers.repositories import RepositoriesContainer
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.facilitators.privacy.processor_erasure_facilitator import (
    ProcessorErasureFacilitator,
)
from app.facilitators.privacy.suppression_list_facilitator import (
    SuppressionListFacilitator,
)


class PrivacyFacilitatorsContainer(containers.DeclarativeContainer):
    """
    Data-subject rights: the suppression list (1113) and the deletions at
    the sub-processors (1123). A child of FacilitatorsContainer, which names
    them flat (`facilitators.suppression_list`).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    job_queue: Dependency[JobQueueFacilitator] = Dependency(
        instance_of=JobQueueFacilitator
    )

    # Customers who said STOP, as digests kept through erasure (1113).
    suppression_list: Singleton[SuppressionListFacilitator] = Singleton(
        build_suppression_list,
        settings=config.app_settings,
        suppression_entry_repo=repositories.suppression_entry_repo,
    )
    # Copies at Langfuse and ElevenLabs deleted with the platform's own, by
    # queued jobs with retries (erasure and retention, 1123).
    processor_erasure: Singleton[ProcessorErasureFacilitator] = Singleton(
        build_processor_erasure,
        settings=config.app_settings,
        elevenlabs_client=clients.elevenlabs_client,
        job_queue=job_queue,
    )
