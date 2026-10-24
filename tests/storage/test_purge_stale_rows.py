"""The daily purge of stale rows, in memory and on Postgres."""

from typing import cast

import pytest
from typed_time_provider import Microseconds

from app.containers.app import AppContainer
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.gateways.worker.periodic.purge_stale_rows import (
    PURGE_STALE_ROWS_JOB,
    purge_stale_rows_job,
)
from app.repositories.call_follow_up_repositories import MissedCallRepository
from app.repositories.channel_repositories import ChannelMessageReceiptRepository
from app.repositories.delivery_repositories import (
    InboundEventRepository,
    OutboundMessageRepository,
)
from app.repositories.meta_connection_state_repository import (
    MetaConnectionStateRepository,
)
from app.repositories.mfa_repositories import MfaChallengeRepository
from app.repositories.passkey_repositories import PasskeyChallengeRepository
from app.repositories.user_repositories import (
    OtpChallengeRepository,
    UserSessionRepository,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.channel_receipts import ChannelMessageReceiptDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.meta_connections import MetaConnectionStateDocument
from app.schemas.domain.mfa import MfaChallengeDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.domain.passkeys import PasskeyChallengeDocument
from app.schemas.domain.users import OtpChallengeDocument, UserSessionDocument
from app.schemas.dto.jobs import JobTick
from app.use_cases.maintenance.purge_stale_rows_use_case import PurgeStaleRowsUseCase
from tests.compliance.audit_repositories import audit_log_repository
from tests.storage.conftest import CollectionFactory
from tests.storage.stale_row_samples import (
    ceremony,
    challenge,
    facebook_sign_in,
    inbound_event,
    missed_call,
    outbound_message,
    receipt,
    second_step,
    session,
)
from tests.storage.storage_testing import FIXED_NANOSECONDS, build_fixed_wall_clock

# Seeding and checking rows of several businesses runs platform-wide; the
# business scopes a test enters nest inside (tests/storage/conftest.py).
pytestmark = pytest.mark.usefixtures("platform_scope")

NOW: int = FIXED_NANOSECONDS // 1_000
HOUR: int = 3_600_000_000
DAY: int = 24 * HOUR
TICK = JobTick(job_name=PURGE_STALE_ROWS_JOB, scheduled_at=Microseconds(NOW))


def test_stale_sessions_codes_and_receipts_are_purged_and_audited(
    collections: CollectionFactory,
) -> None:
    sessions = UserSessionRepository(collections(UserSessionDocument, "user_sessions"))
    challenge_collection = collections(OtpChallengeDocument, "otp_challenges")
    challenges = OtpChallengeRepository(challenge_collection)
    receipt_collection = collections(
        ChannelMessageReceiptDocument, "channel_message_receipts"
    )
    receipts = ChannelMessageReceiptRepository(receipt_collection)
    audit_collection = collections(AuditLogEntryDocument, "audit_log_entries")
    audit = audit_log_repository(audit_collection)
    expired, at_expiry, valid = session(NOW - 1), session(NOW), session(NOW + 1)
    for stored in (expired, at_expiry, valid):
        sessions.save(stored)
    old_code, fresh_code = challenge(NOW - DAY - 1), challenge(NOW - HOUR)
    challenges.save(old_code)
    challenges.save(fresh_code)
    old_receipt, fresh_receipt = receipt(NOW - 31 * DAY, "1"), receipt(NOW - DAY, "2")
    receipt_collection.upsert(str(old_receipt.id), old_receipt)
    receipt_collection.upsert(str(fresh_receipt.id), fresh_receipt)
    event_collection = collections(InboundEventDocument, "inbound_events")
    outbox_collection = collections(OutboundMessageDocument, "outbound_messages")
    old_event, fresh_event = inbound_event(NOW - 31 * DAY), inbound_event(NOW - DAY)
    old_reply, fresh_reply = outbound_message(NOW - 31 * DAY), outbound_message(NOW)
    for event in (old_event, fresh_event):
        event_collection.upsert(str(event.id), event)
    for reply in (old_reply, fresh_reply):
        outbox_collection.upsert(str(reply.id), reply)
    missed_collection = collections(MissedCallDocument, "missed_calls")
    old_missed, fresh_missed = missed_call(NOW - 91 * DAY), missed_call(NOW - 89 * DAY)
    for missed in (old_missed, fresh_missed):
        missed_collection.upsert(str(missed.id), missed)
    second_steps = MfaChallengeRepository(
        collections(MfaChallengeDocument, "mfa_challenges")
    )
    old_step, fresh_step = second_step(NOW - DAY - 1), second_step(NOW - HOUR)
    second_steps.save(old_step)
    second_steps.save(fresh_step)
    ceremonies = PasskeyChallengeRepository(
        collections(PasskeyChallengeDocument, "passkey_challenges")
    )
    old_ceremony, fresh_ceremony = ceremony(NOW - DAY - 1), ceremony(NOW - HOUR)
    ceremonies.save(old_ceremony)
    ceremonies.save(fresh_ceremony)
    sign_in_collection = collections(
        MetaConnectionStateDocument, "meta_connection_states"
    )
    ended_sign_in, open_sign_in = facebook_sign_in(NOW - 1), facebook_sign_in(NOW + 1)
    for sign_in in (ended_sign_in, open_sign_in):
        sign_in_collection.upsert(str(sign_in.state_hash), sign_in)
    use_case = PurgeStaleRowsUseCase(
        user_session_repo=sessions,
        otp_challenge_repo=challenges,
        channel_message_receipt_repo=receipts,
        inbound_event_repo=InboundEventRepository(event_collection),
        outbound_message_repo=OutboundMessageRepository(outbox_collection),
        missed_call_repo=MissedCallRepository(missed_collection),
        audit_log_repo=audit,
        wall_clock=build_fixed_wall_clock(),
        mfa_challenge_repo=second_steps,
        passkey_challenge_repo=ceremonies,
        meta_connection_state_repo=MetaConnectionStateRepository(sign_in_collection),
    )

    report = use_case.run(TICK)
    second_report = use_case.run(TICK)

    assert report.processed_count == 10
    assert second_report.processed_count == 0
    assert sessions.find_by_token_hash(expired.token_hash) is None
    assert sessions.find_by_token_hash(at_expiry.token_hash) is None
    assert sessions.find_by_token_hash(valid.token_hash) == valid
    assert [c.id for c in challenge_collection.list_all()] == [fresh_code.id]
    assert [r.id for r in receipt_collection.list_all()] == [fresh_receipt.id]
    assert [e.id for e in event_collection.list_all()] == [fresh_event.id]
    assert [m.id for m in outbox_collection.list_all()] == [fresh_reply.id]
    assert [m.id for m in missed_collection.list_all()] == [fresh_missed.id]
    assert second_steps.get(old_step.id) is None
    assert second_steps.get(fresh_step.id) == fresh_step
    assert ceremonies.get(old_ceremony.id) is None
    assert ceremonies.get(fresh_ceremony.id) == fresh_ceremony
    assert [r.state_hash for r in sign_in_collection.list_all()] == [
        open_sign_in.state_hash
    ]
    entries = audit_collection.list_all()
    assert sorted(str(entry.entity) for entry in entries) == [
        "channel_message_receipt",
        "inbound_event",
        "meta_connection_state",
        "mfa_challenge",
        "missed_call",
        "otp_challenge",
        "outbound_message",
        "passkey_challenge",
        "user_session",
    ]
    assert {entry.action for entry in entries} == {AuditAction.RETENTION_PURGE}
    assert all(entry.actor_id is None for entry in entries)


def test_the_worker_runs_the_purge_once_a_day() -> None:
    specs = cast(list[PeriodicJobSpec], AppContainer().gateways.periodic_jobs())
    purge: list[PeriodicJobSpec] = [
        spec for spec in specs if spec.name == PURGE_STALE_ROWS_JOB
    ]

    assert len(purge) == 1
    assert int(purge[0].interval_seconds) == 24 * 60 * 60
    assert purge_stale_rows_job(purge[0].operator).name == PURGE_STALE_ROWS_JOB
