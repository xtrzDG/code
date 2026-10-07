"""Example exchanges in the instruction, and the limited fact table of a big catalog."""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.businesses import BusinessDocument
from app.transformers.assembly.assistant_instruction_transformer import (
    AssistantInstructionTransformer,
)
from app.utilities.assembly.assistant_tools import select_assistant_tools
from app.utilities.assembly.fact_table_limits import LISTED_KNOWLEDGE_ITEMS
from tests.assembly.builders import build_menu_item
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.international_business_seeds import seed_online_shop
from tests.assembly.test_assistant_instruction import build_instruction_source
from tests.assembly.testbed import AssemblyTestbed


def example_section(prompt: str) -> str:
    return prompt.split("# Example exchanges\n")[1]


def seed_menu(testbed: AssemblyTestbed, business: BusinessDocument, count: int) -> None:
    for number in range(1, count + 1):
        testbed.knowledge_repo.save(
            build_menu_item(
                business,
                f"Dish {number:03d}",
                1000 + number,
                tags=["hot_soups" if number % 3 == 0 else "grill", "popular"]
                if number % 2 == 0
                else ["grill"],
            )
        )


def test_a_booking_business_sees_its_three_examples() -> None:
    testbed = AssemblyTestbed()
    prompt = str(testbed.assemble(seed_georgian_restaurant(testbed).id).prompt_text)
    section = example_section(prompt)

    assert section.startswith("They show how to behave, not what is true")
    assert "Confirming a booking:\nCustomer: A table for four" in section
    assert "A price that is not in the price list:\nCustomer:" in section
    assert "Handing off:\nCustomer:" in section
    assert prompt.index("# Answer format") < prompt.index("# Example exchanges")


def test_a_business_that_cannot_book_never_sees_a_booking_example() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    source = build_instruction_source(
        testbed,
        business,
        select_assistant_tools(takes_bookings=False, has_links=False),
    )

    prompt = str(AssistantInstructionTransformer().transform(source))

    assert "Confirming a booking" not in prompt
    assert "create_booking" not in example_section(prompt)
    assert "A price that is not in the price list" in prompt


def test_a_shop_confirms_an_order_request_instead() -> None:
    testbed = AssemblyTestbed()
    prompt = str(testbed.assemble(seed_online_shop(testbed).id).prompt_text)

    assert "Taking a request:\nCustomer: The black hoodie" in prompt
    assert "Confirming a booking" not in prompt


def test_no_examples_without_the_tools_they_show() -> None:
    testbed = AssemblyTestbed()
    source = build_instruction_source(
        testbed, seed_georgian_restaurant(testbed), [AssistantToolName.SEARCH_KNOWLEDGE]
    )

    prompt = str(AssistantInstructionTransformer().transform(source))

    assert "# Example exchanges" not in prompt


def test_up_to_eighty_items_every_item_is_listed() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    # 77 dishes plus the seed's 2 dishes and 1 question: exactly 80 items.
    seed_menu(testbed, business, 77)

    version = testbed.assemble(business.id)
    prompt = str(version.prompt_text)

    assert "- Menu item: Dish 077: Price: 10.77 GEL;" in prompt
    assert "Knowledge base:" not in prompt


def test_a_big_menu_lists_an_overview_and_the_first_thirty_items() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    seed_menu(testbed, business, 120)

    version = testbed.assemble(business.id)
    prompt = str(version.prompt_text)
    listed_items = [
        line for line in prompt.splitlines() if line.startswith("- Menu item: ")
    ]
    knowledge_rows = [
        line
        for line in prompt.splitlines()
        if line.startswith(("- Menu item: ", "- Question: "))
    ]

    # 120 dishes plus the seed's 2 dishes and 1 question: 123 items.
    assert len(knowledge_rows) == LISTED_KNOWLEDGE_ITEMS
    assert knowledge_rows[0].startswith("- Question: Is there parking?")
    assert listed_items[-1].startswith("- Menu item: Dish 029:")
    assert (
        "- Knowledge base: 123 items (1 questions, 122 menu items). Only the "
        "first 30 are listed here: find any other item with search_knowledge "
        "and its price with get_price before you say that something is not "
        "offered."
    ) in prompt
    assert (
        "- Categories of menu items: grill, popular, hot soups, vegetarian"
    ) in prompt
    assert prompt.index("- Knowledge base:") < prompt.index("- Question:")
    # The version keeps every row: the guard and the cabinet see them all.
    assert (
        len(
            [
                fact
                for fact in version.facts
                if str(fact.key).startswith(KnowledgeItemKind.MENU_ITEM.value)
            ]
        )
        == 122
    )
    assert "- Opening hours on Monday: 12:00–23:00" in prompt
    assert "- Default language: Georgian (ka)" in prompt
