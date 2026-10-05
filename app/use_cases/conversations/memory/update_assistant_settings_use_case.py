from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.customer_memory_repositories import (
    AssistantSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistant_settings import AssistantSettingsDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.customer_memory.assistant_settings import (
    AssistantSettingsCommand,
    AssistantSettingsView,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.utilities.memory.assistant_settings_views import view_assistant_settings

ASSISTANT_SETTINGS_ENTITY: AuditEntityName = AuditEntityName("assistant_settings")


class UpdateAssistantSettingsUseCase(
    UseCaseContract[AssistantSettingsCommand, AssistantSettingsView]
):
    """
    An owner turns the customer memory on or off, and lets the team's notes
    reach it or not. Off takes effect at the next customer message: no
    summaries are written and no memory reaches the assistant; summaries
    already written stay with their conversations (the customer's data
    erasure removes them). Audited (UPDATE of "assistant_settings"): it
    decides what the assistant reads of customers' personal data.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        assistant_settings_repo: AssistantSettingsRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._assistant_settings_repo: AssistantSettingsRepoContract = (
            assistant_settings_repo
        )
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AssistantSettingsCommand) -> AssistantSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()

        def update(stored: AssistantSettingsDocument) -> None:
            stored.remembers_customers = input_data.settings.remembers_customers
            stored.shares_team_notes = input_data.settings.shares_team_notes

        settings: AssistantSettingsDocument = self._assistant_settings_repo.change(
            business.id, update, now
        )
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=ASSISTANT_SETTINGS_ENTITY,
                entity_id=AuditEntityReference(str(settings.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return view_assistant_settings(settings)
