from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.contracts.invoicing import InvoiceIssuingFacilitatorContract
from app.contracts.payment_methods import PaymentProviderRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.payments import PaymentOrderPurpose, PaymentProvider
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing import Money
from app.schemas.dto.payment_methods import (
    CardSetupSessionView,
    StartCardSetupCommand,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.billing.strings import (
    InvoiceDescription,
    PaymentProviderReference,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.billing.card_on_file.card_on_file_views import (
    can_save_card,
    select_card_provider,
)
from app.use_cases.billing.card_on_file.dunning_rules import find_schedule_order
from app.use_cases.billing.payment_order_opening import (
    PaymentOrderOpening,
    open_payment_order,
)
from app.use_cases.shared.billing_records import (
    list_subscription_invoices,
    require_current_subscription,
)
from app.use_cases.shared.subscription_pricing import subscription_price
from app.utilities.billing.return_urls import require_allowed_return_url
from app.utilities.localization.babel_locales import require_babel_locale

CARD_SETUP_DESCRIPTION: InvoiceDescription = InvoiceDescription(
    "Card for automatic payments"
)


class StartCardSetupUseCase(
    UseCaseContract[StartCardSetupCommand, CardSetupSessionView]
):
    """
    "Save card" (a trial) and "Update card" (a paid subscription), owners
    only: the provider's page that saves the card for the automatic charges
    without charging it now. Flitt verifies the card for nothing (a zero
    amount); Stripe opens Checkout in subscription mode for a first card
    and its billing portal to replace one. The charges start when the
    trial or the paid period ends, at the plan price with tax, and replace
    those of an earlier card once the provider confirms the new one.

    Raises:
        ConflictError: no card can be saved now (an unpaid bill is paid
            instead, which saves the card too; a paused or cancelled
            subscription has no charges to save it for).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        payment_order_repo: PaymentOrderRepoContract,
        payment_gateway: PaymentGatewayAdapterContract,
        payment_provider_registry: PaymentProviderRegistryContract,
        invoice_issuing: InvoiceIssuingFacilitatorContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._payment_order_repo: PaymentOrderRepoContract = payment_order_repo
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._payment_provider_registry: PaymentProviderRegistryContract = (
            payment_provider_registry
        )
        self._invoice_issuing: InvoiceIssuingFacilitatorContract = invoice_issuing
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: StartCardSetupCommand) -> CardSetupSessionView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        language: LanguageTag = input_data.display_language or business.owner_language
        require_babel_locale(language)
        require_allowed_return_url(input_data.request.return_url, self._app_settings)
        subscription: SubscriptionDocument = require_current_subscription(
            self._subscription_repo, business.id
        )
        if not can_save_card(
            subscription, list_subscription_invoices(self._invoice_repo, subscription)
        ):
            raise ConflictError("A card cannot be saved now.")

        provider: PaymentProvider = select_card_provider(
            self._payment_provider_registry, business, subscription
        )
        recurring: Money = self._invoice_issuing.price_with_tax(
            business, subscription_price(subscription)
        ).total
        now: Microseconds = self._wall_clock.now_unix()
        payment_order, session = open_payment_order(
            self._payment_gateway,
            self._payment_order_repo,
            business,
            subscription,
            PaymentOrderOpening(
                provider=provider,
                purpose=PaymentOrderPurpose.CARD_SETUP,
                invoice_ids=[],
                amount=Money(
                    amount_minor=MoneyAmountMinor(0),
                    currency_code=recurring.currency_code,
                ),
                recurring=recurring,
                charges_from=self._charges_from(subscription, now),
                description=CARD_SETUP_DESCRIPTION,
                language=language,
                return_url=input_data.request.return_url,
                customer_reference=self._stripe_customer(provider, subscription),
            ),
            now,
        )
        return CardSetupSessionView(
            provider=provider,
            url=session.checkout_url,
            payment_order_id=payment_order.id,
        )

    def _charges_from(
        self, subscription: SubscriptionDocument, now: Microseconds
    ) -> Microseconds:
        """The trial's end, or the end of the paid period (never the past)."""

        if (
            subscription.status is SubscriptionStatus.TRIALING
            and subscription.trial_ends_at is not None
        ):
            return max(subscription.trial_ends_at, now)

        return max(subscription.period_end, now)

    def _stripe_customer(
        self, provider: PaymentProvider, subscription: SubscriptionDocument
    ) -> PaymentProviderReference | None:
        """The Stripe customer of the running charges: its card is replaced."""

        if provider is not PaymentProvider.STRIPE:
            return None

        schedule_order: PaymentOrderDocument | None = find_schedule_order(
            self._payment_order_repo, subscription
        )
        return None if schedule_order is None else schedule_order.customer_reference
