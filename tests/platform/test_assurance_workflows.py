"""
The supply-chain and scheduled guards stay in place: the workflow audit
(actionlint, zizmor) is a required check with both tools pinned by version
and SHA-256; CodeQL reads the workflows too; CI audits the cabinet's dev
dependencies at level high and runs Trivy's misconfiguration and secret
scanners; no package runs install scripts and uv builds nothing; every
lockfile is audited nightly, the release images are rescanned weekly,
staging is attacked weekly and production checked hourly; high-risk pull
requests are labelled by path.
"""

import fnmatch
import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any, cast

import yaml

ROOT: Path = Path(__file__).resolve().parents[2]
GITHUB: Path = ROOT / ".github"
WORKFLOWS: Path = GITHUB / "workflows"
SHA256: re.Pattern[str] = re.compile(r"^[0-9a-f]{64}$")


def load(path: Path) -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def triggers(document: dict[Any, Any]) -> dict[str, Any]:
    # YAML 1.1 reads the key `on` as True.
    return cast(dict[str, Any], document.get("on", document.get(True)))


def script(job: dict[str, Any]) -> str:
    steps = cast(list[dict[str, Any]], job["steps"])
    return "\n".join(str(step.get("run", "")) for step in steps)


def required_checks() -> set[str]:
    settings = json.loads((GITHUB / "repository-settings.json").read_text("utf-8"))
    return set(settings["branches"]["main"]["required_status_checks"])


def test_the_workflow_audit_is_required_and_its_tools_are_pinned() -> None:
    document = load(WORKFLOWS / "workflow-audit.yml")
    job = document["jobs"]["audit"]
    env = document["env"]
    run = script(job)

    assert job["name"] in required_checks()
    assert set(triggers(document)) == {"push", "pull_request", "workflow_dispatch"}
    assert re.fullmatch(r"\d+\.\d+\.\d+", env["ACTIONLINT_VERSION"])
    assert re.fullmatch(r"\d+\.\d+\.\d+", env["ZIZMOR_VERSION"])
    assert SHA256.match(env["ACTIONLINT_SHA256"]) and SHA256.match(env["ZIZMOR_SHA256"])
    assert run.count("sha256sum --check") == 2
    assert '"$RUNNER_TEMP/actionlint"' in run and '"$RUNNER_TEMP/zizmor"' in run
    zizmor = load(GITHUB / "zizmor.yml")
    assert zizmor["rules"]["unpinned-uses"]["config"]["policies"] == {"*": "hash-pin"}


def test_codeql_reads_the_workflows_as_a_required_check() -> None:
    matrix = load(WORKFLOWS / "codeql.yml")["jobs"]["analyze"]["strategy"]["matrix"]

    assert "actions" in matrix["language"]
    assert "Analyze (actions)" in required_checks()


def test_ci_audits_dev_dependencies_and_scans_images_for_secrets() -> None:
    jobs = load(WORKFLOWS / "ci.yml")["jobs"]
    security = script(jobs["security"])
    images = jobs["images"]
    trivy = [
        step
        for step in images["steps"]
        if str(step.get("uses", "")).startswith("aquasecurity/trivy-action@")
    ]

    assert "npm audit --audit-level=high" in security and "--omit=dev" not in security
    assert (
        "--require-hashes --requirement .github/tools/pip-audit/requirements.txt"
        in (security)
    )
    assert "uvx" not in security
    assert len(trivy) == 2
    assert all(step["with"]["scanners"] == "vuln,misconfig,secret" for step in trivy)
    assert images["env"]["TRIVY_IMAGE_CONFIG_SCANNERS"] == "misconfig,secret"
    secret_config = load(ROOT / images["env"]["TRIVY_SECRET_CONFIG"])
    assert {rule["id"] for rule in secret_config["allow-rules"]} == {
        "backend-python-packages",
        "cabinet-node-packages",
        "python-standard-library",
    }


