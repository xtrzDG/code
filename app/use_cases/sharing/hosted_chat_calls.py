"""The phone side of a hosted chat's privacy notice."""

from app.contracts.registries import CountryRegistryContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.localization import RecordingConsentRule
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.sharing import HostedChatPhoneCalls
from app.schemas.exceptions.application_errors import UnknownCountryError


def describe_phone_calls(
    business: BusinessDocument,
    channels: list[ChannelDocument],
    version_repo: AssistantVersionRepoContract,
    country_registry: CountryRegistryContract,
) -> HostedChatPhoneCalls | None:
    """
    How the business's calls are recorded, when its AI assistant answers
    them: its live version has voice and its phone number is connected.
    The consent rule is its country's (all-party consent where the
    platform does not know the country, as the call's greeting does).
    """

    if business.published_assistant_version_id is None or not any(
        channel.kind is ChannelKind.PHONE and channel.status is ChannelStatus.CONNECTED
        for channel in channels
    ):
        return None

    version: AssistantVersionDocument | None = version_repo.get(
        business.id, business.published_assistant_version_id
    )
    if version is None or not version.is_voice_enabled:
        return None

    try:
        rule: RecordingConsentRule = country_registry.get(
            business.country_code
        ).recording_consent_rule
    except UnknownCountryError:
        rule = RecordingConsentRule.ALL_PARTY_CONSENT

    return HostedChatPhoneCalls(recording_consent_rule=rule)
