"""
A deposit rule moved to a page another rule already uses, and another
default template, change where guests pay: refused without a fresh
confirmation (nothing written) and told to the owners. A rule that keeps
its page while its amount changes needs neither.
"""

import pytest

from app.schemas.constants.deposits import DepositRule, DepositTarget, PaymentLinkKind
from app.schemas.domain.deposits import (
    BookingDepositPolicy,
    PaymentLink,
    TargetedDepositPolicy,
)
from app.schemas.dto.deposits.deposit_settings import (
    DepositPolicyInput,
    DepositPolicyRequest,
    DepositSettingsRequest,
    SetDepositPolicyCommand,
    UpdateDepositSettingsCommand,
)
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.deposits.constrained_integers import DepositAmountMinor
from app.schemas.typings.deposits.constrained_strings import (
    PaymentLinkAddress,
    PaymentLinkLabel,
)
from app.schemas.typings.deposits.prefixed_id import PaymentLinkId
from app.schemas.typings.deposits.strings import PaymentLinkHost, PaymentLinkPreview
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.deposits.set_deposit_policy_use_case import SetDepositPolicyUseCase
from app.use_cases.deposits.update_deposit_settings_use_case import (
    UpdateDepositSettingsUseCase,
)
from tests.deposits.deposit_owner_actions import owner_changes, stored_settings
from tests.deposits.deposit_world import DepositWorld
from tests.deposits.test_payment_page_step_up import RecordingAlerts, SwitchableStepUp

SECOND_PAGE: str = "https://pay.example.net/caparra?importo={amount}&rif={reference}"


def add_banquet_page(world: DepositWorld) -> PaymentLinkId:
    """A second template, on which the banquets already pay."""

    settings = stored_settings(world)
    link = PaymentLink(
        label=PaymentLinkLabel("Satispay"),
        kind=PaymentLinkKind.TEMPLATE,
        address=PaymentLinkAddress(SECOND_PAGE),
        host=PaymentLinkHost("pay.example.net"),
        preview=PaymentLinkPreview(SECOND_PAGE),
        added_at=settings.created_at,
    )
    settings.payment_links.append(link)
    settings.policies.append(
        TargetedDepositPolicy(
            target=DepositTarget.BANQUET,
            policy=BookingDepositPolicy(
                rule=DepositRule.FIXED,
                amount_minor=DepositAmountMinor(5000),
                currency_code=world.business.currency_code,
                payment_link_id=link.id,
            ),
        )
    )
    world.deposit_settings_repo.save(settings)
    return link.id


def set_policy(
    world: DepositWorld,
    request: DepositPolicyRequest,
    step_up: SwitchableStepUp,
    alerts: RecordingAlerts,
) -> None:
    SetDepositPolicyUseCase(
        owner_changes(world, step_up, alerts), world.resource_repo, world.knowledge_repo
    ).run(
        SetDepositPolicyCommand(
            user_id=world.owner_id, business_id=world.business.id, request=request
        )
    )


def table_rule_page(world: DepositWorld) -> PaymentLinkId | None:
    [table] = [
        entry
        for entry in stored_settings(world).policies
        if entry.target is DepositTarget.RESOURCE
    ]
    return table.policy.payment_link_id


def test_a_rule_moved_to_a_page_another_rule_uses_needs_a_confirmation() -> None:
    world = DepositWorld()
    world.take_deposits(rule=DepositRule.FIXED, min_party_size=None)
    page_id = add_banquet_page(world)
    request = DepositPolicyRequest(
        target=DepositTarget.RESOURCE,
        resource_id=world.table_for_eight.id,
        policy=DepositPolicyInput(
            rule=DepositRule.FIXED,
            amount_minor=DepositAmountMinor(2000),
            payment_link_id=page_id,
        ),
    )

    with pytest.raises(StepUpRequiredError):
        set_policy(world, request, SwitchableStepUp(is_recent=False), RecordingAlerts())
    assert table_rule_page(world) is None

    alerts = RecordingAlerts()
    set_policy(world, request, SwitchableStepUp(is_recent=True), alerts)

    assert table_rule_page(world) == page_id
    [(_, texts)] = alerts.alerts
    assert "A deposit rule now uses the payment page pay.example.net" in str(
        texts.brief(LanguageTag("en")).detail
    )


def test_a_rule_keeping_its_page_needs_no_confirmation() -> None:
    world = DepositWorld()
    world.take_deposits()
    page_id = add_banquet_page(world)
    step_up, alerts = SwitchableStepUp(is_recent=False), RecordingAlerts()

    set_policy(
        world,
        DepositPolicyRequest(
            target=DepositTarget.BANQUET,
            policy=DepositPolicyInput(
                rule=DepositRule.FIXED,
                amount_minor=DepositAmountMinor(8000),
                payment_link_id=page_id,
            ),
        ),
        step_up,
        alerts,
    )

    assert step_up.checks == 0
    assert alerts.alerts == []


def test_another_default_template_needs_a_confirmation_and_is_told() -> None:
    world = DepositWorld()
    world.take_deposits()
    page_id = add_banquet_page(world)
    first_default = stored_settings(world).default_payment_link_id

    def choose_default(step_up: SwitchableStepUp, alerts: RecordingAlerts) -> None:
        UpdateDepositSettingsUseCase(owner_changes(world, step_up, alerts)).run(
            UpdateDepositSettingsCommand(
                user_id=world.owner_id,
                business_id=world.business.id,
                request=DepositSettingsRequest(
                    is_enabled=True, default_payment_link_id=page_id
                ),
            )
        )

    with pytest.raises(StepUpRequiredError):
        choose_default(SwitchableStepUp(is_recent=False), RecordingAlerts())
    assert stored_settings(world).default_payment_link_id == first_default

    alerts = RecordingAlerts()
    choose_default(SwitchableStepUp(is_recent=True), alerts)

    assert stored_settings(world).default_payment_link_id == page_id
    [(_, texts)] = alerts.alerts
    assert "La pagina di pagamento predefinita ora è pay.example.net" in str(
        texts.brief(LanguageTag("it")).detail
    )
