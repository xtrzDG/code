"""The review link a customer opens: counted, then redirected."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.feedback.booleans import IsLinkPreviewRequest
from app.schemas.typings.feedback.constrained_strings import ReviewLinkToken


class ReviewLinkVisit(ImmutableDTO):
    """
    Someone opened a review link. A messenger fetching it for a link
    preview (`is_link_preview`) is redirected the same way but not counted.
    """

    token: ReviewLinkToken
    is_link_preview: IsLinkPreviewRequest = False


class ReviewLinkTarget(ImmutableDTO):
    """Where the link leads now: the business's current review page."""

    url: WebLink
