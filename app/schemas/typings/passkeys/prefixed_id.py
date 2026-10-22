"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class PasskeyChallengeId(BasePrefixedTypedId):
    """
    Random identifier of one passkey ceremony (adding a passkey, or using
    one to sign in or to confirm it is you): the challenge it signs.
    """

    prefix = "passkey_challenge"


class PasskeyId(BasePrefixedTypedId):
    """
    Identifier of one passkey a person added to their account, derived
    (UUID v5) from its credential id: one credential is one passkey.
    """

    prefix = "passkey"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = None


# Keep abc order for all non example types, if possible.
