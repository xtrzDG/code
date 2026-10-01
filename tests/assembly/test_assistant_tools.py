from app.schemas.constants.assistants import AssistantToolName
from app.schemas.domain.resources import ResourceDocument
from app.utilities.assembly.assistant_tools import (
    BOOKING_TOOLS,
    can_take_bookings,
    select_assistant_tools,
)
from tests.assembly.builders import (
    seed_georgian_restaurant,
    seed_israeli_clinic,
    seed_japanese_restaurant,
    seed_online_shop,
)
from tests.assembly.testbed import AssemblyTestbed


def test_restaurant_with_tables_rules_and_links_gets_all_ten_tools() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)

    version = testbed.assemble(business.id)

    assert version.tools == list(AssistantToolName)
    assert len(version.tools) == 10


def test_clinic_books_doctors_but_has_no_links() -> None:
    testbed = AssemblyTestbed()
    version = testbed.assemble(seed_israeli_clinic(testbed).id)

    assert AssistantToolName.CREATE_BOOKING in version.tools
    assert AssistantToolName.SEND_LINK not in version.tools
    assert len(version.tools) == 9


def test_online_shop_takes_orders_as_leads() -> None:
    testbed = AssemblyTestbed()
    version = testbed.assemble(seed_online_shop(testbed).id)

    assert version.tools == [
        AssistantToolName.SEARCH_KNOWLEDGE,
        AssistantToolName.GET_PRICE,
        AssistantToolName.CREATE_LEAD,
        AssistantToolName.HANDOFF_TO_HUMAN,
        AssistantToolName.RECORD_UNANSWERED_QUESTION,
    ]


def test_booking_needs_rules_and_an_active_resource() -> None:
    testbed = AssemblyTestbed()
    business = seed_japanese_restaurant(testbed)
    profile = testbed.profile_repo.get_by_business(business.id)
    assert profile is not None
    resources: list[ResourceDocument] = testbed.resource_repo.list_by_business(
        business.id
    )
    inactive_resources = [
        resource.model_copy(update={"is_active": False}) for resource in resources
    ]
    profile_without_rules = profile.model_copy(update={"booking_rules": None})

    assert can_take_bookings(profile, resources)
    assert not can_take_bookings(profile, inactive_resources)
    assert not can_take_bookings(profile, [])
    assert not can_take_bookings(profile_without_rules, resources)


def test_tool_selection_keeps_declaration_order() -> None:
    no_bookings_no_links = select_assistant_tools(takes_bookings=False, has_links=False)
    bookings_only = select_assistant_tools(takes_bookings=True, has_links=False)
    links_only = select_assistant_tools(takes_bookings=False, has_links=True)

    assert not BOOKING_TOOLS & set(no_bookings_no_links)
    assert set(bookings_only) >= BOOKING_TOOLS
    assert AssistantToolName.SEND_LINK in links_only
    for tools in (no_bookings_no_links, bookings_only, links_only):
        assert tools == [tool for tool in AssistantToolName if tool in tools]
        assert AssistantToolName.HANDOFF_TO_HUMAN in tools
        assert AssistantToolName.GET_PRICE in tools
