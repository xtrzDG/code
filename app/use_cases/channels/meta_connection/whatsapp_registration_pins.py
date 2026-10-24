"""
The two-step PINs the platform registers WhatsApp numbers with (Embedded
Signup). A channel keeps one per number, kept while the channel is off and
when another number is connected meanwhile: Meta refuses to register a
number that has a PIN with another one (133005), and the owner never saw
the PIN the platform chose.
"""

import secrets

from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.domain.channels import ChannelDocument, WhatsAppNumberPin
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    ChannelSecret,
    EncryptedChannelSecret,
)
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppRegistrationPin,
)

PIN_DIGITS: int = 6
# Numbers a business moved between are few; the oldest PINs go past this.
KEPT_PINS: int = 10


def registration_pin(
    existing: ChannelDocument | None,
    number_id: ChannelExternalId,
    secret_cipher: SecretCipherAdapterContract,
) -> WhatsAppRegistrationPin:
    """
    The PIN the business's channel registered this number with before
    (whatever the channel's status now), else a new random one.
    """

    kept: WhatsAppNumberPin | None = None
    if existing is not None:
        kept = next(
            (
                pin
                for pin in existing.whatsapp_registration_pins
                if pin.phone_number_id == number_id
            ),
            None,
        )
    if kept is not None:
        try:
            secret: ChannelSecret = secret_cipher.decrypt(kept.encrypted_pin)
            return WhatsAppRegistrationPin(str(secret))
        except ValidationFailedError, ValueError:
            pass  # Unreadable (an old key): a new PIN is set.

    return WhatsAppRegistrationPin(
        "".join(secrets.choice("0123456789") for _ in range(PIN_DIGITS))
    )


def keeping_pin(
    pins: list[WhatsAppNumberPin],
    number_id: ChannelExternalId,
    encrypted_pin: EncryptedChannelSecret,
) -> list[WhatsAppNumberPin]:
    """The channel's PINs with this number's (new or again) as the newest."""

    others: list[WhatsAppNumberPin] = [
        pin for pin in pins if pin.phone_number_id != number_id
    ]
    newest = WhatsAppNumberPin(phone_number_id=number_id, encrypted_pin=encrypted_pin)
    return [*others, newest][-KEPT_PINS:]
