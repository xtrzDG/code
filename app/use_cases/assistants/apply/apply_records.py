"""Moving the current "Apply changes" of a business from stage to stage."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.setup_repositories import AssistantApplyRepoContract
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.setup import ApplyChangesStage
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.setup import ApplyAttentionReason, AssistantApplyDocument
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId

# Stages after which nothing more happens until the owner applies again.
FINAL_STAGES: frozenset[ApplyChangesStage] = frozenset(
    {ApplyChangesStage.LIVE, ApplyChangesStage.NEEDS_ATTENTION}
)
# A request that built or published for this long has died on the way.
STALE_STEP_MICROSECONDS: int = 15 * 60 * 1_000_000


def is_apply_running(
    apply: AssistantApplyDocument,
    versions: Sequence[AssistantVersionDocument],
    now: Microseconds,
) -> bool:
    """
    Still under way: building or publishing recently, or checking while
    the worker plays the version's checks.
    """

    match apply.stage:
        case ApplyChangesStage.BUILDING | ApplyChangesStage.PUBLISHING:
            return int(now) - int(apply.updated_at) < STALE_STEP_MICROSECONDS
        case ApplyChangesStage.CHECKING:
            return any(
                version.id == apply.assistant_version_id
                and version.status is AssistantVersionStatus.TESTING
                for version in versions
            )
        case ApplyChangesStage.LIVE | ApplyChangesStage.NEEDS_ATTENTION:
            return False


def move_apply(
    apply_repo: AssistantApplyRepoContract,
    live_events: EventPublisherFacilitatorContract,
    business_id: BusinessId,
    version_id: AssistantVersionId | None,
    stage: ApplyChangesStage,
    now: Microseconds,
    attention: Sequence[ApplyAttentionReason] = (),
) -> AssistantApplyDocument | None:
    """
    Move the business's apply to `stage` (with its version and, for
    NEEDS_ATTENTION, the reasons), unless a newer apply of another version
    replaced it meanwhile, and tell the business's open cabinets
    (`assistant.apply`), so the progress they show follows at once.
    """

    def move(stored: AssistantApplyDocument) -> AssistantApplyDocument | None:
        if (
            version_id is not None
            and stored.assistant_version_id is not None
            and stored.assistant_version_id != version_id
        ):
            return None

        stored.stage = stage
        if version_id is not None:
            stored.assistant_version_id = version_id

        stored.attention = list(attention)
        stored.finished_at = now if stage in FINAL_STAGES else None
        stored.updated_at = now
        return stored

    moved: AssistantApplyDocument | None = apply_repo.modify(business_id, move)
    if moved is not None:
        announce_apply(live_events, moved)

    return moved


def announce_apply(
    live_events: EventPublisherFacilitatorContract,
    apply: AssistantApplyDocument,
) -> None:
    """The apply moved: its id, and its version's once it has one."""

    live_events.publish(
        apply.business_id,
        LiveEventKind.ASSISTANT_APPLY,
        (apply.id,)
        if apply.assistant_version_id is None
        else (apply.id, apply.assistant_version_id),
    )
