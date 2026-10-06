"""WORKER_LANE_CONCURRENCY: threads per worker lane."""

import pytest

from app.schemas.constants.jobs import JobLane
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)


def test_lanes_default_to_customer_messages_first() -> None:
    settings = assemble_app_settings({})

    assert {
        lane: int(threads) for lane, threads in settings.worker_lane_concurrency.items()
    } == {
        JobLane.INBOUND: 8,
        JobLane.OUTBOUND: 4,
        JobLane.DEFAULT: 2,
        JobLane.AUTOTESTS: 2,
    }


def test_lanes_left_out_keep_their_default() -> None:
    settings = assemble_app_settings(
        {"WORKER_LANE_CONCURRENCY": " Inbound = 16 , autotests=1,"}
    )

    assert {
        lane: int(threads) for lane, threads in settings.worker_lane_concurrency.items()
    } == {
        JobLane.INBOUND: 16,
        JobLane.OUTBOUND: 4,
        JobLane.DEFAULT: 2,
        JobLane.AUTOTESTS: 1,
    }


@pytest.mark.parametrize(
    ("raw_value", "message"),
    [
        ("inbound", "lane=threads pairs"),
        ("priority=3", "unknown lane 'priority'"),
        ("inbound=many", "must be a whole number"),
        ("inbound=0", "from 1 to 64"),
        ("default=65", "from 1 to 64"),
        ("default=2,default=3", "names lane 'default' twice"),
    ],
)
def test_broken_values_stop_the_start(raw_value: str, message: str) -> None:
    with pytest.raises(ValidationFailedError, match=message):
        assemble_app_settings({"WORKER_LANE_CONCURRENCY": raw_value})


def test_a_worker_serves_every_lane_unless_its_role_names_some() -> None:
    every = assemble_app_settings({})
    customer = assemble_app_settings({"WORKER_LANES": " Outbound , inbound,"})
    batch = assemble_app_settings({"WORKER_LANES": "autotests,default"})

    assert every.worker_lanes == tuple(JobLane)
    assert customer.worker_lanes == (JobLane.INBOUND, JobLane.OUTBOUND)
    assert batch.worker_lanes == (JobLane.DEFAULT, JobLane.AUTOTESTS)
    assert assemble_app_settings({"WORKER_LANES": " , "}).worker_lanes == tuple(JobLane)


@pytest.mark.parametrize(
    ("raw_value", "message"),
    [
        ("inbound,priority", "unknown lane 'priority'"),
        ("inbound,INBOUND", "names lane 'inbound' twice"),
    ],
)
def test_broken_roles_stop_the_start(raw_value: str, message: str) -> None:
    with pytest.raises(ValidationFailedError, match=message):
        assemble_app_settings({"WORKER_LANES": raw_value})
