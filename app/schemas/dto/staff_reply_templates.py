"""
The WhatsApp message template for staff replies outside the 24-hour window
(cabinet: Channels page and the conversation card).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.constrained_integers import (
    StaffTemplateReplyMaxLength,
)
from app.schemas.typings.users.prefixed_id import UserId

# Templates one WhatsApp number keeps for staff replies (one per language).
MAX_STAFF_TEMPLATES: int = 30


class WhatsAppStaffTemplateView(ImmutableDTO):
    """The approved template staff replies use once the window has closed."""

    name: WhatsAppTemplateName
    language_code: WhatsAppTemplateLanguageCode


class StaffReplyTemplateView(ImmutableDTO):
    """
    The template the card offers when the WhatsApp window has closed; the
    staff text becomes its single body parameter, one line of at most
    `max_text_length` characters (line breaks are sent as spaces).
    """

    name: WhatsAppTemplateName
    language_code: WhatsAppTemplateLanguageCode
    max_text_length: StaffTemplateReplyMaxLength


class WhatsAppStaffTemplateRequest(ImmutableDTO):
    """
    HTTP body that sets the template for staff replies (a name and its
    approved language, e.g. "staff_reply" in "en_US"); both left out or null
    remove it.
    """

    name: WhatsAppTemplateName | None = None
    language_code: WhatsAppTemplateLanguageCode | None = None


class SetWhatsAppStaffTemplateCommand(ImmutableDTO):
    """Owner sets (or removes) the WhatsApp template for staff replies."""

    user_id: UserId
    business_id: BusinessId
    request: WhatsAppStaffTemplateRequest
    client_ip_address: ClientIpAddress | None = None


class WhatsAppStaffTemplateEntry(ImmutableDTO):
    """One approved template of the per-language list: its name and language."""

    name: WhatsAppTemplateName
    language_code: WhatsAppTemplateLanguageCode


class WhatsAppStaffTemplatesRequest(ImmutableDTO):
    """
    HTTP body that replaces the templates for staff replies, one per
    template language (e.g. "staff_reply" in "ka", "staff_reply_he" in
    "he"); an empty list removes them all. Staff replies take the template
    of the conversation's language, then the business's default language.
    """

    templates: list[WhatsAppStaffTemplateEntry] = Field(
        default_factory=list[WhatsAppStaffTemplateEntry],
        max_length=MAX_STAFF_TEMPLATES,
    )


class SetWhatsAppStaffTemplatesCommand(ImmutableDTO):
    """Owner replaces the per-language WhatsApp templates for staff replies."""

    user_id: UserId
    business_id: BusinessId
    request: WhatsAppStaffTemplatesRequest
    client_ip_address: ClientIpAddress | None = None
