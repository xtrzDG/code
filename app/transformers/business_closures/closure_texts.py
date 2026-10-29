"""
The notices a business's owners get about its closure, in every cabinet
language (the owner text catalog). Placeholders: {actor}, {business},
{date}.
"""

from app.schemas.constants.business_closures import ClosureNoticeKind
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.owner_texts import owner_text

CLOSURE_NOTICE_TEXTS: dict[ClosureNoticeKind, LocalizedText] = {
    ClosureNoticeKind.OPENED_BY_OWNER: owner_text("closure.notices.opened_by_owner"),
    ClosureNoticeKind.OPENED_UNPAID: owner_text("closure.notices.opened_unpaid"),
    ClosureNoticeKind.CANCELLED: owner_text("closure.notices.cancelled"),
    ClosureNoticeKind.REOPENED_PAID: owner_text("closure.notices.reopened_paid"),
}
