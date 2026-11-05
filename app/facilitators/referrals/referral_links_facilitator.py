from typed_time_provider import Microseconds, WallClock

from app.contracts.referrals import ReferralLinksFacilitatorContract
from app.contracts.repositories.referral_repositories import ReferralCodeRepoContract
from app.schemas.constants.referrals import ReferralCodeOwnerKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.referrals import ReferralCodeDocument
from app.schemas.typings.analytics.constrained_strings import (
    ReferralCode,
    SignupSourceTag,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.referrals.constrained_strings import ReferralLink
from app.utilities.referrals.referral_identity import (
    business_code_candidates,
    referral_code_id,
)
from app.utilities.referrals.referral_links import (
    build_referral_link,
    shows_powered_by,
)


class ReferralLinksFacilitator(ReferralLinksFacilitatorContract):
    """
    Links to the platform's site (CABINET_BASE_URL, where the landing page
    lives) carrying a business's own referral code. The code derives from
    the business and is claimed in `referral_codes` the first time a link
    is made, so a visitor's `?ref=` leads back to it at sign-up; a code a
    partner already holds is skipped for the longer candidate.
    """

    def __init__(
        self,
        referral_code_repo: ReferralCodeRepoContract,
        cabinet_base_url: CabinetBaseUrl | None,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._codes: ReferralCodeRepoContract = referral_code_repo
        self._cabinet_base_url: CabinetBaseUrl | None = cabinet_base_url
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def business_code(self, business_id: BusinessId) -> ReferralCode | None:
        for candidate in business_code_candidates(business_id):
            stored: ReferralCodeDocument | None = self._codes.get(
                referral_code_id(candidate)
            )
            if stored is None:
                stored = self._claim(business_id, candidate)

            if (
                stored.owner_kind is ReferralCodeOwnerKind.BUSINESS
                and stored.business_id == business_id
            ):
                return stored.code

        return None

    def link_for(
        self, business_id: BusinessId, source: SignupSourceTag
    ) -> ReferralLink | None:
        if self._cabinet_base_url is None:
            return None

        code: ReferralCode | None = self.business_code(business_id)
        if code is None:
            return None

        return build_referral_link(str(self._cabinet_base_url), code, source)

    def powered_by_link(
        self, business: BusinessDocument, source: SignupSourceTag
    ) -> ReferralLink | None:
        if not shows_powered_by(business):
            return None

        return self.link_for(business.id, source)

    def _claim(
        self, business_id: BusinessId, candidate: ReferralCode
    ) -> ReferralCodeDocument:
        """Claim the code; when another request won the race, its row."""

        now: Microseconds = self._wall_clock.now_unix()
        row = ReferralCodeDocument(
            id=referral_code_id(candidate),
            code=candidate,
            owner_kind=ReferralCodeOwnerKind.BUSINESS,
            business_id=business_id,
            created_at=now,
            updated_at=now,
        )
        if self._codes.claim(row):
            return row

        return self._codes.get(row.id) or row
