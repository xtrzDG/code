"""The deposits line of Reports: money collected and no-shows compared."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.typings.billing.constrained_integers import CurrencyMinorUnitDigits
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deposits.booleans import (
    AreDepositsEnabled,
    HasEnoughDepositData,
)
from app.schemas.typings.deposits.constrained_integers import (
    DepositOutcomeCount,
    DepositReportDays,
    DepositRequestCount,
    DepositTotalMinor,
    NoShowPercent,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.users.prefixed_id import UserId


class DepositReportQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    days: DepositReportDays = DepositReportDays(90)


class DepositMoney(ImmutableDTO):
    """Deposits of one currency: kept by the business, and still to refund."""

    currency_code: CurrencyCode
    currency_digits: CurrencyMinorUnitDigits
    collected_minor: DepositTotalMinor
    refund_due_minor: DepositTotalMinor


class NoShowRate(ImmutableDTO):
    """
    Finished bookings of one group (the guest came or did not), how many did
    not come, and their share once the group reaches the sample the report
    trusts (`has_enough_data`; below it `no_show_percent` is None).
    """

    finished_count: DepositOutcomeCount
    no_show_count: DepositOutcomeCount
    has_enough_data: HasEnoughDepositData
    no_show_percent: NoShowPercent | None = None


class DepositReport(ImmutableDTO):
    """
    The last `days` until now: the deposits asked, paid and released, the
    money collected per currency (paid and kept; returned ones apart), and
    the no-show rate of bookings that started in the window with a paid
    deposit and without one. A booking still waiting for its outcome (not
    marked arrived or no-show) counts in neither.

    Before and after: the no-show rate of every finished booking that
    started in the `days` before deposits were first turned on
    (`enabled_at`), and of those since then within the window; both None
    while deposits were never on (or were on before the platform noted
    when).
    """

    is_enabled: AreDepositsEnabled
    days: DepositReportDays
    starts_at: Microseconds
    ends_at: Microseconds
    requested_count: DepositRequestCount
    paid_count: DepositRequestCount
    expired_count: DepositRequestCount
    awaiting_count: DepositRequestCount
    money: list[DepositMoney] = Field(default_factory=list[DepositMoney])
    with_deposit: NoShowRate
    without_deposit: NoShowRate
    enabled_at: Microseconds | None = None
    before_deposits: NoShowRate | None = None
    since_deposits: NoShowRate | None = None
    min_sample: DepositOutcomeCount
