"""The Overview's guide as the owner sees it, from the derived steps."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.setup import ActivationEventKind, SetupActionTarget
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.setup import ActivationEventDocument, SetupStateDocument
from app.schemas.dto.setup.setup_guide import SetupGuideView
from app.schemas.dto.setup.setup_progress import ActivationMilestoneView
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.setup.constrained_integers import (
    SetupMinutesLeft,
    SetupPercent,
)
from app.utilities.setup.guide_steps import (
    GuideFacts,
    GuideState,
    guide_next_step,
    is_guide_complete,
)
from app.utilities.setup.phone_check import is_listening, listening_window
from app.utilities.setup.setup_steps import compute_minutes_left, compute_percent
from app.utilities.setup.setup_views import action_view, step_views


def guide_facts(
    state: SetupStateDocument | None,
    channels: Sequence[ChannelDocument],
    events: Sequence[ActivationEventDocument],
) -> GuideFacts:
    """
    What a business did on the way to its first customers: its own message
    from a phone, how many channels customers can write in, and whether the
    link reached anyone (the QR card printed or saved, the hosted page
    opened, or a real customer already wrote).
    """

    has_customer: bool = any(
        event.kind is ActivationEventKind.FIRST_CONVERSATION for event in events
    )
    return GuideFacts(
        has_phone_tested=state is not None and state.phone_tested_at is not None,
        customer_channel_count=count_customer_channels(channels),
        has_shared=has_customer
        or (
            state is not None
            and (
                state.shared_at is not None or state.hosted_page_visited_at is not None
            )
        ),
    )


def count_customer_channels(channels: Sequence[ChannelDocument]) -> int:
    """Connected channels customers write in (the owner's test chat is not one)."""

    return sum(
        1
        for channel in channels
        if channel.status is ChannelStatus.CONNECTED
        and channel.kind is not ChannelKind.OWNER_TEST
    )


def guide_view(
    guide: GuideState,
    after_launch_count: int,
    state: SetupStateDocument | None,
    is_live: bool,
    now: Microseconds,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> SetupGuideView:
    """The guide: the steps after the launch, next step, share done, the phone check."""

    first_after: int = len(guide.steps) - after_launch_count
    next_step = guide_next_step(guide)
    window = listening_window(state)
    return SetupGuideView(
        steps_after_launch=step_views(
            guide.steps[first_after:],
            guide.statuses[first_after:],
            language,
            resolver,
        ),
        next_step=None if next_step is None else next_step.code,
        next_action=action_view(
            SetupActionTarget.OVERVIEW if next_step is None else next_step.target,
            language,
            resolver,
            None if next_step is None else next_step.profile_step,
        ),
        percent=SetupPercent(compute_percent(guide.statuses)),
        minutes_left=SetupMinutesLeft(
            compute_minutes_left(guide.steps, guide.statuses)
        ),
        is_complete=is_guide_complete(guide, is_live),
        is_dismissed=state is not None and state.guide_dismissed_at is not None,
        is_phone_check_listening=is_listening(state, now),
        phone_check_until=None if window is None else window[1],
        phone_tested_at=None if state is None else state.phone_tested_at,
    )


def after_hours_milestone(
    state: SetupStateDocument | None,
) -> list[ActivationMilestoneView]:
    """The first booking after hours, kept in the setup state, as a milestone."""

    if state is None or state.after_hours_booking_at is None:
        return []

    return [
        ActivationMilestoneView(
            kind=ActivationEventKind.FIRST_AFTER_HOURS_BOOKING,
            occurred_at=state.after_hours_booking_at,
            celebrated_at=state.after_hours_booking_celebrated_at,
        )
    ]
