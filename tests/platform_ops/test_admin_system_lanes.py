"""
GET /v1/admin/system lists only the lanes jobs may be queued in: a lane
behind a closed release gate (`ops` until `ops_lane` opens) holds no job,
and the cabinet of the release before cannot name it, so the page leaves
it out until the gate opens.
"""

import pytest

from app.schemas.constants.jobs import JobLane
from app.schemas.dto.admin_system import AdminSystemQuery
from app.utilities.storage import release_gates
from app.utilities.storage.release_gates import OPS_LANE_GATE, RELEASE_GATES
from tests.platform_ops.ops_world import ADMIN, OpsWorld
from tests.platform_ops.test_admin_system_view import system_page


def test_the_ops_lane_is_left_out_while_its_gate_is_closed() -> None:
    view = system_page(OpsWorld()).run(AdminSystemQuery(user_id=ADMIN))

    assert [lane.lane for lane in view.lanes] == [
        JobLane.INBOUND,
        JobLane.OUTBOUND,
        JobLane.DEFAULT,
        JobLane.AUTOTESTS,
    ]


def test_the_ops_lane_is_shown_once_its_gate_opens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened = tuple(
        gate.model_copy(update={"is_open": True})
        if gate.name == OPS_LANE_GATE
        else gate
        for gate in RELEASE_GATES
    )
    monkeypatch.setattr(release_gates, "RELEASE_GATES", opened)

    view = system_page(OpsWorld()).run(AdminSystemQuery(user_id=ADMIN))

    assert [lane.lane for lane in view.lanes] == list(JobLane)
