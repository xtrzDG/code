"""
DTO and stored-document round trips (SDLC-07): what storage writes reads
back as the same document (an audit entry with its request origin, a day
of the status page), DTOs survive their JSON, and a value behind a closed
release gate (the status page's payments) is never written.
"""

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st
from typed_time_provider import Microseconds

from app.adapters.storage.persisted_document_codec import PersistedDocumentCodec
from app.schemas.constants.compliance import (
    AuditAction,
    AuditOutcome,
    AuditSecurityEvent,
)
from app.schemas.constants.platform_status import StatusComponent, StatusLevel
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.platform_status import (
    ComponentDayRecord,
    PlatformStatusDayDocument,
)
from app.schemas.dto.billing import Money
from app.schemas.exceptions.storage_errors import ClosedReleaseGateError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditRecordCount
from app.schemas.typings.compliance.constrained_strings import AuditUserAgent
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.platform.constrained_strings import RequestId
from app.schemas.typings.platform_status.constrained_integers import StatusCheckCount
from app.schemas.typings.platform_status.constrained_strings import StatusDay
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.platform_status.gated_components import stored_components

AUDIT = PersistedDocumentCodec(
    AuditLogEntryDocument, DocumentCollectionName("audit_logs")
)
STATUS_DAYS = PersistedDocumentCodec(
    PlatformStatusDayDocument, DocumentCollectionName("platform_status_days")
)
printable = st.text(
    alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E),
    min_size=1,
    max_size=128,
)
moments = st.integers(min_value=1_700_000_000_000_000, max_value=1_900_000_000_000_000)
texts = st.text(min_size=1, max_size=40)


def optional[T](values: st.SearchStrategy[T]) -> st.SearchStrategy[T | None]:
    return st.none() | values


@st.composite
def audit_entries(draw: st.DrawFn) -> AuditLogEntryDocument:
    created = Microseconds(draw(moments))
    return AuditLogEntryDocument(
        business_id=draw(optional(st.builds(BusinessId))),
        actor_id=draw(optional(st.builds(UserId))),
        action=draw(st.sampled_from(AuditAction)),
        entity=AuditEntityName(draw(texts)),
        entity_id=draw(optional(texts.map(AuditEntityReference))),
        ip_address=draw(optional(st.ip_addresses().map(str).map(ClientIpAddress))),
        record_count=draw(optional(st.integers(0, 10**6).map(AuditRecordCount))),
        security_event=draw(optional(st.sampled_from(AuditSecurityEvent))),
        user_agent=draw(optional(printable.map(AuditUserAgent))),
        request_id=draw(optional(printable.map(RequestId))),
        outcome=draw(optional(st.sampled_from(AuditOutcome))),
        created_at=created,
        updated_at=created,
    )


@st.composite
def status_days(draw: st.DrawFn) -> PlatformStatusDayDocument:
    created = Microseconds(draw(moments))
    day = draw(st.dates(min_value=date(2026, 1, 1))).isoformat()
    counts = st.integers(0, 288).map(StatusCheckCount)
    return PlatformStatusDayDocument(
        day=StatusDay(day),
        components=[
            ComponentDayRecord(
                component=component,
                worst_level=draw(st.sampled_from(StatusLevel)),
                check_count=draw(counts),
                degraded_count=draw(counts),
                outage_count=draw(counts),
            )
            for component in draw(
                st.lists(st.sampled_from(stored_components()), unique=True)
            )
        ],
        created_at=created,
        updated_at=created,
    )


@given(audit_entries())
def test_an_audit_entry_reads_back_as_written(entry: AuditLogEntryDocument) -> None:
    stored = AUDIT.encode(entry)

    assert AUDIT.decode(stored) == entry
    assert "\n" not in stored


@given(status_days())
def test_a_status_day_reads_back_as_written(day: PlatformStatusDayDocument) -> None:
    assert STATUS_DAYS.decode(STATUS_DAYS.encode(day)) == day


@given(status_days(), st.sampled_from(StatusLevel))
def test_a_payments_record_is_never_written_before_its_gate_opens(
    day: PlatformStatusDayDocument, level: StatusLevel
) -> None:
    with_payments = day.model_copy(
        update={
            "components": [
                *day.components,
                ComponentDayRecord(
                    component=StatusComponent.PAYMENTS, worst_level=level
                ),
            ]
        }
    )

    with pytest.raises(ClosedReleaseGateError):
        STATUS_DAYS.encode(with_payments)


@given(
    st.integers(0, 10**15),
    st.sampled_from([CurrencyCode(code) for code in ("EUR", "GEL", "JPY", "USD")]),
)
def test_money_survives_its_json(amount: int, currency: CurrencyCode) -> None:
    money = Money(amount_minor=MoneyAmountMinor(amount), currency_code=currency)

    assert Money.model_validate_json(money.model_dump_json()) == money
