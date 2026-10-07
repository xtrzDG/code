"""scripts/smoke.sh against a local stand-in of a deployment."""

import os
import shutil
import subprocess

import pytest

from tests.platform.environment_sources import ROOT
from tests.platform.smoke_server import (
    BUSINESS_ID,
    REPLY,
    FakeDeployment,
    running_deployment,
)

SMOKE_SCRIPT: str = str(ROOT / "scripts" / "smoke.sh")

pytestmark = pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("bash", "curl", "python3")),
    reason="the smoke script needs bash, curl and python3",
)


def run_smoke(
    *arguments: str,
    business_id: str = "",
    expected_reply: str = "",
) -> subprocess.CompletedProcess[str]:
    environment = {
        **{
            name: value
            for name, value in os.environ.items()
            if not name.startswith("SMOKE_")
        },
        "SMOKE_WAIT_SECONDS": "4",
        "SMOKE_REPLY_SECONDS": "10",
        "SMOKE_WIDGET_BUSINESS_ID": business_id,
        "SMOKE_EXPECT_REPLY": expected_reply,
        # Local requests never go through a proxy.
        "NO_PROXY": "127.0.0.1",
        "no_proxy": "127.0.0.1",
    }
    return subprocess.run(
        ["bash", SMOKE_SCRIPT, *arguments],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_a_healthy_deployment_passes_every_check() -> None:
    deployment = FakeDeployment()
    with running_deployment(deployment) as url:
        result = run_smoke(
            url,
            f"{url}/cabinet",
            business_id=BUSINESS_ID,
            expected_reply="staging server",
        )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[:6] == [
        "ok    GET /healthz",
        "ok    GET /readyz",
        "ok    GET /widget.js",
        "ok    GET /v1/auth/login-options",
        "ok    GET cabinet /login",
        "ok    GET widget config",
    ]
    assert f'ok    test chat: "{REPLY[:80]}"' in result.stdout
    assert str(deployment.posted[0]["session_key"]).startswith("smoke_")


def test_an_answer_that_arrives_later_is_polled() -> None:
    deployment = FakeDeployment(reply_inline=False)
    with running_deployment(deployment) as url:
        result = run_smoke(url, business_id=BUSINESS_ID)

    assert result.returncode == 0, result.stdout + result.stderr
    assert deployment.polls >= 2
    assert "ok    test chat" in result.stdout


def test_without_a_business_the_chat_is_skipped() -> None:
    with running_deployment(FakeDeployment()) as url:
        result = run_smoke(url)

    assert result.returncode == 0
    assert "skip  test chat" in result.stdout


@pytest.mark.parametrize(
    ("deployment", "expected_reply", "message"),
    [
        (FakeDeployment(is_ready=False), "", "GET /readyz answered 503"),
        (FakeDeployment(widget_script="<html></html>"), "", "/widget.js is not"),
        (FakeDeployment(configured_channels=[]), "", "no configured_channels"),
        (FakeDeployment(reply_text="Hello"), "staging server", "without"),
    ],
)
def test_a_broken_deployment_fails_with_the_reason(
    deployment: FakeDeployment,
    expected_reply: str,
    message: str,
) -> None:
    with running_deployment(deployment) as url:
        result = run_smoke(url, business_id=BUSINESS_ID, expected_reply=expected_reply)

    assert result.returncode == 1
    assert message in result.stderr


def test_an_unreachable_deployment_and_a_wrong_business_fail() -> None:
    with running_deployment(FakeDeployment()) as url:
        wrong_business = run_smoke(url, business_id="business_unknown")

    unreachable = run_smoke(url)

    assert wrong_business.returncode == 1
    assert "GET widget config answered 404" in wrong_business.stderr
    assert unreachable.returncode == 1
    assert "did not answer" in unreachable.stderr


def test_usage_is_printed_without_an_address() -> None:
    result = run_smoke()

    assert result.returncode == 2
    assert "scripts/smoke.sh https://" in result.stderr
