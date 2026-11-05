"""
Refusals of publishing and rollback as machine-readable reasons.

A failed blocking go-live check becomes one `ErrorReason` with the check's
code and details, so the 409 body names exactly what the checklist shows.
"""

from collections.abc import Collection, Sequence

from app.schemas.constants.assistants import (
    AssistantVersionRefusalCode,
    GoLiveCheckCode,
)
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.go_live import GoLiveCheck, GoLiveReadiness
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage

GO_LIVE_REFUSAL_PREFIX: str = "The assistant cannot go live yet: "


def find_blocking_failures(
    readiness: GoLiveReadiness,
    ignored_codes: Collection[GoLiveCheckCode] = (),
) -> list[GoLiveCheck]:
    """Checks that fail and stop publishing, in checklist order."""

    return [
        check
        for check in readiness.checks
        if not check.is_ok and check.is_blocking and check.code not in ignored_codes
    ]


def is_voice_configured(readiness: GoLiveReadiness) -> bool:
    """False when the voice check failed (the voice agent must be skipped)."""

    return all(
        check.is_ok
        for check in readiness.checks
        if check.code is GoLiveCheckCode.VOICE_CONFIGURATION
    )


def build_check_reason(check: GoLiveCheck) -> ErrorReason:
    """A failed go-live check as a refusal reason with the same code."""

    return ErrorReason(
        code=ErrorReasonCode(check.code.value),
        message=ErrorReasonMessage(str(check.message)),
        details=[ErrorReasonDetail(str(detail)) for detail in check.details],
    )


def build_version_reason(
    code: AssistantVersionRefusalCode,
    message: str,
    details: Sequence[str] = (),
) -> ErrorReason:
    """A refusal because of the version's state (testing, live, archived)."""

    return ErrorReason(
        code=ErrorReasonCode(code.value),
        message=ErrorReasonMessage(message),
        details=[ErrorReasonDetail(detail) for detail in details],
    )


def describe_go_live_refusal(checks: Sequence[GoLiveCheck]) -> str:
    """One English sentence listing what is still missing."""

    return GO_LIVE_REFUSAL_PREFIX + " ".join(str(check.message) for check in checks)
