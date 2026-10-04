"""Moving the secrets of people's authenticators to the current key."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.mfa import TotpSecretCipherAdapterContract
from app.contracts.repositories.mfa_repositories import TotpFactorRepoContract
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.mfa.strings import SealedTotpSecret
from app.use_cases.admin.security.secret_resealer import RotationTally


class TotpSecretResealer:
    """
    Part of the key rotation run: every authenticator secret (platform-wide)
    is sealed again with the current key, so an old key can be dropped
    without locking anyone out. One no key opens is counted unreadable: its
    person signs in with a recovery code and sets the authenticator up
    again. A factor changed meanwhile is left for the next run.
    """

    def __init__(
        self,
        totp_factor_repo: TotpFactorRepoContract,
        totp_secret_cipher: TotpSecretCipherAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._totp_secret_cipher: TotpSecretCipherAdapterContract = totp_secret_cipher
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def reseal_all(self, tally: RotationTally) -> None:
        for factor in self._totp_factor_repo.list_all():
            tally.total += 1
            if self._totp_secret_cipher.is_current(factor.sealed_secret):
                tally.current += 1
                continue

            try:
                resealed: SealedTotpSecret = self._totp_secret_cipher.reseal(
                    factor.sealed_secret
                )
            except ValidationFailedError:
                tally.unreadable += 1
                continue

            if self._totp_factor_repo.replace_sealed_secret(
                factor.user_id,
                factor.sealed_secret,
                resealed,
                self._wall_clock.now_unix(),
            ):
                tally.rotated += 1
