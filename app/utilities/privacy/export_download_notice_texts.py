"""
What every owner hears when a full export of the business is downloaded:
who downloaded it, from which browser and address, which download of the
three it was, and where to look. No other detail; it may show on a locked
screen.
"""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertTextsContract
from app.schemas.domain.users import UserDocument
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.dto.sessions import SessionDevice
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.schemas.typings.privacy.constrained_integers import ExportDownloadCount
from app.utilities.knowledge.localized_texts import build_localized_text

DOWNLOAD_TITLE: LocalizedText = build_localized_text(
    en="The business data was downloaded",
    ru="Данные бизнеса скачаны",
    ka="ბიზნესის მონაცემები ჩამოიტვირთა",
)
DOWNLOAD_DETAIL: LocalizedText = build_localized_text(
    en=(
        "{person} downloaded the full export ({number} of 3): {device}{address}. "
        "Not expected? Check the team in Settings and the sessions in "
        "Account → Security."
    ),
    ru=(
        "{person} скачал(а) полную выгрузку ({number} из 3): {device}{address}. "
        "Не ожидали? Проверьте команду в Настройках и сеансы в разделе "
        "Аккаунт → Безопасность."
    ),
    ka=(
        "{person}-მ ჩამოტვირთა სრული ექსპორტი ({number} 3-დან): "
        "{device}{address}. მოულოდნელია? შეამოწმეთ გუნდი პარამეტრებში და "
        "სესიები: ანგარიში → უსაფრთხოება."
    ),
)
UNKNOWN_DEVICE: LocalizedText = build_localized_text(
    en="an unknown device",
    ru="неизвестное устройство",
    ka="უცნობი მოწყობილობა",
)
AN_OWNER: LocalizedText = build_localized_text(
    en="An owner",
    ru="Владелец",
    ka="მფლობელი",
)


class ExportDownloadNoticeTexts(StaffAlertTextsContract):
    """The notice of one download of a full export, in any language."""

    def __init__(
        self,
        resolver: LocalizedTextResolverContract,
        downloader: UserDocument | None,
        device: SessionDevice,
        client_ip_address: ClientIpAddress | None,
        download_number: ExportDownloadCount,
    ) -> None:
        self._resolver: LocalizedTextResolverContract = resolver
        self._downloader: UserDocument | None = downloader
        self._device: SessionDevice = device
        self._client_ip_address: ClientIpAddress | None = client_ip_address
        self._download_number: ExportDownloadCount = download_number

    def detailed(self, language: LanguageTag) -> MessageText:
        lines: StaffAlertBrief = self.brief(language)
        return MessageText(f"{lines.title}\n{lines.detail}")

    def brief(self, language: LanguageTag) -> StaffAlertBrief:
        named: list[str] = [
            str(part)
            for part in (self._device.browser, self._device.operating_system)
            if part is not None
        ]
        device: str = (
            " · ".join(named)
            if named
            else str(self._resolver.resolve(UNKNOWN_DEVICE, language))
        )
        address: str = f", {self._client_ip_address}" if self._client_ip_address else ""
        person: str = person_label(self._downloader) or str(
            self._resolver.resolve(AN_OWNER, language)
        )
        return StaffAlertBrief(
            title=StaffAlertTitle(self._resolver.resolve(DOWNLOAD_TITLE, language)),
            detail=StaffAlertDetail(
                str(self._resolver.resolve(DOWNLOAD_DETAIL, language))
                .replace("{person}", person)
                .replace("{number}", str(int(self._download_number)))
                .replace("{device}", device)
                .replace("{address}", address)
            ),
        )


def person_label(user: UserDocument | None) -> str | None:
    """The owner's name, else their e-mail, else their phone number."""

    if user is None:
        return None

    for value in (user.display_name, user.email, user.phone_number):
        if value is not None:
            return str(value)

    return None
