"""
Every owner hears of each download of a full export, with who downloaded
it, the browser and the address: a personal alert on their devices (no
staff contact, no other member) and a message of their own, by e-mail or,
for owners who sign in by phone, by SMS. The notice never breaks a
download.
"""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.privacy.export_download_notice_facilitator import (
    ExportDownloadNoticeFacilitator,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.users import UserDocument
from app.schemas.dto.privacy.business_exports import ExportDownloadNotice
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.notifications.constrained_strings import StaffLinkToken
from app.schemas.typings.privacy.constrained_integers import ExportDownloadCount
from app.schemas.typings.privacy.prefixed_id import BusinessExportId
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import UserDisplayName
from app.transformers.notifications.staff_notification_text_transformer import (
    StaffNotificationTextTransformer,
)
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from app.utilities.security.user_agents import read_user_agent
from tests.notifications.alert_world import AlertWorld
from tests.notifications.staff_alert_fakes import TEST_ENCRYPTION_KEY
from tests.operations.fakes import FakeLocalizedTextResolver
from tests.users.access.session_steps import CAFE_IP, MAC_CHROME

CO_OWNER_PHONE: str = "+995599111222"


class World:
    def __init__(self) -> None:
        self.alerts = AlertWorld()
        self.co_owner = UserId()
        self.business: BusinessDocument = self.alerts.business.model_copy(
            update={
                "members": [
                    *self.alerts.business.members,
                    BusinessMember(
                        user_id=self.co_owner, role=BusinessMemberRole.OWNER
                    ),
                ]
            }
        )
        self.users = UserRepository(InMemoryDocumentCollectionAdapter(UserDocument))
        self.users.save(
            UserDocument(
                id=self.alerts.owner,
                login_method=LoginMethod.EMAIL,
                email=EmailAddress("owner@salobie.example"),
                display_name=UserDisplayName("Nino"),
                locale=LanguageTag("ru"),
            )
        )
        self.users.save(
            UserDocument(
                id=self.co_owner,
                login_method=LoginMethod.PHONE,
                phone_number=E164PhoneNumber(CO_OWNER_PHONE),
                locale=LanguageTag("en"),
            )
        )
        resolver = FakeLocalizedTextResolver()
        self.notices = ExportDownloadNoticeFacilitator(
            user_repo=self.users,
            staff_alerts=self.alerts.alerts,
            manager_notifier=self.alerts.notifier,
            text_transformer=StaffNotificationTextTransformer(resolver),
            link_signer=StaffLinkSigner(TEST_ENCRYPTION_KEY),
            localized_text_resolver=resolver,
            app_settings=self.alerts.settings,
            wall_clock=self.alerts.clock.wall_clock,
        )

    def download(self, number: int = 1) -> None:
        self.notices.notice_download(
            self.business,
            ExportDownloadNotice(
                business_id=self.business.id,
                export_id=BusinessExportId(),
                downloaded_by=self.alerts.owner,
                client_ip_address=ClientIpAddress(CAFE_IP),
                user_agent=read_user_agent(MAC_CHROME),
                download_number=ExportDownloadCount(number),
            ),
        )


def test_every_owner_hears_of_a_download_and_no_one_else() -> None:
    world = World()
    owner_device = world.alerts.add_device(world.alerts.owner, "ru")
    co_owner_device = world.alerts.add_device(world.co_owner, "en")
    world.alerts.add_device(world.alerts.staff, "en")

    world.download(number=2)

    pushes = world.alerts.push_queue.queued
    assert {push.subscription_id for push in pushes} == {
        owner_device.id,
        co_owner_device.id,
    }
    assert all(push.is_urgent for push in pushes)
    [english] = [push for push in pushes if push.subscription_id == co_owner_device.id]
    assert "Nino downloaded the full export (2 of 3)" in str(english.brief.detail)
    assert "Chrome · macOS" in str(english.brief.detail)
    assert CAFE_IP in str(english.brief.detail)
    messages = {
        (contact.channel, str(contact.address)): str(text)
        for contact, text in world.alerts.notifier.sent
    }
    assert set(messages) == {
        (ManagerContactChannel.EMAIL, "owner@salobie.example"),
        (ManagerContactChannel.SMS, CO_OWNER_PHONE),
    }
    assert (
        "Данные бизнеса скачаны"
        in messages[(ManagerContactChannel.EMAIL, "owner@salobie.example")]
    )


def test_the_link_opens_settings_privacy() -> None:
    world = World()
    world.alerts.add_device(world.co_owner, "en")

    world.download()

    [push] = world.alerts.push_queue.queued
    assert push.link is not None
    claims = StaffLinkSigner(TEST_ENCRYPTION_KEY).read(
        StaffLinkToken(str(push.link).rsplit("/", 1)[-1])
    )
    assert claims is not None and claims.target is StaffLinkTarget.PRIVACY


def test_a_failing_notice_never_breaks_the_download() -> None:
    world = World()
    broken = world.business.model_copy(update={"timezone": "Mars/Olympus"})

    world.notices.notice_download(
        broken,
        ExportDownloadNotice(
            business_id=broken.id,
            export_id=BusinessExportId(),
            downloaded_by=UserId(),
            download_number=ExportDownloadCount(1),
        ),
    )

    assert world.alerts.push_queue.queued == []
