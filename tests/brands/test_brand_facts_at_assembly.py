"""
A brand location's assistant is built from its own knowledge and the facts
its brand shares (merged at assembly): the version's fact table carries a
shared fact, a location item with the same key replaces it (an inactive
one hides it), a shared price in another currency is left out, and the
autotests and the quick check of "Apply changes" ask the shared prices.
"""

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.brands import BrandDocument, BrandKnowledgeItemDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.assistants.assistant_views import AssistantVersionDetails
from app.schemas.dto.assistants.autotest_runs import AutotestPlanningRequest
from app.schemas.dto.setup.apply_changes import AppliedVersion
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.knowledge.constrained_strings import KnowledgeShareKey
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.use_cases.autotests.plan_autotest_scenarios_use_case import (
    PlanAutotestScenariosUseCase,
)
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.testbed import AssemblyTestbed
from tests.brands.brand_builders import build_brand, build_shared_fact

SHARED_WIFI: str = "Wi-Fi password: the brand's answer."


def brand_location(testbed: AssemblyTestbed) -> tuple[BusinessDocument, BrandDocument]:
    """The seeded Tbilisi restaurant (GEL), now a location of a brand."""

    seeded = seed_georgian_restaurant(testbed)
    brand = build_brand(seeded.members[0].user_id)
    business = seeded.model_copy(update={"brand_id": brand.id})
    testbed.business_repo.save(business)
    testbed.brand_knowledge_repo.add(build_shared_fact(brand, "wifi", "Wi-Fi password"))
    return business, brand


def shared_dish(
    brand: BrandDocument, key: str, title: str, price: int, currency: str
) -> BrandKnowledgeItemDocument:
    return build_shared_fact(brand, key, title, price, currency).model_copy(
        update={"kind": KnowledgeItemKind.MENU_ITEM, "body": None}
    )


def fact_values(version: AssistantVersionDetails) -> list[str]:
    return [str(fact.value) for fact in version.facts]


def save_own_answer(
    testbed: AssemblyTestbed, business: BusinessDocument, body: str, is_active: bool
) -> KnowledgeItemDocument:
    """The location's own answer to the shared Wi-Fi question (same key)."""

    item = KnowledgeItemDocument(
        business_id=business.id,
        kind=KnowledgeItemKind.FAQ,
        title=KnowledgeTitle("Wi-Fi password"),
        body=KnowledgeBody(body),
        is_active=is_active,
        shared_key=KnowledgeShareKey("wifi"),
    )
    testbed.knowledge_repo.save(item)
    return item


def test_a_version_answers_with_the_brand_s_shared_fact() -> None:
    testbed = AssemblyTestbed()
    business, _ = brand_location(testbed)

    values = fact_values(testbed.assemble(business.id))

    assert SHARED_WIFI in values


def test_the_location_s_own_answer_replaces_the_shared_one() -> None:
    testbed = AssemblyTestbed()
    business, _ = brand_location(testbed)
    own = save_own_answer(testbed, business, "Ask the waiter for it.", True)

    replaced = fact_values(testbed.assemble(business.id))
    testbed.knowledge_repo.save(own.model_copy(update={"is_active": False}))
    hidden = fact_values(testbed.assemble(business.id))

    assert "Ask the waiter for it." in replaced
    assert SHARED_WIFI not in replaced
    assert not any("Wi-Fi" in value or "waiter" in value for value in hidden)


def test_a_shared_price_in_another_currency_is_never_named() -> None:
    testbed = AssemblyTestbed()
    business, brand = brand_location(testbed)
    testbed.brand_knowledge_repo.add(
        shared_dish(brand, "lobiani", "Lobiani", 900, "GEL")
    )
    testbed.brand_knowledge_repo.add(
        shared_dish(brand, "strudel", "Apple strudel", 650, "EUR")
    )

    version = testbed.assemble(business.id)
    facts = {str(fact.label): str(fact.value) for fact in version.facts}

    assert facts["Menu item: Lobiani"] == "Price: 9.00 GEL"
    assert "Price" not in facts.get("Menu item: Apple strudel", "")
    assert not any("EUR" in value for value in facts.values())


def test_the_autotests_ask_the_shared_prices_of_the_location_s_currency() -> None:
    testbed = AssemblyTestbed()
    business, brand = brand_location(testbed)
    testbed.brand_knowledge_repo.add(
        shared_dish(brand, "lobiani", "Lobiani", 900, "GEL")
    )
    testbed.brand_knowledge_repo.add(
        shared_dish(brand, "strudel", "Apple strudel", 650, "EUR")
    )
    version = testbed.version(business.id, testbed.assemble(business.id).id)

    planning = planner(testbed).run(
        AutotestPlanningRequest(
            business=business,
            version=version,
            kinds=[AutotestScenarioKind.PRICE_QUESTION],
        )
    )
    asked = {
        str(scenario.goal): [
            int(price.amount_minor) for price in scenario.expected_prices
        ]
        for scenario in planning.scenarios
    }

    assert asked['Ask how much "Lobiani" costs.'] == [900]
    assert not any("strudel" in goal for goal in asked)


def test_the_quick_check_asks_a_shared_price_that_changed() -> None:
    testbed = AssemblyTestbed()
    business, brand = brand_location(testbed)
    testbed.brand_knowledge_repo.add(
        shared_dish(brand, "lobiani", "Lobiani", 900, "GEL")
    )
    live = testbed.assemble(business.id)
    testbed.business_repo.save(
        business.model_copy(update={"published_assistant_version_id": live.id})
    )
    testbed.brand_knowledge_repo.modify(
        brand.id,
        KnowledgeShareKey("lobiani"),
        lambda stored: stored.model_copy(
            update={"price_minor": MoneyAmountMinor(1100)}
        ),
    )
    changed = testbed.assemble(business.id)

    selection = testbed.select_smoke_checks_use_case.run(
        AppliedVersion(business_id=business.id, assistant_version_id=changed.id)
    )

    assert selection is not None
    assert [str(title) for title in selection.price_item_titles] == ["Lobiani"]


def planner(testbed: AssemblyTestbed) -> PlanAutotestScenariosUseCase:
    return PlanAutotestScenariosUseCase(
        business_profile_repo=testbed.profile_repo,
        knowledge_item_repo=testbed.knowledge_repo,
        brand_knowledge_item_repo=testbed.brand_knowledge_repo,
        resource_repo=testbed.resource_repo,
        autotest_case_repo=testbed.autotest_case_repo,
        niche_template_registry=testbed.niche_registry,
        language_registry=testbed.language_registry,
    )
