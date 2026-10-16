"""Checking a person's authenticator code or one of their recovery codes."""

from typed_time_provider import Microseconds

from app.contracts.mfa import TotpSecretCipherAdapterContract
from app.contracts.repositories.mfa_repositories import (
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.schemas.constants.mfa import TotpFactorStatus
from app.schemas.domain.mfa import RecoveryCodeDocument, TotpFactorDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.mfa.constrained_integers import TotpTimeStep
from app.schemas.typings.mfa.constrained_strings import (
    RecoveryCode,
    TotpCode,
    TotpSecret,
)
from app.schemas.typings.mfa.strings import RawRecoveryCodeInput
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.recovery_codes import (
    is_recovery_code_matching,
    normalize_recovery_code,
)
from app.utilities.security.totp_codes import find_totp_step
from app.utilities.security.two_factor_policy import wrong_code

WRONG_CODE_MESSAGE: str = "The code is wrong or was already used."
ONE_CODE_MESSAGE: str = (
    "Enter either a code from your authenticator app or a recovery code."
)


class SecondFactorCheck:
    """
    An authenticator code is accepted for the current 30-second step or
    one step before or after, and only for a step later than the last
    accepted one (compare-and-swap), so a code works once. A recovery code
    is spent by compare-and-swap, so it works once too. A wrong code is
    WrongCodeError (422); callers limit how often one may try.
    """

    def __init__(
        self,
        totp_factor_repo: TotpFactorRepoContract,
        recovery_code_repo: RecoveryCodeRepoContract,
        totp_secret_cipher: TotpSecretCipherAdapterContract,
    ) -> None:
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._recovery_code_repo: RecoveryCodeRepoContract = recovery_code_repo
        self._totp_secret_cipher: TotpSecretCipherAdapterContract = totp_secret_cipher

    def verify(
        self,
        user_id: UserId,
        code: TotpCode | None,
        recovery_code: RawRecoveryCodeInput | None,
        now: Microseconds,
    ) -> None:
        if (code is None) == (recovery_code is None):
            raise ValidationFailedError(ONE_CODE_MESSAGE)

        if code is not None:
            self._verify_totp(user_id, code, now)
            return

        if recovery_code is not None:
            self._spend_recovery_code(user_id, recovery_code, now)

    def confirm_pending(
        self, factor: TotpFactorDocument, code: TotpCode, now: Microseconds
    ) -> TotpFactorDocument:
        """The first code of a new authenticator turns it on."""

        secret: TotpSecret = self._totp_secret_cipher.open(factor.sealed_secret)
        step: TotpTimeStep | None = find_totp_step(secret, code, int(now), None)
        if step is None:
            raise wrong_code(WRONG_CODE_MESSAGE)

        activated: TotpFactorDocument | None = self._totp_factor_repo.activate(
            factor.user_id, step, now
        )
        if activated is None:
            raise wrong_code(WRONG_CODE_MESSAGE)

        return activated

    def _verify_totp(self, user_id: UserId, code: TotpCode, now: Microseconds) -> None:
        factor: TotpFactorDocument | None = self._totp_factor_repo.get_for_user(user_id)
        if factor is None or factor.status is not TotpFactorStatus.ACTIVE:
            raise wrong_code(WRONG_CODE_MESSAGE)

        secret: TotpSecret = self._totp_secret_cipher.open(factor.sealed_secret)
        step: TotpTimeStep | None = find_totp_step(
            secret, code, int(now), factor.last_used_step
        )
        if (
            step is None
            or self._totp_factor_repo.record_use(user_id, step, now) is None
        ):
            raise wrong_code(WRONG_CODE_MESSAGE)

    def _spend_recovery_code(
        self, user_id: UserId, typed: RawRecoveryCodeInput, now: Microseconds
    ) -> None:
        code: RecoveryCode | None = normalize_recovery_code(typed)
        if code is None:
            raise wrong_code(WRONG_CODE_MESSAGE)

        for stored in self._recovery_code_repo.list_for_user(user_id):
            if stored.used_at is not None or not is_recovery_code_matching(
                user_id, stored.id, code, stored.code_hash
            ):
                continue

            spent: RecoveryCodeDocument | None = self._recovery_code_repo.spend(
                stored.id, now
            )
            if spent is not None:
                return

        raise wrong_code(WRONG_CODE_MESSAGE)
