"""Platform e-mail parts that are more than text, and the platform's SMS sender."""

from typing import Self

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field, model_validator

from app.schemas.typings.messaging.constrained_strings import (
    EmailAttachmentFileName,
    EmailAttachmentMediaType,
    SmsSenderId,
    TwilioAccountSid,
    TwilioMessagingServiceSid,
)
from app.schemas.typings.platform.strings import PlatformSecret


class EmailAttachment(ImmutableDTO):
    """A file attached to a platform e-mail (an invoice or receipt PDF)."""

    file_name: EmailAttachmentFileName
    media_type: EmailAttachmentMediaType
    content: bytes


class TwilioSmsSender(ImmutableDTO):
    """
    What the platform sends SMS with: the Twilio account and its sender, a
    "From" number or a Messaging Service (which wins when both are set).
    The account alone rents phone numbers but sends no SMS, so there is no
    sender without one of them (`platform_sms_sender`).
    """

    account_sid: TwilioAccountSid
    auth_token: PlatformSecret = Field(repr=False)
    sender: SmsSenderId | None = None
    messaging_service_sid: TwilioMessagingServiceSid | None = None

    @model_validator(mode="after")
    def require_a_sender(self) -> Self:
        if self.sender is None and self.messaging_service_sid is None:
            raise ValueError(
                "An SMS sender is TWILIO_FROM_NUMBER or "
                "TWILIO_MESSAGING_SERVICE_SID; neither is set."
            )

        return self
