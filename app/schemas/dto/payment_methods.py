"""The card on file of a business as the billing page shows and changes it."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.payments import PaymentProvider, PaymentRetryOutcome
from app.schemas.typings.billing.booleans import (
    IsAutoDebitActive,
    IsCardSetupAvailable,
    IsTrialCardPromptDue,
)
from app.schemas.typings.billing.constrained_integers import (
    PaymentCardExpiryMonth,
    PaymentCardExpiryYear,
    PaymentRetryAttempt,
)
from app.schemas.typings.billing.constrained_strings import (
    PaymentCheckoutUrl,
    PaymentReturnUrl,
)
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.invoicing.constrained_strings import PaymentCardLastDigits
from app.schemas.typings.invoicing.strings import PaymentCardBrand
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


class PaymentCardView(ImmutableDTO):
    """The saved card: payment system, last four digits and expiry."""

    brand: PaymentCardBrand | None = None
    last_digits: PaymentCardLastDigits | None = None
    expiry_month: PaymentCardExpiryMonth | None = None
    expiry_year: PaymentCardExpiryYear | None = None
    saved_at: Microseconds


class PaymentRetryView(ImmutableDTO):
    """
    Where the retries of a declined automatic charge stand: the last one
    made and how it went, the next one due, and the end of the grace
    period after which the assistant only takes requests.
    """

    last_attempt: PaymentRetryAttempt | None = None
    last_outcome: PaymentRetryOutcome | None = None
    next_retry_at: Microseconds | None = None
    grace_until: Microseconds | None = None


class PaymentMethodView(ImmutableDTO):
    """
    The card on file of a business. `provider` charges it (the one its
    country is served by when no card is saved yet); `can_save_card` is
    True when a card can be saved or replaced now (a trial or a paid
    subscription without an unpaid bill: an unpaid bill is paid instead,
    which saves the card too); `is_trial_card_prompt_due` asks for a card
    from day 10 of a trial that has none.
    """

    provider: PaymentProvider
    card: PaymentCardView | None = None
    has_auto_debit: IsAutoDebitActive
    can_save_card: IsCardSetupAvailable
    trial_ends_at: Microseconds | None = None
    is_trial_card_prompt_due: IsTrialCardPromptDue = False
    retry: PaymentRetryView | None = None


class PaymentMethodQuery(ImmutableDTO):
    """An owner asks for the card on file of a business."""

    user_id: UserId
    business_id: BusinessId


class StartCardSetupRequest(ImmutableDTO):
    """HTTP body of "Save card" / "Update card": the page to come back to."""

    return_url: PaymentReturnUrl | None = None


class StartCardSetupCommand(ImmutableDTO):
    """An owner saves or replaces the card of the automatic charges."""

    user_id: UserId
    business_id: BusinessId
    request: StartCardSetupRequest
    display_language: LanguageTag | None = None


class CardSetupSessionView(ImmutableDTO):
    """
    The provider's page that saves the card: Flitt's verification page or
    Stripe's checkout (a first card) or billing portal (a new one).
    `payment_order_id` names the order a saved card reports back to.
    """

    provider: PaymentProvider
    url: PaymentCheckoutUrl
    payment_order_id: PaymentOrderId | None = None
