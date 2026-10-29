"""The setup steps as pure rules: what is done, next, skipped and required."""

from dataclasses import replace

from app.schemas.constants.niches import ProfileWizardStep
from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.constants.setup import (
    SetupActionTarget,
    SetupStepCode,
    SetupStepStatus,
)
from app.schemas.dto.profiles.profile_gaps import ProfileGapFinding
from app.schemas.typings.profiles.booleans import IsProfileGapBlocking
from app.schemas.typings.profiles.constrained_strings import QuestionKey
from app.utilities.setup.setup_steps import (
    SetupFacts,
    assign_statuses,
    can_go_live,
    compute_minutes_left,
    compute_percent,
    derive_steps,
)

NOTHING_YET = SetupFacts(
    findings=[],
    has_staff_contact=False,
    has_connected_channel=False,
    has_tried_assistant=False,
    is_live=False,
    is_agreement_accepted=False,
    is_service_available=True,
)


def finding(
    kind: ProfileGapKind,
    step: ProfileWizardStep,
    is_blocking: bool = True,
    question_key: str | None = None,
) -> ProfileGapFinding:
    return ProfileGapFinding(
        kind=kind,
        step=step,
        is_blocking=IsProfileGapBlocking(is_blocking),
        question_key=None if question_key is None else QuestionKey(question_key),
    )


def codes_by_status(facts: SetupFacts) -> dict[SetupStepCode, SetupStepStatus]:
    steps = derive_steps(facts)
    return {
        step.code: status
        for step, status in zip(
            steps, assign_statuses(steps, facts.skipped), strict=True
        )
    }


def test_profile_gaps_are_sorted_into_the_steps_they_belong_to() -> None:
    facts = replace(
        NOTHING_YET,
        findings=[
            finding(ProfileGapKind.NO_ADDRESS, ProfileWizardStep.CONTACTS_AND_HOURS),
            finding(
                ProfileGapKind.MISSING_REQUIRED_ANSWER,
                ProfileWizardStep.NICHE_AND_LANGUAGES,
                question_key="cuisine",
            ),
            finding(
                ProfileGapKind.NO_PRICED_ITEMS,
                ProfileWizardStep.OFFER,
                is_blocking=False,
            ),
            finding(ProfileGapKind.NO_BOOKING_RULES, ProfileWizardStep.BOOKING_RULES),
            # Not blocking: the assistant answers, just less well.
            finding(
                ProfileGapKind.NO_FAQ,
                ProfileWizardStep.FAQ_AND_HANDOFF,
                is_blocking=False,
            ),
        ],
    )

    steps = {step.code: step for step in derive_steps(facts)}

    business = steps[SetupStepCode.BUSINESS]
    assert business.missing == [
        ProfileGapKind.NO_ADDRESS,
        ProfileGapKind.MISSING_REQUIRED_ANSWER,
    ]
    # The step opens the wizard where its first gap is.
    assert business.profile_step is ProfileWizardStep.CONTACTS_AND_HOURS
    assert steps[SetupStepCode.OFFER].missing == [ProfileGapKind.NO_PRICED_ITEMS]
    assert steps[SetupStepCode.OFFER].is_required is False
    assert steps[SetupStepCode.HOURS_AND_BOOKINGS].missing == [
        ProfileGapKind.NO_BOOKING_RULES
    ]
    assert steps[SetupStepCode.HOURS_AND_BOOKINGS].profile_step is (
        ProfileWizardStep.BOOKING_RULES
    )


def test_a_blocking_gap_of_the_offer_makes_the_offer_required() -> None:
    facts = replace(
        NOTHING_YET,
        findings=[
            finding(
                ProfileGapKind.MISSING_REQUIRED_ANSWER,
                ProfileWizardStep.OFFER,
                question_key="services",
            )
        ],
    )

    offer = next(
        step for step in derive_steps(facts) if step.code is SetupStepCode.OFFER
    )

    assert offer.is_required is True
    assert offer.is_done is False


def test_only_optional_steps_are_shown_skipped_and_the_first_open_one_is_next() -> None:
    facts = replace(
        NOTHING_YET,
        findings=[
            finding(ProfileGapKind.NO_ADDRESS, ProfileWizardStep.CONTACTS_AND_HOURS),
            finding(
                ProfileGapKind.NO_PRICED_ITEMS,
                ProfileWizardStep.OFFER,
                is_blocking=False,
            ),
        ],
        skipped=frozenset(
            {SetupStepCode.OFFER, SetupStepCode.CHANNELS, SetupStepCode.BUSINESS}
        ),
    )

    statuses = codes_by_status(facts)

    assert statuses == {
        # A required step is never skipped, even when it was marked so.
        SetupStepCode.BUSINESS: SetupStepStatus.NEXT,
        SetupStepCode.OFFER: SetupStepStatus.SKIPPED,
        SetupStepCode.HOURS_AND_BOOKINGS: SetupStepStatus.DONE,
        SetupStepCode.STAFF_CONTACT: SetupStepStatus.TODO,
        SetupStepCode.CHANNELS: SetupStepStatus.SKIPPED,
        SetupStepCode.TEST: SetupStepStatus.TODO,
        SetupStepCode.LAUNCH: SetupStepStatus.TODO,
    }


def test_percent_and_minutes_count_what_is_left() -> None:
    facts = replace(
        NOTHING_YET,
        has_staff_contact=True,
        skipped=frozenset({SetupStepCode.CHANNELS}),
    )
    steps = derive_steps(facts)
    statuses = assign_statuses(steps, facts.skipped)

    # Done: business, offer, hours, staff contact; counted: six of seven.
    assert compute_percent(statuses) == 4 * 100 // 6
    assert compute_minutes_left(steps, statuses) == 2 + 2
    assert compute_percent([SetupStepStatus.SKIPPED]) == 100


def test_going_live_needs_every_required_step_the_agreement_and_a_plan() -> None:
    ready = replace(NOTHING_YET, has_staff_contact=True, is_agreement_accepted=True)
    launch_targets = {
        "agreement": replace(ready, is_agreement_accepted=False),
        "billing": replace(ready, is_service_available=False),
        "apply": ready,
    }

    targets = {
        name: next(
            step.target
            for step in derive_steps(facts)
            if step.code is SetupStepCode.LAUNCH
        )
        for name, facts in launch_targets.items()
    }

    assert targets == {
        "agreement": SetupActionTarget.AGREEMENT,
        "billing": SetupActionTarget.BILLING,
        "apply": SetupActionTarget.APPLY_CHANGES,
    }
    assert can_go_live(derive_steps(ready), ready) is True
    for blocked in (
        replace(ready, has_staff_contact=False),
        replace(ready, is_agreement_accepted=False),
        replace(ready, is_service_available=False),
    ):
        assert can_go_live(derive_steps(blocked), blocked) is False
