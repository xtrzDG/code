"""
The supply-chain records of a release (SDLC-01, SDLC-02): CI writes a
CycloneDX SBOM of both images and, on main, attests it to each published
image next to its provenance; every pull request goes through the
dependency review, which fails on a high advisory or a denied licence.
"""

from pathlib import Path
from typing import Any, cast

import yaml

from tests.platform.environment_sources import ROOT
from tests.platform.test_supply_chain_workflows import steps, uses, workflow

REVIEW_CONFIG: Path = ROOT / ".github" / "dependency-review-config.yml"
PR_TEMPLATE: Path = ROOT / ".github" / "pull_request_template.md"
IMAGES: tuple[str, ...] = ("backend", "web")


def review_config() -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(REVIEW_CONFIG.read_text("utf-8")))


def test_both_images_get_a_cyclonedx_sbom_kept_for_publishing() -> None:
    job = workflow("ci.yml")["jobs"]["images"]
    sboms = uses(job, "anchore/sbom-action")
    [upload] = [
        step
        for step in steps(job)
        if step.get("with", {}).get("name") == "scanned-images"
    ]

    assert [step["with"]["format"] for step in sboms] == ["cyclonedx-json"] * 2
    assert [step["with"]["output-file"] for step in sboms] == [
        f"${{{{ runner.temp }}}}/sbom-{image}.cdx.json" for image in IMAGES
    ]
    for image in IMAGES:
        assert f"${{{{ runner.temp }}}}/sbom-{image}.cdx.json" in upload["with"]["path"]


def test_each_published_image_carries_its_sbom_attestation() -> None:
    job = workflow("ci.yml")["jobs"]["publish-images"]
    attestations = uses(job, "actions/attest")

    assert [step["with"]["subject-name"] for step in attestations] == [
        f"${{{{ steps.push.outputs.{image}-name }}}}" for image in IMAGES
    ]
    assert [step["with"]["subject-digest"] for step in attestations] == [
        f"${{{{ steps.push.outputs.{image}-digest }}}}" for image in IMAGES
    ]
    assert [step["with"]["sbom-path"] for step in attestations] == [
        f"${{{{ runner.temp }}}}/scanned-images/sbom-{image}.cdx.json"
        for image in IMAGES
    ]
    assert all(step["with"]["push-to-registry"] is True for step in attestations)
    assert job["permissions"]["attestations"] == "write"


def test_every_pull_request_goes_through_the_dependency_review() -> None:
    job = workflow("ci.yml")["jobs"]["security"]
    [review] = uses(job, "actions/dependency-review-action")

    assert review["if"] == "github.event_name == 'pull_request'"
    assert review["with"]["config-file"] == "./.github/dependency-review-config.yml"
    assert "security" in workflow("ci.yml")["jobs"]["ci-passed"]["needs"]


def test_the_review_fails_on_high_advisories_and_denied_licences() -> None:
    config = review_config()

    assert config["fail-on-severity"] == "high"
    assert config["vulnerability-check"] is True
    assert config["license-check"] is True
    assert {"runtime", "development"} <= set(config["fail-on-scopes"])
    assert {"AGPL-3.0-only", "AGPL-3.0-or-later", "GPL-3.0-only", "SSPL-1.0"} <= set(
        config["deny-licenses"]
    )
    assert "allow-licenses" not in config
    for exception in config.get("allow-dependencies-licenses", []):
        name = str(exception).rsplit("/", 1)[-1]
        assert f"# - {name} " in REVIEW_CONFIG.read_text("utf-8"), exception


def test_the_pull_request_template_asks_about_a_new_dependency() -> None:
    template = PR_TEMPLATE.read_text("utf-8")

    assert "- [ ] **Dependencies:**" in template
    for question in ("maintained", "typosquats", "licence", "install scripts"):
        assert question in template
