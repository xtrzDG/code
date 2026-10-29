from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.subscription_lifecycle_orchestrators import (
    SubscriptionLifecycleOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class SubscriptionLifecyclePipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the cancel dialog's offers, the pause and win-back."""

    lifecycle: SubscriptionLifecycleOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    get_subscription_lifecycle_pipeline = orchestrator_pipeline(
        lifecycle.get_subscription_lifecycle_orchestrator
    )
    pause_subscription_pipeline = orchestrator_pipeline(
        lifecycle.pause_subscription_orchestrator
    )
    resume_subscription_pipeline = orchestrator_pipeline(
        lifecycle.resume_subscription_orchestrator
    )
    accept_retention_offer_pipeline = orchestrator_pipeline(
        lifecycle.accept_retention_offer_orchestrator
    )
    run_subscription_pauses_pipeline = orchestrator_pipeline(
        lifecycle.run_subscription_pauses_orchestrator
    )
    send_win_back_messages_pipeline = orchestrator_pipeline(
        lifecycle.send_win_back_messages_orchestrator
    )
