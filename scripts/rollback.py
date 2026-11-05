"""
Production rollback in one command (docs/operations/deploys.md, "Rollback"):

    export RENDER_API_KEY=...
    uv run python -m scripts.rollback <good-commit>            # the plan
    uv run python -m scripts.rollback <good-commit> --apply    # do it

Every service that deploys `release` (render.yaml) is rolled back, through
the Render API, to its last successful deploy of <good-commit>: the API
first, then the workers, then the cabinet, as the runbook orders them, and
the backup cron at the very end, so a refusal there leaves no service
customers use on the bad commit. Without --apply nothing changes: it
prints which deploy each service would return to and stops with exit code
1 when a service has none. With --apply it rolls back service after
service and stops at the first refusal. Moving `release` to the good
commit (the ruleset bypass) stays the runbook's second step; the command
for it is printed at the end.

Exit codes: 0 done (or the plan is complete), 1 a service has no deploy of
that commit or Render refused, 2 wrong arguments or no RENDER_API_KEY.
"""

import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO, cast

import httpx
import yaml

RENDER_API: str = "https://api.render.com/v1"
BLUEPRINT: Path = Path(__file__).resolve().parents[1] / "render.yaml"
RELEASE_BRANCH: str = "release"
# The runbook's order: the API before the code that reads what it writes,
# the cabinet (which calls the API) after both; the nightly backup cron,
# which no customer reaches, at the very end.
ROLLBACK_ORDER: tuple[str, ...] = (
    "workshop-api",
    "workshop-worker",
    "workshop-batch-worker",
    "workshop-cabinet",
    "workshop-backup",
)
COMMIT: re.Pattern[str] = re.compile(r"^[0-9a-f]{40}$")
DEPLOY_PAGE: int = 100
LIVE_STATUSES: frozenset[str] = frozenset({"live", "deactivated"})
EXIT_OK: int = 0
EXIT_FAILED: int = 1
EXIT_USAGE: int = 2
TIMEOUT_SECONDS: float = 30.0


@dataclass(frozen=True)
class Step:
    service: str
    service_id: str
    deploy_id: str | None


def release_services(blueprint: Path = BLUEPRINT) -> list[str]:
    """The Blueprint's services that deploy `release`, in rollback order."""

    document = cast(dict[str, Any], yaml.safe_load(blueprint.read_text("utf-8")))
    names = {
        str(service["name"])
        for service in cast(list[dict[str, Any]], document.get("services", []))
        if service.get("branch") == RELEASE_BRANCH
    }
    return [name for name in ROLLBACK_ORDER if name in names] + sorted(
        names - set(ROLLBACK_ORDER)
    )


def service_id(client: httpx.Client, name: str) -> str:
    response = client.get("/services", params={"name": name, "limit": 20})
    response.raise_for_status()
    for item in cast(list[dict[str, Any]], response.json()):
        service = cast(dict[str, Any], item.get("service", item))
        if service.get("name") == name:
            return str(service["id"])
    raise LookupError(f"Render has no service named {name}")


def deploy_of(client: httpx.Client, identifier: str, commit: str) -> str | None:
    """The newest deploy of `commit` that went live, None without one."""

    response = client.get(
        f"/services/{identifier}/deploys", params={"limit": DEPLOY_PAGE}
    )
    response.raise_for_status()
    for item in cast(list[dict[str, Any]], response.json()):
        deploy = cast(dict[str, Any], item.get("deploy", item))
        deployed = str(cast(dict[str, Any], deploy.get("commit") or {}).get("id", ""))
        if deployed == commit and deploy.get("status") in LIVE_STATUSES:
            return str(deploy["id"])
    return None


def plan(client: httpx.Client, services: Sequence[str], commit: str) -> list[Step]:
    steps: list[Step] = []
    for name in services:
        identifier = service_id(client, name)
        steps.append(Step(name, identifier, deploy_of(client, identifier, commit)))
    return steps


def run(
    arguments: Sequence[str],
    environment: Mapping[str, str],
    output: TextIO,
    transport: httpx.BaseTransport | None = None,
    services: Sequence[str] | None = None,
) -> int:
    commits = [argument for argument in arguments if not argument.startswith("--")]
    api_key = environment.get("RENDER_API_KEY", "").strip()
    if len(commits) != 1 or not COMMIT.match(commits[0]) or not api_key:
        output.write(
            "usage: RENDER_API_KEY=... python -m scripts.rollback "
            "<40-character commit> [--apply]\n"
        )
        return EXIT_USAGE

    commit, is_applied = commits[0], "--apply" in arguments
    with httpx.Client(
        base_url=RENDER_API,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        timeout=TIMEOUT_SECONDS,
        transport=transport,
    ) as client:
        steps = plan(client, services or release_services(), commit)
        for step in steps:
            target = step.deploy_id or "NO DEPLOY OF THIS COMMIT"
            output.write(f"{step.service} ({step.service_id}): {target}\n")
        if any(step.deploy_id is None for step in steps):
            output.write("Nothing rolled back: pick a commit every service ran.\n")
            return EXIT_FAILED
        if not is_applied:
            output.write("Plan only: run again with --apply to roll back.\n")
            return EXIT_OK

        for step in steps:
            response = client.post(
                f"/services/{step.service_id}/rollback",
                json={"deployId": step.deploy_id},
            )
            if response.is_error:
                output.write(
                    f"Render refused the rollback of {step.service} "
                    f"({response.status_code}); the services before it are "
                    "rolled back, the rest are not.\n"
                )
                return EXIT_FAILED
            output.write(f"Rolled back {step.service}.\n")

    output.write(
        "Next (runbook step 2): with the ruleset bypass, "
        f"git push --force-with-lease origin {commit}:{RELEASE_BRANCH}\n"
    )
    return EXIT_OK


def main() -> int:
    return run(sys.argv[1:], os.environ, sys.stdout)


if __name__ == "__main__":
    sys.exit(main())
