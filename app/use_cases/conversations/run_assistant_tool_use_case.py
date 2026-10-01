from collections.abc import Callable

from pydantic import ValidationError

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolInvocation,
    AssistantToolOutcome,
    CancelBookingToolInput,
    CheckAvailabilityToolInput,
    CreateBookingToolInput,
    CreateLeadToolInput,
    GetPriceToolInput,
    HandoffToHumanToolInput,
    RecordUnansweredQuestionToolInput,
    RescheduleBookingToolInput,
    SearchKnowledgeToolInput,
    SendLinkToolInput,
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
from app.schemas.dto.conversations import LlmToolCall, LlmToolResult
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
from app.schemas.typings.conversations.strings import LlmToolResultJson
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.utilities.conversations.tool_payloads import (
    describe_tool_input_error,
    render_availability,
    render_booking,
    render_handoff,
    render_knowledge_search,
    render_lead,
    render_link,
    render_price_lookup,
    render_tool_error,
    render_unanswered_question,
)

type ToolHandler = Callable[[LlmToolCall, AssistantToolContext], AssistantToolOutcome]


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
    contact's phone. A tool not offered in the conversation, invalid input
    or a business rule error (slot taken, unknown booking) becomes an error
    result the model can act on instead of an exception.
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
        self._handlers: dict[AssistantToolName, ToolHandler] = {
            AssistantToolName.SEARCH_KNOWLEDGE: self._run_search_knowledge,
            AssistantToolName.GET_PRICE: self._run_get_price,
            AssistantToolName.SEND_LINK: self._run_send_link,
            AssistantToolName.CHECK_AVAILABILITY: self._run_check_availability,
            AssistantToolName.CREATE_BOOKING: self._run_create_booking,
            AssistantToolName.CANCEL_BOOKING: self._run_cancel_booking,
            AssistantToolName.RESCHEDULE_BOOKING: self._run_reschedule_booking,
            AssistantToolName.CREATE_LEAD: self._run_create_lead,
            AssistantToolName.HANDOFF_TO_HUMAN: self._run_handoff_to_human,
            AssistantToolName.RECORD_UNANSWERED_QUESTION: (
                self._run_record_unanswered_question
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
            return error_outcome(call, describe_tool_input_error(error))
        except ApplicationError as error:
            return error_outcome(call, str(error) or type(error).__name__)

    def _run_search_knowledge(
        self,
        call: LlmToolCall,
        context: AssistantToolContext,
    ) -> AssistantToolOutcome:
        tool_input = SearchKnowledgeToolInput.model_validate_json(call.input_json)
        result: KnowledgeSearchResult = self._search_knowledge.run(
            KnowledgeSearchRequest(
                business_id=context.business_id,
                query=tool_input.query,
                language=(
                    tool_input.language
                    if tool_input.language is not None
                    else context.language
                ),
            )
        )
        return success_outcome(call, render_knowledge_search(result))

    def _run_get_price(
        self,
        call: LlmToolCall,
        context: AssistantToolContext,
    ) -> AssistantToolOutcome:
        tool_input = GetPriceToolInput.model_validate_json(call.input_json)
        result: PriceLookupResult = self._get_price.run(
            PriceLookupQuery(
                business_id=context.business_id,
                item_name=tool_input.item_name,
                language=context.language,
            )
        )
        return success_outcome(call, render_price_lookup(result))

    def _run_send_link(
        self,
        call: LlmToolCall,
        context: AssistantToolContext,
    ) -> AssistantToolOutcome:
        tool_input = SendLinkToolInput.model_validate_json(call.input_json)
        result: SendLinkResult = self._send_link.run(
            SendLinkQuery(business_id=context.business_id, kind=tool_input.kind)
        )
        return success_outcome(call, render_link(result))

    def _run_check_availability(
        self,
        call: LlmToolCall,
        context: AssistantToolContext,
    ) -> AssistantToolOutcome:
        tool_input = CheckAvailabilityToolInput.model_validate_json(call.input_json)
        result: AvailabilityResult = self._check_availability.run(
            AvailabilityQuery(
                business_id=context.business_id,
                date=tool_input.date,
                resource_kind=tool_input.resource_type,
                time=tool_input.time,
                party_size=tool_input.party_size,
                duration_minutes=tool_input.duration_minutes,
                nights=tool_input.nights,
                is_sandbox=context.is_sandbox,
            )
        )
        return success_outcome(call, render_availability(result))

    def _run_create_booking(
        self,
        call: LlmToolCall,
        context: AssistantToolContext,
    ) -> AssistantToolOutcome:
        tool_input = CreateBookingToolInput.model_validate_json(call.input_json)
        result: BookingResult = self._create_booking.run(
            CreateBookingCommand(
                business_id=context.business_id,
                contact_id=context.contact_id,
                conversation_id=context.conversation_id,
                contact_name=tool_input.name,
                contact_phone_number=self._resolve_phone(tool_input.phone, context),
                resource_kind=tool_input.resource_type,
                date=tool_input.date,
                time=tool_input.time,
                duration_minutes=tool_input.duration_minutes,
                nights=tool_input.nights,
                party_size=tool_input.party_size,
                notes=tool_input.notes,
                source_channel=context.channel,
                language=context.language,
                is_sandbox=context.is_sandbox,
            )
        )
        return AssistantToolOutcome(
            tool_name=call.tool_name,
            result=LlmToolResult(
                call_id=call.call_id, result_json=render_booking(result)
            ),
            booking_id=result.booking.id,
        )

    def _run_cancel_booking(
        self,
        call: LlmToolCall,
        context: AssistantToolContext,
    ) -> AssistantToolOutcome:
        tool_input = CancelBookingToolInput.model_validate_json(call.input_json)
        result: BookingResult = self._cancel_booking.run(
            CancelBookingCommand(
                business_id=context.business_id,
                contact_id=context.contact_id,
                booking_id=tool_input.booking_id,
                contact_phone_number=self._resolve_phone(tool_input.phone, context),
                date=tool_input.date,
                language=context.language,
            )
        )
        return success_outcome(call, render_booking(result))

    def _run_reschedule_booking(
        self,
        call: LlmToolCall,
        context: AssistantToolContext,
    ) -> AssistantToolOutcome:
        tool_input = RescheduleBookingToolInput.model_validate_json(call.input_json)
        result: BookingResult = self._reschedule_booking.run(
            RescheduleBookingCommand(
                business_id=context.business_id,
                contact_id=context.contact_id,
                booking_id=tool_input.booking_id,
                contact_phone_number=self._resolve_phone(tool_input.phone, context),
                old_date=tool_input.old_date,
                new_date=tool_input.new_date,
                new_time=tool_input.new_time,
                language=context.language,
            )
        )
        return success_outcome(call, render_booking(result))

    def _run_create_lead(
        self,
        call: LlmToolCall,
        context: AssistantToolContext,
    ) -> AssistantToolOutcome:
        tool_input = CreateLeadToolInput.model_validate_json(call.input_json)
        lead: LeadView = self._create_lead.run(
            CreateLeadCommand(
                business_id=context.business_id,
                contact_id=context.contact_id,
                conversation_id=context.conversation_id,
                contact_name=(
                    tool_input.name
                    if tool_input.name is not None
                    else context.contact_name
                ),
                contact_phone_number=self._resolve_phone(tool_input.phone, context),
                lead_type=tool_input.lead_type,
                details=tool_input.details,
                requested_date=tool_input.requested_date,
                party_size=tool_input.party_size,
                budget=tool_input.budget,
                source_channel=context.channel,
                language=context.language,
                is_sandbox=context.is_sandbox,
            )
        )
        return AssistantToolOutcome(
            tool_name=call.tool_name,
            result=LlmToolResult(call_id=call.call_id, result_json=render_lead(lead)),
            lead_id=lead.id,
        )

    def _run_handoff_to_human(
        self,
        call: LlmToolCall,
        context: AssistantToolContext,
    ) -> AssistantToolOutcome:
        tool_input = HandoffToHumanToolInput.model_validate_json(call.input_json)
        result: HandoffResult = self._handoff_to_human.run(
            HandoffCommand(
                business_id=context.business_id,
                conversation_id=context.conversation_id,
                contact_id=context.contact_id,
                reason=tool_input.reason,
                summary=tool_input.summary,
                urgency=tool_input.urgency,
                source_channel=context.channel,
                language=context.language,
                is_sandbox=context.is_sandbox,
            )
        )
        return AssistantToolOutcome(
            tool_name=call.tool_name,
            result=LlmToolResult(
                call_id=call.call_id,
                result_json=render_handoff(result),
            ),
            handoff_id=result.id,
        )

    def _run_record_unanswered_question(
        self,
        call: LlmToolCall,
        context: AssistantToolContext,
    ) -> AssistantToolOutcome:
        tool_input = RecordUnansweredQuestionToolInput.model_validate_json(
            call.input_json
        )
        question: UnansweredQuestionView = self._record_unanswered_question.run(
            RecordUnansweredQuestionCommand(
                business_id=context.business_id,
                question=tool_input.question,
                language=context.language,
                is_sandbox=context.is_sandbox,
            )
        )
        return success_outcome(call, render_unanswered_question(question))

    def _resolve_phone(
        self,
        raw_phone_number: RawPhoneNumberInput | None,
        context: AssistantToolContext,
    ) -> E164PhoneNumber | None:
        """
        Phone from the model in E.164, read with the business country for
        national formats; the contact's phone when the model gives none.

        Raises:
            InvalidPhoneNumberError: the model passed something that is not
                a phone number of any country.
        """

        if raw_phone_number is None or str(raw_phone_number).strip() == "":
            return context.contact_phone_number

        return self._phone_number_parser.parse(
            raw_phone_number,
            context.business_country_code,
        ).e164


def success_outcome(
    call: LlmToolCall,
    result_json: LlmToolResultJson,
) -> AssistantToolOutcome:
    return AssistantToolOutcome(
        tool_name=call.tool_name,
        result=LlmToolResult(call_id=call.call_id, result_json=result_json),
    )


def error_outcome(call: LlmToolCall, message: str) -> AssistantToolOutcome:
    return AssistantToolOutcome(
        tool_name=call.tool_name,
        result=LlmToolResult(
            call_id=call.call_id,
            result_json=render_tool_error(message),
            is_error=True,
        ),
    )
