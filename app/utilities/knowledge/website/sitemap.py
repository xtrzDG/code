"""
Reading a sitemap.xml without an XML parser: the <loc> entries are all a
knowledge import needs, and a regular expression cannot be made to expand
entities or fetch anything (no XML bombs, no external entities).
"""

import html
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

# Bounded, so a page of unclosed <loc> tags cannot make matching slow.
LOCATION: re.Pattern[str] = re.compile(
    r"<loc>\s*([^<]{1,2048}?)\s*</loc>", re.IGNORECASE
)
SITEMAP_INDEX: re.Pattern[str] = re.compile(r"<sitemapindex[\s>]", re.IGNORECASE)
MAX_LOCATIONS: int = 1000


@dataclass
class SitemapEntries:
    """The page addresses of a sitemap, or the sitemaps an index lists."""

    pages: list[str] = field(default_factory=list[str])
    sitemaps: list[str] = field(default_factory=list[str])


def read_sitemap(xml_text: str) -> SitemapEntries:
    locations: list[str] = [
        html.unescape(match.group(1)).strip() for match in LOCATION.finditer(xml_text)
    ][:MAX_LOCATIONS]
    locations = [location for location in locations if location != ""]
    if SITEMAP_INDEX.search(xml_text[:4096]) is not None:
        return SitemapEntries(sitemaps=locations)

    return SitemapEntries(pages=locations)


def sitemap_address(page_url: str) -> str:
    """Where a site keeps its sitemap: /sitemap.xml at the root of the page's host."""

    parts = urlsplit(page_url)
    return urlunsplit((parts.scheme, parts.netloc, "/sitemap.xml", "", ""))
