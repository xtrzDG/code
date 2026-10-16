from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.spend import RequestLimitClass
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.dto.spend_guard import ApiRequestAdmission
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.channels.widget_rate_limits import describe_client_network

MINUTE: RateWindowSeconds = RateWindowSeconds(60)


class AdmitApiRequestUseCase(UseCaseContract[ApiRequestAdmission, None]):
    """
    The generic API limits, in sliding minutes over the shared counters (so
    every API instance counts together): a signed-in person's requests
    (API_REQUESTS_PER_USER_PER_MINUTE, 600) and, stricter, their data
    exports (API_EXPORTS_PER_USER_PER_MINUTE, 30, counted on top); a client
    network's requests without a token (API_REQUESTS_PER_IP_PER_MINUTE,
    120; one IPv4 address or the /64 of an IPv6 one). A stolen token or a
    script reads data no faster than that; the routes with their own limits
    (the website chat, login codes) keep them.

    Raises:
        RateLimitedError: a limit is used up; it carries the seconds until a
            place frees (Retry-After). A refused request is not counted.
    """

    def __init__(
        self,
        rate_limit_registry: RequestRateLimitRegistryContract,
        settings: SpendGuardSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._rate_limits: RequestRateLimitRegistryContract = rate_limit_registry
        self._settings: SpendGuardSettings = settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ApiRequestAdmission) -> None:
        counters: list[RateLimitCounter] = self._counters_of(input_data)
        if not counters:
            return

        now: Microseconds = self._wall_clock.now_unix()
        refused_key = self._rate_limits.try_acquire_all(counters, MINUTE, now)
        if refused_key is None:
            return

        refused = next(counter for counter in counters if counter.key == refused_key)
        raise RateLimitedError(
            "Too many requests; wait a moment and try again.",
            retry_after_seconds=self._rate_limits.seconds_until_free(
                refused, MINUTE, now
            ),
        )

    def _counters_of(self, admission: ApiRequestAdmission) -> list[RateLimitCounter]:
        settings: SpendGuardSettings = self._settings
        if admission.user_id is not None:
            counters = [
                RateLimitCounter(
                    key=RateLimitKey(f"api:user:{admission.user_id}"),
                    limit=RequestsPerWindow(
                        int(settings.api_requests_per_user_per_minute)
                    ),
                )
            ]
            if admission.limit_class is RequestLimitClass.EXPORT:
                counters.append(
                    RateLimitCounter(
                        key=RateLimitKey(f"api-export:user:{admission.user_id}"),
                        limit=RequestsPerWindow(
                            int(settings.api_exports_per_user_per_minute)
                        ),
                    )
                )
            return counters

        if admission.client_ip_address is None:
            return []

        network: str = describe_client_network(admission.client_ip_address)
        return [
            RateLimitCounter(
                key=RateLimitKey(f"api:address:{network}"),
                limit=RequestsPerWindow(int(settings.api_requests_per_ip_per_minute)),
            )
        ]
