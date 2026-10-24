"""Request tools of the assistant: leads, handoffs and unanswered questions."""

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolOutcome,
    CreateLeadToolInput,
    HandoffToHumanToolInput,
    RecordUnansweredQuestionToolInput,
)
from app.schemas.dto.bookings import CreateLeadCommand, LeadView
from app.schemas.dto.conversations import LlmToolCall, LlmToolResult
from app.schemas.dto.handoffs import (
    HandoffCommand,
    HandoffResult,
    RecordUnansweredQuestionCommand,
    UnansweredQuestionView,
)
from app.use_cases.conversations.tools.tool_outcomes import success_outcome
from app.use_cases.conversations.tools.tool_phone_numbers import resolve_phone
from app.utilities.conversations.tool_payloads import (
    render_handoff,
    render_lead,
    render_unanswered_question,
)


def run_create_lead(
    create_lead: UseCaseContract[CreateLeadCommand, LeadView],
    phone_number_parser: PhoneNumberParserContract,
    call: LlmToolCall,
    context: AssistantToolContext,
) -> AssistantToolOutcome:
    tool_input = CreateLeadToolInput.model_validate_json(call.input_json)
    lead: LeadView = create_lead.run(
        CreateLeadCommand(
            business_id=context.business_id,
            contact_id=context.contact_id,
            conversation_id=context.conversation_id,
            contact_name=(
                tool_input.name if tool_input.name is not None else context.contact_name
            ),
            contact_phone_number=resolve_phone(
                phone_number_parser, tool_input.phone, context
            ),
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


def run_handoff_to_human(
    handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult],
    call: LlmToolCall,
    context: AssistantToolContext,
) -> AssistantToolOutcome:
    tool_input = HandoffToHumanToolInput.model_validate_json(call.input_json)
    result: HandoffResult = handoff_to_human.run(
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


def run_record_unanswered_question(
    record_unanswered_question: UseCaseContract[
        RecordUnansweredQuestionCommand, UnansweredQuestionView
    ],
    call: LlmToolCall,
    context: AssistantToolContext,
) -> AssistantToolOutcome:
    tool_input = RecordUnansweredQuestionToolInput.model_validate_json(call.input_json)
    question: UnansweredQuestionView = record_unanswered_question.run(
        RecordUnansweredQuestionCommand(
            business_id=context.business_id,
            question=tool_input.question,
            language=context.language,
            is_sandbox=context.is_sandbox,
        )
    )
    return success_outcome(call, render_unanswered_question(question))
