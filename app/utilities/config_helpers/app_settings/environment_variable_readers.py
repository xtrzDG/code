"""Read raw environment variables: blank means "not set", errors name the variable."""

from collections.abc import Callable, Mapping

from app.schemas.exceptions.application_errors import ValidationFailedError

TRUE_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "on"})
FALSE_VALUES: frozenset[str] = frozenset({"0", "false", "no", "off"})


def read_text(
    environment_variables: Mapping[str, str],
    variable_name: str,
    default_value: str,
) -> str:
    raw_value: str = environment_variables.get(variable_name, "").strip()
    if raw_value == "":
        return default_value

    return raw_value


def read_integer(
    environment_variables: Mapping[str, str],
    variable_name: str,
    default_value: int,
) -> int:
    raw_value: str = environment_variables.get(variable_name, "").strip()
    if raw_value == "":
        return default_value

    try:
        return int(raw_value)
    except ValueError as error:
        raise ValidationFailedError(
            f"{variable_name} must be an integer, got {raw_value!r}."
        ) from error


def read_float(
    environment_variables: Mapping[str, str],
    variable_name: str,
    default_value: float,
) -> float:
    raw_value: str = environment_variables.get(variable_name, "").strip()
    if raw_value == "":
        return default_value

    try:
        return float(raw_value)
    except ValueError as error:
        raise ValidationFailedError(
            f"{variable_name} must be a number, got {raw_value!r}."
        ) from error


def read_boolean(
    environment_variables: Mapping[str, str],
    variable_name: str,
    default_value: bool,
) -> bool:
    raw_value: str = environment_variables.get(variable_name, "").strip().lower()
    if raw_value == "":
        return default_value

    if raw_value in TRUE_VALUES:
        return True

    if raw_value in FALSE_VALUES:
        return False

    raise ValidationFailedError(
        f"{variable_name} must be a boolean (true/false), got {raw_value!r}."
    )


def read_list(
    environment_variables: Mapping[str, str],
    variable_name: str,
    default_value: str,
) -> list[str]:
    raw_value: str = environment_variables.get(variable_name, default_value)
    items: list[str] = []
    for raw_item in raw_value.split(","):
        item: str = raw_item.strip().upper()
        if item != "":
            items.append(item)

    return items


def read_raw_list(
    environment_variables: Mapping[str, str],
    variable_name: str,
) -> list[str]:
    raw_value: str = environment_variables.get(variable_name, "")
    items: list[str] = []
    for raw_item in raw_value.split(","):
        item: str = raw_item.strip()
        if item != "":
            items.append(item)

    return items


def optional_setting[TypedValue](
    environment_variables: Mapping[str, str],
    variable_name: str,
    typed_value_type: Callable[[str], TypedValue],
) -> TypedValue | None:
    """A typed optional value; an invalid one names its variable."""

    raw_value: str = environment_variables.get(variable_name, "").strip()
    if raw_value == "":
        return None

    return parse_setting(variable_name, raw_value, typed_value_type)


def parse_setting[RawValue, TypedValue](
    variable_name: str,
    raw_value: RawValue,
    typed_value_type: Callable[[RawValue], TypedValue],
) -> TypedValue:
    try:
        return typed_value_type(raw_value)
    except ValueError as error:
        raise ValidationFailedError(f"{variable_name} has an invalid value.") from error


def optional_text[TypedText: str](
    environment_variables: Mapping[str, str],
    variable_name: str,
    typed_text_type: Callable[[str], TypedText],
) -> TypedText | None:
    raw_value: str = environment_variables.get(variable_name, "").strip()
    if raw_value == "":
        return None

    return typed_text_type(raw_value)
