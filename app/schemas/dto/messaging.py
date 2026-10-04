"""Platform e-mail parts that are more than text."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.messaging.constrained_strings import (
    EmailAttachmentFileName,
    EmailAttachmentMediaType,
)


class EmailAttachment(ImmutableDTO):
    """A file attached to a platform e-mail (an invoice or receipt PDF)."""

    file_name: EmailAttachmentFileName
    media_type: EmailAttachmentMediaType
    content: bytes
