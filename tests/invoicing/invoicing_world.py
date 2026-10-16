"""Settings and worlds of the invoicing tests: a VAT-registered seller."""

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.billing import BillingPeriod, SetupOption
from app.schemas.domain.billing_profiles import BillingProfileDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.billing_cabinet import StartTrialCommand, StartTrialRequest
from app.schemas.dto.payments import PaymentWebhookReceipt
from app.schemas.typings.invoicing.constrained_strings import (
    BillingAddressText,
    BillingLegalName,
    TaxpayerIdentificationNumber,
)
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.utilities.billing.invoicing_keys import derive_billing_profile_id
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.billing.billing_settings import (
    APP_BASE_URL,
    CABINET_ORIGIN,
    FLITT_MERCHANT_ID,
    FLITT_SECRET_KEY,
    GEORGIA,
    CountryPreset,
)
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.paid_world import PaidWorld

SELLER_TAX_ID: str = "405999999"


def seller_settings(is_vat_registered: bool) -> AppSettings:
    """The billing settings with a seller registered for VAT, or not."""

    return assemble_app_settings(
        {
            "APP_ENV": "test",
            "APP_BASE_URL": APP_BASE_URL,
            "CORS_ALLOWED_ORIGINS": CABINET_ORIGIN,
            "FLITT_MERCHANT_ID": FLITT_MERCHANT_ID,
            "FLITT_SECRET_KEY": FLITT_SECRET_KEY,
            "SELLER_LEGAL_NAME": "Assistant Workshop LLC",
            "SELLER_TAX_ID": SELLER_TAX_ID,
            "SELLER_ADDRESS": "1 Marjanishvili St\\n0102 Tbilisi",
            "SELLER_EMAIL": "Billing@Workshop.example",
            "PLATFORM_VAT_REGISTERED": "true" if is_vat_registered else "false",
        }
    )


def build_seller_trial(
    is_vat_registered: bool,
    country: CountryPreset = GEORGIA,
    setup_option: SetupOption = SetupOption.SELF_SERVE,
) -> PaidWorld:
    """A business in its monthly trial, billed by the given seller."""

    testbed = BillingTestbed(settings=seller_settings(is_vat_registered))
    owner = testbed.add_user(email="owner@example.com", locale="ka")
    business = testbed.add_business(owner, country, name="Mtsvane Ezo")
    testbed.start_trial.run(
        StartTrialCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartTrialRequest(billing_period=BillingPeriod.MONTHLY),
        )
    )
    subscription = testbed.subscription(business.id)
    subscription.setup_option = setup_option
    testbed.subscription_repo.save(subscription)
    return PaidWorld(testbed=testbed, owner=owner, business=business)


def save_billing_profile(
    world: PaidWorld,
    country: str,
    tax_id: str | None = None,
    billing_email: str | None = None,
) -> None:
    world.testbed.invoicing.billing_profile_repo.save(
        BillingProfileDocument(
            id=derive_billing_profile_id(world.business.id),
            business_id=world.business.id,
            legal_name=BillingLegalName("Mtsvane Ezo LLC"),
            tax_id=None if tax_id is None else TaxpayerIdentificationNumber(tax_id),
            address=BillingAddressText("12 Rustaveli Ave\n0108 Tbilisi"),
            billing_email=None
            if billing_email is None
            else EmailAddress(billing_email),
            country_code=CountryCode(country),
        )
    )


def renew(
    world: PaidWorld, order: PaymentOrderDocument, payment_id: int, **extra: object
) -> PaymentWebhookReceipt:
    """An automatic charge of the order's schedule, approved by Flitt."""

    return world.testbed.deliver_flitt_callback(
        {
            **world.testbed.callback_parameters(
                order,
                "approved",
                payment_id=payment_id,
                amount=int(order.recurring_amount_minor),
            ),
            "order_id": f"{order.id}_{payment_id}",
            "parent_order_id": str(order.id),
            **extra,
        }
    )
