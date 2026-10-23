"""
scripts/verify_images.sh against stand-ins of docker, cosign and gh: every
check is made against the digest the tag resolves to, with the identity of
ci.yml on refs/heads/main and the exact commit, and any gap fails.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.platform.environment_sources import ROOT

SCRIPT: str = str(ROOT / "scripts" / "verify_images.sh")
SHA: str = "0123456789abcdef0123456789abcdef01234567"
DIGESTS: dict[str, str] = {"backend": "sha256:" + "a" * 64, "web": "sha256:" + "b" * 64}
# A stand-in tool: records its arguments, then fails when its name and the
# image are listed in STUB_FAIL ("cosign:web docker:backend").
STUB: str = """#!/usr/bin/env bash
tool="$(basename "$0")"
echo "$tool $*" >> "$STUB_LOG"
for failing in $STUB_FAIL; do
  case "$tool:$*" in
    "${failing%%:*}:"*"assistant-workshop-${failing#*:}"*) exit 1 ;;
  esac
done
if [ "$tool" = docker ]; then
  case "$*" in
    *assistant-workshop-backend:*) echo "sha256:BACKEND" ;;
    *assistant-workshop-web:*) echo "sha256:WEB" ;;
  esac
fi
"""

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None, reason="the script needs bash"
)


def install_stubs(directory: Path) -> Path:
    directory.mkdir()
    body: str = STUB.replace("sha256:BACKEND", DIGESTS["backend"]).replace(
        "sha256:WEB", DIGESTS["web"]
    )
    for tool in ("docker", "cosign", "gh"):
        stub: Path = directory / tool
        stub.write_text(body, encoding="utf-8")
        stub.chmod(0o755)
    return directory


def run_verify(
    tmp_path: Path,
    *arguments: str,
    failing: str = "",
    repository: str | None = "XtrzDG/code",
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    stubs: Path = install_stubs(tmp_path / "bin")
    log: Path = tmp_path / "calls.log"
    log.touch()
    environment: dict[str, str] = {
        "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}",
        "STUB_LOG": str(log),
        "STUB_FAIL": failing,
    }
    if repository is not None:
        environment["GITHUB_REPOSITORY"] = repository
    result = subprocess.run(
        ["bash", SCRIPT, *arguments],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return result, log.read_text(encoding="utf-8").splitlines()


def test_both_images_pass_when_signed_and_attested_by_ci_on_main(
    tmp_path: Path,
) -> None:
    result, calls = run_verify(tmp_path, SHA)

    assert result.returncode == 0, result.stdout + result.stderr
    backend = f"ghcr.io/xtrzdg/assistant-workshop-backend@{DIGESTS['backend']}"
    web = f"ghcr.io/xtrzdg/assistant-workshop-web@{DIGESTS['web']}"
    assert result.stdout.splitlines() == [
        f"ok    signature   {backend}",
        f"ok    provenance  {backend}",
        f"ok    signature   {web}",
        f"ok    provenance  {web}",
        f"Both images of {SHA} were built, attested and signed by CI on main.",
    ]
    lookups = [call for call in calls if call.startswith("docker ")]
    assert lookups == [
        f"docker buildx imagetools inspect ghcr.io/xtrzdg/assistant-workshop-{image}:{SHA}"
        " --format {{.Manifest.Digest}}"
        for image in ("backend", "web")
    ]


def test_the_signature_must_name_ci_on_main_and_the_exact_commit(
    tmp_path: Path,
) -> None:
    _, calls = run_verify(tmp_path, SHA)

    (cosign, _) = [call for call in calls if call.startswith("cosign ")]
    assert cosign.split() == [
        "cosign",
        "verify",
        f"ghcr.io/xtrzdg/assistant-workshop-backend@{DIGESTS['backend']}",
        "--certificate-oidc-issuer",
        "https://token.actions.githubusercontent.com",
        "--certificate-identity",
        "https://github.com/XtrzDG/code/.github/workflows/ci.yml@refs/heads/main",
        "--certificate-github-workflow-repository",
        "XtrzDG/code",
        "--certificate-github-workflow-ref",
        "refs/heads/main",
        "--certificate-github-workflow-sha",
        SHA,
    ]


def test_the_provenance_must_come_from_ci_on_main_for_the_exact_commit(
    tmp_path: Path,
) -> None:
    _, calls = run_verify(tmp_path, SHA)

    (_, attestation) = [call for call in calls if call.startswith("gh ")]
    assert attestation.split() == [
        "gh",
        "attestation",
        "verify",
        f"oci://ghcr.io/xtrzdg/assistant-workshop-web@{DIGESTS['web']}",
        "--repo",
        "XtrzDG/code",
        "--signer-workflow",
        "XtrzDG/code/.github/workflows/ci.yml",
        "--source-ref",
        "refs/heads/main",
        "--source-digest",
        SHA,
        "--deny-self-hosted-runners",
    ]


@pytest.mark.parametrize(
    ("failing", "expected"),
    [
        ("cosign:web", "FAIL  signature   ghcr.io/xtrzdg/assistant-workshop-web@"),
        ("gh:backend", "FAIL  provenance  ghcr.io/xtrzdg/assistant-workshop-backend@"),
        ("docker:web", "FAIL  ghcr.io/xtrzdg/assistant-workshop-web:" + SHA),
    ],
)
def test_any_missing_signature_provenance_or_image_fails(
    tmp_path: Path, failing: str, expected: str
) -> None:
    result, calls = run_verify(tmp_path, SHA, failing=failing)

    assert result.returncode == 1
    assert any(line.startswith(expected) for line in result.stdout.splitlines())
    assert "cannot be traced to a reviewed commit" in result.stderr
    # One failure never hides the other image's checks.
    assert len([call for call in calls if call.startswith("docker ")]) == 2


def test_an_image_missing_from_the_registry_is_not_verified_by_tag(
    tmp_path: Path,
) -> None:
    _, calls = run_verify(tmp_path, SHA, failing="docker:backend")

    assert not any("assistant-workshop-backend" in call for call in calls[1:])


@pytest.mark.parametrize(
    ("arguments", "repository"),
    [
        ((), "XtrzDG/code"),
        (("0123abc",), "XtrzDG/code"),
        ((SHA.upper(),), "XtrzDG/code"),
        ((SHA, SHA), "XtrzDG/code"),
        ((SHA,), None),
        ((SHA,), "not a repository"),
    ],
)
def test_wrong_usage_exits_2_without_checking_anything(
    tmp_path: Path, arguments: tuple[str, ...], repository: str | None
) -> None:
    result, calls = run_verify(tmp_path, *arguments, repository=repository)

    assert result.returncode == 2
    assert calls == []
    assert result.stderr.strip() != ""
