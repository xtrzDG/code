"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class PasskeyCeremonyTimeoutMilliseconds(BaseConstrainedTypedInt):
    """
    How long the browser waits for the person to use their authenticator
    in one passkey ceremony (a hint the browser may adjust).
    """

    ge = 30_000
    le = 600_000


class PasskeyCount(BaseConstrainedTypedInt):
    """How many passkeys a person has added to their account."""

    ge = 0
    le = 100


class WebAuthnCoseAlgorithm(BaseConstrainedTypedInt):
    """
    A COSE signature algorithm a passkey may use (RFC 9053): -7 ES256,
    -8 EdDSA, -257 RS256.
    """

    ge = -65_536
    le = 65_535


class WebAuthnSignCount(BaseConstrainedTypedInt):
    """
    The signature counter an authenticator reports with each use of a
    passkey (32 bits). A counter that does not grow between two uses
    betrays a copied authenticator; synced passkeys always report 0.
    """

    ge = 0
    le = 4_294_967_295


# Keep abc order for all non example types, if possible.
