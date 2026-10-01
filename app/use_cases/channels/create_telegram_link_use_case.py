import logging

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.channels import ManagerTelegramLinkRepoContract
from app.contracts.registries import LanguageRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.manager_links import ManagerTelegramLinkDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels import (
    CreateTelegramLinkCommand,
    TelegramBotProfile,
    TelegramLinkView,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.channels.constrained_strings import (
    ManagerLinkCode,
    TelegramBotUsername,
    TelegramDeepLink,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.manager_link_codes import (
    generate_link_code,
    hash_link_code,
)

logger: logging.Logger = logging.getLogger(__name__)

LINK_LIFETIME_SECONDS: int = 30 * 60
MAX_MANAGER_NAME_LENGTH: int = 100


class CreateTelegramLinkUseCase(
    UseCaseContract[CreateTelegramLinkCommand, TelegramLinkView]
):
    """
    Owner invites a staff member to receive notifications from the platform
    Telegram bot (concept: handoffs, new bookings and leads, free of charge).

    Returns a one-time code valid for 30 minutes and, when the bot can be
    reached, a t.me deep link that sends "/start <code>" for the staff
    member. The staff member's language defaults to the owner's.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        link_repo: ManagerTelegramLinkRepoContract,
        language_registry: LanguageRegistryContract,
        telegram_client: TelegramBotApiClientContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._link_repo: ManagerTelegramLinkRepoContract = link_repo
        self._language_registry: LanguageRegistryContract = language_registry
        self._telegram_client: TelegramBotApiClientContract = telegram_client
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._bot_username: TelegramBotUsername | None = None

    def run(self, input_data: CreateTelegramLinkCommand) -> TelegramLinkView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        bot_token: PlatformSecret | None = (
            self._app_settings.telegram_platform_bot_token
        )
        if bot_token is None:
            raise ExternalServiceError(
                "Telegram notifications are not configured: "
                "TELEGRAM_PLATFORM_BOT_TOKEN is missing."
            )

        manager_name = input_data.request.name
        if manager_name.strip() == "" or len(manager_name) > MAX_MANAGER_NAME_LENGTH:
            raise ValidationFailedError(
                f"The staff member's name must have 1 to {MAX_MANAGER_NAME_LENGTH} "
                "characters."
            )

        language: LanguageTag = input_data.request.language or business.owner_language
        self._language_registry.get(language)
        now: Microseconds = self._wall_clock.now_unix()
        code: ManagerLinkCode = generate_link_code()
        link = ManagerTelegramLinkDocument(
            business_id=business.id,
            code_hash=hash_link_code(code),
            manager_name=manager_name,
            language=language,
            created_by=input_data.user_id,
            expires_at=self._wall_clock.now_unix_with_delta(
                Seconds(LINK_LIFETIME_SECONDS)
            ),
            created_at=now,
            updated_at=now,
        )
        self._link_repo.save(link)
        bot_username: TelegramBotUsername | None = self._find_bot_username(bot_token)
        return TelegramLinkView(
            business_id=business.id,
            code=code,
            deep_link=(
                None
                if bot_username is None
                else TelegramDeepLink(f"https://t.me/{bot_username}?start={code}")
            ),
            bot_username=bot_username,
            expires_at=link.expires_at,
        )

    def _find_bot_username(
        self, bot_token: PlatformSecret
    ) -> TelegramBotUsername | None:
        if self._bot_username is None:
            try:
                profile: TelegramBotProfile = self._telegram_client.get_me(bot_token)
            except (ExternalServiceError, ValidationFailedError) as error:
                logger.warning("The platform bot username is unknown: %s", error)
                return None

            self._bot_username = profile.username

        return self._bot_username
