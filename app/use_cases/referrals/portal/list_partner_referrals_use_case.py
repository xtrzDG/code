from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.referral_repositories import (
    PartnerRepoContract,
    ReferralRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.referrals import ReferralDocument
from app.schemas.dto.referrals.partner_portal import (
    PartnerPageQuery,
    PartnerReferralPage,
    PartnerReferralView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.referrals.partner_summaries import require_partner
from app.utilities.paging.keyset_paging import finish_page, read_slice


class ListPartnerReferralsUseCase(
    UseCaseContract[PartnerPageQuery, PartnerReferralPage]
):
    """
    GET /v1/partner/referrals?limit=&cursor=: the businesses that signed up
    by the partner's codes, the newest first, with their name, country,
    plan and state, the code and when they signed up and first paid. The
    partner sees nothing of the businesses' owners or customers.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        partner_repo: PartnerRepoContract,
        referral_repo: ReferralRepoContract,
        business_repo: BusinessRepoContract,
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._partner_repo: PartnerRepoContract = partner_repo
        self._referrals: ReferralRepoContract = referral_repo
        self._businesses: BusinessRepoContract = business_repo

    def run(self, input_data: PartnerPageQuery) -> PartnerReferralPage:
        partner: PartnerDocument = require_partner(
            self._user_repo, self._partner_repo, input_data.user_id
        )
        referrals, next_cursor = finish_page(
            self._referrals.page_by_partner(partner.id, read_slice(input_data.page)),
            input_data.page,
            sort_key=lambda referral: int(referral.referred_at),
            item_id=lambda referral: str(referral.id),
        )
        businesses: dict[BusinessId, BusinessDocument] = {
            business.id: business
            for business in self._businesses.get_many(
                [referral.referred_business_id for referral in referrals]
            )
        }
        return PartnerReferralPage(
            items=[
                referral_view(referral, businesses.get(referral.referred_business_id))
                for referral in referrals
            ],
            next_cursor=next_cursor,
        )


def referral_view(
    referral: ReferralDocument, business: BusinessDocument | None
) -> PartnerReferralView:
    return PartnerReferralView(
        business_id=referral.referred_business_id,
        business_name=None if business is None else business.name,
        country_code=None if business is None else business.country_code,
        plan_key=None if business is None else business.plan_key,
        business_status=None if business is None else business.status,
        code=referral.code,
        referred_at=referral.referred_at,
        first_paid_at=referral.first_paid_at,
    )
