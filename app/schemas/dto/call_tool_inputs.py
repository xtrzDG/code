"""The input of the phone tool send_call_transcript (ACC-03)."""

from base_pydantic_schemas import ImmutableDTO


class SendCallTranscriptToolInput(ImmutableDTO):
    """send_call_transcript: no input; the call comes from the conversation."""
