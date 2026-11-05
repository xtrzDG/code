"""
Keep abc order.

The binary parts of a WebAuthn ceremony travel as unpadded base64url text
(RFC 4648 §5), each with a length bound of its own meaning.
"""

from base_typed_string import BaseConstrainedTypedString

BASE64URL_PATTERN: str = r"^[A-Za-z0-9_-]+$"


class PasskeyName(BaseConstrainedTypedString):
    """
    The name a person gives a passkey to tell it apart in their list (the
    device or password manager that keeps it): one line, no control
    characters.

    Example:
        name = PasskeyName("MacBook Touch ID")
    """

    min_length = 1
    max_length = 60
    pattern = r"^\S(?:[^\x00-\x1f\x7f]*\S)?\Z"


class RawWebAuthnTransport(BaseConstrainedTypedString):
    """
    A transport name exactly as the browser reported it with a new passkey
    ("internal", "hybrid", "usb", ...), before unknown names are dropped.

    Example:
        transport = RawWebAuthnTransport("hybrid")
    """

    min_length = 1
    max_length = 32
    pattern = r"^[a-z][a-z-]*$"


class WebAuthnAaguid(BaseConstrainedTypedString):
    """
    The model of the authenticator that made a passkey (a UUID; all zeros
    when the authenticator does not say).

    Example:
        model = WebAuthnAaguid("fbfc3007-154e-4ecc-8c0b-6e020557d7bd")
    """

    min_length = 36
    max_length = 36
    pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


class WebAuthnAttestationObject(BaseConstrainedTypedString):
    """
    The authenticator's attestation of a new passkey (CBOR): its public
    key, counter and format, as base64url.
    """

    min_length = 50
    max_length = 32_768
    pattern = BASE64URL_PATTERN


class WebAuthnAuthenticatorData(BaseConstrainedTypedString):
    """
    The authenticator data signed with a passkey (relying party hash,
    flags, counter), as base64url: at least the 37 fixed bytes.
    """

    min_length = 50
    max_length = 4_096
    pattern = BASE64URL_PATTERN


class WebAuthnChallenge(BaseConstrainedTypedString):
    """
    The random challenge one passkey ceremony signs (32 bytes as
    base64url); used once.
    """

    min_length = 22
    max_length = 128
    pattern = BASE64URL_PATTERN


class WebAuthnClientDataJson(BaseConstrainedTypedString):
    """
    The browser's record of a ceremony (type, challenge, origin), the JSON
    as base64url; the authenticator signs its hash.
    """

    min_length = 50
    max_length = 8_192
    pattern = BASE64URL_PATTERN


class WebAuthnCredentialId(BaseConstrainedTypedString):
    """
    The credential id an authenticator gives a passkey (16 to 1023 bytes
    as base64url): how a browser finds the passkey again.
    """

    min_length = 22
    max_length = 1_364
    pattern = BASE64URL_PATTERN


class WebAuthnPublicKey(BaseConstrainedTypedString):
    """
    The public key of a passkey (a COSE key, as base64url): what checks
    its signatures. Not secret.
    """

    min_length = 40
    max_length = 4_096
    pattern = BASE64URL_PATTERN


class WebAuthnRelyingPartyId(BaseConstrainedTypedString):
    """
    The domain passkeys are bound to (WEBAUTHN_RP_ID): the cabinet's host
    or a registrable domain above it, lower case, no scheme or port.

    Example:
        rp_id = WebAuthnRelyingPartyId("workshop.example")
    """

    min_length = 1
    max_length = 253
    pattern = r"^(?:localhost|(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63})$"


class WebAuthnSignature(BaseConstrainedTypedString):
    """A passkey's signature over the authenticator and client data, as base64url."""

    min_length = 40
    max_length = 1_024
    pattern = BASE64URL_PATTERN


class WebAuthnUserHandle(BaseConstrainedTypedString):
    """
    The account handle stored with a passkey (at most 64 bytes, as
    base64url): derived from the user's id, never personal data.
    """

    min_length = 2
    max_length = 86
    pattern = BASE64URL_PATTERN


# Keep abc order for all non example types, if possible.
