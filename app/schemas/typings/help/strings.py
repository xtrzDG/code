"""Keep abc order."""

from base_typed_string import BaseTypedString


class HelpArticleMarkdown(BaseTypedString):
    """The body of a help article in Markdown, without its front matter."""


class HelpArticleSummary(BaseTypedString):
    """One or two sentences that say what a help article answers."""


class HelpArticleTitle(BaseTypedString):
    """The heading of a help article in its language."""


class HelpKeyword(BaseTypedString):
    """A word or phrase owners may search with to find a help article."""


class HelpSearchSnippet(BaseTypedString):
    """A short passage of a help article around what was searched for."""


# Keep abc order for all non example types, if possible.
