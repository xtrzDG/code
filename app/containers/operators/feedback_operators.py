from dependency_injector import containers
from dependency_injector.providers import Dependency, Factory

from app.containers.feedback.feedback_operator_factories import (
    FeedbackOperatorFactories,
)
from app.containers.feedback.feedback_root import FeedbackRoot
from app.contracts.operator_contract import OperatorContract
from app.schemas.dto.feedback.feedback_requests import (
    FeedbackRequestPage,
    FeedbackRequestPageQuery,
)
from app.schemas.dto.feedback.review_links import ReviewLinkTarget, ReviewLinkVisit
from app.schemas.dto.feedback.review_settings import (
    ReviewSettingsQuery,
    ReviewSettingsView,
    UpdateReviewSettingsCommand,
)
from app.schemas.dto.feedback.review_stats import ReviewStatsQuery, ReviewStatsView
from app.schemas.dto.jobs import JobReport, JobTick


class FeedbackOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the feedback after visits, built by the context's typed
    root (app/containers/feedback/, ADR 0010) and exposed here for the
    routers and the periodic job: the job over every business that asks
    (platform-wide), the review link a customer opens and Settings →
    Reviews.
    """

    root: Dependency[FeedbackRoot] = Dependency(instance_of=FeedbackRoot)
    operators = root.provided.operators

    request_visit_feedback_operator: Factory[OperatorContract[JobTick, JobReport]] = (
        Factory(FeedbackOperatorFactories.request_visit_feedback, operators)
    )
    open_review_link_operator: Factory[
        OperatorContract[ReviewLinkVisit, ReviewLinkTarget]
    ] = Factory(FeedbackOperatorFactories.open_review_link, operators)
    get_review_settings_operator: Factory[
        OperatorContract[ReviewSettingsQuery, ReviewSettingsView]
    ] = Factory(FeedbackOperatorFactories.get_review_settings, operators)
    update_review_settings_operator: Factory[
        OperatorContract[UpdateReviewSettingsCommand, ReviewSettingsView]
    ] = Factory(FeedbackOperatorFactories.update_review_settings, operators)
    get_review_stats_operator: Factory[
        OperatorContract[ReviewStatsQuery, ReviewStatsView]
    ] = Factory(FeedbackOperatorFactories.get_review_stats, operators)
    list_feedback_requests_operator: Factory[
        OperatorContract[FeedbackRequestPageQuery, FeedbackRequestPage]
    ] = Factory(FeedbackOperatorFactories.list_feedback_requests, operators)
