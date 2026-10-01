import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName, AssistantVersionStatus
from app.schemas.constants.billing import PlanKey, SubscriptionStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants import (
    AssistantVersionDetails,
    PublishAssistantVersionCommand,
    RollbackAssistantVersionCommand,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.assembly.builders import (
    make_launch_ready,
    seed_georgian_restaurant,
    seed_israeli_clinic,
    seed_italian_restaurant,
    seed_online_shop,
)
from tests.assembly.testbed import AssemblyTestbed


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
    admin_id = testbed.add_platform_admin()
    if make_failed:
        testbed.judge_raw_answers["booking__it"] = "unreadable"
        version = testbed.assemble(business.id, run_autotests=True)
        assert version.status is AssistantVersionStatus.TESTS_FAILED
    else:
        version = testbed.assemble(business.id)
        assert version.status is AssistantVersionStatus.DRAFT

    with pytest.raises(ConflictError, match="has not passed the autotests"):
        testbed.publish(business.id, version.id)

    # "A broken version does not reach customers": the owner cannot force it.
    with pytest.raises(AccessDeniedError, match="platform admin"):
        testbed.publish(business.id, version.id, accept_failed_tests=True)

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

    with pytest.raises(ConflictError, match="already live"):
        testbed.publish(business.id, second.id)

    with pytest.raises(ConflictError, match="rollback"):
        testbed.publish(business.id, first.id, accept_failed_tests=True)

    with pytest.raises(ConflictError, match="being tested"):
        testbed.publish(business.id, third.id, accept_failed_tests=True)


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


def test_chat_plan_publishes_without_a_voice_agent() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    version = ready_version(testbed, business)

    published = testbed.publish(business.id, version.id)

    assert version.is_voice_enabled is False
    assert published.voice_agent_id is None
    assert testbed.voice_provisioner.specs == []
    assert testbed.call_greeting.requests == []


def test_voice_agent_is_built_from_the_same_version() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = ready_version(testbed, business)

    published = testbed.publish(business.id, version.id)

    assert published.voice_agent_id == VoiceAgentId("agent_1")
    assert testbed.version(business.id, version.id).voice_agent_id == "agent_1"
    [spec] = testbed.voice_provisioner.specs
    assert spec.business_id == business.id
    assert spec.existing_agent_id is None
    assert spec.business_name == "Café Rustaveli"
    assert spec.prompt_text == version.prompt_text
    assert spec.languages == [LanguageTag("ka"), LanguageTag("ru"), LanguageTag("en")]
    assert spec.default_language == LanguageTag("ka")
    assert [greeting.language for greeting in spec.greetings] == spec.languages
    assert str(spec.greetings[0].text).startswith("[ka] AI assistant here")
    assert [tool.name for tool in spec.tools] == list(AssistantToolName)
    assert spec.tool_webhook_base_url == "https://api.example.com"
    assert [str(request.language) for request in testbed.call_greeting.requests] == [
        "ka",
        "ru",
        "en",
    ]


def test_later_versions_and_rollbacks_reuse_the_voice_agent() -> None:
    testbed = AssemblyTestbed()
    business = seed_israeli_clinic(testbed)
    first = ready_version(testbed, business)
    testbed.publish(business.id, first.id)
    second = ready_version(testbed, business)

    testbed.publish(business.id, second.id)
    rolled_back = rollback(testbed, business, first.id)

    specs = testbed.voice_provisioner.specs
    assert [spec.existing_agent_id for spec in specs] == [
        None,
        VoiceAgentId("agent_1"),
        VoiceAgentId("agent_1"),
    ]
    assert rolled_back.voice_agent_id == VoiceAgentId("agent_1")
    assert specs[2].prompt_text == first.prompt_text
    assert [greeting.language for greeting in specs[0].greetings] == [
        LanguageTag("he"),
        LanguageTag("ar"),
        LanguageTag("en"),
    ]


def test_voice_failure_publishes_nothing() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    first = ready_version(testbed, business)
    testbed.publish(business.id, first.id)
    second = ready_version(testbed, business)
    testbed.voice_provisioner.error = ExternalServiceError("ElevenLabs is down.")

    with pytest.raises(ExternalServiceError, match="ElevenLabs is down"):
        testbed.publish(business.id, second.id)

    assert testbed.version(business.id, first.id).status is (
        AssistantVersionStatus.PUBLISHED
    )
    stored_second = testbed.version(business.id, second.id)
    assert stored_second.status is AssistantVersionStatus.READY
    assert stored_second.published_at is None
    assert testbed.business(business.id).published_assistant_version_id == first.id


def test_greeting_failure_is_reported_as_a_voice_failure() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    version = ready_version(testbed, business)
    testbed.call_greeting.error = NotFoundError("Greeting texts are missing.")

    with pytest.raises(ExternalServiceError, match="Greeting texts are missing"):
        testbed.publish(business.id, version.id)

    assert testbed.voice_provisioner.specs == []
    assert testbed.business(business.id).status is BusinessStatus.TESTING
    assert testbed.version(business.id, version.id).status is (
        AssistantVersionStatus.READY
    )


def test_voice_needs_a_public_base_url() -> None:
    testbed = AssemblyTestbed(environment={"APP_BASE_URL": ""})
    business = seed_georgian_restaurant(testbed)
    version = ready_version(testbed, business)

    with pytest.raises(ExternalServiceError, match="APP_BASE_URL"):
        testbed.publish(business.id, version.id)

    assert testbed.voice_provisioner.specs == []


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

    with pytest.raises(ConflictError, match="is published"):
        rollback(testbed, business, first.id)

    with pytest.raises(ConflictError, match="is draft"):
        rollback(testbed, business, draft.id)

    with pytest.raises(AccessDeniedError):
        rollback(testbed, business, first.id, as_staff=True)

    with pytest.raises(NotFoundError):
        rollback(testbed, business, AssistantVersionId())


def test_paused_business_goes_live_again_on_publish() -> None:
    testbed = AssemblyTestbed()
    business = seed_online_shop(testbed)
    stored = testbed.business(business.id)
    stored.status = BusinessStatus.PAUSED
    testbed.business_repo.save(stored)
    version = ready_version(testbed, business)

    testbed.publish(business.id, version.id)

    assert testbed.business(business.id).status is BusinessStatus.LIVE


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


def test_going_live_needs_a_running_trial_or_a_paid_subscription() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    subscription = only_subscription(testbed, business)
    version = ready_version(testbed, business)
    trial_end = subscription.trial_ends_at
    assert trial_end is not None
    subscription.trial_ends_at = testbed.wall_clock.now_unix()
    testbed.subscription_repo.save(subscription)

    with pytest.raises(ConflictError, match="start the trial or pay"):
        testbed.publish(business.id, version.id)

    assert_nothing_went_live(testbed, business, version)
    subscription.status = SubscriptionStatus.PAST_DUE
    subscription.grace_until = testbed.wall_clock.now_unix()
    testbed.subscription_repo.save(subscription)
    with pytest.raises(ConflictError, match="start the trial or pay"):
        testbed.publish(business.id, version.id)

    subscription.status = SubscriptionStatus.CANCELLED
    subscription.period_end = Microseconds(
        int(testbed.wall_clock.now_unix()) + 3_600_000_000
    )
    testbed.subscription_repo.save(subscription)
    published = testbed.publish(business.id, version.id)  # paid until period end
    assert published.status is AssistantVersionStatus.PUBLISHED


def test_a_business_that_never_started_the_trial_cannot_go_live() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed, is_launch_ready=False)
    version = ready_version(testbed, business)

    with pytest.raises(ConflictError) as refused:
        testbed.publish(business.id, version.id)

    message = str(refused.value)
    assert "start the trial or pay for the subscription" in message
    assert "accept the data processing agreement (version 2026-10-01)" in message
    assert "no_handoff_contact" in message
    assert_nothing_went_live(testbed, business, version)
    make_launch_ready(testbed, business)
    published = testbed.publish(business.id, version.id)
    assert published.status is AssistantVersionStatus.PUBLISHED


