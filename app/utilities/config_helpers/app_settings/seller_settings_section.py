"""
SELLER_LEGAL_NAME, SELLER_TAX_ID, SELLER_ADDRESS, SELLER_EMAIL,
SELLER_COUNTRY_CODE, SELLER_TIME_ZONE, SELLER_INVOICE_SERIES and
PLATFORM_VAT_REGISTERED: the seller on invoices and its VAT.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.seller_settings import (
    DEFAULT_INVOICE_SERIES,
    DEFAULT_SELLER_COUNTRY_CODE,
    DEFAULT_SELLER_LEGAL_NAME,
    DEFAULT_SELLER_TIME_ZONE,
    SellerSettings,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
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
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_setting,
    parse_setting,
    read_boolean,
    read_text,
)
from app.utilities.localization.timezones import is_known_timezone_name


class SellerSettingsSection(TypedDict):
    """The `AppSettings` field of the seller on invoices."""

    seller: SellerSettings


def read_seller_settings(
    environment_variables: Mapping[str, str],
) -> SellerSettingsSection:
    """
    Raises:
        ValidationFailedError: a value has the wrong form, the time zone is
            unknown, or VAT registration is on without the seller's tax number.
    """

    is_vat_registered: bool = read_boolean(
        environment_variables, "PLATFORM_VAT_REGISTERED", False
    )
    tax_id: TaxpayerIdentificationNumber | None = optional_setting(
        environment_variables, "SELLER_TAX_ID", TaxpayerIdentificationNumber
    )
    if is_vat_registered and tax_id is None:
        raise ValidationFailedError(
            "PLATFORM_VAT_REGISTERED needs SELLER_TAX_ID (the VAT number "
            "printed on every invoice)."
        )

    return SellerSettingsSection(
        seller=SellerSettings(
            legal_name=parse_setting(
                "SELLER_LEGAL_NAME",
                read_text(
                    environment_variables,
                    "SELLER_LEGAL_NAME",
                    DEFAULT_SELLER_LEGAL_NAME,
                ),
                BillingLegalName,
            ),
            tax_id=tax_id,
            address=optional_setting(
                environment_variables,
                "SELLER_ADDRESS",
                lambda raw: BillingAddressText(raw.replace("\\n", "\n")),
            ),
            email=optional_setting(
                environment_variables,
                "SELLER_EMAIL",
                lambda raw: EmailAddress(raw.lower()),
            ),
            country_code=parse_setting(
                "SELLER_COUNTRY_CODE",
                read_text(
                    environment_variables,
                    "SELLER_COUNTRY_CODE",
                    DEFAULT_SELLER_COUNTRY_CODE,
                ).upper(),
                CountryCode,
            ),
            time_zone=parse_setting(
                "SELLER_TIME_ZONE",
                read_text(
                    environment_variables,
                    "SELLER_TIME_ZONE",
                    DEFAULT_SELLER_TIME_ZONE,
                ),
                read_time_zone,
            ),
            invoice_series=parse_setting(
                "SELLER_INVOICE_SERIES",
                read_text(
                    environment_variables,
                    "SELLER_INVOICE_SERIES",
                    DEFAULT_INVOICE_SERIES,
                ).upper(),
                InvoiceSeries,
            ),
            is_vat_registered=is_vat_registered,
        )
    )


def read_time_zone(raw_value: str) -> TimezoneName:
    """An IANA time zone that exists; ValueError otherwise."""

    if not is_known_timezone_name(raw_value):
        raise ValueError("Unknown time zone.")

    return TimezoneName(raw_value)
