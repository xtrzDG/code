"""The owner's changes to the deposit settings, made through their use cases."""

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
from app.use_cases.deposits.remove_payment_link_use_case import (
    RemovePaymentLinkUseCase,
)
from app.use_cases.deposits.update_deposit_settings_use_case import (
    UpdateDepositSettingsUseCase,
)
from tests.deposits.deposit_world import DepositWorld


def owner_changes(world: DepositWorld) -> DepositSettingsChanges:
    return DepositSettingsChanges(
        authorize_business_access=world.authorize(),
        settings_repo=world.deposit_settings_repo,
        audit_log_repo=world.audit_repo,
        wall_clock=world.clock.wall_clock,
    )


def remove_page(world: DepositWorld, link_id: PaymentLinkId) -> DepositSettingsView:
    """The owner removes a payment page in Settings → Deposits."""

    return RemovePaymentLinkUseCase(owner_changes(world)).run(
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
