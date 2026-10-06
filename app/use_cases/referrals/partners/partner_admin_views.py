"""A partner as the platform team's list shows them."""

from app.schemas.domain.partners import PartnerDocument
from app.schemas.dto.referrals.partner_admin import PartnerAdminView
from app.use_cases.referrals.partner_summaries import PartnerReaders, PartnerSummary


def build_partner_admin_view(
    partner: PartnerDocument, readers: PartnerReaders
) -> PartnerAdminView:
    summary: PartnerSummary = readers.summarize(partner)
    return PartnerAdminView(
        partner_id=partner.id,
        name=partner.name,
        login_method=partner.login_method,
        phone_number=partner.phone_number,
        email=partner.email,
        commission_rate_basis_points=partner.commission_rate_basis_points,
        status=partner.status,
        codes=summary.codes,
        referred_businesses=summary.referred_businesses,
        paid_businesses=summary.paid_businesses,
        totals=summary.totals,
        created_at=partner.created_at,
    )
