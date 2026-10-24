"""The assistant's waitlist tool: a place on the list for a full day."""

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolOutcome,
    JoinWaitlistToolInput,
)
from app.schemas.dto.conversations import LlmToolCall
from app.schemas.dto.growth.waitlist_joining import (
    DEFAULT_PARTY_SIZE,
    JoinWaitlistCommand,
    WaitlistJoinReceipt,
)
from app.use_cases.conversations.tools.booking_tool_handlers import (
    refuse_past_date,
    today_text,
)
from app.use_cases.conversations.tools.tool_outcomes import success_outcome
from app.utilities.conversations.business_today import BusinessToday
from app.utilities.conversations.waitlist_payloads import render_waitlist_join


def run_join_waitlist(
    join_waitlist: UseCaseContract[JoinWaitlistCommand, WaitlistJoinReceipt],
    call: LlmToolCall,
    context: AssistantToolContext,
    today: BusinessToday | None = None,
) -> AssistantToolOutcome:
    """
    The customer's wish on the waitlist of a day: contact, conversation,
    channel, language and sandbox from the server, the rest from the model;
    a past date is refused before anything is stored.
    """

    tool_input = JoinWaitlistToolInput.model_validate_json(call.input_json)
    past_date_error: AssistantToolOutcome | None = refuse_past_date(
        call, str(tool_input.date), today
    )
    if past_date_error is not None:
        return past_date_error

    receipt: WaitlistJoinReceipt = join_waitlist.run(
        JoinWaitlistCommand(
            business_id=context.business_id,
            contact_id=context.contact_id,
            conversation_id=context.conversation_id,
            contact_name=tool_input.name or context.contact_name,
            source_channel=context.channel,
            language=context.language,
            is_sandbox=context.is_sandbox,
            date=tool_input.date,
            time_from=tool_input.time_from,
            time_to=tool_input.time_to,
            party_size=tool_input.party_size or DEFAULT_PARTY_SIZE,
            nights=tool_input.nights,
            service_reference=tool_input.service_id,
            resource_reference=tool_input.resource_id,
            resource_kind=tool_input.resource_type,
            notes=tool_input.notes,
        )
    )
    return success_outcome(call, render_waitlist_join(receipt, today_text(today)))
