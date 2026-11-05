"""
What a person hears when how they prove it is them changed: an
authenticator app or a passkey added or removed, a new set of recovery
codes. It names the change and the address it came from, and where to act
when it was not them; no other detail (it may show on a locked screen).
"""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertTextsContract
from app.schemas.constants.mfa import SecurityChange
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.utilities.localization.owner_texts import owner_text

SECURITY_CHANGE_TITLE: LocalizedText = owner_text("notifications.security_change.title")
SECURITY_CHANGE_ADVICE: LocalizedText = owner_text(
    "notifications.security_change.advice"
)
CHANGE_TEXTS: dict[SecurityChange, LocalizedText] = {
    SecurityChange.TOTP_ADDED: owner_text("notifications.security_change.totp_added"),
    SecurityChange.TOTP_REMOVED: owner_text(
        "notifications.security_change.totp_removed"
    ),
    SecurityChange.PASSKEY_ADDED: owner_text(
        "notifications.security_change.passkey_added"
    ),
    SecurityChange.PASSKEY_REMOVED: owner_text(
        "notifications.security_change.passkey_removed"
    ),
    SecurityChange.RECOVERY_CODES_RENEWED: owner_text(
        "notifications.security_change.recovery_codes_renewed"
    ),
}


class SecurityChangeNoticeTexts(StaffAlertTextsContract):
    """The notice of one second-factor change, in any language."""

    def __init__(
        self,
        resolver: LocalizedTextResolverContract,
        change: SecurityChange,
        client_ip_address: ClientIpAddress | None,
    ) -> None:
        self._resolver: LocalizedTextResolverContract = resolver
        self._change: SecurityChange = change
        self._client_ip_address: ClientIpAddress | None = client_ip_address

    def brief(self, language: LanguageTag) -> StaffAlertBrief:
        address: str = (
            f" ({self._client_ip_address})" if self._client_ip_address else ""
        )
        what: str = str(
            self._resolver.resolve(CHANGE_TEXTS[self._change], language)
        ).replace("{address}", address)
        advice: str = str(self._resolver.resolve(SECURITY_CHANGE_ADVICE, language))
        return StaffAlertBrief(
            title=StaffAlertTitle(
                self._resolver.resolve(SECURITY_CHANGE_TITLE, language)
            ),
            detail=StaffAlertDetail(f"{what} {advice}"),
        )

    def detailed(self, language: LanguageTag) -> MessageText:
        lines: StaffAlertBrief = self.brief(language)
        return MessageText(f"{lines.title}\n{lines.detail}")
