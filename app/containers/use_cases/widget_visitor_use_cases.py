from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.channels.widget_uploads import (
    WidgetAttachmentView,
    WidgetUploadAdmission,
    WidgetUploadAllowance,
    WidgetUploadCommand,
)
from app.use_cases.channels.uploads.accept_widget_upload_use_case import (
    AcceptWidgetUploadUseCase,
)
from app.use_cases.channels.uploads.admit_widget_upload_use_case import (
    AdmitWidgetUploadUseCase,
)


class WidgetVisitorUseCasesContainer(containers.DeclarativeContainer):
    """
    What a website chat visitor does besides writing: a photo or a voice
    note uploaded for the next message (counted before it is read, then
    checked and kept encrypted, migration 1191).
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    admit_widget_upload_use_case: Factory[
        UseCaseContract[WidgetUploadAdmission, WidgetUploadAllowance]
    ] = Factory(
        AdmitWidgetUploadUseCase,
        business_repo=repositories.business_repo,
        channel_repo=repositories.channel_repo,
        rate_limit_registry=registries.request_rate_limit_registry,
        media_settings=config.app_settings.provided.media,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    accept_widget_upload_use_case: Factory[
        UseCaseContract[WidgetUploadCommand, WidgetAttachmentView]
    ] = Factory(
        AcceptWidgetUploadUseCase,
        widget_upload_repo=repositories.widget_upload_repo,
        media_storage=adapters.media.media_storage,
        media_settings=config.app_settings.provided.media,
        wall_clock=time_provider.microsecond_wall_clock,
    )
