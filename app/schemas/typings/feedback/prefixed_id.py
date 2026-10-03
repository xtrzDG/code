"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class FeedbackRequestId(BasePrefixedTypedId):
    """
    Identifier of the request for feedback after one visit (a booking).

    Derived (UUID v5) from the business and the booking, so a visit is
    asked about at most once, however often the job looks at it.
    """

    prefix = "feedback_request"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class ReviewSettingsId(BasePrefixedTypedId):
    """
    Identifier of the review settings of one business (Settings → Reviews).

    Derived (UUID v5) from the business, so a business has one document.
    """

    prefix = "review_settings"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
