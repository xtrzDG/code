"""
The supply-chain and settings guards exist and stay pinned: CI publishes,
attests and signs both images on main; deploy smoke verifies them before a
promotion; the ZAP baseline scans the running stack with a pinned image;
the repository settings check runs daily and expects exactly the checks
the workflows define.
"""

import itertools
import json
import re
from pathlib import Path
from typing import Any, cast

import yaml

from tests.platform.environment_sources import ROOT

WORKFLOWS: Path = ROOT / ".github" / "workflows"
SETTINGS: Path = ROOT / ".github" / "repository-settings.json"
PINNED_USES: re.Pattern[str] = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
PINNED_IMAGE: re.Pattern[str] = re.compile(r"^[\w./-]+:[\w.-]+@sha256:[0-9a-f]{64}$")
GATES: set[str] = {
    "backend-checks",
    "coverage",
    "web-checks",
    "security",
    "images",
    "e2e",
}


def workflow(name: str) -> dict[Any, Any]:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    return cast(dict[Any, Any], yaml.safe_load(text))


def is_instance(value: object, kind: type) -> bool:
    """isinstance without narrowing: YAML values stay Any for the checkers."""

    return isinstance(value, kind)


def triggers(document: dict[Any, Any]) -> dict[str, Any]:
    # YAML 1.1 reads the key `on` as True.
    return cast(dict[str, Any], document.get("on", document.get(True)))


def steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], job["steps"])


def uses(job: dict[str, Any], action: str) -> list[dict[str, Any]]:
    found = [
        step
        for step in steps(job)
        if str(step.get("uses", "")).startswith(f"{action}@")
    ]
    assert all(PINNED_USES.match(str(step["uses"])) for step in found), action
    return found


def scripts(job: dict[str, Any]) -> str:
    return "\n".join(str(step.get("run", "")) for step in steps(job))


def test_ci_publishes_attests_and_signs_both_images_on_main_only() -> None:
    job = workflow("ci.yml")["jobs"]["publish-images"]

    assert set(job["needs"]) >= GATES
    assert job["if"] == (
        "github.ref == 'refs/heads/main' && (github.event_name == 'push'"
        " || github.event_name == 'workflow_dispatch')"
    )
    assert job["permissions"]["id-token"] == "write"
    assert job["permissions"]["attestations"] == "write"
    assert job["permissions"]["packages"] == "write"
    provenance = uses(job, "actions/attest-build-provenance")
    assert [step["with"]["subject-name"] for step in provenance] == [
        "${{ steps.push.outputs.backend-name }}",
        "${{ steps.push.outputs.web-name }}",
    ]
    assert all(step["with"]["push-to-registry"] is True for step in provenance)
    assert len(uses(job, "sigstore/cosign-installer")) == 1
    run = scripts(job)
    assert 'cosign sign --yes "$reference"' in run
    assert "imagetools inspect" in run and '"$name:$GITHUB_SHA"' in run
    assert 'scripts/verify_images.sh "$GITHUB_SHA"' in run
    # The images published are the ones the `images` job built and scanned.
    assert any(
        step.get("with", {}).get("name") == "scanned-images" for step in steps(job)
    )


def test_deploy_smoke_verifies_the_deployed_commit_before_promoting() -> None:
    jobs = workflow("deploy-smoke.yml")["jobs"]
    images = jobs["images"]

    assert images["needs"] == "target"
    assert images["permissions"] == {
        "contents": "read",
        "packages": "read",
        "attestations": "read",
    }
    assert len(uses(images, "sigstore/cosign-installer")) == 1
    assert 'scripts/verify_images.sh "$SHA"' in scripts(images)
    assert "images" in jobs["promote"]["needs"]


