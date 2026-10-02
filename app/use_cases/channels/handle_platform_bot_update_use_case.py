import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.channels import ManagerTelegramLinkRepoContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channel_events import PlatformBotCommandResult
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.manager_links import ManagerTelegramLinkDocument
from app.schemas.dto.channels import (
    PlatformBotWebhookOutcome,
    PlatformBotWebhookRequest,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ExternalServiceError,
    NotFoundError,
    UnsupportedLanguageError,
)
from app.schemas.typings.channels.constrained_strings import ManagerLinkCode
from app.schemas.typings.channels.strings import OutboundMessagePart
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.handoffs.strings import ManagerContactAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.channel_texts import (
    PLATFORM_BOT_CONTACT_LIMIT_TEXT,
    PLATFORM_BOT_INSTRUCTIONS_TEXT,
    PLATFORM_BOT_LINKED_TEXT,
    PLATFORM_BOT_REJECTED_CODE_TEXT,
)
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_flag,
    read_identifier,
    read_object,
    read_text,
)
from app.utilities.channels.manager_link_codes import hash_link_code, read_link_code
from app.utilities.channels.webhook_signatures import (
    derive_telegram_webhook_secret,
    is_matching_secret,
)
from app.utilities.localization.language_tags import parse_language_tag

logger: logging.Logger = logging.getLogger(__name__)

START_COMMAND: str = "/start"
PRIVATE_CHAT_TYPE: str = "private"
FALLBACK_LANGUAGE: LanguageTag = LanguageTag("en")
# Same limit as the cabinet's manager contacts.
MAX_MANAGER_CONTACTS: int = 20


