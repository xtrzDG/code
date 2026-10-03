from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.billing_go_live import GoLiveTrial, GoLiveTrialRequest
from app.schemas.dto.setup.setup_progress import ActivationEventRecord
from app.use_cases.billing.start_trial_at_go_live_use_case import (
    StartTrialAtGoLiveUseCase,
)
from app.use_cases.setup.record_activation_event_use_case import (
    RecordActivationEventUseCase,
)


class LaunchUseCasesContainer(containers.DeclarativeContainer):
    """
    What happens when an assistant goes live, shared by every way it does
    (publishing, "Apply changes", rollback, resuming): the free trial that
    starts then and the milestones of the guided setup.
    """

    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    start_trial_at_go_live_use_case: Factory[
        UseCaseContract[GoLiveTrialRequest, GoLiveTrial]
    ] = Factory(
        StartTrialAtGoLiveUseCase,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        plan_registry=registries.plan_registry,
        wall_clock=time_provider.microsecond_wall_clock,
        product_events=facilitators.product_events,
    )
    record_activation_event_use_case: Factory[
        UseCaseContract[ActivationEventRecord, None]
    ] = Factory(
        RecordActivationEventUseCase,
        activation_event_repo=repositories.activation_event_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        product_events=facilitators.product_events,
    )
