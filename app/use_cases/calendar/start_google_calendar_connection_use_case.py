from typed_time_provider import Microseconds, WallClock

from app.contracts.operations import (
    CalendarAuthorizationStateRepoContract,
    GoogleCalendarClientContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.calendar import CalendarAuthorizationStateDocument
from app.schemas.dto.operations import (
    CalendarConnectUrlView,
    StartCalendarConnectionCommand,
)
from app.schemas.typings.bookings.constrained_strings import CalendarAuthorizationUrl
from app.schemas.typings.bookings.strings import CalendarAuthorizationState
from app.use_cases.bookings.operations_support import require_business
from app.use_cases.calendar.calendar_state import (
    generate_authorization_state,
    hash_authorization_state,
)
from app.utilities.scheduling.zoned_time import MICROSECONDS_PER_SECOND

AUTHORIZATION_STATE_LIFETIME_SECONDS: int = 10 * 60


class StartGoogleCalendarConnectionUseCase(
    UseCaseContract[StartCalendarConnectionCommand, CalendarConnectUrlView]
):
    """
    Owner starts connecting Google Calendar: a one-time state bound to the
    business and the owner is stored (hashed) for ten minutes, and the Google
    consent link asking for offline access to calendar events is returned.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        authorization_state_repo: CalendarAuthorizationStateRepoContract,
        calendar_client: GoogleCalendarClientContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._authorization_state_repo: CalendarAuthorizationStateRepoContract = (
            authorization_state_repo
        )
        self._calendar_client: GoogleCalendarClientContract = calendar_client
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: StartCalendarConnectionCommand) -> CalendarConnectUrlView:
        require_business(self._business_repo, input_data.business_id)
        state: CalendarAuthorizationState = generate_authorization_state()
        authorization_url: CalendarAuthorizationUrl = (
            self._calendar_client.build_authorization_url(state)
        )
        now: Microseconds = self._wall_clock.now_unix()
        expires_at = Microseconds(
            int(now) + AUTHORIZATION_STATE_LIFETIME_SECONDS * MICROSECONDS_PER_SECOND
        )
        self._authorization_state_repo.save(
            CalendarAuthorizationStateDocument(
                business_id=input_data.business_id,
                user_id=input_data.user_id,
                state_hash=hash_authorization_state(state),
                expires_at=expires_at,
                created_at=now,
                updated_at=now,
            )
        )
        return CalendarConnectUrlView(
            authorization_url=authorization_url,
            expires_at=expires_at,
        )
