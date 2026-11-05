"""What a failed processing of an inbox event means for the event."""

from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.deliveries.strings import InboundErrorText

MAX_ERROR_TEXT_LENGTH: int = 500


def is_final_inbound_failure(error: Exception, is_final_attempt: bool) -> bool:
    """
    A refusal (the business is not live, the message or payload is
    invalid) is final at once; a temporary failure (a provider or the
    database, an unexpected error) is final only on the job's last attempt.
    """

    if isinstance(error, ApplicationError) and not isinstance(
        error, ExternalServiceError
    ):
        return True

    return is_final_attempt


def is_inbound_refusal(error: Exception) -> bool:
    """A failure that no later attempt can fix."""

    return isinstance(error, ApplicationError) and not isinstance(
        error, ExternalServiceError
    )


def describe_inbound_error(error: Exception) -> InboundErrorText:
    text: str = " ".join(str(error).split()) or type(error).__name__
    if len(text) > MAX_ERROR_TEXT_LENGTH:
        text = text[: MAX_ERROR_TEXT_LENGTH - 1].rstrip() + "…"

    return InboundErrorText(text)
