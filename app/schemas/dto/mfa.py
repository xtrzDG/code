"""
Two-factor sign-in: the second step of a sign-in, a person's
authenticator and recovery codes, confirming sensitive actions (step-up)
and a business's two-factor requirement.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.mfa import AuthLevel, StepUpMethod, TotpFactorStatus
from app.schemas.dto.users import OtpChallengeView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.mfa.booleans import IsMfaRequired, IsMfaRequiredForMembers
from app.schemas.typings.mfa.constrained_integers import (
    MemberWithoutTwoFactorCount,
    RecoveryCodeCount,
    StepUpMaxAgeSeconds,
)
from app.schemas.typings.mfa.constrained_strings import (
    RecoveryCode,
    TotpCode,
    TotpSecret,
)
from app.schemas.typings.mfa.prefixed_id import MfaChallengeId
from app.schemas.typings.mfa.strings import (
    RawRecoveryCodeInput,
    TotpAccountLabel,
    TotpIssuerName,
    TotpProvisioningUri,
)
from app.schemas.typings.users.constrained_strings import OtpCode, SessionUserAgent
from app.schemas.typings.users.prefixed_id import (
    OtpChallengeId,
    UserId,
    UserSessionId,
)


class SessionAssurance(ImmutableDTO):
    """
    The signed-in session of the request being served: whose it is, how it
    was signed in and when its person last proved it is them (None for a
    session from before two-factor sign-in existed), and the request
    itself: the caller's address and whether it reads or changes
    (`access_mode`; WRITE unless the gateway knows it reads).
    """

    user_id: UserId
    session_id: UserSessionId
    auth_level: AuthLevel
    authenticated_at: Microseconds | None = None
    client_ip_address: ClientIpAddress | None = None
    access_mode: BusinessAccessMode = BusinessAccessMode.WRITE


class VerifyMfaLoginRequest(ImmutableDTO):
    """The second step of a sign-in: an authenticator code or a recovery code."""

    mfa_challenge_id: MfaChallengeId
    code: TotpCode | None = None
    recovery_code: RawRecoveryCodeInput | None = None


class VerifyMfaLoginCommand(ImmutableDTO):
    mfa_challenge_id: MfaChallengeId
    code: TotpCode | None = None
    recovery_code: RawRecoveryCodeInput | None = None
    client_ip_address: ClientIpAddress | None = None
    user_agent: SessionUserAgent | None = None


class StartMfaEnrollmentRequest(ImmutableDTO):
    """A platform admin without an authenticator sets one up while signing in."""

    mfa_challenge_id: MfaChallengeId


class StartMfaEnrollmentCommand(ImmutableDTO):
    mfa_challenge_id: MfaChallengeId
    client_ip_address: ClientIpAddress | None = None


class TotpEnrollmentView(ImmutableDTO):
    """
    A new authenticator to add to an app: the QR code's address and, for
    typing it in by hand, the secret. Shown once; the first code from the
    app confirms it.
    """

    secret: TotpSecret
    provisioning_uri: TotpProvisioningUri
    account_label: TotpAccountLabel
    issuer: TotpIssuerName


class ConfirmTotpRequest(ImmutableDTO):
    """The first code from the app, which turns the new authenticator on."""

    code: TotpCode


class ConfirmTotpCommand(ImmutableDTO):
    user_id: UserId
    code: TotpCode
    client_ip_address: ClientIpAddress | None = None


class MfaChangeCommand(ImmutableDTO):
    """Remove the authenticator, or replace the recovery codes."""

    user_id: UserId
    client_ip_address: ClientIpAddress | None = None


class RecoveryCodesView(ImmutableDTO):
    """A new set of recovery codes, shown once: only their hashes are kept."""

    recovery_codes: list[RecoveryCode]


class AccountSecurityView(ImmutableDTO):
    """
    The signed-in person's two-factor sign-in: their authenticator (None:
    none set up), how many recovery codes are left, and how the current
    session is signed in. `is_mfa_required`: a platform admin, who must use
    an authenticator.
    """

    totp_status: TotpFactorStatus | None = None
    totp_confirmed_at: Microseconds | None = None
    totp_last_used_at: Microseconds | None = None
    recovery_codes_left: RecoveryCodeCount = RecoveryCodeCount(0)
    auth_level: AuthLevel | None = None
    authenticated_at: Microseconds | None = None
    step_up_max_age_seconds: StepUpMaxAgeSeconds
    is_mfa_required: IsMfaRequired = False


class StartStepUpCommand(ImmutableDTO):
    user_id: UserId
    client_ip_address: ClientIpAddress | None = None


class StepUpChallengeView(ImmutableDTO):
    """
    How to confirm it is you: with an authenticator code (or a recovery
    code), or with the login code just sent (`login_code`).
    """

    method: StepUpMethod
    login_code: OtpChallengeView | None = None


class VerifyStepUpRequest(ImmutableDTO):
    """
    The confirmation: `code` of the authenticator, a `recovery_code`, or the
    `login_code` of the challenge `/v1/auth/step-up` sent.
    """

    code: TotpCode | None = None
    recovery_code: RawRecoveryCodeInput | None = None
    challenge_id: OtpChallengeId | None = None
    login_code: OtpCode | None = None


class VerifyStepUpCommand(ImmutableDTO):
    user_id: UserId
    code: TotpCode | None = None
    recovery_code: RawRecoveryCodeInput | None = None
    challenge_id: OtpChallengeId | None = None
    login_code: OtpCode | None = None
    client_ip_address: ClientIpAddress | None = None


class SessionAssuranceView(ImmutableDTO):
    """How the session is signed in now, and until when it may do sensitive actions."""

    auth_level: AuthLevel
    authenticated_at: Microseconds
    step_up_valid_until: Microseconds


class BusinessSecurityView(ImmutableDTO):
    """
    Whether the team must sign in with two factors, how many members have
    no authenticator yet (they cannot open the business while it is on),
    and whether the viewer's own session is signed in with two factors.
    """

    business_id: BusinessId
    require_mfa_for_members: IsMfaRequiredForMembers
    members_without_two_factor: MemberWithoutTwoFactorCount = (
        MemberWithoutTwoFactorCount(0)
    )
    viewer_auth_level: AuthLevel | None = None


class UpdateBusinessSecurityRequest(ImmutableDTO):
    require_mfa_for_members: IsMfaRequiredForMembers


class UpdateBusinessSecurityCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    require_mfa_for_members: IsMfaRequiredForMembers
    client_ip_address: ClientIpAddress | None = None
