"""
A sign-in from a new device is told to its person, and only to them: a
personal alert on their devices (the staff alert facilitator, no staff
contact) and an e-mail for people who sign in by e-mail. A first sign-in
or a known device tells nobody.
"""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.users.sign_in_notice_facilitator import SignInNoticeFacilitator
from app.repositories.business_repositories import BusinessRepository
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument, UserSessionDocument
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import StaffLinkToken
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.strings import AccessTokenHash
from app.transformers.notifications.staff_notification_text_transformer import (
    StaffNotificationTextTransformer,
)
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from app.utilities.security.user_agents import read_user_agent
from tests.notifications.alert_world import AlertWorld
from tests.notifications.staff_alert_fakes import TEST_ENCRYPTION_KEY
from tests.operations.fakes import FakeLocalizedTextResolver
from tests.users.access.session_steps import (
    ANDROID_CHROME,
    CAFE_IP,
    IPHONE_SAFARI,
    MAC_CHROME,
)


def build_notices(world: AlertWorld) -> SignInNoticeFacilitator:
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
    )


def owner_of(world: AlertWorld, email: str | None = None) -> UserDocument:
    return UserDocument(
        id=world.owner,
        login_method=LoginMethod.EMAIL if email else LoginMethod.PHONE,
        email=EmailAddress(email) if email else None,
        locale=LanguageTag("ru"),
    )


def session(
    world: AlertWorld, user_agent: str, ip: str = CAFE_IP
) -> UserSessionDocument:
    now = world.clock.now_microseconds()
    return UserSessionDocument(
        user_id=world.owner,
        token_hash=AccessTokenHash(f"hash-{user_agent[:12]}-{ip}"),
        expires_at=Microseconds(int(now) + 1),
        user_agent=read_user_agent(user_agent),
        created_ip=ClientIpAddress(ip),
    )


def test_a_new_device_is_told_to_its_person_only() -> None:
    world = AlertWorld()
    owner_phone = world.add_device(world.owner, "ka")
    world.add_device(world.staff, "en")
    notices = build_notices(world)

    notices.notice_new_device(
        owner_of(world, "owner@salobie.example"),
        session(world, IPHONE_SAFARI),
        [session(world, MAC_CHROME)],
    )

    [push] = world.push_queue.queued
    assert push.subscription_id == owner_phone.id
    assert push.is_urgent is True
    assert str(push.tag).startswith("sign_in:")
    assert "Safari · iOS" in str(push.brief.detail)
    assert CAFE_IP in str(push.brief.detail)
    # No staff contact hears it; the owner's e-mail does, in Russian.
    [(contact, text)] = world.notifier.sent
    assert contact.channel is ManagerContactChannel.EMAIL
    assert str(contact.address) == "owner@salobie.example"
    assert "Новый вход в ваш аккаунт" in str(text)
    assert "/n/" in str(text)


def test_the_link_opens_account_security() -> None:
    world = AlertWorld()
    world.add_device(world.owner, "en")

    build_notices(world).notice_new_device(
        owner_of(world), session(world, ANDROID_CHROME), [session(world, MAC_CHROME)]
    )

    [push] = world.push_queue.queued
    assert push.link is not None
    claims = StaffLinkSigner(TEST_ENCRYPTION_KEY).read(
        StaffLinkToken(str(push.link).rsplit("/", 1)[-1])
    )
    assert claims is not None and claims.target is StaffLinkTarget.ACCOUNT_SECURITY
    assert world.notifier.sent == []


def test_a_first_sign_in_or_a_known_device_tells_nobody() -> None:
    world = AlertWorld()
    world.add_device(world.owner, "en")
    notices = build_notices(world)
    owner = owner_of(world, "owner@salobie.example")

    notices.notice_new_device(owner, session(world, MAC_CHROME), [])
    notices.notice_new_device(
        owner, session(world, MAC_CHROME, "192.0.2.1"), [session(world, MAC_CHROME)]
    )

    assert world.push_queue.queued == []
    assert world.notifier.sent == []
