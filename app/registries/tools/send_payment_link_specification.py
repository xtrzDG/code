"""The send_payment_link model tool: the deposit's payment line for a booking."""

from app.registries.tools.tool_schema_parts import (
    JsonSchema,
    nullable,
    object_schema,
    string_property,
)

SEND_PAYMENT_LINK_SPECIFICATION: tuple[str, JsonSchema] = (
    "Ask the deposit that holds a booking or a banquet request. Call it right "
    "after create_booking or create_lead when their result says "
    "deposit_required, or when the customer asks for the payment link again. "
    "The amount and the link come from the business: the system adds the "
    "payment line under your reply, so never write a link, an amount or a "
    "reference for the deposit yourself; say in a few words that the place "
    "is held until held_until and confirmed once the deposit is paid. When "
    "the result says not_required or already_paid, ask for no deposit.",
    object_schema(
        {
            "booking_id": nullable(
                string_property("Booking id from create_booking, if known.")
            ),
            "lead_id": nullable(
                string_property("Request id from create_lead, if known.")
            ),
        }
    ),
)
