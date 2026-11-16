"""scripts/smoke.sh against a local stand-in of a deployment."""

import pytest

from tests.platform.smoke_run import needs_smoke_tools, run_smoke
from tests.platform.smoke_server import (
    BUSINESS_ID,
    CABINET_SCRIPT,
    REPLY,
    SECURITY_TXT,
    FakeDeployment,
    running_deployment,
)

pytestmark = needs_smoke_tools


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
    assert result.stdout.splitlines()[:10] == [
        "ok    GET /healthz",
        "ok    GET /readyz",
        "ok    GET /widget.js",
        "ok    GET /v1/auth/login-options",
        "ok    API hides /.git/HEAD /.git/config /docs /redoc /openapi.json",
        "ok    GET cabinet /login",
        "ok    cabinet /login opens on the e-mail form",
        "ok    cabinet hides /.git/HEAD and its source maps",
        "ok    GET cabinet /.well-known/security.txt",
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


@pytest.mark.parametrize(
    ("security_txt", "message"),
    [
        (
            SECURITY_TXT.replace("Contact: mailto:security@workshop.test\n", ""),
            "names no security mailbox (SECURITY_CONTACT_EMAIL)",
        ),
        (
            SECURITY_TXT.replace("Canonical: https://", "Canonical: http://"),
            "no https Canonical address (SITE_URL)",
        ),
    ],
)
def test_a_cabinet_without_its_security_contact_fails(
    security_txt: str, message: str
) -> None:
    with running_deployment(FakeDeployment(security_txt=security_txt)) as url:
        result = run_smoke(url, f"{url}/cabinet")

    assert result.returncode == 1
    assert message in result.stderr


@pytest.mark.parametrize(
    "published",
    [
        "/.git/HEAD",
        "/.git/config",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/cabinet/.git/HEAD",
        f"{CABINET_SCRIPT}.map",
    ],
)
def test_a_release_that_publishes_what_it_must_not_fails(published: str) -> None:
    deployment = FakeDeployment(published=frozenset({published}))
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet")

    assert result.returncode == 1
    assert f"{published} answered 200: a release must not publish it" in (result.stderr)
    # What leaked is never copied into the log.
    assert "refs/heads/main" not in result.stdout + result.stderr


def test_development_api_docs_may_be_allowed_but_never_git() -> None:
    docs = FakeDeployment(published=frozenset({"/docs", "/openapi.json"}))
    git = FakeDeployment(published=frozenset({"/.git/HEAD"}))
    with running_deployment(docs) as url:
        allowed = run_smoke(url, allow_api_docs="1")
    with running_deployment(git) as url:
        refused = run_smoke(url, allow_api_docs="1")

    assert allowed.returncode == 0, allowed.stdout + allowed.stderr
    assert "ok    API hides /.git/HEAD /.git/config\n" in allowed.stdout
    assert refused.returncode == 1
    assert "/.git/HEAD answered 200" in refused.stderr


def test_a_cabinet_page_without_a_script_fails() -> None:
    deployment = FakeDeployment(login_page="<html>login</html>")
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet")

    assert result.returncode == 1
    assert "cabinet /login loads no /_next/static script" in result.stderr


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
    # The whole header and nothing after it: every line a comment, the last
    # one the exit codes.
    lines = result.stderr.splitlines()
    assert all(line.startswith("#") for line in lines)
    assert lines[-1] == "# Exit codes: 0 all passed, 1 a check failed, 2 wrong usage."
    assert result.stdout == ""
