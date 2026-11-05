"""
A manager's WhatsApp or SMS number is also where calls may be put through
(a transfer, the fallback dial), so it is refused when it is saved if calls
may not go to it (`find_transfer_refusal`), with the field named, as the
profile's handoff phone is; nothing of the change is stored.
"""

import pytest

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.dto.businesses import BusinessSettingsChanges
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.strings import BusinessName
from app.utilities.channels.transfer_destinations import (
    COUNTRY_REASON,
    REFUSED_RANGE_REASON,
)
from tests.businesses.business_settings_steps import (
    contact,
    georgian_restaurant,
    update,
)
from tests.users.accounts_testbed import build_accounts_testbed


@pytest.mark.parametrize(
    ("channel", "phone_number", "reason"),
    [
        # Italian premium-rate and special numbers.
        (ManagerContactChannel.SMS, "+39 899 123456", REFUSED_RANGE_REASON),
        (ManagerContactChannel.WHATSAPP, "+39 178 1234567", REFUSED_RANGE_REASON),
        # A mobile outside Georgia (the business's country) and the EU.
        (ManagerContactChannel.WHATSAPP, "+44 7911 123456", COUNTRY_REASON),
    ],
)
def test_a_number_calls_may_not_go_to_is_refused(
    channel: ManagerContactChannel, phone_number: str, reason: str
) -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)

    with pytest.raises(ValidationFailedError) as refused:
        update(
            testbed,
            owner_id,
            business.id,
            BusinessSettingsChanges(
                name=BusinessName("Should not be saved"),
                manager_contacts=[
                    contact(ManagerContactChannel.TELEGRAM, "123456789"),
                    contact(channel, phone_number),
                ],
            ),
        )

    assert str(refused.value) == f"manager_contacts[1].address: {reason}"
    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    assert stored.name == "Sakhli"
    assert stored.manager_contacts == []
    assert testbed.audit_log_repo.list_by_business(business.id) == []


@pytest.mark.parametrize(
    "phone_number",
    [
        "599 12 34 56",  # a Georgian mobile, read in the business's country
        "+4915123456789",  # a German mobile (EU)
        "+393471234567",  # an Italian mobile (EU)
    ],
)
def test_mobiles_of_the_country_and_the_eu_are_kept(phone_number: str) -> None:
    testbed = build_accounts_testbed()
    owner_id, business = georgian_restaurant(testbed)

    updated = update(
        testbed,
        owner_id,
        business.id,
        BusinessSettingsChanges(
            manager_contacts=[
                contact(ManagerContactChannel.SMS, phone_number),
                contact(ManagerContactChannel.WHATSAPP, phone_number),
            ]
        ),
    )

    assert [manager.channel for manager in updated.manager_contacts] == [
        ManagerContactChannel.SMS,
        ManagerContactChannel.WHATSAPP,
    ]
