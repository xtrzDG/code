"""
Rows of every kind the daily purge deletes (tests/storage/
test_purge_stale_rows.py), each built at the moment it was written or ends.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackSkipReason,
    TextBackStatus,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventKind, OutboundMessageKind
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.meta_connection import MetaConnectionPurpose
from app.schemas.constants.passkeys import PasskeyCeremonyPurpose
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.channel_receipts import ChannelMessageReceiptDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.meta_connections import MetaConnectionStateDocument
from app.schemas.domain.mfa import MfaChallengeDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.domain.passkeys import PasskeyChallengeDocument
from app.schemas.domain.users import OtpChallengeDocument, UserSessionDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import (
    EncryptedChannelSecret,
    ProviderMessageId,
)
from app.schemas.typings.conversations.strings import MessageText, ProviderCallId
from app.schemas.typings.deliveries.constrained_strings import (
    OutboundIdempotencyKey,
    OutboundRecipientKey,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaConnectionStateHash,
)
from app.schemas.typings.passkeys.constrained_strings import WebAuthnChallenge
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessTokenHash, OtpCodeHash
from app.utilities.calls.call_follow_up_keys import missed_call_id_of
from app.utilities.deliveries.delivery_keys import (
    derive_inbound_event_id,
    derive_outbound_message_id,
)


def session(expires_at: int) -> UserSessionDocument:
    return UserSessionDocument(
        user_id=UserId(),
        token_hash=AccessTokenHash(f"{expires_at:064d}"),
        expires_at=Microseconds(expires_at),
    )


def challenge(created_at: int) -> OtpChallengeDocument:
    return OtpChallengeDocument(
        login_method=LoginMethod.PHONE,
        phone_number=E164PhoneNumber("+995555123456"),
        delivery_channel=OtpDeliveryChannel.SMS,
        locale=LanguageTag("ka"),
        code_hash=OtpCodeHash("hash"),
        expires_at=Microseconds(created_at + 600_000_000),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


def second_step(created_at: int) -> MfaChallengeDocument:
    return MfaChallengeDocument(
        user_id=UserId(),
        expires_at=Microseconds(created_at + 300_000_000),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


def ceremony(created_at: int) -> PasskeyChallengeDocument:
    return PasskeyChallengeDocument(
        user_id=UserId(),
        purpose=PasskeyCeremonyPurpose.SIGN_IN,
        challenge=WebAuthnChallenge("test-challenge-0000000000"),
        expires_at=Microseconds(created_at + 300_000_000),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


def facebook_sign_in(expires_at: int) -> MetaConnectionStateDocument:
    """An abandoned page-picker sign-in that kept the owner's token."""

    return MetaConnectionStateDocument(
        business_id=BusinessId(),
        user_id=UserId(),
        purpose=MetaConnectionPurpose.PAGES,
        state_hash=MetaConnectionStateHash(f"{expires_at:064x}"),
        expires_at=Microseconds(expires_at),
        is_consumed=True,
        encrypted_user_token=EncryptedChannelSecret("sealed-test-token-0000"),
        created_at=Microseconds(expires_at - 900_000_000),
        updated_at=Microseconds(expires_at - 900_000_000),
    )


def receipt(created_at: int, message_id: str) -> ChannelMessageReceiptDocument:
    return ChannelMessageReceiptDocument(
        business_id=BusinessId(),
        channel=ChannelKind.WHATSAPP,
        provider_message_id=ProviderMessageId(message_id),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


def inbound_event(created_at: int) -> InboundEventDocument:
    message_id = ProviderMessageId(f"wamid.{created_at}")
    return InboundEventDocument(
        id=derive_inbound_event_id(None, ChannelKind.TELEGRAM, message_id),
        kind=InboundEventKind.PLATFORM_BOT_UPDATE,
        channel=ChannelKind.TELEGRAM,
        provider_message_id=message_id,
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


def outbound_message(created_at: int) -> OutboundMessageDocument:
    business_id = BusinessId()
    key = OutboundIdempotencyKey(f"staff:{created_at}")
    return OutboundMessageDocument(
        id=derive_outbound_message_id(business_id, key),
        business_id=business_id,
        kind=OutboundMessageKind.STAFF_NOTIFICATION,
        idempotency_key=key,
        recipient_key=OutboundRecipientKey("staff:email:levan@example.ge"),
        text=MessageText("A new booking."),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


def missed_call(created_at: int) -> MissedCallDocument:
    business_id = BusinessId()
    call_id = ProviderCallId(f"pbx-{created_at}")
    return MissedCallDocument(
        id=missed_call_id_of(business_id, MissedCallSource.PBX, call_id),
        business_id=business_id,
        source=MissedCallSource.PBX,
        provider_call_id=call_id,
        reason=MissedCallReason.BUSY,
        caller_phone_number=E164PhoneNumber("+995555123456"),
        called_at=Microseconds(created_at),
        language=LanguageTag("ka"),
        status=TextBackStatus.SKIPPED,
        skip_reason=TextBackSkipReason.TURNED_OFF,
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )
