"""Self-serve owners pay no setup fee; done-for-you brings it and an onboarding request."""

from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    OnboardingRequestStatus,
    PlanKey,
    SetupOption,
    SubscriptionStatus,
)
from app.schemas.dto.billing_cabinet import BillingOverviewSource, SetupOptionChoice
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.use_cases.billing.choose_setup_option_use_case import (
    ChooseSetupOptionUseCase,
)
from tests.billing.paid_world import build_trial, checkout
from tests.billing.subscribe_world import World


def kinds(world: World) -> list[InvoiceKind]:
    return [invoice.kind for invoice in world.testbed.invoices(world.business.id)]


def test_a_self_serve_subscription_bills_only_the_first_month() -> None:
    world = World()

    session = world.subscribe(PlanKey.CHAT, setup_option=SetupOption.SELF_SERVE)

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.INCOMPLETE
    assert subscription.setup_option is SetupOption.SELF_SERVE
    assert kinds(world) == [InvoiceKind.SERVICE_PERIOD]
    assert session.amount.text == "293,00\xa0₾"
    assert (
        world.testbed.onboarding_request_repo.get_by_business(world.business.id) is None
    )


def test_done_for_you_bills_the_setup_fee_and_asks_the_team_once() -> None:
    world = World()

    session = world.subscribe(PlanKey.CHAT, setup_option=SetupOption.DONE_FOR_YOU)
    world.subscribe(PlanKey.CHAT, setup_option=SetupOption.DONE_FOR_YOU)

    assert sorted(kind.value for kind in kinds(world)) == [
        "service_period",
        "setup_fee",
    ]
    assert session.amount.text == "736,00\xa0₾"
    request = world.testbed.onboarding_request_repo.get_by_business(world.business.id)
    assert request is not None
    assert request.status is OnboardingRequestStatus.OPEN
    assert request.plan_key is PlanKey.CHAT
    assert request.requested_by == world.owner.id


def test_switching_back_to_self_serve_voids_the_unpaid_setup_fee() -> None:
    world = World()
    world.subscribe(PlanKey.CHAT, setup_option=SetupOption.DONE_FOR_YOU)

    session = world.subscribe(PlanKey.CHAT, setup_option=SetupOption.SELF_SERVE)

    fees = [
        invoice
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.kind is InvoiceKind.SETUP_FEE
    ]
    assert [fee.status for fee in fees] == [InvoiceStatus.VOID]
    assert session.amount.text == "293,00\xa0₾"
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.setup_option is SetupOption.SELF_SERVE


def test_a_trial_that_started_at_go_live_pays_no_setup_fee() -> None:
    world = build_trial(setup_option=SetupOption.SELF_SERVE)

    session = checkout(world)

    invoices = world.testbed.invoices(world.business.id)
    assert [invoice.kind for invoice in invoices] == [InvoiceKind.SERVICE_PERIOD]
    assert session.amount.text == "517,00\xa0₾"


def test_a_paid_setup_fee_keeps_the_business_done_for_you() -> None:
    world = World()
    session = world.subscribe(PlanKey.CHAT, setup_option=SetupOption.DONE_FOR_YOU)
    world.pay(session)

    world.testbed.choose_setup_option.run(
        SetupOptionChoice(
            user_id=world.owner.id,
            business=world.business,
            subscription_id=world.testbed.subscription(world.business.id).id,
            option=SetupOption.SELF_SERVE,
        )
    )

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.setup_option is SetupOption.DONE_FOR_YOU


def test_the_platform_admins_hear_about_a_done_for_you_request_once() -> None:
    world = World()
    world.subscribe(PlanKey.CHAT, setup_option=SetupOption.SELF_SERVE)
    settings = world.testbed.settings.model_copy(
        update={"platform_admin_emails": [EmailAddress("team@example.com")]}
    )
    choose = ChooseSetupOptionUseCase(
        subscription_repo=world.testbed.subscription_repo,
        invoice_repo=world.testbed.invoice_repo,
        onboarding_request_repo=world.testbed.onboarding_request_repo,
        manager_notifier=world.testbed.notifier,
        app_settings=settings,
        wall_clock=world.testbed.clock.wall_clock,
    )
    choice = SetupOptionChoice(
        user_id=world.owner.id,
        business=world.business,
        subscription_id=world.testbed.subscription(world.business.id).id,
        option=SetupOption.DONE_FOR_YOU,
    )

    choose.run(choice)
    choose.run(choice)

    to_team = [
        text
        for contact, text in world.testbed.notifier.sent
        if str(contact.address) == "team@example.com"
    ]
    assert len(to_team) == 1
    assert str(to_team[0]).startswith("Done-for-you setup requested: ")
    assert f"/admin/clients/{world.business.id}" in str(to_team[0])


def test_the_billing_page_shows_the_option_and_when_help_was_asked_for() -> None:
    world = World()
    world.subscribe(PlanKey.CHAT, setup_option=SetupOption.DONE_FOR_YOU)

    overview = world.testbed.assemble_overview.run(
        BillingOverviewSource(business=world.business)
    )

    assert overview.subscription is not None
    assert overview.subscription.setup_option is SetupOption.DONE_FOR_YOU
    assert overview.subscription.onboarding_requested_at == world.testbed.clock.now()
