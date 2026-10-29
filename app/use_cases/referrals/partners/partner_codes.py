"""Claiming a partner's referral code: one code names one owner."""

from typed_time_provider import Microseconds

from app.contracts.repositories.referral_repositories import ReferralCodeRepoContract
from app.schemas.constants.referrals import ReferralCodeOwnerKind
from app.schemas.domain.referrals import ReferralCodeDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.analytics.constrained_strings import ReferralCode
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.referrals.prefixed_id import PartnerId
from app.utilities.referrals.referral_identity import referral_code_id

CODE_TAKEN_REASON: ErrorReasonCode = ErrorReasonCode("code_taken")


def code_taken_error() -> ConflictError:
    return ConflictError(
        "This code is already in use.",
        reasons=[
            ErrorReason(
                code=CODE_TAKEN_REASON,
                message=ErrorReasonMessage("Choose another code for the partner."),
            )
        ],
    )


def require_free_code(codes: ReferralCodeRepoContract, code: ReferralCode) -> None:
    """
    Raises:
        ConflictError: the code (in any case) names a partner or a business.
    """

    if codes.get(referral_code_id(code)) is not None:
        raise code_taken_error()


def claim_partner_code(
    codes: ReferralCodeRepoContract,
    partner_id: PartnerId,
    code: ReferralCode,
    now: Microseconds,
) -> None:
    """
    Raises:
        ConflictError: another partner or a business holds the code.
    """

    is_claimed: bool = codes.claim(
        ReferralCodeDocument(
            id=referral_code_id(code),
            code=code,
            owner_kind=ReferralCodeOwnerKind.PARTNER,
            partner_id=partner_id,
            created_at=now,
            updated_at=now,
        )
    )
    if not is_claimed:
        raise code_taken_error()
