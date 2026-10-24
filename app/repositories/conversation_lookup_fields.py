"""Lookup fields of contacts, conversations, messages, model turns and calls."""

from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

# Contacts.
CHANNEL_USER_IDS_FIELD: DocumentFieldPath = DocumentFieldPath(
    "channel_identities[].channel_user_id"
)
PHONE_NUMBER_FIELD: DocumentFieldPath = DocumentFieldPath("phone_number")
VERIFIED_PHONE_NUMBER_FIELD: DocumentFieldPath = DocumentFieldPath(
    "verified_phone_number"
)

# Conversations.
CONTACT_ID_FIELD: DocumentFieldPath = DocumentFieldPath("contact_id")
CHANNEL_USER_ID_FIELD: DocumentFieldPath = DocumentFieldPath("channel_user_id")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
LAST_MESSAGE_AT_FIELD: DocumentFieldPath = DocumentFieldPath("last_message_at")

# Messages (and model turns, by conversation).
CONVERSATION_ID_FIELD: DocumentFieldPath = DocumentFieldPath("conversation_id")
DIRECTION_FIELD: DocumentFieldPath = DocumentFieldPath("direction")
AUTHOR_FIELD: DocumentFieldPath = DocumentFieldPath("author")
CREATED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("created_at")

# Model turns.
SEQUENCE_NUMBER_FIELD: DocumentFieldPath = DocumentFieldPath("sequence_number")

# Calls.
PROVIDER_CALL_ID_FIELD: DocumentFieldPath = DocumentFieldPath("provider_call_id")
