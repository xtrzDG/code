"""The owner changes the general settings of a business."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.registries import LanguageRegistryContract
from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.businesses import (
    BusinessSettingsChanges,
    BusinessView,
    BusinessViewSource,
    UpdateBusinessSettingsCommand,
)
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
from app.use_cases.businesses.business_status_switch import check_status_switch
from app.use_cases.businesses.manager_contact_rules import (
    limit_manager_contacts,
    validate_manager_contact,
)
from app.utilities.businesses.business_revisions import build_stale_revision_error
from app.utilities.businesses.business_settings_validation import (
    require_existing_timezone,
    require_valid_business_name,
    require_valid_city_name,
    validate_business_languages,
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
    The owner may only pause a live assistant (its voice agent is removed
    once the pause is stored) and resume a paused one (the published version
    is activated again, with the launch conditions and a new voice agent);
    publishing (another module) makes a business live. A refused change
    (invalid, stale) changes nothing, the status included. The plan may be
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

        read_revision: BusinessRevision = business.revision
        status_switch: BusinessStatus | None = check_status_switch(
            business,
            changes.status,
        )
        self._apply_profile_changes(business, changes)
        self._apply_language_changes(business, changes)

        now: Microseconds = self._wall_clock.now_unix()
        contacts_audit_entry: AuditLogEntryDocument | None = None
        if changes.manager_contacts is not None:
            business.manager_contacts = [
                validate_manager_contact(
                    self._language_registry,
                    self._phone_number_parser,
                    contact_input,
                    business,
                )
                for contact_input in limit_manager_contacts(changes.manager_contacts)
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
        # The status switch comes last, after every other change was
        # validated. Resuming activates the published version again (launch
        # conditions, a new voice agent), and activation then writes this
        # whole business, only while nobody saved it since it was read here.
        if status_switch is BusinessStatus.LIVE:
            self._resume_assistant.run(business)
        elif status_switch is BusinessStatus.PAUSED:
            business.status = BusinessStatus.PAUSED

        if business.revision == read_revision and not (
            self._business_repo.save_if_unchanged(business)
        ):
            raise build_stale_revision_error(None)

        if status_switch is BusinessStatus.PAUSED:
            # Only a stored pause switches the voice agent off, so a refused
            # change leaves a live business with its agent. Calls of a paused
            # business are refused even while the removal fails.
            self._remove_voice_agent.run(business.id)

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
