"""
The seller and the buyer as an invoice names them, and the buyer as VAT
sees it: the business's billing details when the owner saved some,
otherwise the business's name and country.
"""

import re

from app.schemas.configurations.seller_settings import SellerSettings
from app.schemas.domain.billing_profiles import BillingProfileDocument, InvoiceParty
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.invoicing import TaxBuyer
from app.schemas.typings.invoicing.constrained_strings import BillingLegalName

MAX_LEGAL_NAME_LENGTH: int = 200
CONTROL_CHARACTERS: re.Pattern[str] = re.compile(r"[\x00-\x1f\x7f]+")
UNNAMED: str = "—"


def build_seller_party(seller: SellerSettings) -> InvoiceParty:
    return InvoiceParty(
        legal_name=seller.legal_name,
        tax_id=seller.tax_id,
        address=seller.address,
        email=seller.email,
        country_code=seller.country_code,
    )


def build_buyer_party(
    business: BusinessDocument,
    profile: BillingProfileDocument | None,
) -> InvoiceParty:
    if profile is None:
        return InvoiceParty(
            legal_name=legal_name_of_business(business),
            country_code=business.country_code,
        )

    return InvoiceParty(
        legal_name=profile.legal_name,
        tax_id=profile.tax_id,
        address=profile.address,
        email=profile.billing_email,
        country_code=profile.country_code,
    )


def build_tax_buyer(buyer: InvoiceParty) -> TaxBuyer:
    return TaxBuyer(
        country_code=buyer.country_code, has_tax_id=buyer.tax_id is not None
    )


def legal_name_of_business(business: BusinessDocument) -> BillingLegalName:
    """The business name on one line, cut to the length of a legal name."""

    one_line: str = " ".join(CONTROL_CHARACTERS.sub(" ", str(business.name)).split())
    return BillingLegalName(one_line[:MAX_LEGAL_NAME_LENGTH].strip() or UNNAMED)
