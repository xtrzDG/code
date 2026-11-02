"""
The links of a reply, vetted: a model may invent an address ("book at
www.mario-pizza.it") or repeat one a customer or an imported page slipped
in. A link passes when its host is one the business published (any link of
the facts, the tool results, the platform's context and staff messages,
with its subdomains; on a shared platform such as Instagram or a link
shortener only the published page and what is under it), the platform's
own (the booking and chat pages) or a well-known map or checkout service
(`link_hosts`); any other one is returned, as written, for the guard to
hold the reply back.

Links are found with a scheme ("https://..."), with "www." or as a bare
domain of a common top-level domain ("mario-pizza.it/menu", "t.me/mario");
an e-mail address is not a link (the personal data check reads those).
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.utilities.reply_guard.link_hosts import (
    SHARED_PLATFORM_HOSTS,
    WELL_KNOWN_LINKS,
)

SCHEME_LINK_PATTERN: re.Pattern[str] = re.compile(
    r"(?i)\b(?:https?://|www\.)[^\s<>\"'`]+"
)
# Generic and country domains links are written with, the link shorteners'
# and the cheap ones of spam pages among them.
COMMON_TOP_LEVEL_DOMAINS: str = (
    "com|net|org|info|biz|eu|it|de|fr|es|pt|nl|be|ch|at|uk|ie|pl|cz|sk|hu|ro|"
    "gr|se|no|dk|fi|ge|ru|ua|am|az|kz|il|tr|co|io|me|app|shop|store|online|"
    "site|menu|restaurant|cafe|bar|hotel|ly|gl|gle|gd|to|sh|ee|lt|lv|si|hr|"
    "rs|bg|lu|mt|cy|li|sm|mc|us|ca|in|cn|jp|br|au|ai|gg|tv|fm|cc|ws|tk|xyz|"
    "top|link|click|icu|vip|win|live|club|pro|page|website|space|tech|blog|"
    "news|bio|world|today"
)
BARE_DOMAIN_PATTERN: re.Pattern[str] = re.compile(
    r"(?i)(?<![@\w.-])((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+"
    rf"(?:{COMMON_TOP_LEVEL_DOMAINS}))(/[^\s<>\"'`]*)?(?![\w@-])"
)
# A host name: labels of letters, digits and hyphens (no spaces, no IPv6).
HOST_PATTERN: re.Pattern[str] = re.compile(r"[\w-]+(?:\.[\w-]+)*")
TRAILING_PUNCTUATION: str = ".,;:!?)]}»”’'\""
WWW_PREFIX: str = "www."


@dataclass(frozen=True)
class FoundLink:
    """A link of a text: as written, its host and its path (technical record)."""

    text: str
    host: str
    path: str


@dataclass(frozen=True)
class LinkScope:
    """
    Where a reply's links may point (technical record): a host with its
    subdomains, and the path its links must stay under (None: any path; ""
    on a shared platform: its home page only).
    """

    host: str
    path: str | None = None


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

    if HOST_PATTERN.fullmatch(host) is None:
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

    allowed: list[LinkScope] = [
        *(read_entry(entry) for entry in WELL_KNOWN_LINKS),
        *(
            LinkScope(host.casefold().removeprefix(WWW_PREFIX))
            for host in platform_hosts
        ),
        *(published(link) for text in trusted_texts for link in find_links(text)),
    ]
    return list(
        dict.fromkeys(link.text for link in links if not is_allowed(link, allowed))
    )


def read_entry(entry: str) -> LinkScope:
    """A well-known entry ("host" or "host/path")."""

    host, slash, path = entry.partition("/")
    return LinkScope(host, f"/{path}" if slash else None)


def published(link: FoundLink) -> LinkScope:
    """
    What a published link allows: its host, or on a shared platform only
    its page (a business's Instagram page is not all of Instagram).
    """

    if not is_within(link.host, SHARED_PLATFORM_HOSTS):
        return LinkScope(link.host)

    return LinkScope(link.host, link.path.rstrip("/").casefold())


def is_within(host: str, hosts: Iterable[str]) -> bool:
    """Whether the host is one of the hosts or a subdomain of one."""

    return any(host == known or host.endswith(f".{known}") for known in hosts)


def is_allowed(link: FoundLink, allowed: Sequence[LinkScope]) -> bool:
    """Whether an entry covers the link (its host, then its path)."""

    path: str = link.path.rstrip("/").casefold()
    for entry in allowed:
        if not is_within(link.host, [entry.host]):
            continue

        if (
            entry.path is None
            or path == entry.path
            or (entry.path != "" and path.startswith(f"{entry.path}/"))
        ):
            return True

    return False


def platform_link_hosts(base_urls: Iterable[str | None]) -> list[str]:
    """The hosts of the platform's configured addresses (cabinet, API)."""

    links: list[FoundLink | None] = [
        parse_link(url) for url in base_urls if url is not None
    ]
    return [link.host for link in links if link is not None]
