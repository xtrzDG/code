"""
Production talks to Postgres over TLS only (SEC-06): every database
address it connects with (DATABASE_URL, DATABASE_URL_TENANT,
DATABASE_URL_PLATFORM, LIVE_EVENTS_DATABASE_URL) asks for
`sslmode=require`, `verify-ca` or `verify-full`, in the address itself
or, for an address that names no sslmode, in PGSSLMODE (libpq's default,
which the backup's pg_dump reads too). An address that names a weaker
mode (`disable`, `allow`, `prefer`) is refused whatever PGSSLMODE says:
libpq lets the address win. A problem names the variable, never the
address (it holds the password).

One exception: an address on the hosting platform's private network,
whose host is a single-label name (Render's internal database address
`dpg-…-a`, a compose service `postgres`), never leaves that network and
may be reached without TLS: Render's internal connections do not require
it and may not offer it, so demanding it there would stop production
from reaching its database. Every dotted host (a public or external
address) must still require TLS.
"""

import re
from urllib.parse import parse_qs, urlsplit

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.storage import DatabaseSslMode
from app.schemas.typings.platform.strings import DatabaseUrl, ProductionSettingProblem

ENCRYPTED_SSL_MODES: frozenset[DatabaseSslMode] = frozenset(
    {
        DatabaseSslMode.REQUIRE,
        DatabaseSslMode.VERIFY_CA,
        DatabaseSslMode.VERIFY_FULL,
    }
)
# The modes that may connect in clear text: refused wherever they appear.
CLEAR_TEXT_SSL_MODES: frozenset[DatabaseSslMode] = frozenset(
    {DatabaseSslMode.DISABLE, DatabaseSslMode.ALLOW, DatabaseSslMode.PREFER}
)
URI_SCHEMES: tuple[str, ...] = ("postgresql://", "postgres://")
# Query parameters by which a URI names another server than its own host
# (libpq lets them win): such an address is never treated as private.
HOST_OVERRIDE_PARAMETERS: frozenset[str] = frozenset({"host", "hostaddr"})
# `sslmode=value` in a key/value connection string (`host=db sslmode=require`).
KEYWORD_SSL_MODE: re.Pattern[str] = re.compile(
    r"(?:^|\s)sslmode\s*=\s*'?([A-Za-z-]+)'?(?:\s|$)"
)
UNREADABLE_MODE: str = "unreadable"


def find_database_tls_problems(
    settings: AppSettings,
) -> list[ProductionSettingProblem]:
    roles = settings.database_roles
    addresses: tuple[tuple[str, DatabaseUrl | None], ...] = (
        ("DATABASE_URL", settings.database_url),
        ("DATABASE_URL_TENANT", roles.tenant_url),
        ("DATABASE_URL_PLATFORM", roles.platform_url),
        ("LIVE_EVENTS_DATABASE_URL", settings.live_events_database_url),
    )
    return [
        unencrypted_address_problem(variable_name)
        for variable_name, address in addresses
        if address is not None
        and not is_private_network_address(address)
        and not is_tls_required(address, roles.default_ssl_mode)
    ]


def is_private_network_address(address: DatabaseUrl) -> bool:
    """
    Whether a URI address's host is a single-label name of the platform's
    private network (no dot, not an IP address). Key/value strings,
    unreadable addresses and a URI whose query names another server
    (`?host=`, `?hostaddr=`) are never treated as private.
    """

    text: str = str(address).strip()
    if not text.startswith(URI_SCHEMES):
        return False

    try:
        parts = urlsplit(text)
        host: str | None = parts.hostname
    except ValueError:
        return False

    named: set[str] = set(parse_qs(parts.query, keep_blank_values=True))
    if named & HOST_OVERRIDE_PARAMETERS:
        return False

    return bool(host) and "." not in str(host) and ":" not in str(host)


def is_tls_required(
    address: DatabaseUrl,
    default_ssl_mode: DatabaseSslMode | None,
) -> bool:
    """
    Whether libpq refuses to connect to `address` without TLS: its own
    sslmode, else the default one (PGSSLMODE). A mode libpq does not know
    (or a query that cannot be read) is never accepted.
    """

    named_text: str | None = named_ssl_mode_text(address)
    if named_text is None:
        return default_ssl_mode in ENCRYPTED_SSL_MODES

    try:
        named_mode = DatabaseSslMode(named_text)
    except ValueError:
        return False

    return named_mode not in CLEAR_TEXT_SSL_MODES


def named_ssl_mode_text(address: DatabaseUrl) -> str | None:
    """
    The raw sslmode a connection address names (the last one, as libpq
    takes it), in a URI's query or as a `sslmode=` keyword; None when it
    names none.
    """

    text: str = str(address).strip()
    if text.startswith(URI_SCHEMES):
        try:
            query: str = urlsplit(text).query
        except ValueError:
            return UNREADABLE_MODE
        modes: list[str] = parse_qs(query, keep_blank_values=True).get("sslmode", [])
        return modes[-1].strip() if modes else None

    matches: list[str] = KEYWORD_SSL_MODE.findall(text)
    return matches[-1] if matches else None


def unencrypted_address_problem(variable_name: str) -> ProductionSettingProblem:
    return ProductionSettingProblem(
        f"{variable_name} does not require TLS: add ?sslmode=require (or "
        "verify-full) to the address, or set PGSSLMODE=require for "
        "addresses that name no sslmode; production never talks to its "
        "database in clear text."
    )
