"""
The weekly active scan of staging (scripts/zap_staging.py,
.github/workflows/zap-staging.yml): it attacks every operation of the public
API from the committed description (reads and writes, no event streams)
against staging's https address only, and fails unless the API key signed
it in; staging that is not configured fails the scheduled run loudly.
"""

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from scripts.zap_staging import (
    EXIT_DONE,
    EXIT_NOT_SIGNED_IN,
    EXIT_UNUSABLE,
    main,
    public_api_definition,
)

ROOT: Path = Path(__file__).resolve().parents[2]
OPENAPI: Path = ROOT / "web" / "openapi.json"
STAGING: str = "https://api.staging.workshop.test"


def run(*arguments: str) -> tuple[int, str, str]:
    output, errors = io.StringIO(), io.StringIO()
    with redirect_stdout(output), redirect_stderr(errors):
        code = main(list(arguments))
    return code, output.getvalue(), errors.getvalue()


def test_the_definition_is_the_public_api_with_its_writes() -> None:
    source = json.loads(OPENAPI.read_text(encoding="utf-8"))
    cut = public_api_definition(source, STAGING + "/")
    public = {path for path in source["paths"] if path.startswith("/v1/public-api/")}

    assert set(cut["paths"]) == public
    assert cut["servers"] == [{"url": STAGING}]
    assert "post" in cut["paths"]["/v1/public-api/bookings"]
    assert cut["components"] == source["components"]


def test_event_streams_are_left_out() -> None:
    stream = {"responses": {"200": {"content": {"text/event-stream": {}}}}}
    plain = {"responses": {"200": {"content": {"application/json": {}}}}}
    source: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {"title": "API", "version": "1"},
        "paths": {
            "/v1/public-api/events": {"get": stream},
            "/v1/public-api/me": {"get": plain, "parameters": []},
            "/v1/businesses/{business_id}": {"get": plain},
        },
    }

    assert set(public_api_definition(source, STAGING)["paths"]) == {"/v1/public-api/me"}


@pytest.mark.parametrize("server", ["http://api.staging.test", "staging", ""])
def test_staging_is_scanned_over_https_only(tmp_path: Path, server: str) -> None:
    code, output, errors = run("definition", str(OPENAPI), "--server", server)

    assert (code, output) == (EXIT_UNUSABLE, "")
    assert "must be https" in errors


def test_the_definition_command_prints_the_cut() -> None:
    code, output, _ = run("definition", str(OPENAPI), "--server", STAGING)

    assert code == EXIT_DONE
    assert json.loads(output)["servers"] == [{"url": STAGING}]


def statuses(tmp_path: Path, answers: list[tuple[str, int]]) -> str:
    path = tmp_path / "api-statuses.json"
    path.write_text(
        json.dumps([{"url": url, "status": status} for url, status in answers]),
        encoding="utf-8",
    )
    return str(path)


def test_a_scan_signed_in_with_the_key_passes(tmp_path: Path) -> None:
    file = statuses(
        tmp_path,
        [
            (f"{STAGING}/v1/public-api/me", 200),
            (f"{STAGING}/v1/public-api/bookings", 422),
            (f"{STAGING}/v1/public-api/leads", 401),
            (f"{STAGING}/healthz", 401),
        ],
    )
    summary = tmp_path / "summary.md"
    code, output, _ = run("signed-in", file, "--summary", str(summary))

    assert code == EXIT_DONE
    assert "3 answers of the public API: 1 2xx, 1 401" in output
    assert "was signed in" in summary.read_text(encoding="utf-8")


def test_a_scan_refused_everywhere_fails(tmp_path: Path) -> None:
    file = statuses(
        tmp_path,
        [(f"{STAGING}/v1/public-api/me", 401), (f"{STAGING}/v1/public-api/leads", 401)],
    )
    code, _, errors = run("signed-in", file)

    assert code == EXIT_NOT_SIGNED_IN
    assert "STAGING_SCAN_API_KEY" in errors


@pytest.mark.parametrize("content", ["[]", "{}", "not json", '[{"url": 1}]'])
def test_an_unusable_status_file_proves_nothing(tmp_path: Path, content: str) -> None:
    path = tmp_path / "api-statuses.json"
    path.write_text(content, encoding="utf-8")

    assert run("signed-in", str(path))[0] == EXIT_UNUSABLE


def test_the_workflow_attacks_staging_weekly_and_fails_when_not_configured() -> None:
    document = cast(
        dict[Any, Any],
        yaml.safe_load(
            (ROOT / ".github" / "workflows" / "zap-staging.yml").read_text("utf-8")
        ),
    )
    on = cast(dict[str, Any], document.get("on", document.get(True)))
    job = cast(dict[str, Any], document["jobs"]["active"])
    steps = cast(list[dict[str, Any]], job["steps"])
    configured = steps[0]
    scan = next(step for step in steps if "zap-api-scan.py" in str(step.get("run")))

    assert on["schedule"] and "workflow_dispatch" in on and "push" not in on
    assert configured["env"]["STAGING_URL"] == "${{ vars.STAGING_URL }}"
    assert "exit 1" in str(configured["run"]) and "::error::" in str(configured["run"])
    # An active scan: no safe mode (-S), signed in with the key, judged by
    # the reviewed rules.
    assert " -S" not in str(scan["run"])
    assert scan["env"]["STAGING_SCAN_API_KEY"] == "${{ secrets.STAGING_SCAN_API_KEY }}"
    script = "\n".join(str(step.get("run", "")) for step in steps)
    assert "scripts.zap_gate" in script and "--rules .zap/rules.tsv" in script
    assert "scripts.zap_staging signed-in" in script
    assert "@sha256:" in str(document["env"]["ZAP_IMAGE"])
