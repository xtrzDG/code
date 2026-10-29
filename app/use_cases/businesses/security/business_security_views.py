"""The two-factor requirement of a business as the cabinet shows it."""

from app.contracts.repositories.mfa_repositories import TotpFactorRepoContract
from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.mfa import BusinessSecurityView, SessionAssurance
from app.schemas.typings.mfa.constrained_integers import MemberWithoutTwoFactorCount
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.second_factors import has_second_factor


def build_business_security_view(
    business: BusinessDocument,
    totp_factor_repo: TotpFactorRepoContract,
    passkey_repo: PasskeyRepoContract,
    assurance: SessionAssurance | None,
    viewer_id: UserId,
) -> BusinessSecurityView:
    """Counts the members without a second factor (a team is small)."""

    without_two_factor: int = sum(
        1
        for member in business.members
        if not has_second_factor(totp_factor_repo, passkey_repo, member.user_id)
    )

    return BusinessSecurityView(
        business_id=business.id,
        require_mfa_for_members=business.require_mfa_for_members,
        members_without_two_factor=MemberWithoutTwoFactorCount(without_two_factor),
        viewer_auth_level=assurance.auth_level
        if assurance is not None and assurance.user_id == viewer_id
        else None,
    )
