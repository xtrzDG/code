"""An owner's digest choices: the defaults, the view, and a change of them."""

from app.contracts.repositories.notification_repositories import (
    PushSubscriptionRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.value import DigestChannel, DigestChannelRefusalCode
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.domain.value_settings import DigestPreferencesDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.value.value_views import (
    DigestPreferencesRequest,
    DigestPreferencesView,
    DigestTelegramChatView,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.notifications.staff_providers import is_provider_configured
from app.utilities.value.digest_choices import digest_channels_of
from app.utilities.value.value_keys import digest_preferences_id_of

REFUSAL_MESSAGES: dict[DigestChannelRefusalCode, str] = {
    DigestChannelRefusalCode.TELEGRAM_NOT_AVAILABLE: (
        "Telegram summaries need the platform bot (TELEGRAM_PLATFORM_BOT_TOKEN)."
    ),
    DigestChannelRefusalCode.TELEGRAM_CHAT_NOT_LINKED: (
        "Choose a Telegram chat linked to this business through the platform bot."
    ),
    DigestChannelRefusalCode.WHATSAPP_NOT_AVAILABLE: (
        "WhatsApp summaries need the platform number and the owner report "
        "template (WHATSAPP_OWNER_REPORT_TEMPLATE)."
    ),
    DigestChannelRefusalCode.WHATSAPP_NUMBER_MISSING: (
        "Give the WhatsApp number the summaries go to."
    ),
}


def stored_preferences_or_default(
    business: BusinessDocument,
    user_id: UserId,
    stored: DigestPreferencesDocument | None,
) -> DigestPreferencesDocument:
    """The owner's stored choices, else the defaults (weekly and monthly on)."""

    if stored is not None:
        return stored

    return DigestPreferencesDocument(
        id=digest_preferences_id_of(business.id, user_id),
        business_id=business.id,
        user_id=user_id,
    )


def is_telegram_ready(settings: AppSettings) -> bool:
    return is_provider_configured(settings, ManagerContactChannel.TELEGRAM)


def is_whatsapp_ready(settings: AppSettings) -> bool:
    return (
        settings.whatsapp_notification_phone_number_id is not None
        and settings.whatsapp_owner_report_template_name is not None
    )


def apply_digest_request(
    business: BusinessDocument,
    preferences: DigestPreferencesDocument,
    request: DigestPreferencesRequest,
    settings: AppSettings,
) -> None:
    """
    The owner's new choices on their stored ones (each None of the request
    keeps what is stored).

    Raises:
        ValidationFailedError: Telegram or WhatsApp chosen where it cannot
            reach them (reason codes `DigestChannelRefusalCode`).
    """

    preferences.is_daily_digest_on = request.is_daily_digest_on
    preferences.is_weekly_digest_on = request.is_weekly_digest_on
    preferences.is_monthly_report_on = request.is_monthly_report_on
    if request.telegram_chat is not None:
        preferences.telegram_chat = request.telegram_chat

    if request.whatsapp_number is not None:
        preferences.whatsapp_number = request.whatsapp_number

    if request.channels is not None:
        preferences.channels = list(dict.fromkeys(request.channels))

    refusal: DigestChannelRefusalCode | None = channel_refusal(
        business, preferences, settings
    )
    if refusal is not None:
        message: str = REFUSAL_MESSAGES[refusal]
        raise ValidationFailedError(
            message,
            reasons=[
                ErrorReason(
                    code=ErrorReasonCode(refusal.value),
                    message=ErrorReasonMessage(message),
                )
            ],
        )


def channel_refusal(
    business: BusinessDocument,
    preferences: DigestPreferencesDocument,
    settings: AppSettings,
) -> DigestChannelRefusalCode | None:
    channels: tuple[DigestChannel, ...] = digest_channels_of(preferences)
    if DigestChannel.TELEGRAM in channels:
        if not is_telegram_ready(settings):
            return DigestChannelRefusalCode.TELEGRAM_NOT_AVAILABLE

        if preferences.telegram_chat not in linked_chat_addresses(business):
            return DigestChannelRefusalCode.TELEGRAM_CHAT_NOT_LINKED

    if DigestChannel.WHATSAPP in channels:
        if not is_whatsapp_ready(settings):
            return DigestChannelRefusalCode.WHATSAPP_NOT_AVAILABLE

        if preferences.whatsapp_number is None:
            return DigestChannelRefusalCode.WHATSAPP_NUMBER_MISSING

    return None


def linked_chat_addresses(business: BusinessDocument) -> list[object]:
    return [chat.address for chat in telegram_chats(business)]


def telegram_chats(business: BusinessDocument) -> list[DigestTelegramChatView]:
    """The business's chats linked to the platform bot (staff contacts)."""

    return [
        DigestTelegramChatView(
            address=contact.address,
            name=contact.name,
            username=contact.telegram_username,
        )
        for contact in business.manager_contacts
        if contact.channel is ManagerContactChannel.TELEGRAM
    ]


def build_digest_preferences_view(
    business: BusinessDocument,
    preferences: DigestPreferencesDocument,
    user_repo: UserRepoContract,
    push_subscription_repo: PushSubscriptionRepoContract,
    app_settings: AppSettings,
) -> DigestPreferencesView:
    user: UserDocument | None = user_repo.get(preferences.user_id)
    return DigestPreferencesView(
        business_id=business.id,
        is_daily_digest_on=preferences.is_daily_digest_on,
        is_weekly_digest_on=preferences.is_weekly_digest_on,
        is_monthly_report_on=preferences.is_monthly_report_on,
        channels=list(digest_channels_of(preferences)),
        email=None if user is None else user.email,
        is_email_ready=is_provider_configured(
            app_settings, ManagerContactChannel.EMAIL
        ),
        device_count=ListItemCount(
            len(push_subscription_repo.list_by_user(business.id, preferences.user_id))
        ),
        telegram_chat=preferences.telegram_chat,
        telegram_chats=telegram_chats(business),
        is_telegram_ready=is_telegram_ready(app_settings),
        whatsapp_number=preferences.whatsapp_number,
        suggested_whatsapp_number=None if user is None else user.phone_number,
        is_whatsapp_ready=is_whatsapp_ready(app_settings),
    )
