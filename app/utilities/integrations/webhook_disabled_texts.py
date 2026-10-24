"""
What owners hear when an outbound webhook endpoint is switched off on its
own: which address (its note or host, nothing of its path), why (failed
attempts in a row, or the receiver's 410 Gone) and where to switch it on
again. Nothing about customers; it may show on a locked screen.
"""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertTextsContract
from app.schemas.constants.integrations import WebhookDeliveryProblem
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.integrations.constrained_integers import WebhookFailureCount
from app.schemas.typings.integrations.strings import WebhookEndpointName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.utilities.localization.owner_texts import owner_text

WEBHOOK_DISABLED_TITLE: LocalizedText = owner_text(
    "notifications.webhook_disabled.title"
)
FAILURES_DETAIL: LocalizedText = owner_text(
    "notifications.webhook_disabled.failures_detail"
)
GONE_DETAIL: LocalizedText = owner_text("notifications.webhook_disabled.gone_detail")


class WebhookDisabledTexts(StaffAlertTextsContract):
    """The notice of one switched-off endpoint, in any language."""

    def __init__(
        self,
        resolver: LocalizedTextResolverContract,
        business_name: BusinessName,
        endpoint: WebhookEndpointName,
        failures: WebhookFailureCount,
        problem: WebhookDeliveryProblem | None,
    ) -> None:
        self._resolver: LocalizedTextResolverContract = resolver
        self._business_name: BusinessName = business_name
        self._endpoint: WebhookEndpointName = endpoint
        self._failures: WebhookFailureCount = failures
        self._problem: WebhookDeliveryProblem | None = problem

    def detailed(self, language: LanguageTag) -> MessageText:
        lines: StaffAlertBrief = self.brief(language)
        return MessageText(f"{lines.title}\n{lines.detail}")

    def brief(self, language: LanguageTag) -> StaffAlertBrief:
        title: str = str(self._resolver.resolve(WEBHOOK_DISABLED_TITLE, language))
        detail: str = str(
            self._resolver.resolve(
                GONE_DETAIL
                if self._problem is WebhookDeliveryProblem.GONE
                else FAILURES_DETAIL,
                language,
            )
        )
        return StaffAlertBrief(
            title=StaffAlertTitle(
                title.replace("{business}", str(self._business_name))
            ),
            detail=StaffAlertDetail(
                detail.replace("{failures}", str(int(self._failures))).replace(
                    "{endpoint}", str(self._endpoint)
                )
            ),
        )
