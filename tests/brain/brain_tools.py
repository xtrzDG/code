"""The fake tool use cases of a brain test world and the real tool runner."""

from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.knowledge import KnowledgeItemView
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.use_cases.conversations.tools.run_assistant_tool_use_case import (
    RunAssistantToolUseCase,
)
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from tests.brain.brain_repositories import BrainRepositories
from tests.brain.fake_tools import (
    FakeBookings,
    FakeCancelBooking,
    FakeCheckAvailability,
    FakeCreateBooking,
    FakeCreateLead,
    FakeGetPrice,
    FakeHandoff,
    FakeRecordUnansweredQuestion,
    FakeRescheduleBooking,
    FakeSearchKnowledge,
    FakeSendLink,
)


@dataclass(frozen=True)
class BrainTools:
    bookings: FakeBookings
    search_knowledge: FakeSearchKnowledge
    get_price: FakeGetPrice
    availability: FakeCheckAvailability
    create_lead: FakeCreateLead
    handoff: FakeHandoff
    record_question: FakeRecordUnansweredQuestion
    run_tool: RunAssistantToolUseCase


def build_brain_tools(
    repos: BrainRepositories,
    business: BusinessDocument,
    items: list[KnowledgeItemView],
    wall_clock: WallClock[Microseconds],
) -> BrainTools:
    bookings = FakeBookings(timezone=business.timezone)
    search_knowledge = FakeSearchKnowledge(items)
    get_price = FakeGetPrice(items)
    availability = FakeCheckAvailability(business.timezone, ["19:30", "20:00"])
    create_lead = FakeCreateLead()
    handoff = FakeHandoff(repos.handoff_repo, repos.conversation_repo, wall_clock)
    record_question = FakeRecordUnansweredQuestion()
    run_tool = RunAssistantToolUseCase(
        search_knowledge=search_knowledge,
        get_price=get_price,
        send_link=FakeSendLink(
            {BusinessLinkKind.MENU: WebLink("https://sakhli.example/menu")}
        ),
        check_availability=availability,
        create_booking=FakeCreateBooking(bookings),
        cancel_booking=FakeCancelBooking(bookings),
        reschedule_booking=FakeRescheduleBooking(bookings),
        create_lead=create_lead,
        handoff_to_human=handoff,
        record_unanswered_question=record_question,
        phone_number_parser=PhoneNumberParser(),
    )
    return BrainTools(
        bookings=bookings,
        search_knowledge=search_knowledge,
        get_price=get_price,
        availability=availability,
        create_lead=create_lead,
        handoff=handoff,
        record_question=record_question,
        run_tool=run_tool,
    )
