"""The website chat a visitor writes to: switched on, its assistant live."""

from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.channels.delivery_targets import find_business_channel


def require_open_widget_chat(
    business_repo: BusinessRepoContract,
    channel_repo: ChannelRepoContract,
    business_id: BusinessId,
) -> BusinessDocument:
    """
    The business whose website chat is switched on (its web chat channel
    connected).

    Raises:
        NotFoundError: an unknown business or a chat switched off (the same
            answer for both, so business ids cannot be probed).
    """

    business, _ = find_open_widget_chat(business_repo, channel_repo, business_id)
    return business


def find_open_widget_chat(
    business_repo: BusinessRepoContract,
    channel_repo: ChannelRepoContract,
    business_id: BusinessId,
) -> tuple[BusinessDocument, ChannelDocument]:
    """
    The business and its connected website chat channel.

    Raises:
        NotFoundError: an unknown business or a chat switched off (the same
            answer for both, so business ids cannot be probed).
    """

    business: BusinessDocument | None = business_repo.get(business_id)
    channel: ChannelDocument | None = (
        None
        if business is None
        else find_business_channel(channel_repo, business.id, ChannelKind.WEB_CHAT)
    )
    if (
        business is None
        or channel is None
        or channel.status is not ChannelStatus.CONNECTED
    ):
        raise NotFoundError("This chat is not available.")

    return business, channel


def require_live_assistant(business: BusinessDocument) -> None:
    """
    Raises:
        ConflictError: the business's assistant is not live (a turn would
            refuse the message, so the widget hears it at once).
    """

    if business.status is not BusinessStatus.LIVE:
        raise ConflictError(f"The assistant of {business.name} is not live.")
