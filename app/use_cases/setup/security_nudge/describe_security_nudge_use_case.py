from app.contracts.repositories.mfa_repositories import TotpFactorRepoContract
from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.contracts.repositories.security_nudge_repositories import (
    SecurityNudgeRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.security_nudges import SecurityNudgeReason
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.security_nudges import SecurityNudgeDocument
from app.schemas.dto.security_nudges import SecurityNudgeSource, SecurityNudgeView
from app.schemas.typings.security_nudges.constrained_integers import TeamMemberCount
from app.use_cases.shared.second_factors import has_second_factor
from app.utilities.security.security_nudge_policy import security_nudge_reason


class DescribeSecurityNudgeUseCase(
    UseCaseContract[SecurityNudgeSource, SecurityNudgeView]
):
    """
    The second-factor reminder of an already authorized person in one
    business (the banner and the setup guide's step read it): whether they
    are an owner, have a passkey or an authenticator app, how many people
    the team has, and whether the reminder is shown and why.
    """

    def __init__(
        self,
        totp_factor_repo: TotpFactorRepoContract,
        passkey_repo: PasskeyRepoContract,
        security_nudge_repo: SecurityNudgeRepoContract,
    ) -> None:
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._security_nudge_repo: SecurityNudgeRepoContract = security_nudge_repo

    def run(self, input_data: SecurityNudgeSource) -> SecurityNudgeView:
        business: BusinessDocument = input_data.business
        is_owner: bool = any(
            member.user_id == input_data.user_id
            and member.role is BusinessMemberRole.OWNER
            for member in business.members
        )
        has_factor: bool = has_second_factor(
            self._totp_factor_repo, self._passkey_repo, input_data.user_id
        )
        team_size = TeamMemberCount(len(business.members))
        nudge: SecurityNudgeDocument | None = (
            self._security_nudge_repo.get(business.id, input_data.user_id)
            if is_owner
            else None
        )
        reason: SecurityNudgeReason | None = security_nudge_reason(
            is_owner=is_owner,
            is_live=business.published_assistant_version_id is not None,
            has_second_factor=has_factor,
            team_size=team_size,
            nudge=nudge,
        )
        return SecurityNudgeView(
            is_shown=reason is not None,
            reason=reason,
            is_owner=is_owner,
            has_second_factor=has_factor,
            team_size=team_size,
            dismissed_at=None if nudge is None else nudge.dismissed_at,
        )
