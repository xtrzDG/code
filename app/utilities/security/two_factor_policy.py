"""Which sessions count as signed in with two factors, and the refusal."""

from app.schemas.constants.mfa import AuthLevel
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.mfa_errors import MfaRequiredError, WrongCodeError
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.users.prefixed_id import UserId

MFA_REQUIRED_CODE: ErrorReasonCode = ErrorReasonCode("mfa_required")
WRONG_CODE_CODE: ErrorReasonCode = ErrorReasonCode("wrong_code")


def is_two_factor_session(assurance: SessionAssurance | None, user_id: UserId) -> bool:
    """The request's session is this user's and was signed in with two factors."""

    return (
        assurance is not None
        and assurance.user_id == user_id
        and assurance.auth_level is AuthLevel.TWO_FACTOR
    )


def mfa_required(message: str) -> MfaRequiredError:
    """HTTP 403 with the reason `mfa_required` (see MfaRequiredError)."""

    return MfaRequiredError(
        message,
        reasons=[
            ErrorReason(
                code=MFA_REQUIRED_CODE,
                message=ErrorReasonMessage(message),
            )
        ],
    )


def wrong_code(message: str) -> WrongCodeError:
    """HTTP 422 with the reason `wrong_code` (see WrongCodeError)."""

    return WrongCodeError(
        message,
        reasons=[
            ErrorReason(code=WRONG_CODE_CODE, message=ErrorReasonMessage(message))
        ],
    )
