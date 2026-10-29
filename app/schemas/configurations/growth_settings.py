from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.subscription_lifecycle.booleans import IsPauseEnabled


class GrowthSettings(ImmutableDTO):
    """
    The approved WhatsApp utility templates of the revenue features, for a
    customer whose 24-hour window is closed (each business's WhatsApp
    Business account registers them under these names; see `.env.example`):

    - `waitlist_template_name` (WHATSAPP_WAITLIST_TEMPLATE): a freed place
      held for a waiting customer; parameters business, date, time and the
      minutes the place is held;
    - `rebooking_template_name` (WHATSAPP_REBOOKING_TEMPLATE): a rebooking
      campaign's invitation back; parameter business.

    Without a name, WhatsApp carries such a message only inside the window;
    otherwise another connected messenger (Telegram) does, or it is skipped
    with its reason.

    `is_subscription_pause_enabled` (SUBSCRIPTION_PAUSE_ENABLED, off by
    default): owners may pause their subscription for the season and the
    cancel dialog offers the pause. The release that introduced the PAUSED
    status reads it everywhere but writes it only with this switch, turned
    on once no instance of the release before is left
    (docs/operations/deploys.md).
    """

    waitlist_template_name: WhatsAppTemplateName | None = None
    rebooking_template_name: WhatsAppTemplateName | None = None
    is_subscription_pause_enabled: IsPauseEnabled = False
