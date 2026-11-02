"""
An audit entry names where it came from and how it ended (LOG-01): the
request id, the outcome, and for a person's own action or a security event
the client address and User-Agent of the request, filled in on append
where the use case named none; outside the hash (format 1).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.request_context_middleware import RequestContextMiddleware
from app.schemas.constants.compliance import (
    AuditAction,
    AuditOutcome,
    AuditSecurityEvent,
)
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_strings import AuditUserAgent
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_strings import RequestId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.compliance.audit_chain_hashing import compute_entry_hash
from app.utilities.compliance.audit_origin import outcome_of, stamp_audit_origin
from app.utilities.observability.log_context import bound_log_context
from app.utilities.observability.request_origin import (
    bound_request_origin,
    read_audit_user_agent,
)
from tests.compliance.audit_chain.audit_entries import entry
from tests.compliance.audit_repositories import audit_log_repository

BROWSER: str = "Mozilla/5.0 (X11; Linux x86_64) Firefox/131.0"
PERSON: UserId = UserId()
BUSINESS: BusinessId = BusinessId()


def without_address(stored: AuditLogEntryDocument) -> AuditLogEntryDocument:
    return stored.model_copy(update={"ip_address": None})


@pytest.mark.parametrize(
    ("security_event", "outcome"),
    [
        (None, AuditOutcome.SUCCESS),
        (AuditSecurityEvent.LOGOUT, AuditOutcome.SUCCESS),
        (AuditSecurityEvent.KEY_ROTATION, AuditOutcome.SUCCESS),
        (AuditSecurityEvent.LOGIN_FAILED, AuditOutcome.FAILURE),
        (AuditSecurityEvent.OTP_LOCKED, AuditOutcome.FAILURE),
        (AuditSecurityEvent.MFA_LOCKED, AuditOutcome.FAILURE),
    ],
)
def test_the_outcome_follows_the_security_event(
    security_event: AuditSecurityEvent | None, outcome: AuditOutcome
) -> None:
    recorded = entry(None, action=AuditAction.LOGIN).model_copy(
        update={"security_event": security_event}
    )

    assert outcome_of(recorded) is outcome
    assert stamp_audit_origin(recorded).outcome is outcome


def test_a_persons_action_names_the_request_and_its_client() -> None:
    with (
        bound_log_context(request_id=RequestId("req-1")),
        bound_request_origin("203.0.113.9", BROWSER + "\r\nX-Injected: 1"),
    ):
        stamped = stamp_audit_origin(without_address(entry(BUSINESS, actor=PERSON)))

    assert stamped.request_id == RequestId("req-1")
    assert stamped.ip_address == ClientIpAddress("203.0.113.9")
    # Printable ASCII only: the header's line break never reaches the entry.
    assert stamped.user_agent == AuditUserAgent(BROWSER + "X-Injected: 1")
    assert stamped.outcome is AuditOutcome.SUCCESS


def test_a_security_event_without_an_actor_names_the_client_too() -> None:
    failed = without_address(entry(None, action=AuditAction.LOGIN)).model_copy(
        update={"security_event": AuditSecurityEvent.LOGIN_FAILED}
    )
    with bound_request_origin("2001:db8::7", BROWSER):
        stamped = stamp_audit_origin(failed)

    assert stamped.ip_address == ClientIpAddress("2001:db8::7")
    assert stamped.user_agent == AuditUserAgent(BROWSER)
    assert stamped.outcome is AuditOutcome.FAILURE


def test_the_assistants_entry_names_no_customer_client() -> None:
    # A contact changed by the assistant while a customer's widget request
    # is served: the request id joins it to the logs, nothing more.
    with (
        bound_log_context(request_id=RequestId("req-widget")),
        bound_request_origin("198.51.100.20", BROWSER),
    ):
        stamped = stamp_audit_origin(without_address(entry(BUSINESS)))

    assert stamped.request_id == RequestId("req-widget")
    assert stamped.ip_address is None
    assert stamped.user_agent is None


def test_what_the_use_case_named_is_kept() -> None:
    named = entry(BUSINESS, actor=PERSON).model_copy(
        update={
            "request_id": RequestId("req-own"),
            "user_agent": AuditUserAgent("Own agent"),
            "outcome": AuditOutcome.FAILURE,
        }
    )
    with (
        bound_log_context(request_id=RequestId("req-other")),
        bound_request_origin("203.0.113.1", BROWSER),
    ):
        stamped = stamp_audit_origin(named)

    assert stamped == named


def test_a_job_outside_any_request_names_only_its_outcome() -> None:
    stamped = stamp_audit_origin(without_address(entry(BUSINESS, actor=PERSON)))

    assert (stamped.request_id, stamped.ip_address, stamped.user_agent) == (
        None,
        None,
        None,
    )
    assert stamped.outcome is AuditOutcome.SUCCESS


@pytest.mark.parametrize("raw", [None, "", "   ", "\r\n\t", " \u0085"])
def test_a_user_agent_without_printable_text_is_none(raw: str | None) -> None:
    assert read_audit_user_agent(raw) is None


def test_a_long_user_agent_is_cut_to_512_characters() -> None:
    cut = read_audit_user_agent("A" * 600)

    assert cut is not None
    assert len(str(cut)) == 512


def test_the_stored_entry_carries_the_origin_outside_its_hash() -> None:
    repository = audit_log_repository()
    with (
        bound_log_context(request_id=RequestId("req-2")),
        bound_request_origin("203.0.113.9", BROWSER),
    ):
        repository.append(without_address(entry(BUSINESS, actor=PERSON)))

    [stored] = repository.list_by_business(BUSINESS)
    assert stored.request_id == RequestId("req-2")
    assert stored.user_agent == AuditUserAgent(BROWSER)
    assert stored.ip_address == ClientIpAddress("203.0.113.9")
    assert stored.outcome is AuditOutcome.SUCCESS
    # The previous release hashes without the new fields: still intact.
    bare = stored.model_copy(
        update={"request_id": None, "user_agent": None, "outcome": None}
    )
    assert compute_entry_hash(bare) == stored.entry_hash


def test_an_http_request_binds_its_origin_for_the_entries_it_makes() -> None:
    repository = audit_log_repository()
    application = FastAPI()
    application.add_middleware(RequestContextMiddleware)

    @application.post("/act")
    def act() -> None:
        repository.append(without_address(entry(BUSINESS, actor=PERSON)))

    client = TestClient(application, client=("192.0.2.44", 51000))
    answer = client.post(
        "/act", headers={"User-Agent": BROWSER, "X-Request-ID": "req-http"}
    )

    assert answer.status_code == 200
    [stored] = repository.list_by_business(BUSINESS)
    assert (stored.request_id, stored.ip_address, stored.user_agent) == (
        RequestId("req-http"),
        ClientIpAddress("192.0.2.44"),
        AuditUserAgent(BROWSER),
    )
