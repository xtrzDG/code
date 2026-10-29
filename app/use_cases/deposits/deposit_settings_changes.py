"""
The one write path of the owner's deposit settings: owners only, a change
applied to the settings as stored (two owners editing two cards at once
both keep their change), and an audit entry.
"""

from collections.abc import Callable
from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.deposit_repositories import (
    DepositSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.deposits import DepositSettingsDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.deposits.deposit_settings import DepositSettingsView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.deposits.deposit_settings_views import (
    build_settings_view,
    stored_or_default,
)
from app.use_cases.shared.operations_support import build_audit_entry

DEPOSIT_SETTINGS_ENTITY: AuditEntityName = AuditEntityName("deposit_settings")

type SettingsEdit = Callable[[DepositSettingsDocument], DepositSettingsDocument]


@dataclass(frozen=True)
class DepositSettingsChanges:
    authorize_business_access: UseCaseContract[BusinessAccessRequest, BusinessDocument]
    settings_repo: DepositSettingsRepoContract
    audit_log_repo: AuditLogRepoContract
    wall_clock: WallClock[Microseconds]

    def owner_business(
        self, user_id: UserId, business_id: BusinessId
    ) -> BusinessDocument:
        return self.authorize_business_access.run(
            BusinessAccessRequest(
                user_id=user_id,
                business_id=business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )

    def apply(
        self, business: BusinessDocument, user_id: UserId, edit: SettingsEdit
    ) -> DepositSettingsView:
        """`edit` on the stored settings (created first when there are none)."""

        now: Microseconds = self.wall_clock.now_unix()
        self.settings_repo.create_if_absent(stored_or_default(None, business.id, now))

        def change(stored: DepositSettingsDocument) -> DepositSettingsDocument:
            edited: DepositSettingsDocument = edit(stored)
            edited.updated_by = user_id
            edited.updated_at = now
            return edited

        saved: DepositSettingsDocument | None = self.settings_repo.update(
            business.id, change
        )
        settings: DepositSettingsDocument = stored_or_default(saved, business.id, now)
        self.audit_log_repo.append(
            build_audit_entry(
                business.id,
                user_id,
                AuditAction.UPDATE,
                DEPOSIT_SETTINGS_ENTITY,
                str(settings.id),
                now,
            )
        )
        return build_settings_view(settings, business)
