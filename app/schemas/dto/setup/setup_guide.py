"""
The guide on the Overview after (and before) the launch: steps to the
first real customer, trying the assistant from a phone, putting it where
customers see it, putting the finished guide away, and the reminders.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.setup import SetupShareMark, SetupStepCode
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.setup.apply_changes import SetupActionView
from app.schemas.dto.setup.setup_steps_view import SetupStepView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.setup.booleans import (
    AreSetupRemindersOn,
    IsAssistantLive,
    IsPhoneCheckListening,
    IsSetupGuideComplete,
    IsSetupGuideDismissed,
)
from app.schemas.typings.setup.constrained_integers import (
    SetupMinutesLeft,
    SetupPercent,
)
from app.schemas.typings.users.prefixed_id import UserId


class SetupGuideView(ImmutableDTO):
    """
    The whole guide: the setup's seven steps (`SetupView.steps`) and the
    three after the launch (`steps_after_launch`: writing from the owner's
    own phone, a second channel, the link or QR code where customers see
    it), with the guide's own next step, share done (skipped steps do not
    count) and minutes left. `is_complete` once the assistant is live and
    every step is done or skipped; `is_dismissed` once the owner put the
    finished guide away.

    `is_phone_check_listening` while a conversation that starts counts as
    the owner's test (until `phone_check_until`); `phone_tested_at` is when
    the first message from the owner's phone arrived.
    """

    steps_after_launch: list[SetupStepView] = Field(default_factory=list[SetupStepView])
    next_step: SetupStepCode | None = None
    next_action: SetupActionView
    percent: SetupPercent
    minutes_left: SetupMinutesLeft
    is_complete: IsSetupGuideComplete
    is_dismissed: IsSetupGuideDismissed = False
    is_phone_check_listening: IsPhoneCheckListening = False
    phone_check_until: Microseconds | None = None
    phone_tested_at: Microseconds | None = None


class StartPhoneCheckCommand(ImmutableDTO):
    """The owner opened "Try it from your phone": listen for their message."""

    user_id: UserId
    business_id: BusinessId


class MarkSetupSharedCommand(ImmutableDTO):
    """The cabinet saw the owner print or save the QR card."""

    user_id: UserId
    business_id: BusinessId
    mark: SetupShareMark


class DismissSetupGuideCommand(ImmutableDTO):
    """Put the finished guide away, or bring it back (`is_dismissed` False)."""

    user_id: UserId
    business_id: BusinessId
    is_dismissed: IsSetupGuideDismissed


class SetupRemindersQuery(ImmutableDTO):
    """Read whether the owners get activation reminders for a business."""

    user_id: UserId
    business_id: BusinessId


class SetupRemindersRequest(ImmutableDTO):
    """
    Body of the reminders switch.

    Example: {"is_on": false}.
    """

    is_on: AreSetupRemindersOn


class UpdateSetupRemindersCommand(ImmutableDTO):
    """An owner turns the activation reminders of a business on or off."""

    user_id: UserId
    business_id: BusinessId
    request: SetupRemindersRequest


class SetupRemindersView(ImmutableDTO):
    """
    Whether the owners get activation reminders (by e-mail, Telegram and on
    their devices) while the launch or the first customers are not there.
    """

    business_id: BusinessId
    is_on: AreSetupRemindersOn


class GuideProgressCheck(ImmutableDTO):
    """Notice what the guide after the launch waits for, for one business."""

    business: BusinessDocument
    is_live: IsAssistantLive
