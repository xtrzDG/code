from collections.abc import Sequence

from app.schemas.dto.errors import ErrorReason


class ApplicationError(Exception):
    """
    Base of every business error.

    `reasons` optionally lists machine-readable reasons (stable codes with
    details) next to the English message; the HTTP layer returns them as
    the `reasons` field of the error body, so clients do not have to parse
    the message. Raise it like any exception:

        raise ConflictError("Cannot go live yet: ...", reasons=[...])
    """

    def __init__(self, *args: object, reasons: Sequence[ErrorReason] = ()) -> None:
        super().__init__(*args)
        self.reasons: tuple[ErrorReason, ...] = tuple(reasons)
