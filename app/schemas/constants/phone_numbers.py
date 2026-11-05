"""Phone numbers the platform rents for a business's assistant (W21)."""

from enum import StrEnum


class PhoneNumberProvider(StrEnum):
    """
    The carrier a number is rented from. Twilio sells numbers through its
    API and the voice platform (ElevenLabs) imports them natively.
    """

    TWILIO = "twilio"


class PhoneNumberType(StrEnum):
    """
    What kind of number: a city (geographic) line, a mobile number, or a
    toll-free one. The carrier's price list prices each kind per country.
    """

    LOCAL = "local"
    MOBILE = "mobile"
    TOLL_FREE = "toll_free"


class PhoneNumberStatus(StrEnum):
    """
    ACTIVE: rented, answering for the business. RELEASING: given up (the
    phone channel was turned off, or nobody pays for it any more); the
    maintenance job returns it to the carrier and the voice platform.
    RELEASED: returned; the row stays as the record of the rental.
    """

    ACTIVE = "active"
    RELEASING = "releasing"
    RELEASED = "released"


class PhoneNumberAvailability(StrEnum):
    """
    How a business gets a number in a country.

    SELF_SERVE: the owner picks one in the cabinet and has it at once.
    REQUIRES_DOCUMENTS: the country's regulator wants the business's papers
    (an address or a company proof), so the platform team arranges the
    number from an admin request. ON_REQUEST: this server rents no numbers
    by itself (no carrier configured) or the carrier sells none there, so
    the team arranges it too.
    """

    SELF_SERVE = "self_serve"
    REQUIRES_DOCUMENTS = "requires_documents"
    ON_REQUEST = "on_request"


class PhoneNumberRequestStatus(StrEnum):
    """An owner's request for a number the team arranges by hand."""

    OPEN = "open"
    DONE = "done"
    CANCELLED = "cancelled"


class PhoneNumberReleaseReason(StrEnum):
    """
    Why a rented number is given up: the owner turned the phone channel off
    (OWNER), or a rental month began while nobody paid for the service
    (UNPAID: no paid subscription and no running trial).
    """

    OWNER = "owner"
    UNPAID = "unpaid"


class RentalMonthOutcome(StrEnum):
    """
    What happens when a rental month of a number begins: billed to the
    business's subscription (BILLED), on the platform (INCLUDED: the first
    month of a number taken before the first payment, or a month of a
    running trial), or the number goes back (RELEASED).
    """

    BILLED = "billed"
    INCLUDED = "included"
    RELEASED = "released"
