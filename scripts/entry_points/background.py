"""
The entry points without an outside caller: the background worker's jobs,
as the worker is wired (`GatewaysContainer.periodic_jobs` and
`.queued_job_operators`), and the commands of the backend image
(`docker/entrypoint.sh`) with the Render services that run them
(`render.yaml`).
"""

import ast
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import yaml

from app.containers.app import AppContainer
from app.gateways.worker.periodic_job_spec import PeriodicJobSpec
from scripts.entry_points.access_classes import OPERATOR_SHELL, WORKER

ROOT: Path = Path(__file__).resolve().parents[2]
ENTRYPOINT: Path = ROOT / "docker" / "entrypoint.sh"
RENDER_BLUEPRINT: Path = ROOT / "render.yaml"
CASE_LINE: re.Pattern[str] = re.compile(r"^  ([a-z][a-z-]*)\)$")
EXEC_LINE: re.Pattern[str] = re.compile(
    r"^\s+exec (?:python -m ([\w.]+)|uvicorn ([\w.]+):)"
)
COMMAND_PREFIX: str = "workshop "


def periodic_jobs(container: AppContainer) -> list[dict[str, object]]:
    """The periodic jobs in the order they run within a tick."""

    specs = cast(Sequence[PeriodicJobSpec], container.gateways.periodic_jobs())
    return [
        {
            "name": str(spec.name),
            "access": WORKER,
            "every_seconds": int(spec.interval_seconds),
            "lane": spec.lane.value,
            "runs_in": "every worker process"
            if spec.is_process_local
            else "one worker",
        }
        for spec in specs
    ]


def queued_jobs(container: AppContainer) -> list[dict[str, object]]:
    """The kinds of queued jobs the worker has a handler for."""

    handlers = cast(Mapping[str, object], container.gateways.queued_job_operators())
    return [{"name": str(name), "access": WORKER} for name in sorted(handlers)]


def image_commands(entrypoint: Path = ENTRYPOINT) -> dict[str, str]:
    """`workshop <command>` of the image and the Python module it runs."""

    commands: dict[str, str] = {}
    current: str | None = None
    for line in entrypoint.read_text(encoding="utf-8").splitlines():
        case = CASE_LINE.match(line)
        if case is not None:
            current = case.group(1)
            continue
        executed = EXEC_LINE.match(line)
        if executed is not None and current is not None:
            commands[current] = executed.group(1) or executed.group(2)
            current = None
    return commands


def module_summary(module: str) -> str:
    """The first paragraph of a module's docstring, without a closing colon."""

    path: Path = ROOT.joinpath(*module.split(".")).with_suffix(".py")
    docstring: str = ast.get_docstring(ast.parse(path.read_text("utf-8"))) or ""
    paragraph: str = docstring.strip().split("\n\n")[0]
    return " ".join(paragraph.split()).rstrip(":")


def command_role(command: object) -> str | None:
    """`migrate` of `workshop migrate --dry-run`; None for another command."""

    text: str = str(command or "")
    if not text.startswith(COMMAND_PREFIX):
        return None
    return text.removeprefix(COMMAND_PREFIX).split()[0]


def render_services(blueprint: Path = RENDER_BLUEPRINT) -> dict[str, list[str]]:
    """
    The Render services of each image command: the service's own command
    (with a cron's schedule) and the command it runs before each deploy.
    """

    loaded = cast(dict[str, object], yaml.safe_load(blueprint.read_text("utf-8")))
    services = cast(list[dict[str, object]], loaded.get("services", []))
    found: dict[str, list[str]] = {}
    for service in services:
        role: str | None = command_role(service.get("dockerCommand"))
        if role is not None:
            schedule: object = service.get("schedule")
            kind: str = str(service.get("type"))
            described: str = f"{kind}, {schedule}" if schedule is not None else kind
            found.setdefault(role, []).append(f"{service['name']} ({described})")
        before_deploy: str | None = command_role(service.get("preDeployCommand"))
        if before_deploy is not None:
            found.setdefault(before_deploy, []).append(
                f"{service['name']} (before each deploy)"
            )
    return found


def commands(entrypoint: Path = ENTRYPOINT) -> list[dict[str, object]]:
    """Every command of the backend image, with where Render runs it."""

    deployed: dict[str, list[str]] = render_services()
    return [
        {
            "name": f"{COMMAND_PREFIX}{name}",
            "access": OPERATOR_SHELL,
            "module": module,
            "summary": module_summary(module),
            "run_by_render": deployed.get(name, []),
        }
        for name, module in image_commands(entrypoint).items()
    ]
