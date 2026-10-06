"""
Owner-facing billing texts in English, Russian and Georgian.

Tax rule of the concept: invoices name a service ("call and message
handling service"), never a "license" or a "consultation". Placeholders in
braces are filled by the billing transformers.
"""

import re

from app.schemas.constants.billing import BillingNoticeKind, BillingPeriod
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import split_language_tag_text
from app.utilities.localization.owner_texts import owner_text

FALLBACK_LANGUAGE_TAG: LanguageTag = LanguageTag("en")
PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r"\{([a-z_]+)\}")

SERVICE_NAME: LocalizedText = owner_text("billing.texts.service_name")
SETUP_FEE_LINE: LocalizedText = owner_text("billing.texts.setup_fee_line")
USAGE_OVERAGE_LINE: LocalizedText = owner_text("billing.texts.usage_overage_line")
SERVICE_PERIOD_LINE: LocalizedText = owner_text("billing.texts.service_period_line")
# A month of a seasonal pause names this instead of its billing period.
PAUSE_PERIOD_NAME: LocalizedText = owner_text("billing.texts.pause_period_name")
BILLING_PERIOD_NAMES: dict[BillingPeriod, LocalizedText] = {
    BillingPeriod.MONTHLY: owner_text("billing.texts.billing_period_names.monthly"),
    BillingPeriod.ANNUAL: owner_text("billing.texts.billing_period_names.annual"),
}

NOTICE_TEXTS: dict[BillingNoticeKind, LocalizedText] = {
    BillingNoticeKind.PAYMENT_FAILED: owner_text(
        "billing.texts.notice_texts.payment_failed"
    ),
    BillingNoticeKind.TRIAL_ENDED_UNPAID: owner_text(
        "billing.texts.notice_texts.trial_ended_unpaid"
    ),
    BillingNoticeKind.RENEWAL_MISSED: owner_text(
        "billing.texts.notice_texts.renewal_missed"
    ),
    BillingNoticeKind.LEADS_ONLY_STARTED: owner_text(
        "billing.texts.notice_texts.leads_only_started"
    ),
    BillingNoticeKind.OVERAGE_INVOICED: owner_text(
        "billing.texts.notice_texts.overage_invoiced"
    ),
    BillingNoticeKind.SUBSCRIPTION_ENDED: owner_text(
        "billing.texts.notice_texts.subscription_ended"
    ),
    BillingNoticeKind.PAUSE_STARTED: owner_text(
        "billing.texts.notice_texts.pause_started"
    ),
    BillingNoticeKind.PAUSE_ENDED: owner_text("billing.texts.notice_texts.pause_ended"),
}
FULL_SERVICE_DEADLINE: LocalizedText = owner_text("billing.texts.full_service_deadline")
VOICE_MINUTES_WARNING: LocalizedText = owner_text("billing.texts.voice_minutes_warning")
DIALOGS_WARNING: LocalizedText = owner_text("billing.texts.dialogs_warning")


def select_text_language(
    text: LocalizedText,
    requested_language: LanguageTag,
) -> LanguageTag:
    """
    Language the text will actually be shown in: the requested one when the
    text has its base language, English otherwise. Numbers and dates are
    formatted in the same language, so a sentence never mixes conventions.
    """

    requested_base: str = split_language_tag_text(str(requested_language)).language
    for value_language in text.values:
        if split_language_tag_text(str(value_language)).language == requested_base:
            return requested_language

    return FALLBACK_LANGUAGE_TAG


def fill_placeholders(template: str, values: dict[str, str]) -> str:
    """Replace {name} placeholders in one pass (values are never re-read)."""

    return PLACEHOLDER_PATTERN.sub(
        lambda match: values.get(match.group(1), match.group(0)),
        template,
    )
