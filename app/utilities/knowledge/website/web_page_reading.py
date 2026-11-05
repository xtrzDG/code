"""A fetched page as the website reader sees it: title, visible text, links."""

from pydantic import ValidationError

from app.schemas.dto.web_fetching import FetchedWebResource
from app.schemas.dto.website_import import SanitizedWebPage
from app.schemas.typings.web_fetching.constrained_strings import WebResourceUrl
from app.schemas.typings.website_import.strings import (
    WebsitePageText,
    WebsitePageTitle,
)
from app.utilities.knowledge.website.html_to_text import HtmlText, html_to_text
from app.utilities.knowledge.website.page_text_decoding import decode_page
from app.utilities.knowledge.website.visible_text_cleanup import finish_text

HTML_MEDIA_TYPES: frozenset[str] = frozenset({"text/html", "application/xhtml+xml"})
# About 5,000 words: enough for a menu or a price list, bounded for the model.
MAX_PAGE_CHARACTERS: int = 30_000


def read_web_page(
    resource: FetchedWebResource,
    max_characters: int = MAX_PAGE_CHARACTERS,
) -> SanitizedWebPage:
    """The page's visible text (HTML sanitized, plain text tidied) and links."""

    decoded: str = decode_page(
        resource.body, None if resource.charset is None else str(resource.charset)
    )
    page_url: str = str(resource.final_url)
    if str(resource.media_type) in HTML_MEDIA_TYPES:
        content: HtmlText = html_to_text(decoded, page_url, max_characters)
    else:
        content = HtmlText(
            title="", text=finish_text([decoded], max_characters), links=[]
        )

    return SanitizedWebPage(
        url=resource.final_url,
        title=WebsitePageTitle(content.title) if content.title else None,
        text=WebsitePageText(content.text),
        links=[link for link in map(to_resource_url, content.links) if link],
    )


def to_resource_url(link: str) -> WebResourceUrl | None:
    """The link as a web address, or None for mailto:, tel:, javascript: ..."""

    try:
        return WebResourceUrl(link)
    except ValidationError, ValueError:
        return None
