"""The team inbox: its views, saved-reply variables and refusal codes."""

from enum import StrEnum


class InboxView(StrEnum):
    """
    One way to look at a business's conversations in the team inbox.

    NEEDS_PERSON: the assistant handed the conversation to staff (an open
    handoff). REQUESTS: a request (lead) of the conversation is new or in
    progress. MINE: waiting for the team and assigned to the viewer.
    UNASSIGNED: waiting for the team and assigned to nobody. ALL: every
    conversation. A conversation waits for the team while it needs a
    person or has an open request.
    """

    NEEDS_PERSON = "needs_person"
    REQUESTS = "requests"
    MINE = "mine"
    UNASSIGNED = "unassigned"
    ALL = "all"


class QuickReplyVariable(StrEnum):
    """
    A value a saved reply can carry, written in braces in its text:
    {name} the customer's name, {booking_time} the start of the
    conversation's next booking in the business time zone, {business_name}.
    """

    NAME = "name"
    BOOKING_TIME = "booking_time"
    BUSINESS_NAME = "business_name"


class InboxRefusalCode(StrEnum):
    """Machine-readable reasons a team inbox change is refused."""

    # Someone changed the assignment since the caller read it (409): reload.
    ASSIGNMENT_CHANGED = "assignment_changed"
    # Staff may take or pass on unassigned conversations and their own,
    # not take a colleague's (403); the owner may.
    ASSIGNED_TO_COLLEAGUE = "assigned_to_colleague"
    # The chosen person is not a member of the business (422).
    NOT_A_MEMBER = "not_a_member"
    # Another saved reply already uses this shortcut (409).
    SHORTCUT_TAKEN = "shortcut_taken"
    # A saved reply names a variable the inbox does not fill (422).
    UNKNOWN_VARIABLE = "unknown_variable"
    # Two variants of one saved reply have the same language (422).
    DUPLICATE_LANGUAGE = "duplicate_language"
    # The business has as many saved replies as allowed (409).
    TOO_MANY_QUICK_REPLIES = "too_many_quick_replies"
    # Only the author of a note or the owner deletes it (403).
    NOT_NOTE_AUTHOR = "not_note_author"
