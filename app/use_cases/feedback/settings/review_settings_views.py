"""The Settings → Reviews view of a business's review settings."""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.feedback import ReviewSettingsDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.feedback.review_settings import (
    FeedbackTemplatePreview,
    ReviewSettingsView,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.feedback.feedback_keys import review_settings_id_of
from app.utilities.feedback.feedback_request_texts import (
    BUSINESS_FIELD,
    FEEDBACK_REQUEST_TEXT,
    TEMPLATE_PARAMETER,
)
from app.utilities.scheduling.localized_formatting import choose_template_language


def stored_or_default(
    business: BusinessDocument,
    settings: ReviewSettingsDocument | None,
) -> ReviewSettingsDocument:
    """The business's settings, or the defaults (feedback off, two hours)."""

    if settings is not None:
        return settings

    return ReviewSettingsDocument(
        id=review_settings_id_of(business.id),
        business_id=business.id,
        created_at=business.created_at,
        updated_at=business.created_at,
    )


def build_review_settings_view(
    business: BusinessDocument,
    settings: ReviewSettingsDocument,
    profile: BusinessProfileDocument | None,
    channel_repo: ChannelRepoContract,
    text_resolver: LocalizedTextResolverContract,
    app_base_url: PublicBaseUrl | None,
) -> ReviewSettingsView:
    whatsapp: ChannelDocument | None = find_business_channel(
        channel_repo, business.id, ChannelKind.WHATSAPP
    )
    return ReviewSettingsView(
        is_feedback_enabled=settings.is_feedback_enabled,
        delay_minutes=settings.delay_minutes,
        feedback_template_name=settings.feedback_template_name,
        google_review_url=None if profile is None else profile.google_review_url,
        is_whatsapp_connected=whatsapp is not None and is_channel_active(whatsapp),
        is_link_tracked=app_base_url is not None,
        template_previews=[
            build_template_preview(business, language, text_resolver)
            for language in preview_languages(business)
        ],
    )


def preview_languages(business: BusinessDocument) -> list[LanguageTag]:
    """
    The languages the request exists in for the business's languages (its
    default first); a language without one is shown in English.
    """

    languages: list[LanguageTag] = []
    for language in [business.default_language, *business.languages]:
        text_language: LanguageTag = choose_template_language(
            FEEDBACK_REQUEST_TEXT, language
        )
        if text_language not in languages:
            languages.append(text_language)

    return languages


def build_template_preview(
    business: BusinessDocument,
    language: LanguageTag,
    text_resolver: LocalizedTextResolverContract,
) -> FeedbackTemplatePreview:
    text: str = str(text_resolver.resolve(FEEDBACK_REQUEST_TEXT, language))
    return FeedbackTemplatePreview(
        language=language,
        template_body=MessageText(text.replace(BUSINESS_FIELD, TEMPLATE_PARAMETER)),
        example=MessageText(text.format(business=business.name)),
    )
