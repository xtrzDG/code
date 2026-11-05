from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.feedback import FeedbackRequestStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.feedback.feedback_tallies import FeedbackTally
from app.schemas.dto.feedback.review_stats import ReviewStatsQuery, ReviewStatsView
from app.schemas.typings.feedback.constrained_floats import AverageVisitScore
from app.schemas.typings.feedback.constrained_integers import (
    FeedbackRequestCount,
    ReviewStatsPeriodDays,
)

MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
STATS_PERIOD: ReviewStatsPeriodDays = ReviewStatsPeriodDays(30)
AVERAGE_DECIMALS: int = 1


class GetReviewStatsUseCase(UseCaseContract[ReviewStatsQuery, ReviewStatsView]):
    """
    How the feedback after visits went in the last 30 days (owners): the
    customers asked and those who answered, the average rating with the
    count of each score, how many opened the review link, and the visits
    that were not asked or whose request did not arrive. Counted in the
    database; no customer's data.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        feedback_request_repo: FeedbackRequestRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._feedback_request_repo: FeedbackRequestRepoContract = feedback_request_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ReviewStatsQuery) -> ReviewStatsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        since = Microseconds(
            int(self._wall_clock.now_unix()) - int(STATS_PERIOD) * MICROSECONDS_PER_DAY
        )
        return build_review_stats(self._feedback_request_repo.tally(business.id, since))


def build_review_stats(tally: FeedbackTally) -> ReviewStatsView:
    counts: dict[FeedbackRequestStatus, FeedbackRequestCount] = tally.status_counts

    def count(status: FeedbackRequestStatus) -> int:
        return int(counts.get(status, FeedbackRequestCount(0)))

    answered: int = count(FeedbackRequestStatus.ANSWERED)
    return ReviewStatsView(
        period_days=STATS_PERIOD,
        asked_count=FeedbackRequestCount(count(FeedbackRequestStatus.SENT) + answered),
        answered_count=FeedbackRequestCount(answered),
        average_score=(
            None
            if answered == 0
            else AverageVisitScore(
                round(int(tally.score_total) / answered, AVERAGE_DECIMALS)
            )
        ),
        score_counts=list(tally.score_counts),
        review_opened_count=tally.opened_count,
        skipped_count=FeedbackRequestCount(count(FeedbackRequestStatus.SKIPPED)),
        failed_count=FeedbackRequestCount(count(FeedbackRequestStatus.FAILED)),
    )
