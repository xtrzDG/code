"""
Discarding a draft decides and writes in one step: a draft whose checks
start between the owner's press and the write is not discarded, and the
audit log only records a discard that happened.
"""

from collections.abc import Callable

import pytest

from app.repositories.assistant_repositories import AssistantVersionRepository
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.dto.setup.pending_changes import DiscardDraftCommand
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.assistants.pending_changes.discard_assistant_draft_use_case import (
    DiscardAssistantDraftUseCase,
)
from tests.assembly.international_business_seeds import seed_italian_restaurant
from tests.assembly.testbed import AssemblyTestbed
from tests.setup.apply_testbed import apply, settle


class ChecksStartMeanwhile(AssistantVersionRepository):
    """
    The version store, where the draft starts its checks right before the
    discard writes (another owner pressed "Run checks" a moment earlier).
    """

    def __init__(self, stored: AssistantVersionRepository) -> None:
        self._stored: AssistantVersionRepository = stored

    def get(
        self, business_id: BusinessId, version_id: AssistantVersionId
    ) -> AssistantVersionDocument | None:
        return self._stored.get(business_id, version_id)

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[AssistantVersionDocument]:
        return self._stored.list_by_business(business_id)

    def save(self, version: AssistantVersionDocument) -> None:
        self._stored.save(version)

    def modify(
        self,
        business_id: BusinessId,
        version_id: AssistantVersionId,
        change: Callable[[AssistantVersionDocument], AssistantVersionDocument | None],
    ) -> AssistantVersionDocument | None:
        testing = self._stored.get(business_id, version_id)
        assert testing is not None
        testing.status = AssistantVersionStatus.TESTING
        self._stored.save(testing)
        return self._stored.modify(business_id, version_id, change)


def discard_use_case(
    testbed: AssemblyTestbed, versions: AssistantVersionRepository
) -> DiscardAssistantDraftUseCase:
    return DiscardAssistantDraftUseCase(
        authorize_business_access=testbed.authorize,
        assistant_version_repo=versions,
        assistant_apply_repo=testbed.apply_repo,
        audit_log_repo=testbed.audit_repo,
        live_events=testbed.apply_events,
        wall_clock=testbed.wall_clock,
    )


def test_a_draft_whose_checks_start_meanwhile_is_not_discarded() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    apply(testbed, business)
    testbed.run_worker()
    draft = testbed.assemble(business.id)

    with pytest.raises(ConflictError):
        discard_use_case(testbed, ChecksStartMeanwhile(testbed.version_repo)).run(
            DiscardDraftCommand(
                user_id=testbed.owner_id,
                business_id=business.id,
                assistant_version_id=draft.id,
            )
        )

    stored = testbed.version(business.id, draft.id)
    assert stored.status is AssistantVersionStatus.TESTING
    assert stored.discarded_at is None
    assert [
        entry
        for entry in testbed.audit_repo.list_by_business(business.id)
        if entry.action is AuditAction.DELETE
    ] == []


def test_a_quiet_draft_is_discarded_once() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    apply(testbed, business)
    testbed.run_worker()
    draft = testbed.assemble(business.id)
    discard = discard_use_case(testbed, testbed.version_repo)
    command = DiscardDraftCommand(
        user_id=testbed.owner_id,
        business_id=business.id,
        assistant_version_id=draft.id,
    )

    discard.run(command)
    with pytest.raises(ConflictError):
        discard.run(command)

    assert testbed.version(business.id, draft.id).discarded_at is not None
    assert [
        str(entry.entity_id)
        for entry in testbed.audit_repo.list_by_business(business.id)
        if entry.action is AuditAction.DELETE
    ] == [str(draft.id)]
