"""Which assistant versions the owner may talk to in the test chat."""

from app.schemas.constants.assistants import AssistantVersionStatus

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
