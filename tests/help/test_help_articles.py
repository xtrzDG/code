"""
The help center shipped in docs/help: every language has the same
articles, every file reads, and every link inside points somewhere real.
Hebrew and German are drafts marked for a native speaker's review.
"""

import re
from pathlib import Path

from app.registries.help.help_article_registry import HelpArticleRegistry
from app.schemas.constants.help import HelpTopic
from app.schemas.dto.help import HelpArticleRecord
from app.schemas.typings.localization.constrained_strings import LanguageTag

REQUIRED_LANGUAGES: tuple[str, ...] = ("de", "en", "he", "ka", "ru")
TRANSLATED_LANGUAGES: tuple[str, ...] = ("de", "he", "ka", "ru")
# Drafted by the team; a native speaker has not read them yet.
NEEDS_REVIEW_LANGUAGES: tuple[str, ...] = ("de", "he")
HELP_DIRECTORY: Path = Path(__file__).resolve().parents[2] / "docs" / "help"
# The articles the cabinet's pages open ("?") and the package promises.
REQUIRED_SLUGS: frozenset[str] = frozenset(
    {
        "getting-started",
        "call-forwarding",
        "telegram",
        "whatsapp",
        "widget-install",
        "inbox",
        "bookings",
        "billing",
        "privacy",
    }
)
ARTICLE_LINK: re.Pattern[str] = re.compile(r"\]\(([a-z0-9-]+)\)")

REGISTRY = HelpArticleRegistry()


def articles(language: str) -> dict[str, HelpArticleRecord]:
    return {
        str(record.slug): record
        for record in REGISTRY.list_articles(LanguageTag(language))
    }


def test_the_help_center_is_written_in_five_languages() -> None:
    assert [str(language) for language in REGISTRY.available_languages()] == list(
        REQUIRED_LANGUAGES
    )


def test_every_language_has_the_same_slugs() -> None:
    slugs: dict[str, set[str]] = {
        language: set(articles(language)) for language in REQUIRED_LANGUAGES
    }

    for language in TRANSLATED_LANGUAGES:
        assert slugs[language] == slugs["en"], language
    assert slugs["en"] >= REQUIRED_SLUGS


def test_an_article_keeps_its_topic_order_and_links_in_every_language() -> None:
    english: dict[str, HelpArticleRecord] = articles("en")
    for language in TRANSLATED_LANGUAGES:
        for slug, translated in articles(language).items():
            original: HelpArticleRecord = english[slug]
            assert translated.topic is original.topic, (language, slug)
            assert translated.order == original.order, (language, slug)
            assert translated.related == original.related, (language, slug)
            assert sorted(ARTICLE_LINK.findall(translated.markdown)) == sorted(
                ARTICLE_LINK.findall(original.markdown)
            ), (language, slug)


def test_links_and_related_articles_point_to_existing_articles() -> None:
    for language in REQUIRED_LANGUAGES:
        by_slug: dict[str, HelpArticleRecord] = articles(language)
        for slug, record in by_slug.items():
            assert all(str(related) in by_slug for related in record.related), slug
            assert slug not in record.related
            for linked in ARTICLE_LINK.findall(record.markdown):
                assert linked in by_slug, (language, slug, linked)


def test_every_article_says_what_it_answers_and_can_be_found() -> None:
    for language in REQUIRED_LANGUAGES:
        titles: list[str] = []
        for record in articles(language).values():
            assert record.summary.strip()
            assert record.keywords, record.slug
            assert len(record.markdown) > 300, record.slug
            titles.append(str(record.title))
        assert len(set(titles)) == len(titles)


def test_every_topic_of_the_help_center_has_articles() -> None:
    assert {record.topic for record in articles("en").values()} == set(HelpTopic)


def test_draft_translations_are_marked_for_review() -> None:
    for language in NEEDS_REVIEW_LANGUAGES:
        for path in sorted((HELP_DIRECTORY / language).glob("*.md")):
            front_matter: str = path.read_text(encoding="utf-8").split("---")[1]
            assert "status: needs_review" in front_matter.splitlines(), path.name
