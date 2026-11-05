"""
HTML to the text a visitor reads (the website reader's only input).

Scripts, styles, embedded objects, comments and hidden elements are
dropped (`html_visibility`); navigation, forms and buttons give links but
no text. Blocks become lines, list items "- ", headings "#", table cells
are joined with " | " so price tables stay readable. The title and the
links (absolute, resolved against the page and its <base>) come along.
"""

from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin

from app.utilities.knowledge.website.html_visibility import (
    DROP_ALL,
    DROP_TEXT,
    KEEP,
    VOID_TAGS,
    visibility_of,
)
from app.utilities.knowledge.website.visible_text_cleanup import (
    clean_inline_text,
    finish_text,
)

BLOCK_TAGS: frozenset[str] = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "body",
        "br",
        "caption",
        "dd",
        "details",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "header",
        "hr",
        "li",
        "main",
        "ol",
        "p",
        "pre",
        "section",
        "summary",
        "table",
        "tbody",
        "tfoot",
        "thead",
        "tr",
        "ul",
    }
)
HEADING_PREFIXES: dict[str, str] = {
    "h1": "# ",
    "h2": "## ",
    "h3": "### ",
    "h4": "### ",
    "h5": "### ",
    "h6": "### ",
}
CELL_TAGS: frozenset[str] = frozenset({"td", "th"})
MAX_LINKS: int = 500


@dataclass
class HtmlText:
    """What a page shows: title, text (one block per line) and links."""

    title: str
    text: str
    links: list[str] = field(default_factory=list[str])


def html_to_text(html: str, page_url: str, max_characters: int) -> HtmlText:
    """The visible text of `html` (at most `max_characters`), title and links."""

    collector = VisibleTextCollector(page_url)
    collector.feed(html)
    collector.close()
    return HtmlText(
        title=clean_inline_text(" ".join(collector.title_parts))[:300],
        text=finish_text(collector.parts, max_characters),
        links=collector.links,
    )


class VisibleTextCollector(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.links: list[str] = []
        self._base_url: str = page_url
        self._stack: list[tuple[str, int]] = []
        self._in_title: bool = False

    @property
    def _mode(self) -> int:
        return max((mode for _, mode in self._stack), default=KEEP)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes: dict[str, str | None] = {key.lower(): value for key, value in attrs}
        mode: int = max(self._mode, visibility_of(tag, attributes))
        if tag == "base" and attributes.get("href"):
            self._base_url = urljoin(self._base_url, attributes["href"] or "")
        if tag == "a" and mode < DROP_ALL:
            self._add_link(attributes.get("href"))
        if tag == "title" and mode == KEEP and not self.title_parts:
            self._in_title = True
        self._open_block(tag, mode)
        if tag not in VOID_TAGS:
            self._stack.append((tag, mode))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if not any(open_tag == tag for open_tag, _ in self._stack):
            return

        while self._stack:
            open_tag, mode = self._stack.pop()
            if mode == KEEP and (
                open_tag in BLOCK_TAGS or open_tag in HEADING_PREFIXES
            ):
                self.parts.append("\n")
            if open_tag == tag:
                return

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
            return

        if self._mode >= DROP_TEXT:
            return

        if self._stack and self._stack[-1][0] == "pre":
            self.parts.append(data)
        else:
            self.parts.append(clean_inline_text(data, keep_edges=True))

    def _open_block(self, tag: str, mode: int) -> None:
        if mode != KEEP:
            return

        if tag in BLOCK_TAGS or tag in HEADING_PREFIXES:
            self.parts.append("\n")
        if tag in HEADING_PREFIXES:
            self.parts.append(HEADING_PREFIXES[tag])
        elif tag == "li":
            self.parts.append("- ")
        elif tag in CELL_TAGS:
            self.parts.append(" | ")

    def _add_link(self, href: str | None) -> None:
        if href is None or href.strip() == "" or len(self.links) >= MAX_LINKS:
            return

        try:
            self.links.append(urljoin(self._base_url, href.strip()))
        except ValueError:
            return
