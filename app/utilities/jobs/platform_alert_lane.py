"""The worker lane the platform alerts are queued in."""

from collections.abc import Sequence

from app.schemas.constants.jobs import JobLane
from app.schemas.dto.release_gates import ReleaseGate
from app.utilities.storage.release_gates import OPS_LANE_GATE, is_gate_open


def platform_alert_lane(gates: Sequence[ReleaseGate] | None = None) -> JobLane:
    """
    OPS, the alerts' own thread in every worker, once the release gate
    `ops_lane` is open (the release before reads the lane); until then
    OUTBOUND, where no provider holds more than half of the threads.
    """

    return JobLane.OPS if is_gate_open(OPS_LANE_GATE, gates) else JobLane.OUTBOUND
