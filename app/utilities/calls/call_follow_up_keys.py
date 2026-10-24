"""
Identities of what follows a phone call: the settings of a business, a
missed call (one per business, source and provider call id), and the
rate-limit counters of text-backs.
"""

import hashlib
from uuid import UUID, uuid5

from app.schemas.constants.calls import MissedCallSource
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calls.prefixed_id import CallSettingsId, MissedCallId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.constrained_strings import RateLimitKey

# Fixed namespaces of derived ids (never change them: stored ids depend on
# them).
CALL_SETTINGS_NAMESPACE: UUID = UUID("5e0c6d2b-8a41-4f7e-b3d9-1c2a7f4e9b60")
MISSED_CALL_NAMESPACE: UUID = UUID("a8f3b1c4-2d6e-4b07-9e15-7c3d0f8a6b21")
RATE_KEY_DIGEST_LENGTH: int = 32


def call_settings_id_of(business_id: BusinessId) -> CallSettingsId:
    """One settings document per business."""

    return CallSettingsId(uuid5(CALL_SETTINGS_NAMESPACE, str(business_id)))


def missed_call_id_of(
    business_id: BusinessId,
    source: MissedCallSource,
    provider_call_id: ProviderCallId,
) -> MissedCallId:
    """The same call reported again is the same missed call."""

    name: str = f"{business_id}|{source.value}|{provider_call_id}"
    return MissedCallId(uuid5(MISSED_CALL_NAMESPACE, name))


def caller_text_back_key(
    business_id: BusinessId,
    caller_phone_number: E164PhoneNumber,
) -> RateLimitKey:
    """The counter of text-backs to one caller (a digest: no number in it)."""

    digest: str = hashlib.sha256(
        f"{business_id}|{caller_phone_number}".encode()
    ).hexdigest()[:RATE_KEY_DIGEST_LENGTH]
    return RateLimitKey(f"text_back:caller:{digest}")


def business_text_back_key(business_id: BusinessId) -> RateLimitKey:
    """The counter of all text-backs of one business."""

    return RateLimitKey(f"text_back:business:{business_id}")
