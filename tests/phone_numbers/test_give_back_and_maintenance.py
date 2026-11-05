"""A rented number given back, returned to the carrier, kept with its agent."""

import pytest

from app.schemas.constants.channels import ChannelStatus
from app.schemas.constants.phone_numbers import (
    PhoneNumberReleaseReason,
    PhoneNumberStatus,
)
from app.schemas.dto.jobs import JobTick
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.platform.constrained_strings import JobName
from app.utilities.telephony.number_release import mark_releasing
from tests.phone_numbers.phone_line_channels import PhoneLineChannels
from tests.phone_numbers.phone_world import AUSTIN_NUMBER, PhoneWorld


def maintain(world: PhoneWorld) -> int:
    report = world.maintain.run(
        JobTick(
            job_name=JobName("maintain_phone_numbers"),
            scheduled_at=world.clock.now(),
        )
    )
    return int(report.processed_count)


def test_turning_the_phone_channel_off_gives_the_number_back() -> None:
    world = PhoneWorld()
    channels = PhoneLineChannels(world)
    owner, business = world.owner_and_business()
    world.rent_austin_number(owner, business)

    view = channels.turn_phone_off(owner, business)

    assert view.status is ChannelStatus.DISABLED
    number = world.rented(business)
    assert number.status is PhoneNumberStatus.RELEASING
    assert number.release_reason is PhoneNumberReleaseReason.OWNER
    assert number.release_requested_at == world.clock.now()
    assert channels.voice_agent_removals == [business.id]
    # Nothing at the carrier yet: the maintenance job returns it.
    assert world.provisioner.releases == []

    assert maintain(world) == 1
    [release] = world.provisioner.releases
    assert release.provider_number_id == number.provider_number_id
    assert release.voice_platform_number_id == number.voice_platform_number_id
    assert world.phone_number_repo.find_held(business.id) is None
    released = world.phone_number_repo.get(business.id, number.id)
    assert released is not None
    assert released.status is PhoneNumberStatus.RELEASED
    assert released.released_at == world.clock.now()
    assert maintain(world) == 0


def test_giving_back_twice_or_with_nothing_rented_changes_nothing() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    world.give_back.run(business.id)
    assert world.phone_number_repo.find_held(business.id) is None

    world.rent_austin_number(owner, business)
    world.give_back.run(business.id)
    first = world.rented(business)
    world.clock.advance(hours=1)
    world.give_back.run(business.id)

    assert world.rented(business).release_requested_at == first.release_requested_at


def test_a_carrier_outage_keeps_the_number_until_the_next_run() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    world.rent_austin_number(owner, business)
    world.give_back.run(business.id)
    world.provisioner.is_release_failing = True

    assert maintain(world) == 0
    assert world.rented(business).status is PhoneNumberStatus.RELEASING

    world.provisioner.is_release_failing = False
    assert maintain(world) == 1
    assert world.phone_number_repo.find_held(business.id) is None


def test_a_number_nobody_pays_for_also_turns_the_phone_line_off() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    world.rent_austin_number(owner, business)
    number = world.rented(business)
    world.phone_number_repo.modify(
        business.id,
        number.id,
        lambda stored: mark_releasing(
            stored, PhoneNumberReleaseReason.UNPAID, world.clock.now()
        ),
    )

    assert maintain(world) == 1

    [channel] = world.channel_repo.list_by_business(business.id)
    assert channel.status is ChannelStatus.DISABLED
    assert channel.external_id is None


def test_the_number_follows_the_live_voice_agent() -> None:
    world = PhoneWorld()
    world.provisioner.is_import_failing = True
    owner, business = world.owner_and_business()
    world.rent_austin_number(owner, business)
    world.provisioner.is_import_failing = False

    # Imported into the voice platform although nobody answers yet.
    assert maintain(world) == 1
    number = world.rented(business)
    assert number.voice_platform_number_id is not None
    assert number.attached_agent_id is None
    assert maintain(world) == 0

    world.publish_voice_agent(business, "agent_0002")
    assert maintain(world) == 1
    assert str(world.rented(business).attached_agent_id) == "agent_0002"
    assert (
        str(world.provisioner.assignments[str(number.voice_platform_number_id)])
        == "agent_0002"
    )
    assert maintain(world) == 0


def test_another_number_is_refused_while_one_is_rented() -> None:
    world = PhoneWorld()
    channels = PhoneLineChannels(world)
    owner, business = world.owner_and_business()
    world.rent_austin_number(owner, business)

    with pytest.raises(ConflictError, match="rents a number from us"):
        channels.connect_phone(owner, business, "+995322000111")
    # The rented number itself reconnects (after a manual switch-off).
    view = channels.connect_phone(owner, business, str(AUSTIN_NUMBER))
    assert view.status is ChannelStatus.CONNECTED

    channels.turn_phone_off(owner, business)
    view = channels.connect_phone(owner, business, "+995322000111")
    assert view.status is ChannelStatus.CONNECTED
