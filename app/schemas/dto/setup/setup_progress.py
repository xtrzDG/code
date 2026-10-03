"""The guided setup of a business: its steps, progress, links and milestones."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.constants.setup import (
    ActivationEventKind,
    SetupStepCode,
    SetupStepStatus,
)
from app.schemas.dto.setup.apply_changes import ApplyChangesView, SetupActionView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.setup.booleans import (
    CanGoLive,
    IsAssistantLive,
    IsPhoneTestAnswering,
    IsSetupComplete,
    IsSetupStepRequired,
    IsSetupStepSkipped,
)
from app.schemas.typings.setup.constrained_integers import (
    SetupMinutesLeft,
    SetupPercent,
    SetupStepMinutes,
)
from app.schemas.typings.setup.constrained_strings import PhoneTestUrl
from app.schemas.typings.setup.strings import SetupStepDescription, SetupStepTitle
from app.schemas.typings.users.prefixed_id import UserId


class SetupQuery(ImmutableDTO):
    """Read the setup of a business (texts in `language`, the owner's by default)."""

    user_id: UserId
    business_id: BusinessId
    language: LanguageTag | None = None


class SetupStepView(ImmutableDTO):
    """
    One step of the guided setup. `missing` names what the profile still
    lacks for it (profile gap kinds); `minutes` is how long it usually
    takes. Optional steps (`is_required` False) may be skipped.
    """

    code: SetupStepCode
    status: SetupStepStatus
    is_required: IsSetupStepRequired
    title: SetupStepTitle
    description: SetupStepDescription
    minutes: SetupStepMinutes
    action: SetupActionView
    missing: list[ProfileGapKind] = Field(default_factory=list[ProfileGapKind])


class PhoneTestLinkView(ImmutableDTO):
    """
    A link the owner opens on their phone (or as a QR code) to write to
    their own assistant: the hosted website chat page or the Telegram bot.
    `is_answering` is False until the assistant is live there.
    """

    channel: ChannelKind
    url: PhoneTestUrl
    is_answering: IsPhoneTestAnswering


class ActivationMilestoneView(ImmutableDTO):
    """A milestone reached; `celebrated_at` is set once the cabinet showed it."""

    kind: ActivationEventKind
    occurred_at: Microseconds
    celebrated_at: Microseconds | None = None


class SetupView(ImmutableDTO):
    """
    The guided setup in order: business, offer, hours and bookings, staff
    contact, channels, test, launch; each done, skipped, next or to do.
    `percent` counts done steps among those not skipped; `minutes_left`
    adds up the steps still ahead. `can_go_live` is True once every
    required step before the launch is done; `is_complete` once the
    assistant is live and every required step is done.
    """

    business_id: BusinessId
    language: LanguageTag
    steps: list[SetupStepView]
    next_step: SetupStepCode | None = None
    next_action: SetupActionView
    percent: SetupPercent
    minutes_left: SetupMinutesLeft
    can_go_live: CanGoLive
    is_live: IsAssistantLive
    is_complete: IsSetupComplete
    went_live_at: Microseconds | None = None
    trial_ends_at: Microseconds | None = None
    phone_test_links: list[PhoneTestLinkView] = Field(
        default_factory=list[PhoneTestLinkView]
    )
    milestones: list[ActivationMilestoneView] = Field(
        default_factory=list[ActivationMilestoneView]
    )
    apply: ApplyChangesView


class SkipSetupStepCommand(ImmutableDTO):
    """Skip an optional setup step, or bring it back (`is_skipped` False)."""

    user_id: UserId
    business_id: BusinessId
    step: SetupStepCode
    is_skipped: IsSetupStepSkipped


class CelebrateMilestoneCommand(ImmutableDTO):
    """The cabinet has shown the celebration of a milestone."""

    user_id: UserId
    business_id: BusinessId
    kind: ActivationEventKind


class ActivationMilestoneCheck(ImmutableDTO):
    """Notice and store the milestones a business has reached."""

    business_id: BusinessId


class ActivationEventRecord(ImmutableDTO):
    """A milestone that just happened (stored once per business and kind)."""

    business_id: BusinessId
    kind: ActivationEventKind
    occurred_at: Microseconds | None = None
