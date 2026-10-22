"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class PasskeyChallengeId(BasePrefixedTypedId):
    """
    Random identifier of one passkey ceremony (adding a passkey, or using
    one to sign in or to confirm it is you): the challenge it signs.
    """

    prefix = "passkey_challenge"


class PasskeyId(BasePrefixedTypedId):
    """Random identifier of one passkey a person added to their account."""

    prefix = "passkey"


# Keep abc order for all non example types, if possible.
