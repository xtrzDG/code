"""Keep abc order."""

from base_typed_string import BaseTypedString


class PasskeyAccountName(BaseTypedString):
    """
    The account name an authenticator shows next to a passkey: the
    person's e-mail address or phone number.

    Example:
        name = PasskeyAccountName("owner@example.com")
    """


class WebAuthnRelyingPartyName(BaseTypedString):
    """
    The service name an authenticator shows when a passkey is added.

    Example:
        name = WebAuthnRelyingPartyName("Assistant Workshop")
    """


# Keep abc order for all non example types, if possible.
