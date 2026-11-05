"""
The one write path of the owner's deposit settings: owners only, a change
applied to the settings as stored (two owners editing two cards at once
both keep their change), and an audit entry. A change of the pages guests
pay on (`payment_page_changes`) needs the person to have confirmed it is
them within the step-up window (a fresh sign-in, code or passkey; refused
with `step_up_required` and nothing written otherwise), and the owners
hear of it once it is saved.
"""

from collections.abc import Callable
from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.deposit_repositories import (
    DepositSettingsRepoContract,
)
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.deposits import DepositSettingsDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.deposits.deposit_settings import DepositSettingsView
from app.schemas.dto.deposits.payment_page_changes import PaymentPageChange
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.deposits.deposit_settings_views import (
    build_settings_view,
    stored_or_default,
)
from app.use_cases.deposits.payment_page_changes import (
    payment_page_changes,
    payment_page_state,
)
from app.use_cases.deposits.payment_page_notices import PaymentPageNotices
from app.use_cases.shared.operations_support import build_audit_entry

DEPOSIT_SETTINGS_ENTITY: AuditEntityName = AuditEntityName("deposit_settings")

type SettingsEdit = Callable[[DepositSettingsDocument], DepositSettingsDocument]


@dataclass(frozen=True)
class DepositSettingsChanges:
    authorize_business_access: UseCaseContract[BusinessAccessRequest, BusinessDocument]
    settings_repo: DepositSettingsRepoContract
    audit_log_repo: AuditLogRepoContract
    wall_clock: WallClock[Microseconds]
    step_up: StepUpGuardContract
    page_notices: PaymentPageNotices

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
        page_changes: list[PaymentPageChange] = []

        def change(stored: DepositSettingsDocument) -> DepositSettingsDocument:
            before = payment_page_state(stored)
            edited: DepositSettingsDocument = edit(stored)
            # A retried change starts again from the settings as stored.
            page_changes[:] = payment_page_changes(before, payment_page_state(edited))
            if page_changes:
                self.step_up.require_recent_authentication()
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
        self.page_notices.notify(business, page_changes, now)
        return build_settings_view(settings, business)
