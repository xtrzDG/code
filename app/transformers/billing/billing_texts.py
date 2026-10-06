"""
Owner-facing billing notices in every cabinet language (the owner text
catalog), and how a billing text picks its language and fills its
placeholders. The wording of invoice lines is in invoice_wording_texts.
"""

import re

from app.schemas.constants.billing import BillingNoticeKind
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import split_language_tag_text
from app.utilities.localization.owner_texts import owner_text

FALLBACK_LANGUAGE_TAG: LanguageTag = LanguageTag("en")
PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r"\{([a-z_]+)\}")

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
