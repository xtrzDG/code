"""
Every Render Blueprint fits its database's connection limit at the worst
moment, a deploy with the old and new instances running side by side (see
tests/platform/connection_budget.py for how the worst case is counted).
"""

import pytest

from app.schemas.configurations.app_settings import AppSettings
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.platform.connection_budget import (
    API_COMMAND,
    BACKUP_CONNECTIONS,
    DEPLOY_OVERLAP,
    LISTEN_CONNECTIONS,
    MIGRATE_CONNECTIONS,
    RESERVED_CONNECTIONS,
    WORKER_COMMAND,
    BlueprintService,
    blueprint_services,
    connection_budget,
    pool_size,
    process_connections,
)

BLUEPRINTS: tuple[str, ...] = ("render.yaml", "render.staging.yaml")


@pytest.mark.parametrize("blueprint_path", BLUEPRINTS)
def test_the_worst_case_fits_the_database_plan(blueprint_path: str) -> None:
    budget = connection_budget(blueprint_path)

    assert budget.worst_case <= budget.limit, (
        f"{blueprint_path} may open {budget.worst_case} connections, "
        f"{budget.plan} accepts {budget.limit}: {budget.parts}. Lower "
        "DB_POOL_SIZE, put PgBouncer in front or take a larger plan "
        "(docs/operations/capacity.md, 'Connection budget')."
    )


def test_production_counts_every_api_and_worker_instance_and_the_backup() -> None:
    budget = connection_budget("render.yaml")

    # Two API instances, two customer workers and one batch worker, each
    # with the pool of its role: 150 of the 200 of pro-8gb.
    assert budget.parts == {
        "reserved": RESERVED_CONNECTIONS,
        "workshop-api (migrate)": MIGRATE_CONNECTIONS,
        "workshop-api": DEPLOY_OVERLAP * 2 * (12 + LISTEN_CONNECTIONS),
        "workshop-worker": DEPLOY_OVERLAP * 2 * (16 + LISTEN_CONNECTIONS),
        "workshop-batch-worker": DEPLOY_OVERLAP * (10 + LISTEN_CONNECTIONS),
        "workshop-backup": BACKUP_CONNECTIONS,
    }
    assert (budget.plan, budget.limit, budget.worst_case) == ("pro-8gb", 200, 150)


@pytest.mark.parametrize("blueprint_path", BLUEPRINTS)
def test_every_worker_sets_the_pool_of_its_role(blueprint_path: str) -> None:
    """The default pool (half of 64 threads) is no role's size."""

    for service in blueprint_services(blueprint_path):
        if service.command == WORKER_COMMAND:
            assert "DB_POOL_SIZE" in service.values, service.name


@pytest.mark.parametrize("blueprint_path", BLUEPRINTS)
def test_api_instances_have_more_request_threads_than_connections(
    blueprint_path: str,
) -> None:
    """
    Most requests hold a connection for a moment, and a request waiting for
    one is cheaper than one refused: the threads outnumber the pool.
    """

    for service in blueprint_services(blueprint_path):
        if service.command != API_COMMAND:
            continue
        settings: AppSettings = assemble_app_settings(
            {"THREADPOOL_SIZE": service.values["THREADPOOL_SIZE"]}
        )
        assert int(settings.threadpool_size) > pool_size(service), service.name


@pytest.mark.parametrize("blueprint_path", BLUEPRINTS)
def test_no_api_runs_the_worker_inside(blueprint_path: str) -> None:
    """An embedded worker would open a pool and a LISTEN the budget misses."""

    for service in blueprint_services(blueprint_path):
        assert "EMBEDDED_WORKER" not in service.values, service.name


def test_an_unset_pool_follows_the_request_threads() -> None:
    service = BlueprintService(
        name="workshop-api",
        command=API_COMMAND,
        pre_deploy_command=None,
        instances=3,
        values={"THREADPOOL_SIZE": "40"},
        reads_database=True,
    )

    # Half the threads: 20 connections, a LISTEN, twice during a deploy.
    assert pool_size(service) == 20
    assert process_connections(service) == 2 * 3 * 21
