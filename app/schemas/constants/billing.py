from enum import StrEnum


class PlanKey(StrEnum):
    """Subscription plan of one assistant ("employee")."""

    CHAT = "chat"
    VOICE_AND_CHAT = "voice_and_chat"
    PLUS = "plus"


class SetupOption(StrEnum):
    """
    How a business gets set up: SELF_SERVE, the owner in the cabinet's
    guided setup (free), or DONE_FOR_YOU, the platform team sets it up for
    the plan's setup fee (an onboarding request reaches the team).
    """

    SELF_SERVE = "self_serve"
    DONE_FOR_YOU = "done_for_you"


class OnboardingRequestStatus(StrEnum):
    """A done-for-you setup the owner asked for: OPEN until the team is done."""

    OPEN = "open"
    DONE = "done"


class BillingPeriod(StrEnum):
    """How often a subscription is charged."""

    MONTHLY = "monthly"
    ANNUAL = "annual"


class SubscriptionStatus(StrEnum):
    """
    Subscription state driven by the payment provider.

    INCOMPLETE: chosen without a trial and waiting for its first payment;
    the business has no service from it until that payment arrives.
    """

    INCOMPLETE = "incomplete"
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
    TRANSCRIPTION_SECONDS = "transcription_seconds"


class InvoiceKind(StrEnum):
    """What an invoice charges for."""

    SERVICE_PERIOD = "service_period"
    SETUP_FEE = "setup_fee"
    USAGE_OVERAGE = "usage_overage"


class PackageMetric(StrEnum):
    """Included package quantity of a plan that is metered per period."""

    VOICE_MINUTES = "voice_minutes"
    DIALOGS = "dialogs"


class BillingNoticeKind(StrEnum):
    """Billing message sent to the owners of a business."""

    PAYMENT_FAILED = "payment_failed"
    TRIAL_ENDED_UNPAID = "trial_ended_unpaid"
    RENEWAL_MISSED = "renewal_missed"
    LEADS_ONLY_STARTED = "leads_only_started"
    SUBSCRIPTION_ENDED = "subscription_ended"
    PACKAGE_USAGE_WARNING = "package_usage_warning"
    OVERAGE_INVOICED = "overage_invoiced"


class ExchangeRateSource(StrEnum):
    """
    Who set an exchange rate. NBG: the National Bank of Georgia's official
    rates against the lari (about 40 currencies, daily). ECB: the European
    Central Bank's euro reference rates (about 30 currencies, each TARGET
    day). PLANNING: the rate of the platform's own cost model, the last
    fallback when no published rate is stored yet.
    """

    NBG = "nbg"
    ECB = "ecb"
    PLANNING = "planning"


class ManualPaymentMethod(StrEnum):
    """
    How money a platform admin recorded by hand arrived, outside the
    payment provider: a BANK_TRANSFER to the platform's account, or CASH.
    """

    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"


class BillingCreditKind(StrEnum):
    """
    One line of a business's credit ledger: credit a platform admin
    GRANTED (with the reason), or credit an invoice USED when it was
    issued (given back by voiding that invoice).
    """

    GRANTED = "granted"
    USED = "used"
