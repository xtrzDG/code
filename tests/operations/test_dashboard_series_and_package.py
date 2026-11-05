"""The dashboard's daily series and the package usage of the billing window."""

from datetime import datetime

from app.schemas.constants.billing import (
    BillingPeriod,
    PlanKey,
    SubscriptionStatus,
    UsageKind,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.billing import SubscriptionDocument, UsageEventDocument
from app.schemas.typings.billing.constrained_integers import (
    MoneyAmountMinor,
    UsageQuantity,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from tests.operations.dashboard_fixture import DashboardFixture
from tests.operations.fakes import to_microseconds


def test_daily_series_counts_each_local_day_of_the_period() -> None:
    dashboard = DashboardFixture()
    first = dashboard.conversation(
        "2026-10-01T00:30:00+04:00", ChannelKind.WHATSAPP, "ka"
    )
    dashboard.conversation("2026-10-03T23:30:00+04:00", ChannelKind.TELEGRAM, "ru")
    dashboard.conversation(
        "2026-10-03T12:00:00+04:00", ChannelKind.OWNER_TEST, "en", is_sandbox=True
    )
    dashboard.booking("2026-10-03T23:45:00+04:00")
    dashboard.booking("2026-10-03T10:00:00+04:00", is_sandbox=True)
    dashboard.handoff(
        first,
        "2026-10-05T09:00:00+04:00",
        HandoffReason.COMPLAINT,
        HandoffUrgency.HIGH,
    )

    stats = dashboard.stats()

    assert [
        (
            str(day.date),
            int(day.conversation_count),
            int(day.booking_count),
            int(day.handoff_count),
        )
        for day in stats.daily
    ] == [
        ("2026-10-01", 1, 0, 0),
        ("2026-10-02", 0, 0, 0),
        ("2026-10-03", 1, 1, 0),
        ("2026-10-04", 0, 0, 0),
        ("2026-10-05", 0, 0, 1),
    ]


def test_package_of_the_billing_window_without_prices() -> None:
    dashboard = DashboardFixture()
    assert dashboard.stats().package is None

    start = to_microseconds(datetime.fromisoformat("2026-09-20T00:00:00+04:00"))
    end = to_microseconds(datetime.fromisoformat("2026-10-20T00:00:00+04:00"))
    dashboard.world.subscription_repo.save(
        SubscriptionDocument(
            business_id=dashboard.business.id,
            plan_key=PlanKey.VOICE_AND_CHAT,
            billing_period=BillingPeriod.MONTHLY,
            price_minor=MoneyAmountMinor(25_000),
            currency_code=CurrencyCode("GEL"),
            status=SubscriptionStatus.ACTIVE,
            period_start=start,
            period_end=end,
        )
    )
    for occurred, kind, quantity in (
        ("2026-09-25T10:00:00+04:00", UsageKind.VOICE_SECONDS, 20_000),
        ("2026-10-02T10:00:00+04:00", UsageKind.VOICE_SECONDS, 1_000),
        ("2026-10-02T10:00:00+04:00", UsageKind.DIALOG, 300),
        ("2026-09-10T10:00:00+04:00", UsageKind.VOICE_SECONDS, 9_000),
    ):
        moment = to_microseconds(datetime.fromisoformat(occurred))
        dashboard.world.usage_repo.append(
            UsageEventDocument(
                business_id=dashboard.business.id,
                kind=kind,
                quantity=UsageQuantity(quantity),
                occurred_at=moment,
                created_at=moment,
                updated_at=moment,
            )
        )

    package = dashboard.stats().package

    assert package is not None
    assert (package.period_start, package.period_end) == (start, end)
    assert (package.used_voice_minutes, package.included_voice_minutes) == (350, 400)
    assert package.voice_usage_percent == 87
    assert package.overage_voice_minutes == 0
    assert (package.used_dialogs, package.included_dialogs) == (300, 1500)
    assert package.dialog_usage_percent == 20


def test_no_package_while_the_subscription_waits_for_its_first_payment() -> None:
    dashboard = DashboardFixture()
    start = to_microseconds(datetime.fromisoformat("2026-10-01T00:00:00+04:00"))
    end = to_microseconds(datetime.fromisoformat("2026-11-01T00:00:00+04:00"))
    dashboard.world.subscription_repo.save(
        SubscriptionDocument(
            business_id=dashboard.business.id,
            plan_key=PlanKey.VOICE_AND_CHAT,
            billing_period=BillingPeriod.MONTHLY,
            price_minor=MoneyAmountMinor(25_000),
            currency_code=CurrencyCode("GEL"),
            status=SubscriptionStatus.INCOMPLETE,
            period_start=start,
            period_end=end,
        )
    )

    assert dashboard.stats().package is None
