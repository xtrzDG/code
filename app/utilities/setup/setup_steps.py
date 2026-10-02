"""
The guided setup derived from what a business already has: which steps are
done, which one is next, what each still misses and where it is fixed.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.schemas.constants.niches import ProfileWizardStep
from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.constants.setup import (
    SetupActionTarget,
    SetupStepCode,
    SetupStepStatus,
)
from app.schemas.dto.profiles.profile_gaps import ProfileGapFinding

SETUP_STEP_ORDER: tuple[SetupStepCode, ...] = tuple(SetupStepCode)
# Optional steps make the assistant better but never block going live.
OPTIONAL_STEPS: frozenset[SetupStepCode] = frozenset(
    {SetupStepCode.OFFER, SetupStepCode.CHANNELS, SetupStepCode.TEST}
)
STEP_MINUTES: dict[SetupStepCode, int] = {
    SetupStepCode.BUSINESS: 2,
    SetupStepCode.OFFER: 4,
    SetupStepCode.HOURS_AND_BOOKINGS: 2,
    SetupStepCode.STAFF_CONTACT: 1,
    SetupStepCode.CHANNELS: 3,
    SetupStepCode.TEST: 2,
    SetupStepCode.LAUNCH: 2,
}
BUSINESS_ANSWER_STEPS: frozenset[ProfileWizardStep] = frozenset(
    {
        ProfileWizardStep.NICHE_AND_LANGUAGES,
        ProfileWizardStep.FAQ_AND_HANDOFF,
        ProfileWizardStep.CHANNELS,
    }
)
HOURS_ANSWER_STEPS: frozenset[ProfileWizardStep] = frozenset(
    {ProfileWizardStep.CONTACTS_AND_HOURS, ProfileWizardStep.BOOKING_RULES}
)
HOURS_GAP_KINDS: frozenset[ProfileGapKind] = frozenset(
    {
        ProfileGapKind.NO_OPENING_HOURS,
        ProfileGapKind.NO_BOOKING_RULES,
        ProfileGapKind.NO_RESOURCES,
    }
)


@dataclass(frozen=True)
class SetupFacts:
    """What a business has, as far as the setup is concerned."""

    findings: Sequence[ProfileGapFinding]
    has_staff_contact: bool
    has_connected_channel: bool
    has_tried_assistant: bool
    is_live: bool
    is_agreement_accepted: bool
    is_service_available: bool
    skipped: frozenset[SetupStepCode] = frozenset()


@dataclass(frozen=True)
class StepState:
    """One derived setup step: done or not, and where the owner acts."""

    code: SetupStepCode
    is_done: bool
    is_required: bool
    target: SetupActionTarget
    profile_step: ProfileWizardStep | None = None
    missing: list[ProfileGapKind] = field(default_factory=list[ProfileGapKind])


def derive_steps(facts: SetupFacts) -> list[StepState]:
    """The seven steps in order, each done or not with what it misses."""

    business = [
        finding
        for finding in facts.findings
        if finding.is_blocking
        and (
            finding.kind is ProfileGapKind.NO_ADDRESS
            or (
                finding.kind is ProfileGapKind.MISSING_REQUIRED_ANSWER
                and finding.step in BUSINESS_ANSWER_STEPS
            )
        )
    ]
    offer = [
        finding
        for finding in facts.findings
        if finding.kind is ProfileGapKind.NO_PRICED_ITEMS
        or (finding.is_blocking and finding.step is ProfileWizardStep.OFFER)
    ]
    hours = [
        finding
        for finding in facts.findings
        if finding.is_blocking
        and (
            finding.kind in HOURS_GAP_KINDS
            or (
                finding.kind is ProfileGapKind.MISSING_REQUIRED_ANSWER
                and finding.step in HOURS_ANSWER_STEPS
            )
        )
    ]
    return [
        profile_step_state(
            SetupStepCode.BUSINESS, business, ProfileWizardStep.NICHE_AND_LANGUAGES
        ),
        profile_step_state(
            SetupStepCode.OFFER,
            offer,
            ProfileWizardStep.OFFER,
            is_required=any(finding.is_blocking for finding in offer),
        ),
        profile_step_state(
            SetupStepCode.HOURS_AND_BOOKINGS,
            hours,
            ProfileWizardStep.CONTACTS_AND_HOURS,
        ),
        StepState(
            code=SetupStepCode.STAFF_CONTACT,
            is_done=facts.has_staff_contact,
            is_required=True,
            target=SetupActionTarget.STAFF_CONTACTS,
            missing=[]
            if facts.has_staff_contact
            else [ProfileGapKind.NO_HANDOFF_CONTACT],
        ),
        StepState(
            code=SetupStepCode.CHANNELS,
            is_done=facts.has_connected_channel,
            is_required=False,
            target=SetupActionTarget.CHANNELS,
        ),
        StepState(
            code=SetupStepCode.TEST,
            is_done=facts.has_tried_assistant,
            is_required=False,
            target=SetupActionTarget.TEST_CHAT,
        ),
        StepState(
            code=SetupStepCode.LAUNCH,
            is_done=facts.is_live,
            is_required=True,
            target=launch_target(facts),
        ),
    ]


def profile_step_state(
    code: SetupStepCode,
    findings: Sequence[ProfileGapFinding],
    default_step: ProfileWizardStep,
    is_required: bool = True,
) -> StepState:
    """A step finished in the profile wizard, opened at its first gap."""

    return StepState(
        code=code,
        is_done=findings == [],
        is_required=is_required,
        target=SetupActionTarget.PROFILE,
        profile_step=findings[0].step if findings else default_step,
        missing=list(dict.fromkeys(finding.kind for finding in findings)),
    )


def launch_target(facts: SetupFacts) -> SetupActionTarget:
    """What stands between the owner and going live, the agreement first."""

    if not facts.is_agreement_accepted:
        return SetupActionTarget.AGREEMENT

    if not facts.is_service_available:
        return SetupActionTarget.BILLING

    return SetupActionTarget.APPLY_CHANGES


def assign_statuses(
    steps: Sequence[StepState],
    skipped: frozenset[SetupStepCode],
) -> list[SetupStepStatus]:
    """Done, skipped (optional ones only), the first left NEXT, the rest TODO."""

    statuses: list[SetupStepStatus] = []
    has_next: bool = False
    for step in steps:
        if step.is_done:
            statuses.append(SetupStepStatus.DONE)
        elif not step.is_required and step.code in skipped:
            statuses.append(SetupStepStatus.SKIPPED)
        elif not has_next:
            statuses.append(SetupStepStatus.NEXT)
            has_next = True
        else:
            statuses.append(SetupStepStatus.TODO)

    return statuses


def compute_percent(statuses: Sequence[SetupStepStatus]) -> int:
    """Done steps among those not skipped, rounded down."""

    counted: list[SetupStepStatus] = [
        status for status in statuses if status is not SetupStepStatus.SKIPPED
    ]
    if counted == []:
        return 100

    done: int = sum(1 for status in counted if status is SetupStepStatus.DONE)
    return done * 100 // len(counted)


def compute_minutes_left(
    steps: Sequence[StepState],
    statuses: Sequence[SetupStepStatus],
) -> int:
    """Typical minutes of the steps still ahead (next and to do)."""

    return sum(
        STEP_MINUTES[step.code]
        for step, status in zip(steps, statuses, strict=True)
        if status in (SetupStepStatus.NEXT, SetupStepStatus.TODO)
    )


def can_go_live(steps: Sequence[StepState], facts: SetupFacts) -> bool:
    """Every required step before the launch done, the agreement and plan ready."""

    return (
        all(
            step.is_done
            for step in steps
            if step.is_required and step.code is not SetupStepCode.LAUNCH
        )
        and facts.is_agreement_accepted
        and facts.is_service_available
    )
