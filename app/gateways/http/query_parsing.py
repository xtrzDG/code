"""Optional query parameters of cabinet lists as typed values."""

from collections.abc import Callable

from pydantic import ValidationError

from app.schemas.exceptions.application_errors import ValidationFailedError

TRUE_TEXTS: frozenset[str] = frozenset({"true", "1", "yes"})
FALSE_TEXTS: frozenset[str] = frozenset({"false", "0", "no"})


def parse_optional[Value](
    raw_value: str | None,
    value_type: Callable[[str], Value],
    parameter_name: str,
) -> Value | None:
    """A query parameter as a typed value; blank means absent, invalid is 422."""

    if raw_value is None or raw_value.strip() == "":
        return None

    try:
        return value_type(raw_value)
    except (ValueError, TypeError, ValidationError) as error:
        raise ValidationFailedError(f"{parameter_name} is not valid.") from error


def parse_boolean_text(raw_value: str) -> bool:
    """A query flag: true/false, 1/0 or yes/no in any letter case."""

    folded: str = raw_value.strip().casefold()
    if folded in TRUE_TEXTS:
        return True

    if folded in FALSE_TEXTS:
        return False

    raise ValueError(f"{raw_value!r} is not a boolean.")
