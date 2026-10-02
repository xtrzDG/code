"""'Apply changes': build, check and publish in one call, and its progress."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.niches import ProfileWizardStep
from app.schemas.constants.setup import (
    ApplyAttentionCode,
    ApplyChangesStage,
    SetupActionTarget,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import AssistantApplyDocument
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
    AutotestScenarioCount,
)
from app.schemas.typings.assistants.constrained_strings import GoLiveCheckDetail
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.setup.booleans import HasUnappliedChanges, IsApplyInProgress
from app.schemas.typings.setup.strings import ApplyAttentionMessage, SetupActionLabel
from app.schemas.typings.users.prefixed_id import UserId


class SetupActionView(ImmutableDTO):
    """
    Where the owner goes to act: a cabinet place (and the wizard step for
    PROFILE) with a button label in the owner's language.
    """

    target: SetupActionTarget
    profile_step: ProfileWizardStep | None = None
    label: SetupActionLabel


class ApplyChangesCommand(ImmutableDTO):
    """The owner presses "Apply changes"."""

    user_id: UserId
    business_id: BusinessId


class ApplyChangesQuery(ImmutableDTO):
    """Read the progress of the last "Apply changes" (texts in `language`)."""

    user_id: UserId
    business_id: BusinessId
    language: LanguageTag | None = None


class ApplyAttentionView(ImmutableDTO):
    """One reason the changes are not live, in plain words, with where to fix it."""

    code: ApplyAttentionCode
    message: ApplyAttentionMessage
    details: list[GoLiveCheckDetail] = Field(default_factory=list[GoLiveCheckDetail])
    action: SetupActionView


class ApplyChangesView(ImmutableDTO):
    """
    Progress of "Apply changes". `stage` is None before the first apply.
    While CHECKING, `checks_done` of `checks_total` automatic checks have
    run. NEEDS_ATTENTION lists the reasons. `has_unapplied_changes` is True
    when the profile or knowledge changed after the live version was built
    (or nothing is live yet).
    """

    business_id: BusinessId
    stage: ApplyChangesStage | None = None
    is_in_progress: IsApplyInProgress
    has_unapplied_changes: HasUnappliedChanges
    assistant_version_id: AssistantVersionId | None = None
    version_number: AssistantVersionNumber | None = None
    checks_done: AutotestScenarioCount | None = None
    checks_total: AutotestScenarioCount | None = None
    started_at: Microseconds | None = None
    finished_at: Microseconds | None = None
    attention: list[ApplyAttentionView] = Field(
        default_factory=list[ApplyAttentionView]
    )


class ApplyStart(ImmutableDTO):
    """
    How an apply goes on after it was registered: build a new version
    (`version_to_publish` None) or publish an already checked one;
    `is_running` when an apply was already under way (nothing new starts).
    """

    business: BusinessDocument
    apply: AssistantApplyDocument
    version_to_publish: AssistantVersionId | None = None
    is_running: IsApplyInProgress = False


class AppliedVersion(ImmutableDTO):
    """The version an apply built (or reused), to check or publish next."""

    business_id: BusinessId
    assistant_version_id: AssistantVersionId


class ApplyBuildFailure(ImmutableDTO):
    """The version of an apply could not be built; the owner's message says why."""

    business_id: BusinessId
    code: ApplyAttentionCode
    detail: GoLiveCheckDetail | None = None
