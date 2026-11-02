"""The platform's global pause and daily budget stop, for the admin."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.spend import PlatformBrake
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.spend.booleans import IsPlatformPaused
from app.schemas.typings.spend.constrained_integers import (
    PlatformSpendStopPercent,
    SpendPercent,
)
from app.schemas.typings.spend.constrained_strings import PlatformPauseReason
from app.schemas.typings.users.prefixed_id import UserId


class PlatformBrakeReading(ImmutableDTO):
    """
    Whether a platform brake holds every assistant back now: the global
    pause first, else the daily budget stop; None when neither holds.
    """

    brake: PlatformBrake | None = None
    spend_micro_usd: CostMicroUsd | None = None
    budget_micro_usd: CostMicroUsd | None = None


class PlatformPauseQuery(ImmutableDTO):
    """A platform admin asks how the pause and the budget stop stand."""

    user_id: UserId


class PlatformPauseRequest(ImmutableDTO):
    """
    Body of PUT /v1/admin/platform/pause: pause (true) or resume (false)
    every assistant, with the reason the audit log keeps.
    """

    is_paused: IsPlatformPaused
    reason: PlatformPauseReason


class PlatformPauseCommand(ImmutableDTO):
    """A SUPER platform admin pauses or resumes every assistant."""

    user_id: UserId
    request: PlatformPauseRequest
    client_ip_address: ClientIpAddress | None = None


class PlatformPauseView(ImmutableDTO):
    """
    The global pause as it stands (`changed_*`: the last pause or resume;
    None before the first), and the daily budget stop: the share of the
    budget where it holds, today's share (None without a budget) and
    whether it holds now.
    """

    is_paused: IsPlatformPaused
    reason: PlatformPauseReason | None = None
    changed_by: UserId | None = None
    changed_at: Microseconds | None = None
    stop_percent: PlatformSpendStopPercent
    budget_used_percent: SpendPercent | None = None
    brake: PlatformBrake | None = None
