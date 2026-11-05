"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class OtpChallengeId(BasePrefixedTypedId):
    """Random identifier of one one-time code login attempt."""

    prefix = "otp_challenge"


class UserId(BasePrefixedTypedId):
    """Random identifier of a user (owner, staff, or platform admin)."""

    prefix = "user"


class UserSessionId(BasePrefixedTypedId):
    """Random identifier of a signed-in session."""

    prefix = "user_session"


# Keep abc order for all non example types, if possible.
