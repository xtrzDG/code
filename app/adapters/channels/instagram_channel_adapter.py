from typing import ClassVar

from app.adapters.channels.meta_page_channel_adapter import MetaPageChannelAdapter
from app.schemas.constants.channels import ChannelKind


class InstagramChannelAdapter(MetaPageChannelAdapter):
    """
    Instagram Direct of a professional account linked to a Facebook page:
    webhook object "instagram", the Instagram account id as the account,
    replies of at most 1000 characters each through the page token's Send
    API.
    """

    webhook_object: ClassVar[str] = "instagram"
    channel_kind: ClassVar[ChannelKind] = ChannelKind.INSTAGRAM
    message_limit: ClassVar[int] = 1000
