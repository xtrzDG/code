"""
Where an audit entry came from and how it ended (LOG-01, version 7 of the
entry), filled in when it is appended for what its use case left unset:

- `outcome`: FAILURE for a refused sign-in (a wrong code, a code locked by
  its last attempt), SUCCESS for everything else that was recorded;
- `request_id`: the request being served, or the one that queued the job
  that writes the entry (the log context);
- `ip_address` and `user_agent`: the request's client, only for a person's
  own action (an entry with an actor) or a security event. An entry the
  assistant or a job writes while a customer's request is served names no
  customer's address or browser.
"""

from app.schemas.constants.compliance import AuditOutcome, AuditSecurityEvent
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.utilities.observability.log_context import current_log_context
from app.utilities.observability.request_origin import (
    RequestOrigin,
    current_request_origin,
)

FAILED_SECURITY_EVENTS: frozenset[AuditSecurityEvent] = frozenset(
    {
        AuditSecurityEvent.LOGIN_FAILED,
        AuditSecurityEvent.OTP_LOCKED,
        AuditSecurityEvent.MFA_LOCKED,
    }
)


def outcome_of(entry: AuditLogEntryDocument) -> AuditOutcome:
    """How the recorded operation ended, from its security event."""

    if entry.security_event in FAILED_SECURITY_EVENTS:
        return AuditOutcome.FAILURE

    return AuditOutcome.SUCCESS


def stamp_audit_origin(entry: AuditLogEntryDocument) -> AuditLogEntryDocument:
    """The entry with its outcome and origin filled where they were unset."""

    updates: dict[str, object] = {}
    if entry.outcome is None:
        updates["outcome"] = outcome_of(entry)

    request_id = current_log_context().request_id
    if entry.request_id is None and request_id is not None:
        updates["request_id"] = request_id

    origin: RequestOrigin | None = current_request_origin()
    if origin is not None and (
        entry.actor_id is not None or entry.security_event is not None
    ):
        if entry.ip_address is None and origin.client_ip_address is not None:
            updates["ip_address"] = origin.client_ip_address
        if entry.user_agent is None and origin.user_agent is not None:
            updates["user_agent"] = origin.user_agent

    return entry.model_copy(update=updates) if updates else entry
