"""How long each platform shows "typing…", so it can be shown again in time."""

from app.schemas.constants.channels import ChannelKind

# Telegram shows a chat action for about 5 s, Messenger and Instagram
# typing_on for about 20 s, the WhatsApp indicator for up to 25 s: each is
# sent again a little before it would disappear.
TYPING_REFRESH_SECONDS: dict[ChannelKind, float] = {
    ChannelKind.TELEGRAM: 4.0,
    ChannelKind.WHATSAPP: 20.0,
    ChannelKind.MESSENGER: 15.0,
    ChannelKind.INSTAGRAM: 15.0,
}
# Longer than any turn (the inbox lease): a stuck turn stops typing anyway.
MAX_TYPING_SECONDS: float = 180.0
