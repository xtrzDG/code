from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.bookable_offers import StayQuote
from app.schemas.dto.knowledge import PriceLookupQuery, PriceLookupResult
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.constrained_integers import NightCount
from app.utilities.bookings.stay_quotes import quote_stay
from app.utilities.knowledge.knowledge_item_views import to_item_view
from app.utilities.knowledge.ranking.price_matching import rank_price_matches
from app.utilities.scheduling.booking_placement import DEFAULT_NIGHT_COUNT
from app.utilities.scheduling.zoned_time import parse_local_date

MAX_PRICE_MATCHES: int = 5


class GetPriceUseCase(UseCaseContract[PriceLookupQuery, PriceLookupResult]):
    """
    Model tool get_price: priced active items that match a name, best first.

    Matching tolerates case, accents, inflection and typos in any script.
    Each match carries the price formatted in its currency for the request
    language; a room type also its seasonal nightly rates, and with a
    check-in date a quote for the stay (each night at its season's rate,
    "the deluxe room for 3 nights in August"). An empty result means "not
    in the price list", and the assistant may then name no price at all
    (concept section 5).
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
            if item.is_active and (item.price_minor is not None or item.seasonal_rates)
        ]
        matches: list[KnowledgeItemDocument] = [
            ranked_item.item
            for ranked_item in rank_price_matches(
                item_name=input_data.item_name,
                items=priced_items,
            )[:MAX_PRICE_MATCHES]
        ]
        return PriceLookupResult(
            matches=[
                to_item_view(item, business.currency_code, input_data.language)
                for item in matches
            ],
            stay_quotes=self._quote_stays(matches, business, input_data),
        )

    def _quote_stays(
        self,
        matches: list[KnowledgeItemDocument],
        business: BusinessDocument,
        query: PriceLookupQuery,
    ) -> list[StayQuote]:
        """Quotes of the matching room types for the asked stay, if any."""

        if query.check_in is None:
            return []

        quotes: list[StayQuote] = []
        for item in matches:
            if item.kind is not KnowledgeItemKind.ROOM_TYPE:
                continue

            quote: StayQuote | None = quote_stay(
                item,
                parse_local_date(query.check_in),
                NightCount(DEFAULT_NIGHT_COUNT)
                if query.nights is None
                else query.nights,
                business.currency_code,
            )
            if quote is not None:
                quotes.append(quote)

        return quotes
