"""
The help center: articles kept as Markdown in docs/help/<language>/ (one
file per slug, the same slugs in every language), their index by topic,
search, and the platform's support contacts (SUPPORT_*).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.help import HelpTopic
from app.schemas.typings.help.constrained_integers import HelpArticleOrder
from app.schemas.typings.help.constrained_strings import (
    HelpArticleSlug,
    HelpSearchText,
    SupportLinkUrl,
    SupportTelegramUsername,
)
from app.schemas.typings.help.strings import (
    HelpArticleMarkdown,
    HelpArticleSummary,
    HelpArticleTitle,
    HelpKeyword,
    HelpSearchSnippet,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress


class HelpArticleRecord(ImmutableDTO):
    """One article in one language as the registry read it from its file."""

    slug: HelpArticleSlug
    language: LanguageTag
    title: HelpArticleTitle
    summary: HelpArticleSummary
    topic: HelpTopic
    order: HelpArticleOrder
    keywords: list[HelpKeyword] = Field(default_factory=list[HelpKeyword])
    related: list[HelpArticleSlug] = Field(default_factory=list[HelpArticleSlug])
    markdown: HelpArticleMarkdown


class HelpArticleCard(ImmutableDTO):
    """An article as a list shows it: where it is, its title and summary."""

    slug: HelpArticleSlug
    title: HelpArticleTitle
    summary: HelpArticleSummary
    topic: HelpTopic


class HelpCenterQuery(ImmutableDTO):
    """GET /v1/help/{language}."""

    language: LanguageTag


class HelpTopicView(ImmutableDTO):
    topic: HelpTopic
    articles: list[HelpArticleCard]


class HelpCenterView(ImmutableDTO):
    """
    Every article of the language served (the one asked for, else its base
    language, else English), grouped by topic in the help center's order.
    """

    language: LanguageTag
    available_languages: list[LanguageTag]
    topics: list[HelpTopicView]


class HelpArticleQuery(ImmutableDTO):
    """GET /v1/help/{language}/{slug}."""

    language: LanguageTag
    slug: HelpArticleSlug


class HelpArticleView(ImmutableDTO):
    """One article, its Markdown and the articles it points to."""

    slug: HelpArticleSlug
    language: LanguageTag
    available_languages: list[LanguageTag]
    title: HelpArticleTitle
    summary: HelpArticleSummary
    topic: HelpTopic
    markdown: HelpArticleMarkdown
    related: list[HelpArticleCard]


class HelpSearchRequest(ImmutableDTO):
    """GET /v1/help/{language}/search?q=."""

    language: LanguageTag
    text: HelpSearchText


class HelpSearchHit(ImmutableDTO):
    """An article that matches, best first, with the passage that matched."""

    slug: HelpArticleSlug
    title: HelpArticleTitle
    summary: HelpArticleSummary
    topic: HelpTopic
    snippet: HelpSearchSnippet | None = None


class HelpSearchResults(ImmutableDTO):
    language: LanguageTag
    items: list[HelpSearchHit]


class SupportContactsQuery(ImmutableDTO):
    """GET /v1/support/contacts (no input)."""


class SupportContactsView(ImmutableDTO):
    """
    How owners reach a person at the platform (SUPPORT_WHATSAPP,
    SUPPORT_TELEGRAM, SUPPORT_EMAIL), with ready links; a channel the
    platform did not set up is null.
    """

    whatsapp_number: E164PhoneNumber | None = None
    whatsapp_url: SupportLinkUrl | None = None
    telegram_username: SupportTelegramUsername | None = None
    telegram_url: SupportLinkUrl | None = None
    email: EmailAddress | None = None
    email_url: SupportLinkUrl | None = None
