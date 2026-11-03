"""
A change of the pages guests pay deposits on reaches every owner at the
e-mail address of their account too (PAY-06), in their language, with a
signed link to Account → Security: an owner without a device or a staff
contact is still told. An address a staff contact already gets the alert
at is not mailed twice, owners who sign in by phone have no address, and
staff are never mailed this way. Every change is audited.
"""

from app.facilitators.notifications.owner_account_email_facilitator import (
    OwnerAccountEmailFacilitator,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.deposits import PaymentLinkKind
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import BusinessMember, ManagerContact
from app.schemas.domain.users import UserDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.deposits.deposit_settings import (
    AddPaymentLinkCommand,
    PaymentLinkInput,
)
from app.schemas.typings.deposits.constrained_strings import (
    PaymentLinkAddressInput,
    PaymentLinkLabel,
)
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.transformers.notifications.staff_notification_text_transformer import (
    StaffNotificationTextTransformer,
)
from app.use_cases.deposits.add_payment_link_use_case import AddPaymentLinkUseCase
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from tests.billing.billing_fakes import RecordingNotifier
from tests.deposits.deposit_owner_actions import owner_changes
from tests.deposits.deposit_world import DepositWorld

CABINET: str = "https://app.example.com"
PAGE: str = "https://pay.example.org/deposit?sum={amount}&ref={reference}"


def add_member(
    world: DepositWorld,
    role: BusinessMemberRole,
    email: str | None = None,
    locale: str = "en",
) -> UserDocument:
    user = UserDocument(
        login_method=LoginMethod.EMAIL if email else LoginMethod.PHONE,
        email=None if email is None else EmailAddress(email),
        phone_number=None if email else E164PhoneNumber("+393331112233"),
        locale=LanguageTag(locale),
        is_verified=True,
    )
    world.user_repo.save(user)
    world.business.members.append(BusinessMember(user_id=user.id, role=role))
    world.business_repo.save(world.business)
    return user


def mailer(
    world: DepositWorld, notifier: RecordingNotifier
) -> OwnerAccountEmailFacilitator:
    resolver = LocalizedTextResolver()
    return OwnerAccountEmailFacilitator(
        user_repo=world.user_repo,
        manager_notifier=notifier,
        link_signer=StaffLinkSigner(PlatformSecret("test-link-key-0000")),
        text_transformer=StaffNotificationTextTransformer(resolver),
        cabinet_base_url=CabinetBaseUrl(CABINET),
        wall_clock=world.clock.wall_clock,
    )


def add_page(world: DepositWorld, notifier: RecordingNotifier) -> None:
    changes = owner_changes(world, owner_emails=mailer(world, notifier))
    AddPaymentLinkUseCase(changes, world.cipher).run(
        AddPaymentLinkCommand(
            user_id=world.owner_id,
            business_id=world.business.id,
            link=PaymentLinkInput(
                label=PaymentLinkLabel("Satispay"),
                kind=PaymentLinkKind.TEMPLATE,
                address=PaymentLinkAddressInput(PAGE),
            ),
        )
    )


def test_every_owner_hears_of_a_new_page_at_their_account_email() -> None:
    world = DepositWorld()
    world.take_deposits()
    italian = add_member(world, BusinessMemberRole.OWNER, "giulia@example.it", "it")
    english = add_member(world, BusinessMemberRole.OWNER, "tom@example.com")
    add_member(world, BusinessMemberRole.OWNER)  # signs in by phone
    add_member(world, BusinessMemberRole.STAFF, "waiter@example.com")
    notifier = RecordingNotifier()

    add_page(world, notifier)

    sent = {
        str(contact.address): (contact, str(text)) for contact, text in notifier.sent
    }
    assert set(sent) == {str(italian.email), str(english.email)}
    contact, text = sent[str(italian.email)]
    assert contact.channel is ManagerContactChannel.EMAIL
    assert contact.language == LanguageTag("it")
    assert "Pagine di pagamento delle caparre modificate" in text
    assert "Pagina di pagamento aggiunta: pay.example.org" in text
    assert f"{CABINET}/n/" in text
    _, english_text = sent[str(english.email)]
    assert "Payment page added: pay.example.org" in english_text
    assert "end unknown sessions in Account → Security" in english_text


def test_an_address_a_staff_contact_already_gets_is_not_mailed_twice() -> None:
    world = DepositWorld()
    world.take_deposits()
    owner = add_member(world, BusinessMemberRole.OWNER, "owner@example.com")
    world.business.manager_contacts.append(
        ManagerContact(
            name=ManagerName("Owner"),
            channel=ManagerContactChannel.EMAIL,
            address=ManagerContactAddress("Owner@Example.com"),
            language=LanguageTag("en"),
        )
    )
    world.business_repo.save(world.business)
    notifier = RecordingNotifier()

    add_page(world, notifier)

    assert str(owner.email) not in {
        str(contact.address) for contact, _ in notifier.sent
    }


def test_a_page_change_is_audited_as_a_deposit_settings_update() -> None:
    world = DepositWorld()
    world.take_deposits()
    before = len(world.audit_repo.list_by_business(world.business.id))

    add_page(world, RecordingNotifier())

    entries = world.audit_repo.list_by_business(world.business.id)[before:]
    assert [(entry.action, str(entry.entity), entry.actor_id) for entry in entries] == [
        (AuditAction.UPDATE, "deposit_settings", world.owner_id)
    ]


class FailingFor(RecordingNotifier):
    def __init__(self, address: str) -> None:
        super().__init__()
        self.address: str = address

    def notify(self, notification: StaffNotification) -> bool:
        if str(notification.contact.address) == self.address:
            raise RuntimeError("outbox down")

        return super().notify(notification)


def test_one_failing_owner_never_stops_the_others() -> None:
    world = DepositWorld()
    world.take_deposits()
    add_member(world, BusinessMemberRole.OWNER, "first@example.com")
    second = add_member(world, BusinessMemberRole.OWNER, "second@example.com")
    notifier = FailingFor("first@example.com")

    add_page(world, notifier)

    assert [str(contact.address) for contact, _ in notifier.sent] == [str(second.email)]
