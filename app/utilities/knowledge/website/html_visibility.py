"""
What of an HTML page a visitor does not see, so the website reader never
gets it: code, embedded documents, hidden elements and the page's chrome.

Two levels:

- DROP_ALL: neither text nor links (scripts, styles, templates, embedded
  objects, and any element hidden with `hidden`, `aria-hidden="true"`,
  `display: none`, `visibility: hidden`, zero size or opacity, or a
  hiding class). Text hidden from people is a classic place for
  instructions aimed at a model.
- DROP_TEXT: links are kept (they are how the site's pages are found),
  but the text is not a fact (navigation, forms, buttons).
"""

import re
from typing import Final

KEEP: Final[int] = 0
DROP_TEXT: Final[int] = 1
DROP_ALL: Final[int] = 2

CODE_TAGS: Final[frozenset[str]] = frozenset(
    {
        "script",
        "style",
        "noscript",
        "template",
        "svg",
        "math",
        "iframe",
        "frame",
        "frameset",
        "object",
        "embed",
        "applet",
        "canvas",
        "video",
        "audio",
        "dialog",
        "datalist",
        "select",
        "textarea",
    }
)
CHROME_TAGS: Final[frozenset[str]] = frozenset({"nav", "form", "button", "menu"})
VOID_TAGS: Final[frozenset[str]] = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
HIDING_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "hidden",
        "d-none",
        "is-hidden",
        "invisible",
        "visually-hidden",
        "sr-only",
        "screen-reader-text",
        "hide",
    }
)
HIDING_STYLE: Final[re.Pattern[str]] = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*(hidden|collapse)"
    r"|(?<![-\w])(font-size|width|height|max-height|max-width)\s*:\s*0(px|em|rem|%)?\s*(;|!|$)"
    r"|opacity\s*:\s*0?\.?0+\s*(;|!|$)"
    r"|(?<![-\w])(left|top|text-indent)\s*:\s*-\d{4,}",
    re.IGNORECASE,
)


def visibility_of(tag: str, attributes: dict[str, str | None]) -> int:
    """KEEP, DROP_TEXT or DROP_ALL for an element and its content."""

    if tag in CODE_TAGS or is_hidden(attributes):
        return DROP_ALL

    if tag in CHROME_TAGS:
        return DROP_TEXT

    return KEEP


def is_hidden(attributes: dict[str, str | None]) -> bool:
    if "hidden" in attributes:
        return True

    if (attributes.get("aria-hidden") or "").strip().lower() == "true":
        return True

    if (attributes.get("type") or "").strip().lower() == "hidden":
        return True

    classes: set[str] = set((attributes.get("class") or "").lower().split())
    if classes & HIDING_CLASSES:
        return True

    return HIDING_STYLE.search(attributes.get("style") or "") is not None
