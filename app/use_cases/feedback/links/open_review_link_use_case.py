from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
)
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.feedback.review_links import ReviewLinkTarget, ReviewLinkVisit
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.feedback.constrained_integers import ReviewLinkClickCount

UNAVAILABLE_MESSAGE: str = "This review link is not available."


class OpenReviewLinkUseCase(UseCaseContract[ReviewLinkVisit, ReviewLinkTarget]):
    """
    A customer opens the review link they were sent after rating a visit:
    the business's current Google review page, with the visit counted on
    their request (a messenger's link preview is not counted). An unknown
    token, or a business that removed its review link, is not found.

    The link names only a random token, so the request is found across
    businesses explicitly; the count is written in its business's scope.
    """

    def __init__(
        self,
        feedback_request_repo: FeedbackRequestRepoContract,
        profile_repo: BusinessProfileRepoContract,
        storage_scope: StorageScopeContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._feedback_request_repo: FeedbackRequestRepoContract = feedback_request_repo
        self._profile_repo: BusinessProfileRepoContract = profile_repo
        self._storage_scope: StorageScopeContract = storage_scope
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ReviewLinkVisit) -> ReviewLinkTarget:
        with self._storage_scope.platform_wide():
            request: FeedbackRequestDocument | None = (
                self._feedback_request_repo.find_by_token(input_data.token)
            )
        if request is None:
            raise NotFoundError(UNAVAILABLE_MESSAGE)

        with self._storage_scope.scoped_to_business(request.business_id):
            profile: BusinessProfileDocument | None = (
                self._profile_repo.get_by_business(request.business_id)
            )
            if profile is None or profile.google_review_url is None:
                raise NotFoundError(UNAVAILABLE_MESSAGE)

            if not input_data.is_link_preview:
                self._count(request)

        return ReviewLinkTarget(url=profile.google_review_url)

    def _count(self, request: FeedbackRequestDocument) -> None:
        now: Microseconds = self._wall_clock.now_unix()

        def count(current: FeedbackRequestDocument) -> FeedbackRequestDocument:
            current.review_clicks = ReviewLinkClickCount(int(current.review_clicks) + 1)
            current.first_clicked_at = current.first_clicked_at or now
            current.updated_at = now
            return current

        self._feedback_request_repo.update(request.business_id, request.id, count)
