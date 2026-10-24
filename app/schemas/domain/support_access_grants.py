from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.access import (
    SupportAccessEndReason,
    SupportAccessKind,
    SupportAccessStatus,
)
from app.schemas.typings.access.constrained_strings import SupportAccessReason
from app.schemas.typings.access.prefixed_id import SupportAccessGrantId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId


class SupportAccessGrantDocument(BaseDocument):
    """
    Platform support's access to one business (migration 1103), kept apart
    from the business document so opening and ending access never touches
    the business.

    - SESSION: a platform admin's look into the cabinet, opened with a
      `reason` from `opened_from_ip`, read-only, until `expires_at` (an
      hour). `admin_user_id` is the admin.
    - WRITE_CONSENT: the owner (`granted_by`) lets support also change
      things until `expires_at` (the hours the owner chose).

    A grant stays OPEN until it ends: by time (EXPIRED, closed by the
    periodic job or at its next check), by the admin (CLOSED_BY_ADMIN,
    REPLACED) or by the owner (REVOKED_BY_OWNER); `ended_at` and
    `ended_by` record when and by whom.
    """

    id: SupportAccessGrantId = Field(default_factory=SupportAccessGrantId)
    business_id: BusinessId
    kind: SupportAccessKind
    status: SupportAccessStatus = SupportAccessStatus.OPEN
    granted_by: UserId
    admin_user_id: UserId | None = None
    reason: SupportAccessReason | None = None
    opened_from_ip: ClientIpAddress | None = None
    expires_at: Microseconds
    ended_at: Microseconds | None = None
    ended_by: UserId | None = None
    end_reason: SupportAccessEndReason | None = None
