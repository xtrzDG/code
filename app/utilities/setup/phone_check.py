"""
"Try it from your phone": how the guide recognizes the owner's own message.

A message counts as the owner's when it comes from one of their own
senders on a messaging channel (the WhatsApp number of an owner's sign-in
phone or of a staff contact, a Telegram chat linked to the platform bot),
or when a real conversation starts while the guide listens: the owner
opened the QR code in the cabinet within the last half hour (the web chat
knows nothing about who writes).
"""

from collections.abc import Iterable

from typed_time_provider import Microseconds

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import SetupStateDocument
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber

PHONE_CHECK_WINDOW_MICROSECONDS: int = 30 * 60 * 1_000_000
PHONE_CONTACT_CHANNELS: frozenset[ManagerContactChannel] = frozenset(
    {ManagerContactChannel.WHATSAPP, ManagerContactChannel.SMS}
)


def owner_sender_ids(
    business: BusinessDocument,
    owner_phones: Iterable[E164PhoneNumber],
) -> frozenset[ChannelUserId]:
    """
    The channel user ids the owner's team writes from: WhatsApp ids (the
    digits of a phone number) and Telegram chat ids.
    """

    phones: list[str] = [str(phone) for phone in owner_phones]
    telegram_chats: list[str] = []
    for contact in business.manager_contacts:
        if contact.channel in PHONE_CONTACT_CHANNELS:
            phones.append(str(contact.address))
        elif contact.channel is ManagerContactChannel.TELEGRAM:
            telegram_chats.append(str(contact.address).strip())

    whatsapp_ids: list[str] = [whatsapp_id(phone) for phone in phones]
    return frozenset(
        ChannelUserId(sender)
        for sender in (*whatsapp_ids, *telegram_chats)
        if sender != ""
    )


def whatsapp_id(phone: str) -> str:
    """WhatsApp names a sender by the digits of their number ("+995 5…" → "9955…")."""

    return "".join(character for character in phone if character.isdigit())


def listening_window(
    state: SetupStateDocument | None,
) -> tuple[Microseconds, Microseconds] | None:
    """When the guide counts any new conversation as the owner's test."""

    if state is None or state.phone_check_started_at is None:
        return None

    started: Microseconds = state.phone_check_started_at
    return started, Microseconds(int(started) + PHONE_CHECK_WINDOW_MICROSECONDS)


def is_listening(state: SetupStateDocument | None, now: Microseconds) -> bool:
    """The window is open and the owner's message has not arrived yet."""

    window = listening_window(state)
    return (
        window is not None
        and state is not None
        and state.phone_tested_at is None
        and int(window[0]) <= int(now) < int(window[1])
    )
