"""Keep abc order."""

from base_typed_string import BaseTypedString


class HandoffQuotedText(BaseTypedString):
    """
    Words quoted in a handoff the platform created, as they were written:
    the customer's message the assistant could not answer, or the reply
    that never reached the customer. Personal data.
    """


class HandoffSummary(BaseTypedString):
    """Short retelling of a conversation for the staff member."""


class ManagerContactAddress(BaseTypedString):
    """
    Address on the manager's channel.

    Telegram chat id, E.164 phone for WhatsApp/SMS, or e-mail address.
    """


class ManagerName(BaseTypedString):
    """Name of a staff member who receives handoffs."""


class UnansweredQuestionText(BaseTypedString):
    """Customer question that the business knowledge did not answer."""


# Keep abc order for all non example types, if possible.
