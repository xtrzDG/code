"""A tool input the model got wrong, as an error message it can act on."""

from pydantic import ValidationError

MAX_REPORTED_INPUT_ERRORS: int = 3


def describe_tool_input_error(error: ValidationError) -> str:
    """Which arguments were wrong and why, without repeating their values."""

    problems: list[str] = []
    for detail in error.errors()[:MAX_REPORTED_INPUT_ERRORS]:
        location: str = ".".join(str(part) for part in detail["loc"]) or "input"
        problems.append(f"{location}: {detail['msg']}")

    return "Invalid tool input: " + "; ".join(problems)
