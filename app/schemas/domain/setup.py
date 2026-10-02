from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.setup import (
    ActivationEventKind,
    ApplyAttentionCode,
    ApplyChangesStage,
    SetupStepCode,
)
from app.schemas.typings.assistants.constrained_strings import GoLiveCheckDetail
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.setup.prefixed_id import (
    ActivationEventId,
    AssistantApplyId,
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
    """

    id: ActivationEventId
    business_id: BusinessId
    kind: ActivationEventKind
    occurred_at: Microseconds
    celebrated_at: Microseconds | None = None


class SetupStateDocument(BaseDocument):
    """
    What the owner decided about the guided setup of one business: the
    optional steps they chose to skip. Everything else about the setup is
    computed from the business's own data.
    """

    id: SetupStateId
    business_id: BusinessId
    skipped_steps: list[SetupStepCode] = Field(default_factory=list[SetupStepCode])


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
