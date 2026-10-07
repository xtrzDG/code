"""
A customer's erasure also deletes the copies at the sub-processors: the
traces of their conversations at Langfuse and their calls at ElevenLabs,
by queued jobs, so a processor's outage never fails the erasure.
"""

from app.schemas.constants.privacy import ProcessorErasureReason, SubProcessor
from app.schemas.domain.conversations import CallSummary
from app.schemas.dto.compliance import ContactDataCommand
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.dto.processor_erasure import ProcessorErasureJobPayload
from app.schemas.typings.calls.constrained_strings import CallSummaryText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.use_cases.compliance.erase_processor_copies_use_case import (
    EraseProcessorCopiesUseCase,
)
from tests.compliance.visitor_records import seed_visitor
from tests.users.accounts_phones import GEORGIA_MOBILE
from tests.users.accounts_testbed import build_accounts_testbed


def test_the_erasure_queues_the_deletion_of_every_conversation_and_call() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    visitor = seed_visitor(testbed, business, "Nino", "+995599111222", "777", "ka")
    processors = testbed.processor_erasure
    processors.langfuse.sessions = {
        str(visitor.chat_conversation.id): ["trace-a", "trace-b"],
        str(visitor.phone_conversation.id): ["trace-c"],
    }

    result = testbed.delete_contact_data.run(
        ContactDataCommand(
            user_id=owner.user.id,
            business_id=business.id,
            contact_id=visitor.contact.id,
        )
    )

    assert int(result.queued_processor_erasures) == 2
    payloads = [
        ProcessorErasureJobPayload.model_validate_json(str(job.payload))
        for job in processors.job_queue.jobs
    ]
    assert [(payload.processor, payload.reason) for payload in payloads] == [
        (SubProcessor.LANGFUSE, ProcessorErasureReason.CONTACT_ERASURE),
        (SubProcessor.ELEVENLABS, ProcessorErasureReason.CONTACT_ERASURE),
    ]
    assert set(payloads[0].conversation_ids) == {
        visitor.chat_conversation.id,
        visitor.phone_conversation.id,
    }
    assert set(payloads[1].provider_call_ids) == {
        visitor.conversation_call.provider_call_id,
        visitor.phone_matched_call.provider_call_id,
    }

    job = EraseProcessorCopiesUseCase(
        processor_erasure=processors.facilitator(),
        audit_log_repo=testbed.audit_log_repo,
        wall_clock=testbed.clock.build_wall_clock(),
    )
    for queued in processors.job_queue.jobs:
        job.run(
            QueuedJobInput(
                job_id=QueuedJobId(),
                job_name=queued.name,
                payload=queued.payload,
                business_id=queued.business_id,
            )
        )

    assert sorted(processors.langfuse.deleted) == ["trace-a", "trace-b", "trace-c"]
    assert sorted(processors.elevenlabs.deleted) == sorted(
        str(call.provider_call_id)
        for call in (visitor.conversation_call, visitor.phone_matched_call)
    )
    copies = {
        str(entry.entity): entry.record_count
        for entry in testbed.audit_log_repo.list_by_business(business.id)
        if str(entry.entity).endswith("_copies")
    }
    assert copies == {"langfuse_copies": 3, "elevenlabs_copies": 2}


def test_an_erased_call_loses_its_summaries_for_staff_too() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    visitor = seed_visitor(testbed, business, "Nino", "+995599111222", "777", "ka")
    summarized = visitor.conversation_call.model_copy(
        update={
            "summaries": [
                CallSummary(
                    language=LanguageTag("en"),
                    text=CallSummaryText("Nino wants a table for four"),
                )
            ]
        }
    )
    testbed.call_repo.save(summarized)

    testbed.delete_contact_data.run(
        ContactDataCommand(
            user_id=owner.user.id,
            business_id=business.id,
            contact_id=visitor.contact.id,
        )
    )

    call = testbed.call_repo.get(business.id, visitor.conversation_call.id)
    assert call is not None
    assert (call.transcript, call.summaries, call.from_phone_number) == (None, [], None)
