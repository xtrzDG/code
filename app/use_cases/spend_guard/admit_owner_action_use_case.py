from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.dto.spend_guard import OwnerActionAdmission
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.limits.owner_action_limits import (
    OWNER_ACTION_LIMITS,
    OwnerActionLimit,
)


class AdmitOwnerActionUseCase(UseCaseContract[OwnerActionAdmission, None]):
    """
    Count one limited cabinet action (`owner_action_limits`: test chat 30 a
    minute per person, menu imports 10 an hour and autotest runs 20 a day
    per business) in the shared counters, or refuse it.

    Raises:
        RateLimitedError: the limit is used up; it carries the seconds until
            the action is allowed again (Retry-After). A refused action is
            not counted.
    """

    def __init__(
        self,
        rate_limit_registry: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._rate_limits: RequestRateLimitRegistryContract = rate_limit_registry
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: OwnerActionAdmission) -> None:
        limit: OwnerActionLimit = OWNER_ACTION_LIMITS[input_data.action]
        owner: str = (
            f"user:{input_data.user_id}"
            if limit.is_per_person
            else f"business:{input_data.business_id}"
        )
        counter = RateLimitCounter(
            key=RateLimitKey(f"{limit.key_prefix}:{owner}"),
            limit=RequestsPerWindow(limit.limit),
        )
        window = RateWindowSeconds(limit.window_seconds)
        now: Microseconds = self._wall_clock.now_unix()
        if self._rate_limits.try_acquire_all([counter], window, now) is None:
            return

        raise RateLimitedError(
            limit.refusal,
            retry_after_seconds=self._rate_limits.seconds_until_free(
                counter, window, now
            ),
        )
