"""
Deploys happen only after green checks and a smoke test: production follows
`release`, staging follows `main`, both wait for CI, and the smoke workflow
promotes only what passed on staging (docs/operations/deploys.md).
"""

import json
import re

import pytest

from tests.platform.deployment_variables import (
    DEPLOYMENT_VARIABLES,
    PRODUCTION_REQUIRED_VARIABLES,
    REQUIRED_BACKEND_VARIABLES,
    REQUIRED_CABINET_VARIABLES,
    render_services,
)
from tests.platform.environment_sources import (
    ROOT,
    backend_variables,
    cabinet_variables,
    read,
)

SERVICE_BLOCK: re.Pattern[str] = re.compile(
    r"^  - type: (?P<kind>\w+)\n    name: (?P<name>\S+)\n(?P<body>(?:    .*\n|\n)*?)"
    r"(?=^  - |\Z)",
    re.MULTILINE,
)
ROUTES_WITHOUT_DESCRIPTION: frozenset[str] = frozenset(
    {"/healthz", "/readyz", "/widget.js"}
)


def services_of(blueprint_path: str) -> dict[str, str]:
    """`name -> settings block` of every service of a Blueprint."""

    services_text: str = read(blueprint_path).split("\nservices:\n", 1)[1]
    return {
        match.group("name"): match.group("body")
        for match in SERVICE_BLOCK.finditer(services_text + "\n")
    }


def test_production_deploys_only_checked_commits_of_release() -> None:
    services = services_of("render.yaml")

    assert set(services) == {
        "workshop-api",
        "workshop-worker",
        "workshop-batch-worker",
        "workshop-backup",
        "workshop-cabinet",
    }
    for name, body in services.items():
        assert "    branch: release\n" in body, name
        assert "    autoDeployTrigger: checksPass\n" in body, name


def test_staging_mirrors_production_on_main_with_a_real_model() -> None:
    staging = services_of("render.staging.yaml")
    blueprint: str = read("render.staging.yaml")

    assert set(staging) == {
        "workshop-staging-api",
        "workshop-staging-worker",
        "workshop-staging-cabinet",
    }
    for name, body in staging.items():
        assert "    branch: main\n" in body, name
        assert "    autoDeployTrigger: checksPass\n" in body, name
    assert set(re.findall(r"region: (\w+)", blueprint)) == {"frankfurt"}
    assert "preDeployCommand: workshop migrate" in staging["workshop-staging-api"]
    assert "healthCheckPath: /readyz" in staging["workshop-staging-api"]
    assert "maxShutdownDelaySeconds: 30" in staging["workshop-staging-api"]
    assert "maxShutdownDelaySeconds: 60" in staging["workshop-staging-worker"]
    # Production refuses the scripted model, so its rehearsal answers with
    # OpenAI (staging's own project and key).
    assert re.search(r"- key: LLM_PROVIDER\n\s+value: openai\n", blueprint)
    assert "scripted\n" not in blueprint
    assert re.search(r"- key: RECORDINGS_STORAGE\n\s+value: s3\n", blueprint)
    # Its own database and env group: nothing of production is shared.
    assert "workshop-db" not in blueprint.replace("workshop-staging-db", "")
    assert "fromGroup: workshop-backend" not in blueprint
    assert "generateValue: true" in blueprint


def test_staging_sets_known_variables_and_what_a_deployment_needs() -> None:
    known: set[str] = backend_variables() | DEPLOYMENT_VARIABLES | cabinet_variables()
    services = render_services("render.staging.yaml")
    api: set[str] = services["workshop-staging-api"]

    for name, variables in services.items():
        assert variables - known == set(), name
    assert api >= REQUIRED_BACKEND_VARIABLES | PRODUCTION_REQUIRED_VARIABLES | {"PORT"}
    assert services["workshop-staging-worker"] == api - {"PORT"}
    assert services["workshop-staging-cabinet"] >= REQUIRED_CABINET_VARIABLES | {
        "SITE_URL"
    }


