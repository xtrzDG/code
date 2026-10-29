"""Whether a sign-in needs a second step, and how the person can answer it."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.repositories.mfa_repositories import (
    MfaChallengeRepoContract,
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.schemas.constants.passkeys import SecondFactorMethod
from app.schemas.domain.users import UserDocument
from app.schemas.dto.mfa_login import MfaChallengeView
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.booleans import IsNewUser
from app.use_cases.shared.second_factors import has_second_factor, second_factor_methods
from app.use_cases.users.mfa.mfa_challenges import issue_mfa_challenge


class SecondStepOffer:
    """
    A person with a second factor (a passkey or the authenticator app), and
    every platform admin (who sets one up then if they have none), gets a
    second step after the login code. The step names how it can be
    answered, a passkey first (phishing resistant), and, for an admin
    without a factor, how one can be set up: a passkey first when this
    server offers them, else the authenticator app.
    """

    def __init__(
        self,
        mfa_challenge_repo: MfaChallengeRepoContract,
        totp_factor_repo: TotpFactorRepoContract,
        passkey_repo: PasskeyRepoContract,
        recovery_code_repo: RecoveryCodeRepoContract,
        ceremony: PasskeyCeremonyAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._mfa_challenge_repo: MfaChallengeRepoContract = mfa_challenge_repo
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._recovery_code_repo: RecoveryCodeRepoContract = recovery_code_repo
        self._ceremony: PasskeyCeremonyAdapterContract = ceremony
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def offer(
        self,
        user: UserDocument,
        is_new_user: IsNewUser,
        client_ip_address: ClientIpAddress | None,
    ) -> MfaChallengeView | None:
        """The second step (stored), or None when the sign-in needs none."""

        has_factor: bool = has_second_factor(
            self._totp_factor_repo, self._passkey_repo, user.id
        )
        if not has_factor and not user.is_platform_admin:
            return None

        are_passkeys_available: bool = self._ceremony.is_available()
        enrollment_methods: list[SecondFactorMethod] = []
        if not has_factor:
            if are_passkeys_available:
                enrollment_methods.append(SecondFactorMethod.PASSKEY)
            enrollment_methods.append(SecondFactorMethod.TOTP)

        return issue_mfa_challenge(
            self._mfa_challenge_repo,
            self._wall_clock,
            user.id,
            is_new_user,
            client_ip_address,
            requires_enrollment=not has_factor,
            methods=second_factor_methods(
                self._totp_factor_repo,
                self._passkey_repo,
                self._recovery_code_repo,
                user.id,
                are_passkeys_available,
            ),
            enrollment_methods=enrollment_methods,
        )
