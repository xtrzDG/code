from base_pydantic_schemas import PersistentDocument
from typed_time_provider import Microseconds

from app.schemas.constants.payments import PaymentProvider
from app.schemas.typings.billing.constrained_integers import (
    PaymentCardExpiryMonth,
    PaymentCardExpiryYear,
)
from app.schemas.typings.invoicing.constrained_strings import PaymentCardLastDigits
from app.schemas.typings.invoicing.strings import PaymentCardBrand


class PaymentMethodSummary(PersistentDocument):
    """
    The card the automatic charges of a subscription go to, as its payment
    provider reported it: the payment system, the last four digits and the
    expiry, never more of the card. `saved_at` is when the provider saved
    it (its event time), so an older event that arrives late never replaces
    a newer card.
    """

    provider: PaymentProvider
    brand: PaymentCardBrand | None = None
    last_digits: PaymentCardLastDigits | None = None
    expiry_month: PaymentCardExpiryMonth | None = None
    expiry_year: PaymentCardExpiryYear | None = None
    saved_at: Microseconds
