"""
Rolling back to an archived version: owner only, and only while the service is paid.
"""

import pytest

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from tests.assembly.international_business_seeds import seed_online_shop
from tests.assembly.publish_helpers import (
    only_subscription,
    ready_version,
    reason_codes,
    rollback,
)
from tests.assembly.testbed import AssemblyTestbed


def test_rollback_publishes_an_archived_version_again() -> None:
    testbed = AssemblyTestbed()
    business = seed_online_shop(testbed)
    first = ready_version(testbed, business)
    testbed.publish(business.id, first.id)
    second = ready_version(testbed, business)
    testbed.publish(business.id, second.id)

    restored = rollback(testbed, business, first.id)

    assert restored.id == first.id
    assert restored.status is AssistantVersionStatus.PUBLISHED
    assert testbed.version(business.id, second.id).status is (
        AssistantVersionStatus.ARCHIVED
    )
    assert testbed.business(business.id).published_assistant_version_id == first.id
    assert restored.published_at == testbed.wall_clock.now_unix()


def test_rollback_needs_an_archived_version_and_the_owner() -> None:
    testbed = AssemblyTestbed()
    business = seed_online_shop(testbed)
    first = ready_version(testbed, business)
    testbed.publish(business.id, first.id)
    draft = testbed.assemble(business.id)

    with pytest.raises(ConflictError, match="is published") as published:
        rollback(testbed, business, first.id)

    with pytest.raises(ConflictError, match="is draft") as drafted:
        rollback(testbed, business, draft.id)

    assert reason_codes(published.value) == [("version_not_archived", ["published"])]
    assert reason_codes(drafted.value) == [("version_not_archived", ["draft"])]

    with pytest.raises(AccessDeniedError):
        rollback(testbed, business, first.id, as_staff=True)

    with pytest.raises(NotFoundError):
        rollback(testbed, business, AssistantVersionId())


def test_rollback_is_refused_once_the_service_is_no_longer_paid() -> None:
    testbed = AssemblyTestbed()
    business = seed_online_shop(testbed)
    first = ready_version(testbed, business)
    testbed.publish(business.id, first.id)
    second = ready_version(testbed, business)
    testbed.publish(business.id, second.id)
    subscription = only_subscription(testbed, business)
    subscription.status = SubscriptionStatus.CANCELLED
    subscription.period_end = testbed.wall_clock.now_unix()
    testbed.subscription_repo.save(subscription)

    with pytest.raises(ConflictError, match="Start the trial or pay"):
        rollback(testbed, business, first.id)

    assert testbed.business(business.id).published_assistant_version_id == second.id
    assert testbed.version(business.id, first.id).status is (
        AssistantVersionStatus.ARCHIVED
    )
