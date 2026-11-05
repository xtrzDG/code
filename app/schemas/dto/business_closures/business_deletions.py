"""
The deletion job's payload and a person's deletion certificates (Account:
the closed businesses whose data is gone).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.business_closures import (
    BusinessClosureReason,
    BusinessDeletionState,
)
from app.schemas.typings.business_closures.constrained_strings import (
    DeletionCertificateFileName,
)
from app.schemas.typings.business_closures.prefixed_id import BusinessDeletionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


class DeleteBusinessJobPayload(ImmutableDTO):
    """The queued job "delete_business": the business whose data goes."""

    business_id: BusinessId


class BusinessDeletionView(ImmutableDTO):
    """One deleted (or being deleted) business a person owned."""

    id: BusinessDeletionId
    business_name: BusinessName
    reason: BusinessClosureReason
    state: BusinessDeletionState
    started_at: Microseconds
    completed_at: Microseconds | None = None


class BusinessDeletionList(ImmutableDTO):
    items: list[BusinessDeletionView] = Field(
        default_factory=list[BusinessDeletionView]
    )


class DeletionCertificateQuery(ImmutableDTO):
    user_id: UserId
    deletion_id: BusinessDeletionId
    language: LanguageTag | None = None


class DeletionCertificateFile(ImmutableDTO):
    """The certificate's PDF and its download name."""

    file_name: DeletionCertificateFileName
    content: bytes = Field(repr=False)
