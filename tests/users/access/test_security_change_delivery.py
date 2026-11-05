"""
How a second-factor change reaches its person: a personal, urgent alert on
their devices (no staff contact hears it) and an e-mail when they sign in
by e-mail, in their language, linking to Account → Security. An unknown
person, or a facilitator built without the people's store, tells nobody
and never raises.
"""

from datetime import timedelta

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.users.sign_in_notice_facilitator import SignInNoticeFacilitator
from app.repositories.business_repositories import BusinessRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.mfa import SecurityChange
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import StaffLinkToken
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.transformers.notifications.staff_notification_text_transformer import (
    StaffNotificationTextTransformer,
)
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from tests.notifications.alert_world import NOON, AlertWorld
from tests.notifications.staff_alert_fakes import TEST_ENCRYPTION_KEY
from tests.operations.fakes import FakeLocalizedTextResolver

CAFE_IP: ClientIpAddress = ClientIpAddress("203.0.113.7")


def build_notices(
    world: AlertWorld, users: UserRepository | None
) -> SignInNoticeFacilitator:
    businesses = BusinessRepository(
        InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
    )
    businesses.save(world.business)
    resolver = FakeLocalizedTextResolver()
    return SignInNoticeFacilitator(
        business_repo=businesses,
        staff_alerts=world.alerts,
        manager_notifier=world.notifier,
        text_transformer=StaffNotificationTextTransformer(resolver),
        link_signer=StaffLinkSigner(TEST_ENCRYPTION_KEY),
        localized_text_resolver=resolver,
        app_settings=world.settings,
        wall_clock=world.clock.wall_clock,
        user_repo=users,
    )


def people(world: AlertWorld, email: str | None) -> UserRepository:
    users = UserRepository(InMemoryDocumentCollectionAdapter(UserDocument))
    users.save(
        UserDocument(
            id=world.owner,
            login_method=LoginMethod.EMAIL if email else LoginMethod.PHONE,
            email=EmailAddress(email) if email else None,
            locale=LanguageTag("it"),
        )
    )
    return users


def test_a_change_is_told_on_the_devices_and_by_e_mail() -> None:
    world = AlertWorld()
    owner_phone = world.add_device(world.owner, "en")
    world.add_device(world.staff, "en")
    notices = build_notices(world, people(world, "owner@salobie.example"))

    notices.notice_security_change(world.owner, SecurityChange.TOTP_REMOVED, CAFE_IP)

    [push] = world.push_queue.queued
    assert push.subscription_id == owner_phone.id
    assert push.is_urgent is True
    assert str(push.tag).startswith(f"security_change:{world.owner}-")
    assert str(push.brief.title) == "Your sign-in protection changed"
    assert "authenticator app was removed" in str(push.brief.detail)
    assert str(CAFE_IP) in str(push.brief.detail)
    assert push.link is not None
    claims = StaffLinkSigner(TEST_ENCRYPTION_KEY).read(
        StaffLinkToken(str(push.link).rsplit("/", 1)[-1])
    )
    assert claims is not None and claims.target is StaffLinkTarget.ACCOUNT_SECURITY
    [(contact, text)] = world.notifier.sent
    assert contact.channel is ManagerContactChannel.EMAIL
    assert str(contact.address) == "owner@salobie.example"
    assert "La protezione del tuo accesso è cambiata" in str(text)


def test_two_changes_in_a_row_are_both_told() -> None:
    world = AlertWorld()
    world.add_device(world.owner, "en")
    notices = build_notices(world, people(world, None))

    notices.notice_security_change(world.owner, SecurityChange.PASSKEY_ADDED, None)
    world.clock.move_to(NOON + timedelta(seconds=1))
    notices.notice_security_change(world.owner, SecurityChange.PASSKEY_REMOVED, None)

    briefs = [str(push.brief.detail) for push in world.push_queue.queued]
    assert len(briefs) == 2
    assert "passkey was added" in briefs[0]
    assert "passkey was removed" in briefs[1]
    # Signed in by phone: no e-mail.
    assert world.notifier.sent == []


def test_an_unknown_person_or_no_store_tells_nobody() -> None:
    world = AlertWorld()
    world.add_device(world.owner, "en")

    build_notices(world, people(world, None)).notice_security_change(
        UserId(), SecurityChange.TOTP_ADDED, CAFE_IP
    )
    build_notices(world, None).notice_security_change(
        world.owner, SecurityChange.TOTP_ADDED, CAFE_IP
    )

    assert world.push_queue.queued == []
    assert world.notifier.sent == []
