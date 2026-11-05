from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.client_health import (
    AdminDigestKind,
    ClientHealthIssue,
    ClientHealthStatus,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.client_health.prefixed_id import ClientHealthChangeId


class ClientHealthChangeDocument(BaseDocument):
    """
    A client's health moved from one status to another
    (`client_health_changes`, migration 1143): written by the job that
    refreshes the admin's client list when it finds a client's status
    changed, with the issues behind the new one. The client's timeline
    shows it, and the daily digest tells the team who newly turned
    critical.
    """

    id: ClientHealthChangeId = Field(default_factory=ClientHealthChangeId)
    business_id: BusinessId
    previous_status: ClientHealthStatus
    status: ClientHealthStatus
    issues: list[ClientHealthIssue] = Field(default_factory=list[ClientHealthIssue])
    changed_at: Microseconds


class AdminDigestStateDocument(BaseDocument):
    """
    How far a digest of the platform team has looked
    (`admin_digest_states`, a platform collection, migration 1143; the
    storage key is the kind): the changes up to `covered_until` were
    considered, so a day the worker missed is told the next day and
    nothing twice.
    """

    kind: AdminDigestKind
    covered_until: Microseconds
    last_sent_at: Microseconds | None = None
