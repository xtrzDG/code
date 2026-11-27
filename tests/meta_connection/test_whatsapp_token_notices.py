"""
What the owners of a WhatsApp number hear about its token: each stage in
English and Italian, with the day the token ends in the business's time
zone and the way to connect the number again; the staff alert for their
devices and the staff contacts, and the e-mail to their account address
in their own language. A reminder never raises.
"""

from zoneinfo import ZoneInfo

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.notifications.owner_account_email_facilitator import (
    OwnerAccountEmailFacilitator,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.meta_connection import WhatsAppTokenNoticeStage
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.transformers.notifications.staff_notification_text_transformer import (
    StaffNotificationTextTransformer,
)
from app.use_cases.channels.meta_connection.whatsapp_token_notices import (
    WhatsAppTokenNotices,
)
from app.utilities.channels.whatsapp_token_notice_texts import (
    WhatsAppTokenNoticeTexts,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from tests.billing.billing_fakes import RecordingNotifier
from tests.meta_connection.token_refresh_fakes import (
    RecordingOwnerEmails,
    RecordingStaffAlerts,
)
from tests.platform_ops.ops_documents import DAY, HOUR, MINUTE, at, business, member
from tests.platform_ops.ops_world import OpsClock

Stage = WhatsAppTokenNoticeStage
CABINET: str = "https://cabinet.workshop.example"
# Wednesday 2026-10-21 22:30 UTC: already Thursday in Tbilisi (UTC+4).
ENDS_AT = at(16 * DAY + 14 * HOUR + 30 * MINUTE)
TBILISI = ZoneInfo("Asia/Tbilisi")
EN = LanguageTag("en")
IT = LanguageTag("it")
WAY_BACK_EN = "Channels → WhatsApp → Update details → Continue with Facebook"
WAY_BACK_IT = "Canali → WhatsApp → Aggiorna i dati → Continua con Facebook"


def texts(stage: WhatsAppTokenNoticeStage) -> WhatsAppTokenNoticeTexts:
    return WhatsAppTokenNoticeTexts(
        LocalizedTextResolver(), BusinessName("Funicular VR"), stage, ENDS_AT, TBILISI
    )


def whatsapp(owner: BusinessDocument) -> ChannelDocument:
    return ChannelDocument(
        business_id=owner.id,
        kind=ChannelKind.WHATSAPP,
        status=ChannelStatus.CONNECTED,
        credential_expires_at=ENDS_AT,
    )


def test_each_stage_reads_in_english() -> None:
    refused = texts(Stage.REFRESH_REFUSED).brief(EN)
    ending = texts(Stage.ENDING).brief(EN)
    ended = texts(Stage.ENDED).brief(EN)

    assert str(refused.title) == "Connect WhatsApp again · Funicular VR"
    assert str(refused.detail).startswith("Meta did not renew")
    assert str(ending.title) == str(refused.title)
    assert "ends on Thursday, October 22, 2026" in str(ending.detail)
    assert str(ended.title) == "WhatsApp stopped replying to customers · Funicular VR"
    assert "ended on Thursday, October 22, 2026" in str(ended.detail)
    for brief in (refused, ending, ended):
        assert WAY_BACK_EN in str(brief.detail)


def test_each_stage_reads_in_italian() -> None:
    refused = texts(Stage.REFRESH_REFUSED).brief(IT)
    ending = texts(Stage.ENDING).brief(IT)
    ended = texts(Stage.ENDED).brief(IT)

    assert str(refused.title) == "Collega di nuovo WhatsApp · Funicular VR"
    assert str(refused.detail).startswith("Meta non ha rinnovato")
    assert "scade giovedì 22 ottobre 2026" in str(ending.detail)
    assert str(ended.title) == "WhatsApp non risponde più ai clienti · Funicular VR"
    assert "è scaduto giovedì 22 ottobre 2026" in str(ended.detail)
    for brief in (refused, ending, ended):
        assert WAY_BACK_IT in str(brief.detail)

    detailed = texts(Stage.ENDED).detailed(IT)
    assert str(detailed) == f"{ended.title}\n{ended.detail}"


def test_the_alert_is_for_the_owners_and_opens_channels() -> None:
    owner = business("Funicular VR")
    channel = whatsapp(owner)
    alerts = RecordingStaffAlerts()
    emails = RecordingOwnerEmails()
    notices = WhatsAppTokenNotices(alerts, emails, LocalizedTextResolver())

    for stage in Stage:
        notices.notify(owner, channel, stage)

    assert [alert.is_urgent for alert, _ in alerts.raised] == [False, False, True]
    for (alert, _), stage in zip(alerts.raised, Stage, strict=True):
        assert alert.business_id == owner.id
        assert alert.target is StaffLinkTarget.CHANNELS
        assert alert.member_roles == [BusinessMemberRole.OWNER]
        assert alert.event is None
        assert str(alert.tag) == f"whatsapp_token:{channel.id}"
        assert str(alert.subject) == f"whatsapp_token:{channel.id}-20261021-{stage}"
    assert emails.mailed == [alert for alert, _ in alerts.raised]
    # In the business's time zone, the token ends on the 22nd.
    _, ended_texts = alerts.raised[2]
    assert "October 22, 2026" in str(ended_texts.brief(EN).detail)


def test_every_owner_gets_it_at_their_account_address_in_their_language() -> None:
    users = UserRepository(InMemoryDocumentCollectionAdapter(UserDocument))
    italian = UserDocument(
        login_method=LoginMethod.EMAIL,
        email=EmailAddress("giulia@example.it"),
        locale=IT,
        is_verified=True,
    )
    english = UserDocument(
        login_method=LoginMethod.EMAIL,
        email=EmailAddress("tom@example.com"),
        locale=EN,
        is_verified=True,
    )
    by_phone = UserDocument(
        login_method=LoginMethod.PHONE,
        phone_number=E164PhoneNumber("+393331112233"),
        locale=IT,
        is_verified=True,
    )
    for user in (italian, english, by_phone):
        users.save(user)
    owner = business(
        "Funicular VR",
        *(member(user.id, BusinessMemberRole.OWNER) for user in (italian, english)),
        member(by_phone.id, BusinessMemberRole.OWNER),
    )
    notifier = RecordingNotifier()
    resolver = LocalizedTextResolver()
    mailer = OwnerAccountEmailFacilitator(
        user_repo=users,
        manager_notifier=notifier,
        link_signer=StaffLinkSigner(PlatformSecret("test-link-key-0000")),
        text_transformer=StaffNotificationTextTransformer(resolver),
        cabinet_base_url=CabinetBaseUrl(CABINET),
        wall_clock=OpsClock().wall_clock,
    )

    WhatsAppTokenNotices(RecordingStaffAlerts(), mailer, resolver).notify(
        owner, whatsapp(owner), Stage.ENDING
    )

    sent = {str(contact.address): str(text) for contact, text in notifier.sent}
    assert set(sent) == {"giulia@example.it", "tom@example.com"}
    assert "Collega di nuovo WhatsApp · Funicular VR" in sent["giulia@example.it"]
    assert WAY_BACK_IT in sent["giulia@example.it"]
    assert "Connect WhatsApp again · Funicular VR" in sent["tom@example.com"]
    assert f"{CABINET}/n/" in sent["tom@example.com"]


def test_a_reminder_never_raises() -> None:
    owner = business("Funicular VR")
    failing = RecordingStaffAlerts()
    failing.fails = True
    emails = RecordingOwnerEmails()
    notices = WhatsAppTokenNotices(failing, emails, LocalizedTextResolver())

    notices.notify(owner, whatsapp(owner), Stage.ENDED)
    assert len(emails.mailed) == 1  # The outbox of alerts was down.

    lost = owner.model_copy(update={"timezone": TimezoneName("Mars/Olympus_Mons")})
    notices.notify(lost, whatsapp(lost), Stage.ENDING)
    endless = whatsapp(owner).model_copy(update={"credential_expires_at": None})
    notices.notify(owner, endless, Stage.ENDING)

    assert len(failing.raised) == 1
    assert len(emails.mailed) == 1
