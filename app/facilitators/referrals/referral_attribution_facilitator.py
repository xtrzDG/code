from typed_time_provider import Microseconds, WallClock

from app.contracts.referrals import ReferralAttributionFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.referral_repositories import (
    PartnerRepoContract,
    ReferralCodeRepoContract,
    ReferralRepoContract,
)
from app.schemas.constants.referrals import ReferralCodeOwnerKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.referrals import (
    BusinessReferral,
    ReferralCodeDocument,
    ReferralDocument,
)
from app.schemas.domain.users import UserDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.referrals.partner_identity import is_partner_person
from app.utilities.referrals.referral_identity import (
    referral_code_id,
    referral_id,
)

MICROSECONDS_IN_DAY: int = 86_400_000_000
# A code counts for the businesses an owner creates in the first 90 days
# after signing up by it (the cabinet's first-touch cookie lasts as long).
REFERRAL_WINDOW_DAYS: int = 90


class ReferralAttributionFacilitator(ReferralAttributionFacilitatorContract):
    """
    Who brought a new business, from the code its owner signed up by (the
    first-touch `aw_attr` cookie kept in `UserDocument.signup_attribution`):

    - a partner's code: the partner, whatever their state (a paused partner
      earns nothing until resumed), unless the owner is the partner;
    - a business's code: that business, unless the owner already works in
      it (an owner never invites themselves) or it is the new business.

    A code counts for the businesses created in the first 90 days after
    sign-up; an unknown code, or none, refers nobody.
    """

    def __init__(
        self,
        referral_code_repo: ReferralCodeRepoContract,
        referral_repo: ReferralRepoContract,
        partner_repo: PartnerRepoContract,
        business_repo: BusinessRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._codes: ReferralCodeRepoContract = referral_code_repo
        self._referrals: ReferralRepoContract = referral_repo
        self._partners: PartnerRepoContract = partner_repo
        self._businesses: BusinessRepoContract = business_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def referral_of(
        self, owner: UserDocument, business_id: BusinessId, now: Microseconds
    ) -> BusinessReferral | None:
        attribution = owner.signup_attribution
        if attribution is None or attribution.referral_code is None:
            return None

        window_end: int = int(owner.created_at) + (
            REFERRAL_WINDOW_DAYS * MICROSECONDS_IN_DAY
        )
        if int(now) > window_end:
            return None

        code: ReferralCodeDocument | None = self._codes.get(
            referral_code_id(attribution.referral_code)
        )
        if code is None:
            return None

        if code.owner_kind is ReferralCodeOwnerKind.PARTNER:
            return self._partner_referral(code, owner, now)

        return self._business_referral(code, owner, business_id, now)

    def record(self, business: BusinessDocument) -> None:
        referral: BusinessReferral | None = business.referred_by
        if referral is None:
            return

        now: Microseconds = self._wall_clock.now_unix()
        self._referrals.record(
            ReferralDocument(
                id=referral_id(business.id),
                business_id=referral.referring_business_id,
                referred_business_id=business.id,
                code=referral.code,
                owner_kind=referral.owner_kind,
                partner_id=referral.partner_id,
                referred_at=referral.referred_at,
                created_at=now,
                updated_at=now,
            )
        )

    def _partner_referral(
        self, code: ReferralCodeDocument, owner: UserDocument, now: Microseconds
    ) -> BusinessReferral | None:
        partner: PartnerDocument | None = (
            None if code.partner_id is None else self._partners.get(code.partner_id)
        )
        if partner is None or is_partner_person(partner, owner):
            return None

        return BusinessReferral(
            code=code.code,
            owner_kind=ReferralCodeOwnerKind.PARTNER,
            partner_id=partner.id,
            referred_at=now,
        )

    def _business_referral(
        self,
        code: ReferralCodeDocument,
        owner: UserDocument,
        business_id: BusinessId,
        now: Microseconds,
    ) -> BusinessReferral | None:
        if code.business_id is None or code.business_id == business_id:
            return None

        referring: BusinessDocument | None = self._businesses.get(code.business_id)
        if referring is None or any(
            member.user_id == owner.id for member in referring.members
        ):
            return None

        return BusinessReferral(
            code=code.code,
            owner_kind=ReferralCodeOwnerKind.BUSINESS,
            referring_business_id=referring.id,
            referred_at=now,
        )
