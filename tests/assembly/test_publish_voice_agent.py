"""
The voice agent on publish: built, reused, removed, failing and transferring calls.
"""

import pytest

from app.schemas.constants.assistants import AssistantToolName, AssistantVersionStatus
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.dto.voice import VoiceAgentSpec
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.use_cases.assistants.resume_assistant_use_case import ResumeAssistantUseCase
from app.use_cases.voice.remove_voice_agent_use_case import RemoveVoiceAgentUseCase
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.international_business_seeds import (
    seed_israeli_clinic,
    seed_italian_restaurant,
)
from tests.assembly.publish_helpers import (
    assert_nothing_went_live,
    ready_version,
    reason_codes,
    rollback,
)
from tests.assembly.testbed import AssemblyTestbed


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
    # The agent speaks from the phone instruction of the same version.
    assert spec.prompt_text == version.phone_prompt_text
    assert "https://" not in str(spec.prompt_text)
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
    assert specs[2].prompt_text == first.phone_prompt_text
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


def test_voice_needs_its_settings_in_production() -> None:
    testbed = AssemblyTestbed(environment={"APP_BASE_URL": "", "APP_ENV": "production"})
    testbed.voice_provisioner.missing_settings = [
        EnvironmentVariableName("ELEVENLABS_API_KEY")
    ]
    business = seed_georgian_restaurant(testbed)
    version = ready_version(testbed, business)

    with pytest.raises(ConflictError, match="APP_BASE_URL, ELEVENLABS_API_KEY") as (
        refused
    ):
        testbed.publish(business.id, version.id)

    assert reason_codes(refused.value) == [
        ("voice_configuration", ["APP_BASE_URL", "ELEVENLABS_API_KEY"])
    ]
    assert testbed.voice_provisioner.specs == []
    assert_nothing_went_live(testbed, business, version)


def test_voice_versions_go_live_without_an_agent_when_development_lacks_voice(
    caplog: pytest.LogCaptureFixture,
) -> None:
    testbed = AssemblyTestbed()
    testbed.voice_provisioner.missing_settings = [
        EnvironmentVariableName("ELEVENLABS_API_KEY"),
        EnvironmentVariableName("ELEVENLABS_WEBHOOK_SECRET"),
    ]
    business = seed_georgian_restaurant(testbed)
    version = ready_version(testbed, business)
    assert version.is_voice_enabled

    published = testbed.publish(business.id, version.id)

    assert published.status is AssistantVersionStatus.PUBLISHED
    assert published.voice_agent_id is None
    assert testbed.voice_provisioner.specs == []
    assert "goes live without a voice agent" in caplog.text


def test_publishing_a_version_without_voice_removes_the_voice_agent() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    with_voice = ready_version(testbed, business)
    testbed.publish(business.id, with_voice.id)
    stored = testbed.business(business.id)
    stored.plan_key = PlanKey.CHAT
    testbed.business_repo.save(stored)
    without_voice = ready_version(testbed, business)
    assert without_voice.is_voice_enabled is False

    testbed.publish(business.id, without_voice.id)

    assert testbed.voice_provisioner.removed_agent_ids == [VoiceAgentId("agent_1")]


def test_resuming_activates_the_published_version_and_its_voice_agent_again() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = ready_version(testbed, business)
    testbed.publish(business.id, version.id)
    paused = testbed.business(business.id)
    paused.status = BusinessStatus.PAUSED
    testbed.business_repo.save(paused)
    RemoveVoiceAgentUseCase(testbed.version_repo, testbed.voice_provisioner).run(
        business.id
    )
    resume = ResumeAssistantUseCase(testbed.version_repo, testbed.activate_use_case)

    resume.run(paused)

    assert paused.status is BusinessStatus.LIVE
    assert testbed.voice_provisioner.removed_agent_ids == [VoiceAgentId("agent_1")]
    assert len(testbed.voice_provisioner.specs) == 2  # the agent set up anew
    assert testbed.business(business.id).status is BusinessStatus.LIVE


def test_a_voice_platform_outage_does_not_block_switching_voice_off() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = ready_version(testbed, business)
    testbed.publish(business.id, version.id)
    unreachable = UnreachableVoicePlatform()

    RemoveVoiceAgentUseCase(testbed.version_repo, unreachable).run(business.id)

    assert unreachable.attempts == [VoiceAgentId("agent_1")]


class UnreachableVoicePlatform:
    def __init__(self) -> None:
        self.attempts: list[VoiceAgentId] = []

    def list_missing_settings(self) -> list[EnvironmentVariableName]:
        return []

    def upsert_agent(self, spec: VoiceAgentSpec) -> VoiceAgentId:
        raise ExternalServiceError(f"down for {spec.business_id}")

    def remove_agent(self, agent_id: VoiceAgentId) -> None:
        self.attempts.append(agent_id)
        raise ExternalServiceError("Voice platform is down.")


def test_the_voice_agent_can_put_callers_through_to_the_handoff_phone() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = ready_version(testbed, business)

    testbed.publish(business.id, version.id)

    [spec] = testbed.voice_provisioner.specs
    assert spec.transfer_phone_number == "+995555123456"


def test_a_version_from_before_the_phone_instruction_keeps_its_chat_instruction() -> (
    None
):
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = ready_version(testbed, business)
    stored = testbed.version(business.id, version.id)
    stored.phone_prompt_text = None
    testbed.version_repo.save(stored)

    testbed.publish(business.id, version.id)

    [spec] = testbed.voice_provisioner.specs
    assert spec.prompt_text == version.prompt_text
