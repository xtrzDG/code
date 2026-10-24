"""Telegram staff contacts: the @username from the bot, choices kept on relink."""

import pytest

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffAlertEvent
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.notification_preferences import (
    QuietHours,
    StaffNotificationPreferences,
)
from app.schemas.dto.businesses import BusinessSettingsChanges
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_strings import LocalTimeOfDay
from app.schemas.typings.handoffs.constrained_strings import ManagerTelegramUsername
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.businesses.business_settings_steps import (
    contact,
    georgian_restaurant,
    update,
)
from tests.channels.platform_bot_setup import PlatformBotSetup
from tests.users.accounts_testbed import build_accounts_testbed


def test_linking_keeps_the_username_and_relinking_keeps_the_choices() -> None:
    setup = PlatformBotSetup()
    code = setup.create_link({"name": "Nino"}).json()["code"]

    setup.send_to_bot(f"/start {code}", username="nino_salobie")

    [linked] = setup.stored_business().manager_contacts
    assert linked.telegram_username == "nino_salobie"
    assert linked.preferences is None

    lead_only = StaffNotificationPreferences(events=[StaffAlertEvent.LEAD])
    business = setup.stored_business()
    business.manager_contacts = [linked.model_copy(update={"preferences": lead_only})]
    setup.testbed.business_repo.save(business)
    second_code = setup.create_link({"name": "Nino B."}).json()["code"]

    setup.send_to_bot(f"/start {second_code}", username="@bad name")

    [relinked] = setup.stored_business().manager_contacts
    assert relinked.name == "Nino B."
    assert relinked.preferences == lead_only
    assert relinked.telegram_username is None


def test_settings_keep_the_linked_username_and_check_the_quiet_hours() -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)
    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    stored.manager_contacts = [
        ManagerContact(
            name=ManagerName("Nino"),
            channel=ManagerContactChannel.TELEGRAM,
            address=ManagerContactAddress("31337"),
            language=LanguageTag("ka"),
            telegram_username=ManagerTelegramUsername("nino_salobie"),
        )
    ]
    testbed.business_repo.save(stored)
    night = StaffNotificationPreferences(
        events=[StaffAlertEvent.HANDOFF],
        quiet_hours=QuietHours(
            starts_at=LocalTimeOfDay("23:00"), ends_at=LocalTimeOfDay("07:30")
        ),
    )
    nino = contact(ManagerContactChannel.TELEGRAM, "31337")

    updated = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(
            manager_contacts=[nino.model_copy(update={"preferences": night})]
        ),
    )

    [view] = updated.manager_contacts
    assert view.telegram_username == "nino_salobie"
    assert view.preferences == night
    endless = StaffNotificationPreferences(
        quiet_hours=QuietHours(
            starts_at=LocalTimeOfDay("09:00"), ends_at=LocalTimeOfDay("09:00")
        )
    )
    with pytest.raises(ValidationFailedError):
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(
                manager_contacts=[nino.model_copy(update={"preferences": endless})]
            ),
        )
