"""The second step of a sign-in, as the login code step answers it."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.passkeys import SecondFactorMethod
from app.schemas.typings.mfa.booleans import IsMfaRequired, IsTotpEnrollmentRequired
from app.schemas.typings.mfa.constrained_integers import MfaChallengeLifetimeSeconds
from app.schemas.typings.mfa.prefixed_id import MfaChallengeId
from app.schemas.typings.users.booleans import IsNewUser


class MfaChallengeView(ImmutableDTO):
    """
    The login code matched; the sign-in needs a second factor too.
    `methods`: what the person can answer with, the preferred first (a
    passkey, the authenticator app, a recovery code). `requires_enrollment`:
    a platform admin without a second factor sets one up first, with one of
    `enrollment_methods` (a passkey, `POST /v1/auth/mfa/passkey/enroll`,
    when the server offers them; the authenticator app,
    `POST /v1/auth/mfa/enroll`).
    """

    mfa_challenge_id: MfaChallengeId
    expires_in_seconds: MfaChallengeLifetimeSeconds
    requires_enrollment: IsTotpEnrollmentRequired = False
    methods: list[SecondFactorMethod] = Field(default_factory=list[SecondFactorMethod])
    enrollment_methods: list[SecondFactorMethod] = Field(
        default_factory=list[SecondFactorMethod]
    )


class MfaRequiredView(ImmutableDTO):
    """
    The answer of the login code step for a person who must also give an
    authenticator code (they set one up, or they are a platform admin): no
    session yet. `POST /v1/auth/mfa/verify` with `mfa_challenge` opens it.
    """

    mfa_required: IsMfaRequired = True
    mfa_challenge: MfaChallengeView
    is_new_user: IsNewUser
