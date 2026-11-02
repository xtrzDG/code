"""
An Italian seller registered for VAT (Italy is the first market): Italian
buyers pay the ordinary rate of 22 % on top, businesses elsewhere in the EU
account for it themselves (reverse charge), anyone else pays none; the
invoice names the rate in the reader's language ("VAT 22%", "IVA 22%").
"""

from decimal import ROUND_HALF_UP, Decimal

import pytest

from app.registries.billing.tax_policy_catalog import STANDARD_VAT_RATES
from app.registries.billing.tax_policy_registry import TaxPolicyRegistry
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.billing import BillingPeriod, InvoiceKind
from app.schemas.constants.invoicing import TaxTreatment
from app.schemas.dto.billing_cabinet import StartTrialCommand, StartTrialRequest
from app.schemas.dto.invoicing import TaxBuyer
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.transformers.invoicing import billing_document_texts as texts
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.localization.owner_texts import owner_text
from tests.billing.billing_settings import (
    APP_BASE_URL,
    CABINET_ORIGIN,
    FLITT_MERCHANT_ID,
    FLITT_SECRET_KEY,
    ITALY,
)
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.paid_world import PaidWorld, checkout
from tests.invoicing.document_world import HtmlEchoRenderer, build_document_world
from tests.invoicing.invoicing_world import save_billing_profile
from tests.invoicing.test_billing_documents import download

ITALIAN_VAT_NUMBER: str = "IT12345678901"


def italian_seller() -> AppSettings:
    return assemble_app_settings(
        {
            "APP_ENV": "test",
            "APP_BASE_URL": APP_BASE_URL,
            "CORS_ALLOWED_ORIGINS": CABINET_ORIGIN,
            "FLITT_MERCHANT_ID": FLITT_MERCHANT_ID,
            "FLITT_SECRET_KEY": FLITT_SECRET_KEY,
            "SELLER_LEGAL_NAME": "Workshop Italia S.r.l.",
            "SELLER_TAX_ID": ITALIAN_VAT_NUMBER,
            "SELLER_ADDRESS": "Via Roma 1\\n00184 Roma",
            "SELLER_COUNTRY_CODE": "IT",
            "SELLER_TIME_ZONE": "Europe/Rome",
            "PLATFORM_VAT_REGISTERED": "true",
        }
    )


def italian_trial() -> PaidWorld:
    testbed = BillingTestbed(settings=italian_seller())
    owner = testbed.add_user(email="titolare@example.it", locale="it")
    business = testbed.add_business(owner, ITALY, name="Trattoria da Luca")
    testbed.start_trial.run(
        StartTrialCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartTrialRequest(billing_period=BillingPeriod.MONTHLY),
        )
    )
    return PaidWorld(testbed=testbed, owner=owner, business=business)


def test_italy_has_its_ordinary_rate() -> None:
    assert int(STANDARD_VAT_RATES[CountryCode("IT")]) == 2200


@pytest.mark.parametrize(
    ("country", "has_tax_id", "treatment", "rate"),
    [
        ("IT", True, TaxTreatment.STANDARD, 2200),
        ("IT", False, TaxTreatment.STANDARD, 2200),
        ("DE", True, TaxTreatment.REVERSE_CHARGE, 0),
        ("GE", False, TaxTreatment.OUTSIDE_SCOPE, 0),
    ],
)
def test_a_registered_italian_seller_charges_vat_in_italy_only(
    country: str, has_tax_id: bool, treatment: TaxTreatment, rate: int
) -> None:
    decision = TaxPolicyRegistry(italian_seller().seller).decide(
        TaxBuyer(country_code=CountryCode(country), has_tax_id=has_tax_id)
    )

    assert (decision.treatment, int(decision.rate_basis_points)) == (treatment, rate)


def test_an_italian_buyer_pays_22_percent_on_top_and_reads_it() -> None:
    world = italian_trial()
    save_billing_profile(world, "IT", tax_id="IT98765432109")

    checkout(world)

    [invoice] = [
        invoice
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
    ]
    subtotal: int = int(invoice.subtotal_minor or 0)
    expected_tax: int = int(
        (Decimal(subtotal) * 22 / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    )
    assert invoice.tax_treatment is TaxTreatment.STANDARD
    assert int(invoice.tax_rate_basis_points or 0) == 2200
    assert subtotal > 0
    assert int(invoice.tax_minor or 0) == expected_tax
    assert int(invoice.amount_minor) == subtotal + expected_tax
    assert str(invoice.currency_code) == "EUR"
    assert invoice.seller is not None
    assert str(invoice.seller.country_code) == "IT"

    _, page = download(
        build_document_world(world, HtmlEchoRenderer()), invoice, language="en"
    )
    for text in ("Workshop Italia S.r.l.", "VAT 22%", "VAT is charged at 22%."):
        assert text in page, text


def test_the_vat_line_reads_iva_22_in_italian() -> None:
    italian: LanguageTag = LanguageTag("it")

    vat_line: str = str(owner_text("billing.document.vat").values[italian])
    note: str = str(owner_text("billing.document.tax_notes.standard").values[italian])

    assert vat_line.format(rate="22%") == "IVA 22%"
    assert note.format(rate="22%") == "IVA applicata con aliquota 22%."
    # Kept invoices print only reviewed wording: the same keys.
    assert texts.VAT.values[LanguageTag("en")] == "VAT {rate}"
