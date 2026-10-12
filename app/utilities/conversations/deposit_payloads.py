"""
The deposit as the language model reads it: what send_payment_link did,
and the hint a new booking or banquet request carries when it needs one.
The link and the payment reference are never in a tool result (the link
may carry the owner's key, and the model must write neither): the payment
line with both goes under the reply.
"""

import json
from typing import cast

from app.schemas.constants.deposits import PaymentLinkOutcome
from app.schemas.dto.deposits.payment_link_requests import PaymentLinkReceipt
from app.schemas.typings.conversations.strings import LlmToolResultJson
from app.schemas.typings.localization.strings import FormattedMoneyText
from app.utilities.conversations.tool_payloads import render

SENT_NOTE: str = (
    "The payment line with the amount, the link and the reference is added "
    "under your reply by the system. Do not write a link, an amount or a "
    "reference for the deposit; say in one or two short sentences that the "
    "place is held until held_until and is confirmed once the deposit is paid."
)
NOT_REQUIRED_NOTE: str = (
    "No deposit is needed for this: do not mention one, and continue."
)
ALREADY_PAID_NOTE: str = (
    "The deposit is paid already: the booking stands; ask for nothing more."
)
REQUIRED_HINT: str = (
    "This needs a deposit: call send_payment_link now, before you answer."
)


def render_payment_link_receipt(receipt: PaymentLinkReceipt) -> LlmToolResultJson:
    if receipt.outcome is PaymentLinkOutcome.NOT_REQUIRED:
        return render(
            {
                "status": receipt.outcome.value,
                "reason": None
                if receipt.exemption is None
                else receipt.exemption.value,
                "note": NOT_REQUIRED_NOTE,
            }
        )

    if receipt.outcome is PaymentLinkOutcome.ALREADY_PAID:
        return render({"status": receipt.outcome.value, "note": ALREADY_PAID_NOTE})

    return render(
        {
            "status": receipt.outcome.value,
            "deposit": None
            if receipt.amount_text is None
            else str(receipt.amount_text),
            "held_until": (
                None
                if receipt.held_until_text is None
                else str(receipt.held_until_text)
            ),
            "note": SENT_NOTE,
        }
    )


def with_deposit_hint(
    result_json: LlmToolResultJson, amount_text: FormattedMoneyText
) -> LlmToolResultJson:
    """A create_booking or create_lead result telling the model to ask the deposit."""

    payload: object = json.loads(str(result_json))
    if not isinstance(payload, dict):
        return result_json

    hinted: dict[str, object] = dict(cast(dict[str, object], payload))
    hinted["deposit_required"] = True
    hinted["deposit"] = str(amount_text)
    hinted["deposit_note"] = REQUIRED_HINT
    return render(hinted)
