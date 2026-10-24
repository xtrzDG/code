"""The help center's use cases: topics in order, one article, search, contacts."""

from pathlib import Path

import pytest

from app.registries.help.help_article_registry import HelpArticleRegistry
from app.schemas.configurations.support_settings import SupportSettings
from app.schemas.constants.help import HelpTopic
from app.schemas.dto.help import (
    HelpArticleQuery,
    HelpCenterQuery,
    HelpSearchRequest,
    SupportContactsQuery,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.help.constrained_strings import (
    HelpArticleSlug,
    HelpSearchText,
    SupportTelegramUsername,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.use_cases.help.get_help_article_use_case import GetHelpArticleUseCase
from app.use_cases.help.get_help_center_use_case import GetHelpCenterUseCase
from app.use_cases.help.get_support_contacts_use_case import (
    GetSupportContactsUseCase,
)
from app.use_cases.help.search_help_use_case import SearchHelpUseCase
from tests.help.help_fixtures import two_language_registry

RU = LanguageTag("ru")


@pytest.fixture
def registry(tmp_path: Path) -> HelpArticleRegistry:
    return two_language_registry(tmp_path)


def test_the_help_center_groups_articles_by_topic_in_order(
    registry: HelpArticleRegistry,
) -> None:
    view = GetHelpCenterUseCase(registry).run(HelpCenterQuery(language=RU))

    assert view.language == "ru"
    assert view.available_languages == ["en", "ru"]
    assert [topic.topic for topic in view.topics] == [
        HelpTopic.GETTING_STARTED,
        HelpTopic.CHANNELS,
    ]
    assert [card.title for card in view.topics[1].articles] == ["Телеграм", "Ватсап"]


def test_an_unknown_language_is_answered_in_english(
    registry: HelpArticleRegistry,
) -> None:
    view = GetHelpCenterUseCase(registry).run(
        HelpCenterQuery(language=LanguageTag("ka"))
    )

    assert view.language == "en"


def test_without_articles_the_help_center_is_not_found(tmp_path: Path) -> None:
    with pytest.raises(NotFoundError):
        GetHelpCenterUseCase(HelpArticleRegistry(tmp_path)).run(
            HelpCenterQuery(language=RU)
        )


def test_an_article_comes_with_the_related_articles_that_exist(
    registry: HelpArticleRegistry,
) -> None:
    view = GetHelpArticleUseCase(registry).run(
        HelpArticleQuery(
            language=LanguageTag("en-GB"), slug=HelpArticleSlug("telegram")
        )
    )

    assert view.language == "en"
    assert view.title == "Telegram"
    assert view.markdown.startswith("Open @BotFather")
    assert [card.slug for card in view.related] == ["whatsapp"]


def test_an_unknown_article_is_not_found(registry: HelpArticleRegistry) -> None:
    with pytest.raises(NotFoundError, match="no help article"):
        GetHelpArticleUseCase(registry).run(
            HelpArticleQuery(language=RU, slug=HelpArticleSlug("refunds"))
        )


def test_search_answers_in_the_served_language(registry: HelpArticleRegistry) -> None:
    results = SearchHelpUseCase(registry).run(
        HelpSearchRequest(language=RU, text=HelpSearchText("токен"))
    )

    assert results.language == "ru"
    assert [hit.slug for hit in results.items] == ["telegram"]
    assert results.items[0].snippet is None  # found by a keyword only

    body_hit = SearchHelpUseCase(registry).run(
        HelpSearchRequest(language=RU, text=HelpSearchText("botfather"))
    )
    assert body_hit.items[0].snippet == "Откройте @BotFather и отправьте /newbot."


def test_support_contacts_open_the_chat_or_the_mail_at_once() -> None:
    view = GetSupportContactsUseCase(
        SupportSettings(
            whatsapp_number=E164PhoneNumber("+995322000000"),
            telegram_username=SupportTelegramUsername("workshop_support"),
            email=EmailAddress("help@workshop.example"),
        )
    ).run(SupportContactsQuery())

    assert view.whatsapp_url == "https://wa.me/995322000000"
    assert view.telegram_url == "https://t.me/workshop_support"
    assert view.email_url == "mailto:help@workshop.example"


def test_support_channels_not_set_up_are_not_offered() -> None:
    view = GetSupportContactsUseCase(SupportSettings()).run(SupportContactsQuery())

    assert view.model_dump(exclude_none=True) == {}
