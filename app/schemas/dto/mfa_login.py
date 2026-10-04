"""The second step of a sign-in, as the first step's answer names it."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.mfa.booleans import IsTotpEnrollmentRequired
from app.schemas.typings.mfa.constrained_integers import MfaChallengeLifetimeSeconds
from app.schemas.typings.mfa.prefixed_id import MfaChallengeId


class MfaChallengeView(ImmutableDTO):
    """
    The login code matched; the sign-in needs an authenticator code (or a
    recovery code) too. `requires_enrollment`: a platform admin without an
    authenticator sets one up first (`POST /v1/auth/mfa/enroll`).
    """

    mfa_challenge_id: MfaChallengeId
    expires_in_seconds: MfaChallengeLifetimeSeconds
    requires_enrollment: IsTotpEnrollmentRequired = False
