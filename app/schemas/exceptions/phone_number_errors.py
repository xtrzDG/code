"""Why a number could not be taken."""

from app.schemas.exceptions.application_errors import ConflictError


class PhoneNumberUnavailableError(ConflictError):
    """
    The carrier no longer rents the chosen number (someone took it since the
    search, or it was withdrawn): the owner searches again and picks another.
    """


class PhoneNumberPriceChangedError(ConflictError):
    """
    The monthly price of the chosen kind of number is not the one the
    cabinet showed (the carrier's price or the exchange rate moved since the
    search): the owner looks at the new price before taking the number.
    """
