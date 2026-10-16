from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.nudges import NudgeCode
from app.schemas.constants.setup import (
    ActivationEventKind,
    ApplyAttentionCode,
    ApplyChangesStage,
    SetupStepCode,
)
from app.schemas.typings.assistants.constrained_strings import GoLiveCheckDetail
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.setup.constrained_integers import NudgeRecipientCount
from app.schemas.typings.setup.prefixed_id import (
    ActivationEventId,
    AssistantApplyId,
    NudgeSentId,
    SetupStateId,
)
from app.schemas.typings.users.prefixed_id import UserId


class ActivationEventDocument(BaseDocument):
    """
    A milestone of a business on its way to real customers (first publish,
    first conversation, booking and handoff, the first test chat), stored
    once per kind; the id is derived from the business and the kind.

    `occurred_at` is when it happened; `celebrated_at` is set once the
    cabinet has shown its celebration, so it is shown only once.

    Version 2: `kind` may be FIRST_AFTER_HOURS_BOOKING. This release only
    learns the value (the milestone is kept in the setup state); the next
    one may write it here, since every running release then reads it.
    """

    schema_version: SchemaVersion = SchemaVersion("2")
    id: ActivationEventId
    business_id: BusinessId
    kind: ActivationEventKind
    occurred_at: Microseconds
    celebrated_at: Microseconds | None = None


class SetupStateDocument(BaseDocument):
    """
    What the owner decided about the guided setup of one business, and what
    the guide noticed that no other record keeps. Everything else about the
    setup is computed from the business's own data.

    - `skipped_steps`: the optional steps before the launch the owner
      skipped; `skipped_after_launch` the ones after it (kept apart: the
      release before this field does not know those step codes).
    - `phone_check_started_at`: the owner opened "Try it from your phone";
      a real conversation that starts within the next half hour counts as
      theirs. `phone_tested_at`: the first message that came from the
      owner's own phone (their number, a linked chat, or that window).
    - `shared_at`: the QR card was first printed or saved;
      `hosted_page_visited_at`: the hosted chat page was first opened.
    - `after_hours_booking_at` / `after_hours_booking_celebrated_at`: the
      first real booking made while the business was closed, and when the
      cabinet celebrated it (the milestone lives here until
      `activation_events` may carry its kind).
    - `guide_dismissed_at`: the owner put away the finished guide.
    - `reminders_off_at`: the owners asked for no activation nudges.

    Version 2: everything after `skipped_steps` (all optional, so version 1
    rows read as they are).
    """

    schema_version: SchemaVersion = SchemaVersion("2")
    id: SetupStateId
    business_id: BusinessId
    skipped_steps: list[SetupStepCode] = Field(default_factory=list[SetupStepCode])
    skipped_after_launch: list[SetupStepCode] = Field(
        default_factory=list[SetupStepCode]
    )
    phone_check_started_at: Microseconds | None = None
    phone_tested_at: Microseconds | None = None
    shared_at: Microseconds | None = None
    hosted_page_visited_at: Microseconds | None = None
    after_hours_booking_at: Microseconds | None = None
    after_hours_booking_celebrated_at: Microseconds | None = None
    guide_dismissed_at: Microseconds | None = None
    reminders_off_at: Microseconds | None = None


class NudgeSentDocument(BaseDocument):
    """
    An activation nudge sent to a business (`nudges_sent`): one per
    business and code, its id derived from both, so a nudge goes out once
    however often, and on however many workers, the job runs.
    `recipient_count` is how many addresses and devices it was queued for.
    """

    id: NudgeSentId
    business_id: BusinessId
    code: NudgeCode
    recipient_count: NudgeRecipientCount
    sent_at: Microseconds


class ApplyAttentionReason(PersistentDocument):
    """
    Why applied changes did not go live, with machine details (profile gap
    kinds, missing server settings, the agreement version to accept).
    """

    code: ApplyAttentionCode
    details: list[GoLiveCheckDetail] = Field(default_factory=list[GoLiveCheckDetail])


class AssistantApplyDocument(BaseDocument):
    """
    The current "Apply changes" of a business: the version built from the
    profile and knowledge, where it stands (building, checking, publishing,
    live, needs attention) and, when it needs attention, why. One per
    business (the id is derived from it); a new apply replaces the last.
    """

    id: AssistantApplyId
    business_id: BusinessId
    stage: ApplyChangesStage
    requested_by: UserId
    assistant_version_id: AssistantVersionId | None = None
    attention: list[ApplyAttentionReason] = Field(
        default_factory=list[ApplyAttentionReason]
    )
    started_at: Microseconds
    finished_at: Microseconds | None = None
