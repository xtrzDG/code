"""
The wording of invoice lines (the cabinet's invoice list, the invoice and
receipt PDFs) in every language whose texts are reviewed: English, Russian
and Georgian; other languages, Hebrew and German drafts among them, read
English. An issued invoice keeps its wording, so a draft never reaches one.

Tax rule of the concept: invoices name a service ("call and message
handling service"), never a "license" or a "consultation". Placeholders in
braces are filled by the invoice transformers.
"""

from app.schemas.constants.billing import BillingPeriod
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.owner_texts import reviewed_owner_text

SERVICE_NAME: LocalizedText = reviewed_owner_text("billing.texts.service_name")
SETUP_FEE_LINE: LocalizedText = reviewed_owner_text("billing.texts.setup_fee_line")
USAGE_OVERAGE_LINE: LocalizedText = reviewed_owner_text(
    "billing.texts.usage_overage_line"
)
SERVICE_PERIOD_LINE: LocalizedText = reviewed_owner_text(
    "billing.texts.service_period_line"
)
# A month of a seasonal pause names this instead of its billing period.
PAUSE_PERIOD_NAME: LocalizedText = reviewed_owner_text(
    "billing.texts.pause_period_name"
)
BILLING_PERIOD_NAMES: dict[BillingPeriod, LocalizedText] = {
    BillingPeriod.MONTHLY: reviewed_owner_text(
        "billing.texts.billing_period_names.monthly"
    ),
    BillingPeriod.ANNUAL: reviewed_owner_text(
        "billing.texts.billing_period_names.annual"
    ),
}
