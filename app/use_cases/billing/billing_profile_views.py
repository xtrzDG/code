"""The billing details as the cabinet shows them, with the VAT they lead to."""

from app.contracts.invoicing import TaxPolicyRegistryContract
from app.schemas.domain.billing_profiles import BillingProfileDocument, InvoiceParty
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing_profiles import BillingProfileView
from app.schemas.dto.invoicing import TaxDecision
from app.utilities.billing.invoice_parties import build_buyer_party, build_tax_buyer


def view_billing_profile(
    business: BusinessDocument,
    profile: BillingProfileDocument | None,
    tax_policy_registry: TaxPolicyRegistryContract,
) -> BillingProfileView:
    buyer: InvoiceParty = build_buyer_party(business, profile)
    decision: TaxDecision = tax_policy_registry.decide(build_tax_buyer(buyer))
    return BillingProfileView(
        business_id=business.id,
        is_saved=profile is not None,
        legal_name=buyer.legal_name,
        tax_id=buyer.tax_id,
        address=buyer.address,
        billing_email=buyer.email,
        country_code=buyer.country_code,
        tax_treatment=decision.treatment,
        tax_rate_basis_points=decision.rate_basis_points,
    )
