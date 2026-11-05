"""Publishing a version: ready ones go live, others only when forced; owner only."""

import pytest

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.dto.assistants.assistant_commands import PublishAssistantVersionCommand
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from tests.assembly.international_business_seeds import (
    seed_italian_restaurant,
    seed_online_shop,
)
from tests.assembly.publish_helpers import ready_version, reason_codes
from tests.assembly.testbed import AssemblyTestbed


def test_ready_version_goes_live() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    version = ready_version(testbed, business)

    published = testbed.publish(business.id, version.id)

    assert published.status is AssistantVersionStatus.PUBLISHED
    assert published.published_at == testbed.wall_clock.now_unix()
    stored_business = testbed.business(business.id)
    assert stored_business.status is BusinessStatus.LIVE
    assert stored_business.published_assistant_version_id == version.id
    assert testbed.version(business.id, version.id).status is (
        AssistantVersionStatus.PUBLISHED
    )


def test_publishing_archives_the_previous_live_version() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    first = ready_version(testbed, business)
    testbed.publish(business.id, first.id)
    second = ready_version(testbed, business)

    testbed.publish(business.id, second.id)

    assert testbed.version(business.id, first.id).status is (
        AssistantVersionStatus.ARCHIVED
    )
    assert testbed.version(business.id, second.id).status is (
        AssistantVersionStatus.PUBLISHED
    )
    assert testbed.business(business.id).published_assistant_version_id == second.id


@pytest.mark.parametrize("make_failed", [True, False])
def test_untested_or_failed_versions_go_live_only_when_an_admin_forces_them(
    make_failed: bool,
) -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    admin_id = testbed.add_platform_admin(business.id)
    if make_failed:
        testbed.judge_raw_answers["booking__it"] = "unreadable"
        version = testbed.assemble(business.id, run_autotests=True)
        assert version.status is AssistantVersionStatus.TESTS_FAILED
    else:
        version = testbed.assemble(business.id)
        assert version.status is AssistantVersionStatus.DRAFT

    with pytest.raises(ConflictError, match="has not passed the autotests") as (
        refused
    ):
        testbed.publish(business.id, version.id)

    assert reason_codes(refused.value) == [
        (
            "autotests",
            ["tests_failed", "finished"] if make_failed else ["draft"],
        )
    ]
    # "A broken version does not reach customers": the owner cannot force it.
    with pytest.raises(AccessDeniedError, match="platform admin") as denied:
        testbed.publish(business.id, version.id, accept_failed_tests=True)

    assert reason_codes(denied.value) == [("force_publish_admin_only", [])]

    assert testbed.business(business.id).status is BusinessStatus.TESTING
    published = testbed.publish(
        business.id,
        version.id,
        accept_failed_tests=True,
        user_id=admin_id,
    )
    assert published.status is AssistantVersionStatus.PUBLISHED
    forced = [
        entry
        for entry in testbed.audit_repo.list_by_business(business.id)
        if entry.action is AuditAction.PUBLISH_UNTESTED
    ]
    assert [(entry.actor_id, str(entry.entity_id)) for entry in forced] == [
        (admin_id, str(version.id))
    ]


def test_versions_under_test_live_or_archived_cannot_be_published() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    first = ready_version(testbed, business)
    testbed.publish(business.id, first.id)
    second = ready_version(testbed, business)
    testbed.publish(business.id, second.id)
    third = testbed.assemble(business.id)
    stored_third = testbed.version(business.id, third.id)
    stored_third.status = AssistantVersionStatus.TESTING
    testbed.version_repo.save(stored_third)

    with pytest.raises(ConflictError, match="already live") as live:
        testbed.publish(business.id, second.id)

    with pytest.raises(ConflictError, match="rollback") as archived:
        testbed.publish(business.id, first.id, accept_failed_tests=True)

    with pytest.raises(ConflictError, match="being tested") as testing:
        testbed.publish(business.id, third.id, accept_failed_tests=True)

    assert reason_codes(live.value) == [("version_already_live", [])]
    assert reason_codes(archived.value) == [("version_archived", [])]
    assert reason_codes(testing.value) == [("autotests", ["testing"])]


def test_only_the_owner_publishes() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    version = ready_version(testbed, business)

    for user_id, error in (
        (testbed.staff_id, AccessDeniedError),
        (testbed.stranger_id, NotFoundError),
    ):
        with pytest.raises(error):
            testbed.publish_use_case.run(
                PublishAssistantVersionCommand(
                    user_id=user_id,
                    business_id=business.id,
                    version_id=version.id,
                )
            )

    with pytest.raises(NotFoundError):
        testbed.publish(business.id, AssistantVersionId())

    assert testbed.version(business.id, version.id).status is (
        AssistantVersionStatus.READY
    )


def test_paused_business_goes_live_again_on_publish() -> None:
    testbed = AssemblyTestbed()
    business = seed_online_shop(testbed)
    stored = testbed.business(business.id)
    stored.status = BusinessStatus.PAUSED
    testbed.business_repo.save(stored)
    version = ready_version(testbed, business)

    testbed.publish(business.id, version.id)

    assert testbed.business(business.id).status is BusinessStatus.LIVE
