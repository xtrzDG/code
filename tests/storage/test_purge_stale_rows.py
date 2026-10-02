"""The daily purge of stale rows, in memory and on Postgres."""

from typing import cast

from typed_time_provider import Microseconds

from app.containers.app import AppContainer
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.gateways.worker.periodic.purge_stale_rows import (
    PURGE_STALE_ROWS_JOB,
    purge_stale_rows_job,
)
from app.repositories.channel_repositories import ChannelMessageReceiptRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.user_repositories import (
    OtpChallengeRepository,
    UserSessionRepository,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.channel_receipts import ChannelMessageReceiptDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import OtpChallengeDocument, UserSessionDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessTokenHash, OtpCodeHash
from app.use_cases.maintenance.purge_stale_rows_use_case import PurgeStaleRowsUseCase
from tests.storage.conftest import CollectionFactory
from tests.storage.storage_testing import FIXED_NANOSECONDS, build_fixed_wall_clock

NOW: int = FIXED_NANOSECONDS // 1_000
HOUR: int = 3_600_000_000
DAY: int = 24 * HOUR
TICK = JobTick(job_name=PURGE_STALE_ROWS_JOB, scheduled_at=Microseconds(NOW))


def session(expires_at: int) -> UserSessionDocument:
    return UserSessionDocument(
        user_id=UserId(),
        token_hash=AccessTokenHash(f"{expires_at:064d}"),
        expires_at=Microseconds(expires_at),
    )


def challenge(created_at: int) -> OtpChallengeDocument:
    return OtpChallengeDocument(
        login_method=LoginMethod.PHONE,
        phone_number=E164PhoneNumber("+995555123456"),
        delivery_channel=OtpDeliveryChannel.SMS,
        locale=LanguageTag("ka"),
        code_hash=OtpCodeHash("hash"),
        expires_at=Microseconds(created_at + 600_000_000),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


def receipt(created_at: int, message_id: str) -> ChannelMessageReceiptDocument:
    return ChannelMessageReceiptDocument(
        business_id=BusinessId(),
        channel=ChannelKind.WHATSAPP,
        provider_message_id=ProviderMessageId(message_id),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


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
    audit = AuditLogRepository(audit_collection)
    expired, at_expiry, valid = session(NOW - 1), session(NOW), session(NOW + 1)
    for stored in (expired, at_expiry, valid):
        sessions.save(stored)
    old_code, fresh_code = challenge(NOW - DAY - 1), challenge(NOW - HOUR)
    challenges.save(old_code)
    challenges.save(fresh_code)
    old_receipt, fresh_receipt = receipt(NOW - 31 * DAY, "1"), receipt(NOW - DAY, "2")
    assert receipts.record_if_new(old_receipt)
    assert receipts.record_if_new(fresh_receipt)
    use_case = PurgeStaleRowsUseCase(
        user_session_repo=sessions,
        otp_challenge_repo=challenges,
        channel_message_receipt_repo=receipts,
        audit_log_repo=audit,
        wall_clock=build_fixed_wall_clock(),
    )

    report = use_case.run(TICK)
    second_report = use_case.run(TICK)

    assert report.processed_count == 4
    assert second_report.processed_count == 0
    assert sessions.find_by_token_hash(expired.token_hash) is None
    assert sessions.find_by_token_hash(at_expiry.token_hash) is None
    assert sessions.find_by_token_hash(valid.token_hash) == valid
    assert [c.id for c in challenge_collection.list_all()] == [fresh_code.id]
    assert [r.id for r in receipt_collection.list_all()] == [fresh_receipt.id]
    entries = audit_collection.list_all()
    assert sorted(str(entry.entity) for entry in entries) == [
        "channel_message_receipt",
        "otp_challenge",
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
