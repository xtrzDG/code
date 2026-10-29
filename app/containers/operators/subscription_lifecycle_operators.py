from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.subscription_lifecycle_pipelines import (
    SubscriptionLifecyclePipelinesContainer,
)
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class SubscriptionLifecycleOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the subscription lifecycle: the cabinet's endpoints in
    their business's scope; the hourly pause and win-back jobs over every
    business (platform-wide).
    """

    pipelines: SubscriptionLifecyclePipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    get_subscription_lifecycle_operator = pipeline_operator(
        pipelines.get_subscription_lifecycle_pipeline, storage_scope
    )
    pause_subscription_operator = pipeline_operator(
        pipelines.pause_subscription_pipeline, storage_scope
    )
    resume_subscription_operator = pipeline_operator(
        pipelines.resume_subscription_pipeline, storage_scope
    )
    accept_retention_offer_operator = pipeline_operator(
        pipelines.accept_retention_offer_pipeline, storage_scope
    )
    run_subscription_pauses_operator = platform_pipeline_operator(
        pipelines.run_subscription_pauses_pipeline, storage_scope
    )
    send_win_back_messages_operator = platform_pipeline_operator(
        pipelines.send_win_back_messages_pipeline, storage_scope
    )
