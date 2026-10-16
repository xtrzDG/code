from app.contracts.help import HelpArticleRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.help import HelpTopic
from app.schemas.dto.help import (
    HelpArticleRecord,
    HelpCenterQuery,
    HelpCenterView,
    HelpTopicView,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.help.help_articles import (
    article_card,
    reading_order,
    served_language,
)


class GetHelpCenterUseCase(UseCaseContract[HelpCenterQuery, HelpCenterView]):
    """
    GET /v1/help/{language}: every article of the language served (the
    one asked for, else its base language, else English), grouped by
    topic in the help center's order and by each article's order inside.
    Public: a visitor reads the help before signing up.
    """

    def __init__(self, help_article_registry: HelpArticleRegistryContract) -> None:
        self._registry: HelpArticleRegistryContract = help_article_registry

    def run(self, input_data: HelpCenterQuery) -> HelpCenterView:
        language: LanguageTag = served_language(self._registry, input_data.language)
        articles: list[HelpArticleRecord] = self._registry.list_articles(language)
        topics: list[HelpTopicView] = []
        for topic in HelpTopic:
            in_topic: list[HelpArticleRecord] = sorted(
                (article for article in articles if article.topic is topic),
                key=reading_order,
            )
            if in_topic:
                topics.append(
                    HelpTopicView(
                        topic=topic,
                        articles=[article_card(article) for article in in_topic],
                    )
                )

        return HelpCenterView(
            language=language,
            available_languages=self._registry.available_languages(),
            topics=topics,
        )
