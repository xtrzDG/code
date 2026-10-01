import re

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.registries import LanguageRegistryContract
from app.contracts.repositories import (
    AuditLogRepoContract,
    BusinessRepoContract,
    SubscriptionRepoContract,
    UserRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import (
    BusinessSettingsRefusalCode,
    BusinessStatus,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.businesses import (
    BusinessSettingsChanges,
    BusinessView,
    BusinessViewSource,
    ManagerContactInput,
    UpdateBusinessSettingsCommand,
)
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.constrained_integers import BusinessRevision
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.handoffs.strings import ManagerContactAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.utilities.businesses.business_settings_validation import (
    require_existing_timezone,
    require_valid_business_name,
    require_valid_city_name,
    validate_business_languages,
)
from app.utilities.security.email_addresses import parse_email_address

MAX_MANAGER_CONTACTS: int = 20
MAX_MANAGER_NAME_LENGTH: int = 100
# Telegram chat ids are integers; group and channel chats are negative.
TELEGRAM_CHAT_ID_PATTERN: re.Pattern[str] = re.compile(r"^-?[0-9]{1,20}$")
STALE_REVISION_MESSAGE: str = (
    "These settings were saved by someone else after you opened them. Reload "
    "them and make your change again."
)
OWNER_STATUS_SWITCHES: frozenset[tuple[BusinessStatus, BusinessStatus]] = frozenset(
    {
        (BusinessStatus.LIVE, BusinessStatus.PAUSED),
        (BusinessStatus.PAUSED, BusinessStatus.LIVE),
    }
)


class UpdateBusinessSettingsUseCase(
    UseCaseContract[UpdateBusinessSettingsCommand, BusinessView]
):
    """
    Owner changes business settings; missing fields stay unchanged.

    Languages follow the creation rules; when the default language drops out
    of a new language list, the first language becomes the default. Manager
    contacts are validated per channel: a numeric Telegram chat id, a phone
    number of any country for WhatsApp and SMS (stored as E.164, national
    formats read in the business country), an e-mail address for e-mail.
    The owner may only pause a live assistant (its voice agent is removed)
    and resume a paused one (the published version is activated again, with
    the launch conditions and a new voice agent); publishing (another
    module) makes a business live. The plan may be
    chosen here until the business has a subscription; after that it is
    changed in billing, which also changes the price. Contact changes are
    audited because they hold staff personal data.

    Optimistic concurrency: a change made from an older revision than the
    stored one (`expected_revision`) is refused with ConflictError (reason
    `stale_revision`), and the write itself only succeeds while nobody else
    saved the business since it was read here, so a newer save (another
    owner, a manager linking the platform bot, billing) is never silently
    overwritten.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        subscription_repo: SubscriptionRepoContract,
        language_registry: LanguageRegistryContract,
        phone_number_parser: PhoneNumberParserContract,
        audit_log_repo: AuditLogRepoContract,
        business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ],
        wall_clock: WallClock[Microseconds],
        remove_voice_agent: UseCaseContract[BusinessId, None],
        resume_assistant: UseCaseContract[BusinessDocument, None],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._business_repo: BusinessRepoContract = business_repo
        self._user_repo: UserRepoContract = user_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._language_registry: LanguageRegistryContract = language_registry
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ] = business_view_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._remove_voice_agent: UseCaseContract[BusinessId, None] = remove_voice_agent
        self._resume_assistant: UseCaseContract[BusinessDocument, None] = (
            resume_assistant
        )

    def run(self, input_data: UpdateBusinessSettingsCommand) -> BusinessView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        changes: BusinessSettingsChanges = input_data.changes
        if (
            changes.expected_revision is not None
            and changes.expected_revision != business.revision
        ):
            raise build_stale_revision_error(business.revision)

        self._apply_profile_changes(business, changes)
        self._apply_language_changes(business, changes)
        self._apply_status_change(business, changes.status)

        now: Microseconds = self._wall_clock.now_unix()
        contacts_audit_entry: AuditLogEntryDocument | None = None
        if changes.manager_contacts is not None:
            business.manager_contacts = [
                self._validate_manager_contact(contact_input, business)
                for contact_input in self._limit_contacts(changes.manager_contacts)
            ]
            contacts_audit_entry = AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=AuditEntityName("manager_contacts"),
                entity_id=AuditEntityReference(str(business.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )

        business.updated_at = now
        if not self._business_repo.save_if_unchanged(business):
            raise build_stale_revision_error(None)

        if contacts_audit_entry is not None:
            self._audit_log_repo.append(contacts_audit_entry)
        member_users: list[UserDocument] = [
            user
            for member in business.members
            if (user := self._user_repo.get(member.user_id)) is not None
        ]
        return self._business_view_transformer.transform(
            BusinessViewSource(
                business=business,
                member_users=member_users,
                viewer_id=input_data.user_id,
            )
        )

    def _apply_profile_changes(
        self,
        business: BusinessDocument,
        changes: BusinessSettingsChanges,
    ) -> None:
        if changes.name is not None:
            require_valid_business_name(changes.name)
            business.name = changes.name

        if changes.city is not None:
            require_valid_city_name(changes.city)
            business.city = None if changes.city.strip() == "" else changes.city

        if changes.timezone is not None:
            require_existing_timezone(changes.timezone)
            business.timezone = changes.timezone

        if changes.plan_key is not None and changes.plan_key is not business.plan_key:
            if self._subscription_repo.list_by_business(business.id):
                raise ConflictError(
                    "The plan is part of the subscription; change it in billing."
                )

            business.plan_key = changes.plan_key

        if changes.recording_retention_days is not None:
            business.recording_retention_days = changes.recording_retention_days

    def _apply_language_changes(
        self,
        business: BusinessDocument,
        changes: BusinessSettingsChanges,
    ) -> None:
        if changes.languages is not None:
            business.languages = validate_business_languages(
                changes.languages,
                self._language_registry,
            )

        if changes.default_language is not None:
            if changes.default_language not in business.languages:
                raise ValidationFailedError(
                    "The default language must be one of the business languages."
                )

            business.default_language = changes.default_language
        elif business.default_language not in business.languages:
            business.default_language = business.languages[0]

        if changes.owner_language is not None:
            self._language_registry.get(changes.owner_language)
            business.owner_language = changes.owner_language

    def _apply_status_change(
        self,
        business: BusinessDocument,
        requested_status: BusinessStatus | None,
    ) -> None:
        if requested_status is None or requested_status is business.status:
            return

        if (business.status, requested_status) not in OWNER_STATUS_SWITCHES:
            raise ConflictError(
                "Only a live assistant can be paused and only a paused one "
                f"resumed; the business is {business.status.value}."
            )

        if requested_status is BusinessStatus.LIVE:
            # Resuming re-activates the published version: launch conditions
            # are checked again and the voice agent is set up anew.
            self._resume_assistant.run(business)
            return

        business.status = requested_status
        # A paused assistant answers no calls: its voice agent is removed.
        self._remove_voice_agent.run(business.id)

    def _limit_contacts(
        self,
        contact_inputs: list[ManagerContactInput],
    ) -> list[ManagerContactInput]:
        if len(contact_inputs) > MAX_MANAGER_CONTACTS:
            raise ValidationFailedError(
                f"A business can have at most {MAX_MANAGER_CONTACTS} manager contacts."
            )

        return contact_inputs

    def _validate_manager_contact(
        self,
        contact_input: ManagerContactInput,
        business: BusinessDocument,
    ) -> ManagerContact:
        if contact_input.name.strip() == "":
            raise ValidationFailedError("Manager name must not be empty.")

        if len(contact_input.name) > MAX_MANAGER_NAME_LENGTH:
            raise ValidationFailedError(
                f"Manager name must be at most {MAX_MANAGER_NAME_LENGTH} characters."
            )

        language: LanguageTag = contact_input.language or business.owner_language
        self._language_registry.get(language)
        return ManagerContact(
            name=contact_input.name,
            channel=contact_input.channel,
            address=self._validate_contact_address(contact_input, business),
            language=language,
        )

    def _validate_contact_address(
        self,
        contact_input: ManagerContactInput,
        business: BusinessDocument,
    ) -> ManagerContactAddress:
        match contact_input.channel:
            case ManagerContactChannel.TELEGRAM:
                chat_id: str = contact_input.address.strip()
                if TELEGRAM_CHAT_ID_PATTERN.fullmatch(chat_id) is None:
                    raise ValidationFailedError(
                        "A Telegram contact needs the numeric chat id the platform "
                        "bot shows after the manager presses Start."
                    )

                return ManagerContactAddress(chat_id)
            case ManagerContactChannel.EMAIL:
                email: EmailAddress = parse_email_address(contact_input.address)
                return ManagerContactAddress(str(email))
            case ManagerContactChannel.WHATSAPP | ManagerContactChannel.SMS:
                phone_number: PhoneNumberDetails = self._phone_number_parser.parse(
                    RawPhoneNumberInput(str(contact_input.address)),
                    business.country_code,
                )
                return ManagerContactAddress(str(phone_number.e164))


def build_stale_revision_error(
    current_revision: BusinessRevision | None,
) -> ConflictError:
    """
    The refusal of a change made from an older revision; its details carry
    the current revision when it is known.
    """

    return ConflictError(
        STALE_REVISION_MESSAGE,
        reasons=[
            ErrorReason(
                code=ErrorReasonCode(BusinessSettingsRefusalCode.STALE_REVISION.value),
                message=ErrorReasonMessage(STALE_REVISION_MESSAGE),
                details=(
                    []
                    if current_revision is None
                    else [ErrorReasonDetail(str(int(current_revision)))]
                ),
            )
        ],
    )
