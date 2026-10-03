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
from app.schemas.typings.setup.booleans import (
    HasUnappliedChanges,
    IsApplyInProgress,
    IsApplyStarted,
)
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


class ApplyChangesSource(ImmutableDTO):
    """An authorized business whose "Apply changes" progress is described."""

    business: BusinessDocument
    language: LanguageTag


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
    How an apply goes on once registered: build a new version, or publish
    `version_to_publish` (already checked, nothing changed since). With
    `is_new` False nothing starts: an apply is already under way, or what
    is live is already up to date.
    """

    business: BusinessDocument
    apply: AssistantApplyDocument
    version_to_publish: AssistantVersionId | None = None
    is_new: IsApplyStarted


class AppliedVersion(ImmutableDTO):
    """The version an apply built (or reused), to check or publish next."""

    business_id: BusinessId
    assistant_version_id: AssistantVersionId


class ApplyBuildFailure(ImmutableDTO):
    """
    An apply could not go on: its version could not be built (no version
    yet) or its checks could not start; `code` says why in owner words.
    """

    business_id: BusinessId
    assistant_version_id: AssistantVersionId | None = None
    code: ApplyAttentionCode
    detail: GoLiveCheckDetail | None = None
