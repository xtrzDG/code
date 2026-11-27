"""
What the owners of a WhatsApp number hear about the access Meta gave the
platform for it (the number's token of Embedded Signup): Meta would not
renew it, it ends within three days, or it ended and customers on WhatsApp
get no replies; on which day (in the business's time zone), and how to
connect the number again (Channels → WhatsApp → Update details → Continue
with Facebook). Nothing about customers; it may show on a locked screen.
"""

from collections.abc import Mapping
from datetime import date
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertTextsContract
from app.schemas.constants.meta_connection import WhatsAppTokenNoticeStage
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.utilities.localization.owner_texts import owner_text
from app.utilities.scheduling.localized_formatting import format_full_date
from app.utilities.scheduling.zoned_time import (
    microseconds_to_seconds,
    to_local_moment,
)

RECONNECT_TITLE: LocalizedText = owner_text(
    "notifications.whatsapp_token.reconnect_title"
)
ENDED_TITLE: LocalizedText = owner_text("notifications.whatsapp_token.ended_title")
STAGE_DETAILS: Mapping[WhatsAppTokenNoticeStage, LocalizedText] = {
    WhatsAppTokenNoticeStage.REFRESH_REFUSED: owner_text(
        "notifications.whatsapp_token.refresh_refused_detail"
    ),
    WhatsAppTokenNoticeStage.ENDING: owner_text(
        "notifications.whatsapp_token.ending_detail"
    ),
    WhatsAppTokenNoticeStage.ENDED: owner_text(
        "notifications.whatsapp_token.ended_detail"
    ),
}


class WhatsAppTokenNoticeTexts(StaffAlertTextsContract):
    """One reminder about a WhatsApp number's token, in any language."""

    def __init__(
        self,
        resolver: LocalizedTextResolverContract,
        business_name: BusinessName,
        stage: WhatsAppTokenNoticeStage,
        ends_at: Microseconds,
        zone: ZoneInfo,
    ) -> None:
        self._resolver: LocalizedTextResolverContract = resolver
        self._business_name: BusinessName = business_name
        self._stage: WhatsAppTokenNoticeStage = stage
        self._ends_on: date = to_local_moment(
            microseconds_to_seconds(int(ends_at)), zone
        ).date()

    def detailed(self, language: LanguageTag) -> MessageText:
        lines: StaffAlertBrief = self.brief(language)
        return MessageText(f"{lines.title}\n{lines.detail}")

    def brief(self, language: LanguageTag) -> StaffAlertBrief:
        title: str = str(
            self._resolver.resolve(
                ENDED_TITLE
                if self._stage is WhatsAppTokenNoticeStage.ENDED
                else RECONNECT_TITLE,
                language,
            )
        )
        detail: str = str(self._resolver.resolve(STAGE_DETAILS[self._stage], language))
        return StaffAlertBrief(
            title=StaffAlertTitle(
                title.replace("{business}", str(self._business_name))
            ),
            detail=StaffAlertDetail(
                detail.replace("{date}", format_full_date(self._ends_on, language))
            ),
        )
