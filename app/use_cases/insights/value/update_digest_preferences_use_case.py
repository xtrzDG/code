from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.notification_repositories import (
    PushSubscriptionRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.repositories.value_repositories import (
    DigestPreferencesRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.value_settings import DigestPreferencesDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.value.value_views import (
    DigestPreferencesView,
    UpdateDigestPreferencesCommand,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.insights.value.digest_preferences_views import (
    apply_digest_request,
    build_digest_preferences_view,
    stored_preferences_or_default,
)

DIGEST_PREFERENCES_ENTITY: AuditEntityName = AuditEntityName("digest_preferences")


class UpdateDigestPreferencesUseCase(
    UseCaseContract[UpdateDigestPreferencesCommand, DigestPreferencesView]
):
    """
    The signed-in owner turns their daily or weekly digest or their
    monthly report on or off (the opt-out every digest links to) and
    chooses where they arrive: e-mail, devices, their Telegram chat linked
    to the platform bot, WhatsApp to the number they opt in with
    (`apply_digest_request` refuses a channel that cannot reach them).
    Only their own choices change; a report already queued still arrives.
    Audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        digest_preferences_repo: DigestPreferencesRepoContract,
        user_repo: UserRepoContract,
        push_subscription_repo: PushSubscriptionRepoContract,
        audit_log_repo: AuditLogRepoContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._digest_preferences_repo: DigestPreferencesRepoContract = (
            digest_preferences_repo
        )
        self._user_repo: UserRepoContract = user_repo
        self._push_subscription_repo: PushSubscriptionRepoContract = (
            push_subscription_repo
        )
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateDigestPreferencesCommand) -> DigestPreferencesView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        preferences: DigestPreferencesDocument = stored_preferences_or_default(
            business,
            input_data.user_id,
            self._digest_preferences_repo.get(business.id, input_data.user_id),
        )
        apply_digest_request(
            business, preferences, input_data.request, self._app_settings
        )
        preferences.updated_at = now
        self._digest_preferences_repo.save(preferences)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=DIGEST_PREFERENCES_ENTITY,
                entity_id=AuditEntityReference(str(preferences.id)),
                created_at=now,
                updated_at=now,
            )
        )
        return build_digest_preferences_view(
            business,
            preferences,
            self._user_repo,
            self._push_subscription_repo,
            self._app_settings,
        )
