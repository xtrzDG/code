from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.feedback_use_cases import FeedbackUseCasesContainer


class FeedbackOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the feedback after visits: the periodic job, the
    review link a customer opens and Settings → Reviews (one use case each).
    """

    feedback_use_cases: FeedbackUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    request_visit_feedback_orchestrator = use_case_orchestrator(
        feedback_use_cases.request_visit_feedback_use_case
    )
    open_review_link_orchestrator = use_case_orchestrator(
        feedback_use_cases.open_review_link_use_case
    )
    get_review_settings_orchestrator = use_case_orchestrator(
        feedback_use_cases.get_review_settings_use_case
    )
    update_review_settings_orchestrator = use_case_orchestrator(
        feedback_use_cases.update_review_settings_use_case
    )
    get_review_stats_orchestrator = use_case_orchestrator(
        feedback_use_cases.get_review_stats_use_case
    )
    list_feedback_requests_orchestrator = use_case_orchestrator(
        feedback_use_cases.list_feedback_requests_use_case
    )
