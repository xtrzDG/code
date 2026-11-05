from enum import StrEnum


class MetaConnectionPurpose(StrEnum):
    """
    What a Facebook sign-in started in the cabinet is for: WhatsApp
    Embedded Signup (a business number), or Facebook Login listing the
    owner's pages for Messenger and Instagram.
    """

    WHATSAPP = "whatsapp"
    PAGES = "pages"


class MetaConnectionRefusal(StrEnum):
    """
    Why finishing a Facebook sign-in was refused, as stable reason codes the
    cabinet explains: the sign-in is too old, used or someone else's
    (LINK_EXPIRED); Meta's platform is not set up on this server
    (NOT_CONFIGURED); a permission the owner unticked (PERMISSION_MISSING);
    no WhatsApp account or number came with it (NO_WHATSAPP_ACCOUNT,
    NO_WHATSAPP_NUMBER); the number has its own two-step PIN
    (WHATSAPP_PIN_MISMATCH); the chosen page is not offered or has no
    Instagram professional account (PAGE_NOT_FOUND, NO_INSTAGRAM_ACCOUNT).
    """

    LINK_EXPIRED = "meta_link_expired"
    NOT_CONFIGURED = "meta_not_configured"
    PERMISSION_MISSING = "meta_permission_missing"
    NO_WHATSAPP_ACCOUNT = "whatsapp_account_missing"
    NO_WHATSAPP_NUMBER = "whatsapp_number_missing"
    WHATSAPP_PIN_MISMATCH = "whatsapp_pin_mismatch"
    PAGE_NOT_FOUND = "meta_page_not_found"
    NO_INSTAGRAM_ACCOUNT = "instagram_account_missing"
