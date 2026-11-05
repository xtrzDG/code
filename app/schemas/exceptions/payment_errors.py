"""Errors of the payment provider (Flitt) that say nothing about its health."""

from app.schemas.exceptions.application_errors import ExternalServiceError


class PaymentProviderRefusedError(ExternalServiceError):
    """
    The payment provider answered and refused this call (an HTTP 4xx, or an
    answer with the status "failure": a currency the merchant account does
    not take, an order already stopped). It is up: the same call again
    gets the same answer.
    """


class PaymentsNotConfiguredError(ExternalServiceError):
    """
    Online payments are not set up (no merchant credentials, or no public
    base URL for the provider's notifications): no call was made.
    """
