"""Whether the phone assistant may take a new call (concept section 7)."""

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelStatus
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.billing import PlanDefinition


def find_voice_refusal(
    business: BusinessDocument,
    published_version: AssistantVersionDocument | None,
    plan: PlanDefinition,
    phone_channel: ChannelDocument | None,
) -> str | None:
    """
    Why a new call must not be answered, or None when it may: the business
    is live, its published version has voice, its plan includes voice and
    its phone number is connected. A paused business, a downgrade to a plan
    without voice, a version without voice or a disconnected number all
    switch the phone assistant off.
    """

    if business.status is not BusinessStatus.LIVE:
        return f"{business.name} is not live ({business.status.value})."

    if published_version is None or not published_version.is_voice_enabled:
        return f"The live assistant of {business.name} has no voice."

    if not plan.is_voice_included:
        return f"The plan of {business.name} does not include voice."

    if phone_channel is None or phone_channel.status is not ChannelStatus.CONNECTED:
        return f"{business.name} has no connected phone number."

    return None
