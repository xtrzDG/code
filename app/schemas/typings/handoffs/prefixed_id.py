"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class HandoffId(BasePrefixedTypedId):
    """Random identifier of a handoff to a human."""

    prefix = "handoff"


class UnansweredQuestionId(BasePrefixedTypedId):
    """Random identifier of a customer question the assistant could not answer."""

    prefix = "unanswered_question"


# Keep abc order for all non example types, if possible.
