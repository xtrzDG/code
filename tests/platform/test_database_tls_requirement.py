"""
Production refuses a database address that does not require TLS (SEC-06):
its own sslmode, else PGSSLMODE, must be require, verify-ca or
verify-full; development and the preview stand never ask.
"""

import pytest

from app.schemas.constants.storage import DatabaseSslMode
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.config_helpers.production.database_tls_requirements import (
    CLEAR_TEXT_SSL_MODES,
    ENCRYPTED_SSL_MODES,
    is_tls_required,
    named_ssl_mode_text,
)
from app.utilities.config_helpers.production.production_problems import (
    find_production_problems,
    require_production_settings,
)
from tests.platform.production_settings import problems_with

PLAIN: str = "postgresql://workshop:fake-password@db.internal:5432/workshop"
ADDRESS_VARIABLES: tuple[str, ...] = (
    "DATABASE_URL",
    "DATABASE_URL_TENANT",
    "DATABASE_URL_PLATFORM",
)


def test_pgsslmode_require_covers_addresses_that_name_no_mode() -> None:
    assert problems_with({}) == []


@pytest.mark.parametrize("mode", [None, "disable", "allow", "prefer"])
def test_without_a_tls_default_every_address_is_named(mode: str | None) -> None:
    problems = problems_with({"PGSSLMODE": mode})

    assert [problem.split(" ", 1)[0] for problem in problems] == list(ADDRESS_VARIABLES)
    assert all("does not require TLS" in problem for problem in problems)


@pytest.mark.parametrize("variable", ADDRESS_VARIABLES)
@pytest.mark.parametrize("mode", ["require", "verify-ca", "verify-full"])
def test_an_address_that_requires_tls_passes_without_pgsslmode(
    variable: str, mode: str
) -> None:
    changes: dict[str, str | None] = {
        name: f"{PLAIN}?sslmode={mode}" for name in ADDRESS_VARIABLES
    }
    changes["PGSSLMODE"] = None

    assert problems_with(changes) == []


@pytest.mark.parametrize("weaker", ["disable", "allow", "prefer", "required", ""])
def test_a_weaker_mode_in_the_address_wins_over_pgsslmode(weaker: str) -> None:
    [problem] = problems_with(
        {"DATABASE_URL_TENANT": f"{PLAIN}?connect_timeout=5&sslmode={weaker}"}
    )

    assert problem.startswith("DATABASE_URL_TENANT does not require TLS")


def test_the_live_events_address_is_checked_too() -> None:
    [problem] = problems_with({"LIVE_EVENTS_DATABASE_URL": f"{PLAIN}?sslmode=disable"})

    assert problem.startswith("LIVE_EVENTS_DATABASE_URL does not require TLS")


def test_the_refusal_never_shows_the_address() -> None:
    problems = problems_with({"DATABASE_URL": f"{PLAIN}?sslmode=disable"})

    assert problems
    assert all("fake-password" not in problem for problem in problems)
    assert all("db.internal" not in problem for problem in problems)


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        (PLAIN, None),
        (f"{PLAIN}?sslmode=require", "require"),
        (f"{PLAIN}?sslmode=disable&sslmode=verify-full", "verify-full"),
        ("postgres://u@h/d?application_name=x&sslmode=prefer", "prefer"),
        ("host=db.internal dbname=workshop sslmode=verify-full", "verify-full"),
        ("host=db.internal sslmode = 'require' user=u", "require"),
        ("host=db.internal dbname=workshop", None),
    ],
)
def test_the_named_mode_is_read_as_libpq_reads_it(
    address: str, expected: str | None
) -> None:
    assert named_ssl_mode_text(DatabaseUrl(address)) == expected


def test_an_unreadable_uri_is_never_accepted() -> None:
    address = DatabaseUrl("postgresql://u:p@[::1/d?sslmode=require")

    assert is_tls_required(address, DatabaseSslMode.REQUIRE) is False


def test_an_unknown_pgsslmode_fails_the_start_naming_it() -> None:
    with pytest.raises(ValidationFailedError, match="PGSSLMODE"):
        problems_with({"PGSSLMODE": "on"})


def test_development_never_asks_for_tls() -> None:
    # docker-compose.yml's database talks plain TCP on its private network.
    settings = assemble_app_settings(
        {
            "APP_ENV": "development",
            "LLM_PROVIDER": "scripted",
            "DATABASE_URL": PLAIN,
        }
    )
    problems = find_production_problems(settings)

    assert any(str(problem).startswith("DATABASE_URL does not") for problem in problems)
    require_production_settings(settings, problems)


def test_every_ssl_mode_is_either_encrypted_or_clear_text() -> None:
    assert ENCRYPTED_SSL_MODES.isdisjoint(CLEAR_TEXT_SSL_MODES)
    assert set(DatabaseSslMode) == ENCRYPTED_SSL_MODES | CLEAR_TEXT_SSL_MODES
    for mode in DatabaseSslMode:
        address = DatabaseUrl(f"{PLAIN}?sslmode={mode.value}")
        assert is_tls_required(address, None) is (mode in ENCRYPTED_SSL_MODES)


@pytest.mark.parametrize(
    "address",
    [
        "postgresql://workshop:fake-password@dpg-cr0abc123def456-a/workshop",
        "postgres://workshop:fake-password@dpg-cr0abc123def456-a:5432/workshop",
        "postgresql://workshop:fake-password@postgres/workshop?sslmode=disable",
    ],
)
def test_an_internal_private_network_address_needs_no_tls(address: str) -> None:
    changes: dict[str, str | None] = {name: address for name in ADDRESS_VARIABLES}
    changes["PGSSLMODE"] = None

    assert problems_with(changes) == []


@pytest.mark.parametrize(
    "host",
    [
        "dpg-cr0abc123def456-a.frankfurt-postgres.render.com",
        "10.0.0.5",
        "[::1]",
    ],
)
def test_a_dotted_or_ip_host_still_needs_tls(host: str) -> None:
    [problem] = problems_with(
        {
            "PGSSLMODE": None,
            "DATABASE_URL": f"postgresql://workshop:fake-password@{host}/workshop",
            "DATABASE_URL_TENANT": f"{PLAIN}?sslmode=require",
            "DATABASE_URL_PLATFORM": f"{PLAIN}?sslmode=require",
        }
    )

    assert problem.startswith("DATABASE_URL does not require TLS")
