"""Adding, searching and pricing knowledge items, and saving profile steps."""

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.knowledge import KnowledgeSearchRequest, PriceLookupQuery
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    KnowledgeItemDetails,
    KnowledgeItemInput,
)
from app.schemas.dto.profiles.profile_steps import (
    ProfileStepInput,
    SaveProfileStepCommand,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.knowledge.constrained_integers import KnowledgeSearchLimit
from app.schemas.typings.knowledge.strings import (
    KnowledgeBody,
    KnowledgeSearchQuery,
    KnowledgeTitle,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from tests.knowledge.harness import KnowledgeHarness


def add_item(
    harness: KnowledgeHarness,
    business: BusinessDocument,
    title: str,
    kind: KnowledgeItemKind = KnowledgeItemKind.MENU_ITEM,
    price_minor: int | None = None,
    body: str | None = None,
    is_active: bool = True,
    languages: tuple[str, ...] = (),
) -> KnowledgeItemDetails:
    return harness.create_knowledge_item.run(
        CreateKnowledgeItemCommand(
            business_id=business.id,
            item=KnowledgeItemInput(
                kind=kind,
                title=KnowledgeTitle(title),
                body=None if body is None else KnowledgeBody(body),
                price_minor=(
                    None if price_minor is None else MoneyAmountMinor(price_minor)
                ),
                is_active=is_active,
                languages=[LanguageTag(language) for language in languages],
            ),
        )
    )


def search(
    harness: KnowledgeHarness,
    business: BusinessDocument,
    query: str,
    language: str,
    limit: int = 5,
) -> list[str]:
    result = harness.search_knowledge.run(
        KnowledgeSearchRequest(
            business_id=business.id,
            query=KnowledgeSearchQuery(query),
            language=LanguageTag(language),
            limit=KnowledgeSearchLimit(limit),
        )
    )
    return [item.title for item in result.items]


def price_titles(
    harness: KnowledgeHarness,
    business: BusinessDocument,
    item_name: str,
    language: str = "en",
) -> list[str]:
    result = harness.get_price.run(
        PriceLookupQuery(
            business_id=business.id,
            item_name=KnowledgeTitle(item_name),
            language=LanguageTag(language),
        )
    )
    return [match.title for match in result.matches]


def save_step(
    harness: KnowledgeHarness,
    business: BusinessDocument,
    step_input: ProfileStepInput,
) -> None:
    harness.save_profile_step.run(
        SaveProfileStepCommand(
            business_id=business.id,
            actor_id=UserId(),
            step_input=step_input,
        )
    )
