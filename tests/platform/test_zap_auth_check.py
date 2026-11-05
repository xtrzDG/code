"""
The /v1 scan of zap.yml must prove it was signed in: the hook
(scripts/zap_status_hook.py) records every answer ZAP received and
scripts/zap_auth_check.py fails a scan whose bearer header never reached
the API, which would otherwise pass on 401 answers alone.
"""

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

import pytest

from scripts import zap_status_hook
from scripts.zap_auth_check import (
    EXIT_NOT_SIGNED_IN,
    EXIT_SIGNED_IN,
    EXIT_UNUSABLE,
    main,
)
from tests.platform.test_supply_chain_workflows import scripts, steps, workflow

API: str = "http://localhost:8000"
BUSINESS: str = f"{API}/v1/businesses/b-1"


def write(directory: Path, answers: list[dict[str, Any]]) -> Path:
    path = directory / "api-statuses.json"
    path.write_text(json.dumps(answers), encoding="utf-8")
    return path


def run(*arguments: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(list(arguments))
    return code, out.getvalue(), err.getvalue()


def test_a_scan_signed_in_as_the_owner_passes(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        [
            {"url": f"{BUSINESS}/bookings", "status": 200},
            {"url": f"{BUSINESS}/leads", "status": 200},
            {"url": f"{BUSINESS}/bookings/10", "status": 404},
            {"url": f"{BUSINESS}/exports/download-link", "status": 401},
            {"url": f"{API}/v1/public-api/me", "status": 401},
            {"url": f"{API}/v1/public-api/leads", "status": 401},
        ],
    )
    summary = tmp_path / "summary.md"

    code, out, _ = run(str(path), "--summary", str(summary))

    assert code == EXIT_SIGNED_IN
    assert "signed in (4 answers of the seeded business's routes: 2 2xx, 1 401)" in out
    assert "was signed in" in summary.read_text(encoding="utf-8")


def test_a_scan_without_the_bearer_header_fails(tmp_path: Path) -> None:
    # Public routes answer 200 either way; the business's routes refuse.
    path = write(
        tmp_path,
        [
            {"url": f"{API}/v1/catalog/niches", "status": 200},
            {"url": f"{API}/v1/legal/overview", "status": 200},
            {"url": f"{BUSINESS}/bookings", "status": 401},
            {"url": f"{BUSINESS}/leads", "status": 401},
        ],
    )

    code, _, err = run(str(path))

    assert code == EXIT_NOT_SIGNED_IN
    assert "::error::The /v1 scan was not signed in (2 answers" in err


def test_401_on_half_of_the_business_routes_fails_despite_a_success(
    tmp_path: Path,
) -> None:
    path = write(
        tmp_path,
        [
            {"url": f"{BUSINESS}/bookings", "status": 200},
            {"url": f"{BUSINESS}/leads", "status": 401},
        ],
    )

    assert run(str(path))[0] == EXIT_NOT_SIGNED_IN


def test_a_scan_that_never_reached_the_business_fails(tmp_path: Path) -> None:
    path = write(tmp_path, [{"url": f"{API}/v1/catalog/niches", "status": 200}])

    assert run(str(path))[0] == EXIT_NOT_SIGNED_IN


@pytest.mark.parametrize(
    "content",
    ["", "[]", "{}", "not json", '[{"url": 1, "status": 200}]', '["x"]'],
)
def test_an_unusable_status_file_proves_nothing(tmp_path: Path, content: str) -> None:
    path = tmp_path / "api-statuses.json"
    path.write_text(content, encoding="utf-8")

    code, _, err = run(str(path))

    assert code == EXIT_UNUSABLE
    assert "proves nothing" in err


def test_a_missing_status_file_proves_nothing(tmp_path: Path) -> None:
    assert run(str(tmp_path / "absent.json"))[0] == EXIT_UNUSABLE


class FakeCore:
    """ZAP's `zap.core.messages` over a fixed history, page by page."""

    def __init__(self, messages: list[dict[str, str]]) -> None:
        self.history = messages
        self.pages: list[tuple[int, int]] = []

    def messages(self, start: str, count: str) -> list[dict[str, str]]:
        first, size = int(start), int(count)
        self.pages.append((first, size))
        return self.history[first : first + size]


class FakeZap:
    def __init__(self, messages: list[dict[str, str]]) -> None:
        self.core = FakeCore(messages)


def message(url: str, status_line: str) -> dict[str, str]:
    return {
        "requestHeader": f"GET {url} HTTP/1.1\r\nHost: localhost\r\n",
        "responseHeader": f"{status_line}\r\nContent-Type: application/json\r\n",
    }


def test_the_hook_records_every_answer_across_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "api-statuses.json"
    monkeypatch.setenv(zap_status_hook.STATUS_FILE_VARIABLE, str(target))
    monkeypatch.setattr(zap_status_hook, "PAGE_SIZE", 2)
    zap = FakeZap(
        [
            message(f"{BUSINESS}/bookings", "HTTP/1.1 200 OK"),
            message(f"{BUSINESS}/leads", "HTTP/1.1 401 Unauthorized"),
            message(f"{BUSINESS}/media", ""),
        ]
    )

    zap_status_hook.zap_pre_shutdown(zap)

    assert json.loads(target.read_text(encoding="utf-8")) == [
        {"url": f"{BUSINESS}/bookings", "status": 200},
        {"url": f"{BUSINESS}/leads", "status": 401},
        {"url": f"{BUSINESS}/media", "status": 0},
    ]
    assert zap.core.pages == [(0, 2), (2, 2)]
    assert run(str(target))[0] == EXIT_SIGNED_IN


def test_the_api_scan_runs_the_hook_and_its_verdict_gates_the_job() -> None:
    job = workflow("zap.yml")["jobs"]["baseline"]
    run_text = scripts(job)
    check = next(
        step
        for step in steps(job)
        if "scripts.zap_auth_check" in str(step.get("run", ""))
    )

    assert (
        'cp scripts/zap_status_hook.py "$RUNNER_TEMP/zap/zap_status_hook.py"'
        in run_text
    )
    assert "--hook=/zap/wrk/zap_status_hook.py" in run_text
    assert zap_status_hook.DEFAULT_STATUS_FILE == "/zap/wrk/api-statuses.json"
    assert '"$RUNNER_TEMP/zap/api-statuses.json"' in str(check["run"])
    assert "steps.seed.outcome == 'success'" in str(check["if"])
