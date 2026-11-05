from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessMember
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.billing.owner_notifications import (
    build_owner_contact,
    notify_business_owners,
)
from tests.billing.billing_settings import GEORGIA, ISRAEL
from tests.billing.billing_testbed import BillingTestbed


def test_every_owner_is_told_and_staff_is_not() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(phone_number="+972502345678", display_name="Dana")
    co_owner = testbed.add_user(email="co@example.co.il")
    staff = testbed.add_user(email="staff@example.co.il")
    business = testbed.add_business(owner, ISRAEL, staff=[staff])
    business.members.append(
        BusinessMember(user_id=co_owner.id, role=BusinessMemberRole.OWNER)
    )
    business.members.append(
        BusinessMember(user_id=UserId(), role=BusinessMemberRole.OWNER)
    )

    delivered = notify_business_owners(
        business,
        testbed.user_repo,
        testbed.notifier,
        MessageText("Payment received"),
    )

    assert delivered == 2
    contacts = [contact for contact, _ in testbed.notifier.sent]
    assert [(contact.channel, str(contact.address)) for contact in contacts] == [
        (ManagerContactChannel.WHATSAPP, "+972502345678"),
        (ManagerContactChannel.EMAIL, "co@example.co.il"),
    ]
    assert [str(contact.name) for contact in contacts] == ["Dana", "Funicular VR"]
    assert {str(contact.language) for contact in contacts} == {"he"}


def test_failed_deliveries_are_not_counted() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.ge")
    business = testbed.add_business(owner, GEORGIA)
    testbed.notifier.is_delivering = False

    assert (
        notify_business_owners(
            business,
            testbed.user_repo,
            testbed.notifier,
            MessageText("Hello"),
        )
        == 0
    )


def test_an_owner_without_contact_details_cannot_be_reached() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.ge")
    business = testbed.add_business(owner, GEORGIA)
    unreachable = owner.model_copy(update={"email": None, "phone_number": None})

    assert build_owner_contact(unreachable, business) is None
