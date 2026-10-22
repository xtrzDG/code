"""
The parameters of Stripe's hosted pages: a Checkout Session in subscription
mode (the open bills charged now as a one-time line, the plan price as the
recurring line from the paid period's end) and the billing portal page
that replaces a saved card.
"""

from app.clients.stripe.stripe_protocol import FormValue
from app.schemas.constants.payments import PaymentOrderPurpose
from app.schemas.dto.payments import PaymentCheckoutRequest
from app.utilities.localization.language_tags import split_language_tag_text

MICROSECONDS_PER_SECOND: int = 1_000_000
MONTHS_IN_YEAR: int = 12
# Checkout accepts a trial end only this far ahead; nearer recurring starts
# anchor the billing cycle instead, without prorating the gap.
MIN_TRIAL_SECONDS: int = 48 * 60 * 60
# Checkout page languages (https://docs.stripe.com/api/checkout/sessions).
STRIPE_CHECKOUT_LANGUAGES: frozenset[str] = frozenset(
    {
        "bg", "cs", "da", "de", "el", "en", "es", "et", "fi", "fil", "fr",
        "hr", "hu", "id", "it", "ja", "ko", "lt", "lv", "ms", "mt", "nb",
        "nl", "pl", "pt", "ro", "ru", "sk", "sl", "sv", "th", "tr", "vi",
        "zh",
    }
)  # fmt: skip
AUTO_LANGUAGE: str = "auto"


def build_checkout_parameters(
    request: PaymentCheckoutRequest, return_url: str, now_unix_seconds: int
) -> dict[str, FormValue]:
    """A subscription-mode session; nothing is charged now for a card setup."""

    order_id: str = str(request.payment_order_id)
    currency: str = str(request.amount.currency_code).lower()
    line_items: list[FormValue] = [
        {
            "price_data": {
                "currency": currency,
                "unit_amount": int(request.recurring_charge.amount.amount_minor),
                "product_data": {"name": str(request.description)},
                "recurring": recurring_interval(
                    int(request.recurring_charge.interval_months)
                ),
            },
            "quantity": 1,
        }
    ]
    if request.purpose is PaymentOrderPurpose.CHECKOUT and (
        int(request.amount.amount_minor) > 0
    ):
        line_items.append(
            {
                "price_data": {
                    "currency": currency,
                    "unit_amount": int(request.amount.amount_minor),
                    "product_data": {"name": str(request.description)},
                },
                "quantity": 1,
            }
        )

    return {
        "mode": "subscription",
        "client_reference_id": order_id,
        "success_url": return_url,
        "cancel_url": return_url,
        "locale": select_checkout_language(str(request.language)),
        "payment_method_collection": "always",
        "metadata": {"payment_order_id": order_id},
        "line_items": line_items,
        "subscription_data": {
            "metadata": {"payment_order_id": order_id},
            **schedule_start(
                int(request.recurring_charge.starts_at) // MICROSECONDS_PER_SECOND,
                now_unix_seconds,
            ),
        },
    }


def build_portal_parameters(customer: str, return_url: str) -> dict[str, FormValue]:
    """The billing portal page that replaces the card of the subscription."""

    return {
        "customer": customer,
        "return_url": return_url,
        "flow_data": {"type": "payment_method_update"},
    }


def recurring_interval(interval_months: int) -> dict[str, FormValue]:
    """Monthly as month x1, annual as year x1."""

    if interval_months % MONTHS_IN_YEAR == 0:
        return {"interval": "year", "interval_count": interval_months // 12}

    return {"interval": "month", "interval_count": interval_months}


def schedule_start(
    starts_at_seconds: int, now_unix_seconds: int
) -> dict[str, FormValue]:
    """
    The first automatic charge at the paid period's end: a free trial up
    to then (any length Checkout allows), or, when it is less than two
    days away, the billing cycle anchored there with no proration.
    """

    if starts_at_seconds - now_unix_seconds >= MIN_TRIAL_SECONDS:
        return {"trial_end": starts_at_seconds}

    return {
        "billing_cycle_anchor": max(starts_at_seconds, now_unix_seconds + 60),
        "proration_behavior": "none",
    }


def select_checkout_language(language_tag: str) -> str:
    """Checkout's language for a tag ("ru-GE" -> "ru"), else Stripe's guess."""

    language: str = split_language_tag_text(language_tag).language
    return language if language in STRIPE_CHECKOUT_LANGUAGES else AUTO_LANGUAGE
