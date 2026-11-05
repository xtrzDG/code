"""
How deep a JSON request body nests, measured before it is parsed: a body
of thousands of nested brackets would make a parser recurse until it fails
(Python's json raises RecursionError), so it is refused with 422 first.

The measure needs no parse: strings are cut out (a bracket inside a string
is text), the brackets left are counted in order. A body that is not JSON
at all is measured the same way and refused by the parser after. The cut
is linear in the body's length whatever it holds: a string runs to its
closing quote or, unterminated, to the end of the body (the parser stops
there too), and nothing is tried twice (possessive quantifiers), so a
body of escaped quotes cannot make it quadratic.
"""

import re

from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage

# The deepest request of the API nests about ten levels (a provider's
# webhook); the parsers themselves give up near 200 (pydantic) and 1000.
MAX_JSON_NESTING_DEPTH: int = 64
JSON_STRING: re.Pattern[bytes] = re.compile(
    rb'"[^"\\]*+(?:\\.[^"\\]*+)*+(?:"|\\?\Z)', re.DOTALL
)
OPENING: frozenset[int] = frozenset(b"[{")
NOT_A_BRACKET: bytes = bytes(byte for byte in range(256) if byte not in b"[]{}")
TOO_DEEP_MESSAGE: str = (
    f"The request body nests deeper than {MAX_JSON_NESTING_DEPTH} levels."
)
JSON_BODY_START: frozenset[int] = frozenset(b"[{")
# A UTF-8 byte order mark, which JSON parsers skip before the first value.
UTF8_BOM: bytes = b"\xef\xbb\xbf"


def json_nesting_depth(
    raw_body: bytes, stop_above: int = MAX_JSON_NESTING_DEPTH
) -> int:
    """
    The deepest nesting of arrays and objects in `raw_body`; counting
    stops once it passes `stop_above`.
    """

    brackets: bytes = JSON_STRING.sub(b"", raw_body).translate(None, NOT_A_BRACKET)
    depth: int = 0
    deepest: int = 0
    for bracket in brackets:
        if bracket in OPENING:
            depth += 1
            if depth > deepest:
                deepest = depth
                if deepest > stop_above:
                    break
        elif depth > 0:
            depth -= 1

    return deepest


def looks_like_json(raw_body: bytes, content_type: str | None) -> bool:
    """A JSON media type, or a body that opens like JSON (a raw webhook)."""

    if content_type is not None and "json" in content_type.lower():
        return True

    stripped: bytes = raw_body.lstrip().removeprefix(UTF8_BOM).lstrip()
    return stripped != b"" and stripped[0] in JSON_BODY_START


def ensure_json_nesting_within_limit(raw_body: bytes) -> None:
    """
    Raises:
        ValidationFailedError: the body nests deeper than the limit (422,
            reason `too_deep`).
    """

    if json_nesting_depth(raw_body) <= MAX_JSON_NESTING_DEPTH:
        return

    raise ValidationFailedError(
        TOO_DEEP_MESSAGE,
        reasons=[
            ErrorReason(
                code=ErrorReasonCode("too_deep"),
                message=ErrorReasonMessage(TOO_DEEP_MESSAGE),
                details=[ErrorReasonDetail("body")],
            )
        ],
    )
