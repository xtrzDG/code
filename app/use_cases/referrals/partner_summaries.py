"""What the portal and the admin's list say about a partner."""

from dataclasses import dataclass

from app.contracts.repositories.referral_repositories import (
    CommissionEntryRepoContract,
    PartnerRepoContract,
    ReferralCodeRepoContract,
    ReferralRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.constants.referrals import PARTNER_SOURCE_TAG
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.referrals.partner_portal import (
    CommissionTotalView,
    PartnerCodeView,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.referrals.constrained_integers import ReferredBusinessCount
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.referrals.partner_identity import find_partner_of
from app.utilities.referrals.referral_links import build_referral_link


@dataclass(frozen=True)
class PartnerSummary:
    """A partner's codes with links, businesses brought and paid, and totals."""

    codes: list[PartnerCodeView]
    referred_businesses: ReferredBusinessCount
    paid_businesses: ReferredBusinessCount
    totals: list[CommissionTotalView]


@dataclass(frozen=True)
class PartnerReaders:
    """The repositories a partner summary reads, and the site's address."""

    referral_code_repo: ReferralCodeRepoContract
    referral_repo: ReferralRepoContract
    commission_entry_repo: CommissionEntryRepoContract
    cabinet_base_url: CabinetBaseUrl | None

    def summarize(self, partner: PartnerDocument) -> PartnerSummary:
        return PartnerSummary(
            codes=[
                PartnerCodeView(
                    code=code.code,
                    link=(
                        None
                        if self.cabinet_base_url is None
                        else build_referral_link(
                            str(self.cabinet_base_url), code.code, PARTNER_SOURCE_TAG
                        )
                    ),
                )
                for code in sorted(
                    self.referral_code_repo.list_by_partner(partner.id),
                    key=lambda code: int(code.created_at),
                )
            ],
            referred_businesses=self.referral_repo.count_by_partner(partner.id),
            paid_businesses=self.referral_repo.count_by_partner(
                partner.id, only_paid=True
            ),
            totals=[
                CommissionTotalView(
                    currency_code=total.currency_code,
                    status=total.status,
                    invoice_count=total.invoice_count,
                    amount_minor=total.amount_minor,
                )
                for total in sorted(
                    self.commission_entry_repo.totals_by_partner(partner.id),
                    key=lambda total: (str(total.currency_code), total.status.value),
                )
            ],
        )


def require_partner(
    user_repo: UserRepoContract, partner_repo: PartnerRepoContract, user_id: UserId
) -> PartnerDocument:
    """
    The partner the signed-in person is.

    Raises:
        NotFoundError: no partner signs in with their phone number or e-mail.
    """

    user: UserDocument | None = user_repo.get(user_id)
    partner: PartnerDocument | None = (
        None if user is None else find_partner_of(partner_repo, user)
    )
    if partner is None:
        raise NotFoundError("No partner account signs in with this phone or e-mail.")

    return partner
