"""One voice agent per business, kept across versions (concept section 7)."""

from collections.abc import Sequence

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.typings.assistants.constrained_integers import VoiceAgentRevision
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


# How the platform builds a voice agent today. Raise it when what an agent
# is built from changes (its tools, its call settings); `resync_voice_agents`
# then sets up every live agent of an older revision again.
# 1 (W20): list_my_bookings and join_waitlist for a version assembled
#   before them, and decline_recording on every agent.
# 2 (W22): the tuning (model, temperature, a voice per language, speech
#   recognition keywords, turn timeout) and the evaluation of every call.
# 3: the agent's authentication (signed URLs only), its call caps (calls at
#   once and a day), the transfer to the call's transfer_number variable
#   only while open and allowed, the Current call block without the
#   caller's name or bookings, no tools bound to the caller id
#   (list_my_bookings, cancel_booking, reschedule_booking) and the provider
#   recording the voice only while the business records calls.
# 4: the provider's retention backstop (`privacy.retention_days`: a day, a
#   week while the business records calls) and the filler said when an
#   answer is late (`turn.soft_timeout_config`).
# 5: send_link on every agent (a version assembled without links gets it),
#   so a caller who asks for the privacy notice the greeting offers gets
#   its link, the platform's hosted notice when the business stored none.
#   The rule for "repeat" and "speak slower" is part of the phone
#   instruction a version stores, which an agent of an older revision keeps
#   until the owner publishes again: no revision brings it.
VOICE_AGENT_REVISION: VoiceAgentRevision = VoiceAgentRevision(5)


def needs_voice_agent_resync(version: AssistantVersionDocument) -> bool:
    """A version with a voice agent set up before the current revision."""

    return (
        version.is_voice_enabled
        and version.voice_agent_id is not None
        and (
            version.voice_agent_revision is None
            or int(version.voice_agent_revision) < int(VOICE_AGENT_REVISION)
        )
    )
