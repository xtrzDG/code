from app.contracts.help import HelpArticleRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.help import HelpSearchHit, HelpSearchRequest, HelpSearchResults
from app.schemas.typings.help.strings import HelpSearchSnippet
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.help.help_articles import served_language
from app.utilities.help.help_search import SearchMatch, search_articles

MAX_SEARCH_HITS: int = 10


class SearchHelpUseCase(UseCaseContract[HelpSearchRequest, HelpSearchResults]):
    """
    GET /v1/help/{language}/search?q=: the articles of the language served
    that match the words typed, best first, each with the passage that
    matched (app/utilities/help/help_search.py). No match is an empty list.
    """

    def __init__(self, help_article_registry: HelpArticleRegistryContract) -> None:
        self._registry: HelpArticleRegistryContract = help_article_registry

    def run(self, input_data: HelpSearchRequest) -> HelpSearchResults:
        language: LanguageTag = served_language(self._registry, input_data.language)
        matches: list[SearchMatch] = search_articles(
            self._registry.list_articles(language), input_data.text, MAX_SEARCH_HITS
        )
        return HelpSearchResults(
            language=language,
            items=[
                HelpSearchHit(
                    slug=match.article.slug,
                    title=match.article.title,
                    summary=match.article.summary,
                    topic=match.article.topic,
                    snippet=(
                        None
                        if match.snippet is None
                        else HelpSearchSnippet(match.snippet)
                    ),
                )
                for match in matches
            ],
        )
