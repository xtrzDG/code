"""The owner's changes to the deposit settings, made through their use cases."""

from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.session_assurance import StepUpGuardContract
from app.schemas.domain.deposits import DepositSettingsDocument
from app.schemas.dto.deposits.deposit_settings import (
    DepositSettingsRequest,
    DepositSettingsView,
    RemovePaymentLinkCommand,
    UpdateDepositSettingsCommand,
)
from app.schemas.typings.deposits.constrained_integers import DepositHoldMinutes
from app.schemas.typings.deposits.prefixed_id import PaymentLinkId
from app.use_cases.deposits.deposit_settings_changes import DepositSettingsChanges
from app.use_cases.deposits.payment_page_notices import PaymentPageNotices
from app.use_cases.deposits.remove_payment_link_use_case import (
    RemovePaymentLinkUseCase,
)
from app.use_cases.deposits.update_deposit_settings_use_case import (
    UpdateDepositSettingsUseCase,
)
from tests.deposits.deposit_world import DepositWorld
from tests.foundation.access_support import AllowStepUp


def owner_changes(
    world: DepositWorld,
    step_up: StepUpGuardContract | None = None,
    staff_alerts: StaffAlertFacilitatorContract | None = None,
) -> DepositSettingsChanges:
    """The write path; a page change passes the step-up unless `step_up` says."""

    return DepositSettingsChanges(
        authorize_business_access=world.authorize(),
        settings_repo=world.deposit_settings_repo,
        audit_log_repo=world.audit_repo,
        wall_clock=world.clock.wall_clock,
        step_up=step_up or AllowStepUp(),
        page_notices=PaymentPageNotices(
            staff_alerts or world.staff_alerts, world.resolver
        ),
    )


def remove_page(
    world: DepositWorld,
    link_id: PaymentLinkId,
    step_up: StepUpGuardContract | None = None,
    staff_alerts: StaffAlertFacilitatorContract | None = None,
) -> DepositSettingsView:
    """The owner removes a payment page in Settings → Deposits."""

    return RemovePaymentLinkUseCase(owner_changes(world, step_up, staff_alerts)).run(
        RemovePaymentLinkCommand(
            user_id=world.owner_id, business_id=world.business.id, link_id=link_id
        )
    )


def switch_deposits(
    world: DepositWorld, is_enabled: bool, hold_minutes: int = 60
) -> DepositSettingsView:
    """The owner turns deposits on or off in Settings → Deposits."""

    return UpdateDepositSettingsUseCase(owner_changes(world)).run(
        UpdateDepositSettingsCommand(
            user_id=world.owner_id,
            business_id=world.business.id,
            request=DepositSettingsRequest(
                is_enabled=is_enabled, hold_minutes=DepositHoldMinutes(hold_minutes)
            ),
        )
    )


def stored_settings(world: DepositWorld) -> DepositSettingsDocument:
    settings = world.deposit_settings_repo.get_by_business(world.business.id)
    assert settings is not None
    return settings
