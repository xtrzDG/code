"""Keep abc order."""

from base_typed_string import BaseTypedString


class EvalCheckNote(BaseTypedString):
    """
    English note of a failed evaluation criterion, e.g. "The reply does
    not mention 25 GEL."
    """


class ExpectedToolFieldValue(BaseTypedString):
    """
    One acceptable value of a tool input field as the dataset writes it
    ("2", "2026-10-08", "Nino"); compared as text, as a number or as a
    phone number by the scorer.
    """


class ForbiddenReplyValue(BaseTypedString):
    """A text the assistant must never write in a scenario ("%", "customer_text")."""


class LlmCassetteMissReason(BaseTypedString):
    """
    Why a replayed model call found no recording: the instruction or the
    tools changed (with a diff), or the conversation took another path.
    """


class LlmTranscriptTail(BaseTypedString):
    """
    The last turn of a recorded model call in canonical form, kept to
    explain why a replayed conversation took another path.
    """


class RequiredReplyFact(BaseTypedString):
    """A text the assistant's replies must contain, e.g. "23:00" or "ლარ"."""
