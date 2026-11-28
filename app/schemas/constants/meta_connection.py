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


class WhatsAppTokenRefreshOutcome(StrEnum):
    """
    What renewing a WhatsApp Embedded Signup token that ends soon came to:
    Meta issued a new one and it was stored (REFRESHED); Meta refused, the
    new token failed its check or the stored one cannot be read, so the old
    one stays (REFUSED); Meta could not be asked now (a rate limit, an open
    circuit, an outage), so the next run tries again (DEFERRED); the owner
    reconnected or switched the channel off meanwhile, so the new token was
    dropped (REPLACED). Never stored: it names log lines and picks the
    owner's notice.
    """

    REFRESHED = "refreshed"
    REFUSED = "refused"
    DEFERRED = "deferred"
    REPLACED = "replaced"


class WhatsAppTokenNoticeStage(StrEnum):
    """
    Which reminder the owners of a WhatsApp number get about its token:
    Meta would not renew it (REFRESH_REFUSED), it ends within three days
    (ENDING), it ended and the number needs connecting again (ENDED). Each
    stage reaches each recipient once per token (it is part of the notice's
    subject). Never stored.
    """

    REFRESH_REFUSED = "refresh_refused"
    ENDING = "ending"
    ENDED = "ended"
