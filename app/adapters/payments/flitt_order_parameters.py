"""
The orders the platform sends Flitt (protocol 2.0): a hosted page that pays
the open invoices and subscribes the card to automatic charges, a card
setup page that verifies the card for nothing and only subscribes it, and
a charge of a saved card's token (a retry of a declined automatic charge).
Every order asks for the card's token (`required_rectoken`), which the
retries charge.
"""

from app.schemas.constants.payments import PaymentOrderPurpose
from app.schemas.dto.payment_retries import PaymentRetryRequest
from app.schemas.dto.payments import PaymentCheckoutRequest
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import split_language_tag_text

# Payment page languages listed for the Flitt `lang` parameter.
FLITT_PAGE_LANGUAGES: frozenset[str] = frozenset(
    {
        "az", "cs", "da", "de", "en", "es", "fi", "fr", "hu", "it", "ka",
        "ko", "lv", "nl", "pl", "ro", "ru", "sk", "uk", "zh",
    }
)  # fmt: skip
RECURRING_PERIOD_UNIT: str = "month"
FLAG_YES: str = "y"
UPPER_FLAG_YES: str = "Y"
MAX_ORDER_DESCRIPTION_LENGTH: int = 1024
# A card setup verifies the card without charging it (zero-amount
# verification); the automatic charges then start on their date.
CARD_VERIFICATION_AMOUNT_MINOR: int = 0
CARD_VERIFICATION_TYPE: str = "amount"


def build_checkout_order(
    request: PaymentCheckoutRequest, callback_url: str
) -> dict[str, object]:
    order: dict[str, object] = {
        "order_id": str(request.payment_order_id),
        "order_desc": str(request.description)[:MAX_ORDER_DESCRIPTION_LENGTH],
        "amount": int(request.amount.amount_minor),
        "currency": str(request.amount.currency_code),
        "server_callback_url": callback_url,
        "merchant_data": str(request.payment_order_id),
        "required_rectoken": UPPER_FLAG_YES,
        "subscription": UPPER_FLAG_YES,
        "subscription_callback_url": callback_url,
        "recurring_data": {
            "every": int(request.recurring_charge.interval_months),
            "period": RECURRING_PERIOD_UNIT,
            "amount": int(request.recurring_charge.amount.amount_minor),
            "start_time": str(request.recurring_charge.start_date),
            "state": FLAG_YES,
            "readonly": FLAG_YES,
        },
    }
    if request.purpose is PaymentOrderPurpose.CARD_SETUP:
        order["amount"] = CARD_VERIFICATION_AMOUNT_MINOR
        order["verification"] = UPPER_FLAG_YES
        order["verification_type"] = CARD_VERIFICATION_TYPE

    page_language: str | None = select_page_language(request.language)
    if page_language is not None:
        order["lang"] = page_language

    if request.return_url is not None:
        order["response_url"] = str(request.return_url)

    return order


def build_retry_order(
    request: PaymentRetryRequest, card_token: str, callback_url: str
) -> dict[str, object]:
    """
    A charge of the saved card under the retry's own order id; its
    notification names the payment order through the merchant data.
    """

    return {
        "order_id": str(request.retry_id),
        "order_desc": str(request.description)[:MAX_ORDER_DESCRIPTION_LENGTH],
        "amount": int(request.amount.amount_minor),
        "currency": str(request.amount.currency_code),
        "rectoken": card_token,
        "server_callback_url": callback_url,
        "merchant_data": str(request.payment_order_id),
    }


def select_page_language(language_tag: LanguageTag) -> str | None:
    """Flitt page language for a tag ("ka-GE" -> "ka"), if Flitt has it."""

    language: str = split_language_tag_text(str(language_tag)).language
    return language if language in FLITT_PAGE_LANGUAGES else None
