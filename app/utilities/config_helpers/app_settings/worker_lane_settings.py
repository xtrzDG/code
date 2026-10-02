"""WORKER_LANE_CONCURRENCY: how many jobs of each lane one worker runs at once."""

from collections.abc import Mapping

from app.schemas.constants.jobs import JobLane
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_integers import WorkerLaneConcurrency

# Customer messages first; autotest runs (hundreds of model calls each) and
# other background work cannot take their threads.
DEFAULT_WORKER_LANE_CONCURRENCY: dict[JobLane, int] = {
    JobLane.INBOUND: 8,
    JobLane.OUTBOUND: 4,
    JobLane.DEFAULT: 2,
    JobLane.AUTOTESTS: 2,
}
LANE_SEPARATOR: str = ","
VALUE_SEPARATOR: str = "="


def read_worker_lane_concurrency(
    environment_variables: Mapping[str, str],
) -> dict[JobLane, WorkerLaneConcurrency]:
    """
    WORKER_LANE_CONCURRENCY, e.g. "inbound=8,outbound=4,default=2,autotests=2"
    (the default). Lanes left out keep their default; each value is 1 to 64
    threads per worker process.

    Raises:
        ValidationFailedError: an unknown lane, a repeated lane, or a value
            that is not a whole number from 1 to 64.
    """

    raw_value: str = environment_variables.get("WORKER_LANE_CONCURRENCY", "")
    concurrency: dict[JobLane, int] = dict(DEFAULT_WORKER_LANE_CONCURRENCY)
    seen: set[JobLane] = set()
    for raw_item in raw_value.split(LANE_SEPARATOR):
        item: str = raw_item.strip()
        if item == "":
            continue

        lane, threads = parse_lane_item(item)
        if lane in seen:
            raise ValidationFailedError(
                f"WORKER_LANE_CONCURRENCY names lane {lane.value!r} twice."
            )

        seen.add(lane)
        concurrency[lane] = threads

    try:
        return {
            lane: WorkerLaneConcurrency(threads)
            for lane, threads in concurrency.items()
        }
    except ValueError as error:
        raise ValidationFailedError(
            "WORKER_LANE_CONCURRENCY values must be whole numbers from "
            f"{WorkerLaneConcurrency.ge} to {WorkerLaneConcurrency.le}."
        ) from error


def parse_lane_item(item: str) -> tuple[JobLane, int]:
    """One "lane=threads" pair."""

    raw_lane, separator, raw_threads = item.partition(VALUE_SEPARATOR)
    lanes: str = ", ".join(lane.value for lane in JobLane)
    if separator == "":
        raise ValidationFailedError(
            f"WORKER_LANE_CONCURRENCY must list lane=threads pairs ({lanes}), "
            f"got {item!r}."
        )

    try:
        lane = JobLane(raw_lane.strip().lower())
    except ValueError as error:
        raise ValidationFailedError(
            f"WORKER_LANE_CONCURRENCY names an unknown lane {raw_lane.strip()!r}; "
            f"the lanes are {lanes}."
        ) from error

    try:
        return lane, int(raw_threads.strip())
    except ValueError as error:
        raise ValidationFailedError(
            f"WORKER_LANE_CONCURRENCY for {lane.value} must be a whole number, "
            f"got {raw_threads.strip()!r}."
        ) from error
