from base_pydantic_schemas import BaseDocument, SchemaVersion
from pydantic import Field

from app.schemas.constants.billing import BillingCreditKind
from app.schemas.typings.access.constrained_strings import AdminActionReason
from app.schemas.typings.billing.constrained_integers import BillingCreditAmountMinor
from app.schemas.typings.billing.prefixed_id import BillingCreditId, InvoiceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.users.prefixed_id import UserId


class BillingCreditDocument(BaseDocument):
    """
    One line of a business's credit ledger (`billing_credits`, migration
    1143): credit a platform admin GRANTED, with who and why, or credit an
    invoice USED when it was issued, which names that invoice (its id
    derives from the invoice, so an invoice uses credit once).

    Credit is money off the price before tax, in one currency: an invoice
    in another currency leaves it be. The balance of a currency is what was
    granted minus what invoices used, an invoice that was voided since
    giving its credit back, so nothing has to remember to return it.

    Version 2: `referral_of`, on credit the referral program GRANTED (no
    admin, no reason): the month a business earned when the business it
    invited paid its first invoice, or the month the invited business got
    for it. Its id derives from the referred business and the side, so it
    is granted once. None on every other line, so version 1 reads as is.
    """

    schema_version: SchemaVersion = SchemaVersion("2")
    id: BillingCreditId = Field(default_factory=BillingCreditId)
    business_id: BusinessId
    kind: BillingCreditKind
    amount_minor: BillingCreditAmountMinor
    currency_code: CurrencyCode
    invoice_id: InvoiceId | None = None
    granted_by: UserId | None = None
    reason: AdminActionReason | None = None
    referral_of: BusinessId | None = None
