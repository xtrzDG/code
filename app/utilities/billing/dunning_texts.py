"""
The owners' notices about the retries of a declined automatic charge, in
every cabinet language (the owner text catalog): a retry was declined
(and when the next one is), the last one was, or the payment went through.
"""

from app.schemas.constants.payments import DunningNoticeKind
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.owner_texts import owner_text

DUNNING_TEXTS: dict[DunningNoticeKind, LocalizedText] = {
    DunningNoticeKind.RETRY_DECLINED: owner_text("billing.dunning.retry_declined"),
    DunningNoticeKind.LAST_RETRY_DECLINED: owner_text(
        "billing.dunning.last_retry_declined"
    ),
    DunningNoticeKind.PAYMENT_RECOVERED: owner_text(
        "billing.dunning.payment_recovered"
    ),
}
FULL_SERVICE_DEADLINE: LocalizedText = owner_text("billing.texts.full_service_deadline")
