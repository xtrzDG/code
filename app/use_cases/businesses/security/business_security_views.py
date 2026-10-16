"""The two-factor requirement of a business as the cabinet shows it."""

from app.contracts.repositories.mfa_repositories import TotpFactorRepoContract
from app.schemas.constants.mfa import TotpFactorStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.dto.mfa import BusinessSecurityView, SessionAssurance
from app.schemas.typings.mfa.constrained_integers import MemberWithoutTwoFactorCount
from app.schemas.typings.users.prefixed_id import UserId


def build_business_security_view(
    business: BusinessDocument,
    totp_factor_repo: TotpFactorRepoContract,
    assurance: SessionAssurance | None,
    viewer_id: UserId,
) -> BusinessSecurityView:
    """Counts the members without an authenticator (a team is small)."""

    without_two_factor: int = 0
    for member in business.members:
        factor: TotpFactorDocument | None = totp_factor_repo.get_for_user(
            member.user_id
        )
        if factor is None or factor.status is not TotpFactorStatus.ACTIVE:
            without_two_factor += 1

    return BusinessSecurityView(
        business_id=business.id,
        require_mfa_for_members=business.require_mfa_for_members,
        members_without_two_factor=MemberWithoutTwoFactorCount(without_two_factor),
        viewer_auth_level=assurance.auth_level
        if assurance is not None and assurance.user_id == viewer_id
        else None,
    )
