"""
Every image a build or a workflow runs is pinned by tag and digest: the base
images of both Dockerfiles (and their BuildKit syntax image), the workflows'
service and tool images, the load test's k6. A tag can be moved to other
content by whoever publishes it; a digest cannot. Dependabot (docker,
docker-compose) moves the tag and the digest together, and the weekly
rescan reports how old the pinned bases are.
"""

import re
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

ROOT: Path = Path(__file__).resolve().parents[2]
WORKFLOWS: Path = ROOT / ".github" / "workflows"
DOCKERFILES: list[Path] = [ROOT / "Dockerfile", ROOT / "web" / "Dockerfile"]
PINNED: re.Pattern[str] = re.compile(r"^[\w./-]+:[\w.-]+@sha256:[0-9a-f]{64}$")
FROM_LINE: re.Pattern[str] = re.compile(r"^FROM\s+(?P<image>\S+)(?:\s+AS\s+\S+)?$")


@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=lambda path: path.parent.name)
def test_dockerfile_bases_are_pinned_by_digest(dockerfile: Path) -> None:
    lines = dockerfile.read_text(encoding="utf-8").splitlines()
    stages: set[str] = set()
    unpinned: list[str] = []
    for line in lines:
        match = FROM_LINE.match(line.strip())
        if match is None:
            continue
        image = match.group("image")
        if image not in stages and not PINNED.match(image):
            unpinned.append(line)
        stages.add(line.split()[-1])

    syntax = lines[0].removeprefix("# syntax=")
    assert lines[0].startswith("# syntax=") and PINNED.match(syntax), lines[0]
    assert unpinned == []


def workflow_images() -> list[tuple[str, str]]:
    images: list[tuple[str, str]] = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        document = cast(dict[str, Any], yaml.safe_load(path.read_text("utf-8")))
        for name, value in cast(dict[str, Any], document.get("env", {})).items():
            if str(name).endswith("_IMAGE"):
                images.append((f"{path.name}: env {name}", str(value)))
        for job_name, job in cast(dict[str, dict[str, Any]], document["jobs"]).items():
            container = job.get("container")
            if container is not None:
                image = container if isinstance(container, str) else container["image"]
                images.append((f"{path.name}: {job_name} container", str(image)))
            services = cast(dict[str, dict[str, Any]], job.get("services", {}))
            for service, body in services.items():
                images.append(
                    (f"{path.name}: {job_name}/{service}", str(body["image"]))
                )
    return images


def test_workflow_images_are_pinned_by_digest() -> None:
    images = workflow_images()
    unpinned = [
        f"{where}: {image}" for where, image in images if not PINNED.match(image)
    ]

    assert len(images) >= 3
    assert unpinned == []


def test_the_load_tests_k6_is_pinned_by_digest() -> None:
    compose = cast(
        dict[str, Any],
        yaml.safe_load(
            (ROOT / "perf" / "docker-compose.perf.yml").read_text(encoding="utf-8")
        ),
    )

    assert PINNED.match(str(compose["services"]["k6"]["image"]))
