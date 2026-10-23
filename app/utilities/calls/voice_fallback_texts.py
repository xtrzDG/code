"""
What the owner hears when the phone assistant could not take a call and
the line's fallback took over: the call was put through to the staff
mobile on duty (which number), or nobody could take it and it is a missed
call (add a handoff phone). Nothing about the caller: it may show on a
locked screen.
"""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertTextsContract
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.utilities.localization.owner_texts import owner_text

VOICE_FALLBACK_TITLE: LocalizedText = owner_text("notifications.voice_fallback.title")
TRANSFERRED_DETAIL: LocalizedText = owner_text(
    "notifications.voice_fallback.transferred_detail"
)
NO_STAFF_DETAIL: LocalizedText = owner_text(
    "notifications.voice_fallback.no_staff_detail"
)


class VoiceFallbackTexts(StaffAlertTextsContract):
    """The notice of calls the phone assistant could not take, in any language."""

    def __init__(
        self,
        resolver: LocalizedTextResolverContract,
        business_name: BusinessName,
        transfer_phone: FormattedPhoneNumber | None,
    ) -> None:
        self._resolver: LocalizedTextResolverContract = resolver
        self._business_name: BusinessName = business_name
        self._transfer_phone: FormattedPhoneNumber | None = transfer_phone

    def detailed(self, language: LanguageTag) -> MessageText:
        lines: StaffAlertBrief = self.brief(language)
        return MessageText(f"{lines.title}\n{lines.detail}")

    def brief(self, language: LanguageTag) -> StaffAlertBrief:
        title: str = str(self._resolver.resolve(VOICE_FALLBACK_TITLE, language))
        detail: str = str(
            self._resolver.resolve(
                NO_STAFF_DETAIL if self._transfer_phone is None else TRANSFERRED_DETAIL,
                language,
            )
        )
        return StaffAlertBrief(
            title=StaffAlertTitle(
                title.replace("{business}", str(self._business_name))
            ),
            detail=StaffAlertDetail(
                detail.replace("{phone}", str(self._transfer_phone or ""))
            ),
        )
