"""
The WhatsApp templates that carry staff replies after the 24-hour window,
one per language, and which one a conversation gets.

A staff reply goes out in the template of the conversation's language
(the exact template language first, "pt_BR" for "pt-BR", then any template
of the same base language), else in the one of the business's default
language, else, so that a reply that could go out before per-language
templates existed still can, in the first template the owner set.
"""

from collections.abc import Sequence

from app.schemas.domain.channels import ChannelDocument, WhatsAppStaffTemplate
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.language_codes import to_whatsapp_template_language

TEMPLATE_REGION_SEPARATOR: str = "_"


def choose_staff_template(
    templates: Sequence[WhatsAppStaffTemplate],
    conversation_language: LanguageTag | None,
    default_language: LanguageTag,
) -> WhatsAppStaffTemplate | None:
    """The template of a conversation's staff reply; None without templates."""

    for language in (conversation_language, default_language):
        if language is None:
            continue

        found: WhatsAppStaffTemplate | None = find_language_template(
            templates, language
        )
        if found is not None:
            return found

    return templates[0] if templates else None


def find_language_template(
    templates: Sequence[WhatsAppStaffTemplate],
    language: LanguageTag,
) -> WhatsAppStaffTemplate | None:
    """The template approved in a language: exactly, else in its base language."""

    code: WhatsAppTemplateLanguageCode = to_whatsapp_template_language(language)
    for template in templates:
        if str(template.language_code) == str(code):
            return template

    base: str = template_base_language(code)
    for template in templates:
        if template_base_language(template.language_code) == base:
            return template

    return None


def template_base_language(code: WhatsAppTemplateLanguageCode) -> str:
    """ "pt_BR" -> "pt", "ka" -> "ka" (a technical value for comparison)."""

    return str(code).split(TEMPLATE_REGION_SEPARATOR, 1)[0]


def channel_staff_templates(channel: ChannelDocument) -> list[WhatsAppStaffTemplate]:
    """
    A channel's templates: its list, else the single template of a channel
    written with only that one (the previous release's shape).
    """

    if channel.whatsapp_staff_templates:
        return list(channel.whatsapp_staff_templates)

    single: WhatsAppStaffTemplate | None = channel.whatsapp_staff_template
    return [] if single is None else [single]


def fallback_staff_template(
    templates: Sequence[WhatsAppStaffTemplate],
    default_language: LanguageTag,
) -> WhatsAppStaffTemplate | None:
    """
    The one template the previous release reads (`whatsapp_staff_template`):
    the default language's, else the first.
    """

    found: WhatsAppStaffTemplate | None = find_language_template(
        templates, default_language
    )
    if found is not None:
        return found

    return templates[0] if templates else None
