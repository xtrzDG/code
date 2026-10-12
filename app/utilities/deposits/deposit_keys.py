"""
Identities of deposits: the settings of a business, the reference a
deposit is paid under, and the outbox message of each customer notice.
"""

import secrets
from uuid import UUID, uuid5

from app.schemas.constants.deposits import DepositNoticeKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.constrained_strings import OutboundIdempotencyKey
from app.schemas.typings.deposits.constrained_strings import DepositReference
from app.schemas.typings.deposits.prefixed_id import DepositRequestId, DepositSettingsId

# A fixed namespace of derived ids (never change it: stored ids depend on it).
DEPOSIT_SETTINGS_NAMESPACE: UUID = UUID("8f2d6c41-3b7e-4a95-9e0c-5d1a7b3f6e28")
# Letters and digits no one confuses when reading a code aloud (no 0/O, 1/I).
REFERENCE_LETTERS: str = "ACDEFHJKLMNPQRTUVWXY"
REFERENCE_DIGITS: str = "3479"
REFERENCE_ALPHABET: str = REFERENCE_LETTERS + REFERENCE_DIGITS
REFERENCE_LENGTH: int = 8


def deposit_settings_id_of(business_id: BusinessId) -> DepositSettingsId:
    """One settings document per business."""

    return DepositSettingsId(uuid5(DEPOSIT_SETTINGS_NAMESPACE, str(business_id)))


def new_deposit_reference() -> DepositReference:
    """
    A fresh payment reference (about 8.4e10 codes): letters and at least
    one digit, so it never reads as a word or a number and a transcript
    can tell it apart (the evaluations' cassette keys do).
    """

    while True:
        code: str = "".join(
            secrets.choice(REFERENCE_ALPHABET) for _ in range(REFERENCE_LENGTH)
        )
        if is_mixed_reference(code):
            return DepositReference(code)


def is_mixed_reference(code: str) -> bool:
    return any(char in REFERENCE_DIGITS for char in code) and any(
        char in REFERENCE_LETTERS for char in code
    )


def deposit_notice_idempotency_key(
    request_id: DepositRequestId, notice: DepositNoticeKind
) -> OutboundIdempotencyKey:
    """One outbox message per notice of a deposit (its reminder, its release)."""

    return OutboundIdempotencyKey(f"deposit:{request_id}:{notice.value}")