def test_the_dast_baseline_scans_the_running_stack_with_a_pinned_image() -> None:
    document = workflow("zap.yml")
    on = triggers(document)
    job = document["jobs"]["baseline"]
    run = scripts(job)

    assert on["push"] == {"branches": ["main"]}
    assert on["schedule"] and "workflow_dispatch" in on
    assert PINNED_IMAGE.match(str(document["env"]["ZAP_IMAGE"]))
    assert (
        document["env"]["COMPOSE_FILE"]
        == "docker-compose.yml:.zap/docker-compose.zap.yml"
    )
    assert all(
        PINNED_USES.match(str(step["uses"])) for step in steps(job) if "uses" in step
    )
    for target in [
        "http://localhost:3000/ ",
        '"http://localhost:3000/c/$SLUG"',
        "/widget/demo?business_id=$BUSINESS_ID",
        "api-definition.json -f openapi",
    ]:
        assert target in run, target
    assert "seed-load" in run and "::add-mask::" in run
    gate = next(
        step for step in steps(job) if "scripts.zap_gate" in str(step.get("run", ""))
    )
    assert "--rules .zap/rules.tsv" in str(gate["run"])
    assert "steps.seed.outcome == 'success'" in str(gate["if"])
    assert job["timeout-minutes"] <= 45


def test_the_settings_check_runs_daily_with_a_read_only_token() -> None:
    document = workflow("repo-settings.yml")
    on = triggers(document)
    job = document["jobs"]["check"]
    read_step = next(
        step for step in steps(job) if "gh api" in str(step.get("run", ""))
    )
    run = str(read_step["run"])

    assert on["schedule"] and "workflow_dispatch" in on
    assert document["permissions"] == {"contents": "read"}
    assert "permissions" not in job
    assert read_step["env"]["GH_TOKEN"] == "${{ secrets.REPO_SETTINGS_TOKEN }}"
    assert '[ -z "$GH_TOKEN" ]' in run
    for endpoint in [
        "branches/$branch/protection",
        "rules/branches/$branch",
        "private-vulnerability-reporting",
        "automated-security-fixes",
    ]:
        assert endpoint in run, endpoint
    for name in ["protection-$branch", "rules-$branch", "reporting", "security-fixes"]:
        assert f'fetch "{name}"' in run or f"fetch {name} " in run, name
    assert "scripts.check_repository_settings" in scripts(job)
    assert all(
        PINNED_USES.match(str(step["uses"])) for step in steps(job) if "uses" in step
    )


def rendered_names(job_id: str, job: dict[str, Any]) -> set[str]:
    """A job's check names: its name with each value of a one-list matrix."""

    name = str(job.get("name", job_id))
    matrix = cast(dict[str, Any], job.get("strategy", {}).get("matrix", {}))
    lists: dict[str, list[Any]] = {
        str(key): cast(list[Any], value)
        for key, value in matrix.items()
        if is_instance(value, list)
    }
    names: set[str] = set()
    for values in itertools.product(*lists.values()):
        rendered = name
        for key, value in zip(lists, values, strict=True):
            rendered = rendered.replace(f"${{{{ matrix.{key} }}}}", str(value))
        names.add(rendered)
    return {each for each in names if "${{" not in each}


def runs_on_every_pull_request(document: dict[Any, Any]) -> bool:
    pull_request = triggers(document).get("pull_request", False)
    if pull_request is None:
        return True
    filters = {"paths", "branches", "paths-ignore"}
    return is_instance(pull_request, dict) and not filters & set(
        cast(dict[str, Any], pull_request)
    )


def test_the_required_checks_are_jobs_every_pull_request_runs() -> None:
    expected = json.loads(SETTINGS.read_text(encoding="utf-8"))
    main = expected["branches"]["main"]
    checks: set[str] = set()
    for path in sorted(WORKFLOWS.glob("*.yml")):
        document = workflow(path.name)
        if runs_on_every_pull_request(document):
            for job_id, job in cast(dict[str, Any], document["jobs"]).items():
                checks |= rendered_names(job_id, cast(dict[str, Any], job))

    assert set(main["required_status_checks"]) <= checks
    assert "CI passed (every gate)" in main["required_status_checks"]
    assert (
        main["pull_request_required"]
        and main["force_pushes_blocked"]
        and main["deletions_blocked"]
    )
    assert expected["private_vulnerability_reporting"] is True
    assert expected["dependabot_security_updates"] is True
