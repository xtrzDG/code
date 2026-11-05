"""Help search: words in the title count most, word forms match, a passage shows why."""

from app.schemas.constants.help import HelpTopic
from app.schemas.dto.help import HelpArticleRecord
from app.schemas.typings.help.constrained_integers import HelpArticleOrder
from app.schemas.typings.help.constrained_strings import HelpArticleSlug
from app.schemas.typings.help.strings import (
    HelpArticleMarkdown,
    HelpArticleSummary,
    HelpArticleTitle,
    HelpKeyword,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.help.help_search import (
    find_snippet,
    plain_text,
    search_articles,
    search_terms,
)


def record(
    slug: str, title: str, body: str, keywords: tuple[str, ...] = (), order: int = 10
) -> HelpArticleRecord:
    return HelpArticleRecord(
        slug=HelpArticleSlug(slug),
        language=LanguageTag("ru"),
        title=HelpArticleTitle(title),
        summary=HelpArticleSummary("Коротко."),
        topic=HelpTopic.CHANNELS,
        order=HelpArticleOrder(order),
        keywords=[HelpKeyword(keyword) for keyword in keywords],
        markdown=HelpArticleMarkdown(body),
    )


FORWARDING = record(
    "call-forwarding",
    "Переадресация звонков",
    "Наберите `**61*номер#` и нажмите вызов. Звонки уйдут помощнику.",
    keywords=("magti", "оператор"),
)
TELEGRAM = record(
    "telegram", "Telegram", "Откройте **@BotFather** и [подключите](channels) бота."
)
WIDGET = record(
    "widget-install", "Чат на сайте", "Вставьте код перед </body>.", order=5
)
ALL = [WIDGET, TELEGRAM, FORWARDING]


def slugs(text: str) -> list[str]:
    return [str(match.article.slug) for match in search_articles(ALL, text, 10)]


def test_the_title_wins_and_word_forms_match() -> None:
    assert slugs("переадресацию") == ["call-forwarding"]
    assert slugs("Переадресация звонков") == ["call-forwarding"]


def test_keywords_and_the_body_are_searched_too() -> None:
    assert slugs("Magti") == ["call-forwarding"]
    assert slugs("botfather") == ["telegram"]


def test_articles_matching_more_words_come_first() -> None:
    assert slugs("бота звонки") == ["call-forwarding", "telegram"]
    assert set(slugs("код бота вызов")) == {
        "call-forwarding",
        "telegram",
        "widget-install",
    }


def test_nothing_to_search_or_nothing_found_is_empty() -> None:
    assert slugs("  ?! ") == []
    assert slugs("холодильник") == []
    assert search_terms("a Бот бот ok") == ["бот", "ok"]


def test_the_limit_keeps_the_best() -> None:
    assert len(search_articles(ALL, "код бота вызов", 2)) == 2


def test_the_passage_is_plain_text_around_the_word() -> None:
    match = search_articles(ALL, "botfather", 10)[0]

    assert match.snippet == "Откройте @BotFather и подключите бота."
    assert plain_text("## Title\n- **one**\n2. `two` | x |") == "Title one two x"


def test_a_long_body_is_cut_around_the_word_with_ellipses() -> None:
    body: str = " ".join(["слово"] * 60) + " переадресация " + " ".join(["текст"] * 60)

    snippet = find_snippet(body, ["переадресация"])

    assert snippet is not None
    assert snippet.startswith("…") and snippet.endswith("…")
    assert "переадресация" in snippet
    assert len(snippet) < 230
    assert find_snippet(body, ["холодильник"]) is None
    assert find_snippet("переадресацию включают так", ["переадресация"]) == (
        "переадресацию включают так"
    )
