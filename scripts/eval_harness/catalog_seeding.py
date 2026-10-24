"""
A big catalog for a dataset's business (`business.catalog`): generated
items of the business's first offer kind ("Kakheti herbal blend No. 1"
to "No. 90"), so the knowledge base holds more items than the
instruction's fact table lists (fact_table_limits) and the assistant has
to look the rest up with search_knowledge, as with a real big price list.
"""

from decimal import Decimal

from pydantic import Field
from typed_time_provider import Microseconds

from app.registries.demo.demo_foundation_parts import knowledge_item
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.utilities.money.money_math import build_money_from_major_units
from scripts.eval_harness.strict_model import StrictModel

NUMBER_PLACEHOLDER: str = "{n}"


class CatalogSpec(StrictModel):
    """
    `count` generated items: `title` and `body` with {n} for the item's
    number, each at `price` (major units of the business currency).
    """

    title: str
    body: str
    price: str
    count: int = Field(ge=1, le=300)


def build_catalog(
    business: BusinessDocument,
    catalog: CatalogSpec,
    kind: KnowledgeItemKind,
    now: Microseconds,
) -> list[KnowledgeItemDocument]:
    """The generated items, numbered from 1."""

    money = build_money_from_major_units(Decimal(catalog.price), business.currency_code)
    return [
        knowledge_item(
            business,
            kind,
            catalog.title.replace(NUMBER_PLACEHOLDER, str(number)),
            since=now,
            body=catalog.body.replace(NUMBER_PLACEHOLDER, str(number)),
            price_minor=int(money.amount_minor),
        )
        for number in range(1, catalog.count + 1)
    ]
