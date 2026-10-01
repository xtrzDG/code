"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class OtpChallengeId(BasePrefixedTypedId):
    """Random identifier of one one-time code login attempt."""

    prefix = "otp_challenge"


class OwnerId(BasePrefixedTypedId):
    """Random identifier of a business owner account."""

    prefix = "owner"


class OwnerSessionId(BasePrefixedTypedId):
    """Random identifier of an owner session."""

    prefix = "owner_session"


# Keep abc order for all non example types, if possible.