def test_going_live_needs_the_current_dpa() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    version = ready_version(testbed, business)
    for acceptance in testbed.dpa_repo.list_by_business(business.id):
        acceptance.document_version = DpaDocumentVersion("2025-01-01")
        testbed.dpa_repo.save(acceptance)

    with pytest.raises(ConflictError, match="data processing agreement"):
        testbed.publish(business.id, version.id)

    assert_nothing_went_live(testbed, business, version)


def test_going_live_needs_a_manager_contact_and_no_blocking_gap() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    version = ready_version(testbed, business)
    stored = testbed.business(business.id)
    stored.manager_contacts = []
    testbed.business_repo.save(stored)
    profile = testbed.profile_repo.get_by_business(business.id)
    assert profile is not None
    profile.hours = []
    testbed.profile_repo.save(profile)

    with pytest.raises(
        ConflictError,
        match=r"complete the profile \(see what to add: no_opening_hours, "
        r"no_handoff_contact\)",
    ):
        testbed.publish(business.id, version.id)

    assert_nothing_went_live(testbed, business, version)


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

    with pytest.raises(ConflictError, match="start the trial or pay"):
        rollback(testbed, business, first.id)

    assert testbed.business(business.id).published_assistant_version_id == second.id
    assert testbed.version(business.id, first.id).status is (
        AssistantVersionStatus.ARCHIVED
    )
