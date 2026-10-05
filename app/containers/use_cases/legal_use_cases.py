from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.legal import (
    LegalDocumentQuery,
    LegalDocumentView,
    SubprocessorListQuery,
    SubprocessorListView,
)
from app.use_cases.legal.get_legal_document_use_case import GetLegalDocumentUseCase
from app.use_cases.legal.get_subprocessors_use_case import GetSubprocessorsUseCase
from app.use_cases.legal.send_subprocessor_notices_use_case import (
    SendSubprocessorNoticesUseCase,
)


class LegalUseCasesContainer(containers.DeclarativeContainer):
    """
    The platform's legal texts (terms, privacy policy, cookies), its
    sub-processor list and the notices of its changes to owners (1124).
    """

    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_subprocessors_use_case: Factory[
        UseCaseContract[SubprocessorListQuery, SubprocessorListView]
    ] = Factory(
        GetSubprocessorsUseCase,
        subprocessor_registry=registries.subprocessor_registry,
        localized_text_resolver=utilities.localized_text_resolver,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_legal_document_use_case: Factory[
        UseCaseContract[LegalDocumentQuery, LegalDocumentView]
    ] = Factory(
        GetLegalDocumentUseCase,
        legal_text_registry=registries.legal_text_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    send_subprocessor_notices_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            SendSubprocessorNoticesUseCase,
            subprocessor_registry=registries.subprocessor_registry,
            announcement_repo=repositories.subprocessor_announcement_repo,
            notice_repo=repositories.subprocessor_notice_repo,
            business_repo=repositories.business_repo,
            user_repo=repositories.user_repo,
            audit_log_repo=repositories.audit_log_repo,
            manager_notifier=facilitators.manager_notification_facilitator,
            localized_text_resolver=utilities.localized_text_resolver,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
