"""
What staff hear when a paid deposit is to be returned: the amount and the
reference to find it by in their merchant account, the booking's date and
time, and that it was cancelled in time. Nothing about the customer; it
may show on a locked screen.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertTextsContract
from app.schemas.dto.billing import Money
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deposits.constrained_strings import DepositReference
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.utilities.localization.owner_texts import owner_text
from app.utilities.money.money_formatting import format_money
from app.utilities.scheduling.localized_formatting import format_full_date

DEPOSIT_REFUND_TITLE: LocalizedText = owner_text("notifications.deposit_refund.title")
DEPOSIT_REFUND_DETAIL: LocalizedText = owner_text("notifications.deposit_refund.detail")


class DepositRefundTexts(StaffAlertTextsContract):
    """The refund note of one cancelled booking, in any language."""

    def __init__(
        self,
        resolver: LocalizedTextResolverContract,
        business_name: BusinessName,
        amount: Money,
        reference: DepositReference,
        starts: datetime,
        zone: ZoneInfo,
    ) -> None:
        self._resolver: LocalizedTextResolverContract = resolver
        self._business_name: BusinessName = business_name
        self._amount: Money = amount
        self._reference: DepositReference = reference
        self._starts: datetime = starts.astimezone(zone)

    def detailed(self, language: LanguageTag) -> MessageText:
        lines: StaffAlertBrief = self.brief(language)
        return MessageText(f"{lines.title}\n{lines.detail}")

    def brief(self, language: LanguageTag) -> StaffAlertBrief:
        title: str = str(self._resolver.resolve(DEPOSIT_REFUND_TITLE, language))
        detail: str = str(self._resolver.resolve(DEPOSIT_REFUND_DETAIL, language))
        return StaffAlertBrief(
            title=StaffAlertTitle(
                title.replace("{business}", str(self._business_name))
            ),
            detail=StaffAlertDetail(
                detail.replace("{amount}", str(format_money(self._amount, language)))
                .replace("{reference}", str(self._reference))
                .replace("{date}", format_full_date(self._starts.date(), language))
                .replace("{time}", self._starts.strftime("%H:%M"))
            ),
        )
