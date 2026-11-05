"""Reading help articles from files: the format, languages and their fallback."""

from pathlib import Path

import pytest

from app.registries.help.help_article_files import (
    HelpArticleFormatError,
    parse_article,
    read_help_directory,
)
from app.registries.help.help_article_registry import HelpArticleRegistry
from app.schemas.constants.help import HelpTopic
from app.schemas.typings.help.constrained_strings import HelpArticleSlug
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.help.help_fixtures import article, two_language_registry, write_help

SLUG = HelpArticleSlug("telegram")
EN = LanguageTag("en")


def test_an_article_reads_its_front_matter_title_and_body() -> None:
    record = parse_article(
        SLUG,
        EN,
        "﻿"
        + article(
            "Telegram",
            summary="Connect a bot.",
            order=7,
            keywords="bot, token , ",
            related="whatsapp",
            body="## Connect\n\n1. Open @BotFather.",
        ),
    )

    assert record.title == "Telegram"
    assert record.summary == "Connect a bot."
    assert record.topic is HelpTopic.CHANNELS
    assert int(record.order) == 7
    assert record.keywords == ["bot", "token"]
    assert record.related == ["whatsapp"]
    assert record.markdown == "## Connect\n\n1. Open @BotFather.\n"


def test_the_order_defaults_to_the_end_of_its_topic() -> None:
    text = "---\nsummary: S.\ntopic: account\n---\n# Billing\nText.\n"

    assert int(parse_article(SLUG, EN, text).order) == 100


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("# No front matter\n", "starts with front matter"),
        ("---\nsummary: S.\ntopic: channels\n", "not closed"),
        ("---\nsummary: S.\ntopic: channels\nnot a field\n---\n# T\n", "unreadable"),
        ("---\ntopic: channels\n---\n# T\n", "'summary'"),
        ("---\nsummary: S.\n---\n# T\n", "'topic'"),
        ("---\nsummary: S.\ntopic: news\n---\n# T\n", "unknown topic"),
        ("---\nsummary: S.\ntopic: channels\norder: first\n---\n# T\n", "number"),
        ("---\nsummary: S.\ntopic: channels\n---\n\nNo title.\n", "'# ' title"),
        ("---\nsummary: S.\ntopic: channels\n---\n", "'# ' title"),
    ],
)
def test_a_malformed_article_names_its_problem(text: str, problem: str) -> None:
    with pytest.raises(HelpArticleFormatError, match=problem):
        parse_article(SLUG, EN, text)


def test_other_files_and_folders_are_left_alone(tmp_path: Path) -> None:
    root = write_help(tmp_path, {"en": {"telegram": article("Telegram")}})
    (root / "README.md").write_text("# Help\n", encoding="utf-8")
    (root / "en" / "notes.txt").write_text("draft", encoding="utf-8")
    (root / "en" / "Draft Article.md").write_text("draft", encoding="utf-8")
    (root / "_drafts").mkdir()
    (root / "empty").mkdir()

    articles = read_help_directory(root)

    assert list(articles) == [EN]
    assert [str(record.slug) for record in articles[EN]] == ["telegram"]


def test_a_missing_folder_means_no_articles(tmp_path: Path) -> None:
    registry = HelpArticleRegistry(tmp_path / "missing")

    assert registry.available_languages() == []
    assert registry.serve_language(EN) is None
    assert registry.list_articles(EN) == []


def test_a_language_falls_back_to_its_base_then_english(tmp_path: Path) -> None:
    registry = two_language_registry(tmp_path)

    assert registry.available_languages() == [EN, LanguageTag("ru")]
    assert registry.serve_language(LanguageTag("ru")) == "ru"
    assert registry.serve_language(LanguageTag("ru-GE")) == "ru"
    assert registry.serve_language(LanguageTag("de")) == "en"
    assert len(registry.list_articles(LanguageTag("ru"))) == 3
    assert registry.list_articles(LanguageTag("de")) == []
