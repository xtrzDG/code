"""
The links of a reply, vetted: a model may invent an address ("book at
www.mario-pizza.it") or repeat one a customer or an imported page slipped
in. A link passes when its host is one the business published (any link of
the facts, the tool results, the platform's context and staff messages,
with its subdomains), the platform's own (the booking and chat pages) or a
well-known map or payment service (`link_hosts`); any other one is
returned, as written, for the guard to hold the reply back.

Links are found with a scheme ("https://..."), with "www." or as a bare
domain of a common top-level domain ("mario-pizza.it/menu"); an e-mail
address is not a link (the personal data check reads those).
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.utilities.reply_guard.link_hosts import WELL_KNOWN_LINKS

SCHEME_LINK_PATTERN: re.Pattern[str] = re.compile(
    r"(?i)\b(?:https?://|www\.)[^\s<>\"'`]+"
)
COMMON_TOP_LEVEL_DOMAINS: str = (
    "com|net|org|info|biz|eu|it|de|fr|es|pt|nl|be|ch|at|uk|ie|pl|cz|sk|hu|ro|"
    "gr|se|no|dk|fi|ge|ru|ua|am|az|kz|il|tr|co|io|me|app|shop|store|online|"
    "site|menu|restaurant|cafe|bar|hotel"
)
BARE_DOMAIN_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![@\w.-])((?:[a-z0-9][a-z0-9-]*[a-z0-9]\.)+"
    rf"(?:{COMMON_TOP_LEVEL_DOMAINS}))(/[^\s<>\"'`]*)?(?![\w@-])"
)
TRAILING_PUNCTUATION: str = ".,;:!?)]}»”’'\""
WWW_PREFIX: str = "www."


@dataclass(frozen=True)
class FoundLink:
    """A link of a text: as written, its host and its path (technical record)."""

    text: str
    host: str
    path: str


def find_links(text: str) -> list[FoundLink]:
    """The links of a text, in their order (bare domains after the others)."""

    links: list[FoundLink] = []
    remaining: str = text
    for match in SCHEME_LINK_PATTERN.finditer(text):
        written: str = match.group(0).rstrip(TRAILING_PUNCTUATION)
        remaining = remaining.replace(written, " ")
        link: FoundLink | None = parse_link(written)
        if link is not None:
            links.append(link)

    for match in BARE_DOMAIN_PATTERN.finditer(remaining):
        written = match.group(0).rstrip(TRAILING_PUNCTUATION)
        link = parse_link(written)
        if link is not None:
            links.append(link)

    return links


def parse_link(written: str) -> FoundLink | None:
    """The link's host (lower case, without "www." and port) and path."""

    address: str = written if "://" in written else f"https://{written}"
    try:
        parts = urlsplit(address)
        host: str = (parts.hostname or "").casefold()
    except ValueError:
        return None

    if host == "":
        return None

    return FoundLink(text=written, host=host.removeprefix(WWW_PREFIX), path=parts.path)


def find_foreign_links(
    reply_text: str,
    trusted_texts: Iterable[str],
    platform_hosts: Sequence[str] = (),
) -> list[str]:
    """The reply's links that pass none of the allowed hosts, as written."""

    links: list[FoundLink] = find_links(reply_text)
    if not links:
        return []

    allowed: list[str] = [
        *WELL_KNOWN_LINKS,
        *(host.casefold().removeprefix(WWW_PREFIX) for host in platform_hosts),
        *(link.host for text in trusted_texts for link in find_links(text)),
    ]
    return list(
        dict.fromkeys(link.text for link in links if not is_allowed(link, allowed))
    )


def is_allowed(link: FoundLink, allowed: Sequence[str]) -> bool:
    """Whether an entry ("host" or "host/path") covers the link."""

    for entry in allowed:
        entry_host, _, entry_path = entry.partition("/")
        if not (link.host == entry_host or link.host.endswith(f".{entry_host}")):
            continue

        if entry_path == "" or link.path.startswith(f"/{entry_path}"):
            return True

    return False


def link_host(url: str | None) -> str | None:
    """The host of a configured address (a platform base URL); None if none."""

    if url is None:
        return None

    link: FoundLink | None = parse_link(url)
    return None if link is None else link.host
