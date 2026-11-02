"""A tool input the model got wrong, as an error message it can act on."""

from pydantic import ValidationError
from pydantic_core import ErrorDetails

MAX_REPORTED_INPUT_ERRORS: int = 3
PATTERN_MISMATCH: str = "string_pattern_mismatch"
# A pattern of refused characters (a name's or a note's limits) reads as
# noise to the model: it hears what to change instead. A pattern of a
# format (a date, a time) is quoted, it shows the format.
EXCLUSION_PATTERN_START: str = "^[^"
DISALLOWED_CHARACTERS: str = (
    "has characters that are not allowed here: write it on one line, without "
    "markup characters such as < > [ ] { } ` * # | and without invisible "
    "characters"
)


def describe_tool_input_error(error: ValidationError) -> str:
    """Which arguments were wrong and why, without repeating their values."""

    problems: list[str] = []
    for detail in error.errors()[:MAX_REPORTED_INPUT_ERRORS]:
        location: str = ".".join(str(part) for part in detail["loc"]) or "input"
        problems.append(f"{location}: {describe_problem(detail)}")

    return "Invalid tool input: " + "; ".join(problems)


def describe_problem(detail: ErrorDetails) -> str:
    """The error's message; refused characters as what to change."""

    pattern: object = (detail.get("ctx") or {}).get("pattern")
    if (
        detail["type"] == PATTERN_MISMATCH
        and isinstance(pattern, str)
        and pattern.startswith(EXCLUSION_PATTERN_START)
    ):
        return DISALLOWED_CHARACTERS

    return detail["msg"]
