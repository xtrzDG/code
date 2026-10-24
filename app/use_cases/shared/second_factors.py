"""
A person's second factors, for every check that asks whether they have
one: an authenticator app that is on, or a passkey (one suspected of a
copy still counts: the account keeps asking for a second factor, and the
person uses another one or a recovery code). Sign-in, step-up, Account →
Security and a business's two-factor rule read them here.
"""

from app.contracts.repositories.mfa_repositories import (
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.schemas.constants.mfa import TotpFactorStatus
from app.schemas.constants.passkeys import SecondFactorMethod
from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.domain.passkeys import PasskeyDocument
from app.schemas.typings.users.prefixed_id import UserId


def has_active_authenticator(
    totp_factor_repo: TotpFactorRepoContract, user_id: UserId
) -> bool:
    factor: TotpFactorDocument | None = totp_factor_repo.get_for_user(user_id)
    return factor is not None and factor.status is TotpFactorStatus.ACTIVE


def has_second_factor(
    totp_factor_repo: TotpFactorRepoContract,
    passkey_repo: PasskeyRepoContract,
    user_id: UserId,
) -> bool:
    return (
        has_active_authenticator(totp_factor_repo, user_id)
        or int(passkey_repo.count_for_user(user_id)) > 0
    )


def usable_passkeys(
    passkey_repo: PasskeyRepoContract, user_id: UserId
) -> list[PasskeyDocument]:
    """The person's passkeys that may sign: none suspected of a copy."""

    return [
        passkey
        for passkey in passkey_repo.list_for_user(user_id)
        if passkey.clone_suspected_at is None
    ]


def second_factor_methods(
    totp_factor_repo: TotpFactorRepoContract,
    passkey_repo: PasskeyRepoContract,
    recovery_code_repo: RecoveryCodeRepoContract,
    user_id: UserId,
    are_passkeys_available: bool,
) -> list[SecondFactorMethod]:
    """
    How the person can pass the second step of a sign-in, the preferred
    first: a passkey (phishing resistant), the authenticator app, a
    recovery code left.
    """

    methods: list[SecondFactorMethod] = []
    if are_passkeys_available and usable_passkeys(passkey_repo, user_id):
        methods.append(SecondFactorMethod.PASSKEY)
    if has_active_authenticator(totp_factor_repo, user_id):
        methods.append(SecondFactorMethod.TOTP)
    if any(code.used_at is None for code in recovery_code_repo.list_for_user(user_id)):
        methods.append(SecondFactorMethod.RECOVERY_CODE)
    return methods
