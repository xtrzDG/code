"""'Apply changes' over the in-memory assembly slice (tests/assembly/testbed.py)."""

from app.schemas.constants.setup import ApplyAttentionCode, ApplyChangesStage
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import AssistantApplyDocument
from app.schemas.dto.setup.apply_changes import (
    ApplyChangesCommand,
    ApplyChangesQuery,
    ApplyChangesView,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.assembly.testbed import AssemblyTestbed


def settle(testbed: AssemblyTestbed, business: BusinessDocument) -> BusinessDocument:
    """
    Date the seeded profile, knowledge, resources and special days at the
    testbed's clock
    (the seeds stamp them with the real time), so "changed since the
    version was built" compares like with like.
    """

    now = testbed.wall_clock.now_unix()
    profile = testbed.profile_repo.get_by_business(business.id)
    if profile is not None:
        profile.updated_at = now
        testbed.profile_repo.save(profile)

    for item in testbed.knowledge_repo.list_by_business(business.id):
        item.created_at = item.updated_at = now
        testbed.knowledge_repo.save(item)

    for resource in testbed.resource_repo.list_by_business(business.id):
        resource.created_at = resource.updated_at = now
        testbed.resource_repo.save(resource)

    for special_day in testbed.exception_repo.list_by_business(business.id):
        special_day.created_at = special_day.updated_at = now
        testbed.exception_repo.save(special_day)

    return testbed.business(business.id)


def apply(testbed: AssemblyTestbed, business: BusinessDocument) -> ApplyChangesView:
    """The owner presses "Apply changes"."""

    testbed.advance(60)
    return testbed.apply_changes_orchestrator.execute(
        ApplyChangesCommand(user_id=testbed.owner_id, business_id=business.id)
    )


def progress(
    testbed: AssemblyTestbed,
    business: BusinessDocument,
    language: str | None = None,
) -> ApplyChangesView:
    return testbed.get_apply_use_case.run(
        ApplyChangesQuery(
            user_id=testbed.owner_id,
            business_id=business.id,
            language=None if language is None else LanguageTag(language),
        )
    )


def stored_apply(
    testbed: AssemblyTestbed,
    business: BusinessDocument,
) -> AssistantApplyDocument:
    stored = testbed.apply_repo.get_by_business(business.id)
    assert stored is not None
    return stored


def attention_codes(view: ApplyChangesView) -> list[ApplyAttentionCode]:
    return [reason.code for reason in view.attention]


def assert_needs_attention(
    view: ApplyChangesView,
    *codes: ApplyAttentionCode,
) -> None:
    assert view.stage is ApplyChangesStage.NEEDS_ATTENTION, view
    assert view.is_in_progress is False
    assert view.finished_at is not None
    assert attention_codes(view) == list(codes)
