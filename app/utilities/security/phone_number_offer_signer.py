"""
Signed offers of numbers (`PhoneNumberOfferToken`).

A search offers numbers of one kind; taking one sends back its token, so
the number's kind (which fixes its price and whether the regulator wants
papers) and the business are the ones the search vouched for, and the
offer lapses after a while. Nothing is stored: the token is the expiry in
whole seconds and a truncated HMAC-SHA256 over the business, the number,
its kind and the expiry. The key derives from ENCRYPTION_KEY with its own
label; after a rotation a token signed with a previous key still holds
until it lapses.
"""

import base64
import hashlib
import hmac
import logging
import secrets
from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.phone_numbers import PhoneNumberOfferSignerContract
from app.schemas.dto.phone_numbers.provisioning import PhoneNumberOfferClaims
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.telephony.constrained_strings import PhoneNumberOfferToken

logger: logging.Logger = logging.getLogger(__name__)

KEY_LABEL: bytes = b"assistant-workshop/phone-number-offers/v1"
SIGNATURE_LENGTH: int = 16
MICROSECONDS_PER_SECOND: int = 1_000_000


def derive_offer_key(encryption_key: PlatformSecret | None) -> bytes:
    """
    The signing key: from ENCRYPTION_KEY, or a key of this process alone
    when none is set (development: offers lapse with a restart).
    """

    if encryption_key is None or str(encryption_key).strip() == "":
        logger.warning(
            "ENCRYPTION_KEY is not set; phone number offers are signed with a "
            "temporary key of this process."
        )
        return secrets.token_bytes(32)

    return hmac.new(
        str(encryption_key).strip().encode("utf-8"), KEY_LABEL, hashlib.sha256
    ).digest()


class PhoneNumberOfferSigner(PhoneNumberOfferSignerContract):
    """HMAC-signed offers (see the module docstring)."""

    def __init__(
        self,
        encryption_key: PlatformSecret | None,
        previous_keys: Sequence[PlatformSecret] = (),
    ) -> None:
        self._key: bytes = derive_offer_key(encryption_key)
        self._verification_keys: list[bytes] = [
            self._key,
            *(derive_offer_key(previous_key) for previous_key in previous_keys),
        ]

    def sign(self, claims: PhoneNumberOfferClaims) -> PhoneNumberOfferToken:
        seconds: int = int(claims.expires_at) // MICROSECONDS_PER_SECOND
        signature: bytes = sign_claims(self._key, claims, seconds)
        return PhoneNumberOfferToken(
            f"{seconds}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"
        )

    def read_expiry(self, token: PhoneNumberOfferToken) -> Microseconds:
        seconds, _, _ = str(token).partition(".")
        return Microseconds(int(seconds) * MICROSECONDS_PER_SECOND)

    def is_genuine(
        self, claims: PhoneNumberOfferClaims, token: PhoneNumberOfferToken
    ) -> bool:
        seconds: int = int(claims.expires_at) // MICROSECONDS_PER_SECOND
        if claims.expires_at != Microseconds(seconds * MICROSECONDS_PER_SECOND):
            return False

        return any(
            hmac.compare_digest(
                str(token),
                f"{seconds}."
                + base64.urlsafe_b64encode(sign_claims(key, claims, seconds))
                .rstrip(b"=")
                .decode(),
            )
            for key in self._verification_keys
        )


def sign_claims(key: bytes, claims: PhoneNumberOfferClaims, seconds: int) -> bytes:
    message: bytes = "|".join(
        (
            "offer-v1",
            str(claims.business_id),
            str(claims.phone_number),
            claims.number_type.value,
            str(seconds),
        )
    ).encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).digest()[:SIGNATURE_LENGTH]
