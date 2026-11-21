"""
GET /v1/admin/system lists only the lanes jobs may be queued in: a lane
behind a closed release gate holds no job, and the cabinet of the release
before cannot name it, so the page leaves it out until the gate opens.
`ops` is listed from this release, which opens its gate `ops_lane`.
"""

import pytest

from app.schemas.constants.jobs import JobLane
from app.schemas.dto.admin_system import AdminSystemQuery
from app.utilities.storage import release_gates
from app.utilities.storage.release_gates import OPS_LANE_GATE, RELEASE_GATES
from tests.platform_ops.ops_world import ADMIN, OpsWorld
from tests.platform_ops.test_admin_system_view import system_page


def test_the_ops_lane_is_listed_now_its_gate_is_open() -> None:
    view = system_page(OpsWorld()).run(AdminSystemQuery(user_id=ADMIN))

    assert [lane.lane for lane in view.lanes] == list(JobLane)


def test_a_lane_behind_a_closed_gate_is_left_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed = tuple(
        gate.model_copy(update={"is_open": False})
        if gate.name == OPS_LANE_GATE
        else gate
        for gate in RELEASE_GATES
    )
    monkeypatch.setattr(release_gates, "RELEASE_GATES", closed)

    view = system_page(OpsWorld()).run(AdminSystemQuery(user_id=ADMIN))

    assert [lane.lane for lane in view.lanes] == [
        JobLane.INBOUND,
        JobLane.OUTBOUND,
        JobLane.DEFAULT,
        JobLane.AUTOTESTS,
    ]
