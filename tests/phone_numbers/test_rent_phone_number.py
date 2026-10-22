"""An owner takes a number: purchase, record, phone channel, voice agent."""

import pytest

from app.schemas.constants.analytics import ProductEventName
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.phone_numbers import PhoneNumberStatus
from app.schemas.dto.billing import Money
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    RateLimitedError,
)
from app.schemas.exceptions.phone_number_errors import (
    PhoneNumberPriceChangedError,
    PhoneNumberUnavailableError,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    E164PhoneNumber,
)
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from tests.phone_numbers.phone_world import AUSTIN_NUMBER, PhoneWorld
from tests.phone_numbers.provisioner_fakes import AUSTIN_NUMBERS


def test_the_number_is_bought_recorded_connected_and_audited() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()

    view = world.rent_austin_number(owner, business)

    number = world.rented(business)
    assert number.status is PhoneNumberStatus.ACTIVE
    assert str(number.phone_number) == str(AUSTIN_NUMBER)
    assert int(number.monthly_price_minor) == 500
    assert str(number.currency_code) == "GEL"
    assert int(number.monthly_cost_micro_usd) == 1_150_000
    # The first rental month begins now.
    assert number.billed_until == world.clock.now()
    assert str(view.display_number) == "+1 512-555-0142"
    assert str(view.locality) == "Austin"
    [channel] = world.channel_repo.list_by_business(business.id)
    assert channel.kind is ChannelKind.PHONE
    assert channel.status is ChannelStatus.CONNECTED
    assert str(channel.external_id) == str(AUSTIN_NUMBER)
    entries = world.audit_log_repo.list_by_business(business.id)
    assert {(str(entry.entity), entry.action) for entry in entries} == {
        ("phone_number", AuditAction.CREATE),
        ("channel", AuditAction.CREATE),
    }
    # The carrier was told the business's name, not the owner's.
    assert [str(bought.phone_number) for bought in world.provisioner.bought] == [
        str(AUSTIN_NUMBER)
    ]
    assert world.product_events.named(ProductEventName.CHANNEL_CONNECTED) != []


def test_a_live_business_answers_on_the_new_number_at_once() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    world.publish_voice_agent(business, "agent_0001")

    view = world.rent_austin_number(owner, business)

    [voice_import] = world.provisioner.imports
    assert str(voice_import.agent_id) == "agent_0001"
    assert str(voice_import.label) == "Funicular VR"
    assert view.is_attached is True
    assert str(world.rented(business).attached_agent_id) == "agent_0001"


def test_a_voice_platform_outage_leaves_the_number_rented() -> None:
    world = PhoneWorld()
    world.provisioner.is_import_failing = True
    owner, business = world.owner_and_business()
    world.publish_voice_agent(business)

    view = world.rent_austin_number(owner, business)

    number = world.rented(business)
    assert number.status is PhoneNumberStatus.ACTIVE
    assert number.voice_platform_number_id is None
    assert view.is_attached is False


def test_a_changed_price_is_shown_before_anything_is_bought() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    shown = Money(amount_minor=MoneyAmountMinor(400), currency_code=CurrencyCode("GEL"))

    with pytest.raises(PhoneNumberPriceChangedError) as refusal:
        world.rent_austin_number(owner, business, price=shown)

    assert "now GEL5.00 (it was GEL4.00)" in str(refusal.value)
    assert [str(reason.code) for reason in refusal.value.reasons] == ["price_changed"]
    assert world.provisioner.bought == []
    assert world.phone_number_repo.find_held(business.id) is None


def test_a_number_someone_else_took_is_refused() -> None:
    world = PhoneWorld()
    world.provisioner.taken_numbers.add(str(AUSTIN_NUMBER))
    owner, business = world.owner_and_business()

    with pytest.raises(PhoneNumberUnavailableError) as refusal:
        world.rent_austin_number(owner, business)

    assert [str(reason.code) for reason in refusal.value.reasons] == ["number_taken"]
    assert world.phone_number_repo.find_held(business.id) is None
    assert world.channel_repo.list_by_business(business.id) == []


def test_a_number_another_business_rents_is_refused_before_the_carrier() -> None:
    world = PhoneWorld()
    first_owner, first = world.owner_and_business()
    second_owner, second = world.owner_and_business("second@example.com")
    world.rent_austin_number(first_owner, first)

    with pytest.raises(PhoneNumberUnavailableError):
        world.rent_austin_number(second_owner, second)

    assert len(world.provisioner.bought) == 1


def test_one_number_at_a_time() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    world.rent_austin_number(owner, business)

    with pytest.raises(ConflictError, match="already has a number"):
        world.rent_austin_number(
            owner, business, phone_number=E164PhoneNumber(AUSTIN_NUMBERS[1])
        )

    assert len(world.provisioner.bought) == 1


def test_a_line_connected_with_another_number_is_turned_off_first() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    world.rent_austin_number(owner, business)
    number = world.rented(business)
    world.phone_number_repo.modify(
        business.id,
        number.id,
        lambda stored: stored.model_copy(update={"status": PhoneNumberStatus.RELEASED}),
    )

    with pytest.raises(ConflictError, match="connected with another number"):
        world.rent_austin_number(
            owner, business, phone_number=E164PhoneNumber(AUSTIN_NUMBERS[1])
        )


def test_only_the_owner_takes_a_number() -> None:
    world = PhoneWorld()
    owner = world.add_user(email="owner@example.com", locale="en")
    staff = world.add_user(email="staff@example.com", locale="en")
    business = world.add_business(owner, staff=[staff])

    with pytest.raises(AccessDeniedError):
        world.rent_austin_number(staff, business)


def test_a_server_without_the_carrier_sends_owners_to_the_team() -> None:
    world = PhoneWorld()
    world.provisioner.missing_settings = [EnvironmentVariableName("TWILIO_AUTH_TOKEN")]
    owner, business = world.owner_and_business()

    with pytest.raises(ConflictError, match="send a request"):
        world.rent_austin_number(owner, business)


def test_a_country_that_wants_documents_is_never_bought_directly() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()

    with pytest.raises(ConflictError, match="arranged by the platform team"):
        world.rent_austin_number(
            owner, business, phone_number=E164PhoneNumber("+995322000111")
        )


def test_a_business_takes_three_numbers_a_day() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    for phone_number in AUSTIN_NUMBERS:
        world.rent_austin_number(
            owner, business, phone_number=E164PhoneNumber(phone_number)
        )
        released = world.rented(business)
        world.phone_number_repo.modify(
            business.id,
            released.id,
            lambda stored: stored.model_copy(
                update={"status": PhoneNumberStatus.RELEASED}
            ),
        )
        [channel] = world.channel_repo.list_by_business(business.id)
        channel.status = ChannelStatus.DISABLED
        channel.external_id = None
        world.channel_repo.save(channel)

    with pytest.raises(RateLimitedError):
        world.rent_austin_number(
            owner, business, phone_number=E164PhoneNumber("+15125550199")
        )
