"""
The Postgres connections a Render Blueprint can open at its worst moment,
read from the Blueprint itself (docs/operations/capacity.md, "Connection
budget").

The worst moment is a deploy: Render starts the new instances of the API
and the worker before it stops the old ones, so both run at once, each with
a full pool and its LISTEN connection, while the nightly backup and the
pre-deploy migration may run too.
"""

import re
from dataclasses import dataclass

from app.schemas.configurations.app_settings import AppSettings
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.platform.environment_sources import read

# Render, "Postgres connection limits": instances with less than 8 GB of
# memory accept 100 connections. A plan missing here fails the test until
# its limit is added.
PLAN_CONNECTION_LIMITS: dict[str, int] = {
    "basic-256mb": 100,
    "basic-1gb": 100,
    "basic-4gb": 100,
}
# Old and new instances run side by side until the new ones are healthy.
DEPLOY_OVERLAP: int = 2
# The API listens for live events, the worker for job wake-ups: one
# connection each beside the pool (app/clients/postgres/
# postgres_notification_listener.py).
LISTEN_CONNECTIONS: int = 1
# `workshop backup`: the snapshot connection and pg_dump's own.
BACKUP_CONNECTIONS: int = 2
# `workshop migrate` (preDeployCommand): a pool of one.
MIGRATE_CONNECTIONS: int = 1
# Postgres keeps three for superusers (superuser_reserved_connections), and
# an operator's psql session or Render's own checks need a couple more.
RESERVED_CONNECTIONS: int = 5

# The settings that size a process's pool.
POOL_VARIABLES: tuple[str, ...] = ("THREADPOOL_SIZE", "DB_POOL_SIZE")
API_COMMAND: str = "workshop api"
WORKER_COMMAND: str = "workshop worker"
BACKUP_COMMAND: str = "workshop backup"
MIGRATE_COMMAND: str = "workshop migrate"


@dataclass(frozen=True)
class BlueprintService:
    name: str
    command: str | None
    pre_deploy_command: str | None
    instances: int
    # Literal `value:` settings, those of its env groups included.
    values: dict[str, str]
    reads_database: bool


@dataclass(frozen=True)
class ConnectionBudget:
    plan: str
    limit: int
    # What each part may open, by name, for the failure message.
    parts: dict[str, int]

    @property
    def worst_case(self) -> int:
        return sum(self.parts.values())


def literal_values(text: str) -> dict[str, str]:
    """`- key: NAME` followed by `value: ...` (not secrets, not references)."""

    return {
        name: value.strip().strip('"')
        for name, value in re.findall(r"- key: ([A-Z0-9_]+)\n\s+value: ([^\n]+)", text)
    }


def single(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.MULTILINE)
    return None if match is None else match.group(1).strip().strip('"')


def blueprint_services(blueprint_path: str) -> list[BlueprintService]:
    blueprint: str = read(blueprint_path)
    groups_text, services_text = blueprint.split("\nservices:\n", 1)
    groups: dict[str, dict[str, str]] = {}
    for chunk in re.split(r"^  - name: ", groups_text, flags=re.MULTILINE)[1:]:
        groups[chunk.split("\n", 1)[0].strip()] = literal_values(chunk)

    services: list[BlueprintService] = []
    for chunk in re.split(r"^  - type: ", services_text, flags=re.MULTILINE)[1:]:
        values: dict[str, str] = {}
        for group_name in re.findall(r"- fromGroup: (\S+)", chunk):
            values |= groups[group_name]
        values |= literal_values(chunk)
        name = single(r"^    name: (\S+)$", chunk)
        assert name is not None, chunk
        services.append(
            BlueprintService(
                name=name,
                command=single(r"^    dockerCommand: (.+)$", chunk),
                pre_deploy_command=single(r"^    preDeployCommand: (.+)$", chunk),
                instances=int(single(r"^    numInstances: (\d+)$", chunk) or "1"),
                values=values,
                reads_database="- key: DATABASE_URL" in chunk,
            )
        )

    return services


def database_plan(blueprint_path: str) -> str:
    databases_text: str = read(blueprint_path).split("\nenvVarGroups:\n", 1)[0]
    plan = single(r"^    plan: (\S+)$", databases_text.split("\ndatabases:\n", 1)[1])
    assert plan is not None, blueprint_path
    return plan


def pool_size(service: BlueprintService) -> int:
    """DB_POOL_SIZE as the process would read it (its default included)."""

    settings: AppSettings = assemble_app_settings(
        {
            name: service.values[name]
            for name in POOL_VARIABLES
            if name in service.values
        }
    )
    return int(settings.db_pool_size)


def process_connections(service: BlueprintService) -> int:
    """A process's whole pool and its LISTEN connection, during a deploy."""

    per_instance: int = pool_size(service) + LISTEN_CONNECTIONS
    return DEPLOY_OVERLAP * service.instances * per_instance


def connection_budget(blueprint_path: str) -> ConnectionBudget:
    plan: str = database_plan(blueprint_path)
    assert plan in PLAN_CONNECTION_LIMITS, (
        f"{blueprint_path}: add the connection limit of the {plan} plan."
    )
    parts: dict[str, int] = {"reserved": RESERVED_CONNECTIONS}
    for service in blueprint_services(blueprint_path):
        if service.pre_deploy_command == MIGRATE_COMMAND:
            parts[f"{service.name} (migrate)"] = MIGRATE_CONNECTIONS
        if service.command in (API_COMMAND, WORKER_COMMAND):
            parts[service.name] = process_connections(service)
        elif service.command == BACKUP_COMMAND:
            parts[service.name] = BACKUP_CONNECTIONS
        else:
            assert not service.reads_database, (
                f"{blueprint_path}: count the connections of {service.name} "
                f"({service.command})."
            )

    return ConnectionBudget(plan, PLAN_CONNECTION_LIMITS[plan], parts)
