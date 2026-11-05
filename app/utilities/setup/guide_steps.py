"""
The guide after the launch: from a live assistant to the first real
customer. Three optional steps follow the seven of the setup (and, for
an owner, a fourth: a second factor that protects the customers' data),
and the whole guide has its own next step, share done and minutes left.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace

from app.schemas.constants.security_nudges import SecurityNudgeReason
from app.schemas.constants.setup import (
    SetupActionTarget,
    SetupStepCode,
    SetupStepStatus,
)
from app.schemas.dto.security_nudges import SecurityNudgeView
from app.utilities.setup.setup_steps import OPTIONAL_STEPS, StepState, assign_statuses

AFTER_LAUNCH_STEPS: tuple[SetupStepCode, ...] = (
    SetupStepCode.PHONE_TEST,
    SetupStepCode.SECOND_CHANNEL,
    SetupStepCode.SHARE,
)
# The steps an owner may skip: the optional ones before the launch and every
# step after it (a business may well live on one channel).
SKIPPABLE_STEPS: frozenset[SetupStepCode] = OPTIONAL_STEPS | frozenset(
    AFTER_LAUNCH_STEPS
)
# A second channel where customers write is the guide's goal; the web chat
# alone reaches only the visitors of a site or of the hosted page.
ENOUGH_CUSTOMER_CHANNELS: int = 2


@dataclass(frozen=True)
class GuideFacts:
    """What a live business has done on the way to its first real customers."""

    has_phone_tested: bool
    customer_channel_count: int
    has_shared: bool


@dataclass(frozen=True)
class GuideState:
    """Every step of the guide with its status, in order (setup, then after)."""

    steps: list[StepState]
    statuses: list[SetupStepStatus]


def derive_after_launch_steps(facts: GuideFacts) -> list[StepState]:
    """Writing from the owner's own phone, a second channel, and the link out."""

    return [
        StepState(
            code=SetupStepCode.PHONE_TEST,
            is_done=facts.has_phone_tested,
            is_required=False,
            target=SetupActionTarget.PHONE_TEST,
        ),
        StepState(
            code=SetupStepCode.SECOND_CHANNEL,
            is_done=facts.customer_channel_count >= ENOUGH_CUSTOMER_CHANNELS,
            is_required=False,
            target=SetupActionTarget.CHANNELS,
        ),
        StepState(
            code=SetupStepCode.SHARE,
            is_done=facts.has_shared,
            is_required=False,
            target=SetupActionTarget.SHARE,
        ),
    ]


def protect_data_steps(nudge: SecurityNudgeView) -> list[StepState]:
    """
    An owner's last step: a passkey or an authenticator app, so the
    customers' data needs more than a login code (staff do not see it).
    """

    if not nudge.is_owner:
        return []

    return [
        StepState(
            code=SetupStepCode.PROTECT_DATA,
            is_done=nudge.has_second_factor,
            is_required=False,
            target=SetupActionTarget.ACCOUNT_SECURITY,
        )
    ]


def protect_data_skips(nudge: SecurityNudgeView) -> frozenset[SetupStepCode]:
    """
    The owner put the reminder away (the step is skipped with it), unless
    it came back because the team has grown since.
    """

    if (
        not nudge.is_owner
        or nudge.dismissed_at is None
        or nudge.reason is SecurityNudgeReason.TEAM_GREW
    ):
        return frozenset()

    return frozenset({SetupStepCode.PROTECT_DATA})


def derive_guide(
    setup_steps: Sequence[StepState],
    after_launch_steps: Sequence[StepState],
    skipped: frozenset[SetupStepCode],
    is_live: bool = False,
) -> GuideState:
    """
    The whole guide's statuses: done, skipped (optional steps only), the
    first left is NEXT. Before the launch the next step is always one of
    the setup's; the steps after it wait as TODO. Once live, trying the
    assistant in the test chat gives way to trying it from a phone.
    """

    steps: list[StepState] = [
        replace(step, is_done=True)
        if is_live and step.code is SetupStepCode.TEST
        else step
        for step in setup_steps
    ]
    steps.extend(after_launch_steps)
    return GuideState(steps=steps, statuses=assign_statuses(steps, skipped))


def is_guide_complete(guide: GuideState, is_live: bool) -> bool:
    """Live, with every step done or (an optional one) skipped."""

    return is_live and all(
        status in (SetupStepStatus.DONE, SetupStepStatus.SKIPPED)
        for status in guide.statuses
    )


def guide_next_step(guide: GuideState) -> StepState | None:
    return next(
        (
            step
            for step, status in zip(guide.steps, guide.statuses, strict=True)
            if status is SetupStepStatus.NEXT
        ),
        None,
    )
