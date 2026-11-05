"""
Two-factor sign-in on both storages: an authenticator per user whose
codes count once (compare-and-swap on the last used step), recovery codes
spent once, second sign-in steps that count attempts and open one
session, and the key rotation's keyset walk over every authenticator.
"""

import pytest
from typed_time_provider import Microseconds

from app.adapters.security.totp_secret_cipher_adapter import TotpSecretCipherAdapter
from app.repositories import mfa_repositories
from app.repositories.mfa_repositories import (
    MfaChallengeRepository,
    RecoveryCodeRepository,
    TotpFactorRepository,
)
from app.schemas.constants.mfa import TotpFactorStatus
from app.schemas.domain.mfa import (
    MfaChallengeDocument,
    RecoveryCodeDocument,
    TotpFactorDocument,
)
from app.schemas.typings.mfa.constrained_integers import MfaAttemptCount, TotpTimeStep
from app.schemas.typings.mfa.constrained_strings import TotpSecret
from app.schemas.typings.mfa.strings import RecoveryCodeHash, SealedTotpSecret
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.security.secret_resealer import RotationTally
from app.use_cases.admin.security.totp_secret_resealer import TotpSecretResealer
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.storage.conftest import CollectionFactory
from tests.storage.storage_testing import build_fixed_wall_clock

pytestmark = pytest.mark.usefixtures("platform_scope")

NOW: Microseconds = Microseconds(1_800_000_000_000_000)
SECRET: TotpSecret = TotpSecret("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ")
OLD_KEY: str = "old-totp-test-key-0000000000000000"
NEW_KEY: str = "new-totp-test-key-0000000000000000"


def factor(user_id: UserId, sealed: str, created_at: int = 1) -> TotpFactorDocument:
    return TotpFactorDocument(
        user_id=user_id,
        sealed_secret=SealedTotpSecret(sealed),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


def test_an_authenticator_is_set_up_once_and_its_codes_count_once(
    collections: CollectionFactory,
) -> None:
    repo = TotpFactorRepository(collections(TotpFactorDocument, "totp_factors"))
    user_id = UserId()

    assert repo.start_enrollment(factor(user_id, "first"))
    # A new setup replaces an unconfirmed one.
    assert repo.start_enrollment(factor(user_id, "second"))
    assert repo.record_use(user_id, TotpTimeStep(9), NOW) is None
    activated = repo.activate(user_id, TotpTimeStep(10), NOW)
    assert repo.activate(user_id, TotpTimeStep(11), NOW) is None
    assert not repo.start_enrollment(factor(user_id, "third"))
    replayed = repo.record_use(user_id, TotpTimeStep(10), NOW)
    used = repo.record_use(user_id, TotpTimeStep(11), NOW)

    assert activated is not None
    assert activated.status is TotpFactorStatus.ACTIVE
    assert activated.sealed_secret == "second"
    assert replayed is None
    assert used is not None and used.last_used_step == 11
    assert not repo.replace_sealed_secret(
        user_id, SealedTotpSecret("first"), SealedTotpSecret("x"), NOW
    )
    assert repo.replace_sealed_secret(
        user_id, SealedTotpSecret("second"), SealedTotpSecret("resealed"), NOW
    )
    stored = repo.get_for_user(user_id)
    assert stored is not None and stored.sealed_secret == "resealed"
    repo.delete_for_user(user_id)
    assert repo.get_for_user(user_id) is None


def test_recovery_codes_are_replaced_per_user_and_spent_once(
    collections: CollectionFactory,
) -> None:
    repo = RecoveryCodeRepository(collections(RecoveryCodeDocument, "recovery_codes"))
    user_id, other_id = UserId(), UserId()

    def codes(owner: UserId, count: int) -> list[RecoveryCodeDocument]:
        return [
            RecoveryCodeDocument(user_id=owner, code_hash=RecoveryCodeHash(f"h{n}"))
            for n in range(count)
        ]

    repo.replace_for_user(user_id, codes(user_id, 3))
    repo.replace_for_user(other_id, codes(other_id, 2))
    fresh = codes(user_id, 2)
    repo.replace_for_user(user_id, fresh)
    spent = repo.spend(fresh[0].id, NOW)
    again = repo.spend(fresh[0].id, NOW)

    assert sorted(str(code.id) for code in repo.list_for_user(user_id)) == sorted(
        str(code.id) for code in fresh
    )
    assert len(repo.list_for_user(other_id)) == 2
    assert spent is not None and spent.used_at == NOW
    assert again is None
    repo.delete_for_user(user_id)
    assert repo.list_for_user(user_id) == []


def test_a_second_step_counts_attempts_and_is_consumed_once(
    collections: CollectionFactory,
) -> None:
    repo = MfaChallengeRepository(collections(MfaChallengeDocument, "mfa_challenges"))
    challenge = MfaChallengeDocument(user_id=UserId(), expires_at=NOW)
    repo.save(challenge)
    limit = MfaAttemptCount(2)

    attempts = [
        repo.register_failed_attempt(challenge.id, limit, NOW) for _ in range(3)
    ]
    consumed = repo.consume(challenge.id, NOW)

    assert attempts == [1, 2, None]
    assert consumed is not None and consumed.is_consumed
    assert repo.consume(challenge.id, NOW) is None
    assert repo.register_failed_attempt(challenge.id, MfaAttemptCount(5), NOW) is None


def test_key_rotation_reseals_every_authenticator_in_batches(
    collections: CollectionFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mfa_repositories, "FACTOR_BATCH_SIZE", DocumentQueryLimit(2))
    repo = TotpFactorRepository(collections(TotpFactorDocument, "totp_factors"))
    old = TotpSecretCipherAdapter(assemble_app_settings({"ENCRYPTION_KEYS": OLD_KEY}))
    ring = TotpSecretCipherAdapter(
        assemble_app_settings({"ENCRYPTION_KEYS": f"{NEW_KEY},{OLD_KEY}"})
    )
    users = [UserId() for _ in range(5)]
    sealed = [old.seal(SECRET), old.seal(SECRET), ring.seal(SECRET), old.seal(SECRET)]
    for index, sealed_secret in enumerate(sealed):
        repo.start_enrollment(factor(users[index], str(sealed_secret), created_at=7))
    repo.start_enrollment(factor(users[4], "not-a-token", created_at=3))
    tally = RotationTally()

    TotpSecretResealer(repo, ring, build_fixed_wall_clock()).reseal_all(tally)

    assert (tally.total, tally.rotated, tally.current, tally.unreadable) == (5, 3, 1, 1)
    for user_id in users[:4]:
        stored = repo.get_for_user(user_id)
        assert stored is not None and ring.is_current(stored.sealed_secret)
        assert ring.open(stored.sealed_secret) == SECRET
