from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.feedback_orchestrators import (
    FeedbackOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class FeedbackPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the feedback after visits and Settings → Reviews."""

    feedback: FeedbackOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    request_visit_feedback_pipeline = orchestrator_pipeline(
        feedback.request_visit_feedback_orchestrator
    )
    open_review_link_pipeline = orchestrator_pipeline(
        feedback.open_review_link_orchestrator
    )
    get_review_settings_pipeline = orchestrator_pipeline(
        feedback.get_review_settings_orchestrator
    )
    update_review_settings_pipeline = orchestrator_pipeline(
        feedback.update_review_settings_orchestrator
    )
    get_review_stats_pipeline = orchestrator_pipeline(
        feedback.get_review_stats_orchestrator
    )
    list_feedback_requests_pipeline = orchestrator_pipeline(
        feedback.list_feedback_requests_orchestrator
    )
