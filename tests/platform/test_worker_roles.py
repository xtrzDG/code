"""
The worker roles of the Render Blueprints: customer replies run on at least
two workers, batch jobs on another, every lane has exactly one role, each
role's pool fits its threads, and only light customer-facing periodic jobs
run with the workers that answer customers.
"""

import re
from typing import cast

import pytest

from app.containers.app import AppContainer
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.jobs import JobLane
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.platform.connection_budget import (
    WORKER_COMMAND,
    BlueprintService,
    blueprint_services,
    pool_size,
)
from tests.platform.environment_sources import read

CUSTOMER_LANES: frozenset[JobLane] = frozenset({JobLane.INBOUND, JobLane.OUTBOUND})
BATCH_LANES: frozenset[JobLane] = frozenset({JobLane.DEFAULT, JobLane.AUTOTESTS})
# Threads of a worker besides its lanes that may hold a connection: the
# periodic thread (its jobs, the reaper) and the lease heartbeat.
OTHER_THREADS: int = 2
# The periodic jobs that run with the workers that answer customers: light,
# indexed, and late if a batch worker is busy or down.
CUSTOMER_PERIODIC_JOBS: dict[str, JobLane] = {
    "send_booking_reminders": JobLane.OUTBOUND,
    "sweep_stale_inbound_events": JobLane.INBOUND,
}


def workers(blueprint_path: str) -> list[BlueprintService]:
    return [
        service
        for service in blueprint_services(blueprint_path)
        if service.command == WORKER_COMMAND
    ]


def settings_of(service: BlueprintService) -> AppSettings:
    return assemble_app_settings(service.values)


def service_plan(blueprint_path: str, name: str) -> str:
    block: str = read(blueprint_path).split(f"    name: {name}\n", 1)[1]
    match = re.search(r"^    plan: (\S+)$", block, re.MULTILINE)
    assert match is not None, name
    return match.group(1)


def test_production_runs_a_customer_role_and_a_batch_role() -> None:
    roles = {
        service.name: (frozenset(settings_of(service).worker_lanes), service.instances)
        for service in workers("render.yaml")
    }

    assert roles == {
        "workshop-worker": (CUSTOMER_LANES, 2),
        "workshop-batch-worker": (BATCH_LANES, 1),
    }
    # Batch jobs hold more data than a customer turn.
    assert service_plan("render.yaml", "workshop-worker") == "starter"
    assert service_plan("render.yaml", "workshop-batch-worker") == "standard"


@pytest.mark.parametrize("blueprint_path", ["render.yaml", "render.staging.yaml"])
def test_every_lane_has_exactly_one_role(blueprint_path: str) -> None:
    served: list[JobLane] = [
        lane
        for service in workers(blueprint_path)
        for lane in settings_of(service).worker_lanes
    ]

    assert sorted(served) == sorted(JobLane)


def test_customer_replies_survive_one_lost_worker() -> None:
    for service in workers("render.yaml"):
        if JobLane.INBOUND in settings_of(service).worker_lanes:
            assert service.instances >= 2, service.name


@pytest.mark.parametrize("blueprint_path", ["render.yaml", "render.staging.yaml"])
def test_every_worker_pool_fits_its_lane_threads(blueprint_path: str) -> None:
    for service in workers(blueprint_path):
        settings = settings_of(service)
        threads: int = sum(
            int(settings.worker_lane_concurrency[lane])
            for lane in settings.worker_lanes
        )
        assert pool_size(service) >= threads + OTHER_THREADS, service.name
        if JobLane.INBOUND in settings.worker_lanes:
            # Every inbound thread can take a turn place at once.
            assert int(settings.llm_max_concurrency) >= int(
                settings.worker_lane_concurrency[JobLane.INBOUND]
            ), service.name


def test_only_light_customer_jobs_run_with_the_customer_workers() -> None:
    specs = cast(list[PeriodicJobSpec], AppContainer().gateways.periodic_jobs())
    on_customer_lanes: dict[str, JobLane] = {
        str(spec.name): spec.lane
        for spec in specs
        if not spec.is_process_local and spec.lane in CUSTOMER_LANES
    }

    assert on_customer_lanes == CUSTOMER_PERIODIC_JOBS
    assert {spec.lane for spec in specs} <= CUSTOMER_LANES | {JobLane.DEFAULT}
