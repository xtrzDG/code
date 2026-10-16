"""
Who pays VAT on the platform's invoices: nobody while the seller is not
registered; a Georgian buyer 18 % on top once it is; buyers abroad none,
with the reverse-charge note for businesses with a tax number.
"""

import pytest

from app.registries.billing.tax_policy_registry import TaxPolicyRegistry
from app.schemas.configurations.seller_settings import SellerSettings
from app.schemas.constants.invoicing import TaxTreatment
from app.schemas.dto.invoicing import TaxBuyer, TaxDecision
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.invoicing.constrained_integers import TaxRateBasisPoints
from app.schemas.typings.invoicing.constrained_strings import (
    TaxpayerIdentificationNumber,
)
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.invoicing.invoicing_world import seller_settings

REGISTERED: SellerSettings = SellerSettings(
    tax_id=TaxpayerIdentificationNumber("405999999"), is_vat_registered=True
)


def decide(seller: SellerSettings, country: str, has_tax_id: bool) -> TaxDecision:
    return TaxPolicyRegistry(seller).decide(
        TaxBuyer(country_code=CountryCode(country), has_tax_id=has_tax_id)
    )


@pytest.mark.parametrize(
    ("country", "has_tax_id", "treatment", "rate"),
    [
        ("GE", True, TaxTreatment.STANDARD, 1800),
        ("GE", False, TaxTreatment.STANDARD, 1800),
        ("DE", True, TaxTreatment.REVERSE_CHARGE, 0),
        ("AM", False, TaxTreatment.OUTSIDE_SCOPE, 0),
        ("US", False, TaxTreatment.OUTSIDE_SCOPE, 0),
    ],
)
def test_a_registered_georgian_seller_charges_vat_at_home_only(
    country: str, has_tax_id: bool, treatment: TaxTreatment, rate: int
) -> None:
    decision = decide(REGISTERED, country, has_tax_id)

    assert decision == TaxDecision(
        treatment=treatment, rate_basis_points=TaxRateBasisPoints(rate)
    )


@pytest.mark.parametrize(("country", "has_tax_id"), [("GE", True), ("DE", True)])
def test_a_seller_not_registered_charges_no_vat_to_anyone(
    country: str, has_tax_id: bool
) -> None:
    decision = decide(SellerSettings(), country, has_tax_id)

    assert decision.treatment is TaxTreatment.NOT_REGISTERED
    assert int(decision.rate_basis_points) == 0


def test_registration_needs_a_country_whose_rate_is_known() -> None:
    seller = SellerSettings(
        country_code=CountryCode("FR"),
        tax_id=TaxpayerIdentificationNumber("FR12345678901"),
        is_vat_registered=True,
    )

    with pytest.raises(ValidationFailedError, match="SELLER_COUNTRY_CODE=FR"):
        TaxPolicyRegistry(seller)

    # Not registered, the country needs no rate.
    TaxPolicyRegistry(seller.model_copy(update={"is_vat_registered": False}))


def test_vat_registration_needs_the_sellers_tax_number() -> None:
    with pytest.raises(ValidationFailedError, match="SELLER_TAX_ID"):
        assemble_app_settings({"PLATFORM_VAT_REGISTERED": "true"})


def test_seller_settings_read_their_variables() -> None:
    seller = seller_settings(is_vat_registered=True).seller

    assert str(seller.legal_name) == "Assistant Workshop LLC"
    assert str(seller.address) == "1 Marjanishvili St\n0102 Tbilisi"
    assert str(seller.email) == "billing@workshop.example"
    assert (str(seller.country_code), str(seller.time_zone)) == ("GE", "Asia/Tbilisi")
    assert str(seller.invoice_series) == "AW"
    assert seller.is_vat_registered


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("SELLER_TIME_ZONE", "Mars/Olympus"),
        ("SELLER_INVOICE_SERIES", "A-W"),
        ("SELLER_COUNTRY_CODE", "Georgia"),
        ("SELLER_EMAIL", "not an address"),
        ("PLATFORM_VAT_REGISTERED", "maybe"),
    ],
)
def test_a_wrong_seller_value_stops_the_start(variable: str, value: str) -> None:
    with pytest.raises(ValidationFailedError, match=variable):
        assemble_app_settings({variable: value})
