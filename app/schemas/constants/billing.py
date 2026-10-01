from enum import StrEnum


class PlanKey(StrEnum):
    """Subscription plan of one assistant ("employee")."""

    CHAT = "chat"
    VOICE_AND_CHAT = "voice_and_chat"
    PLUS = "plus"


class BillingPeriod(StrEnum):
    """How often a subscription is charged."""

    MONTHLY = "monthly"
    ANNUAL = "annual"


class SubscriptionStatus(StrEnum):
    """Subscription state driven by the payment provider."""

    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


class InvoiceStatus(StrEnum):
    """Invoice state."""

    ISSUED = "issued"
    PAID = "paid"
    FAILED = "failed"
    VOID = "void"


class UsageKind(StrEnum):
    """Metered usage unit, as in the concept's usage_events table."""

    VOICE_SECONDS = "voice_seconds"
    LLM_INPUT_TOKENS = "llm_input_tokens"
    LLM_OUTPUT_TOKENS = "llm_output_tokens"
    DIALOG = "dialog"
    WHATSAPP_REPLY = "whatsapp_reply"
    WHATSAPP_TEMPLATE = "whatsapp_template"
    TRANSFER_SECONDS = "transfer_seconds"
