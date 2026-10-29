"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class ReviewLinkToken(BaseConstrainedTypedString):
    """
    The random public token of one customer's review link: the address
    they open (`/v1/public/reviews/{token}`) names it instead of any id, so
    it reveals nothing and cannot be guessed (128 bits, base64url).

    Example:
        token = ReviewLinkToken("q3Jd8sLq0Pz-Xb7W2nVc1A")
    """

    min_length = 22
    max_length = 22
    pattern = r"^[A-Za-z0-9_-]{22}$"


class ReviewRedirectUrl(BaseConstrainedTypedString):
    """
    The platform's address a customer opens to reach the business's review
    page: it counts the visit, then redirects.

    Example:
        url = ReviewRedirectUrl(
            "https://api.example.com/v1/public/reviews/q3Jd8sLq0Pz-Xb7W2nVc1A"
        )
    """

    min_length = 10
    max_length = 2048
    pattern = r"^https?://[^\s/]+(/[^\s]*)?$"


# Keep abc order for all non example types, if possible.
