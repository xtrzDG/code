from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge import PriceLookupQuery, PriceLookupResult
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.knowledge.knowledge_items import to_item_view
from app.utilities.knowledge.lexical_ranking import RankedItem, rank_price_matches

MAX_PRICE_MATCHES: int = 5


class GetPriceUseCase(UseCaseContract[PriceLookupQuery, PriceLookupResult]):
    """
    Model tool get_price: priced active items that match a name, best first.

    Matching tolerates case, accents, inflection and typos in any script.
    Each match carries the price formatted in its currency for the request
    language. An empty result means "not in the price list", and the
    assistant may then name no price at all (concept section 5).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo

    def run(self, input_data: PriceLookupQuery) -> PriceLookupResult:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        priced_items: list[KnowledgeItemDocument] = [
            item
            for item in self._knowledge_item_repo.list_by_business(business.id)
            if item.is_active and item.price_minor is not None
        ]
        ranked_items: list[RankedItem] = rank_price_matches(
            item_name=input_data.item_name,
            items=priced_items,
        )
        return PriceLookupResult(
            matches=[
                to_item_view(
                    ranked_item.item,
                    business.currency_code,
                    input_data.language,
                )
                for ranked_item in ranked_items[:MAX_PRICE_MATCHES]
            ]
        )
