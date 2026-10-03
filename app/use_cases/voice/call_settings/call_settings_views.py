"""The Settings → Calls view of a business's call settings."""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.calls.call_settings import (
    CallSettingsView,
    TextBackTemplatePreview,
    TextBackView,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.calls.call_follow_up_keys import call_settings_id_of
from app.utilities.calls.text_back_texts import TEXT_BACK_MESSAGE_TEXT, template_body
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.scheduling.localized_formatting import choose_template_language


def stored_or_default(
    business: BusinessDocument,
    settings: CallSettingsDocument | None,
) -> CallSettingsDocument:
    """The business's settings, or the defaults (summaries on, text-backs off)."""

    if settings is not None:
        return settings

    return CallSettingsDocument(
        id=call_settings_id_of(business.id),
        business_id=business.id,
        created_at=business.created_at,
        updated_at=business.created_at,
    )


def build_call_settings_view(
    business: BusinessDocument,
    settings: CallSettingsDocument,
    channel_repo: ChannelRepoContract,
    text_resolver: LocalizedTextResolverContract,
    is_sms_available: bool,
) -> CallSettingsView:
    whatsapp: ChannelDocument | None = find_business_channel(
        channel_repo, business.id, ChannelKind.WHATSAPP
    )
    return CallSettingsView(
        is_summary_enabled=settings.is_summary_enabled,
        is_text_back_enabled=settings.is_text_back_enabled,
        text_back_template_name=settings.text_back_template_name,
        is_sms_fallback_enabled=settings.is_sms_fallback_enabled,
        is_whatsapp_connected=whatsapp is not None and is_channel_active(whatsapp),
        is_sms_available=is_sms_available,
        template_previews=[
            build_template_preview(business, language, text_resolver)
            for language in preview_languages(business)
        ],
    )


def preview_languages(business: BusinessDocument) -> list[LanguageTag]:
    """
    The languages the text-back exists in for the business's languages
    (its default first); a language without one is shown in English.
    """

    languages: list[LanguageTag] = []
    for language in [business.default_language, *business.languages]:
        text_language: LanguageTag = choose_template_language(
            TEXT_BACK_MESSAGE_TEXT, language
        )
        if text_language not in languages:
            languages.append(text_language)

    return languages


def build_template_preview(
    business: BusinessDocument,
    language: LanguageTag,
    text_resolver: LocalizedTextResolverContract,
) -> TextBackTemplatePreview:
    text: str = str(text_resolver.resolve(TEXT_BACK_MESSAGE_TEXT, language))
    return TextBackTemplatePreview(
        language=language,
        template_body=MessageText(template_body(text)),
        example=MessageText(text.format(business=business.name)),
    )


def build_text_back_view(missed: MissedCallDocument) -> TextBackView:
    return TextBackView(
        id=missed.id,
        reason=missed.reason,
        source=missed.source,
        caller_phone_number=missed.caller_phone_number,
        called_at=missed.called_at,
        language=missed.language,
        status=missed.status,
        skip_reason=missed.skip_reason,
        channel=missed.channel,
        conversation_id=missed.conversation_id,
        sent_at=missed.sent_at,
        last_error=missed.last_error,
    )
