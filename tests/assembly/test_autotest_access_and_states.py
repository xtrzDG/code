"""Who may run autotests on which version, re-testing and the one-go pipeline."""

import pytest

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.dto.assistants.assistant_commands import AssistantVersionQuery
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from tests.assembly.autotest_run_helpers import start
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.testbed import AssemblyTestbed


def test_restricted_states_and_access() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)

    with pytest.raises(AccessDeniedError):
        testbed.run_autotests(business.id, version.id, user_id=testbed.staff_id)

    with pytest.raises(NotFoundError):
        testbed.run_autotests(business.id, version.id, user_id=testbed.stranger_id)

    with pytest.raises(NotFoundError):
        testbed.run_autotests(business.id, AssistantVersionId())

    testbed.publish(
        business.id,
        version.id,
        accept_failed_tests=True,
        user_id=testbed.add_platform_admin(),
    )
    with pytest.raises(ConflictError, match="published"):
        testbed.run_autotests(business.id, version.id)

    assert testbed.conversation.inbound_messages == []


def test_failed_version_can_be_tested_again() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.judge_raw_answers["booking__en"] = "no verdict"
    first = testbed.run_autotests(business.id, version.id)
    del testbed.judge_raw_answers["booking__en"]

    second = testbed.run_autotests(business.id, version.id)

    assert first.version_status is AssistantVersionStatus.TESTS_FAILED
    assert second.version_status is AssistantVersionStatus.READY
    assert testbed.version(business.id, version.id).autotest_run_id == second.id
    assert testbed.run_repo.get(business.id, first.id) is not None


def test_latest_run_is_readable_by_staff() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    query = AssistantVersionQuery(
        user_id=testbed.staff_id,
        business_id=business.id,
        version_id=version.id,
    )
    with pytest.raises(NotFoundError, match="no autotest run"):
        testbed.get_autotest_run_use_case.run(query)

    run = testbed.run_autotests(business.id, version.id)

    stored = testbed.get_autotest_run_use_case.run(query)
    assert stored.id == run.id
    assert stored.version_status is AssistantVersionStatus.READY
    assert stored.results == run.results


def test_pipeline_assembles_and_tests_in_one_go() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)

    version = testbed.assemble(business.id, run_autotests=True)

    assert version.status is AssistantVersionStatus.READY
    assert version.test_score is not None
    assert float(version.test_score) == 5.0
    assert version.autotest_run_id is not None
