"""Lane names written in worker settings: blueprints and `.env.example`."""

from app.schemas.constants.jobs import JobLane

LANE_SEPARATOR: str = ","
VALUE_SEPARATOR: str = "="


def named_lanes(variable: str, raw_value: str) -> set[str]:
    """
    The lane names a WORKER_LANES ("inbound,outbound") or
    WORKER_LANE_CONCURRENCY ("inbound=8,ops=1") value spells out.
    """

    names: set[str] = set()
    for raw_item in raw_value.split(LANE_SEPARATOR):
        item: str = raw_item.strip().lower()
        if item == "":
            continue
        if variable == "WORKER_LANE_CONCURRENCY":
            item = item.partition(VALUE_SEPARATOR)[0].strip()
        names.add(item)

    return names


def lane_values(lanes: frozenset[JobLane]) -> set[str]:
    return {lane.value for lane in lanes}
