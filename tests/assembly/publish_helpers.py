"""Ready versions, rollbacks and go-live checks shared by the publish tests."""

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants.assistant_commands import (
    RollbackAssistantVersionCommand,
)
from app.schemas.dto.assistants.assistant_views import AssistantVersionDetails
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from tests.assembly.testbed import AssemblyTestbed


def reason_codes(error: ApplicationError) -> list[tuple[str, list[str]]]:
    """Codes and details of the machine-readable reasons of a refusal."""

    return [
        (str(reason.code), [str(detail) for detail in reason.details])
        for reason in error.reasons
    ]


def ready_version(
    testbed: AssemblyTestbed,
    business: BusinessDocument,
) -> AssistantVersionDetails:
    version = testbed.assemble(business.id, run_autotests=True)
    assert version.status is AssistantVersionStatus.READY
    return version


def rollback(
    testbed: AssemblyTestbed,
    business: BusinessDocument,
    version_id: AssistantVersionId,
    as_staff: bool = False,
) -> AssistantVersionDetails:
    testbed.advance(60)
    return testbed.rollback_use_case.run(
        RollbackAssistantVersionCommand(
            user_id=testbed.staff_id if as_staff else testbed.owner_id,
            business_id=business.id,
            version_id=version_id,
        )
    )


def only_subscription(
    testbed: AssemblyTestbed,
    business: BusinessDocument,
) -> SubscriptionDocument:
    subscriptions = testbed.subscription_repo.list_by_business(business.id)
    assert len(subscriptions) == 1
    return subscriptions[0]


def assert_nothing_went_live(
    testbed: AssemblyTestbed,
    business: BusinessDocument,
    version: AssistantVersionDetails,
) -> None:
    stored_business = testbed.business(business.id)
    assert stored_business.status is BusinessStatus.TESTING
    assert stored_business.published_assistant_version_id is None
    assert testbed.version(business.id, version.id).status is (
        AssistantVersionStatus.READY
    )
    assert testbed.voice_provisioner.specs == []
