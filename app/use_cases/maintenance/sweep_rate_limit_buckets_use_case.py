import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentCount

LOGGER: logging.Logger = logging.getLogger(__name__)


class SweepRateLimitBucketsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Periodic job: drop the request counters of the shared rate limits that
    no limit needs any more (older than their window and the next one), so
    the counters table stays as small as the traffic of the last minutes.
    The counters hold network addresses only as limit keys and live for
    minutes, so a sweep is not audited. Running it twice is harmless.
    """

    def __init__(
        self,
        rate_limit_registry: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        swept: DocumentCount = self._rate_limit_registry.forget_expired(
            self._wall_clock.now_unix()
        )
        LOGGER.info("Swept %d expired rate limit counters", int(swept))
        return JobReport(processed_count=ProcessedItemCount(int(swept)))
