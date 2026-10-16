"""
The deploy guard (scripts/check_data_tasks.sh) against a local stand-in of
production, and the promotion that runs it (deploy-smoke.yml).
"""

import os
import shutil
import subprocess

import pytest

from tests.platform.environment_sources import ROOT, read
from tests.platform.smoke_server import FakeDeployment, running_deployment

GUARD: str = str(ROOT / "scripts" / "check_data_tasks.sh")

needs_tools = pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("bash", "curl", "python3")),
    reason="the guard needs bash, curl and python3",
)


def guard(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "GUARD_REQUEST_SECONDS": "5",
        "NO_PROXY": "127.0.0.1",
        "no_proxy": "127.0.0.1",
    }
    return subprocess.run(
        ["bash", GUARD, *arguments],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def guard_against(deployment: FakeDeployment) -> subprocess.CompletedProcess[str]:
    with running_deployment(deployment) as url:
        return guard(url)


@needs_tools
def test_promotion_goes_ahead_once_every_task_is_done() -> None:
    result = guard_against(
        FakeDeployment(data_tasks={"status": "ok", "open": 0, "failed": 0})
    )

    assert result.returncode == 0, result.stderr
    assert "every post-deploy data task of production is done" in result.stdout


@needs_tools
def test_promotion_waits_while_a_task_is_open_or_failed() -> None:
    pending = guard_against(
        FakeDeployment(
            data_tasks={"status": "degraded", "open": 3, "failed": 1, "stalled": 1}
        )
    )
    not_ready = guard_against(
        FakeDeployment(is_ready=False, data_tasks={"status": "degraded", "open": 1})
    )

    assert pending.returncode == 1
    assert "3 post-deploy data task(s) of production are not done" in pending.stderr
    assert "(1 failed, 1 stalled)" in pending.stderr
    assert not_ready.returncode == 1


@needs_tools
def test_promotion_waits_when_the_guard_cannot_tell() -> None:
    skipped = guard_against(FakeDeployment(data_tasks={"status": "skipped"}))
    unreachable = guard("http://127.0.0.1:9")

    assert skipped.returncode == 1
    assert "could not read its data tasks" in skipped.stderr
    assert unreachable.returncode == 1


@needs_tools
def test_a_production_from_before_data_tasks_does_not_block() -> None:
    result = guard_against(FakeDeployment(data_tasks=None))

    assert result.returncode == 0
    assert "a release from before them" in result.stdout


@needs_tools
def test_the_guard_needs_the_production_address() -> None:
    assert guard().returncode == 2
    assert guard("").returncode == 2


def test_the_promotion_runs_the_guard_before_it_moves_release() -> None:
    promote: str = read(".github/workflows/deploy-smoke.yml").split(
        "\n  promote:\n", 1
    )[1]
    guard_step: int = promote.index('scripts/check_data_tasks.sh "$PRODUCTION_API_URL"')
    push: int = promote.index('git push origin "$SHA:refs/heads/release"')

    assert guard_step < push
    assert "PRODUCTION_API_URL: ${{ vars.PRODUCTION_API_URL }}" in promote
    assert (ROOT / "scripts" / "check_data_tasks.sh").stat().st_mode & 0o111
