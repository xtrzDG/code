from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_safety import PlatformBrakeRegistryContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.spend import OwnerAction, PlatformBrake
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
from app.utilities.spend.platform_brakes import platform_brake_refusal

# The actions that make the platform pay a model or the carrier at once,
# refused while a platform brake holds (the global pause, the daily budget
# stop). The test chat stays: its turns pass the spend guard, which hands
# them to the team; searching numbers and asking the team for one cost
# nothing.
BRAKED_ACTIONS: frozenset[OwnerAction] = frozenset(
    {
        OwnerAction.MENU_IMPORT,
        OwnerAction.AUTOTEST_RUN,
        OwnerAction.ALIAS_SUGGESTION,
        OwnerAction.PHONE_NUMBER_RENTAL,
    }
)


class AdmitOwnerActionUseCase(UseCaseContract[OwnerActionAdmission, None]):
    """
    Count one limited cabinet action (`owner_action_limits`: test chat 30 a
    minute per person, menu imports 10 an hour and autotest runs 20 a day
    per business) in the shared counters, or refuse it. While a platform
    brake holds, a costly action (`BRAKED_ACTIONS`) is refused first.

    Raises:
        ConflictError: a platform brake holds (reason `platform_brake`).
        RateLimitedError: the limit is used up; it carries the seconds until
            the action is allowed again (Retry-After). A refused action is
            not counted.
    """

    def __init__(
        self,
        rate_limit_registry: RequestRateLimitRegistryContract,
        platform_brakes: PlatformBrakeRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._rate_limits: RequestRateLimitRegistryContract = rate_limit_registry
        self._platform_brakes: PlatformBrakeRegistryContract = platform_brakes
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: OwnerActionAdmission) -> None:
        limit: OwnerActionLimit = OWNER_ACTION_LIMITS[input_data.action]
        counter: RateLimitCounter = owner_action_counter(input_data)
        window = RateWindowSeconds(limit.window_seconds)
        now: Microseconds = self._wall_clock.now_unix()
        refuse_under_a_brake(self._platform_brakes, input_data.action, now)
        if self._rate_limits.try_acquire_all([counter], window, now) is None:
            return

        raise RateLimitedError(
            limit.refusal,
            retry_after_seconds=self._rate_limits.seconds_until_free(
                counter, window, now
            ),
        )


class CheckOwnerActionRoomUseCase(UseCaseContract[OwnerActionAdmission, None]):
    """
    Whether one more limited action would stay within its limit, counting
    nothing: for an action that counts only when it succeeds (a number
    rental the carrier refused is not one of the day's rentals), checked
    before the costly work and admitted (`AdmitOwnerActionUseCase`) after.
    A costly action is refused while a platform brake holds, as there.

    Raises:
        ConflictError: a platform brake holds (reason `platform_brake`).
        RateLimitedError: the limit is used up (with Retry-After).
    """

    def __init__(
        self,
        rate_limit_registry: RequestRateLimitRegistryContract,
        platform_brakes: PlatformBrakeRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._rate_limits: RequestRateLimitRegistryContract = rate_limit_registry
        self._platform_brakes: PlatformBrakeRegistryContract = platform_brakes
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: OwnerActionAdmission) -> None:
        limit: OwnerActionLimit = OWNER_ACTION_LIMITS[input_data.action]
        counter: RateLimitCounter = owner_action_counter(input_data)
        window = RateWindowSeconds(limit.window_seconds)
        now: Microseconds = self._wall_clock.now_unix()
        refuse_under_a_brake(self._platform_brakes, input_data.action, now)
        if self._rate_limits.has_room(counter, window, now):
            return

        raise RateLimitedError(
            limit.refusal,
            retry_after_seconds=self._rate_limits.seconds_until_free(
                counter, window, now
            ),
        )


def refuse_under_a_brake(
    platform_brakes: PlatformBrakeRegistryContract,
    action: OwnerAction,
    now: Microseconds,
) -> None:
    """Refuse a costly action while a platform brake holds (nothing counted)."""

    if action not in BRAKED_ACTIONS:
        return

    brake: PlatformBrake | None = platform_brakes.current_brake(now)
    if brake is not None:
        raise platform_brake_refusal(brake)


def owner_action_counter(admission: OwnerActionAdmission) -> RateLimitCounter:
    """The shared counter of the action: per person or per business."""

    limit: OwnerActionLimit = OWNER_ACTION_LIMITS[admission.action]
    owner: str = (
        f"user:{admission.user_id}"
        if limit.is_per_person
        else f"business:{admission.business_id}"
    )
    return RateLimitCounter(
        key=RateLimitKey(f"{limit.key_prefix}:{owner}"),
        limit=RequestsPerWindow(limit.limit),
    )
