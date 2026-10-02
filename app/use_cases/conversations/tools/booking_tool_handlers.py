"""Booking tools of the assistant: availability, booking, cancelling, moving."""

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolOutcome,
    CancelBookingToolInput,
    CheckAvailabilityToolInput,
    CreateBookingToolInput,
    RescheduleBookingToolInput,
)
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    BookingResult,
    CancelBookingCommand,
    CreateBookingCommand,
    RescheduleBookingCommand,
)
from app.schemas.dto.conversations import LlmToolCall, LlmToolResult
from app.use_cases.conversations.tools.tool_outcomes import success_outcome
from app.use_cases.conversations.tools.tool_phone_numbers import (
    require_verified_phone,
    resolve_phone,
)
from app.utilities.conversations.tool_payloads import (
    render_availability,
    render_booking,
)


def run_check_availability(
    check_availability: UseCaseContract[AvailabilityQuery, AvailabilityResult],
    call: LlmToolCall,
    context: AssistantToolContext,
) -> AssistantToolOutcome:
    tool_input = CheckAvailabilityToolInput.model_validate_json(call.input_json)
    result: AvailabilityResult = check_availability.run(
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


def run_create_booking(
    create_booking: UseCaseContract[CreateBookingCommand, BookingResult],
    phone_number_parser: PhoneNumberParserContract,
    call: LlmToolCall,
    context: AssistantToolContext,
) -> AssistantToolOutcome:
    tool_input = CreateBookingToolInput.model_validate_json(call.input_json)
    result: BookingResult = create_booking.run(
        CreateBookingCommand(
            business_id=context.business_id,
            contact_id=context.contact_id,
            conversation_id=context.conversation_id,
            contact_name=tool_input.name,
            contact_phone_number=resolve_phone(
                phone_number_parser, tool_input.phone, context
            ),
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
        result=LlmToolResult(call_id=call.call_id, result_json=render_booking(result)),
        booking_id=result.booking.id,
    )


def run_cancel_booking(
    cancel_booking: UseCaseContract[CancelBookingCommand, BookingResult],
    phone_number_parser: PhoneNumberParserContract,
    call: LlmToolCall,
    context: AssistantToolContext,
) -> AssistantToolOutcome:
    tool_input = CancelBookingToolInput.model_validate_json(call.input_json)
    result: BookingResult = cancel_booking.run(
        CancelBookingCommand(
            business_id=context.business_id,
            contact_id=context.contact_id,
            booking_id=tool_input.booking_id,
            contact_phone_number=require_verified_phone(
                phone_number_parser, tool_input.phone, context
            ),
            date=tool_input.date,
            language=context.language,
            is_sandbox=context.is_sandbox,
        )
    )
    return success_outcome(call, render_booking(result))


def run_reschedule_booking(
    reschedule_booking: UseCaseContract[RescheduleBookingCommand, BookingResult],
    phone_number_parser: PhoneNumberParserContract,
    call: LlmToolCall,
    context: AssistantToolContext,
) -> AssistantToolOutcome:
    tool_input = RescheduleBookingToolInput.model_validate_json(call.input_json)
    result: BookingResult = reschedule_booking.run(
        RescheduleBookingCommand(
            business_id=context.business_id,
            contact_id=context.contact_id,
            booking_id=tool_input.booking_id,
            contact_phone_number=require_verified_phone(
                phone_number_parser, tool_input.phone, context
            ),
            is_sandbox=context.is_sandbox,
            old_date=tool_input.old_date,
            new_date=tool_input.new_date,
            new_time=tool_input.new_time,
            language=context.language,
        )
    )
    return success_outcome(call, render_booking(result))
