"""
The building blocks of two-factor sign-in: authenticator codes (RFC 6238,
one step of drift, each code once), recovery codes, the sealed secrets
and the step-up check of sensitive actions.
"""

from contextvars import copy_context

import pytest
from typed_time_provider import Microseconds

from app.adapters.security.totp_secret_cipher_adapter import TotpSecretCipherAdapter
from app.schemas.constants.mfa import AuthLevel
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.mfa.constrained_integers import (
    StepUpMaxAgeSeconds,
    TotpTimeStep,
)
from app.schemas.typings.mfa.constrained_strings import TotpSecret
from app.schemas.typings.mfa.prefixed_id import RecoveryCodeId
from app.schemas.typings.mfa.strings import (
    RawRecoveryCodeInput,
    SealedTotpSecret,
    TotpAccountLabel,
    TotpIssuerName,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.security.recovery_codes import (
    generate_recovery_codes,
    hash_recovery_code,
    is_recovery_code_matching,
    normalize_recovery_code,
)
from app.utilities.security.require_recent_authentication import (
    RequireRecentAuthentication,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from app.utilities.security.totp_codes import (
    current_totp_step,
    find_totp_step,
    generate_totp_secret,
    totp_code_at,
    totp_provisioning_uri,
)
from tests.foundation.access_support import signed_in
from tests.storage.storage_testing import build_fixed_wall_clock

# RFC 6238 appendix B: the SHA-1 secret "12345678901234567890" in Base32.
RFC_SECRET: TotpSecret = TotpSecret("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ")
SECOND: int = 1_000_000
OLD_KEY: str = "old-totp-test-key-0000000000000000"
NEW_KEY: str = "new-totp-test-key-0000000000000000"


def test_codes_follow_rfc_6238() -> None:
    # 59 s and 1111111109 s after the epoch (the RFC's 8 digits, last 6).
    assert totp_code_at(RFC_SECRET, current_totp_step(59 * SECOND)) == "287082"
    assert (
        totp_code_at(RFC_SECRET, current_totp_step(1_111_111_109 * SECOND)) == "081804"
    )


def test_a_code_is_accepted_one_step_around_now_and_only_once() -> None:
    now: int = 1_800_000_000 * SECOND
    step: int = int(current_totp_step(now))
    previous = totp_code_at(RFC_SECRET, TotpTimeStep(step - 1))
    following = totp_code_at(RFC_SECRET, TotpTimeStep(step + 1))
    too_old = totp_code_at(RFC_SECRET, TotpTimeStep(step - 2))

    assert find_totp_step(RFC_SECRET, previous, now, None) == step - 1
    assert find_totp_step(RFC_SECRET, following, now, None) == step + 1
    assert find_totp_step(RFC_SECRET, too_old, now, None) is None
    assert find_totp_step(RFC_SECRET, previous, now, TotpTimeStep(step - 1)) is None
    assert find_totp_step(RFC_SECRET, following, now, TotpTimeStep(step)) == step + 1


def test_new_secrets_and_the_setup_link() -> None:
    secrets = {generate_totp_secret() for _ in range(20)}
    uri = totp_provisioning_uri(
        RFC_SECRET, TotpAccountLabel("+995 555 12 34 56"), TotpIssuerName("Café & Co")
    )

    assert len(secrets) == 20
    assert all(len(secret) == 32 for secret in secrets)
    assert uri == (
        "otpauth://totp/Caf%C3%A9%20%26%20Co:%2B995%20555%2012%2034%2056"
        f"?secret={RFC_SECRET}&issuer=Caf%C3%A9%20%26%20Co"
    )


def test_recovery_codes_are_typed_loosely_and_stored_as_keyed_hashes() -> None:
    codes = generate_recovery_codes()
    user_id, code_id = UserId(), RecoveryCodeId()
    code = codes[0]
    stored = hash_recovery_code(user_id, code_id, code)
    typed = normalize_recovery_code(RawRecoveryCodeInput(f" {code.upper()} "))
    compact = normalize_recovery_code(RawRecoveryCodeInput(code.replace("-", "")))

    assert len(codes) == 10 and len(set(codes)) == 10
    assert str(code) not in str(stored)
    assert typed == code and compact == code
    assert normalize_recovery_code(RawRecoveryCodeInput("abcd-efgh")) is None
    assert normalize_recovery_code(RawRecoveryCodeInput("abcd-efgh-ijk1")) is None
    assert is_recovery_code_matching(user_id, code_id, code, stored)
    assert not is_recovery_code_matching(UserId(), code_id, code, stored)
    assert not is_recovery_code_matching(user_id, RecoveryCodeId(), code, stored)


def test_secrets_are_sealed_with_the_newest_key_and_resealed_after_rotation() -> None:
    old_ring = TotpSecretCipherAdapter(
        assemble_app_settings({"ENCRYPTION_KEYS": OLD_KEY})
    )
    new_ring = TotpSecretCipherAdapter(
        assemble_app_settings({"ENCRYPTION_KEYS": f"{NEW_KEY},{OLD_KEY}"})
    )
    other = TotpSecretCipherAdapter(assemble_app_settings({"ENCRYPTION_KEYS": NEW_KEY}))
    sealed = old_ring.seal(RFC_SECRET)

    resealed = new_ring.reseal(sealed)

    assert str(RFC_SECRET) not in str(sealed)
    assert old_ring.is_current(sealed)
    assert not new_ring.is_current(sealed)
    assert new_ring.open(sealed) == RFC_SECRET
    assert new_ring.is_current(resealed)
    assert other.open(resealed) == RFC_SECRET
    with pytest.raises(ValidationFailedError):
        other.open(sealed)
    with pytest.raises(ValidationFailedError):
        other.reseal(SealedTotpSecret("not-a-token"))
    assert not other.is_current(SealedTotpSecret("not-a-token"))


def guard(
    context: SessionAssuranceContext, now_seconds: int
) -> RequireRecentAuthentication:
    return RequireRecentAuthentication(
        context,
        build_fixed_wall_clock(now_seconds * 1_000_000_000),
        StepUpMaxAgeSeconds(600),
    )


def check_at(signed_in_at: int | None, now_seconds: int) -> None:
    context = SessionAssuranceContext()

    def request() -> None:
        context.bind(
            signed_in(
                UserId(),
                AuthLevel.ONE_FACTOR,
                None if signed_in_at is None else signed_in_at * SECOND,
            )
        )
        guard(context, now_seconds).require_recent_authentication()

    copy_context().run(request)


def test_step_up_passes_within_the_window_only() -> None:
    check_at(1_000, 1_000)
    check_at(1_000, 1_600)
    with pytest.raises(StepUpRequiredError) as refusal:
        check_at(1_000, 1_601)
    with pytest.raises(StepUpRequiredError):
        check_at(None, 1_000)
    # A time in the future (a moved clock) is not trusted either.
    with pytest.raises(StepUpRequiredError):
        check_at(1_001, 1_000)

    assert [reason.code for reason in refusal.value.reasons] == ["step_up_required"]
    assert refusal.value.reasons[0].details == ["600"]


def test_step_up_refuses_work_outside_a_signed_in_request() -> None:
    context = SessionAssuranceContext()

    with pytest.raises(StepUpRequiredError):
        guard(context, 1_000).require_recent_authentication()


def test_a_bound_session_stays_in_its_own_request() -> None:
    context = SessionAssuranceContext()
    assurance = signed_in(UserId(), authenticated_at=Microseconds(5))

    def request() -> object:
        context.bind(assurance)
        return context.current()

    assert copy_context().run(request) == assurance
    assert context.current() is None
