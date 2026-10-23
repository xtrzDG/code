from app.contracts.subscription_lifecycle import OwnerWinBackFacilitatorContract
from app.facilitators.billing.owner_billing_notices import OwnerBillingNotices
from app.schemas.constants.subscription_lifecycle import WinBackStage
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.win_back_messages import WinBackMessage
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    WinBackRecipientCount,
)
from app.utilities.billing.win_back_texts import (
    CONVERSATIONS_LINE,
    KEPT_LINE,
    REASON_HINTS,
    WIN_BACK_TITLES,
)


class OwnerWinBackFacilitator(OwnerBillingNotices, OwnerWinBackFacilitatorContract):
    """
    Sends a win-back message the way every billing message reaches the
    owners (OwnerBillingNotices).

    The text names how many customers wrote since the cancellation, says
    everything set up is kept, adds the second message's hint for the
    reason given, and ends with a signed link to the billing page. Each
    stage reaches each address once (its outbox ids derive from the
    subscription and the stage). One failing recipient never stops the
    others.
    """

    def send(
        self, business: BusinessDocument, message: WinBackMessage
    ) -> WinBackRecipientCount:
        subject = StaffAlertSubject(
            f"win_back:{message.subscription_id}_{message.stage.value}"
        )
        return WinBackRecipientCount(
            self.notify_owners(
                business,
                subject,
                lambda language: self._lines(business, message, language),
                "A win-back message",
            )
        )

    def _lines(
        self, business: BusinessDocument, message: WinBackMessage, language: LanguageTag
    ) -> list[str]:
        values: dict[str, str] = {
            "business": str(business.name),
            "count": str(int(message.conversations_since)),
        }
        lines: list[str] = [self.say(WIN_BACK_TITLES[message.stage], language, values)]
        lines.append("")
        if int(message.conversations_since) > 0:
            lines.append(self.say(CONVERSATIONS_LINE, language, values))

        lines.append(self.say(KEPT_LINE, language, values))
        hint: LocalizedText | None = (
            None if message.reason is None else REASON_HINTS.get(message.reason)
        )
        if message.stage is WinBackStage.DAY_30 and hint is not None:
            lines.append(self.say(hint, language, values))

        return lines
