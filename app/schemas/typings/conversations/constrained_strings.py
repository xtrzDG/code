"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class ConversationSearchText(BaseConstrainedTypedString):
    """
    What staff type to find conversations: part of a customer's name, phone
    digits in any format, or words of a message, in any script.

    Example:
        search = ConversationSearchText("нино 555")
    """

    min_length = 1
    max_length = 200


class ConversationSummaryText(BaseConstrainedTypedString):
    """
    What one conversation was about, in at most 300 characters: written by
    a cheap model once the conversation has been quiet for two hours, and
    read by the assistant when the customer comes back (customer memory).

    Example:
        summary = ConversationSummaryText(
            "Asked about a table for 4 on Saturday; booked 20:00 by the window."
        )
    """

    min_length = 1
    max_length = 300
    pattern = r"\S"


class OwnerTestChatSessionKey(BaseConstrainedTypedString):
    """
    Key that separates parallel owner test chats of one user, e.g. "tab-2".

    Example:
        key = OwnerTestChatSessionKey("tab-2")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[A-Za-z0-9][A-Za-z0-9_\-]*$"


class RecordingMediaType(BaseConstrainedTypedString):
    """
    Audio media type of a call recording as it is played back, e.g.
    "audio/mpeg" for the MP3 the voice platform keeps.

    Example:
        media_type = RecordingMediaType("audio/mpeg")
    """

    min_length = 7
    max_length = 100
    pattern = r"^audio/[a-z0-9][a-z0-9.+\-]*$"


class StaffReplyText(BaseConstrainedTypedString):
    """
    Text an owner or staff member writes to a customer from the cabinet;
    at least one visible character.

    Example:
        reply = StaffReplyText("Yes, we will keep the table until 20:30.")
    """

    min_length = 1
    max_length = 4000
    pattern = r"\S"


class StaffTemplateReplyText(BaseConstrainedTypedString):
    """
    A staff reply as the single body parameter of a WhatsApp message
    template: one line (WhatsApp refuses line breaks, tabs and more than
    four spaces in a row in template parameters), at most 1024 characters.

    Example:
        reply = StaffTemplateReplyText("Your table for Saturday is confirmed.")
    """

    min_length = 1
    max_length = 1024
    pattern = r"\A(?!.* {5})[^\t\n\r]*\S[^\t\n\r]*\Z"


# Keep abc order for all non example types, if possible.
