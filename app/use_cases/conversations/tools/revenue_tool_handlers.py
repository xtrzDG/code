"""
The assistant's revenue tools: a place on the waitlist for a full day, and
the deposit that holds a booking or a banquet request (send_payment_link).
A new booking or banquet request that needs a deposit says so in its own
tool result, so the model asks it at once; the amount and the link never
come from the model.
"""

import logging
from dataclasses import dataclass

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.assistant_tools import AssistantToolContext, AssistantToolOutcome
from app.schemas.dto.conversations import LlmToolCall, LlmToolResult
from app.schemas.dto.deposits.payment_link_requests import (
    DepositQuote,
    DepositQuoteQuery,
    PaymentLinkReceipt,
    SendPaymentLinkCommand,
    SendPaymentLinkToolInput,
)
from app.schemas.dto.growth.waitlist_joining import (
    JoinWaitlistCommand,
    WaitlistJoinReceipt,
)
from app.use_cases.conversations.tools.tool_outcomes import (
    error_outcome,
    success_outcome,
)
from app.use_cases.conversations.tools.waitlist_tool_handlers import run_join_waitlist
from app.utilities.conversations.business_today import BusinessToday
from app.utilities.conversations.deposit_payloads import (
    render_payment_link_receipt,
    with_deposit_hint,
)
from app.utilities.deposits.deposit_amounts import deposit_amount_text

type SendPaymentLink = UseCaseContract[SendPaymentLinkCommand, PaymentLinkReceipt]
type QuoteDeposit = UseCaseContract[DepositQuoteQuery, DepositQuote]
LOGGER: logging.Logger = logging.getLogger(__name__)
# The tool results that may ask the model for a deposit next.
DEPOSIT_HINTED_TOOLS: frozenset[AssistantToolName] = frozenset(
    {AssistantToolName.CREATE_BOOKING, AssistantToolName.CREATE_LEAD}
)


@dataclass(frozen=True)
class RevenueTools:
    join_waitlist: UseCaseContract[JoinWaitlistCommand, WaitlistJoinReceipt] | None
    send_payment_link: SendPaymentLink | None
    quote_deposit: QuoteDeposit | None

    def run_join_waitlist(
        self,
        call: LlmToolCall,
        context: AssistantToolContext,
        today: BusinessToday | None,
    ) -> AssistantToolOutcome:
        if self.join_waitlist is None:
            return error_outcome(call, "This business keeps no waitlist.")

        return run_join_waitlist(self.join_waitlist, call, context, today)

    def run_send_payment_link(
        self, call: LlmToolCall, context: AssistantToolContext
    ) -> AssistantToolOutcome:
        if self.send_payment_link is None:
            return error_outcome(call, "This business takes no deposits.")

        tool_input = SendPaymentLinkToolInput.model_validate_json(call.input_json)
        receipt: PaymentLinkReceipt = self.send_payment_link.run(
            SendPaymentLinkCommand(
                business_id=context.business_id,
                contact_id=context.contact_id,
                conversation_id=context.conversation_id,
                source_channel=context.channel,
                language=context.language,
                is_sandbox=context.is_sandbox,
                booking_id=tool_input.booking_id,
                lead_id=tool_input.lead_id,
            )
        )
        return success_outcome(call, render_payment_link_receipt(receipt)).model_copy(
            update={"deposit_line": receipt.issued}
        )

    def with_deposit_hint(
        self, outcome: AssistantToolOutcome, context: AssistantToolContext
    ) -> AssistantToolOutcome:
        """
        A new booking or banquet request that needs a deposit, where the
        conversation offers send_payment_link, tells the model to call it.
        """

        if (
            self.quote_deposit is None
            or outcome.tool_name not in DEPOSIT_HINTED_TOOLS
            or outcome.result.is_error
            or AssistantToolName.SEND_PAYMENT_LINK not in context.available_tools
            or (outcome.booking_id is None and outcome.lead_id is None)
        ):
            return outcome

        try:
            quote: DepositQuote = self.quote_deposit.run(
                DepositQuoteQuery(
                    business_id=context.business_id,
                    booking_id=outcome.booking_id,
                    lead_id=outcome.lead_id,
                )
            )
        except Exception:
            # The booking stands; only the deposit's hint is missing.
            LOGGER.exception("The deposit of a new booking was not quoted.")
            return outcome

        if quote.amount is None:
            return outcome

        return outcome.model_copy(
            update={
                "result": LlmToolResult(
                    call_id=outcome.result.call_id,
                    result_json=with_deposit_hint(
                        outcome.result.result_json,
                        deposit_amount_text(quote.amount, context.language),
                    ),
                )
            }
        )
