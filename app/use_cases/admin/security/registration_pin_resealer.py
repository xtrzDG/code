"""
Seal the two-step PINs of a business's WhatsApp numbers (Embedded Signup,
1212) again with the current key, each written back only if it did not
change meanwhile (a number registered again is sealed with the current key
already).
"""

from collections.abc import Callable

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.schemas.domain.channels import ChannelDocument, WhatsAppNumberPin
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret

type Reseal = Callable[[EncryptedChannelSecret], EncryptedChannelSecret | None]


def reseal_registration_pins(
    channel_repo: ChannelRepoContract,
    business_id: BusinessId,
    reseal: Reseal,
) -> None:
    """Every kept registration PIN of the business under the current key."""

    for channel in channel_repo.list_by_business(business_id):
        for kept in channel.whatsapp_registration_pins:
            sealed: EncryptedChannelSecret | None = reseal(kept.encrypted_pin)
            if sealed is None or sealed == kept.encrypted_pin:
                continue

            channel_repo.modify(business_id, channel.id, replacing_pin(kept, sealed))


def replacing_pin(
    previous: WhatsAppNumberPin, sealed: EncryptedChannelSecret
) -> Callable[[ChannelDocument], ChannelDocument | None]:
    def replace(stored: ChannelDocument) -> ChannelDocument | None:
        if previous not in stored.whatsapp_registration_pins:
            return None  # Registered again meanwhile: the current key.

        pins: list[WhatsAppNumberPin] = [
            pin.model_copy(update={"encrypted_pin": sealed}) if pin == previous else pin
            for pin in stored.whatsapp_registration_pins
        ]
        return stored.model_copy(update={"whatsapp_registration_pins": pins})

    return replace
