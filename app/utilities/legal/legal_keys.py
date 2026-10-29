"""
Derived ids of the sub-processor notices: one announcement per change, one
notice per business and change.
"""

from uuid import UUID, uuid5

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.legal.constrained_strings import SubprocessorChangeKey
from app.schemas.typings.legal.prefixed_id import (
    SubprocessorAnnouncementId,
    SubprocessorNoticeId,
)

# Fixed namespaces (never change them: the once-only notices depend on them).
SUBPROCESSOR_ANNOUNCEMENT_NAMESPACE: UUID = UUID("7c2e9a41-3f5b-4d86-a1e0-5b9d2c7f4a13")
SUBPROCESSOR_NOTICE_NAMESPACE: UUID = UUID("e4b17d29-8a6c-4f3e-9d52-1c8a6f3b2e70")


def derive_subprocessor_announcement_id(
    change_key: SubprocessorChangeKey,
) -> SubprocessorAnnouncementId:
    """The same change: the same announcement."""

    return SubprocessorAnnouncementId(
        uuid5(SUBPROCESSOR_ANNOUNCEMENT_NAMESPACE, str(change_key))
    )


def derive_subprocessor_notice_id(
    business_id: BusinessId, change_key: SubprocessorChangeKey
) -> SubprocessorNoticeId:
    """The same change for the same business: the same notice (sent once)."""

    return SubprocessorNoticeId(
        uuid5(SUBPROCESSOR_NOTICE_NAMESPACE, f"{business_id}|{change_key}")
    )
