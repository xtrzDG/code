"""
Which pages of a website a knowledge import reads.

Only pages of the same site (the same host, with or without "www."), over
http(s), without files (images, documents, archives), sign-in, cart or
admin pages. The rest is ordered so the useful pages come first: menus,
prices, services, questions, contacts and opening hours in several
languages, then shallow pages before deep ones; blog posts and legal pages
come last. Addresses are compared without fragments, default ports and
tracking parameters, so one page is read once.
"""

import re
from collections.abc import Iterable
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

SKIPPED_EXTENSIONS: tuple[str, ...] = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp", ".avif",
    ".css", ".js", ".mjs", ".json", ".xml", ".rss", ".atom", ".txt",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv",
    ".zip", ".rar", ".7z", ".gz", ".tar", ".dmg", ".exe", ".apk",
    ".mp3", ".mp4", ".mov", ".avi", ".webm", ".ogg", ".wav",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
)  # fmt: skip
SKIPPED_PATH: re.Pattern[str] = re.compile(
    r"(^|/)(wp-admin|wp-login|wp-json|xmlrpc|cdn-cgi|admin|login|log-in|signin|"
    r"sign-in|signup|sign-up|register|account|my-account|cart|basket|checkout|"
    r"logout|feed|search)(/|\.|$)",
    re.IGNORECASE,
)
USEFUL_WORDS: re.Pattern[str] = re.compile(
    r"menu|menyu|меню|მენიუ|speisekarte|carta|carte|price|pricing|preise|precio|"
    r"prix|tarif|цен|tseny|ceny|ფას|fasebi|service|uslug|услуг|სერვის|leistung|"
    r"servicio|faq|question|вопрос|კითხვ|contact|kontakt|контакт|კონტაქტ|"
    r"about|о-нас|o-nas|ჩვენ-შესახებ|hours|opening|часы|режим|delivery|доставк|"
    r"(?<![a-z])book|reserv|бронир|rooms|номера|treatment|процедур|product|"
    r"catalog|каталог|shop|team|staff|location|address|адрес|მისამართ",
    re.IGNORECASE,
)
LATE_WORDS: re.Pattern[str] = re.compile(
    r"(?<![a-z])(blog|news|novosti|новост|articles?|posts?|press|events?|tags?|"
    r"category|author|privacy|terms|cookies?|gdpr|impressum|legal|careers?|"
    r"jobs?|vacanc|ваканс)|page/\d",
    re.IGNORECASE,
)
TRACKING_PARAMETER: re.Pattern[str] = re.compile(
    r"^(utm_\w+|fbclid|gclid|yclid|mc_cid|mc_eid|_ga|ref)$", re.IGNORECASE
)
DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}


def site_host(url: str) -> str:
    """The host that names the site, lower case and without "www."."""

    host: str = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host.removeprefix("www.")


def normalize_page_url(url: str) -> str | None:
    """The page's address in one spelling, or None when it is not a page."""

    try:
        parts = urlsplit(url.strip())
        port: int | None = parts.port
    except ValueError:
        return None

    scheme: str = parts.scheme.lower()
    host: str = (parts.hostname or "").lower().rstrip(".")
    if scheme not in DEFAULT_PORTS or host == "" or parts.username is not None:
        return None

    path: str = parts.path or "/"
    if path.lower().endswith(SKIPPED_EXTENSIONS) or SKIPPED_PATH.search(path):
        return None

    netloc: str = host if port in (None, DEFAULT_PORTS[scheme]) else f"{host}:{port}"
    query: str = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not TRACKING_PARAMETER.match(key)
        ]
    )
    return urlunsplit((scheme, netloc, path, query, ""))


def same_site_pages(
    candidates: Iterable[str], site: str, already_known: Iterable[str]
) -> list[str]:
    """
    The candidates that are pages of `site` (see `site_host`), normalized,
    without duplicates and without the pages already known.
    """

    seen: set[str] = {page_key(known) for known in already_known}
    pages: list[str] = []
    for candidate in candidates:
        page: str | None = normalize_page_url(candidate)
        if page is None or site_host(page) != site:
            continue

        key: str = page_key(page)
        if key in seen:
            continue

        seen.add(key)
        pages.append(page)

    return pages


def page_key(url: str) -> str:
    """http/https, www and a trailing slash do not make another page."""

    normalized: str = normalize_page_url(url) or url
    parts = urlsplit(normalized)
    path: str = parts.path.rstrip("/") or "/"
    return f"{site_host(normalized)}{path}?{parts.query}"


def rank_pages(pages: list[str]) -> list[str]:
    """The pages, most useful first (stable within the same score)."""

    return sorted(pages, key=page_score)


def page_score(url: str) -> tuple[int, int]:
    """Lower is better: (usefulness band, depth)."""

    path: str = unquote(urlsplit(url).path).lower()
    depth: int = len([segment for segment in path.split("/") if segment])
    if USEFUL_WORDS.search(path):
        band = 0
    elif LATE_WORDS.search(path):
        band = 2
    else:
        band = 1

    return band, depth
