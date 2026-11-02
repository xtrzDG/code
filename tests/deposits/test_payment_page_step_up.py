"""
The pages guests pay deposits on are money: adding, removing, making one
the default or giving one to a deposit rule needs a fresh confirmation of
the person (step-up, refused with nothing written), and every owner hears
of the change. Turning deposits on or a hold time is neither.
"""

import pytest

from app.contracts.notifications import (
    StaffAlertFacilitatorContract,
    StaffAlertTextsContract,
)
from app.contracts.session_assurance import StepUpGuardContract
from app.schemas.constants.deposits import (
    DepositRule,
    DepositTarget,
    PaymentLinkKind,
)
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.deposits.deposit_settings import (
    AddPaymentLinkCommand,
    DepositPolicyInput,
    DepositPolicyRequest,
    DepositSettingsRequest,
    PaymentLinkInput,
    SetDepositPolicyCommand,
    UpdateDepositSettingsCommand,
)
from app.schemas.dto.notifications.staff_alerts import StaffAlert
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.deposits.constrained_integers import DepositAmountMinor
from app.schemas.typings.deposits.constrained_strings import (
    PaymentLinkAddressInput,
    PaymentLinkLabel,
)
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.deposits.add_payment_link_use_case import AddPaymentLinkUseCase
from app.use_cases.deposits.set_deposit_policy_use_case import SetDepositPolicyUseCase
from app.use_cases.deposits.update_deposit_settings_use_case import (
    UpdateDepositSettingsUseCase,
)
from tests.deposits.deposit_owner_actions import (
    owner_changes,
    remove_page,
    stored_settings,
)
from tests.deposits.deposit_world import DepositWorld

TEMPLATE: str = "https://pay.example.org/deposit?sum={amount}&ref={reference}"


class SwitchableStepUp(StepUpGuardContract):
    """Confirmed recently or not, as the test says; counts the checks."""

    def __init__(self, is_recent: bool) -> None:
        self.is_recent: bool = is_recent
        self.checks: int = 0

    def require_recent_authentication(self) -> None:
        self.checks += 1
        if not self.is_recent:
            raise StepUpRequiredError("Confirm it is you.")


class RecordingAlerts(StaffAlertFacilitatorContract):
    def __init__(self) -> None:
        self.alerts: list[tuple[StaffAlert, StaffAlertTextsContract]] = []

    def alert(
        self,
        business: BusinessDocument,
        alert: StaffAlert,
        texts: StaffAlertTextsContract,
    ) -> DeliveredNotificationCount:
        self.alerts.append((alert, texts))
        return DeliveredNotificationCount(1)


def add_page(
    world: DepositWorld, step_up: StepUpGuardContract, alerts: RecordingAlerts
) -> None:
    AddPaymentLinkUseCase(owner_changes(world, step_up, alerts), world.cipher).run(
        AddPaymentLinkCommand(
            user_id=world.owner_id,
            business_id=world.business.id,
            link=PaymentLinkInput(
                label=PaymentLinkLabel("Satispay"),
                kind=PaymentLinkKind.TEMPLATE,
                address=PaymentLinkAddressInput(TEMPLATE),
            ),
        )
    )


def test_adding_a_page_without_a_fresh_confirmation_writes_nothing() -> None:
    world = DepositWorld()
    world.take_deposits()
    pages_before = len(stored_settings(world).payment_links)
    alerts = RecordingAlerts()

    with pytest.raises(StepUpRequiredError):
        add_page(world, SwitchableStepUp(is_recent=False), alerts)

    assert len(stored_settings(world).payment_links) == pages_before
    assert alerts.alerts == []


def test_an_added_page_is_told_to_every_owner_urgently() -> None:
    world = DepositWorld()
    world.take_deposits()
    step_up, alerts = SwitchableStepUp(is_recent=True), RecordingAlerts()

    add_page(world, step_up, alerts)

    assert step_up.checks == 1
    [(alert, texts)] = alerts.alerts
    assert alert.is_urgent is True
    assert alert.member_roles == [BusinessMemberRole.OWNER]
    assert alert.target is StaffLinkTarget.ACCOUNT_SECURITY
    brief = texts.brief(LanguageTag("it"))
    assert "Pagina di pagamento aggiunta: pay.example.org" in str(brief.detail)
    assert str(world.business.name) in str(brief.title)
    english = texts.brief(LanguageTag("en"))
    assert "Payment page added: pay.example.org" in str(english.detail)


def test_removing_a_page_needs_a_confirmation_and_is_told() -> None:
    world = DepositWorld()
    world.take_deposits()
    page = stored_settings(world).payment_links[0]
    alerts = RecordingAlerts()

    with pytest.raises(StepUpRequiredError):
        remove_page(world, page.id, SwitchableStepUp(is_recent=False), alerts)
    assert [link.id for link in stored_settings(world).payment_links] == [page.id]

    remove_page(world, page.id, SwitchableStepUp(is_recent=True), alerts)

    assert stored_settings(world).payment_links == []
    [(_, texts)] = alerts.alerts
    assert "Payment page removed: pay.example.com" in str(
        texts.brief(LanguageTag("en")).detail
    )


def test_a_rule_pointed_at_another_page_needs_a_confirmation() -> None:
    world = DepositWorld()
    world.take_deposits(rule=DepositRule.FIXED, min_party_size=None)
    page = stored_settings(world).payment_links[0]
    step_up = SwitchableStepUp(is_recent=False)

    with pytest.raises(StepUpRequiredError):
        SetDepositPolicyUseCase(
            owner_changes(world, step_up, RecordingAlerts()),
            world.resource_repo,
            world.knowledge_repo,
        ).run(
            SetDepositPolicyCommand(
                user_id=world.owner_id,
                business_id=world.business.id,
                request=DepositPolicyRequest(
                    target=DepositTarget.BANQUET,
                    policy=DepositPolicyInput(
                        rule=DepositRule.FIXED,
                        amount_minor=DepositAmountMinor(5000),
                        payment_link_id=page.id,
                    ),
                ),
            )
        )

    assert step_up.checks == 1


def test_switching_deposits_and_hold_times_need_no_confirmation() -> None:
    world = DepositWorld()
    world.take_deposits()
    step_up, alerts = SwitchableStepUp(is_recent=False), RecordingAlerts()

    UpdateDepositSettingsUseCase(owner_changes(world, step_up, alerts)).run(
        UpdateDepositSettingsCommand(
            user_id=world.owner_id,
            business_id=world.business.id,
            request=DepositSettingsRequest(is_enabled=False),
        )
    )

    assert stored_settings(world).is_enabled is False
    assert step_up.checks == 0
    assert alerts.alerts == []
