"""scripts/smoke.sh: the cabinet's sign-in page opens on the right form.

The cabinet's server reads the API's sign-in options while it renders
`/login` and puts their form into the first HTML
(web/src/app/login/_lib/openingMethod.ts): e-mail where login codes go by
e-mail only, phone otherwise and whenever that read fails. The form names
its method (`data-login-method`).
"""

import time

import pytest

from tests.platform.smoke_run import needs_smoke_tools, run_smoke
from tests.platform.smoke_server import (
    CUT_OFF,
    NO_ANSWER,
    FakeDeployment,
    login_page,
    running_deployment,
)

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
        # Every phone channel counts, not SMS alone.
        (
            FakeDeployment(
                configured_channels=["whatsapp"], login_page=login_page("phone")
            ),
            "ok    cabinet /login opens on the phone form",
        ),
        (
            FakeDeployment(
                configured_channels=["telegram", "email"],
                login_page=login_page("phone"),
            ),
            "ok    cabinet /login opens on the phone form",
        ),
        # E-mail configured but not delivering: the page opens on phone.
        (
            FakeDeployment(
                is_email_login_available=False, login_page=login_page("phone")
            ),
            "ok    cabinet /login opens on the phone form",
        ),
        # A flag that is no boolean counts as the cabinet's JavaScript reads it.
        (
            FakeDeployment(is_email_login_available=[]),
            "ok    cabinet /login opens on the e-mail form",
        ),
        (
            FakeDeployment(is_email_login_available=0, login_page=login_page("phone")),
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
        "FAIL  cabinet /login opens on the phone form in 3 reads, the sign-in"
        " options call for the e-mail form: the cabinet's server did not read"
        " them within two seconds (its BACKEND_URL, a slow API or the API's"
        " request limit)"
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
    # A pass after a read again leaves a trace.
    assert "note  cabinet /login opened on phone in 1 of 2 reads" in result.stdout
    assert deployment.login_reads == 2
    # The checks after it read the page that was fetched last.
    assert "ok    cabinet hides /.git/HEAD and its source maps" in result.stdout


def test_the_reads_wait_for_each_other() -> None:
    deployment = FakeDeployment(login_page=login_page("phone"))
    started = time.monotonic()
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet", login_read_pause="1")

    assert result.returncode == 1
    assert deployment.login_reads == 3
    # Two pauses of one second between three reads (a lower bound cannot flake).
    assert time.monotonic() - started >= 2


@pytest.mark.parametrize(
    ("later_answer", "causes"),
    [
        ((NO_ANSWER, ""), ["curl: (52)"]),
        ((CUT_OFF, login_page("email")), ["curl: (18)", "(after status 200)"]),
    ],
)
def test_a_read_again_that_gets_no_whole_answer_fails_without_the_old_page(
    later_answer: tuple[int, str], causes: list[str]
) -> None:
    deployment = FakeDeployment(
        first_login_answers=[(200, login_page("phone")), later_answer]
    )
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet")

    assert result.returncode == 1
    assert "/cabinet/login answered 000" in result.stderr
    # The line under it says why.
    assert all(cause in result.stderr for cause in causes), result.stderr
    # The first read's page is not printed as this read's answer.
    assert "data-login-method" not in result.stderr


def test_a_first_read_that_is_cut_off_fails() -> None:
    deployment = FakeDeployment(first_login_answers=[(CUT_OFF, login_page("email"))])
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet")

    assert result.returncode == 1
    assert "GET " in result.stderr
    assert "/cabinet/login answered 000" in result.stderr
    assert "(after status 200)" in result.stderr


def test_a_page_on_phone_and_then_on_no_form_fails() -> None:
    deployment = FakeDeployment(
        first_login_answers=[(200, login_page("phone")), (200, login_page(None))]
    )
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet")

    assert result.returncode == 1
    assert (
        "cabinet /login opened on phone, then named no form: a page from another"
        " release or cut off"
    ) in result.stderr
    assert "skip  the form" not in result.stdout


def test_a_page_that_names_an_unknown_form_fails_at_once() -> None:
    deployment = FakeDeployment(login_page=login_page("passkey"))
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet")

    assert result.returncode == 1
    assert "cabinet /login opens on the passkey form" in result.stderr
    assert deployment.login_reads == 1


@pytest.mark.parametrize(
    "quote",
    [
        '<script>self.x={"data-login-method":"email"};'
        ' /* data-login-method="email" */</script>',
        "<script>document.write('<form data-login-method=\"email\">')</script>",
        '<!-- <form data-login-method="email"> -->',
        '<template><form data-login-method="email">login</form></template>',
        # A form of the page that names no method is passed over.
        '<form action="/search">search</form>',
    ],
)
def test_only_the_page_s_own_form_element_names_the_form(quote: str) -> None:
    page = (
        '<html><head><script src="/_next/static/chunks/main-app-4f1c.js?dpl=1"'
        f" async></script></head><body>{quote}"
        '<form novalidate="" data-login-method="phone">login</form></body></html>'
    )
    deployment = FakeDeployment(login_page=page)
    with running_deployment(deployment) as url:
        result = run_smoke(url, f"{url}/cabinet")

    # The form says phone, the options e-mail: the quote before it does not count.
    assert result.returncode == 1
    assert "opens on the phone form in 3 reads" in result.stderr


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
        " the phone form: the cabinet reads another API than"
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
