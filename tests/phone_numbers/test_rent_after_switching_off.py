"""
Switching the phone channel off removes the voice agent; a number taken
afterwards must not be attached to that deleted agent, and it follows the
new agent once a voice version is published again.
"""

from app.schemas.constants.phone_numbers import PhoneNumberStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.phone_numbers.phone_line import (
    PhoneLineQuery,
    RentedPhoneNumberView,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.constrained_strings import JobName
from tests.assembly.fake_engine_and_voice import FakeVoiceAgentProvisioner
from tests.phone_numbers.phone_line_channels import PhoneLineChannels
from tests.phone_numbers.phone_world import PhoneWorld
from tests.phone_numbers.provisioner_fakes import AUSTIN_NUMBERS


def maintain(world: PhoneWorld) -> int:
    report = world.maintain.run(
        JobTick(
            job_name=JobName("maintain_phone_numbers"),
            scheduled_at=world.clock.now(),
        )
    )
    return int(report.processed_count)


def card(
    world: PhoneWorld, owner: UserDocument, business: BusinessDocument
) -> RentedPhoneNumberView:
    line = world.get_line.run(PhoneLineQuery(user_id=owner.id, business_id=business.id))
    assert line.rented_number is not None
    return line.rented_number


def test_a_number_taken_after_switching_off_does_not_name_the_deleted_agent() -> None:
    world = PhoneWorld()
    voice_agents = FakeVoiceAgentProvisioner()
    channels = PhoneLineChannels(world, voice_agents)
    owner, business = world.owner_and_business()
    world.publish_voice_agent(business, "agent_live")
    world.rent_austin_number(owner, business)
    assert card(world, owner, business).has_answering_agent is True

    channels.turn_phone_off(owner, business)
    assert voice_agents.removed_agent_ids == [VoiceAgentId("agent_live")]
    assert maintain(world) == 1
    world.clock.advance(hours=1)
    world.rent_austin_number(
        owner, business, phone_number=E164PhoneNumber(AUSTIN_NUMBERS[1])
    )

    second = world.rented(business)
    assert second.status is PhoneNumberStatus.ACTIVE
    assert second.attached_agent_id is None
    assert world.provisioner.imports[-1].agent_id is None
    assert all(
        version.voice_agent_id is None
        for version in world.assistant_version_repo.list_by_business(business.id)
    )
    # The card says it waits for a publish, not that it answers.
    assert card(world, owner, business).is_attached is False
    assert card(world, owner, business).has_answering_agent is False

    # Publishing voice again sets up a new agent; the number follows it.
    [version] = world.assistant_version_repo.list_by_business(business.id)
    world.assistant_version_repo.modify(
        business.id,
        version.id,
        lambda stored: stored.model_copy(
            update={"voice_agent_id": VoiceAgentId("agent_new")}
        ),
    )
    assert maintain(world) == 1
    assert str(world.rented(business).attached_agent_id) == "agent_new"
    assert card(world, owner, business).has_answering_agent is True
    assert card(world, owner, business).is_attached is True
