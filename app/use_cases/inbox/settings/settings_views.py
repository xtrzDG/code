"""The inbox settings as the cabinet reads them."""

from app.schemas.domain.inbox_settings import InboxSettingsDocument
from app.schemas.dto.inbox.inbox_settings import InboxSettingsView
from app.schemas.typings.businesses.prefixed_id import BusinessId


def build_settings_view(
    business_id: BusinessId,
    settings: InboxSettingsDocument | None,
) -> InboxSettingsView:
    """The stored settings, the defaults (no auto-assignment) without any."""

    if settings is None:
        return InboxSettingsView(business_id=business_id)

    return InboxSettingsView(
        business_id=business_id,
        auto_assign_new_handoffs=settings.auto_assign_new_handoffs,
        auto_assign_new_requests=settings.auto_assign_new_requests,
        auto_assign_user_ids=list(settings.auto_assign_user_ids),
    )
