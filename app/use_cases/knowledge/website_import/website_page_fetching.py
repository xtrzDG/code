"""
Fetching a business's website through the safe fetcher: one page as the
reader sees it, and the pages worth reading (sitemap.xml and the start
page's links, same site only, most useful first).
"""

from pydantic import ValidationError

from app.contracts.web_fetching import SafeHttpFetcherContract
from app.schemas.dto.web_fetching import FetchedWebResource, WebFetchRequest
from app.schemas.dto.website_import import SanitizedWebPage
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.schemas.typings.web_fetching.constrained_strings import (
    WebMediaType,
    WebResourceUrl,
)
from app.utilities.knowledge.website.page_text_decoding import decode_page
from app.utilities.knowledge.website.site_links import (
    rank_pages,
    same_site_pages,
    site_host,
)
from app.utilities.knowledge.website.sitemap import (
    SitemapEntries,
    read_sitemap,
    sitemap_address,
)
from app.utilities.knowledge.website.web_page_reading import read_web_page

# The pages one import reads, the start page included.
MAX_PAGES: int = 15
# Of a sitemap index, the first sitemaps that are read.
MAX_CHILD_SITEMAPS: int = 2
PAGE_MEDIA_TYPES: frozenset[WebMediaType] = frozenset(
    WebMediaType(media_type)
    for media_type in ("text/html", "application/xhtml+xml", "text/plain")
)
SITEMAP_MEDIA_TYPES: frozenset[WebMediaType] = frozenset(
    WebMediaType(media_type)
    for media_type in ("application/xml", "text/xml", "text/plain")
)


def fetch_page(
    fetcher: SafeHttpFetcherContract, url: WebResourceUrl
) -> SanitizedWebPage:
    """
    The page's visible text and links.

    Raises:
        WebFetchError: the page was refused, not fetched, or is not a page.
    """

    resource: FetchedWebResource = fetcher.fetch(
        WebFetchRequest(url=url, accepted_media_types=PAGE_MEDIA_TYPES)
    )
    return read_web_page(resource)


def plan_pages(
    fetcher: SafeHttpFetcherContract,
    start_page: SanitizedWebPage,
    requested_url: str,
) -> list[WebResourceUrl]:
    """
    The other pages to read after the start page (at most MAX_PAGES - 1):
    pages of the same site from its sitemap and from the start page's links.
    """

    site: str = site_host(str(start_page.url))
    candidates: list[str] = [
        *(str(link) for link in start_page.links),
        *read_sitemap_pages(fetcher, sitemap_address(str(start_page.url))),
    ]
    pages: list[str] = same_site_pages(
        candidates, site, already_known=[str(start_page.url), requested_url]
    )
    planned: list[WebResourceUrl] = []
    for page in rank_pages(pages):
        url: WebResourceUrl | None = to_resource_url(page)
        if url is not None:
            planned.append(url)
        if len(planned) == MAX_PAGES - 1:
            break

    return planned


def read_sitemap_pages(fetcher: SafeHttpFetcherContract, address: str) -> list[str]:
    """The pages a sitemap lists (an index: its first sitemaps); [] without one."""

    entries: SitemapEntries | None = fetch_sitemap(fetcher, address)
    if entries is None:
        return []

    pages: list[str] = list(entries.pages)
    for child in entries.sitemaps[:MAX_CHILD_SITEMAPS]:
        child_entries: SitemapEntries | None = fetch_sitemap(fetcher, child)
        if child_entries is not None:
            pages.extend(child_entries.pages)

    return pages


def fetch_sitemap(
    fetcher: SafeHttpFetcherContract, address: str
) -> SitemapEntries | None:
    url: WebResourceUrl | None = to_resource_url(address)
    if url is None:
        return None

    try:
        resource: FetchedWebResource = fetcher.fetch(
            WebFetchRequest(url=url, accepted_media_types=SITEMAP_MEDIA_TYPES)
        )
    except WebFetchError:
        return None

    return read_sitemap(
        decode_page(
            resource.body, None if resource.charset is None else str(resource.charset)
        )
    )


def to_resource_url(address: str) -> WebResourceUrl | None:
    try:
        return WebResourceUrl(address)
    except ValidationError, ValueError:
        return None
