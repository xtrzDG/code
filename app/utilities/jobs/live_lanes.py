"""The worker lanes jobs may be queued in by this release."""

from collections.abc import Sequence

from app.schemas.constants.jobs import JobLane
from app.schemas.dto.release_gates import ReleaseGate
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.release_gates import closed_gates_of

QUEUED_JOBS: DocumentCollectionName = DocumentCollectionName("queued_jobs")
LANE_PATH: tuple[str, ...] = ("lane",)


def closed_lanes(gates: Sequence[ReleaseGate] | None = None) -> frozenset[JobLane]:
    """
    The lanes behind a closed release gate: this release reads them, but no
    job is queued in them yet, and the release before does not know them
    (so no worker setting and no API answer names them either).
    """

    return frozenset(
        JobLane(value)
        for steps, values in closed_gates_of(QUEUED_JOBS, gates)
        if steps == LANE_PATH
        for value in values
    )


def live_lanes(gates: Sequence[ReleaseGate] | None = None) -> tuple[JobLane, ...]:
    """Every lane but the closed ones, in lane order."""

    closed: frozenset[JobLane] = closed_lanes(gates)
    return tuple(lane for lane in JobLane if lane not in closed)
