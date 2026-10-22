"""Numbers the platform team arranges: the owner's request and its end."""

import pytest

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.phone_numbers import (
    PhoneNumberRequestStatus,
    PhoneNumberType,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.phone_numbers.phone_line import (
    CancelPhoneNumberRequestCommand,
    PhoneLineQuery,
    PhoneNumberRequestBody,
    PhoneNumberRequestView,
    RequestPhoneNumberCommand,
)
from app.schemas.exceptions.application_errors import AccessDeniedError, NotFoundError
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.telephony.constrained_strings import PhoneNumberCityQuery
from tests.phone_numbers.phone_settings import PLATFORM_TEAM_EMAIL
from tests.phone_numbers.phone_world import PhoneWorld


def ask(
    world: PhoneWorld,
    owner: UserDocument,
    business: BusinessDocument,
    country: str = "GE",
    city: str | None = "Batumi",
) -> PhoneNumberRequestView:
    return world.request_number.run(
        RequestPhoneNumberCommand(
            user_id=owner.id,
            business_id=business.id,
            request=PhoneNumberRequestBody(
                country_code=CountryCode(country),
                number_type=PhoneNumberType.LOCAL,
                city=None if city is None else PhoneNumberCityQuery(city),
            ),
        )
    )


def team_mails(world: PhoneWorld) -> list[str]:
    return [
        str(text)
        for contact, text in world.notifier.sent
        if str(contact.address) == PLATFORM_TEAM_EMAIL
    ]


def test_the_team_hears_of_a_request_once_and_the_card_shows_it() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()

    view = ask(world, owner, business)
    again = ask(world, owner, business, city="Tbilisi")

    assert view.status is PhoneNumberRequestStatus.OPEN
    # Asking again while it is open keeps the request as it was.
    assert str(again.city) == "Batumi"
    [mail] = team_mails(world)
    assert "Phone number requested: Funicular VR" in mail
    assert "A local number in GE, near Batumi" in mail
    assert f"/admin/clients/{business.id}" in mail
    line = world.get_line.run(PhoneLineQuery(user_id=owner.id, business_id=business.id))
    assert line.open_request is not None
    assert str(line.open_request.country_code) == "GE"
    entries = world.audit_log_repo.list_by_business(business.id)
    assert [(str(entry.entity), entry.action) for entry in entries] == [
        ("phone_number_request", AuditAction.CREATE)
    ]


def test_a_cancelled_request_can_be_made_again() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    ask(world, owner, business)

    world.cancel_request.run(
        CancelPhoneNumberRequestCommand(user_id=owner.id, business_id=business.id)
    )
    line = world.get_line.run(PhoneLineQuery(user_id=owner.id, business_id=business.id))
    assert line.open_request is None
    with pytest.raises(NotFoundError):
        world.cancel_request.run(
            CancelPhoneNumberRequestCommand(user_id=owner.id, business_id=business.id)
        )

    world.clock.advance(hours=1)
    reopened = ask(world, owner, business, country="AM", city=None)

    assert reopened.status is PhoneNumberRequestStatus.OPEN
    assert str(reopened.country_code) == "AM"
    assert reopened.city is None
    assert len(team_mails(world)) == 2


def test_only_the_owner_asks() -> None:
    world = PhoneWorld()
    owner = world.add_user(email="owner@example.com", locale="en")
    staff = world.add_user(email="staff@example.com", locale="en")
    business = world.add_business(owner, staff=[staff])

    with pytest.raises(AccessDeniedError):
        ask(world, staff, business)

    assert team_mails(world) == []


def test_the_request_closes_once_the_team_connects_the_number() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    ask(world, owner, business)
    tick = JobTick(
        job_name=JobName("maintain_phone_numbers"), scheduled_at=world.clock.now()
    )

    assert int(world.maintain.run(tick).processed_count) == 0
    world.channel_repo.save(
        ChannelDocument(
            business_id=business.id,
            kind=ChannelKind.PHONE,
            external_id=ChannelExternalId("+995322000111"),
            status=ChannelStatus.CONNECTED,
            created_at=world.clock.now(),
            updated_at=world.clock.now(),
        )
    )

    assert int(world.maintain.run(tick).processed_count) == 1
    request = world.request_repo.get_by_business(business.id)
    assert request is not None
    assert request.status is PhoneNumberRequestStatus.DONE
    assert request.closed_at == world.clock.now()
