from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.feedback_pipelines import FeedbackPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class FeedbackOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the feedback after visits: the periodic job over every
    business that asks (platform-wide), the review link a customer opens
    (its input names no business, so it runs unscoped and the use case
    finds the business itself) and Settings → Reviews (in the business's
    scope).
    """

    feedback_pipelines: FeedbackPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    request_visit_feedback_operator = platform_pipeline_operator(
        feedback_pipelines.request_visit_feedback_pipeline, storage_scope
    )
    open_review_link_operator = pipeline_operator(
        feedback_pipelines.open_review_link_pipeline, storage_scope
    )
    get_review_settings_operator = pipeline_operator(
        feedback_pipelines.get_review_settings_pipeline, storage_scope
    )
    update_review_settings_operator = pipeline_operator(
        feedback_pipelines.update_review_settings_pipeline, storage_scope
    )
    get_review_stats_operator = pipeline_operator(
        feedback_pipelines.get_review_stats_pipeline, storage_scope
    )
    list_feedback_requests_operator = pipeline_operator(
        feedback_pipelines.list_feedback_requests_pipeline, storage_scope
    )
