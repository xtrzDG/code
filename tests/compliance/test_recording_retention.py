from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.compliance import PurgeExpiredRecordingsCommand
from app.schemas.typings.businesses.constrained_integers import (
    RecordingRetentionDays,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import (
    CallTranscriptText,
    ProviderCallId,
    RecordingStoragePath,
)
from tests.users.accounts_testbed import (
    GEORGIA_MOBILE,
    SECONDS_PER_DAY,
    USA_MOBILE,
    AccountsTestbed,
    build_accounts_testbed,
)


def store_call(
    testbed: AccountsTestbed,
    business: BusinessDocument,
    age_in_days: float,
    has_recording: bool = True,
    has_transcript: bool = True,
) -> CallDocument:
    started_at = Microseconds(
        testbed.clock.now_microseconds()
        - int(age_in_days * SECONDS_PER_DAY) * 1_000_000
    )
    call = CallDocument(
        business_id=business.id,
        started_at=started_at,
        recording_path=RecordingStoragePath(f"{business.id}/{age_in_days}.mp3")
        if has_recording
        else None,
        transcript=CallTranscriptText("Caller asked for a table.")
        if has_transcript
        else None,
        provider_call_id=ProviderCallId(f"{business.id}-{age_in_days}"),
    )
    testbed.call_repo.save(call)
    return call


def two_businesses(
    testbed: AccountsTestbed,
) -> tuple[BusinessDocument, BusinessDocument]:
    georgian_owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    american_owner = testbed.sign_in_with_phone(USA_MOBILE)
    georgian = testbed.create_restaurant(georgian_owner.user.id, "Sakhli")
    american = testbed.create_restaurant(american_owner.user.id, "Diner")
    american.recording_retention_days = RecordingRetentionDays(7)
    testbed.business_repo.save(american)
    return georgian, american


def test_each_business_keeps_recordings_for_its_own_retention_period() -> None:
    testbed = build_accounts_testbed()
    georgian, american = two_businesses(testbed)
    old_georgian = store_call(testbed, georgian, 91)
    recent_georgian = store_call(testbed, georgian, 89)
    old_american = store_call(testbed, american, 8)
    recent_american = store_call(testbed, american, 6.5)
    old_without_content = store_call(
        testbed,
        georgian,
        200,
        has_recording=False,
        has_transcript=False,
    )
    old_transcript_only = store_call(testbed, american, 30, has_recording=False)

    result = testbed.purge_expired_recordings.run(PurgeExpiredRecordingsCommand())

    assert result.scanned_businesses == 2
    assert result.purged_calls == 3
    assert result.deleted_recordings == 2
    assert set(testbed.recording_storage.deleted_paths) == {
        old_georgian.recording_path,
        old_american.recording_path,
    }
    for purged in (old_georgian, old_american, old_transcript_only):
        stored = testbed.call_repo.get(purged.business_id, purged.id)
        assert stored is not None
        assert stored.recording_path is None
        assert stored.transcript is None
        assert stored.provider_call_id == purged.provider_call_id
    for kept in (recent_georgian, recent_american):
        stored = testbed.call_repo.get(kept.business_id, kept.id)
        assert stored is not None
        assert stored.recording_path == kept.recording_path
        assert stored.transcript == kept.transcript
    untouched = testbed.call_repo.get(georgian.id, old_without_content.id)
    assert untouched is not None
    assert untouched.updated_at == old_without_content.updated_at


def test_purge_is_audited_without_an_actor_and_is_idempotent() -> None:
    testbed = build_accounts_testbed()
    georgian, american = two_businesses(testbed)
    old_call = store_call(testbed, georgian, 120)
    store_call(testbed, american, 10)

    testbed.purge_expired_recordings.run(PurgeExpiredRecordingsCommand())
    second_run = testbed.purge_expired_recordings.run(PurgeExpiredRecordingsCommand())

    georgian_entries = testbed.audit_log_repo.list_by_business(georgian.id)
    purge_entries = [
        entry
        for entry in georgian_entries
        if entry.action is AuditAction.RETENTION_PURGE
    ]
    assert [(entry.entity, entry.entity_id) for entry in purge_entries] == [
        ("call", str(old_call.id))
    ]
    assert purge_entries[0].actor_id is None
    assert purge_entries[0].created_at == testbed.clock.now_microseconds()
    assert second_run.purged_calls == 0
    assert second_run.deleted_recordings == 0
    assert len(testbed.recording_storage.deleted_paths) == 2


def test_purge_can_target_one_business() -> None:
    testbed = build_accounts_testbed()
    georgian, american = two_businesses(testbed)
    store_call(testbed, georgian, 100)
    american_call = store_call(testbed, american, 100)

    result = testbed.purge_expired_recordings.run(
        PurgeExpiredRecordingsCommand(business_id=georgian.id)
    )
    unknown = testbed.purge_expired_recordings.run(
        PurgeExpiredRecordingsCommand(business_id=BusinessId())
    )

    assert result.scanned_businesses == 1
    assert result.purged_calls == 1
    stored_american = testbed.call_repo.get(american.id, american_call.id)
    assert stored_american is not None
    assert stored_american.recording_path is not None
    assert unknown.scanned_businesses == 0
    assert unknown.purged_calls == 0


def test_retention_follows_the_clock() -> None:
    testbed = build_accounts_testbed()
    georgian, _ = two_businesses(testbed)
    call = store_call(testbed, georgian, 80)

    assert (
        testbed.purge_expired_recordings.run(
            PurgeExpiredRecordingsCommand()
        ).purged_calls
        == 0
    )

    testbed.clock.advance(11 * SECONDS_PER_DAY)

    assert (
        testbed.purge_expired_recordings.run(
            PurgeExpiredRecordingsCommand()
        ).purged_calls
        == 1
    )
    stored = testbed.call_repo.get(georgian.id, call.id)
    assert stored is not None
    assert stored.recording_path is None
