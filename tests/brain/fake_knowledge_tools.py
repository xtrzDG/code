"""
In-memory stand-ins for the knowledge tools: search, price lookup, links.

Each fake implements the same UseCaseContract the conversation engine
depends on and remembers the queries it received.
"""

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.dto.knowledge import (
    KnowledgeItemView,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    PriceLookupQuery,
    PriceLookupResult,
    SendLinkQuery,
    SendLinkResult,
)
from app.schemas.typings.businesses.constrained_strings import WebLink


class FakeSearchKnowledge(
    UseCaseContract[KnowledgeSearchRequest, KnowledgeSearchResult]
):
    def __init__(self, items: list[KnowledgeItemView]) -> None:
        self.items: list[KnowledgeItemView] = items
        self.requests: list[KnowledgeSearchRequest] = []

    def run(self, input_data: KnowledgeSearchRequest) -> KnowledgeSearchResult:
        self.requests.append(input_data)
        query: str = str(input_data.query).casefold()
        matches: list[KnowledgeItemView] = [
            item
            for item in self.items
            if query in str(item.title).casefold()
            or (item.body is not None and query in str(item.body).casefold())
        ]
        return KnowledgeSearchResult(items=matches[: int(input_data.limit)])


class FakeGetPrice(UseCaseContract[PriceLookupQuery, PriceLookupResult]):
    def __init__(self, items: list[KnowledgeItemView]) -> None:
        self.items: list[KnowledgeItemView] = items
        self.queries: list[PriceLookupQuery] = []

    def run(self, input_data: PriceLookupQuery) -> PriceLookupResult:
        self.queries.append(input_data)
        name: str = str(input_data.item_name).casefold()
        return PriceLookupResult(
            matches=[
                item
                for item in self.items
                if item.price_minor is not None and name in str(item.title).casefold()
            ]
        )


class FakeSendLink(UseCaseContract[SendLinkQuery, SendLinkResult]):
    def __init__(self, links: dict[BusinessLinkKind, WebLink]) -> None:
        self.links: dict[BusinessLinkKind, WebLink] = links

    def run(self, input_data: SendLinkQuery) -> SendLinkResult:
        return SendLinkResult(kind=input_data.kind, url=self.links.get(input_data.kind))
