"""
What a person hears when their account is signed in from a new device or
from a country none of their live sessions is in: the browser and system,
the address (and the country), and where to end that session. No other
detail; it may show on a locked screen.
"""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertTextsContract
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.dto.sessions import SessionDevice
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.utilities.localization.owner_texts import owner_text

NEW_DEVICE_TITLE: LocalizedText = owner_text("notifications.sign_in.title")
NEW_DEVICE_DETAIL: LocalizedText = owner_text("notifications.sign_in.detail")
UNKNOWN_DEVICE: LocalizedText = owner_text("notifications.sign_in.unknown_device")
NEW_COUNTRY_TITLE: LocalizedText = owner_text("notifications.sign_in.new_country_title")
NEW_COUNTRY_DETAIL: LocalizedText = owner_text(
    "notifications.sign_in.new_country_detail"
)


class SignInNoticeTexts(StaffAlertTextsContract):
    """
    The notice of one sign-in from a new device, or from a new country
    (`new_country`, its ISO code), in any language.
    """

    def __init__(
        self,
        resolver: LocalizedTextResolverContract,
        device: SessionDevice,
        client_ip_address: ClientIpAddress | None,
        new_country: CountryCode | None = None,
    ) -> None:
        self._resolver: LocalizedTextResolverContract = resolver
        self._device: SessionDevice = device
        self._client_ip_address: ClientIpAddress | None = client_ip_address
        self._new_country: CountryCode | None = new_country

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
        is_new_country: bool = self._new_country is not None
        title: LocalizedText = NEW_COUNTRY_TITLE if is_new_country else NEW_DEVICE_TITLE
        detail: LocalizedText = (
            NEW_COUNTRY_DETAIL if is_new_country else NEW_DEVICE_DETAIL
        )
        return StaffAlertBrief(
            title=StaffAlertTitle(self._resolver.resolve(title, language)),
            detail=StaffAlertDetail(
                str(self._resolver.resolve(detail, language))
                .replace("{device}", device)
                .replace("{address}", address)
                .replace("{country}", str(self._new_country or ""))
            ),
        )

    def detailed(self, language: LanguageTag) -> MessageText:
        lines: StaffAlertBrief = self.brief(language)
        return MessageText(f"{lines.title}\n{lines.detail}")
