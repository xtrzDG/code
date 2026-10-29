"""
What a person hears when their account is signed in from a new device:
the browser and system, the address, and where to end that session. No
other detail; it may show on a locked screen.
"""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertTextsContract
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
from app.utilities.knowledge.localized_texts import build_localized_text

NEW_DEVICE_TITLE: LocalizedText = build_localized_text(
    en="New sign-in to your account",
    ru="Новый вход в ваш аккаунт",
    ka="ახალი შესვლა თქვენს ანგარიშში",
)
NEW_DEVICE_DETAIL: LocalizedText = build_localized_text(
    en=(
        "{device}{address}. Not you? End that session in Account → Security "
        "and sign in again."
    ),
    ru=(
        "{device}{address}. Это были не вы? Завершите этот сеанс в разделе "
        "Аккаунт → Безопасность и войдите заново."
    ),
    ka=(
        "{device}{address}. ეს თქვენ არ იყავით? დაასრულეთ ეს სესია: ანგარიში → "
        "უსაფრთხოება, და ხელახლა შედით."
    ),
)
UNKNOWN_DEVICE: LocalizedText = build_localized_text(
    en="An unknown device",
    ru="Неизвестное устройство",
    ka="უცნობი მოწყობილობა",
)


class SignInNoticeTexts(StaffAlertTextsContract):
    """The notice of one new-device sign-in, in any language."""

    def __init__(
        self,
        resolver: LocalizedTextResolverContract,
        device: SessionDevice,
        client_ip_address: ClientIpAddress | None,
    ) -> None:
        self._resolver: LocalizedTextResolverContract = resolver
        self._device: SessionDevice = device
        self._client_ip_address: ClientIpAddress | None = client_ip_address

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
        return StaffAlertBrief(
            title=StaffAlertTitle(self._resolver.resolve(NEW_DEVICE_TITLE, language)),
            detail=StaffAlertDetail(
                str(self._resolver.resolve(NEW_DEVICE_DETAIL, language))
                .replace("{device}", device)
                .replace("{address}", address)
            ),
        )

    def detailed(self, language: LanguageTag) -> MessageText:
        lines: StaffAlertBrief = self.brief(language)
        return MessageText(f"{lines.title}\n{lines.detail}")
