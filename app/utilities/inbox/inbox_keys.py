"""
Derived ids of the team inbox: one saved-reply library and one settings
document per business.
"""

from uuid import UUID, uuid5

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.inbox.prefixed_id import InboxSettingsId, QuickReplyLibraryId

# Fixed namespaces of the derived ids (never change them: stored ids depend
# on them).
QUICK_REPLY_LIBRARY_NAMESPACE: UUID = UUID("5f0c2b7e-93a1-4d6e-8b24-61e9d3a7c815")
INBOX_SETTINGS_NAMESPACE: UUID = UUID("a87d4e12-3c6b-4f05-9e1a-2b8c7d5f6e93")


def derive_quick_reply_library_id(business_id: BusinessId) -> QuickReplyLibraryId:
    return QuickReplyLibraryId(uuid5(QUICK_REPLY_LIBRARY_NAMESPACE, str(business_id)))


def derive_inbox_settings_id(business_id: BusinessId) -> InboxSettingsId:
    return InboxSettingsId(uuid5(INBOX_SETTINGS_NAMESPACE, str(business_id)))
