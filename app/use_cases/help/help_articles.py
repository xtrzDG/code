"""What the help center's use cases share: the language served and the cards."""

from app.contracts.help import HelpArticleRegistryContract
from app.schemas.dto.help import HelpArticleCard, HelpArticleRecord
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.constrained_strings import LanguageTag


def served_language(
    registry: HelpArticleRegistryContract, requested: LanguageTag
) -> LanguageTag:
    """The language to answer in; NotFoundError when no article exists at all."""

    language: LanguageTag | None = registry.serve_language(requested)
    if language is None:
        raise NotFoundError("The help center has no articles.")
    return language


def article_card(article: HelpArticleRecord) -> HelpArticleCard:
    return HelpArticleCard(
        slug=article.slug,
        title=article.title,
        summary=article.summary,
        topic=article.topic,
    )


def reading_order(article: HelpArticleRecord) -> tuple[int, str]:
    return int(article.order), str(article.title).casefold()
