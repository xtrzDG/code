from app.contracts.help import HelpArticleRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.help import HelpArticleQuery, HelpArticleRecord, HelpArticleView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.help.constrained_strings import HelpArticleSlug
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.help.help_articles import article_card, served_language


class GetHelpArticleUseCase(UseCaseContract[HelpArticleQuery, HelpArticleView]):
    """
    GET /v1/help/{language}/{slug}: one article in the language served,
    its Markdown and the articles it points to (those that exist). The
    cabinet's "?" opens it in a drawer beside the page it explains.

    Raises:
        NotFoundError: no article has that slug.
    """

    def __init__(self, help_article_registry: HelpArticleRegistryContract) -> None:
        self._registry: HelpArticleRegistryContract = help_article_registry

    def run(self, input_data: HelpArticleQuery) -> HelpArticleView:
        language: LanguageTag = served_language(self._registry, input_data.language)
        by_slug: dict[HelpArticleSlug, HelpArticleRecord] = {
            article.slug: article for article in self._registry.list_articles(language)
        }
        article: HelpArticleRecord | None = by_slug.get(input_data.slug)
        if article is None:
            raise NotFoundError(f"There is no help article {input_data.slug}.")

        return HelpArticleView(
            slug=article.slug,
            language=language,
            available_languages=self._registry.available_languages(),
            title=article.title,
            summary=article.summary,
            topic=article.topic,
            markdown=article.markdown,
            related=[
                article_card(by_slug[slug])
                for slug in article.related
                if slug in by_slug and slug != article.slug
            ],
        )
