"""
What a Facebook sign-in of the Channels page asks Meta for: the Graph API
version, the permissions of the page picker and of WhatsApp Embedded
Signup, and the platform's Meta app as configured.
"""

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.channels.meta_provider import MetaAppCredentials
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaGraphApiVersion,
    MetaPermissionName,
)

# The version the Graph clients speak (app/clients/meta/meta_graph_client.py)
# and the cabinet's Facebook SDK starts with.
META_GRAPH_API_VERSION: MetaGraphApiVersion = MetaGraphApiVersion("v23.0")
# Embedded Signup's granular permissions: the WhatsApp Business Accounts the
# business shared are this permission's targets.
WHATSAPP_MANAGEMENT: MetaPermissionName = MetaPermissionName(
    "whatsapp_business_management"
)
WHATSAPP_MESSAGING: MetaPermissionName = MetaPermissionName(
    "whatsapp_business_messaging"
)
# The page picker: list the pages, answer their Messenger and Instagram
# messages, subscribe the app to them, and read and answer Instagram comments.
PAGE_PERMISSIONS: tuple[MetaPermissionName, ...] = tuple(
    MetaPermissionName(name)
    for name in (
        "pages_show_list",
        "pages_messaging",
        "pages_manage_metadata",
        "business_management",
        "instagram_basic",
        "instagram_manage_messages",
        "instagram_manage_comments",
    )
)


def meta_app_of(settings: AppSettings) -> MetaAppCredentials | None:
    """The platform's Meta app, or None while META_APP_ID or its secret is unset."""

    if settings.meta_app_id is None or settings.meta_app_secret is None:
        return None

    return MetaAppCredentials(
        app_id=settings.meta_app_id, app_secret=settings.meta_app_secret
    )
