"""Runs scripts/smoke.sh for the tests (against tests/platform/smoke_server.py)."""

import os
import shutil
import subprocess

import pytest

from tests.platform.environment_sources import ROOT

SMOKE_SCRIPT: str = str(ROOT / "scripts" / "smoke.sh")

needs_smoke_tools: pytest.MarkDecorator = pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("bash", "curl", "python3")),
    reason="the smoke script needs bash, curl and python3",
)


def run_smoke(
    *arguments: str,
    business_id: str = "",
    expected_reply: str = "",
    allow_api_docs: str = "",
    login_read_pause: str = "0",
    request_seconds: str = "",
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
        "SMOKE_ALLOW_API_DOCS": allow_api_docs,
        "SMOKE_LOGIN_READ_PAUSE_SECONDS": login_read_pause,
        # Empty: the script's own default.
        "SMOKE_REQUEST_SECONDS": request_seconds,
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
