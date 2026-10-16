"""Result and transcript of a finished phone call."""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import CallOutcome, MessageAuthor
from app.schemas.dto.voice_webhooks import FinishedCallTranscriptLine
from app.schemas.typings.conversations.strings import CallTranscriptText

# A call shorter than this, or where the caller never spoke, was abandoned.
MIN_INFORMATIVE_CALL_SECONDS: int = 10
SECONDS_PER_MINUTE: int = 60


def determine_call_outcome(
    has_booking: bool,
    has_lead: bool,
    has_handoff: bool,
    called_tools: list[AssistantToolName],
    transcript: list[FinishedCallTranscriptLine],
    duration_seconds: int,
) -> CallOutcome:
    """
    What the call produced, most valuable first: a booking, a lead for a
    manager, a handoff to staff, a question the knowledge did not answer;
    otherwise the caller got information, or hung up early.
    """

    if has_booking:
        return CallOutcome.BOOKING

    if has_lead:
        return CallOutcome.LEAD

    if has_handoff or AssistantToolName.HANDOFF_TO_HUMAN in called_tools:
        return CallOutcome.HANDOFF

    if AssistantToolName.RECORD_UNANSWERED_QUESTION in called_tools:
        return CallOutcome.UNANSWERED_QUESTION

    caller_spoke: bool = any(
        line.author is MessageAuthor.CUSTOMER for line in transcript
    )
    if not caller_spoke or duration_seconds < MIN_INFORMATIVE_CALL_SECONDS:
        return CallOutcome.ABANDONED

    return CallOutcome.INFORMATION


def render_call_transcript(
    transcript: list[FinishedCallTranscriptLine],
) -> CallTranscriptText | None:
    """ "[01:05] customer: ..." lines; None for a call without speech."""

    if not transcript:
        return None

    rendered_lines: list[str] = []
    for line in transcript:
        minutes, seconds = divmod(int(line.offset_seconds), SECONDS_PER_MINUTE)
        rendered_lines.append(
            f"[{minutes:02d}:{seconds:02d}] {line.author.value}: {line.text}"
        )

    return CallTranscriptText("\n".join(rendered_lines))
