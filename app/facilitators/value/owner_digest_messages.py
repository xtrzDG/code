"""
The messages one owner's report goes out as, per channel: their sign-in
e-mail, their own Telegram chat linked to the platform bot, and WhatsApp
from the platform's number (the approved owner report template).
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.outbound_messages import OutboundTemplate
from app.schemas.domain.users import UserDocument
from app.schemas.domain.value_settings import DigestPreferencesDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.value.value_digests import ValueDigestText
from app.schemas.dto.value.value_reports import ValueReportView
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import (
    CabinetDeepLink,
    StaffAlertSubject,
)
from app.utilities.channels.language_codes import to_whatsapp_template_language

# The third parameter of the template when the cabinet has no address yet.
NO_LINK: MessageText = MessageText("—")


@dataclass(frozen=True)
class OwnerReport:
    """One report for one owner, with their choices and the link to it."""

    business: BusinessDocument
    user: UserDocument
    preferences: DigestPreferencesDocument | None
    report: ValueReportView
    link: CabinetDeepLink | None


def owner_name(user: UserDocument) -> ManagerName:
    return ManagerName(str(user.display_name or user.email or user.phone_number or ""))


def email_notification(
    business: BusinessDocument,
    user: UserDocument,
    text: ValueDigestText,
    subject: StaffAlertSubject,
) -> StaffNotification | None:
    """The report to the owner's sign-in e-mail (None: they sign in by phone)."""

    if user.email is None:
        return None

    return StaffNotification(
        business_id=business.id,
        contact=ManagerContact(
            name=owner_name(user),
            channel=ManagerContactChannel.EMAIL,
            address=ManagerContactAddress(str(user.email)),
            language=user.locale,
        ),
        text=text.message,
        subject=subject,
    )


def owner_telegram_chat(
    business: BusinessDocument,
    preferences: DigestPreferencesDocument | None,
) -> ManagerContact | None:
    """
    The Telegram chat the owner chose, while it is still linked to the
    business through the platform bot (an unlinked chat gets nothing).
    """

    if preferences is None or preferences.telegram_chat is None:
        return None

    return next(
        (
            contact
            for contact in business.manager_contacts
            if contact.channel is ManagerContactChannel.TELEGRAM
            and contact.address == preferences.telegram_chat
        ),
        None,
    )


def telegram_notification(
    business: BusinessDocument,
    chat: ManagerContact,
    text: ValueDigestText,
    subject: StaffAlertSubject,
    deliver_after: Microseconds | None,
) -> StaffNotification:
    """The whole report, as the e-mail reads, from the platform bot."""

    return StaffNotification(
        business_id=business.id,
        contact=chat,
        text=text.message,
        subject=subject,
        deliver_after=deliver_after,
    )


def whatsapp_notification(
    business: BusinessDocument,
    user: UserDocument,
    preferences: DigestPreferencesDocument | None,
    text: ValueDigestText,
    link: CabinetDeepLink | None,
    settings: AppSettings,
    delivery: tuple[StaffAlertSubject, Microseconds | None],
) -> StaffNotification | None:
    """
    The report's summary in the owner report template ({{1}} the business,
    {{2}} the summary, {{3}} the link), to the number the owner chose;
    None without a number or without the template configured.
    """

    template_name: WhatsAppTemplateName | None = (
        settings.whatsapp_owner_report_template_name
    )
    if (
        preferences is None
        or preferences.whatsapp_number is None
        or template_name is None
    ):
        return None

    subject, deliver_after = delivery
    language: LanguageTag = user.locale
    return StaffNotification(
        business_id=business.id,
        contact=ManagerContact(
            name=owner_name(user),
            channel=ManagerContactChannel.WHATSAPP,
            address=ManagerContactAddress(str(preferences.whatsapp_number)),
            language=language,
        ),
        text=text.summary,
        subject=subject,
        deliver_after=deliver_after,
        template=OutboundTemplate(
            name=template_name,
            language_code=to_whatsapp_template_language(language),
            body_parameters=[
                MessageText(str(business.name)),
                text.summary,
                NO_LINK if link is None else MessageText(str(link)),
            ],
        ),
    )
