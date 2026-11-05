"""The platform team hears of a number it is to arrange."""

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.phone_numbers import PhoneNumberRequestDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject

TEAM_LANGUAGE: LanguageTag = LanguageTag("en")
TEAM_NAME: ManagerName = ManagerName("Platform team")


def tell_team_of_request(
    notifier: ManagerNotificationFacilitatorContract,
    app_settings: AppSettings,
    business: BusinessDocument,
    request: PhoneNumberRequestDocument,
) -> None:
    """An e-mail to every platform admin (PLATFORM_ADMIN_EMAILS) via the outbox."""

    base: str = str(app_settings.cabinet_base_url or "").rstrip("/")
    text = MessageText(
        f"Phone number requested: {business.name}\n\n"
        f"A {request.number_type.value.replace('_', '-')} number in "
        f"{request.country_code}"
        + ("" if request.city is None else f", near {request.city}")
        + f" (the business is in {business.country_code}). Arrange it, then "
        "connect it as the business's phone channel; the request closes "
        "by itself once the channel is connected.\n"
        f"{base}/admin/clients/{business.id}"
    )
    for address in app_settings.platform_admin_emails:
        notifier.notify(
            StaffNotification(
                business_id=business.id,
                contact=ManagerContact(
                    name=TEAM_NAME,
                    channel=ManagerContactChannel.EMAIL,
                    address=ManagerContactAddress(str(address)),
                    language=TEAM_LANGUAGE,
                ),
                text=text,
                subject=StaffAlertSubject(f"phone_number_request:{business.id}"),
            )
        )
