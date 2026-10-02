"""
Setting up the voice agent takes seconds; a business save made meanwhile
(another owner, a manager linking the platform bot, billing) is never
overwritten by publishing or by resuming from the settings.
"""

import pytest

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.dto.assistants.assistant_views import AssistantVersionDetails
from app.schemas.dto.businesses import (
    BusinessSettingsChanges,
    ManagerContactInput,
    UpdateBusinessSettingsCommand,
)
from app.schemas.dto.voice import VoiceAgentSpec
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.businesses.strings import (
    BusinessName,
    RawManagerContactAddress,
)
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.businesses.business_view_transformer import (
    BusinessViewTransformer,
)
from app.use_cases.assistants.resume_assistant_use_case import ResumeAssistantUseCase
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.businesses.update_business_settings_use_case import (
    UpdateBusinessSettingsUseCase,
)
from app.use_cases.voice.remove_voice_agent_use_case import RemoveVoiceAgentUseCase
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.testbed import AssemblyTestbed
from tests.users.accounts_testbed import PhonenumbersParser

LEVAN = ManagerContact(
    name=ManagerName("Levan"),
    channel=ManagerContactChannel.TELEGRAM,
    address=ManagerContactAddress("777000111"),
    language=LanguageTag("ka"),
)


def ready_version(
    testbed: AssemblyTestbed,
    business: BusinessDocument,
) -> AssistantVersionDetails:
    version = testbed.assemble(business.id, run_autotests=True)
    assert version.status is AssistantVersionStatus.READY
    return version


def add_contact_while_the_agent_is_set_up(testbed: AssemblyTestbed) -> list[int]:
    """
    Co-owner B saves a new manager contact (a conditional save that
    succeeds) while the voice agent is being set up; returns B's revisions.
    """

    provisioner = testbed.voice_provisioner
    upsert_agent = provisioner.upsert_agent
    saved_revisions: list[int] = []

    def upsert_while_someone_saves(spec: VoiceAgentSpec) -> VoiceAgentId:
        meanwhile = testbed.business(spec.business_id)
        meanwhile.manager_contacts = [*meanwhile.manager_contacts, LEVAN]
        assert testbed.business_repo.save_if_unchanged(meanwhile)
        saved_revisions.append(int(meanwhile.revision))
        return upsert_agent(spec)

    provisioner.upsert_agent = upsert_while_someone_saves  # type: ignore[method-assign]
    return saved_revisions


def build_settings(testbed: AssemblyTestbed) -> UpdateBusinessSettingsUseCase:
    return UpdateBusinessSettingsUseCase(
        authorize_business_access=AuthorizeBusinessAccessUseCase(
            testbed.business_repo,
            testbed.user_repo,
            testbed.audit_repo,
            testbed.wall_clock,
        ),
        business_repo=testbed.business_repo,
        user_repo=testbed.user_repo,
        subscription_repo=testbed.subscription_repo,
        language_registry=testbed.language_registry,
        phone_number_parser=PhonenumbersParser(),
        audit_log_repo=testbed.audit_repo,
        business_view_transformer=BusinessViewTransformer(),
        wall_clock=testbed.wall_clock,
        remove_voice_agent=RemoveVoiceAgentUseCase(
            testbed.version_repo,
            testbed.voice_provisioner,
        ),
        resume_assistant=ResumeAssistantUseCase(
            testbed.version_repo,
            testbed.activate_use_case,
        ),
    )


def published_and_paused(testbed: AssemblyTestbed) -> BusinessDocument:
    business = seed_georgian_restaurant(testbed)
    version = ready_version(testbed, business)
    testbed.publish(business.id, version.id)
    paused = testbed.business(business.id)
    paused.status = BusinessStatus.PAUSED
    testbed.business_repo.save(paused)
    RemoveVoiceAgentUseCase(testbed.version_repo, testbed.voice_provisioner).run(
        business.id
    )
    return paused


def test_a_save_during_publishing_is_kept_and_the_business_goes_live() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    version = ready_version(testbed, business)
    contacts_before = list(testbed.business(business.id).manager_contacts)
    saved_revisions = add_contact_while_the_agent_is_set_up(testbed)

    testbed.publish(business.id, version.id)

    stored = testbed.business(business.id)
    assert stored.manager_contacts == [*contacts_before, LEVAN]
    assert stored.status is BusinessStatus.LIVE
    assert stored.published_assistant_version_id == version.id
    # Publishing wrote after B, from B's business: one revision more.
    assert int(stored.revision) == saved_revisions[-1] + 1
    assert testbed.version(business.id, version.id).status is (
        AssistantVersionStatus.PUBLISHED
    )


def test_a_save_during_resume_provisioning_is_not_overwritten() -> None:
    testbed = AssemblyTestbed()
    paused = published_and_paused(testbed)
    published_id = paused.published_assistant_version_id
    assert published_id is not None
    add_contact_while_the_agent_is_set_up(testbed)

    with pytest.raises(ConflictError, match="saved by someone else"):
        build_settings(testbed).run(
            UpdateBusinessSettingsCommand(
                user_id=testbed.owner_id,
                business_id=paused.id,
                changes=BusinessSettingsChanges(
                    expected_revision=paused.revision,
                    status=BusinessStatus.LIVE,
                    name=BusinessName("Owner A rename"),
                ),
            )
        )

    stored = testbed.business(paused.id)
    assert LEVAN in stored.manager_contacts
    assert stored.name == paused.name
    assert stored.status is BusinessStatus.PAUSED
    # The refused activation published nothing: the version stays as it was.
    assert testbed.version(paused.id, published_id).status is (
        AssistantVersionStatus.PUBLISHED
    )


def test_a_resume_with_invalid_contacts_changes_nothing() -> None:
    testbed = AssemblyTestbed()
    paused = published_and_paused(testbed)
    specs_before = len(testbed.voice_provisioner.specs)

    with pytest.raises(ValidationFailedError):
        build_settings(testbed).run(
            UpdateBusinessSettingsCommand(
                user_id=testbed.owner_id,
                business_id=paused.id,
                changes=BusinessSettingsChanges(
                    status=BusinessStatus.LIVE,
                    name=BusinessName("Renamed"),
                    manager_contacts=[
                        ManagerContactInput(
                            name=ManagerName("Nino"),
                            channel=ManagerContactChannel.TELEGRAM,
                            address=RawManagerContactAddress("not-a-chat-id"),
                        )
                    ],
                ),
            )
        )

    stored = testbed.business(paused.id)
    assert stored.status is BusinessStatus.PAUSED
    assert stored.name == paused.name
    # No voice agent was set up for the refused change.
    assert len(testbed.voice_provisioner.specs) == specs_before


def test_resuming_from_the_settings_saves_the_other_changes_with_it() -> None:
    testbed = AssemblyTestbed()
    paused = published_and_paused(testbed)

    resumed = build_settings(testbed).run(
        UpdateBusinessSettingsCommand(
            user_id=testbed.owner_id,
            business_id=paused.id,
            changes=BusinessSettingsChanges(
                expected_revision=paused.revision,
                status=BusinessStatus.LIVE,
                name=BusinessName("Back again"),
            ),
        )
    )

    stored = testbed.business(paused.id)
    assert (stored.status, stored.name) == (BusinessStatus.LIVE, "Back again")
    assert resumed.revision == stored.revision == int(paused.revision) + 1
