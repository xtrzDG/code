"""Cabinet billing details: what invoices say about the business."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.invoicing import TaxTreatment
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.invoicing.booleans import IsBillingProfileSaved
from app.schemas.typings.invoicing.constrained_integers import TaxRateBasisPoints
from app.schemas.typings.invoicing.constrained_strings import (
    BillingAddressText,
    BillingLegalName,
    TaxpayerIdentificationNumber,
)
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId


class BillingProfileRequest(ImmutableDTO):
    """
    Body of the billing details. The country decides the VAT; the e-mail
    receives every invoice and receipt.

    Example: {"legal_name": "Mtsvane Ezo LLC", "tax_id": "405123456",
    "address": "12 Rustaveli Ave, 0108 Tbilisi",
    "billing_email": "accounts@mtsvane-ezo.ge", "country_code": "GE"}.
    """

    legal_name: BillingLegalName
    tax_id: TaxpayerIdentificationNumber | None = None
    address: BillingAddressText | None = None
    billing_email: EmailAddress | None = None
    country_code: CountryCode


class BillingProfileQuery(ImmutableDTO):
    """An owner opens the billing details of a business."""

    user_id: UserId
    business_id: BusinessId


class SaveBillingProfileCommand(ImmutableDTO):
    """An owner saves the billing details (audited)."""

    user_id: UserId
    business_id: BusinessId
    request: BillingProfileRequest
    client_ip_address: ClientIpAddress | None = None


class BillingProfileView(ImmutableDTO):
    """
    The billing details as invoices will print them, and the VAT they
    lead to. Before the owner saves any (`is_saved` false) they are the
    business name and country.
    """

    business_id: BusinessId
    is_saved: IsBillingProfileSaved
    legal_name: BillingLegalName
    tax_id: TaxpayerIdentificationNumber | None = None
    address: BillingAddressText | None = None
    billing_email: EmailAddress | None = None
    country_code: CountryCode
    tax_treatment: TaxTreatment
    tax_rate_basis_points: TaxRateBasisPoints
