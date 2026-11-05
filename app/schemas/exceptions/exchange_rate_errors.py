from app.schemas.exceptions.application_errors import ExternalServiceError


class ExchangeRateFeedError(ExternalServiceError):
    """
    A central bank's rate feed could not be read (refused, unreachable, an
    error status) or did not look like the feed (no date, no rates, a rate
    that is not a positive number). The refresh keeps the rates it has.
    """
