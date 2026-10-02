import logging
from collections.abc import Callable

from pydantic import ValidationError
from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolInvocation,
    AssistantToolOutcome,
)
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    BookingResult,
    CancelBookingCommand,
    CreateBookingCommand,
    CreateLeadCommand,
    LeadView,
    RescheduleBookingCommand,
)
from app.schemas.dto.conversations import LlmToolCall
from app.schemas.dto.handoffs import (
    HandoffCommand,
    HandoffResult,
    RecordUnansweredQuestionCommand,
    UnansweredQuestionView,
)
from app.schemas.dto.knowledge import (
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    PriceLookupQuery,
    PriceLookupResult,
    SendLinkQuery,
    SendLinkResult,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.use_cases.conversations.tools.booking_tool_handlers import (
    run_cancel_booking,
    run_check_availability,
    run_create_booking,
    run_reschedule_booking,
)
from app.use_cases.conversations.tools.knowledge_tool_handlers import (
    run_get_price,
    run_search_knowledge,
    run_send_link,
)
from app.use_cases.conversations.tools.request_tool_handlers import (
    run_create_lead,
    run_handoff_to_human,
    run_record_unanswered_question,
)
from app.use_cases.conversations.tools.tool_outcomes import error_outcome
from app.utilities.conversations.business_today import (
    SCHEDULING_TOOLS,
    BusinessToday,
    find_business_today,
)
from app.utilities.conversations.tool_payloads import (
    describe_tool_input_error,
)

type ToolHandler = Callable[[LlmToolCall, AssistantToolContext], AssistantToolOutcome]

logger: logging.Logger = logging.getLogger(__name__)
UNEXPECTED_TOOL_ERROR: str = (
    "The tool failed; try again once, otherwise offer to pass the request to a "
    "colleague."
)


class RunAssistantToolUseCase(
    UseCaseContract[AssistantToolInvocation, AssistantToolOutcome]
):
    """
    Execute one model tool call with the server-side context (concept
    section 5: "tools check their arguments themselves").

    The input is validated with the tool's strict DTO; business, contact,
    conversation, channel, language and sandbox flag come from the context,
    never from the model. Phones the model passes are parsed with the
    business country as the hint; a missing phone falls back to the
    contact's phone. Cancelling or moving a booking is a customer request
    for the customer's own bookings only: they are found by the contact and
    by the phone the channel proved, never by a phone the customer typed
    (anyone can type someone else's number), and only in the conversation's
    sandbox mode. A tool not offered in the conversation, invalid input or
    a business rule error (slot taken, unknown booking) becomes an error
    result the model can act on instead of an exception. Availability and
    booking results and their errors state today at the business
    (`business_today`), and a date that has already passed is refused.
    """

    def __init__(
        self,
        search_knowledge: UseCaseContract[
            KnowledgeSearchRequest, KnowledgeSearchResult
        ],
        get_price: UseCaseContract[PriceLookupQuery, PriceLookupResult],
        send_link: UseCaseContract[SendLinkQuery, SendLinkResult],
        check_availability: UseCaseContract[AvailabilityQuery, AvailabilityResult],
        create_booking: UseCaseContract[CreateBookingCommand, BookingResult],
        cancel_booking: UseCaseContract[CancelBookingCommand, BookingResult],
        reschedule_booking: UseCaseContract[RescheduleBookingCommand, BookingResult],
        create_lead: UseCaseContract[CreateLeadCommand, LeadView],
        handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult],
        record_unanswered_question: UseCaseContract[
            RecordUnansweredQuestionCommand, UnansweredQuestionView
        ],
        phone_number_parser: PhoneNumberParserContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._search_knowledge: UseCaseContract[
            KnowledgeSearchRequest, KnowledgeSearchResult
        ] = search_knowledge
        self._get_price: UseCaseContract[PriceLookupQuery, PriceLookupResult] = (
            get_price
        )
        self._send_link: UseCaseContract[SendLinkQuery, SendLinkResult] = send_link
        self._check_availability: UseCaseContract[
            AvailabilityQuery, AvailabilityResult
        ] = check_availability
        self._create_booking: UseCaseContract[CreateBookingCommand, BookingResult] = (
            create_booking
        )
        self._cancel_booking: UseCaseContract[CancelBookingCommand, BookingResult] = (
            cancel_booking
        )
        self._reschedule_booking: UseCaseContract[
            RescheduleBookingCommand, BookingResult
        ] = reschedule_booking
        self._create_lead: UseCaseContract[CreateLeadCommand, LeadView] = create_lead
        self._handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult] = (
            handoff_to_human
        )
        self._record_unanswered_question: UseCaseContract[
            RecordUnansweredQuestionCommand, UnansweredQuestionView
        ] = record_unanswered_question
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._handlers: dict[AssistantToolName, ToolHandler] = {
            AssistantToolName.SEARCH_KNOWLEDGE: lambda call, context: (
                run_search_knowledge(self._search_knowledge, call, context)
            ),
            AssistantToolName.GET_PRICE: lambda call, context: run_get_price(
                self._get_price, call, context
            ),
            AssistantToolName.SEND_LINK: lambda call, context: run_send_link(
                self._send_link, call, context
            ),
            AssistantToolName.CHECK_AVAILABILITY: lambda call, context: (
                run_check_availability(
                    self._check_availability, call, context, self._today(context)
                )
            ),
            AssistantToolName.CREATE_BOOKING: lambda call, context: run_create_booking(
                self._create_booking,
                self._phone_number_parser,
                call,
                context,
                self._today(context),
            ),
            AssistantToolName.CANCEL_BOOKING: lambda call, context: run_cancel_booking(
                self._cancel_booking,
                self._phone_number_parser,
                call,
                context,
                self._today(context),
            ),
            AssistantToolName.RESCHEDULE_BOOKING: lambda call, context: (
                run_reschedule_booking(
                    self._reschedule_booking,
                    self._phone_number_parser,
                    call,
                    context,
                    self._today(context),
                )
            ),
            AssistantToolName.CREATE_LEAD: lambda call, context: run_create_lead(
                self._create_lead, self._phone_number_parser, call, context
            ),
            AssistantToolName.HANDOFF_TO_HUMAN: lambda call, context: (
                run_handoff_to_human(self._handoff_to_human, call, context)
            ),
            AssistantToolName.RECORD_UNANSWERED_QUESTION: lambda call, context: (
                run_record_unanswered_question(
                    self._record_unanswered_question, call, context
                )
            ),
        }

    def run(self, input_data: AssistantToolInvocation) -> AssistantToolOutcome:
        call: LlmToolCall = input_data.call
        context: AssistantToolContext = input_data.context
        if call.tool_name not in context.available_tools:
            return error_outcome(
                call,
                f"Tool {call.tool_name} is not available in this conversation.",
            )

        try:
            return self._handlers[call.tool_name](call, context)
        except ValidationError as error:
            return error_outcome(
                call, describe_tool_input_error(error), self._today_text(call, context)
            )
        except ApplicationError as error:
            return error_outcome(
                call,
                str(error) or type(error).__name__,
                self._today_text(call, context),
            )
        except Exception:
            # A bug must not cost the customer the reply: the model gets an
            # error result it can act on, and the error is reported.
            logger.exception("Tool %s failed unexpectedly.", call.tool_name)
            return error_outcome(call, UNEXPECTED_TOOL_ERROR)

    def _today(self, context: AssistantToolContext) -> BusinessToday | None:
        """Today at the business, when its time zone is known."""

        if context.business_timezone is None:
            return None

        return find_business_today(
            self._wall_clock.now_unix(), context.business_timezone
        )

    def _today_text(
        self, call: LlmToolCall, context: AssistantToolContext
    ) -> str | None:
        """Today for an error of a scheduling tool, so a wrong date is caught."""

        if call.tool_name not in SCHEDULING_TOOLS:
            return None

        today: BusinessToday | None = self._today(context)
        return None if today is None else today.text
