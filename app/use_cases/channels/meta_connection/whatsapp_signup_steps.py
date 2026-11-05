"""
Choosing what WhatsApp Embedded Signup connected: the business account the
token was granted for and the number in it (the number's two-step PIN is
chosen in `whatsapp_registration_pins.py`).
"""

from app.schemas.constants.meta_connection import MetaConnectionRefusal
from app.schemas.dto.channels.meta_provider import MetaTokenGrants
from app.schemas.dto.channels.provider_profiles import WhatsAppPhoneNumberProfile
from app.schemas.typings.channels.constrained_strings import MetaObjectId
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
)
from app.use_cases.channels.meta_connection.meta_states import meta_refusal
from app.utilities.channels.meta_sign_in import (
    WHATSAPP_MANAGEMENT,
    WHATSAPP_MESSAGING,
)


def choose_business_account(
    grants: MetaTokenGrants, named: WhatsAppBusinessAccountId | None
) -> WhatsAppBusinessAccountId:
    """
    The WhatsApp Business Account the token was granted for: the one Meta's
    window named when it is among them, else the only one. Messaging must
    be granted too.
    """

    if not grants.has(WHATSAPP_MESSAGING) or not grants.has(WHATSAPP_MANAGEMENT):
        raise meta_refusal(
            MetaConnectionRefusal.PERMISSION_MISSING,
            "WhatsApp was connected without the permission to manage it or "
            "send messages. Start again and keep every permission ticked.",
        )

    granted: list[str] = [
        str(target) for target in grants.targets_of(WHATSAPP_MANAGEMENT)
    ]
    if named is not None and str(named) in granted:
        return named

    if len(set(granted)) == 1:
        return WhatsAppBusinessAccountId(granted[0])

    raise meta_refusal(
        MetaConnectionRefusal.NO_WHATSAPP_ACCOUNT,
        "Meta did not say which WhatsApp Business Account to connect. Start "
        "again and choose one account.",
    )


def choose_phone_number(
    numbers: list[WhatsAppPhoneNumberProfile], named: MetaObjectId | None
) -> WhatsAppPhoneNumberProfile:
    """The number Meta's window named, else the account's only number."""

    for number in numbers:
        if named is not None and number.phone_number_id == named:
            return number

    if named is None and len(numbers) == 1:
        return numbers[0]

    raise meta_refusal(
        MetaConnectionRefusal.NO_WHATSAPP_NUMBER,
        "No single WhatsApp number came with this account. Add the number "
        "in Meta's window and start again.",
    )
