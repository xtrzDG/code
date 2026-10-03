"""What happens to the other versions of a business when one goes live."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.domain.assistants import AssistantVersionDocument

# Versions that never went live and are not under test.
DISCARDABLE_STATUSES: frozenset[AssistantVersionStatus] = frozenset(
    {
        AssistantVersionStatus.DRAFT,
        AssistantVersionStatus.READY,
        AssistantVersionStatus.TESTS_FAILED,
    }
)


def is_outdated_draft(
    candidate: AssistantVersionDocument, live: AssistantVersionDocument
) -> bool:
    """
    A version older than the one going live that never went live and is
    not being checked right now: nobody will publish it any more.
    """

    return (
        candidate.discarded_at is None
        and int(candidate.version_number) < int(live.version_number)
        and candidate.status in DISCARDABLE_STATUSES
    )


def retire_other_versions(
    versions: Sequence[AssistantVersionDocument],
    live: AssistantVersionDocument,
    now: Microseconds,
) -> list[AssistantVersionDocument]:
    """
    The other versions changed by `live` going live, changed in place: the
    published one is archived (a rollback can bring it back) and older
    drafts are discarded.
    """

    changed: list[AssistantVersionDocument] = []
    for other in versions:
        if other.id == live.id:
            continue

        if other.status is AssistantVersionStatus.PUBLISHED:
            other.status = AssistantVersionStatus.ARCHIVED
        elif is_outdated_draft(other, live):
            other.discarded_at = now
        else:
            continue

        other.updated_at = now
        changed.append(other)

    return changed
