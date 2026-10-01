import pytest

from app.schemas.constants.assistants import AssistantToolName, AssistantVersionStatus
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessStatus
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
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.assembly.builders import (
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
def test_untested_or_failed_versions_need_explicit_acceptance(
    make_failed: bool,
) -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    if make_failed:
        testbed.judge_raw_answers["booking__it"] = "unreadable"
        version = testbed.assemble(business.id, run_autotests=True)
        assert version.status is AssistantVersionStatus.TESTS_FAILED
    else:
        version = testbed.assemble(business.id)
        assert version.status is AssistantVersionStatus.DRAFT

    with pytest.raises(ConflictError, match="accept_failed_tests"):
        testbed.publish(business.id, version.id)

    assert testbed.business(business.id).status is BusinessStatus.TESTING
    published = testbed.publish(business.id, version.id, accept_failed_tests=True)
    assert published.status is AssistantVersionStatus.PUBLISHED


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
