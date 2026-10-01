"""Optional query parameters of cabinet lists as typed values."""

from collections.abc import Callable

from pydantic import ValidationError

from app.schemas.exceptions.application_errors import ValidationFailedError


def parse_optional[Value](
    raw_value: str | None,
    value_type: Callable[[str], Value],
    parameter_name: str,
) -> Value | None:
    """A query parameter as a typed value; empty means absent, invalid is 422."""

    if raw_value is None or raw_value == "":
        return None

    try:
        return value_type(raw_value)
    except (ValueError, TypeError, ValidationError) as error:
        raise ValidationFailedError(f"{parameter_name} is not valid.") from error
