"""Which assistant versions the owner may talk to in the test chat."""

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.domain.assistants import AssistantVersionDocument

# Versions the owner may talk to: everything but archived ones.
TESTABLE_STATUSES: frozenset[AssistantVersionStatus] = frozenset(
    {
        AssistantVersionStatus.PUBLISHED,
        AssistantVersionStatus.READY,
        AssistantVersionStatus.TESTS_FAILED,
        AssistantVersionStatus.TESTING,
        AssistantVersionStatus.DRAFT,
    }
)


def is_chosen_for_test_chat(version: AssistantVersionDocument) -> bool:
    """
    A version the test chat may pick by itself: not archived, and not a
    draft the owner discarded (it stays readable for a chat that names it).
    """

    return version.status in TESTABLE_STATUSES and version.discarded_at is None
