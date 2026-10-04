from app.contracts.repositories.mfa_repositories import (
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.mfa import AccountSecurityView, SessionAssurance
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.mfa.constrained_integers import RecoveryCodeCount
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.platform_admins import is_listed_platform_admin


class GetAccountSecurityUseCase(UseCaseContract[UserId, AccountSecurityView]):
    """
    The signed-in person's two-factor sign-in (Account → Security): their
    authenticator, how many unused recovery codes are left, how the current
    session is signed in, and whether they must use two factors (a
    platform admin, by the admin lists of now).
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        totp_factor_repo: TotpFactorRepoContract,
        recovery_code_repo: RecoveryCodeRepoContract,
        session_assurance: SessionAssuranceContract,
        app_settings: AppSettings,
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._recovery_code_repo: RecoveryCodeRepoContract = recovery_code_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: UserId) -> AccountSecurityView:
        user: UserDocument | None = self._user_repo.get(input_data)
        if user is None:
            raise NotFoundError(f"User {input_data} was not found.")

        factor: TotpFactorDocument | None = self._totp_factor_repo.get_for_user(user.id)
        unused_codes: int = sum(
            1
            for code in self._recovery_code_repo.list_for_user(user.id)
            if code.used_at is None
        )
        assurance: SessionAssurance | None = self._session_assurance.current()
        is_own_session: bool = assurance is not None and assurance.user_id == user.id
        return AccountSecurityView(
            totp_status=None if factor is None else factor.status,
            totp_confirmed_at=None if factor is None else factor.confirmed_at,
            totp_last_used_at=None if factor is None else factor.last_used_at,
            recovery_codes_left=RecoveryCodeCount(unused_codes),
            auth_level=assurance.auth_level
            if assurance is not None and is_own_session
            else None,
            authenticated_at=assurance.authenticated_at
            if assurance is not None and is_own_session
            else None,
            step_up_max_age_seconds=self._app_settings.step_up_max_age_seconds,
            is_mfa_required=is_listed_platform_admin(user, self._app_settings),
        )
