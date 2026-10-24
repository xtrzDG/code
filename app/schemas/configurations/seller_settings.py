from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.invoicing.booleans import IsPlatformVatRegistered
from app.schemas.typings.invoicing.constrained_strings import (
    BillingAddressText,
    BillingLegalName,
    InvoiceSeries,
    TaxpayerIdentificationNumber,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    TimezoneName,
)
from app.schemas.typings.users.constrained_strings import EmailAddress

DEFAULT_SELLER_LEGAL_NAME: str = "Assistant Workshop"
DEFAULT_SELLER_COUNTRY_CODE: str = "GE"
DEFAULT_SELLER_TIME_ZONE: str = "Asia/Tbilisi"
DEFAULT_INVOICE_SERIES: str = "AW"


class SellerSettings(ImmutableDTO):
    """
    The platform as the seller on every invoice (SELLER_*): its registered
    name, tax number, address and e-mail, the country whose VAT rules
    apply, the time zone its invoice years and dates follow, the prefix of
    its invoice numbers, and whether it is registered for VAT
    (PLATFORM_VAT_REGISTERED; Georgia then adds 18 % for Georgian buyers).
    """

    legal_name: BillingLegalName = BillingLegalName(DEFAULT_SELLER_LEGAL_NAME)
    tax_id: TaxpayerIdentificationNumber | None = None
    address: BillingAddressText | None = None
    email: EmailAddress | None = None
    country_code: CountryCode = CountryCode(DEFAULT_SELLER_COUNTRY_CODE)
    time_zone: TimezoneName = TimezoneName(DEFAULT_SELLER_TIME_ZONE)
    invoice_series: InvoiceSeries = InvoiceSeries(DEFAULT_INVOICE_SERIES)
    is_vat_registered: IsPlatformVatRegistered = False
