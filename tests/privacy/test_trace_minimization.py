"""
Traces of model calls at Langfuse: tagged with the business, contact and
conversation they answered (metadata, and the conversation as sessionId),
and without phone numbers or e-mail addresses unless LANGFUSE_RAW_TEXT.
"""

from typing import cast

import pytest
from typed_time_provider import Microseconds, MonotonicClock, Nanoseconds, WallClock

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.adapters.llm.tracing_llm_adapter import TracingLlmAdapter
from app.facilitators.observability.langfuse_trace_facilitator import (
    build_generation_events,
)
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.config_helpers.app_settings.observability_settings_section import (
    read_observability_settings,
)
from app.utilities.observability.log_context import bound_log_context
from app.utilities.observability.trace_redaction import redact_contact_details
from tests.platform.test_observability import (
    STARTED_AT_NANOSECONDS,
    RecordingTraceFacilitator,
    build_request,
    build_trace,
    build_tracing_adapter,
)


def scripted(text: str) -> ScriptedLlmAdapter:
    return ScriptedLlmAdapter.from_turns([ScriptedLlmTurn(text=MessageText(text))])


def test_a_trace_names_the_business_contact_and_conversation_of_the_call() -> None:
    inner = scripted("Booked!")
    facilitator = RecordingTraceFacilitator()
    adapter = build_tracing_adapter(inner, facilitator, is_content_traced=False)
    business_id, contact_id, conversation_id = (
        BusinessId(),
        ContactId(),
        ConversationId(),
    )

    with (
        bound_log_context(business_id=business_id),
        bound_log_context(conversation_id=conversation_id, contact_id=contact_id),
    ):
        adapter.complete(build_request(inner))

    trace = facilitator.traces[0]
    assert (trace.business_id, trace.contact_id, trace.conversation_id) == (
        business_id,
        contact_id,
        conversation_id,
    )
    events = build_generation_events(trace)
    trace_body = events[0]["body"]
    assert isinstance(trace_body, dict)
    assert trace_body["sessionId"] == str(conversation_id)
    assert trace_body["metadata"] == {
        "model": "gpt-5-mini",
        "business_id": str(business_id),
        "contact_id": str(contact_id),
        "conversation_id": str(conversation_id),
    }
    generation_body = cast(dict[str, object], events[1]["body"])
    generation_metadata = cast(dict[str, object], generation_body["metadata"])
    assert generation_metadata["conversation_id"] == str(conversation_id)


def test_a_call_outside_a_conversation_has_no_session() -> None:
    events = build_generation_events(build_trace())

    trace_body = events[0]["body"]
    assert isinstance(trace_body, dict)
    assert "sessionId" not in trace_body
    assert trace_body["metadata"] == {"model": "gpt-5-mini"}


def test_traced_texts_lose_phones_and_emails_unless_raw_text_is_allowed() -> None:
    reply = "Booked, Nino! We will call +995 555 12 34 56 or write to nino@example.ge."
    inner = scripted(reply)
    facilitator = RecordingTraceFacilitator()
    adapter = build_tracing_adapter(inner, facilitator, is_content_traced=True)

    adapter.complete(build_request(inner))

    assert facilitator.traces[0].output_text == (
        "Booked, Nino! We will call [phone] or write to [email]."
    )

    raw_inner = scripted(reply)
    raw_facilitator = RecordingTraceFacilitator()
    raw_adapter = TracingLlmAdapter(
        inner_adapter=raw_inner,
        trace_facilitator=raw_facilitator,
        wall_clock=WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: STARTED_AT_NANOSECONDS,
        ),
        monotonic_clock=MonotonicClock(
            preferred_time_unit_type=Nanoseconds,
            monotonic_nanosecond_factory=lambda: 0,
        ),
        is_content_traced=True,
        is_raw_text_traced=True,
    )
    raw_adapter.complete(build_request(raw_inner))

    assert raw_facilitator.traces[0].output_text == reply


@pytest.mark.parametrize(
    ("text", "redacted"),
    [
        ("Call 555-123-456 tomorrow", "Call [phone] tomorrow"),
        ("(032) 2 12 34 56", "[phone]"),
        ("+(995) 555 123 456", "[phone]"),
        ("Mail ANNA.K+vip@mail.example.com now", "Mail [email] now"),
        (
            "A table for 4 at 19:30 on 2026-10-05",
            "A table for 4 at 19:30 on 2026-10-05",
        ),
        ("Khachapuri costs 18 GEL, room 1204", "Khachapuri costs 18 GEL, room 1204"),
    ],
)
def test_redaction_keeps_dates_prices_and_times(text: str, redacted: str) -> None:
    assert redact_contact_details(text) == redacted


def test_raw_text_is_off_unless_langfuse_raw_text_is_set() -> None:
    assert read_observability_settings({}, False)["is_llm_raw_text_traced"] is False
    settings = read_observability_settings({"LANGFUSE_RAW_TEXT": "true"}, True)
    assert settings["is_llm_raw_text_traced"] is True
