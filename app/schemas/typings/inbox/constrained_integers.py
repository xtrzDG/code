"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class AssignmentRevision(BaseConstrainedTypedInt):
    """
    How many times the assignment of a conversation changed: the version a
    reassignment must name, so two people assigning at once cannot both win
    (compare and set).

    Example:
        revision = AssignmentRevision(3)
    """

    ge = 0


class AwaitingConversationCount(BaseConstrainedTypedInt):
    """
    Conversations waiting for the team (a person is needed or a request is
    open) that one member is assigned: their current workload.

    Example:
        load = AwaitingConversationCount(4)
    """

    ge = 0


class ConversationNoteCount(BaseConstrainedTypedInt):
    """
    How many internal notes the team left on one conversation.

    Example:
        notes = ConversationNoteCount(2)
    """

    ge = 0


# Keep abc order for all non example types, if possible.
