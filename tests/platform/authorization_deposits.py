"""
Deposits in the authorization matrix: the bodies of the settings changes,
the operations only owners may call, and business B's payment page and a
deposit waiting for it (the demo asks none).
"""

from typing import Any

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deposits import (
    DepositSubject,
    PaymentLinkKind,
)
from app.schemas.domain.deposits import (
    DepositRequestDocument,
    DepositSettingsDocument,
    PaymentLink,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.deposits.constrained_integers import DepositDueMinor
from app.schemas.typings.deposits.constrained_strings import (
    DepositReference,
    PaymentLinkAddress,
    PaymentLinkLabel,
)
from app.schemas.typings.deposits.strings import PaymentLinkHost, PaymentLinkPreview
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.deposits.deposit_keys import deposit_settings_id_of
from tests.e2e.harness import Workshop

type JsonObject = dict[str, Any]

B: str = "/v1/businesses/{business_id}"
PAGE_ADDRESS: str = "https://pay.example.com/deposit?sum={amount}&ref={reference}"
DEPOSIT_BODIES: dict[str, JsonObject] = {
    f"PUT {B}/deposit-settings": {
        "is_enabled": False,
        "hold_minutes": 60,
        "refund_cutoff_hours": 24,
    },
    f"POST {B}/deposit-settings/payment-links": {
        "label": "Card",
        "kind": "template",
        "address": PAGE_ADDRESS,
    },
    f"PUT {B}/deposit-settings/policies": {"target": "banquet", "policy": None},
}
OWNER_ONLY_DEPOSIT_OPERATIONS: frozenset[str] = frozenset(
    {
        f"PUT {B}/deposit-settings",
        f"POST {B}/deposit-settings/payment-links",
        f"DELETE {B}/deposit-settings/payment-links/{{link_id}}",
        f"PUT {B}/deposit-settings/policies",
        f"GET {B}/deposit-report",
    }
)


def deposit_path_values(
    workshop: Workshop,
    storage_scope: Any,
    business_id: str,
) -> dict[str, str]:
    """link_id and deposit_id: business B's payment page and a deposit on it."""

    container = workshop.container
    business_key = BusinessId(business_id)
    link = PaymentLink(
        label=PaymentLinkLabel("Card"),
        kind=PaymentLinkKind.TEMPLATE,
        address=PaymentLinkAddress(PAGE_ADDRESS),
        host=PaymentLinkHost("pay.example.com"),
        preview=PaymentLinkPreview(PAGE_ADDRESS),
        added_at=Microseconds(0),
    )
    request = DepositRequestDocument(
        business_id=business_key,
        subject=DepositSubject.BOOKING,
        contact_id=ContactId(),
        source_channel=ChannelKind.WEB_CHAT,
        language=LanguageTag("en"),
        amount_minor=DepositDueMinor(5000),
        currency_code=CurrencyCode("GEL"),
        reference=DepositReference("DK7Q3M9X"),
        payment_link_id=link.id,
        requested_at=Microseconds(0),
        hold_expires_at=Microseconds(2**62),
    )
    with storage_scope.scoped_to_business(business_key):
        container.repositories.deposit_settings_repo().save(
            DepositSettingsDocument(
                id=deposit_settings_id_of(business_key),
                business_id=business_key,
                payment_links=[link],
                default_payment_link_id=link.id,
            )
        )
        container.repositories.deposit_request_repo().save(request)

    return {"link_id": str(link.id), "deposit_id": str(request.id)}