def test_no_package_runs_install_scripts_and_uv_builds_nothing() -> None:
    for folder in ("web", "integrations/zapier", ".github/tools/lhci"):
        npmrc = (ROOT / folder / ".npmrc").read_text(encoding="utf-8")
        assert re.search(r"^ignore-scripts=true$", npmrc, re.MULTILINE), folder
        assert (ROOT / folder / "package-lock.json").exists(), folder
    dockerfile = (ROOT / "web" / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY package.json package-lock.json .npmrc ./" in dockerfile
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["uv"]["no-build"] is True
    lighthouse = script(load(WORKFLOWS / "lighthouse.yml")["jobs"]["lighthouse"])
    assert "npx --yes" not in lighthouse
    assert "npm ci --ignore-scripts" in lighthouse
    pip_audit = (GITHUB / "tools" / "pip-audit" / "requirements.txt").read_text("utf-8")
    pins = re.findall(r"^([a-z0-9._-]+)==\S+ \\$", pip_audit, re.MULTILINE)
    assert "pip-audit" in pins
    assert pip_audit.count("--hash=sha256:") >= len(pins)


def test_every_lockfile_is_audited_nightly_into_one_issue() -> None:
    document = load(WORKFLOWS / "dependency-audit.yml")
    job = document["jobs"]["audit"]
    run = script(job)

    assert triggers(document)["schedule"] and "workflow_dispatch" in triggers(document)
    assert job["permissions"] == {"contents": "read", "issues": "write"}
    for lockfile in (
        "uv.lock=",
        "web/package-lock.json=",
        "integrations/zapier/package-lock.json=",
    ):
        assert lockfile in run, lockfile
    assert "--require-hashes" in run and "scripts.dependency_advisories" in run
    for action in ("create)", "comment)", "close)"):
        assert action in run, action


def test_the_release_images_are_rebuilt_and_rescanned_weekly() -> None:
    document = load(WORKFLOWS / "image-rescan.yml")
    job = document["jobs"]["rescan"]
    steps = cast(list[dict[str, Any]], job["steps"])
    trivy = [s for s in steps if str(s.get("uses", "")).startswith("aquasecurity/")]

    assert triggers(document)["schedule"]
    assert any(step.get("with", {}).get("ref") == "release" for step in steps)
    assert [step["with"]["scanners"] for step in trivy] == ["vuln,misconfig,secret"] * 2
    assert "scripts.image_age_report" in script(job)


def test_production_is_checked_hourly_and_unconfigured_runs_fail() -> None:
    document = load(WORKFLOWS / "synthetics.yml")
    job = document["jobs"]["check"]
    first = job["steps"][0]
    run = script(job)

    assert triggers(document)["schedule"] == [{"cron": "41 * * * *"}]
    assert first["env"]["PRODUCTION_URL"] == "${{ vars.PRODUCTION_URL }}"
    assert "exit 1" in str(first["run"]) and "::error::" in str(first["run"])
    assert 'scripts/smoke.sh "$PRODUCTION_URL"' in run
    assert "scripts.synthetic_booking" in run
    assert document["jobs"]["report"]["permissions"] == {"issues": "write"}


def tracked_files() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return listed.stdout.splitlines()


def test_high_risk_paths_are_labelled_and_every_pattern_matches() -> None:
    labeler = load(GITHUB / "labeler.yml")
    [rule] = labeler["risk:high"]
    patterns: list[str] = rule["changed-files"][0]["any-glob-to-any-file"]
    files = tracked_files()
    workflow = load(WORKFLOWS / "risk-labels.yml")
    job = workflow["jobs"]["label"]

    assert set(labeler) == {"risk:high"}
    for pattern in patterns:
        assert any(fnmatch.fnmatch(path, pattern) for path in files), pattern
    for boundary in (
        "app/gateways/http/user_authentication.py",
        "app/adapters/payments/**",
        "app/gateways/http/webhook_routes.py",
        "app/repositories/business_scoped_repository.py",
        "app/use_cases/conversations/tools/**",
        "app/utilities/security/**",
    ):
        assert boundary in patterns, boundary
    assert set(triggers(workflow)) == {"pull_request"}
    assert job["permissions"] == {"contents": "read", "pull-requests": "write"}
    assert str(job["steps"][0]["uses"]).startswith("actions/labeler@")
