"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class PhoneNumberCityQuery(BaseConstrainedTypedString):
    """
    The city an owner would like the number in, as typed in the cabinet:
    narrows the carrier's search, and tells the platform team where to look
    when the number is arranged by hand.

    Example:
        city = PhoneNumberCityQuery("Austin")
    """

    min_length = 1
    max_length = 60
    pattern = r"^[^\x00-\x1f\x7f]*\S[^\x00-\x1f\x7f]*$"


class PhoneNumberLabel(BaseConstrainedTypedString):
    """
    The name a rented number carries at the carrier (Twilio's FriendlyName,
    at most 64 characters) and on the voice platform's list, so the platform
    team recognizes whose line it is: the business's name.
    """

    min_length = 1
    max_length = 64


# Keep abc order for all non example types, if possible.
