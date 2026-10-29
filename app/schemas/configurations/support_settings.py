from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.help.constrained_strings import SupportTelegramUsername
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import EmailAddress


class SupportSettings(ImmutableDTO):
    """
    How owners reach a person at the platform from the cabinet's "Help and
    support": a WhatsApp number (SUPPORT_WHATSAPP, E.164), a Telegram
    username (SUPPORT_TELEGRAM, without "@") and an e-mail address
    (SUPPORT_EMAIL). A channel left empty is not offered.
    """

    whatsapp_number: E164PhoneNumber | None = None
    telegram_username: SupportTelegramUsername | None = None
    email: EmailAddress | None = None
