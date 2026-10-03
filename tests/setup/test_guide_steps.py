"""The guide after the launch as pure rules: its steps, next step and completion."""

from app.schemas.constants.setup import (
    SetupActionTarget,
    SetupStepCode,
    SetupStepStatus,
)
from app.utilities.setup.guide_steps import (
    AFTER_LAUNCH_STEPS,
    SKIPPABLE_STEPS,
    GuideFacts,
    derive_after_launch_steps,
    derive_guide,
    guide_next_step,
    is_guide_complete,
)
from app.utilities.setup.setup_steps import (
    SetupFacts,
    StepState,
    compute_minutes_left,
    compute_percent,
    derive_steps,
)

LIVE = SetupFacts(
    findings=[],
    has_staff_contact=True,
    has_connected_channel=True,
    has_tried_assistant=True,
    is_live=True,
    is_agreement_accepted=True,
    is_service_available=True,
)
NOT_LIVE = SetupFacts(
    findings=[],
    has_staff_contact=False,
    has_connected_channel=False,
    has_tried_assistant=False,
    is_live=False,
    is_agreement_accepted=False,
    is_service_available=True,
)
NOTHING_AFTER = GuideFacts(
    has_phone_tested=False, customer_channel_count=1, has_shared=False
)


def statuses(
    setup: SetupFacts,
    after: GuideFacts,
    skipped: frozenset[SetupStepCode] = frozenset(),
) -> dict[SetupStepCode, SetupStepStatus]:
    guide = derive_guide(derive_steps(setup), derive_after_launch_steps(after), skipped)
    return {
        step.code: status
        for step, status in zip(guide.steps, guide.statuses, strict=True)
    }


def test_before_the_launch_the_next_step_is_the_setups_and_the_rest_waits() -> None:
    by_code = statuses(NOT_LIVE, NOTHING_AFTER)

    assert by_code[SetupStepCode.STAFF_CONTACT] is SetupStepStatus.NEXT
    assert [by_code[code] for code in AFTER_LAUNCH_STEPS] == [SetupStepStatus.TODO] * 3
    guide = derive_guide(
        derive_steps(NOT_LIVE), derive_after_launch_steps(NOTHING_AFTER), frozenset()
    )
    assert is_guide_complete(guide, is_live=False) is False


def test_after_the_launch_the_guide_walks_phone_second_channel_and_sharing() -> None:
    assert statuses(LIVE, NOTHING_AFTER)[SetupStepCode.PHONE_TEST] is (
        SetupStepStatus.NEXT
    )

    tested = GuideFacts(
        has_phone_tested=True, customer_channel_count=1, has_shared=False
    )
    by_code = statuses(LIVE, tested)
    assert by_code[SetupStepCode.PHONE_TEST] is SetupStepStatus.DONE
    assert by_code[SetupStepCode.SECOND_CHANNEL] is SetupStepStatus.NEXT

    two_channels = GuideFacts(
        has_phone_tested=True, customer_channel_count=2, has_shared=False
    )
    assert statuses(LIVE, two_channels)[SetupStepCode.SHARE] is SetupStepStatus.NEXT

    everything = GuideFacts(
        has_phone_tested=True, customer_channel_count=6, has_shared=True
    )
    guide = derive_guide(
        derive_steps(LIVE), derive_after_launch_steps(everything), frozenset()
    )
    assert set(guide.statuses) == {SetupStepStatus.DONE}
    assert guide_next_step(guide) is None
    assert is_guide_complete(guide, is_live=True) is True
    assert compute_percent(guide.statuses) == 100
    assert compute_minutes_left(guide.steps, guide.statuses) == 0


def test_a_business_with_many_channels_is_never_asked_for_another() -> None:
    demo = GuideFacts(has_phone_tested=False, customer_channel_count=6, has_shared=True)

    by_code = statuses(LIVE, demo)

    assert by_code[SetupStepCode.SECOND_CHANNEL] is SetupStepStatus.DONE
    assert by_code[SetupStepCode.SHARE] is SetupStepStatus.DONE
    assert by_code[SetupStepCode.PHONE_TEST] is SetupStepStatus.NEXT


def test_skipped_steps_after_the_launch_finish_the_guide() -> None:
    skipped = frozenset(AFTER_LAUNCH_STEPS)
    guide = derive_guide(
        derive_steps(LIVE), derive_after_launch_steps(NOTHING_AFTER), skipped
    )

    assert set(guide.statuses[-3:]) == {SetupStepStatus.SKIPPED}
    assert is_guide_complete(guide, is_live=True) is True
    # Skipped steps count neither as done nor as left.
    assert compute_percent(guide.statuses) == 100


def test_steps_after_the_launch_are_optional_and_point_where_they_are_done() -> None:
    steps: list[StepState] = derive_after_launch_steps(NOTHING_AFTER)

    assert [step.code for step in steps] == list(AFTER_LAUNCH_STEPS)
    assert all(not step.is_required for step in steps)
    assert [step.target for step in steps] == [
        SetupActionTarget.PHONE_TEST,
        SetupActionTarget.CHANNELS,
        SetupActionTarget.SHARE,
    ]
    assert set(AFTER_LAUNCH_STEPS) <= SKIPPABLE_STEPS
    assert SetupStepCode.LAUNCH not in SKIPPABLE_STEPS
    assert SetupStepCode.STAFF_CONTACT not in SKIPPABLE_STEPS


def test_once_live_the_test_chat_gives_way_to_the_phone() -> None:
    untried = SetupFacts(**{**LIVE.__dict__, "has_tried_assistant": False})
    guide = derive_guide(
        derive_steps(untried),
        derive_after_launch_steps(NOTHING_AFTER),
        frozenset(),
        is_live=True,
    )

    assert guide_next_step(guide) is not None
    assert guide_next_step(guide).code is SetupStepCode.PHONE_TEST  # type: ignore[union-attr]


def test_the_share_done_counts_every_step_of_the_guide() -> None:
    guide = derive_guide(
        derive_steps(LIVE), derive_after_launch_steps(NOTHING_AFTER), frozenset()
    )

    # Seven setup steps done, three after the launch left: 70 %.
    assert compute_percent(guide.statuses) == 70
    assert compute_minutes_left(guide.steps, guide.statuses) == 2 + 5 + 3
