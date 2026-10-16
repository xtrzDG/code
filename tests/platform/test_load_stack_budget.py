"""
The load stack (docker-compose.yml with perf/docker-compose.perf.yml) runs
the API and the worker with production's pools and threads
(render.yaml), and everything it opens at once fits the 100 connections
of its Postgres: the API processes, the worker, `seed-load` (it runs while
both are up) and the migration (docs/operations/capacity.md).
"""

from pathlib import Path
from typing import cast

import yaml

from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.platform.connection_budget import (
    API_COMMAND,
    LISTEN_CONNECTIONS,
    MIGRATE_CONNECTIONS,
    POOL_VARIABLES,
    WORKER_COMMAND,
    blueprint_services,
)

ROOT: Path = Path(__file__).resolve().parents[2]
# The postgres image's max_connections, of which three are kept for
# superusers (superuser_reserved_connections).
POSTGRES_CONNECTIONS: int = 100
SUPERUSER_RESERVED: int = 3
PRODUCTION_SETTINGS: tuple[str, ...] = (
    "THREADPOOL_SIZE",
    "DB_POOL_SIZE",
    "LLM_MAX_CONCURRENCY",
)

type Service = dict[str, object]


def load_stack_services() -> dict[str, Service]:
    """The compose services with the load override's settings merged in."""

    merged: dict[str, Service] = {}
    for name in ("docker-compose.yml", "perf/docker-compose.perf.yml"):
        document = cast(
            dict[str, object],
            yaml.safe_load((ROOT / name).read_text(encoding="utf-8")),
        )
        for service_name, service in cast(
            dict[str, Service], document["services"]
        ).items():
            current: Service = merged.setdefault(service_name, {})
            environment = cast(dict[str, str], current.get("environment", {}))
            current.update(service)
            current["environment"] = {
                **environment,
                **cast(dict[str, str], service.get("environment") or {}),
            }
    return merged


def environment_of(service: Service) -> dict[str, str]:
    return {
        name: str(value)
        for name, value in cast(dict[str, object], service["environment"]).items()
    }


def replicas_of(service: Service) -> int:
    deploy = cast(dict[str, object], service.get("deploy") or {})
    return int(cast(int, deploy.get("replicas", 1)))


def production_values(command: str) -> dict[str, str]:
    service = next(s for s in blueprint_services("render.yaml") if s.command == command)
    return service.values


def pool_of(environment: dict[str, str]) -> int:
    """DB_POOL_SIZE as the process reads it (its default included)."""

    return int(
        assemble_app_settings(
            {name: environment[name] for name in POOL_VARIABLES if name in environment}
        ).db_pool_size
    )


def test_the_load_stack_runs_productions_pools_and_threads() -> None:
    services = load_stack_services()
    api = environment_of(services["api"])
    worker = environment_of(services["worker"])

    for name in ("THREADPOOL_SIZE", "DB_POOL_SIZE"):
        assert api[name] == production_values(API_COMMAND)[name], name
    for name in PRODUCTION_SETTINGS:
        assert worker[name] == production_values(WORKER_COMMAND)[name], name
    # Production runs one worker instance (render.yaml has no numInstances).
    assert replicas_of(services["worker"]) == 1


def test_everything_the_load_stack_opens_fits_its_postgres() -> None:
    services = load_stack_services()
    api = environment_of(services["api"])
    worker = environment_of(services["worker"])

    api_connections = int(api["WEB_CONCURRENCY"]) * (pool_of(api) + LISTEN_CONNECTIONS)
    worker_connections = replicas_of(services["worker"]) * (
        pool_of(worker) + LISTEN_CONNECTIONS
    )
    # `seed-load` runs in an API container while the API and worker are up.
    seed_connections = pool_of(api)
    total = (
        api_connections
        + worker_connections
        + seed_connections
        + MIGRATE_CONNECTIONS
        + SUPERUSER_RESERVED
    )

    assert total <= POSTGRES_CONNECTIONS, (
        f"api {api_connections}, worker {worker_connections}, "
        f"seed-load {seed_connections}: {total} of {POSTGRES_CONNECTIONS}"
    )
