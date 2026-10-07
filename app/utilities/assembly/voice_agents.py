"""One voice agent per business, kept across versions (concept section 7)."""

from collections.abc import Sequence

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.typings.assistants.strings import VoiceAgentId


def find_existing_voice_agent_id(
    versions: Sequence[AssistantVersionDocument],
    version: AssistantVersionDocument,
) -> VoiceAgentId | None:
    """
    The business's voice agent: the one of the published version, else the
    newest version that has one (the version being published included).
    """

    for candidate in versions:
        if (
            candidate.status is AssistantVersionStatus.PUBLISHED
            and candidate.voice_agent_id is not None
        ):
            return candidate.voice_agent_id

    candidates: list[AssistantVersionDocument] = [
        candidate
        for candidate in [*versions, version]
        if candidate.voice_agent_id is not None
    ]
    if not candidates:
        return None

    newest: AssistantVersionDocument = max(
        candidates,
        key=lambda candidate: int(candidate.version_number),
    )
    return newest.voice_agent_id
