"""
A worker lane behind a closed release gate (`ops` until `ops_lane` opens)
is named by no worker setting this release ships: the release before
refuses an unknown lane in WORKER_LANES and WORKER_LANE_CONCURRENCY at
startup, and a Render rollback keeps the service's environment, so naming
it would leave a rolled-back worker unable to start.
"""

import pytest

from app.schemas.constants.jobs import JobLane
from app.utilities.jobs.live_lanes import closed_lanes, live_lanes
from app.utilities.storage.release_gates import OPS_LANE_GATE, RELEASE_GATES
from tests.platform.connection_budget import blueprint_services
from tests.platform.environment_sources import env_file_values
from tests.platform.gated_lanes import lane_values, named_lanes

LANE_VARIABLES: tuple[str, ...] = ("WORKER_LANES", "WORKER_LANE_CONCURRENCY")


def test_the_ops_lane_is_closed_until_its_gate_opens() -> None:
    opened = [
        gate.model_copy(update={"is_open": True})
        if gate.name == OPS_LANE_GATE
        else gate
        for gate in RELEASE_GATES
    ]

    assert closed_lanes() == frozenset({JobLane.OPS})
    assert JobLane.OPS not in live_lanes()
    assert closed_lanes(opened) == frozenset()
    assert live_lanes(opened) == tuple(JobLane)


@pytest.mark.parametrize("blueprint_path", ["render.yaml", "render.staging.yaml"])
def test_no_blueprint_names_a_closed_lane(blueprint_path: str) -> None:
    closed: set[str] = lane_values(closed_lanes())
    for service in blueprint_services(blueprint_path):
        for variable in LANE_VARIABLES:
            named: set[str] = named_lanes(variable, service.values.get(variable, ""))
            assert not named & closed, (service.name, variable)


@pytest.mark.parametrize("env_path", [".env.example"])
def test_the_example_environment_names_no_closed_lane(env_path: str) -> None:
    values: dict[str, str] = env_file_values(env_path, include_commented=True)
    closed: set[str] = lane_values(closed_lanes())
    for variable in LANE_VARIABLES:
        assert not named_lanes(variable, values.get(variable, "")) & closed, variable


def test_named_lanes_reads_both_shapes() -> None:
    assert named_lanes("WORKER_LANES", " Inbound, outbound ,ops,") == {
        "inbound",
        "outbound",
        "ops",
    }
    assert named_lanes("WORKER_LANE_CONCURRENCY", "inbound=8, OPS = 1") == {
        "inbound",
        "ops",
    }
