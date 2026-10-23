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


class PhoneNumberOfferToken(BaseConstrainedTypedString):
    """
    The platform's signature on one number it offered a business: until
    when the offer holds (Unix seconds), a dot, and a truncated HMAC over
    the business, the number, its kind and that time (base64url). Taking a
    number needs the token of its offer, so the kind (and with it the
    price and whether papers are needed) is the one the search found.

    Example:
        token = PhoneNumberOfferToken("1767225600.AAAAAAAAAAAAAAAAAAAAAA")
    """

    min_length = 24
    max_length = 33
    pattern = r"^[0-9]{1,10}\.[A-Za-z0-9_-]{22}$"


class RentedLineNumber(BaseConstrainedTypedString):
    """
    The E.164 number of a line the platform rents for a business from a
    carrier: the business's own phone line, never a person's number (so
    an erasure of a customer's data never looks for it). Built from the
    number the carrier sold, which the phone number parser validated.

    Example:
        line = RentedLineNumber("+15125550142")
    """

    min_length = 8
    max_length = 16
    pattern = r"^\+[1-9][0-9]{6,14}$"


# Keep abc order for all non example types, if possible.
