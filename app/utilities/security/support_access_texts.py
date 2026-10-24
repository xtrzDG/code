"""
What a business's team hears when platform support opens its cabinet:
who (or "Platform support"), why, and that it is read-only for an hour.
No customer detail; it may show on a locked screen.
"""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertTextsContract
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.typings.access.constrained_strings import SupportAccessReason
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.schemas.typings.users.strings import UserDisplayName
from app.utilities.knowledge.localized_texts import build_localized_text

SUPPORT_OPENED_TITLE: LocalizedText = build_localized_text(
    en="Platform support opened your cabinet",
    ru="Поддержка платформы открыла ваш кабинет",
    ka="პლატფორმის მხარდაჭერამ თქვენი კაბინეტი გახსნა",
)
SUPPORT_OPENED_DETAIL: LocalizedText = build_localized_text(
    en=(
        "{who}: “{reason}”. Read-only, for an hour; you see it in a banner in "
        "the cabinet and can end it there."
    ),
    ru=(
        "{who}: «{reason}». Только просмотр, на час; это видно в баннере в "
        "кабинете, там же доступ можно закрыть."
    ),
    ka=(
        "{who}: „{reason}“. მხოლოდ ნახვა, ერთი საათით; ეს კაბინეტის ბანერშია "
        "ნაჩვენები და იქვე შეგიძლიათ დახუროთ."
    ),
)
PLATFORM_SUPPORT: LocalizedText = build_localized_text(
    en="Platform support",
    ru="Поддержка платформы",
    ka="პლატფორმის მხარდაჭერა",
)


class SupportAccessTexts(StaffAlertTextsContract):
    """The notice of one support look into the cabinet, in any language."""

    def __init__(
        self,
        resolver: LocalizedTextResolverContract,
        admin_name: UserDisplayName | None,
        reason: SupportAccessReason,
    ) -> None:
        self._resolver: LocalizedTextResolverContract = resolver
        self._admin_name: UserDisplayName | None = admin_name
        self._reason: SupportAccessReason = reason

    def brief(self, language: LanguageTag) -> StaffAlertBrief:
        support: str = str(self._resolver.resolve(PLATFORM_SUPPORT, language))
        who: str = f"{support} ({self._admin_name})" if self._admin_name else support
        return StaffAlertBrief(
            title=StaffAlertTitle(
                self._resolver.resolve(SUPPORT_OPENED_TITLE, language)
            ),
            detail=StaffAlertDetail(
                str(self._resolver.resolve(SUPPORT_OPENED_DETAIL, language))
                .replace("{who}", who)
                .replace("{reason}", str(self._reason))
            ),
        )

    def detailed(self, language: LanguageTag) -> MessageText:
        lines: StaffAlertBrief = self.brief(language)
        return MessageText(f"{lines.title}\n{lines.detail}")
