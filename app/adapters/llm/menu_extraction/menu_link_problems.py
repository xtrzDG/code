"""A menu link that cannot be used: a 422 with a machine-readable reason."""

from app.schemas.constants.menu_import import MenuLinkProblem
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage


def link_problem(
    problem: MenuLinkProblem,
    message: str,
    detail: str,
) -> ValidationFailedError:
    """A 422 for a menu link, with the problem as its machine-readable reason."""

    return ValidationFailedError(
        message,
        reasons=[
            ErrorReason(
                code=ErrorReasonCode(problem.value),
                message=ErrorReasonMessage(message),
                details=[ErrorReasonDetail(detail)],
            )
        ],
    )
