"""
The service level indicators as stored (docs/operations/slo.md): events of
each series in five-minute slots, and one row per hour with every SLI of
that hour. Platform collections: no business owns them, and they hold
counts only, nothing about a customer.
"""

from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.typings.observability.constrained_integers import (
    AnswerLatencyP95Milliseconds,
    ServiceLevelEventCount,
)


class ServiceLevelSlotDocument(BaseDocument):
    """
    Five minutes of one series, stored under `<series>:<slot_start>`: how
    many events there were and how many were good. API requests are added
    to their slot by every API process (buffered, a few writes a minute);
    customer messages are counted by `record_sli` once a slot is over and
    every message of it had its 60 s.
    """

    series: ServiceLevelSeries
    slot_start: Microseconds
    total: ServiceLevelEventCount = ServiceLevelEventCount(0)
    good: ServiceLevelEventCount = ServiceLevelEventCount(0)


class ServiceLevelHourDocument(BaseDocument):
    """
    One hour of every SLI, stored under its start, written by `record_sli`
    once the hour is over: customer messages and those answered or handed
    off within 60 s, the assistant replies measured and their p95 wait,
    and API requests and those answered with a server error. The error
    budget card and the reviews read these rows.
    """

    hour_start: Microseconds
    inbound_messages: ServiceLevelEventCount = ServiceLevelEventCount(0)
    inbound_in_time: ServiceLevelEventCount = ServiceLevelEventCount(0)
    measured_replies: ServiceLevelEventCount = ServiceLevelEventCount(0)
    reply_p95_ms: AnswerLatencyP95Milliseconds | None = None
    api_requests: ServiceLevelEventCount = ServiceLevelEventCount(0)
    api_server_errors: ServiceLevelEventCount = ServiceLevelEventCount(0)
