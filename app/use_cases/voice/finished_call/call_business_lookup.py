"""The business a finished call belongs to."""

import logging

from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.voice_webhooks import FinishedCallReport
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber

logger: logging.Logger = logging.getLogger(__name__)


def find_call_business(
    channel_repo: ChannelRepoContract,
    business_repo: BusinessRepoContract,
    assistant_version_repo: AssistantVersionRepoContract,
    assistant_number: E164PhoneNumber | None,
    report: FinishedCallReport,
) -> BusinessDocument | None:
    """
    The business whose connected line the call reached, unless an agent of
    another business answered it.
    """

    if assistant_number is None:
        logger.info(
            "Call %s has no assistant number; it is not stored.",
            report.provider_call_id,
        )
        return None

    channel: ChannelDocument | None = channel_repo.find_by_external_id(
        ChannelKind.PHONE,
        ChannelExternalId(str(assistant_number)),
    )
    # A call that ended after the number was turned off (or broke) is
    # still the business's call: it is stored and its minutes metered.
    business: BusinessDocument | None = (
        None if channel is None else business_repo.get(channel.business_id)
    )
    if business is None:
        logger.info(
            "Call %s reached a number no business has connected.",
            report.provider_call_id,
        )
        return None

    known_agent_ids = {
        version.voice_agent_id
        for version in assistant_version_repo.list_by_business(business.id)
        if version.voice_agent_id is not None
    }
    if (
        report.agent_id is not None
        and known_agent_ids
        and report.agent_id not in known_agent_ids
    ):
        logger.warning(
            "Call %s was answered by an agent of another business; ignored.",
            report.provider_call_id,
        )
        return None

    return business
