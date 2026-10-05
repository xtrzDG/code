"""
The websites allowed to show a business's chat: an owner's addresses as
origins, the origin a widget request came from, and whether it may.

A site matches with or without "www." and whatever its scheme (the http and
https pages of one host are one site); an origin with a port matches only
that port. The cabinet's own origins (the hosted chat page and the live
preview) and the API's (the widget demo page) always may; a request without
Origin and Referer is no web page embedding the chat (a server, a script:
the per-address limits bound those) and passes too.
"""

from collections.abc import Iterable
from urllib.parse import SplitResult, urlsplit

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.spend.constrained_strings import (
    WidgetPageOrigin,
    WidgetSiteAddress,
)

DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}
WWW_PREFIX: str = "www."
NULL_ORIGIN: str = "null"


def split_origin(raw_url: str) -> tuple[str, str, int | None] | None:
    """(scheme, host, port) of an http(s) URL, lowercased; None otherwise."""

    try:
        parts: SplitResult = urlsplit(raw_url.strip())
        port: int | None = parts.port
    except ValueError:
        return None

    scheme: str = parts.scheme.lower()
    host: str = (parts.hostname or "").lower().rstrip(".")
    if scheme not in DEFAULT_PORTS or host == "" or any(c.isspace() for c in host):
        return None

    return scheme, host, None if port == DEFAULT_PORTS[scheme] else port


def format_origin(scheme: str, host: str, port: int | None) -> str:
    shown_host: str = f"[{host}]" if ":" in host else host
    return f"{scheme}://{shown_host}" + ("" if port is None else f":{port}")


def page_origin_of(origin: str | None, referer: str | None) -> WidgetPageOrigin | None:
    """
    The page a request came from: its Origin header, else its Referer's
    origin; "null" for an opaque page; None when it names neither.
    """

    for header in (origin, referer):
        if header is None or header.strip() == "":
            continue

        if header.strip().lower() == NULL_ORIGIN:
            return WidgetPageOrigin(NULL_ORIGIN)

        parts = split_origin(header)
        return WidgetPageOrigin(NULL_ORIGIN if parts is None else format_origin(*parts))

    return None


def normalize_site_address(address: WidgetSiteAddress) -> PublicBaseUrl:
    """
    An owner's website as an origin: "https://" when no scheme is given,
    the path, query and credentials dropped.

    Raises:
        ValidationFailedError: not a web address.
    """

    raw: str = str(address).strip()
    with_scheme: str = raw if "://" in raw else f"https://{raw}"
    parts = split_origin(with_scheme)
    if parts is None or ("." not in parts[1] and parts[1] != "localhost"):
        raise ValidationFailedError(f"{raw!r} is not a website address.")

    return PublicBaseUrl(format_origin(*parts))


def site_key(origin: str) -> tuple[str, int | None] | None:
    """The host without "www." and the port: what two origins share as one site."""

    parts = split_origin(origin)
    if parts is None:
        return None

    _, host, port = parts
    return host.removeprefix(WWW_PREFIX), port


def is_origin_allowed(
    page_origin: WidgetPageOrigin | None,
    allowed: Iterable[PublicBaseUrl],
    always_allowed: Iterable[str],
) -> bool:
    """
    Whether a page may use the chat: no list (any site), no page, one of the
    platform's own origins, or a site on the list.
    """

    allowed_keys = {site_key(str(origin)) for origin in allowed} - {None}
    if not allowed_keys or page_origin is None:
        return True

    page_key = site_key(str(page_origin))
    if page_key is None:
        return False

    own_keys = {site_key(origin) for origin in always_allowed} - {None}
    return page_key in own_keys or page_key in allowed_keys


def platform_page_origins(
    cabinet_base_url: str | None,
    app_base_url: str | None,
    cabinet_origins: Iterable[str],
) -> list[PublicBaseUrl]:
    """
    The platform's own pages that always may show a chat: the cabinet
    (CABINET_BASE_URL and CORS_ALLOWED_ORIGINS: the hosted chat page and the
    live preview) and the API (APP_BASE_URL: the widget demo page).
    """

    origins: list[PublicBaseUrl] = []
    for address in (cabinet_base_url, app_base_url, *cabinet_origins):
        parts = None if address is None else split_origin(str(address))
        if parts is not None and format_origin(*parts) not in origins:
            origins.append(PublicBaseUrl(format_origin(*parts)))

    return origins


def unique_sites(origins: Iterable[PublicBaseUrl]) -> list[PublicBaseUrl]:
    """The origins in their order, one per site (www. and scheme aside)."""

    seen: set[tuple[str, int | None]] = set()
    unique: list[PublicBaseUrl] = []
    for origin in origins:
        key = site_key(str(origin))
        if key is not None and key not in seen:
            seen.add(key)
            unique.append(origin)

    return unique