class HandlePlatformBotUpdateUseCase(
    UseCaseContract[PlatformBotWebhookRequest, PlatformBotWebhookOutcome]
):
    """
    Webhook of the platform Telegram bot that notifies staff.

    "/start <code>" with a valid one-time code links the chat: the chat id
    becomes a Telegram manager contact of the code's business, in the
    language the owner chose (an existing contact with the same chat is
    replaced). Wrong, used or expired codes and any other message get an
    explanation in the sender's Telegram language. Linking is audited.
    """

    def __init__(
        self,
        link_repo: ManagerTelegramLinkRepoContract,
        business_repo: BusinessRepoContract,
        audit_log_repo: AuditLogRepoContract,
        telegram_client: TelegramBotApiClientContract,
        text_resolver: LocalizedTextResolverContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._link_repo: ManagerTelegramLinkRepoContract = link_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._telegram_client: TelegramBotApiClientContract = telegram_client
        self._text_resolver: LocalizedTextResolverContract = text_resolver
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PlatformBotWebhookRequest) -> PlatformBotWebhookOutcome:
        bot_token: PlatformSecret = self._authenticate(input_data)
        update: JsonObject = parse_json_object(input_data.payload.body) or {}
        message: JsonObject = read_object(update, "message") or {}
        chat: JsonObject = read_object(message, "chat") or {}
        sender: JsonObject = read_object(message, "from") or {}
        chat_id: str | None = read_identifier(chat, "id")
        text: str | None = read_text(message, "text")
        if (
            chat_id is None
            or text is None
            or read_text(chat, "type") != PRIVATE_CHAT_TYPE
            or read_flag(sender, "is_bot")
        ):
            return PlatformBotWebhookOutcome(result=PlatformBotCommandResult.IGNORED)

        sender_language: LanguageTag = read_sender_language(sender)
        command, _, argument = text.strip().partition(" ")
        if command != START_COMMAND or argument.strip() == "":
            self._reply(
                bot_token, chat_id, PLATFORM_BOT_INSTRUCTIONS_TEXT, sender_language
            )
            return PlatformBotWebhookOutcome(
                result=PlatformBotCommandResult.INSTRUCTIONS_SENT
            )

        result: PlatformBotCommandResult = self._link(
            bot_token,
            chat_id,
            argument,
            sender_language,
        )
        return PlatformBotWebhookOutcome(result=result)

    def _authenticate(self, input_data: PlatformBotWebhookRequest) -> PlatformSecret:
        bot_token: PlatformSecret | None = (
            self._app_settings.telegram_platform_bot_token
        )
        encryption_key: PlatformSecret | None = self._app_settings.encryption_key
        if bot_token is None or encryption_key is None:
            raise NotFoundError("The platform bot is not configured.")

        expected_secret = derive_telegram_webhook_secret(encryption_key, bot_token)
        if not is_matching_secret(
            str(expected_secret),
            input_data.payload.signature_header,
        ):
            raise AuthenticationRequiredError(
                "The Telegram webhook secret token is missing or wrong."
            )

        return bot_token

    def _link(
        self,
        bot_token: PlatformSecret,
        chat_id: str,
        raw_code: str,
        sender_language: LanguageTag,
    ) -> PlatformBotCommandResult:
        now: Microseconds = self._wall_clock.now_unix()
        code: ManagerLinkCode | None = read_link_code(raw_code)
        link: ManagerTelegramLinkDocument | None = (
            None
            if code is None
            else self._link_repo.find_by_code_hash(hash_link_code(code))
        )
        business: BusinessDocument | None = (
            None
            if link is None or link.used_at is not None or link.expires_at <= now
            else self._business_repo.get(link.business_id)
        )
        if link is None or business is None:
            self._reply(
                bot_token, chat_id, PLATFORM_BOT_REJECTED_CODE_TEXT, sender_language
            )
            return PlatformBotCommandResult.REJECTED_CODE

        address = ManagerContactAddress(chat_id)
        linked_contact = ManagerContact(
            name=link.manager_name,
            channel=ManagerContactChannel.TELEGRAM,
            address=address,
            language=link.language,
        )
        contact_limit_reached: list[bool] = []

        def link_contact(current: BusinessDocument) -> None:
            # Rebuilt from the contacts as stored now, so a contact change
            # saved meanwhile (settings, another manager) is kept.
            other_contacts: list[ManagerContact] = [
                contact
                for contact in current.manager_contacts
                if not (
                    contact.channel is ManagerContactChannel.TELEGRAM
                    and contact.address == address
                )
            ]
            if len(other_contacts) >= MAX_MANAGER_CONTACTS:
                contact_limit_reached.append(True)
                return

            current.manager_contacts = [*other_contacts, linked_contact]
            current.updated_at = now

        business = self._business_repo.update(business.id, link_contact)
        if contact_limit_reached:
            self._reply(
                bot_token,
                chat_id,
                PLATFORM_BOT_CONTACT_LIMIT_TEXT,
                link.language,
                business_name=str(business.name),
            )
            return PlatformBotCommandResult.CONTACT_LIMIT_REACHED

        link.used_at = now
        link.linked_chat_id = address
        link.updated_at = now
        self._link_repo.save(link)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=link.created_by,
                action=AuditAction.UPDATE,
                entity=AuditEntityName("manager_contacts"),
                entity_id=AuditEntityReference(str(business.id)),
                created_at=now,
                updated_at=now,
            )
        )
        self._reply(
            bot_token,
            chat_id,
            PLATFORM_BOT_LINKED_TEXT,
            link.language,
            business_name=str(business.name),
        )
        return PlatformBotCommandResult.LINKED

    def _reply(
        self,
        bot_token: PlatformSecret,
        chat_id: str,
        text: LocalizedText,
        language: LanguageTag,
        business_name: str = "",
    ) -> None:
        reply: str = str(self._text_resolver.resolve(text, language)).format(
            business=business_name
        )
        try:
            self._telegram_client.send_message(
                bot_token,
                ChannelUserId(chat_id),
                OutboundMessagePart(reply),
            )
        except ExternalServiceError as error:
            logger.warning("The platform bot could not reply: %s", error)


def read_sender_language(sender: JsonObject) -> LanguageTag:
    """The language of the sender's Telegram app, English when unknown."""

    raw_language: str | None = read_text(sender, "language_code")
    if raw_language is None:
        return FALLBACK_LANGUAGE

    try:
        return parse_language_tag(raw_language)
    except UnsupportedLanguageError:
        return FALLBACK_LANGUAGE
