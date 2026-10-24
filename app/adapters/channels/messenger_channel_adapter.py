from typing import ClassVar

from app.adapters.channels.meta_page_channel_adapter import MetaPageChannelAdapter
from app.schemas.constants.channels import ChannelKind


class MessengerChannelAdapter(MetaPageChannelAdapter):
    """
    Facebook Messenger of a business page: webhook object "page", the page
    id as the account, replies of at most 2000 characters each through the
    Send API with the page token.
    """

    webhook_object: ClassVar[str] = "page"
    channel_kind: ClassVar[ChannelKind] = ChannelKind.MESSENGER
    message_limit: ClassVar[int] = 2000
