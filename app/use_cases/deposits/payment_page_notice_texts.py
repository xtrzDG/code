"""
What owners hear when the pages guests pay deposits on change: which pages
(their hosts, nothing of the address), and what to do when nobody of the
team changed them. Nothing about customers; it may show on a locked screen.
"""

from collections.abc import Mapping, Sequence

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertTextsContract
from app.schemas.constants.deposits import PaymentPageChangeKind
from app.schemas.dto.deposits.payment_page_changes import PaymentPageChange
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

PAGES_CHANGED_TITLE: LocalizedText = owner_text("notifications.deposit_pages.title")
PAGES_CHANGED_DETAIL: LocalizedText = owner_text("notifications.deposit_pages.detail")
CHANGE_LINES: Mapping[PaymentPageChangeKind, LocalizedText] = {
    PaymentPageChangeKind.ADDED: owner_text("notifications.deposit_pages.added"),
    PaymentPageChangeKind.REMOVED: owner_text("notifications.deposit_pages.removed"),
    PaymentPageChangeKind.DEFAULT_CHANGED: owner_text(
        "notifications.deposit_pages.default_changed"
    ),
    PaymentPageChangeKind.RULE_PAGE_CHANGED: owner_text(
        "notifications.deposit_pages.rule_page_changed"
    ),
}


class PaymentPageNoticeTexts(StaffAlertTextsContract):
    """The notice of one change of the payment pages, in any language."""

    def __init__(
        self,
        resolver: LocalizedTextResolverContract,
        business_name: BusinessName,
        changes: Sequence[PaymentPageChange],
    ) -> None:
        self._resolver: LocalizedTextResolverContract = resolver
        self._business_name: BusinessName = business_name
        self._changes: list[PaymentPageChange] = list(changes)

    def detailed(self, language: LanguageTag) -> MessageText:
        lines: StaffAlertBrief = self.brief(language)
        return MessageText(f"{lines.title}\n{lines.detail}")

    def brief(self, language: LanguageTag) -> StaffAlertBrief:
        title: str = str(self._resolver.resolve(PAGES_CHANGED_TITLE, language))
        changes: str = "; ".join(
            str(self._resolver.resolve(CHANGE_LINES[change.kind], language)).replace(
                "{host}", str(change.host)
            )
            for change in self._changes
        )
        detail: str = str(self._resolver.resolve(PAGES_CHANGED_DETAIL, language))
        return StaffAlertBrief(
            title=StaffAlertTitle(
                title.replace("{business}", str(self._business_name))
            ),
            detail=StaffAlertDetail(detail.replace("{changes}", changes)),
        )
