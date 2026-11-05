from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.feedback_collections_container import (
    FeedbackCollectionsContainer,
)
from app.repositories.feedback_repositories import (
    FeedbackRequestRepository,
    ReviewSettingsRepository,
)


class FeedbackRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of the feedback after visits (migration 1062): each
    business's review settings and the requests for feedback.
    `RepositoriesContainer` extends it, so they are read as
    `repositories.feedback_request_repo` like every other repository.
    """

    feedback_collections: FeedbackCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    review_settings_repo: Singleton[ReviewSettingsRepository] = Singleton(
        ReviewSettingsRepository,
        collection=feedback_collections.review_settings_collection,
    )
    feedback_request_repo: Singleton[FeedbackRequestRepository] = Singleton(
        FeedbackRequestRepository,
        collection=feedback_collections.feedback_request_collection,
    )
