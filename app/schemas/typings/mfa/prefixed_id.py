"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class MfaChallengeId(BasePrefixedTypedId):
    """
    Random identifier of the second step of one sign-in: issued after the
    login code matched, for a user who must also give an authenticator code.
    """

    prefix = "mfa_challenge"


class RecoveryCodeId(BasePrefixedTypedId):
    """Random identifier of one single-use recovery code of a user."""

    prefix = "recovery_code"


class TotpFactorId(BasePrefixedTypedId):
    """Random identifier of a user's authenticator app (TOTP factor)."""

    prefix = "totp_factor"


# Keep abc order for all non example types, if possible.
