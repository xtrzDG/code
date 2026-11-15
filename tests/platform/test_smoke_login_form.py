"""scripts/smoke.sh: the cabinet's sign-in page opens on the right form.

The cabinet's server reads the API's sign-in options while it renders
`/login` and puts their form into the first HTML
(web/src/app/login/_lib/openingMethod.ts): e-mail where login codes go by
e-mail only, phone otherwise and whenever that read fails. The form names
its method (`data-login-method`).
"""

import pytest

from tests.platform.smoke_run import needs_smoke_tools, run_smoke
from tests.platform.smoke_server import FakeDeployment, login_page, running_deployment

pytestmark = needs_smoke_tools


@pytest.mark.parametrize(
    ("deployment", "line"),
    [
        (FakeDeployment(), "ok    cabinet /login opens on the e-mail form"),
        # The options may leave the field out: e-mail is offered then.
        (
            FakeDeployment(is_email_login_available=None),
            "ok    cabinet /login opens on the e-mail form",
        ),
        (
            FakeDeployment(
                configured_channels=["sms", "email"], login_page=login_page("phone")
            ),
            "ok    cabinet /login opens on the phone form",
        ),
        # A phone provider and no e-mail provider.
        (
            FakeDeployment(
                configured_channels=["sms"],
                is_email_login_available=False,
                login_page=login_page("phone"),
            ),
            "ok    cabinet /login opens on the phone form",
        ),
    ],
)
def test_a_page_on_the_form_the_options_call_for_passes(
    deployment: FakeDeployment, line: str
) -> None:
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet")

    assert result.returncode == 0, result.stdout + result.stderr
    assert line in result.stdout.splitlines()
    assert deployment.login_reads == 1


def test_a_page_on_phone_where_codes_go_by_e_mail_only_fails_after_three_reads() -> (
    None
):
    deployment = FakeDeployment(login_page=login_page("phone"))
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet")

    assert result.returncode == 1
    assert (
        "FAIL  cabinet /login opens on the phone form, the sign-in options call"
        " for the e-mail form (a cabinet that cannot read its API, BACKEND_URL,"
        " opens on phone)"
    ) in result.stderr
    assert deployment.login_reads == 3
    # The page is not copied into the log.
    assert "response:" not in result.stderr
    assert "ok    cabinet /login opens" not in result.stdout


def test_a_page_whose_read_of_the_options_was_slow_once_is_read_again() -> None:
    deployment = FakeDeployment(first_login_answers=[(200, login_page("phone"))])
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok    cabinet /login opens on the e-mail form" in result.stdout
    assert deployment.login_reads == 2
    # The checks after it read the page that was fetched last.
    assert "ok    cabinet hides /.git/HEAD and its source maps" in result.stdout


def test_a_page_that_stops_answering_while_it_is_read_again_fails() -> None:
    deployment = FakeDeployment(
        first_login_answers=[(200, login_page("phone")), (503, "unavailable")]
    )
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet")

    assert result.returncode == 1
    assert "/cabinet/login answered 503" in result.stderr
    assert deployment.login_reads == 2


def test_a_page_on_e_mail_where_a_phone_channel_delivers_fails_at_once() -> None:
    deployment = FakeDeployment(configured_channels=["sms", "email"])
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet")

    assert result.returncode == 1
    assert (
        "cabinet /login opens on the e-mail form, the sign-in options call for"
        " the phone form"
    ) in result.stderr
    # Only a page on phone can come from one slow read: nothing is read again.
    assert deployment.login_reads == 1


def test_a_release_whose_page_names_no_form_is_skipped_not_failed() -> None:
    deployment = FakeDeployment(login_page=login_page(None))
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        "skip  the form of cabinet /login (a release whose page does not name it)"
        in result.stdout.splitlines()
    )
    assert "cabinet /login opens on" not in result.stdout


def test_without_a_cabinet_the_form_is_not_looked_at() -> None:
    deployment = FakeDeployment(login_page=login_page("phone"))
    with running_deployment(deployment) as url:
        result = run_smoke(url)

    assert result.returncode == 0, result.stdout + result.stderr
    assert deployment.login_reads == 0
