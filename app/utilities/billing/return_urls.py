"""Which pages a payer's browser may be sent back to after paying."""

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_strings import PaymentReturnUrl


def list_return_origins(app_settings: AppSettings) -> list[str]:
    """Cabinet origins (CORS_ALLOWED_ORIGINS) and the API's own address."""

    origins: list[str] = [
        str(origin).rstrip("/") for origin in app_settings.cors_allowed_origins
    ]
    if app_settings.app_base_url is not None:
        origins.append(str(app_settings.app_base_url).rstrip("/"))

    return origins


def require_allowed_return_url(
    return_url: PaymentReturnUrl | None,
    app_settings: AppSettings,
) -> None:
    """
    Accept no return page, or a page of an allowed origin, so the payment
    provider never redirects a payer to a foreign site.

    Raises:
        ValidationFailedError: the page belongs to another origin.
    """

    if return_url is None:
        return

    url: str = str(return_url)
    if not any(
        url == origin or url.startswith(f"{origin}/")
        for origin in list_return_origins(app_settings)
    ):
        raise ValidationFailedError(
            "The return page must belong to an allowed cabinet origin."
        )
