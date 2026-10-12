from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.deposit_repositories import (
    BookingOutcomeRepoContract,
    DepositRequestRepoContract,
    DepositSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deposits import DepositStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.deposits.deposit_counts import BookingOutcomeRow, DepositSumRow
from app.schemas.dto.deposits.deposit_report import DepositReport, DepositReportQuery
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.utilities.deposits.booking_deposit_state import PAID_DEPOSIT_STATUSES
from app.utilities.deposits.deposit_report_math import (
    MIN_FINISHED_BOOKINGS,
    count_in,
    money_lines,
    no_show_rate,
)

MICROSECONDS_PER_SECOND: int = 1_000_000
MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * MICROSECONDS_PER_SECOND


class GetDepositReportUseCase(UseCaseContract[DepositReportQuery, DepositReport]):
    """
    Overview → Reports, deposits (owners): over the last 7 to 366 days, the
    deposits asked and what became of them, the money collected per
    currency (paid and kept; to refund apart), and the no-show rate of the
    bookings that started in the window with a paid deposit and without
    one, each shown only from MIN_FINISHED_BOOKINGS finished bookings on (a
    smaller group says "not enough data" rather than a misleading share).
    Counted and summed by the database; test chats left out.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        deposit_settings_repo: DepositSettingsRepoContract,
        deposit_request_repo: DepositRequestRepoContract,
        booking_outcome_repo: BookingOutcomeRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._settings_repo: DepositSettingsRepoContract = deposit_settings_repo
        self._request_repo: DepositRequestRepoContract = deposit_request_repo
        self._outcome_repo: BookingOutcomeRepoContract = booking_outcome_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: DepositReportQuery) -> DepositReport:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        end = Microseconds(int(self._wall_clock.now_unix()) + 1)
        start = Microseconds(
            max(int(end) - int(input_data.days) * MICROSECONDS_PER_DAY, 0)
        )
        settings = self._settings_repo.get_by_business(business.id)
        requested: list[DepositSumRow] = self._request_repo.sum_requested(
            business.id, start, end
        )
        paid: list[DepositSumRow] = self._request_repo.sum_paid(business.id, start, end)
        outcomes: list[BookingOutcomeRow] = self._outcome_repo.count_outcomes(
            business.id,
            BookingSearchBoundSeconds(int(start) // MICROSECONDS_PER_SECOND),
            BookingSearchBoundSeconds(int(end) // MICROSECONDS_PER_SECOND),
        )
        return DepositReport(
            is_enabled=settings is not None and settings.is_enabled,
            days=input_data.days,
            starts_at=start,
            ends_at=end,
            requested_count=count_in(requested, frozenset(DepositStatus)),
            paid_count=count_in(requested, PAID_DEPOSIT_STATUSES),
            expired_count=count_in(requested, frozenset({DepositStatus.EXPIRED})),
            awaiting_count=count_in(requested, frozenset({DepositStatus.AWAITING})),
            money=money_lines(paid),
            with_deposit=no_show_rate(outcomes, with_deposit=True),
            without_deposit=no_show_rate(outcomes, with_deposit=False),
            min_sample=MIN_FINISHED_BOOKINGS,
        )
