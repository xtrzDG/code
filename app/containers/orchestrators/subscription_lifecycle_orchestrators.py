from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.subscription_lifecycle_use_cases import (
    SubscriptionLifecycleUseCasesContainer,
)


class SubscriptionLifecycleOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the subscription lifecycle (1161): the cancel dialog's
    offers, the pause and its resumption, the pause and win-back jobs (one
    use case each).
    """

    lifecycle: SubscriptionLifecycleUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_subscription_lifecycle_orchestrator = use_case_orchestrator(
        lifecycle.get_subscription_lifecycle_use_case
    )
    pause_subscription_orchestrator = use_case_orchestrator(
        lifecycle.pause_subscription_use_case
    )
    resume_subscription_orchestrator = use_case_orchestrator(
        lifecycle.resume_subscription_use_case
    )
    accept_retention_offer_orchestrator = use_case_orchestrator(
        lifecycle.accept_retention_offer_use_case
    )
    run_subscription_pauses_orchestrator = use_case_orchestrator(
        lifecycle.run_subscription_pauses_use_case
    )
    send_win_back_messages_orchestrator = use_case_orchestrator(
        lifecycle.send_win_back_messages_use_case
    )
