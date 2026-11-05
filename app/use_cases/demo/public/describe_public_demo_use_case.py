from app.contracts.localization_utilities import (
    LanguageDetectorContract,
    LocalizedTextResolverContract,
)
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.public_demo import PublicDemoCard, PublicDemoCardQuery
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.utilities.channels.widget_starters import build_starter_questions

# The starter chips come from the first FAQ items, as in the website chat.
FAQ_ITEMS_READ_FOR_STARTERS: DocumentQueryLimit = DocumentQueryLimit(30)


class DescribePublicDemoUseCase(UseCaseContract[PublicDemoCardQuery, PublicDemoCard]):
    """
    One demo business as the landing page offers it: its name, kind of
    business named in the visitor's language, city, the languages its
    published assistant answers in and up to three starter questions per
    language from its FAQ. Nothing personal or secret is returned. Runs in
    the business's storage scope.

    Raises:
        NotFoundError: the business does not exist or has no published
            assistant yet (the landing page leaves it out).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        localized_text_resolver: LocalizedTextResolverContract,
        language_detector: LanguageDetectorContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._language_detector: LanguageDetectorContract = language_detector

    def run(self, input_data: PublicDemoCardQuery) -> PublicDemoCard:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None or business.published_assistant_version_id is None:
            raise NotFoundError("This demo is not available.")

        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business.id, business.published_assistant_version_id
        )
        languages = list(business.languages if version is None else version.languages)
        return PublicDemoCard(
            business_id=business.id,
            business_name=business.name,
            niche_key=business.niche_key,
            niche_name=self._resolver.resolve(
                self._niche_template_registry.get(business.niche_key).names,
                input_data.language,
            ),
            city=business.city,
            country_code=business.country_code,
            default_language=business.default_language,
            languages=languages,
            starters=build_starter_questions(
                self._knowledge_item_repo.list_by_kind(
                    business.id, KnowledgeItemKind.FAQ, FAQ_ITEMS_READ_FOR_STARTERS
                ),
                languages,
                business.default_language,
                self._language_detector,
            ),
        )
