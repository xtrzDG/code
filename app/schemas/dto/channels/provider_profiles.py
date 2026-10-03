"""Profiles of the provider accounts a channel is connected with."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    TelegramBotUsername,
)
from app.schemas.typings.channels.strings import (
    MetaPageName,
    WhatsAppDisplayPhoneNumber,
)
from app.schemas.typings.sharing.constrained_strings import (
    InstagramUsername,
    MetaPageUsername,
)


class TelegramBotProfile(ImmutableDTO):
    """A Telegram bot as getMe describes it."""

    username: TelegramBotUsername


class MetaPageProfile(ImmutableDTO):
    """
    A Facebook page and its linked Instagram professional account, with
    their public usernames (None when the page or account has none).
    """

    page_id: MetaObjectId
    name: MetaPageName | None = None
    username: MetaPageUsername | None = None
    instagram_account_id: MetaObjectId | None = None
    instagram_username: InstagramUsername | None = None


class WhatsAppPhoneNumberProfile(ImmutableDTO):
    """A WhatsApp Cloud API business phone number."""

    phone_number_id: MetaObjectId
    display_phone_number: WhatsAppDisplayPhoneNumber | None = None