@pytest.mark.parametrize("blueprint_path", ["render.yaml", "render.staging.yaml"])
def test_every_backend_service_runs_as_production_with_what_it_requires(
    blueprint_path: str,
) -> None:
    # APP_ENV comes from the env group every backend service reads, so none
    # of them falls back to development (on Render a missing APP_ENV refuses
    # to start), and each has every variable production refuses to start
    # without, as a value or for the dashboard to ask.
    blueprint: str = read(blueprint_path)
    groups: str = blueprint.split("\nenvVarGroups:\n", 1)[1].split("\nservices:\n")[0]
    services = render_services(blueprint_path)
    backend: dict[str, set[str]] = {
        name: variables
        for name, variables in services.items()
        if "-cabinet" not in name and "-backup" not in name
    }

    assert re.search(r"- key: APP_ENV\n\s+value: production\n", groups)
    assert backend
    for name, body in services_of(blueprint_path).items():
        assert ("fromGroup:" in body) == ("-cabinet" not in name), name
    for name, variables in backend.items():
        assert (
            variables >= REQUIRED_BACKEND_VARIABLES | PRODUCTION_REQUIRED_VARIABLES
        ), name
    assert (
        "workshop-cabinet" not in services or "SITE_URL" in services["workshop-cabinet"]
    )


def test_the_staging_worker_copies_the_staging_api() -> None:
    worker: str = services_of("render.staging.yaml")["workshop-staging-worker"]
    copies = re.findall(
        r"- key: ([A-Z0-9_]+)\n\s+fromService:\n\s+type: web\n\s+name: (\S+)\n"
        r"\s+envVarKey: ([A-Z0-9_]+)",
        worker,
    )

    assert len(copies) == worker.count("fromService:") > 0
    assert {(service, key) for key, service, _ in copies} == {
        ("workshop-staging-api", key) for key, _, _ in copies
    }
    assert all(key == source for key, _, source in copies)


def test_the_smoke_script_calls_only_routes_that_exist() -> None:
    script: str = read("scripts/smoke.sh")
    described: set[str] = {
        re.sub(r"\{[^}]*\}", "{}", path)
        for path in json.loads(read("web/openapi.json"))["paths"]
    }
    called: set[str] = set(re.findall(r'"\$api_url(/[\w/.-]+)"', script))
    called |= {
        f"/v1/widget/{{}}{path}"
        for path in re.findall(r'"\$widget_url(/[\w/.-]+)', script)
    }

    assert {"/healthz", "/readyz", "/widget.js", "/v1/auth/login-options"} <= called
    assert {"/v1/widget/{}/config", "/v1/widget/{}/messages"} <= called
    assert called - described - ROUTES_WITHOUT_DESCRIPTION == set()
    assert (ROOT / "scripts" / "smoke.sh").stat().st_mode & 0o111


def test_the_smoke_workflow_tests_every_deploy_and_promotes_only_staging() -> None:
    workflow: str = read(".github/workflows/deploy-smoke.yml")
    promote: str = workflow.split("\n  promote:\n", 1)[1]

    for trigger in ("deployment_status:", "workflow_dispatch:", "repository_dispatch:"):
        assert f"\n  {trigger}" in workflow, trigger
    assert "scripts/smoke.sh" in workflow
    assert "needs.target.outputs.environment == 'staging'" in promote
    assert "needs: [target, smoke, images]" in promote
    assert 'git push origin "$SHA:refs/heads/release"' in promote
    assert "--force" not in promote
    # A person approves (environment production-release) and the push uses
    # that environment's deploy key: no job's token may write the repository
    # (tests/platform/test_release_paths.py checks the approval in detail).
    assert "\n    environment: production-release\n" in promote
    assert "secrets.RELEASE_DEPLOY_KEY" in promote
    assert "contents: write" not in workflow


def test_ci_runs_the_same_smoke_test_against_the_image() -> None:
    images: str = read(".github/workflows/ci.yml").split("\n  images:\n", 1)[1]

    assert "scripts/smoke.sh http://127.0.0.1:8000" in images
    assert "for runner in migrate migrate-documents" in images


def test_the_deploy_runbook_names_only_what_exists() -> None:
    runbook: str = read("docs/operations/deploys.md")
    files: list[str] = re.findall(r"`([\w/.-]+\.(?:py|md|yml|yaml|sh))`", runbook)

    for heading in ("## The pipeline", "expand, then contract", "## Rollback"):
        assert heading in runbook
    assert "workshop migrate-documents" in runbook
    for name in files:
        assert (ROOT / name).exists(), name
    assert "docs/operations/deploys.md" in read("docs/conventions.md")
    assert "docs/operations/deploys.md" in read("docs/LAUNCH.md")
    assert "git push origin main:release" in read("docs/LAUNCH.md")
